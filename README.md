# Hackathon-Feb2026

# Ticket Routing Engine — Minimum Viable Router (MVR)

A high-throughput, intelligent routing engine that categorizes support tickets, detects urgency, and stores them in an in-memory priority queue.

## Milestone 1: MVR

- **ML**: Baseline classifier routes tickets into **Billing**, **Technical**, or **Legal**. Regex-based urgency (e.g. "broken", "ASAP").
- **System**: REST API (FastAPI) accepts JSON; tickets stored in an in-memory priority queue (heapq).
- **Concurrency**: Single-threaded for this phase.

## Setup

```bash
cd hackathon26
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run (async broker: Redis + worker)

**1. Start Redis** (required):

```bash
docker run -d -p 6379:6379 --name redis redis
```

**2. Start API** (terminal 1):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**3. Start worker** (terminal 2):

```bash
python -m app.worker
```

Or: `arq app.worker.WorkerSettings`

API docs: **http://localhost:8000/docs**

Set `REDIS_URL` if Redis is not on localhost (e.g. `REDIS_URL=redis://localhost:6379/0`).

## API (async broker)

| Method   | Endpoint        | Description |
|----------|-----------------|-------------|
| `POST`   | `/tickets`      | **202 Accepted** with `ticket_id`, `job_id`. Worker processes in background. |
| `GET`    | `/tickets/next` | Pop next highest-urgency (by S) ticket. 404 if empty. |
| `GET`    | `/tickets/peek` | Peek next without removing. |
| `GET`    | `/queue/size`  | Number of **processed** tickets ready to dequeue. |
| `DELETE` | `/queue`       | Clear processed queue. |
| `GET`    | `/health`       | Health check. |
| `POST`   | `/urgency-score`| Test transformer only (body: `{"text":"..."}`). |

### Example

```bash
# Submit — returns 202 immediately with job_id
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","subject":"Login broken ASAP","body":"Cannot login. Need fix ASAP."}'

# After a few seconds (worker processes), get next ticket
curl http://localhost:8000/tickets/next
```

## Testing Milestone 1

### Option 1: Unit tests (no server)

From the project root with your venv activated:

```bash
pip install -r requirements.txt
pytest tests/test_unit.py -v
```

Runs tests for the classifier and priority queue. All should pass if MVR logic is working.

### Option 2: API tests (server must be running)

Start the server in one terminal (`uvicorn app.main:app --host 127.0.0.1 --port 8000`), then run `pytest tests/test_milestone1.py -v`. Or use `python scripts/run_tests_live.py` to start the server, run tests, then stop it.

### Option 3: Manual test with a live server

1. **Start the server** (one terminal):
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Health check**
   ```bash
   curl http://localhost:8000/health
   ```
   Expect: `{"status":"ok"}`

3. **Submit a ticket** (should be classified Technical + urgent):
   ```bash
   curl -X POST http://localhost:8000/tickets \
     -H "Content-Type: application/json" \
     -d '{"ticket_id":"T-001","subject":"Login broken ASAP","body":"Cannot login. Need fix ASAP."}'
   ```
   Expect: JSON with `"category":"Technical"`, `"is_urgent":true`, `"priority_score":1`

4. **Submit a billing ticket** (non-urgent):
   ```bash
   curl -X POST http://localhost:8000/tickets \
     -H "Content-Type: application/json" \
     -d '{"ticket_id":"T-002","subject":"Wrong invoice","body":"I was charged twice."}'
   ```
   Expect: `"category":"Billing"`, `"is_urgent":false`, `"priority_score":0`

5. **Queue size**
   ```bash
   curl http://localhost:8000/queue/size
   ```
   Expect: `{"size":2}`

6. **Pop next** (urgent first):
   ```bash
   curl http://localhost:8000/tickets/next
   ```
   Expect: T-001 (the urgent one). Then call again to get T-002.

7. **Interactive docs**: open **http://localhost:8000/docs** and try the endpoints from the browser.
# Hackathon-Feb2026
