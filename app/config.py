"""Configuration for async broker (Redis)."""

import os

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
# Optional: Slack or Discord webhook URL; if set, high-urgency tickets (S > 0.8) trigger a POST.
WEBHOOK_URL: str = os.environ.get("WEBHOOK_URL", "")
