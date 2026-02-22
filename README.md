# Ticket Routing Engine

A high-throughput, intelligent routing engine that categorizes support tickets, detects urgency, and stores them in a priority queue. It includes a REST API (FastAPI) and an enterprise-ready web frontend.

---

## Implementation overview

### Backend

- **Classifier:** Routes tickets into **Billing**, **Technical**, or **Legal**. Urgency from transformer-based sentiment (continuous score S ∈ [0, 1]); regex baseline in tests.
- **Queue:** Redis-backed processed queue (workers push classified tickets; API pops by urgency). Background worker (ARQ) does classification + sentiment.
- **API:** FastAPI with CORS. **POST /tickets** returns **202 Accepted** with `job_id`; worker enqueues when done. **POST /tickets/batch** accepts multiple tickets and returns 202 with one `job_id` per ticket. Endpoints: submit (single/batch), pop/peek next, queue size, list queue (read-only), clear queue, **GET /activity** (recent backend events), health.
- **Activity:** In-memory activity log plus Redis pub/sub; worker publishes **ticket_processed** so the API can expose a unified event stream (accepted, processed, popped, queue cleared).
- **Data:** Redis for job queue and processed list; no DB/file persistence for ticket content.

### Frontend

- **Stack:** React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query. UI built with shadcn-style components (Button, Input, Card, Badge, etc.).
- **Pages:**
  - **Submit ticket** — Single or multiple tickets (add/remove rows); submit one or batch. Form: Ticket ID, Subject, Body, optional Customer ID; on success shows accepted ticket(s) with `job_id`.
  - **Queue** — Queue size, full list of waiting tickets in priority order, **Pop next** and **Clear queue** actions; auto-refresh.
  - **Activity** — Live backend event log (ticket accepted, processed by worker, popped, queue cleared); polls every 2s.
- **RBAC-ready:** Auth context and `RequireAuth` wrapper are in place for future admin/user roles and role-based access; no login yet.
- **API client:** Typed client with configurable base URL and optional auth token getter for when auth is added.

---

## Running the project

Use **three** steps: Redis, then backend API, then (optional) frontend. For full step-by-step instructions see **[RUN.md](RUN.md)**.

### 1. Backend (API + worker)

From the **project root**:

```bash
# Create and activate a virtual environment (first time only)
python -m venv .venv
```

**Activate the venv:**

- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **Windows (Command Prompt):** `.venv\Scripts\activate.bat`
- **Mac/Linux:** `source .venv/bin/activate`

```bash
pip install -r requirements.txt
```

**Start Redis** (required). Then in **Terminal 1**:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In **Terminal 2** (same venv):

```bash
python -m app.worker
```

Leave both running. Tickets are accepted with 202 and processed by the worker into the queue.

**Troubleshooting — "Cargo is not installed or is not on PATH" (pydantic-core):**  
This can happen with Python 3.13 or when the build subprocess does not see Rust/Cargo.

- **Option A:** Add Cargo to your user PATH (e.g. `C:\Users\<You>\.cargo\bin` on Windows). Then reopen the terminal and run `pip install -r requirements.txt` again.
- **Option B:** Use Python 3.11 or 3.12: `py -3.12 -m venv .venv` (or `python3.11`), then activate and `pip install -r requirements.txt`.

### 2. Frontend (web UI)

In a **second terminal**, from the project root:

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser. The UI talks to the API at `http://localhost:8000` (override with `VITE_API_URL` if needed).

### Quick reference

| What              | Command / URL |
|-------------------|---------------|
| Redis             | Start Redis/Memurai (see [RUN.md](RUN.md)) |
| Backend           | `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| Worker            | `python -m app.worker` |
| API docs          | http://localhost:8000/docs |
| Frontend          | `cd frontend` → `npm install` → `npm run dev` |
| Web UI            | http://localhost:5173 |
| Activity (UI)     | http://localhost:5173/activity |

Set `REDIS_URL` if Redis is not on localhost (e.g. `REDIS_URL=redis://localhost:6379/0`). Optional: set `WEBHOOK_URL` (Slack or Discord webhook) to notify when urgency score S > 0.8. **Milestone 3** adds optional env vars: `DEDUP_SIM_THRESHOLD`, `DEDUP_MIN_COUNT`, `DEDUP_WINDOW_SECONDS`, `TRANSFORMER_LATENCY_MS`, `CIRCUIT_COOLDOWN_SECONDS`, `ROUTING_LOAD_PENALTY_FACTOR` — see [MILESTONE3.md](MILESTONE3.md).

---

### API

| Method   | Endpoint        | Description |
|----------|-----------------|-------------|
| `POST`   | `/tickets`      | Submit ticket (JSON). Returns **202 Accepted** with `ticket_id`, `job_id`; worker enqueues when done. |
| `POST`   | `/tickets/batch`| Submit multiple tickets (JSON array). Returns **202** with `accepted: [{ ticket_id, job_id }, ...]`. |
| `GET`    | `/tickets/next` | Pop next highest-urgency ticket from processed queue. |
| `GET`    | `/tickets/peek` | Peek next without removing. |
| `GET`    | `/queue/size`   | Processed queue length. |
| `GET`    | `/queue`        | List all waiting tickets in priority order (read-only). |
| `DELETE` | `/queue`        | Clear processed queue. |
| `GET`    | `/activity`     | Recent backend activity (`?limit=100`). Events: ticket_accepted, ticket_processed, ticket_popped, queue_cleared. |
| `GET`    | `/health`       | Health check (includes circuit_breaker in M3). |
| `POST`   | `/urgency-score`| Test urgency model (transformer or baseline via circuit breaker). |
| `GET`    | `/incidents`    | List master incidents (M3). |
| `GET`    | `/incidents/{id}` | Get one master incident (M3). |
| `GET`    | `/metrics`      | Circuit breaker, incident count, online agents (M3). |
| `POST`   | `/agents`       | Register/update agent (M3). |
| `GET`    | `/agents`       | List agents (M3). |
| `GET`    | `/assignments`  | Ticket → agent assignments (M3). |

**Example — submit a ticket:**

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","subject":"Login broken ASAP","body":"Cannot login. Need fix ASAP."}'
# → 202 with job_id. After the worker runs, GET /tickets/next returns the classified ticket (category, urgency_score, etc.).
```

---

## Testing

**Unit tests (no server):**

```bash
pytest tests/test_unit.py -v
```

**API tests (server must be running):**

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
# In another terminal:
pytest tests/test_milestone1.py -v
```

Or use `python scripts/run_tests_live.py` to start the server, run tests, then stop it.

---

## Project layout

- `app/` — FastAPI app: `main.py`, `models.py`, `classifier.py`, `queue_store.py`, `broker.py`, `config.py`, `sentiment.py`, `worker.py`, `activity.py`, `webhook.py`
- `frontend/` — React SPA (Vite, TypeScript, Tailwind)
- `tests/` — Unit and API tests
- `scripts/` — Helpers (e.g. run tests against live server)
- `RUN.md` — Detailed run instructions (Redis, API, worker)
- `MILESTONE1.md` — MVR (in-memory) spec and verification.
- `MILESTONE2.md` — Intelligent Queue (async broker, transformer urgency, webhook).
- `MILESTONE3.md` — Autonomous Orchestrator (semantic dedup, circuit breaker, skill-based routing).
