# How to run the Ticket Routing Engine

## 1. Install Python dependencies

In the project folder, with your virtual environment activated (e.g. `.venv`):

```powershell
pip install -r requirements.txt
```

If that fails (e.g. on Python 3.13), install at least these so the app and worker run:

```powershell
pip install "uvicorn[standard]" fastapi pydantic redis arq
```

Then install transformers/torch if you use the urgency model:

```powershell
pip install transformers torch
```

**Important:** Use the **same** venv for both the API and the worker. Run uvicorn with that venv’s Python so it sees `arq`:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 2. Start a Redis server

The app needs a **Redis server** running (the `redis` pip package is only a client).

**Option A – You have Redis/Memurai installed on Windows**

- Start the Redis (or Memurai) service, or run `redis-server` (or `memurai`) in a terminal.
- It should listen on `localhost:6379`. No extra config needed.

**Option B – You don’t have Redis**

- Install **Memurai** (Redis-compatible for Windows): https://www.memurai.com/get-memurai  
  or **Redis** from: https://github.com/microsoftarchive/redis/releases  
- Then start it (service or `redis-server` / `memurai`).

**Option C – Use a cloud Redis (no local install)**

- Create a free Redis instance (e.g. Upstash, Redis Cloud).
- Set the URL before starting the app (see step 4).

---

## 3. Start the API (Terminal 1)

In the project folder, with the same venv activated:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
(Using `python -m uvicorn` ensures the same venv is used by the reloader.)

Wait until you see something like: `Application startup complete.`

If you see **“Connection refused”** or **“Error connecting to Redis”**, Redis is not running or not reachable — fix step 2 first.

---

## 4. Start the worker (Terminal 2)

Open a **second** terminal. Go to the project folder, activate the same venv, then run:

```powershell
python -m app.worker
```

Leave this running. It will process tickets in the background.

**If Redis is not on localhost or uses a different URL**, set it in this terminal before starting the worker:

```powershell
$env:REDIS_URL = "redis://localhost:6379/0"
python -m app.worker
```

(Use your real Redis URL if you use a cloud Redis.)

**Optional (Milestone 3):** Deduplication and circuit breaker thresholds:

```powershell
$env:DEDUP_SIM_THRESHOLD = "0.9"
$env:DEDUP_MIN_COUNT = "10"
$env:DEDUP_WINDOW_SECONDS = "300"
$env:TRANSFORMER_LATENCY_MS = "500"
$env:CIRCUIT_COOLDOWN_SECONDS = "60"
$env:ROUTING_LOAD_PENALTY_FACTOR = "0.1"
```

---

## 5. Test the API

**Health check:**

```powershell
curl http://127.0.0.1:8000/health
```

Expected: `{"status":"ok", ...}` (Milestone 3 may include `circuit_breaker` in the response).

**Submit a ticket (returns 202 immediately):**

```powershell
curl -X POST http://127.0.0.1:8000/tickets -H "Content-Type: application/json" -d "{\"ticket_id\":\"T-1\",\"subject\":\"Login broken ASAP\",\"body\":\"Need fix ASAP.\"}"
```

Expected: HTTP **202** and JSON with `ticket_id`, `job_id`, and `message: "Accepted for processing"`.

**After a few seconds, get the processed ticket:**

```powershell
curl http://127.0.0.1:8000/tickets/next
```

Expected: JSON with the ticket, including `urgency_score`, `category`, `is_urgent`, etc.

**API docs in the browser:**  
http://127.0.0.1:8000/docs

---

## 6. Run and test the frontend

The frontend talks to the API at **http://localhost:8000** by default. Ensure the API and worker are running (steps 2–4) first.

**Install dependencies (once):**

```powershell
cd frontend
npm install
```

**Start the frontend dev server (Terminal 3):**

```powershell
cd frontend
npm run dev
```

Then open **http://localhost:5173** in your browser.

**If your API runs on a different host/port**, create a `.env` file in the `frontend` folder:

```
VITE_API_URL=http://127.0.0.1:8000
```

(Use your actual API URL; no trailing slash.) Restart `npm run dev` after changing `.env`.

### How to check that the frontend works correctly

| Check | What to do | Expected |
|-------|------------|----------|
| **Backend connected** | Open **Dashboard** (home). Look at "API status" and the green "Connected" card at the bottom. | API status: **ok**; card says "Backend is reachable at ...". If you see "…" or errors, the API is not running or CORS/URL is wrong. |
| **Submit ticket** | Go to **Submit**. Fill Ticket ID, Subject, Body. Click "Submit ticket". | Green toast "Ticket … accepted"; "Accepted for processing" card appears. |
| **Queue** | Go to **Queue**. After submitting a ticket, wait a few seconds and refresh or wait for auto-refresh. | Queue size increases; ticket appears in the table with category and urgency. "Pop next" works. |
| **Activity** | Go to **Activity**. | Event log shows "Accepted", "Processed", "Popped", "Queue cleared" with timestamps. |
| **Test urgency** | On **Submit** page, scroll to "Test urgency score". Type some text, click "Score". | Score (S = …) and "Urgent" / "Not urgent" badge appear (calls `/urgency-score`). |
| **Incidents** | Go to **Incidents**. | List of master incidents (or "No incidents found" if none yet). Filter by Open/Resolved works. |
| **Agents** | Go to **Agents**. | List of agents (or "No agents found"). "Register agent" form works; new agent appears after submit. |

**Quick smoke test:** Dashboard → Submit a ticket → wait ~5 s → Queue shows the ticket → Activity shows events. If all of that works, the frontend is correctly connected to the backend.

---

## Summary

| Step | What to run | Where |
|------|-------------|--------|
| 1 | `pip install -r requirements.txt` | Project folder, venv active |
| 2 | Start Redis (or Memurai / cloud) | — |
| 3 | `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` | Terminal 1 |
| 4 | `python -m app.worker` | Terminal 2 (same folder, same venv) |
| 5 | Use curl or /docs to test API | — |
| 6 | `cd frontend` then `npm install` and `npm run dev`; open http://localhost:5173 | Terminal 3 |

Both the API (Terminal 1) and the worker (Terminal 2) must be running for tickets to be processed. The frontend (Terminal 3) needs the API to be up to show "Connected" and to submit tickets, view queue, etc.
