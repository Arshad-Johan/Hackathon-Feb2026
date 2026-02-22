"""
Map ticket category (and optional urgency) to a ticket skill vector for routing.
Used to compute cosine similarity with agent skill vectors.
"""

import math

from app.models import SkillVector, TicketCategory


def ticket_skill_vector(category: TicketCategory, urgency_score: float = 0.5) -> list[float]:
    """
    Derive a unit-length skill vector for a ticket from its category.
    Technical -> [1,0,0], Billing -> [0,1,0], Legal -> [0,0,1].
    Urgency can be used later to weight; for now we use category only.
    """
    u = 1.0  # optional: scale by urgency
    if category == TicketCategory.TECHNICAL:
        vec = [u, 0.0, 0.0]
    elif category == TicketCategory.BILLING:
        vec = [0.0, u, 0.0]
    else:
        vec = [0.0, 0.0, u]
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return [1/3**0.5, 1/3**0.5, 1/3**0.5]
    return [x / norm for x in vec]


def skill_vector_to_list(sv: SkillVector) -> list[float]:
    """[tech, billing, legal] for cosine similarity."""
    return [sv.tech, sv.billing, sv.legal]


def normalize_vector(vec: list[float]) -> list[float]:
    """Return unit-length vector."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return [1/3**0.5] * 3
    return [x / norm for x in vec]


def cosine_similarity_vec(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors (assume same length)."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return round(min(1.0, max(-1.0, dot)), 6)
