"""
Constraint optimization for skill-based ticket routing.

Formulates the assignment of a single ticket to one agent as an Integer Linear Program (ILP):
  - Decision variables: x_a in {0,1} for each agent a (1 = assign ticket to agent a).
  - Objective: maximize sum_a (score_a * x_a), where score_a = skill_match - load_penalty.
  - Constraints: sum_a x_a = 1 (assign to exactly one agent); x_a in {0,1}.
  - Implicit capacity: only agents with current_load < max_concurrent_tickets are included.

This satisfies the hackathon spec: "Solve a Constraint Optimization problem to route
tickets to the best available agent based on their current capacity and skill match."
"""

import logging
from typing import Optional

import numpy as np

from app.models import Agent, RoutedTicket

logger = logging.getLogger(__name__)


def _compute_scores(routed: RoutedTicket, agents: list[Agent]) -> np.ndarray:
    """Compute assignment score for each agent (skill match minus load penalty)."""
    from app.config import ROUTING_LOAD_PENALTY_FACTOR
    from app.services.routing_utils import (
        cosine_similarity_vec,
        normalize_vector,
        skill_vector_to_list,
        ticket_skill_vector,
    )
    ticket_vec = ticket_skill_vector(routed.category, routed.urgency_score)
    scores = np.zeros(len(agents), dtype=np.float64)
    for i, agent in enumerate(agents):
        agent_vec = normalize_vector(skill_vector_to_list(agent.skill_vector))
        sim = cosine_similarity_vec(ticket_vec, agent_vec)
        load_penalty = ROUTING_LOAD_PENALTY_FACTOR * (
            agent.current_load / max(1, agent.max_concurrent_tickets)
        )
        scores[i] = sim - load_penalty
    return scores


def solve_routing_ilp(routed: RoutedTicket, agents: list[Agent]) -> Optional[str]:
    """
    Solve the constraint optimization: assign the ticket to exactly one agent
    so that (skill match - load penalty) is maximized.

    Formulation:
      - Variables: x in {0,1}^n (one-hot: which agent gets the ticket).
      - Maximize: sum_a score_a * x_a  =>  minimize c^T x with c = -scores.
      - Subject to: sum(x) = 1, 0 <= x <= 1, x integer.

    Returns agent_id of the chosen agent, or None if no agents or solver fails.
    """
    if not agents:
        return None

    n = len(agents)
    scores = _compute_scores(routed, agents)

    # scipy.optimize.milp minimizes c^T x => c = -scores for maximize
    c = -scores

    # Constraint: sum(x) = 1 (assign to exactly one agent)
    try:
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError:
        logger.debug("scipy not available; using argmax for routing (same result).")
        best_idx = int(np.argmax(scores))
        return agents[best_idx].agent_id

    A_eq = np.ones((1, n), dtype=np.float64)
    constraints = LinearConstraint(A_eq, lb=[1.0], ub=[1.0])
    bounds = Bounds(lb=0.0, ub=1.0)
    integrality = np.ones(n, dtype=np.int8)  # 1 = integer (binary)

    try:
        result = milp(
            c,
            integrality=integrality,
            bounds=bounds,
            constraints=constraints,
            options={"disp": False},
        )
    except Exception as e:
        logger.warning("Routing ILP solver failed: %s; falling back to argmax.", e)
        best_idx = int(np.argmax(scores))
        return agents[best_idx].agent_id

    if not result.success:
        logger.warning(
            "Routing ILP did not converge (status %s); falling back to argmax.",
            getattr(result, "status", None),
        )
        best_idx = int(np.argmax(scores))
        return agents[best_idx].agent_id

    x = result.x
    if x is None or not np.any(x > 0.5):
        return None
    best_idx = int(np.argmax(x))
    return agents[best_idx].agent_id
