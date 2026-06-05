# Création de variantes en lot — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre à un marchand de créer N variantes (jusqu'à 30) d'un produit au même prix en une seule opération WhatsApp, soit par liste texte (tout type de variante), soit par lot de photos avec détection couleur assistée.

**Architecture:** Une variante reste une ligne `products` partageant un `group_id`. Un nouveau module pur `color_detection.py` (PIL+numpy) propose un nom de couleur depuis une photo (suggestion, jamais autorité). Un nouveau handler `BulkVariantCreationHandler` orchestre les deux flux conversationnels. Une nouvelle méthode repo `create_variants_batch` insère les N variantes atomiquement. Aucune migration de schéma, bridge non modifié.

**Tech Stack:** Python 3, FastAPI, aiosqlite, Pillow, numpy, pytest + pytest-asyncio.

**Spec de référence :** `docs/superpowers/specs/2026-06-05-creation-variantes-en-lot-design.md`

**Note d'exécution :** toutes les commandes `pytest` se lancent depuis le dossier `kalga-api/`.

---

## Structure des fichiers

| Fichier | Action | Responsabilité |
|---|---|---|
| `kalga-api/tests/conftest.py` | Créer | Fixture DB temporaire isolée |
| `kalga-api/pytest.ini` | Créer | Config pytest (asyncio auto) |
| `kalga-api/requirements-dev.txt` | Créer | Dépendances de test |
| `kalga-api/app/services/ai/color_detection.py` | Créer | bytes → `ColorGuess` (pur) |
| `kalga-api/app/database/repositories/product_repo.py` | Modifier | `create_variants_batch(...)` |
| `kalga-api/app/modules/merchant_commands/schemas.py` | Modifier | +2 `CreationStep`, +1 `CommandAction` |
| `kalga-api/app/modules/merchant_commands/handlers/bulk_variant_creation.py` | Créer | Orchestration liste / lot photos / validation |
| `kalga-api/app/modules/merchant_commands/handlers/__init__.py` | Modifier | Export du nouveau handler |
| `kalga-api/app/modules/merchant_commands/handlers/product_creation.py` | Modifier | Routage `_handle_ask_variant` |
| `kalga-api/app/modules/merchant_commands/service.py` | Modifier | Enregistrement steps + commande `variantes` |
| `kalga-api/tests/test_color_detection.py` | Créer | Tests détection couleur |
| `kalga-api/tests/test_product_repo_batch.py` | Créer | Tests création en lot |
| `kalga-api/tests/test_bulk_variant_parsing.py` | Créer | Tests parsing liste/corrections |
| `kalga-api/tests/test_bulk_variant_handler.py` | Créer | Tests handler (flux) |

---

## Task 0: Scaffolding des tests

**Files:**
- Create: `kalga-api/requirements-dev.txt`
- Create: `kalga-api/pytest.ini`
- Create: `kalga-api/tests/__init__.py`
- Create: `kalga-api/tests/conftest.py`

- [ ] **Step 1: Créer `requirements-dev.txt`**

```
pytest>=8.3.0
pytest-asyncio>=1.3.0
```

- [ ] **Step 2: Créer `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 3: Créer `tests/__init__.py`** (fichier vide)

```python
```

- [ ] **Step 4: Créer `tests/conftest.py`**

La connexion utilise une constante module `DB_PATH` (`app/database/connection.py`). On la remplace par un fichier temporaire et on initialise le schéma complet via `init_database()`.

```python
"""Fixtures de test : base SQLite temporaire isolée."""
import os
import tempfile
from pathlib import Path

import pytest_asyncio

from app.database import connection
from app.database.connection import init_database


@pytest_asyncio.fixture
async def temp_db(monkeypatch):
    """Crée une base SQLite temporaire isolée, schéma complet, nettoyée après le test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(connection, "DB_PATH", Path(path))
    await init_database()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass
```

- [ ] **Step 5: Vérifier que la collecte pytest fonctionne**

Run: `python -m pytest --collect-only -q`
Expected: 0 test collecté, sortie sans erreur d'import (« no tests ran »).

- [ ] **Step 6: Commit**

```bash
git add kalga-api/requirements-dev.txt kalga-api/pytest.ini kalga-api/tests/__init__.py kalga-api/tests/conftest.py
git commit -m "test(variantes): scaffolding pytest + fixture DB temporaire"
```

---

## Task 1: Module de détection couleur

**Files:**
- Create: `kalga-api/app/services/ai/color_detection.py`
- Test: `kalga-api/tests/test_color_detection.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Les images de test sont générées en mémoire avec Pillow (aucun fichier externe, déterministe).

```python
"""Tests de la détection de couleur dominante."""
import io

from PIL import Image

from app.services.ai.color_detection import detect_color, ColorGuess


def _img_bytes(color, size=(120, 120)):
    """Crée une image PNG unie de la couleur RGB donnée."""
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _img_object_on_white(obj_color, size=(200, 200), obj_box=(60, 60, 140, 140)):
    """Objet coloré centré sur fond blanc (simule un article photographié)."""
    img = Image.new("RGB", size, (255, 255, 255))
    for x in range(obj_box[0], obj_box[2]):
        for y in range(obj_box[1], obj_box[3]):
            img.putpixel((x, y), obj_color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_returns_color_guess():
    guess = detect_color(_img_bytes((200, 30, 30)))
    assert isinstance(guess, ColorGuess)


def test_solid_red_named_rouge():
    assert detect_color(_img_bytes((200, 30, 30))).name == "rouge"


def test_solid_blue_named_bleu():
    assert detect_color(_img_bytes((40, 80, 200))).name == "bleu"


def test_solid_green_named_vert():
    assert detect_color(_img_bytes((40, 160, 60))).name == "vert"


def test_pure_black_is_noir():
    assert detect_color(_img_bytes((10, 10, 10))).name == "noir"


def test_pure_white_is_blanc():
    assert detect_color(_img_bytes((245, 245, 245))).name == "blanc"


def test_gray_is_gris():
    assert detect_color(_img_bytes((128, 128, 128))).name == "gris"


def test_red_object_on_white_background_is_rouge_not_blanc():
    """Test clé : le fond blanc ne doit pas l'emporter sur l'objet rouge."""
    guess = detect_color(_img_object_on_white((200, 30, 30)))
    assert guess.name == "rouge"


def test_corrupt_bytes_graceful():
    guess = detect_color(b"not-an-image")
    assert isinstance(guess, ColorGuess)
    assert guess.confidence == 0.0


def test_confidence_high_for_clear_color():
    assert detect_color(_img_bytes((200, 30, 30))).confidence >= 0.6
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `python -m pytest tests/test_color_detection.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.ai.color_detection'`

- [ ] **Step 3: Implémenter le module**

```python
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
    if C1p * C2p == 0:
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
    if C1p * C2p == 0:
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
        confidence = 1.0 - (de - _CONFIDENT_DE) / (_UNCERTAIN_DE - _CONFIDENT_DE) * 0.55
    if is_multicolor:
        confidence = min(confidence, 0.4)
    return ColorGuess(name=name, confidence=round(confidence, 2),
                      is_multicolor=is_multicolor, reason=f"ΔE={de:.1f}")
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `python -m pytest tests/test_color_detection.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add kalga-api/app/services/ai/color_detection.py kalga-api/tests/test_color_detection.py
git commit -m "feat(variantes): module détection couleur (median-cut → Lab → CIEDE2000)"
```

---

## Task 2: Création de variantes en lot (repository)

**Files:**
- Modify: `kalga-api/app/database/repositories/product_repo.py`
- Test: `kalga-api/tests/test_product_repo_batch.py`

- [ ] **Step 1: Écrire les tests qui échouent**

```python
"""Tests de ProductRepository.create_variants_batch."""
import pytest

from app.database.repositories.product_repo import ProductRepository
from app.database.connection import get_connection


async def _make_merchant_and_base(repo):
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone) VALUES (?, ?)",
            ("Test", "2250700000000"),
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(
        merchant_id=merchant_id, name="Sac", price=15000, min_price=12000,
        description="Joli sac", group_id="GRP-TEST01",
    )
    return merchant_id, base


async def test_batch_creates_all_variants(temp_db):
    repo = ProductRepository()
    merchant_id, base = await _make_merchant_and_base(repo)
    created = await repo.create_variants_batch(
        merchant_id=merchant_id, base_name="Sac", price=15000, min_price=12000,
        description="Joli sac", group_id="GRP-TEST01",
        variants=[
            {"variant_name": "Rouge", "image_path": None},
            {"variant_name": "Bleu", "image_path": "b.jpg"},
            {"variant_name": "Noir", "image_path": None},
        ],
    )
    assert len(created) == 3


async def test_batch_shares_group_and_price(temp_db):
    repo = ProductRepository()
    merchant_id, base = await _make_merchant_and_base(repo)
    created = await repo.create_variants_batch(
        merchant_id=merchant_id, base_name="Sac", price=15000, min_price=12000,
        description=None, group_id="GRP-TEST01",
        variants=[{"variant_name": "Rouge", "image_path": None}],
    )
    v = created[0]
    assert v["group_id"] == "GRP-TEST01"
    assert v["price"] == 15000
    assert v["variant_name"] == "Rouge"
    assert v["name"] == "Sac - Rouge"


async def test_batch_codes_are_sequential_and_unique(temp_db):
    repo = ProductRepository()
    merchant_id, base = await _make_merchant_and_base(repo)
    created = await repo.create_variants_batch(
        merchant_id=merchant_id, base_name="Sac", price=15000, min_price=12000,
        description=None, group_id="GRP-TEST01",
        variants=[
            {"variant_name": "Rouge", "image_path": None},
            {"variant_name": "Bleu", "image_path": None},
        ],
    )
    codes = [v["code"] for v in created]
    assert len(set(codes)) == 2
    nums = sorted(int(c[2:]) for c in codes)
    assert nums[1] == nums[0] + 1


async def test_batch_rolls_back_on_failure(temp_db):
    """Un variant_name None viole NOT NULL → aucune variante ne doit être créée."""
    repo = ProductRepository()
    merchant_id, base = await _make_merchant_and_base(repo)
    before = await repo.get_by_merchant(merchant_id)
    with pytest.raises(Exception):
        await repo.create_variants_batch(
            merchant_id=merchant_id, base_name="Sac", price=15000, min_price=12000,
            description=None, group_id="GRP-TEST01",
            variants=[
                {"variant_name": "Rouge", "image_path": None},
                {"variant_name": None, "image_path": None},  # invalide
            ],
        )
    after = await repo.get_by_merchant(merchant_id)
    assert len(after) == len(before)  # rollback : rien d'ajouté
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `python -m pytest tests/test_product_repo_batch.py -v`
Expected: FAIL — `AttributeError: 'ProductRepository' object has no attribute 'create_variants_batch'`

- [ ] **Step 3: Implémenter la méthode dans `product_repo.py`**

Ajouter cette méthode dans la classe `ProductRepository` (après `create`, vers la ligne 84) :

```python
    async def create_variants_batch(
        self,
        merchant_id: int,
        base_name: str,
        price: float,
        min_price: float,
        description: Optional[str],
        group_id: str,
        variants: List[Dict[str, Any]],
        stock_quantity: int = -1,
        low_stock_threshold: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Crée N variantes partageant prix/group_id dans UNE transaction atomique.

        variants: liste de {"variant_name": str, "image_path": Optional[str]}.
        Le code (#K00x) est calculé une seule fois puis incrémenté.
        En cas d'échec sur une variante, toute la transaction est annulée.
        Retourne les lignes créées.
        """
        async with get_connection() as db:
            try:
                cursor = await db.execute(
                    "SELECT MAX(CAST(SUBSTR(code, 3) AS INTEGER)) FROM products"
                )
                row = await cursor.fetchone()
                next_num = (row[0] or 0) + 1

                created_ids = []
                for i, variant in enumerate(variants):
                    code = f"#K{next_num + i:03d}"
                    variant_name = variant["variant_name"]
                    full_name = f"{base_name} - {variant_name}"
                    cur = await db.execute(
                        """
                        INSERT INTO products
                            (merchant_id, name, code, price, min_price, description,
                             image_path, group_id, variant_name,
                             stock_quantity, low_stock_threshold)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (merchant_id, full_name, code, price, min_price, description,
                         variant.get("image_path"), group_id, variant_name,
                         stock_quantity, low_stock_threshold),
                    )
                    created_ids.append(cur.lastrowid)

                await db.commit()
            except Exception:
                await db.rollback()
                raise

            placeholders = ",".join("?" for _ in created_ids)
            cursor = await db.execute(
                f"SELECT * FROM products WHERE id IN ({placeholders}) ORDER BY id",
                tuple(created_ids),
            )
            rows = await cursor.fetchall()
            return [_row_to_dict(r) for r in rows]
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `python -m pytest tests/test_product_repo_batch.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add kalga-api/app/database/repositories/product_repo.py kalga-api/tests/test_product_repo_batch.py
git commit -m "feat(variantes): create_variants_batch atomique dans ProductRepository"
```

---

## Task 3: Nouveaux états et actions (schemas)

**Files:**
- Modify: `kalga-api/app/modules/merchant_commands/schemas.py`

- [ ] **Step 1: Ajouter les valeurs `CommandAction`**

Dans l'enum `CommandAction`, après la ligne `VARIANTS_COMPLETE = "variants_complete"` (ligne 19), ajouter :

```python
    VARIANTS_BATCH_CREATED = "variants_batch_created"
    VARIANT_BATCH_STEP = "variant_batch_step"
```

- [ ] **Step 2: Ajouter les valeurs `CreationStep`**

Dans l'enum `CreationStep`, après la ligne `ASK_ANOTHER_VARIANT = "ask_another_variant"` (ligne 64), ajouter :

```python
    VARIANT_BATCH_PHOTOS = "variant_batch_photos"
    VARIANT_BATCH_CONFIRM = "variant_batch_confirm"
```

- [ ] **Step 3: Vérifier l'import**

Run: `python -c "from app.modules.merchant_commands.schemas import CreationStep, CommandAction; print(CreationStep.VARIANT_BATCH_PHOTOS, CommandAction.VARIANTS_BATCH_CREATED)"`
Expected: `CreationStep.VARIANT_BATCH_PHOTOS CommandAction.VARIANTS_BATCH_CREATED` (ou leurs valeurs string selon config)

- [ ] **Step 4: Commit**

```bash
git add kalga-api/app/modules/merchant_commands/schemas.py
git commit -m "feat(variantes): états VARIANT_BATCH_* et actions associées"
```

---

## Task 4: Fonctions de parsing (liste + corrections)

**Files:**
- Create: `kalga-api/app/modules/merchant_commands/handlers/bulk_variant_creation.py` (helpers d'abord)
- Test: `kalga-api/tests/test_bulk_variant_parsing.py`

- [ ] **Step 1: Écrire les tests qui échouent**

```python
"""Tests des helpers de parsing du flux variantes en lot."""
from app.modules.merchant_commands.handlers.bulk_variant_creation import (
    parse_variant_list,
    parse_corrections,
    MAX_VARIANTS,
)


def test_parse_simple_list():
    assert parse_variant_list("rouge, bleu, noir") == ["rouge", "bleu", "noir"]


def test_parse_trims_and_drops_empty():
    assert parse_variant_list("rouge ,  , bleu ,") == ["rouge", "bleu"]


def test_parse_newlines_supported():
    assert parse_variant_list("rouge\nbleu\nnoir") == ["rouge", "bleu", "noir"]


def test_parse_dedupes_case_insensitive_keep_first():
    assert parse_variant_list("Rouge, rouge, ROUGE, bleu") == ["Rouge", "bleu"]


def test_parse_caps_at_max():
    items = ", ".join(f"c{i}" for i in range(MAX_VARIANTS + 5))
    assert len(parse_variant_list(items)) == MAX_VARIANTS


def test_parse_single_item_no_comma():
    assert parse_variant_list("rouge") == ["rouge"]


def test_corrections_ok_returns_empty():
    assert parse_corrections("ok", 3) == {}


def test_corrections_single():
    assert parse_corrections("3=beige", 3) == {3: "beige"}


def test_corrections_multiple():
    assert parse_corrections("3=beige, 1=bordeaux", 3) == {3: "beige", 1: "bordeaux"}


def test_corrections_ignores_out_of_range():
    assert parse_corrections("5=beige", 3) == {}


def test_corrections_unparseable_returns_empty():
    assert parse_corrections("n'importe quoi", 3) == {}
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `python -m pytest tests/test_bulk_variant_parsing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named '...bulk_variant_creation'`

- [ ] **Step 3: Créer le fichier avec les helpers**

```python
"""
Handler de création de variantes EN LOT.

Deux flux :
- Mode liste texte : "rouge, bleu, noir" → création immédiate (tout type de variante).
- Mode lot de photos : photos bufferisées → détection couleur (suggestion) →
  validation/correction → création.

La détection couleur n'est qu'une suggestion ; le marchand valide toujours.
"""
from typing import Optional, Any, Dict, List
import os
import re
import logging

from .base import BaseHandler
from ..session_manager import ProductSession, session_manager
from ..schemas import CommandResponse, CommandAction, CreationStep

logger = logging.getLogger("kalga.handlers.bulk_variant")

MAX_VARIANTS = 30

# Dossier des images uploadées (cohérent avec routers/products.py et main.py).
_UPLOADS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "uploads"
)


def parse_variant_list(text: str) -> List[str]:
    """
    Découpe une liste de noms de variantes sur virgules / retours à la ligne.
    Trim, supprime les vides, dédoublonne (insensible à la casse, garde la 1ʳᵉ
    occurrence), plafonne à MAX_VARIANTS.
    """
    raw = re.split(r"[,\n]+", text)
    result: List[str] = []
    seen = set()
    for item in raw:
        name = item.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(name)
        if len(result) >= MAX_VARIANTS:
            break
    return result


def parse_corrections(text: str, n: int) -> Dict[int, str]:
    """
    Parse des corrections du type "3=beige, 1=bordeaux".
    "ok"/"oui"/"valider" → {} (on accepte les suggestions).
    Indices hors plage [1..n] ignorés. Aucun motif valide → {}.
    """
    cleaned = text.strip().lower()
    if cleaned in ("ok", "oui", "valider", "valide", "c'est bon", "cest bon"):
        return {}
    corrections: Dict[int, str] = {}
    for match in re.finditer(r"(\d+)\s*=\s*([^,;\n]+)", text):
        idx = int(match.group(1))
        name = match.group(2).strip()
        if 1 <= idx <= n and name:
            corrections[idx] = name
    return corrections
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `python -m pytest tests/test_bulk_variant_parsing.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add kalga-api/app/modules/merchant_commands/handlers/bulk_variant_creation.py kalga-api/tests/test_bulk_variant_parsing.py
git commit -m "feat(variantes): helpers parsing liste + corrections"
```

---

## Task 5: Handler de variantes en lot (flux complet)

**Files:**
- Modify: `kalga-api/app/modules/merchant_commands/handlers/bulk_variant_creation.py`
- Test: `kalga-api/tests/test_bulk_variant_handler.py`

- [ ] **Step 1: Écrire les tests qui échouent**

```python
"""Tests du flux BulkVariantCreationHandler."""
import io
import os

import pytest
from PIL import Image

from app.database import get_db
from app.database.connection import get_connection
from app.database.repositories.product_repo import ProductRepository
from app.modules.merchant_commands.handlers.bulk_variant_creation import (
    BulkVariantCreationHandler,
)
from app.modules.merchant_commands.session_manager import (
    ProductSession, session_manager,
)
from app.modules.merchant_commands.schemas import CreationStep, CommandAction


async def _base_session(group_id="GRP-H1"):
    repo = ProductRepository()
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone) VALUES (?, ?)", ("M", "2250711111111")
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(
        merchant_id=merchant_id, name="Sac", price=15000, min_price=12000,
        description=None, group_id=group_id,
    )
    session = ProductSession(
        merchant_phone="2250711111111",
        step=CreationStep.VARIANT_BATCH_PHOTOS,
        data={
            "merchant_id": merchant_id, "name": "Sac", "price": 15000,
            "min_price": 12000, "description": None, "group_id": group_id,
            "original_code": base["code"], "batch_photos": [],
        },
    )
    return merchant_id, session


def _write_upload(filename, color):
    """Écrit une image unie dans le dossier uploads réel utilisé par le handler."""
    from app.modules.merchant_commands.handlers import bulk_variant_creation as mod
    os.makedirs(mod._UPLOADS_DIR, exist_ok=True)
    path = os.path.join(mod._UPLOADS_DIR, filename)
    Image.new("RGB", (80, 80), color).save(path)
    return path


async def test_text_list_creates_variants(temp_db):
    merchant_id, session = await _base_session()
    session.step = CreationStep.VARIANT_BATCH_CONFIRM  # mode liste passe direct
    session.set_data("pending_variants",
                     [{"variant_name": "Rouge", "image_path": None},
                      {"variant_name": "Bleu", "image_path": None}])
    handler = BulkVariantCreationHandler()
    db = await get_db()
    resp = await handler.handle(session, "ok", None, db)
    assert resp.action == CommandAction.VARIANTS_BATCH_CREATED
    repo = ProductRepository()
    products = await repo.get_by_merchant(merchant_id)
    names = {p["name"] for p in products}
    assert "Sac - Rouge" in names and "Sac - Bleu" in names


async def test_batch_photos_buffer_then_confirm(temp_db):
    merchant_id, session = await _base_session(group_id="GRP-H2")
    handler = BulkVariantCreationHandler()
    db = await get_db()

    p1 = _write_upload("h2_red.png", (200, 30, 30))
    p2 = _write_upload("h2_blue.png", (40, 80, 200))
    # Deux photos bufferisées
    await handler.handle(session, "", "h2_red.png", db)
    await handler.handle(session, "", "h2_blue.png", db)
    assert len(session.get_data("batch_photos")) == 2

    # "fini" → passage en confirmation
    resp = await handler.handle(session, "fini", None, db)
    assert session.step == CreationStep.VARIANT_BATCH_CONFIRM
    assert "rouge" in resp.response.lower()
    assert "bleu" in resp.response.lower()

    # "ok" → création
    resp2 = await handler.handle(session, "ok", None, db)
    assert resp2.action == CommandAction.VARIANTS_BATCH_CREATED
    repo = ProductRepository()
    products = await repo.get_by_merchant(merchant_id)
    assert any(p["name"] == "Sac - rouge" for p in products)
    os.remove(p1)
    os.remove(p2)


async def test_batch_confirm_with_correction(temp_db):
    merchant_id, session = await _base_session(group_id="GRP-H3")
    session.step = CreationStep.VARIANT_BATCH_CONFIRM
    session.set_data("pending_variants",
                     [{"variant_name": "rouge", "image_path": None},
                      {"variant_name": "à préciser", "image_path": None}])
    handler = BulkVariantCreationHandler()
    db = await get_db()
    resp = await handler.handle(session, "2=édition limitée", None, db)
    assert resp.action == CommandAction.VARIANTS_BATCH_CREATED
    repo = ProductRepository()
    products = await repo.get_by_merchant(merchant_id)
    assert any(p["name"] == "Sac - édition limitée" for p in products)


async def test_fini_with_no_photo_reasks(temp_db):
    merchant_id, session = await _base_session(group_id="GRP-H4")
    handler = BulkVariantCreationHandler()
    db = await get_db()
    resp = await handler.handle(session, "fini", None, db)
    assert resp.action == CommandAction.ASK_AGAIN
    assert session.step == CreationStep.VARIANT_BATCH_PHOTOS
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run: `python -m pytest tests/test_bulk_variant_handler.py -v`
Expected: FAIL — `ImportError: cannot import name 'BulkVariantCreationHandler'`

- [ ] **Step 3: Ajouter le handler dans `bulk_variant_creation.py`**

Ajouter à la fin du fichier (après les helpers) :

```python
def _read_upload_bytes(image_path: str) -> Optional[bytes]:
    """Lit les bytes d'une image stockée dans le dossier uploads."""
    if not image_path:
        return None
    full = os.path.join(_UPLOADS_DIR, image_path)
    try:
        with open(full, "rb") as f:
            return f.read()
    except OSError as e:
        logger.debug(f"_read_upload_bytes: {e}")
        return None


class BulkVariantCreationHandler(BaseHandler):
    """Gère les flux de création de variantes en lot."""

    async def handle(
        self,
        session: ProductSession,
        message: str,
        image_path: Optional[str],
        db: Any,
    ) -> CommandResponse:
        step = session.step
        if step == CreationStep.VARIANT_BATCH_PHOTOS:
            return await self._handle_batch_photos(session, message, image_path, db)
        if step == CreationStep.VARIANT_BATCH_CONFIRM:
            return await self._handle_batch_confirm(session, message, db)
        logger.warning(f"Étape non gérée par BulkVariantCreationHandler: {step}")
        return self._error("Erreur interne: étape non reconnue")

    async def _handle_batch_photos(
        self, session, message, image_path, db
    ) -> CommandResponse:
        """Bufferise les photos ; 'fini' → récap de validation."""
        if image_path:
            from ....services.ai.color_detection import detect_color
            img_bytes = _read_upload_bytes(image_path)
            guess = detect_color(img_bytes) if img_bytes else None
            buffer = session.get_data("batch_photos") or []
            buffer.append({
                "image_path": image_path,
                "name": guess.name if guess else "à préciser",
                "confidence": guess.confidence if guess else 0.0,
            })
            session.set_data("batch_photos", buffer)
            if len(buffer) == 1:
                return self._response(
                    "📸 Photo reçue ! Envoie les autres, puis écris *fini*.",
                    CommandAction.VARIANT_BATCH_STEP,
                )
            return self._ignored()  # silence anti-ban sur les suivantes

        if message.strip().lower() in ("fini", "termine", "terminé", "ok", "stop"):
            buffer = session.get_data("batch_photos") or []
            if not buffer:
                return self._response(
                    "Je n'ai encore reçu aucune photo. Envoie-les puis écris *fini*.",
                    CommandAction.ASK_AGAIN,
                )
            pending = [
                {"variant_name": item["name"], "image_path": item["image_path"]}
                for item in buffer
            ]
            session.set_data("pending_variants", pending)
            session.update_step(CreationStep.VARIANT_BATCH_CONFIRM)
            return self._response(self._build_recap(buffer),
                                  CommandAction.VARIANT_BATCH_STEP)

        return self._response(
            "Envoie tes photos une par une, puis écris *fini*.",
            CommandAction.ASK_AGAIN,
        )

    def _build_recap(self, buffer: List[Dict]) -> str:
        lines = ["J'ai reçu ces photos, voici les noms détectés :", ""]
        for i, item in enumerate(buffer, start=1):
            mark = "✅" if item["confidence"] >= 0.6 else "⚠️"
            lines.append(f"{i}. {item['name']}  {mark}")
        lines.append("")
        lines.append('→ Réponds *ok* pour créer, ou corrige : ex. "2=beige, 1=bordeaux"')
        return "\n".join(lines)

    async def _handle_batch_confirm(self, session, message, db) -> CommandResponse:
        """Applique les corrections puis crée les variantes."""
        pending = session.get_data("pending_variants") or []
        if not pending:
            session_manager.delete(session.merchant_phone)
            return self._error("Aucune variante en attente. Recommence avec *variantes #code*.")

        corrections = parse_corrections(message, len(pending))
        cleaned = message.strip().lower()
        is_accept = cleaned in ("ok", "oui", "valider", "valide", "c'est bon", "cest bon")
        if not corrections and not is_accept:
            return self._response(
                'Réponds *ok* pour valider, ou corrige : ex. "2=beige".',
                CommandAction.ASK_AGAIN,
            )
        for idx, name in corrections.items():
            pending[idx - 1]["variant_name"] = name

        # Refus de création si une variante reste "à préciser"
        unresolved = [i + 1 for i, v in enumerate(pending)
                      if v["variant_name"] == "à préciser"]
        if unresolved:
            nums = ", ".join(str(n) for n in unresolved)
            return self._response(
                f"Nomme d'abord : {nums}. Ex. \"{unresolved[0]}=rouge\".",
                CommandAction.ASK_AGAIN,
            )

        from ....database.repositories.product_repo import ProductRepository
        repo = ProductRepository()
        try:
            created = await repo.create_variants_batch(
                merchant_id=session.get_data("merchant_id"),
                base_name=session.get_data("name"),
                price=session.get_data("price"),
                min_price=session.get_data("min_price"),
                description=session.get_data("description"),
                group_id=session.get_data("group_id"),
                variants=pending,
            )
        except Exception as e:
            logger.error(f"Échec création variantes en lot: {e}")
            session_manager.delete(session.merchant_phone)
            return self._error("Erreur lors de la création des variantes. Réessaie.")

        original_code = session.get_data("original_code")
        session_manager.delete(session.merchant_phone)
        lines = [f"✅ *{len(created)} variantes créées !*", ""]
        for v in created:
            lines.append(f"• {v['variant_name']} ({v['code']})")
        lines.append("")
        lines.append(f"👉 Ajoute *{original_code}* dans ton Status WhatsApp.")
        return self._response("\n".join(lines), CommandAction.VARIANTS_BATCH_CREATED,
                              product_code=original_code)
```

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `python -m pytest tests/test_bulk_variant_handler.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add kalga-api/app/modules/merchant_commands/handlers/bulk_variant_creation.py kalga-api/tests/test_bulk_variant_handler.py
git commit -m "feat(variantes): BulkVariantCreationHandler (lot photos + validation)"
```

---

## Task 6: Câblage (routage, service, commande, export)

**Files:**
- Modify: `kalga-api/app/modules/merchant_commands/handlers/__init__.py`
- Modify: `kalga-api/app/modules/merchant_commands/handlers/product_creation.py`
- Modify: `kalga-api/app/modules/merchant_commands/service.py`
- Test: `kalga-api/tests/test_bulk_variant_handler.py` (ajout)

- [ ] **Step 1: Écrire le test d'intégration qui échoue**

Ajouter à la fin de `tests/test_bulk_variant_handler.py` :

```python
from app.modules.merchant_commands.service import MerchantCommandService
from app.modules.merchant_commands.schemas import MerchantMessage


async def test_command_variantes_creates_list(temp_db):
    repo = ProductRepository()
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone) VALUES (?, ?)", ("M", "2250799999999")
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(
        merchant_id=merchant_id, name="Sac", price=15000, min_price=12000,
        description=None,
    )
    service = MerchantCommandService()
    msg = MerchantMessage(
        merchant_phone="2250799999999",
        message=f"variantes {base['code']} rouge, bleu, noir",
    )
    resp = await service.process_command(msg)
    assert resp.action == CommandAction.VARIANTS_BATCH_CREATED
    products = await repo.get_by_merchant(merchant_id)
    names = {p["name"] for p in products}
    assert {"Sac - rouge", "Sac - bleu", "Sac - noir"} <= names


async def test_ask_variant_comma_routes_to_bulk(temp_db):
    """Au step ASK_VARIANT, une liste avec virgule crée les variantes en lot."""
    repo = ProductRepository()
    async with get_connection() as db:
        cur = await db.execute(
            "INSERT INTO merchants (name, phone) VALUES (?, ?)", ("M", "2250788888888")
        )
        await db.commit()
        merchant_id = cur.lastrowid
    base = await repo.create(
        merchant_id=merchant_id, name="Sac", price=15000, min_price=12000,
        description=None,
    )
    session_manager.create(
        merchant_phone="2250788888888",
        step=CreationStep.ASK_VARIANT,
        data={"merchant_id": merchant_id, "name": "Sac", "price": 15000,
              "min_price": 12000, "description": None,
              "product_code": base["code"], "product_id": base["id"]},
    )
    service = MerchantCommandService()
    msg = MerchantMessage(merchant_phone="2250788888888", message="rouge, bleu")
    resp = await service.process_command(msg)
    assert resp.action == CommandAction.VARIANTS_BATCH_CREATED
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `python -m pytest tests/test_bulk_variant_handler.py::test_command_variantes_creates_list -v`
Expected: FAIL (la commande `variantes` n'est pas encore reconnue → action `UNKNOWN`)

- [ ] **Step 3: Exporter le handler dans `handlers/__init__.py`**

Lire le fichier existant, ajouter l'import et l'export. Ajouter la ligne d'import à côté des autres :

```python
from .bulk_variant_creation import BulkVariantCreationHandler
```

Et ajouter `"BulkVariantCreationHandler"` à la liste `__all__` si elle existe.

- [ ] **Step 4: Router le step `ASK_VARIANT` vers le mode lot (product_creation.py)**

Dans `_handle_ask_variant` (`handlers/product_creation.py`, ~ligne 219), au tout début de la méthode après `msg_lower = message.lower().strip()`, insérer le routage liste / photos AVANT le bloc `if msg_lower in ['oui', ...]` :

```python
        # Mode lot — liste de couleurs/variantes (présence d'une virgule = liste explicite)
        if "," in message:
            from .bulk_variant_creation import parse_variant_list
            names = parse_variant_list(message)
            if names:
                group_id = await self._ensure_group_id(session, db)
                session.update_step(CreationStep.VARIANT_BATCH_CONFIRM)
                session.set_data("group_id", group_id)
                session.set_data("original_code", session.get_data("product_code"))
                session.set_data(
                    "pending_variants",
                    [{"variant_name": n, "image_path": None} for n in names],
                )
                from .bulk_variant_creation import BulkVariantCreationHandler
                return await BulkVariantCreationHandler().handle(session, "ok", None, db)

        # Mode lot — envoi de photos
        if msg_lower in ("photos", "photo"):
            group_id = await self._ensure_group_id(session, db)
            session.update_step(CreationStep.VARIANT_BATCH_PHOTOS)
            session.set_data("group_id", group_id)
            session.set_data("original_code", session.get_data("product_code"))
            session.set_data("batch_photos", [])
            return self._response(
                "📸 Envoie tes photos une par une, puis écris *fini*.\n"
                "Je détecte la couleur de chacune automatiquement.",
                CommandAction.VARIANT_BATCH_STEP,
            )
```

Puis ajouter la méthode helper `_ensure_group_id` dans la classe `ProductCreationHandler` (réutilise la logique de génération de group_id déjà présente, factorisée) :

```python
    async def _ensure_group_id(self, session: ProductSession, db: Any) -> str:
        """Retourne le group_id du produit de base, en le générant si absent."""
        product_code = session.get_data("product_code")
        product = await db.get_product_by_code(product_code)
        group_id = product.get("group_id") if product else None
        if not group_id:
            group_id = await db.generate_group_id()
            from ....database.connection import get_connection
            async with get_connection() as conn:
                await conn.execute(
                    "UPDATE products SET group_id = ? WHERE id = ?",
                    (group_id, product["id"]),
                )
                await conn.commit()
        return group_id
```

Et enrichir le message proposant les variantes (dans `_handle_image`, le texte « Tu as d'autres couleurs/modèles ? ») pour mentionner les nouveaux modes. Remplacer le bloc texte existant :

```python
                "🎨 Tu as *d'autres couleurs/modèles* de ce produit?\n\n"
                "Réponds *oui* pour ajouter une variante\n"
                "Réponds *non* pour terminer",
```

par :

```python
                "🎨 Tu as *d'autres variantes* (couleurs, tailles, modèles)?\n\n"
                "• Tape la liste : ex. *rouge, bleu, noir* → créées d'un coup\n"
                "• Ou écris *photos* pour envoyer un lot (je détecte les couleurs)\n"
                "• Ou *oui* pour les ajouter une par une\n"
                "• Ou *non* pour terminer",
```

- [ ] **Step 5: Enregistrer les steps + la commande dans `service.py`**

Dans `_handle_creation_step` (`service.py`, ~ligne 142), ajouter le set des steps lot et le dispatch. Après la définition de `variant_steps` (ligne ~145), ajouter :

```python
            # Étapes de création de variantes en lot
            bulk_variant_steps = {
                CreationStep.VARIANT_BATCH_PHOTOS,
                CreationStep.VARIANT_BATCH_CONFIRM,
            }
```

Puis dans la chaîne de dispatch `if step in product_steps: ... elif step in variant_steps: ...`, ajouter une branche AVANT le `else` final :

```python
            elif step in bulk_variant_steps:
                return await self.bulk_variant_handler.handle(
                    current_session, message, image_path, db
                )
```

Dans `__init__` de `MerchantCommandService` (ligne ~36), ajouter l'instance :

```python
        self.bulk_variant_handler = BulkVariantCreationHandler()
```

Et l'import en tête (ligne ~12, dans le `from .handlers import (...)`), ajouter `BulkVariantCreationHandler,`.

Enfin, ajouter la commande autonome `variantes #K0xx ...` dans `_handle_command`, JUSTE AVANT le bloc `variante_match` existant (~ligne 232) pour qu'elle soit prioritaire sur `variante` :

```python
        # === CRÉATION DE VARIANTES EN LOT (liste) ===
        bulk_match = re.search(
            r'variantes?\s+#?(K?\d{3})\s+(.+)', message, re.IGNORECASE | re.DOTALL
        )
        if bulk_match:
            return await self._start_bulk_variants(bulk_match, merchant, db)
```

Et ajouter la méthode `_start_bulk_variants` dans la classe (à côté de `_start_variant_creation`, ~ligne 549) :

```python
    async def _start_bulk_variants(
        self, match: re.Match, merchant: dict, db
    ) -> CommandResponse:
        """Crée plusieurs variantes d'un coup : 'variantes #K001 rouge, bleu, noir'."""
        from .handlers.bulk_variant_creation import parse_variant_list, BulkVariantCreationHandler
        code = f"#K{match.group(1).replace('K', '').replace('k', '')}"
        names = parse_variant_list(match.group(2))
        product = await db.get_product_by_code(code)
        if not product or product['merchant_id'] != merchant['id']:
            return CommandResponse(
                response=f"Produit {code} non trouvé ou non autorisé.",
                action=CommandAction.ERROR,
            )
        if not names:
            return CommandResponse(
                response="Donne au moins une variante. Ex: *variantes #K001 rouge, bleu*",
                action=CommandAction.ERROR,
            )
        group_id = product.get('group_id')
        if not group_id:
            group_id = await db.generate_group_id()
            from ...database.connection import get_connection
            async with get_connection() as conn:
                await conn.execute(
                    "UPDATE products SET group_id = ? WHERE id = ?",
                    (group_id, product['id']),
                )
                await conn.commit()
        session_manager.create(
            merchant_phone=merchant['phone'],
            step=CreationStep.VARIANT_BATCH_CONFIRM,
            data={
                "merchant_id": merchant['id'], "name": product['name'],
                "price": product['price'], "min_price": product['min_price'],
                "description": product.get('description'), "group_id": group_id,
                "original_code": code,
                "pending_variants": [
                    {"variant_name": n, "image_path": None} for n in names
                ],
            },
        )
        session = session_manager.get(merchant['phone'])
        return await BulkVariantCreationHandler().handle(session, "ok", None, db)
```

- [ ] **Step 6: Lancer toute la suite**

Run: `python -m pytest tests/ -v`
Expected: PASS (tous les tests des tâches 1, 2, 4, 5, 6)

- [ ] **Step 7: Commit**

```bash
git add kalga-api/app/modules/merchant_commands/handlers/__init__.py kalga-api/app/modules/merchant_commands/handlers/product_creation.py kalga-api/app/modules/merchant_commands/service.py kalga-api/tests/test_bulk_variant_handler.py
git commit -m "feat(variantes): câblage routage ASK_VARIANT, commande 'variantes', dispatch service"
```

---

## Task 7: Vérification finale

- [ ] **Step 1: Lancer la suite complète**

Run: `python -m pytest tests/ -v`
Expected: PASS sur l'ensemble.

- [ ] **Step 2: Vérification d'imports de l'app**

Run: `python -c "from app.main import app; print('OK import app')"`
Expected: `OK import app` (aucune erreur d'import circulaire).

- [ ] **Step 3: Mettre à jour le statut de la spec**

Dans `docs/superpowers/specs/2026-06-05-creation-variantes-en-lot-design.md`, changer la ligne `**Statut**` en `**Statut** : Implémenté`.

- [ ] **Step 4: Commit final**

```bash
git add docs/superpowers/specs/2026-06-05-creation-variantes-en-lot-design.md
git commit -m "docs(variantes): marque la spec comme implémentée"
```

---

## Notes de dette tracée

- **Réception des photos en lot** : repose sur l'envoi séquentiel de photos par le bridge (chaque photo = 1 appel `/api/merchant/command`). Si WhatsApp regroupe un album différemment, le buffer reste correct mais l'accusé « Photo reçue » n'apparaît que sur la première — comportement voulu (anti-ban).
- **Détection couleur** : limites assumées (doré/argenté, motifs → confiance basse, `is_multicolor`). Remplaçable par un modèle vision via la même signature `detect_color(bytes) -> ColorGuess` (approche C, hors périmètre).
- **`_UPLOADS_DIR`** est recalculé localement dans le handler (cohérent avec `routers/products.py` et `main.py`, qui dupliquent déjà cette constante). Une centralisation dans `core/config.py` serait souhaitable mais hors périmètre.
