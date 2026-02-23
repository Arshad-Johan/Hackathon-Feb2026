# Smart-Support Ticket Routing Engine

A high-throughput, intelligent routing engine that categorizes support tickets, detects urgency, and stores them in a priority queue. It includes a REST API (FastAPI) and an enterprise-ready web frontend.

---

## Team

**Team name:** InferX

| Name              | Roll Number |
|-------------------|-------------|
| Arshad Johan P    | 22PT04      |
| Jeeva Vilasini    | 22PT13      |
| Roobika T         | 22PT26      |
| SriDharsan V      | 22PT33      |

---

## Problem Statement

**Problem Statement 2:** Hackathon Challenge — **"Smart-Support" Ticket Routing Engine**

**Brief description:** Build an intelligent ticket routing system that automatically categorizes incoming support tickets (e.g. Billing, Technical, Legal), detects urgency using sentiment/ML, and routes them into a priority queue. The system should support single and batch submission, real-time activity tracking, and optional integration with agents and master incidents for high-volume or duplicate-ticket scenarios.

---

## Tech Stack

| Layer    | Technologies |
|----------|--------------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, Pydantic, Redis, ARQ (async task queue), Transformers (DistilBERT), Sentence-Transformers, NumPy, SciPy |
| **Frontend** | React 19, TypeScript, Vite 7, Tailwind CSS 4, React Router 7, TanStack Query 5 |
| **UI**       | shadcn-style components (Button, Input, Card, Badge, etc.), class-variance-authority, Tailwind Merge |
| **Infra**    | Redis (queue + pub/sub + state) |

---

## Steps to Run the Project Locally

### Prerequisites

- **Python 3.11 or 3.12** (recommended; 3.13 may need Cargo/Rust on PATH for some deps)
- **Node.js** (for frontend)
- **Redis** (or Memurai on Windows) running locally or a cloud Redis URL

### 1. Clone and set up backend

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

### 2. Start Redis

- **Windows:** Install [Memurai](https://www.memurai.com/get-memurai) or [Redis](https://github.com/microsoftarchive/redis/releases), then start the service or run `redis-server` / `memurai`.
- **Mac/Linux:** Run `redis-server`.
- **Cloud:** Use a Redis URL (e.g. Upstash) and set `REDIS_URL` before starting the app.

Redis must be listening on `localhost:6379` (or set `REDIS_URL`).

### 3. Start the API (Terminal 1)

In the project root with the venv activated:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Wait until you see `Application startup complete.`

### 4. Start the worker (Terminal 2)

Same folder, same venv:

```bash
python -m app.worker
```

Leave this running so tickets are classified and enqueued.

**If Redis is not on localhost:**

```bash
# Windows PowerShell
$env:REDIS_URL = "redis://localhost:6379/0"
python -m app.worker
```

### 5. Run the frontend (Terminal 3)

From the project root:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser. The UI uses the API at `http://localhost:8000` by default. To use a different API URL, create `frontend/.env` with:

```
VITE_API_URL=http://127.0.0.1:8000
```

### Quick reference

| What        | Command / URL |
|------------|----------------|
| Redis      | Start Redis/Memurai (see [RUN.md](RUN.md)) |
| Backend API| `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| Worker     | `python -m app.worker` |
| API docs   | http://localhost:8000/docs |
| Frontend   | `cd frontend` → `npm install` → `npm run dev` |
| Web UI     | http://localhost:5173 |

---

## Live Deployment

**Live deployment link:** [Add your working deployment URL here]

*(Deploy the backend (e.g. Railway, Render) and frontend (e.g. Vercel, Netlify), then replace this line with the live frontend URL and ensure the API URL is set in the frontend environment.)*

---

## Screenshots of Working Application

### 1. Dashboard / Home

![Dashboard](screenshots/dashboard.png)

*Dashboard with API status and backend connection.*

### 2. Submit Ticket

![Submit Ticket](screenshots/submit-ticket.png)

*Submit single or batch tickets; form shows Ticket ID, Subject, Body, and optional Customer ID.*

### 3. Queue & Activity

![Queue and Activity](screenshots/queue-activity.png)

*Queue view with priority-ordered tickets and pop/clear actions; Activity page with live event log.*

**Note:** Add your own screenshots in the `screenshots/` folder as `dashboard.png`, `submit-ticket.png`, and `queue-activity.png` (or update the paths above). Minimum 3 screenshots required.

---

## Features Implemented vs Planned

### Implemented

| Feature | Description |
|--------|-------------|
| **Ticket classification** | Routes tickets into Billing, Technical, or Legal |
| **Urgency detection** | Transformer-based sentiment (DistilBERT); continuous score S ∈ [0, 1]; regex baseline in tests |
| **Priority queue** | Redis-backed processed queue; workers push classified tickets; API pops by urgency |
| **Async processing** | ARQ worker: classification + sentiment; POST returns 202 with `job_id` |
| **Single & batch submit** | `POST /tickets` and `POST /tickets/batch` with 202 and `job_id`(s) |
| **Queue API** | Pop/peek next, queue size, list queue (read-only), clear queue |
| **Activity stream** | In-memory log + Redis pub/sub; `GET /activity` with events: accepted, processed, popped, queue cleared |
| **Web UI** | React app: Submit ticket (single/batch), Queue (size, list, pop, clear), Activity (live polling) |
| **Test urgency** | UI and `POST /urgency-score` to test the urgency model |
| **Health check** | `GET /health` (includes circuit breaker state in M3) |
| **Semantic deduplication (M3)** | Sentence embeddings, sliding window, master incidents when >10 similar in 5 min |
| **Circuit breaker (M3)** | Transformer calls via model router; fallback to regex baseline on latency/timeout |
| **Skill-based routing (M3)** | Agent registry, skill vectors, capacity; ticket–agent assignment by best match |
| **Incidents & agents API** | `GET /incidents`, `GET /agents`, `POST /agents`, `GET /assignments` |
| **RBAC-ready** | Auth context and `RequireAuth` wrapper in place for future roles |

### Planned / Incomplete

| Feature | Status |
|--------|--------|
| **Login & authentication** | Not implemented; RBAC structure only |
| **Role-based access control** | Prepared in frontend; no roles or permissions yet |
| **Optional webhook** | `WEBHOOK_URL` (Slack/Discord) for high-urgency and master incidents is supported in backend; needs configuration for live use |

---

## Implementation Overview (Backend & Frontend)

### Backend

- **Classifier:** Billing / Technical / Legal; urgency from transformer-based sentiment (S ∈ [0, 1]); regex baseline in tests.
- **Queue:** Redis-backed processed queue; workers push classified tickets; API pops by urgency. ARQ worker does classification + sentiment.
- **API:** FastAPI with CORS. `POST /tickets` and `POST /tickets/batch` return 202 with `job_id`; worker enqueues when done. Endpoints: submit (single/batch), pop/peek next, queue size, list queue, clear queue, `GET /activity`, health.
- **Activity:** In-memory activity log plus Redis pub/sub; worker publishes `ticket_processed` for a unified event stream.
- **Data:** Redis for job queue and processed list; no DB/file persistence for ticket content.

### Frontend

- **Stack:** React 19, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query. shadcn-style components.
- **Pages:** Submit ticket (single/batch), Queue (size, list, pop, clear, auto-refresh), Activity (live event log, poll every 2s).
- **API client:** Typed client with configurable base URL and optional auth token getter for future auth.

---

## API Summary

| Method   | Endpoint         | Description |
|----------|------------------|-------------|
| `POST`   | `/tickets`       | Submit ticket. Returns 202 with `ticket_id`, `job_id`. |
| `POST`   | `/tickets/batch` | Submit multiple tickets. Returns 202 with `accepted: [{ ticket_id, job_id }, ...]`. |
| `GET`    | `/tickets/next`  | Pop next highest-urgency ticket. |
| `GET`    | `/tickets/peek`  | Peek next without removing. |
| `GET`    | `/queue/size`    | Processed queue length. |
| `GET`    | `/queue`         | List all waiting tickets in priority order (read-only). |
| `DELETE` | `/queue`         | Clear processed queue. |
| `GET`    | `/activity`      | Recent backend activity (`?limit=100`). |
| `GET`    | `/health`        | Health check. |
| `POST`   | `/urgency-score` | Test urgency model. |
| `GET`    | `/incidents`     | List master incidents (M3). |
| `GET`    | `/incidents/{id}`| Get one master incident (M3). |
| `GET`    | `/metrics`       | Circuit breaker, incident count, online agents (M3). |
| `POST`   | `/agents`        | Register/update agent (M3). |
| `GET`    | `/agents`        | List agents (M3). |
| `GET`    | `/assignments`   | Ticket → agent assignments (M3). |

---

## Testing

**Unit tests (no server):**

```bash
pytest tests/test_unit.py -v
```

**API tests (server must be running):**

```bash
# Terminal 1: uvicorn app.main:app --host 127.0.0.1 --port 8000
# Terminal 2:
pytest tests/test_milestone1.py -v
```

Or use `python scripts/run_tests_live.py` to start the server, run tests, then stop it.

---

## Project Layout

- `app/` — FastAPI app: `main.py`, `models.py`, `classifier.py`, `queue_store.py`, `broker.py`, `config.py`, `sentiment.py`, `worker.py`, `activity.py`, `webhook.py`
- `frontend/` — React SPA (Vite, TypeScript, Tailwind)
- `tests/` — Unit and API tests
- `scripts/` — Helpers (e.g. run tests against live server)
- `RUN.md` — Detailed run instructions (Redis, API, worker)
- `MILESTONE1.md`, `MILESTONE2.md`, `MILESTONE3.md` — Specs and verification
