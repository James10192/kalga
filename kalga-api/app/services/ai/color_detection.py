"""
Détection de la couleur dominante d'une image — PIL + numpy uniquement.

Pipeline : downscale → quantification median-cut → suppression du fond →
conversion sRGB→Lab → nommage par distance perceptuelle CIEDE2000 vers une
palette FR. Sert de SUGGESTION de nom de variante (jamais d'autorité finale).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import io
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger("kalga.color")

# Palette de référence : nom FR → RGB représentatif.
_PALETTE_RGB: Dict[str, Tuple[int, int, int]] = {
    "rouge": (200, 30, 30),
    "bordeaux": (110, 20, 40),
    "rose": (230, 130, 170),
    "orange": (230, 130, 30),
    "jaune": (235, 210, 50),
    "moutarde": (200, 160, 40),
    "vert": (40, 160, 60),
    "kaki": (110, 110, 60),
    "turquoise": (40, 180, 180),
    "bleu": (40, 80, 200),
    "bleu marine": (25, 35, 80),
    "bleu ciel": (130, 190, 230),
    "violet": (120, 60, 170),
    "marron": (90, 55, 35),
    "camel": (175, 130, 85),
    "beige": (220, 200, 165),
    "taupe": (140, 120, 110),
    "noir": (20, 20, 20),
    "blanc": (245, 245, 245),
    "gris": (130, 130, 130),
}

_MAX_DIM = 200            # downscale cible
_QUANTIZE_COLORS = 8      # clusters median-cut
_BG_DELTA = 18.0          # ΔE en-dessous duquel un cluster est jugé "comme le fond"
_CONFIDENT_DE = 12.0      # ΔE en-dessous duquel le nommage est sûr
_UNCERTAIN_DE = 28.0      # ΔE au-dessus duquel le nommage est douteux


@dataclass
class ColorGuess:
    name: str
    confidence: float       # 0..1
    is_multicolor: bool
    reason: str


def _srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convertit un tableau RGB (..., 3) 0-255 en CIELAB (D65). Vectorisé."""
    arr = rgb.astype(np.float64) / 255.0
    # Linéarisation sRGB
    mask = arr > 0.04045
    arr = np.where(mask, ((arr + 0.055) / 1.055) ** 2.4, arr / 12.92)
    # sRGB linéaire → XYZ (matrice D65)
    m = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ])
    xyz = arr @ m.T
    # Normalisation par le blanc de référence D65
    white = np.array([0.95047, 1.00000, 1.08883])
    xyz = xyz / white
    eps = 216.0 / 24389.0
    kappa = 24389.0 / 27.0
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16.0) / 116.0)
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return np.stack([L, a, b], axis=-1)


def _ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> float:
    """Distance perceptuelle CIEDE2000 entre deux couleurs Lab (scalaires)."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    Cbar = (C1 + C2) / 2.0
    Cbar7 = Cbar ** 7
    G = 0.5 * (1 - np.sqrt(Cbar7 / (Cbar7 + 25.0 ** 7)))
    a1p = (1 + G) * a1
    a2p = (1 + G) * a2
    C1p = np.hypot(a1p, b1)
    C2p = np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0
    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p < 1e-10:
        dhp = 0.0
    else:
        dh = h2p - h1p
        if dh > 180:
            dh -= 360
        elif dh < -180:
            dh += 360
        dhp = dh
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp) / 2.0)
    Lbarp = (L1 + L2) / 2.0
    Cbarp = (C1p + C2p) / 2.0
    if C1p * C2p < 1e-10:
        hbarp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbarp = (h1p + h2p) / 2.0
    elif (h1p + h2p) < 360:
        hbarp = (h1p + h2p + 360) / 2.0
    else:
        hbarp = (h1p + h2p - 360) / 2.0
    T = (1 - 0.17 * np.cos(np.radians(hbarp - 30))
         + 0.24 * np.cos(np.radians(2 * hbarp))
         + 0.32 * np.cos(np.radians(3 * hbarp + 6))
         - 0.20 * np.cos(np.radians(4 * hbarp - 63)))
    dtheta = 30 * np.exp(-(((hbarp - 275) / 25.0) ** 2))
    Cbarp7 = Cbarp ** 7
    RC = 2 * np.sqrt(Cbarp7 / (Cbarp7 + 25.0 ** 7))
    SL = 1 + (0.015 * (Lbarp - 50) ** 2) / np.sqrt(20 + (Lbarp - 50) ** 2)
    SC = 1 + 0.045 * Cbarp
    SH = 1 + 0.015 * Cbarp * T
    RT = -np.sin(np.radians(2 * dtheta)) * RC
    return float(np.sqrt(
        (dLp / SL) ** 2
        + (dCp / SC) ** 2
        + (dHp / SH) ** 2
        + RT * (dCp / SC) * (dHp / SH)
    ))


# Palette Lab pré-calculée une fois.
_PALETTE_LAB: List[Tuple[str, np.ndarray]] = [
    (name, _srgb_to_lab(np.array(rgb)))
    for name, rgb in _PALETTE_RGB.items()
]


def _nearest_name(lab: np.ndarray) -> Tuple[str, float]:
    """Retourne (nom, ΔE) de l'ancre la plus proche."""
    best_name, best_de = "à préciser", float("inf")
    for name, anchor in _PALETTE_LAB:
        de = _ciede2000(lab, anchor)
        if de < best_de:
            best_name, best_de = name, de
    return best_name, best_de


def detect_color(image_bytes: bytes) -> ColorGuess:
    """Détecte la couleur dominante d'une image. Ne lève jamais d'exception."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        logger.debug(f"detect_color: image illisible: {e}")
        return ColorGuess(name="à préciser", confidence=0.0,
                          is_multicolor=False, reason="image illisible")

    img.thumbnail((_MAX_DIM, _MAX_DIM))
    arr = np.asarray(img)

    # Estimation de la couleur de fond via les 4 coins.
    h, w = arr.shape[0], arr.shape[1]
    corners = np.array([arr[0, 0], arr[0, w - 1], arr[h - 1, 0], arr[h - 1, w - 1]])
    bg_lab = _srgb_to_lab(corners.mean(axis=0))

    # Quantification median-cut → palette + comptes.
    q = img.quantize(colors=_QUANTIZE_COLORS, method=Image.Quantize.MEDIANCUT)
    palette = q.getpalette()  # liste plate [r,g,b, r,g,b, ...]
    counts = q.getcolors()    # liste de (count, palette_index)
    if not counts:
        return ColorGuess(name="à préciser", confidence=0.0,
                          is_multicolor=False, reason="quantification vide")

    clusters = []  # (count, rgb, lab, chroma)
    for count, idx in counts:
        r, g, b = palette[idx * 3], palette[idx * 3 + 1], palette[idx * 3 + 2]
        lab = _srgb_to_lab(np.array([r, g, b]))
        chroma = float(np.hypot(lab[1], lab[2]))
        clusters.append((count, (r, g, b), lab, chroma))

    # Suppression du fond : on écarte les clusters proches du fond OU très clairs
    # et désaturés (papier/ombre). Sauf si tout est achromatique → vrai article neutre.
    def is_background(lab, chroma):
        near_bg = _ciede2000(lab, bg_lab) < _BG_DELTA
        pale = lab[0] > 90 and chroma < 10
        return near_bg or pale

    foreground = [c for c in clusters if not is_background(c[2], c[3])]
    if not foreground:
        foreground = clusters  # article uni neutre (blanc/noir/gris)

    # Cluster dominant = pixels × pondération de chroma (le produit est souvent
    # plus vif que le fond/ombre).
    foreground.sort(key=lambda c: c[0] * (1.0 + c[3] / 50.0), reverse=True)
    top = foreground[0]
    top_lab, top_chroma = top[2], top[3]

    # Multicolore : ≥2 clusters de premier plan comparables et de teintes éloignées.
    is_multicolor = False
    if len(foreground) >= 2:
        second = foreground[1]
        if second[0] >= 0.6 * top[0] and second[3] > 12 and top_chroma > 12:
            if _ciede2000(top_lab, second[2]) > 40:
                is_multicolor = True

    # Achromatique : chroma basse → nommage par luminance.
    if top_chroma < 12:
        if top_lab[0] < 35:
            name, reason = "noir", "achromatique sombre"
        elif top_lab[0] > 80:
            name, reason = "blanc", "achromatique clair"
        else:
            name, reason = "gris", "achromatique moyen"
        return ColorGuess(name=name, confidence=0.85,
                          is_multicolor=is_multicolor, reason=reason)

    name, de = _nearest_name(top_lab)
    if de <= _CONFIDENT_DE:
        confidence = 0.9
    elif de >= _UNCERTAIN_DE:
        confidence = 0.35
    else:
        confidence = 0.9 - (de - _CONFIDENT_DE) / (_UNCERTAIN_DE - _CONFIDENT_DE) * 0.55
    if is_multicolor:
        confidence = min(confidence, 0.4)
    return ColorGuess(name=name, confidence=round(confidence, 2),
                      is_multicolor=is_multicolor, reason=f"ΔE={de:.1f}")
