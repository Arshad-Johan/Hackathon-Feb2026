"""Configuration for async broker (Redis)."""

import os

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
