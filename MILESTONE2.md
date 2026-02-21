# Milestone 2: The Intelligent Queue

This document describes **Milestone 2**: production-grade reliability, transformer-based urgency, async broker, and webhook integration.

---

## What Milestone 2 delivers

- **ML Component:** Transformer-based model (DistilBERT fine-tuned on SST-2) for **regression-style Sentiment Analysis**. Produces a continuous **urgency score S ∈ [0, 1]**; replaces the baseline regex urgency. Category remains regex-based (Billing / Technical / Legal).
- **System Component:** **Asynchronous Broker** using **Redis** and **ARQ**:
  - **POST /tickets** returns **202 Accepted** immediately with `ticket_id` and `job_id`.
  - Background workers (ARQ) classify tickets, compute S, and push to a Redis-backed processed queue.
  - API pops from the processed queue via **GET /tickets/next** (highest urgency first).
- **Concurrency:** Redis **ZPOPMAX** is atomic; multiple workers and 10+ simultaneous requests at the same time are safe. No duplicate processing; ARQ job queue and Redis sorted set handle distribution.
- **Integration:** Optional **Slack/Discord webhook**. When **S > 0.8**, the worker POSTs a mock payload to `WEBHOOK_URL` (env). Fire-and-forget; does not fail the job if the webhook fails.
- **Batch submission:** **POST /tickets/batch** accepts an array of tickets and returns **202 Accepted** with one `job_id` per ticket; each is enqueued for processing.
- **Activity stream:** **GET /activity** returns recent backend events (ticket accepted, ticket processed by worker, ticket popped, queue cleared). The API keeps an in-memory log; the worker publishes **ticket_processed** via Redis pub/sub so the Activity tab shows end-to-end flow.

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

**You need Redis running** (see [RUN.md](RUN.md)). Optional: set `WEBHOOK_URL` for high-urgency notifications (S > 0.8).

**Troubleshooting — "Cargo is not installed or is not on PATH" (pydantic-core):**  
Use Python 3.11/3.12 or add Cargo to PATH; see main [README.md](README.md).

---

## Run (backend: API + worker)

**Terminal 1 — API:**

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Worker (same venv):**

```bash
python -m app.worker
```

Leave both running. Tickets are accepted with 202 and processed by the worker into the Redis processed queue.

**Optional webhook (Terminal 2):**

```powershell
$env:WEBHOOK_URL = "https://hooks.slack.com/services/..."
python -m app.worker
```

---

## API (Milestone 2)

| Method   | Endpoint         | Description |
|----------|------------------|-------------|
| `POST`   | `/tickets`       | Submit ticket (JSON). Returns **202 Accepted** with `ticket_id`, `job_id`; worker enqueues when done. |
| `POST`   | `/tickets/batch` | Submit multiple tickets (JSON array). Returns **202 Accepted** with `accepted: [{ ticket_id, job_id }, ...]` in same order. |
| `GET`    | `/tickets/next`  | Pop next highest-urgency ticket from processed queue. 404 if empty. |
| `GET`    | `/tickets/peek` | Peek next without removing. |
| `GET`    | `/queue/size`   | Processed queue length. |
| `GET`    | `/queue`        | List all waiting tickets in priority order (read-only). |
| `DELETE` | `/queue`        | Clear processed queue. |
| `GET`    | `/activity`     | Recent backend activity (query `?limit=100`). Returns `{ events: [{ ts, type, data }, ...] }`. |
| `GET`    | `/health`       | Health check. |
| `POST`   | `/urgency-score`| Test transformer only (body: `{"text":"..."}`). Returns `urgency_score` S and `is_urgent` (S ≥ 0.5). |

**Example — submit a ticket (202 immediately):**

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","subject":"Login broken ASAP","body":"Cannot login. Need fix ASAP."}'
```

Response: **202** and `{"ticket_id":"T-001","job_id":"...","message":"Accepted for processing"}`.

**Example — submit multiple tickets (batch):**

```bash
curl -X POST http://localhost:8000/tickets/batch \
  -H "Content-Type: application/json" \
  -d '[{"ticket_id":"T-001","subject":"Login broken","body":"Cannot login."},{"ticket_id":"T-002","subject":"Wrong invoice","body":"Charged twice."}]'
```

Response: **202** and `{"accepted":[{"ticket_id":"T-001","job_id":"...","message":"Accepted for processing"},{"ticket_id":"T-002","job_id":"...","message":"Accepted for processing"}]}`.

**After the worker runs (a few seconds), get the classified ticket:**

```bash
curl http://localhost:8000/tickets/next
```

Response includes `category`, `is_urgent`, `priority_score`, and **`urgency_score`** (S ∈ [0, 1]).

---

## Verifying Milestone 2

### Option 1: Interactive API docs

1. Start Redis, then API (Terminal 1) and worker (Terminal 2).
2. Open **http://localhost:8000/docs**.
3. **GET /health** → `{"status":"ok"}`.
4. **POST /tickets** with body above → **202** with `ticket_id`, `job_id`.
5. Wait a few seconds, then **GET /queue/size** → `{"size":1}` (or more).
6. **GET /tickets/next** → full ticket with `urgency_score`.
7. **POST /urgency-score** with `{"text":"Everything is broken ASAP"}` → high `urgency_score`, `is_urgent`: true.

### Option 2: curl (second terminal)

```bash
# Health
curl http://localhost:8000/health

# Submit (202 immediately)
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","subject":"Login broken ASAP","body":"Cannot login. Need fix ASAP."}'

# After a few seconds: queue size and pop next
curl http://localhost:8000/queue/size
curl http://localhost:8000/tickets/next
```

### Option 3: Unit and API tests

```bash
pytest tests/test_unit.py -v
# With API + worker running:
pytest tests/test_milestone1.py tests/test_async_broker.py -v
```

### Option 4: Frontend

From **frontend** directory: `npm install` then `npm run dev`. Open http://localhost:5173.

- **Submit ticket:** Single-ticket form or **Add another ticket** for batch; submit one or all. Shows “Accepted for processing” with `ticket_id` and `job_id` (202 flow).
- **Queue:** Lists tickets with **Urgency S** and **High (webhook)** badge when S > 0.8.
- **Activity:** Live view of backend events (ticket accepted, processed by worker, popped, queue cleared). Polls **GET /activity** every 2s.

---

## Summary of changes from Milestone 1

| Area        | Milestone 1              | Milestone 2 |
|------------|---------------------------|-------------|
| Urgency    | Regex (e.g. "ASAP")       | Transformer sentiment → S ∈ [0, 1] |
| POST /tickets | 200 + full ticket        | **202 Accepted** + `job_id` |
| Queue      | In-memory (heapq)         | Redis sorted set (atomic ZPOPMAX) |
| Processing | Synchronous in API        | Async: ARQ workers |
| Concurrency| Single-threaded           | 10+ simultaneous requests; atomic ops |
| Integration| —                         | Optional webhook when S > 0.8 |
| Frontend   | Result = full ticket      | Result = job_id; Queue shows S and S>0.8 |

---

## Summary

| Step | Action |
|------|--------|
| 1 | Create venv, activate, `pip install -r requirements.txt` |
| 2 | Start Redis (see [RUN.md](RUN.md)) |
| 3 | Terminal 1: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| 4 | Terminal 2: `python -m app.worker` |
| 5 | Verify via /docs, curl, pytest, or frontend |

If the above work, Milestone 2 is complete. For Milestone 1 (MVR) spec, see [MILESTONE1.md](MILESTONE1.md). For full project details, see [README.md](README.md).
