"""Configuration for async broker (Redis) and Milestone 3."""

import os

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
# Optional: Slack or Discord webhook URL; if set, high-urgency tickets (S > 0.8) trigger a POST.
WEBHOOK_URL: str = os.environ.get("WEBHOOK_URL", "")

# --- Milestone 3: Semantic deduplication ---
DEDUP_SIM_THRESHOLD: float = float(os.environ.get("DEDUP_SIM_THRESHOLD", "0.9"))
DEDUP_MIN_COUNT: int = int(os.environ.get("DEDUP_MIN_COUNT", "10"))
DEDUP_WINDOW_SECONDS: int = int(os.environ.get("DEDUP_WINDOW_SECONDS", "300"))  # 5 minutes

# --- Milestone 3: Circuit breaker ---
TRANSFORMER_LATENCY_MS: int = int(os.environ.get("TRANSFORMER_LATENCY_MS", "500"))
CIRCUIT_COOLDOWN_SECONDS: int = int(os.environ.get("CIRCUIT_COOLDOWN_SECONDS", "60"))
CIRCUIT_HALF_OPEN_PROBES: int = int(os.environ.get("CIRCUIT_HALF_OPEN_PROBES", "3"))

# --- Milestone 3: Skill-based routing ---
ROUTING_LOAD_PENALTY_FACTOR: float = float(os.environ.get("ROUTING_LOAD_PENALTY_FACTOR", "0.1"))
