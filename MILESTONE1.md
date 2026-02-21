# Milestone 1: Minimum Viable Router (MVR)

This document describes **Milestone 1 only**: the backend API and how to run and verify it.  
**The current application implements Milestone 2.** For the Intelligent Queue (async broker, transformer urgency, webhook), see [MILESTONE2.md](MILESTONE2.md).

---

## What Milestone 1 delivers

- **Classifier:** Routes tickets into **Billing**, **Technical**, or **Legal**. Regex-based urgency (e.g. "broken", "ASAP") sets priority.
- **Queue:** In-memory priority queue (heapq); higher-priority tickets are served first.
- **API:** FastAPI with endpoints to submit tickets, pop/peek next, get queue size, list queue (read-only), clear queue, and health check.
- **Data:** In-memory only; no database or file persistence.

---

## Setup

From the **project root**:

```bash
python -m venv .venv
```

**Activate the virtual environment:**

- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **Windows (Command Prompt):** `.venv\Scripts\activate.bat`
- **Mac/Linux:** `source .venv/bin/activate`

```bash
pip install -r requirements.txt
```

**Troubleshooting — "Cargo is not installed or is not on PATH" (pydantic-core):**  
Common with Python 3.13 or when the build subprocess cannot see Rust/Cargo.

- **Option A:** Add Cargo to your user PATH (e.g. `C:\Users\<You>\.cargo\bin` on Windows). Reopen the terminal and run `pip install -r requirements.txt` again.
- **Option B:** Use Python 3.11 or 3.12: `py -3.12 -m venv .venv` (or `python3.11`), then activate and `pip install -r requirements.txt`.

---

## Run (backend only)

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave this terminal open. You should see: `Uvicorn running on http://127.0.0.1:8000`.

---

## API (Milestone 1)

| Method   | Endpoint        | Description |
|----------|-----------------|-------------|
| `POST`   | `/tickets`      | Submit ticket (JSON). Returns classified + urgency; enqueues. |
| `GET`    | `/tickets/next` | Pop next highest-priority ticket. |
| `GET`    | `/tickets/peek` | Peek next without removing. |
| `GET`    | `/queue/size`   | Current queue length. |
| `GET`    | `/queue`        | List all waiting tickets in priority order (read-only). |
| `DELETE` | `/queue`        | Clear queue. |
| `GET`    | `/health`       | Health check. |

**Example — submit a ticket:**

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","subject":"Login broken ASAP","body":"Cannot login. Need fix ASAP."}'
```

Response includes `category`, `is_urgent`, and `priority_score`; the ticket is stored in the queue.

---

## Verifying Milestone 1

### Option 1: Interactive API docs

1. With the server running, open **http://localhost:8000/docs**.
2. Try **GET /health** → expect `{"status":"ok"}`.
3. Try **POST /tickets** with body: `{"ticket_id":"T-001","subject":"Login broken ASAP","body":"Cannot login. Need fix ASAP."}` → expect `"category":"Technical"`, `"is_urgent":true`, `"priority_score":1`.
4. Try **GET /queue/size** → expect `{"size":1}`.
5. Try **GET /tickets/next** → expect the ticket you submitted.

### Option 2: curl (second terminal)

Activate the venv, then:

```bash
# Health
curl http://localhost:8000/health
# Expect: {"status":"ok"}

# Submit urgent technical ticket
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","subject":"Login broken ASAP","body":"Cannot login. Need fix ASAP."}'
# Expect: "category":"Technical", "is_urgent":true, "priority_score":1

# Submit billing ticket (not urgent)
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-002","subject":"Wrong invoice","body":"I was charged twice."}'
# Expect: "category":"Billing", "is_urgent":false, "priority_score":0

# Queue size
curl http://localhost:8000/queue/size
# Expect: {"size":2}

# Pop next (urgent first)
curl http://localhost:8000/tickets/next
# Expect: T-001. Run again to get T-002.
```

### Option 3: Unit tests (no server)

```bash
pytest tests/test_unit.py -v
```

Covers the classifier and priority queue logic.

### Option 4: API tests (server must be running)

In a second terminal:

```bash
pytest tests/test_milestone1.py -v
```

Or use `python scripts/run_tests_live.py` to start the server, run tests, then stop it.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Create venv, activate, `pip install -r requirements.txt` |
| 2 | `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| 3 | Verify via http://localhost:8000/docs, curl, or pytest |

If the above work, Milestone 1 is complete. For the full project (including the web frontend), see the main [README.md](README.md).
