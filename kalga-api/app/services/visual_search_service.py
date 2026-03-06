"""
Service de recherche visuelle par similarité CLIP.
Chargement lazy du modèle (au 1er appel, ~150MB pour clip-vit-base-patch32).
"""
import io
import logging
import numpy as np
from typing import List, Tuple, Optional

logger = logging.getLogger("kalga.vision")

_clip_model = None
_clip_processor = None
EMBEDDING_DIM = 768         # clip-vit-base-patch32 pooler_output (CLIPVisionModel)
SIMILARITY_THRESHOLD = 0.70 # En dessous = pas assez similaire pour suggérer


def _load_clip():
    global _clip_model, _clip_processor
    if _clip_model is None:
        try:
            from transformers import CLIPVisionModel, CLIPProcessor
            # CLIPVisionModel donne directement pooler_output (768-dim)
            _clip_model = CLIPVisionModel.from_pretrained("openai/clip-vit-base-patch32")
            _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            logger.info("CLIP vision model chargé (clip-vit-base-patch32, 768-dim)")
        except ImportError:
            logger.warning("transformers/torch non installé — visual search indisponible")
            return None, None
    return _clip_model, _clip_processor


def compute_image_embedding(image_bytes: bytes) -> Optional[np.ndarray]:
    """
    Calcule l'embedding CLIP normalisé (768-dim float32) d'une image via CLIPVisionModel.
    Retourne None si l'image est invalide ou si CLIP n'est pas installé.
    """
    try:
        import torch
        from PIL import Image

        model, processor = _load_clip()
        if model is None:
            return None

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = processor(images=img, return_tensors="pt")

        with torch.no_grad():
            out = model(**inputs)

        # pooler_output: shape [1, 768] → squeeze → [768]
        embedding = out.pooler_output.squeeze(0).numpy().astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return None
        return embedding / norm

    except Exception as e:
        logger.error(f"Erreur calcul embedding: {e}")
        return None


def embedding_to_blob(embedding: np.ndarray) -> bytes:
    """Sérialise l'embedding numpy en bytes pour stockage SQLite BLOB."""
    return embedding.astype(np.float32).tobytes()


def blob_to_embedding(blob: bytes) -> np.ndarray:
    """Désérialise un BLOB SQLite en numpy array float32."""
    return np.frombuffer(blob, dtype=np.float32)


def find_similar_products(
    query_embedding: np.ndarray,
    product_embeddings: List[Tuple[int, str, Optional[bytes]]],
    top_k: int = 3,
    threshold: float = SIMILARITY_THRESHOLD,
) -> List[Tuple[str, float]]:
    """
    Retourne les top_k produits les plus similaires à l'image query.

    Args:
        query_embedding: Embedding de l'image client (512-dim normalisé)
        product_embeddings: Liste de (product_id, product_code, embedding_blob)
        top_k: Nombre max de résultats
        threshold: Score minimum (0-1) pour inclure un produit

    Returns:
        Liste de (product_code, similarity_score) triée par score décroissant
    """
    if not product_embeddings:
        return []

    scores = []
    for _product_id, product_code, blob in product_embeddings:
        if not blob:
            continue
        prod_emb = blob_to_embedding(blob)
        # Cosine similarity = dot product (embeddings normalisés)
        score = float(np.dot(query_embedding, prod_emb))
        if score >= threshold:
            scores.append((product_code, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]
