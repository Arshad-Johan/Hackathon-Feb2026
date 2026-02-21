# Ticket Routing Engine

A high-throughput, intelligent routing engine that categorizes support tickets, detects urgency, and stores them in a priority queue. It includes a REST API (FastAPI) and an enterprise-ready web frontend.

---

## Implementation overview

### Backend (Milestone 1 — MVR)

- **Classifier:** Routes tickets into **Billing**, **Technical**, or **Legal**. Regex-based urgency detection (e.g. "broken", "ASAP") sets priority.
- **Queue:** In-memory priority queue (heapq); higher priority served first.
- **API:** FastAPI with CORS for the frontend. Endpoints: submit ticket, pop/peek next, queue size, list queue (read-only snapshot), clear queue, health.
- **Data:** Stored in memory only; no database or file persistence.

### Frontend

- **Stack:** React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query. UI built with shadcn-style components (Button, Input, Card, Badge, etc.).
- **Pages:**
  - **Submit ticket** — Form (Ticket ID, Subject, Body, optional Customer ID); validation; on success shows category, urgency, and priority score.
  - **Queue** — Queue size, full list of waiting tickets in priority order, **Pop next** and **Clear queue** actions; auto-refresh.
- **RBAC-ready:** Auth context and `RequireAuth` wrapper are in place for future admin/user roles and role-based access; no login yet.
- **API client:** Typed client with configurable base URL and optional auth token getter for when auth is added.

---

## Running the project

Use two terminals: one for the backend, one for the frontend.

### 1. Backend (API)

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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave this terminal open. You should see: `Uvicorn running on http://127.0.0.1:8000`.

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
| Backend           | `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| API docs          | http://localhost:8000/docs |
| Frontend          | `cd frontend` → `npm install` → `npm run dev` |
| Web UI            | http://localhost:5173 |

---

## API

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

- `app/` — FastAPI app: `main.py`, `models.py`, `classifier.py`, `queue_store.py`
- `frontend/` — React SPA (Vite, TypeScript, Tailwind)
- `tests/` — Unit and API tests
- `scripts/` — Helpers (e.g. run tests against live server)
