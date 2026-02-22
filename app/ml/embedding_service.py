"""
Sentence embeddings for semantic deduplication.
Uses a lightweight model (e.g. all-MiniLM-L6-v2) to embed ticket text.
"""

import logging
from typing import List, Union

import numpy as np

logger = logging.getLogger(__name__)

# Lightweight sentence embedding model
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def _get_model(model_name: str = DEFAULT_MODEL):
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)
    return _model


def embed_ticket(subject: str, body: str, model_name: str = DEFAULT_MODEL) -> np.ndarray:
    """
    Embed ticket text (subject + body) into a fixed-size vector.
    Returns a 1D numpy array of shape (dim,) normalized to unit length for cosine similarity.
    """
    text = f"{subject or ''} {body or ''}".strip()
    if not text:
        # Return zero vector for empty text (will have zero similarity with others)
        m = _get_model(model_name)
        return np.zeros(m.get_sentence_embedding_dimension(), dtype=np.float32)
    model = _get_model(model_name)
    emb = model.encode(text, normalize_embeddings=True)
    if isinstance(emb, np.ndarray):
        return emb.astype(np.float32)
    return np.array(emb, dtype=np.float32)


def embed_batch(texts: List[str], model_name: str = DEFAULT_MODEL) -> np.ndarray:
    """Embed a batch of texts; returns shape (len(texts), dim)."""
    if not texts:
        m = _get_model(model_name)
        return np.zeros((0, m.get_sentence_embedding_dimension()), dtype=np.float32)
    model = _get_model(model_name)
    emb = model.encode(texts, normalize_embeddings=True)
    return np.asarray(emb, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: Union[np.ndarray, List[float]]) -> float:
    """
    Cosine similarity between two vectors: cos(θ) = A·B / (||A|| ||B||).
    Assumes vectors are already normalized so this reduces to dot product.
    """
    b = np.asarray(b, dtype=np.float32)
    if a.size != b.size:
        raise ValueError("Vector dimensions must match")
    dot = float(np.dot(a, b))
    return round(min(1.0, max(-1.0, dot)), 6)
