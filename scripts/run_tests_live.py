#!/usr/bin/env python3
"""
Start the API server, run pytest against it, then stop the server.
Usage: python scripts/run_tests_live.py
(Run from project root with venv activated.)
"""

import os
import subprocess
import sys
import time

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.http_client import get

BASE_URL = "http://127.0.0.1:8765"


def wait_for_server(timeout=10):
    for _ in range(timeout):
        try:
            r = get(f"{BASE_URL}/health")
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for_server():
            print("Server did not start in time.")
            sys.exit(1)
        env = os.environ.copy()
        env["BASE_URL"] = BASE_URL
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_milestone1.py", "-v"],
            env=env,
        )
        sys.exit(result.returncode)
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
