# Milestone 3: The Autonomous Orchestrator

This document describes **Milestone 3**: self-healing, agent-aware system with semantic deduplication (flash-flood suppression), circuit breakers, and skill-based routing.

---

## What Milestone 3 delivers

### 4.1 ML: Semantic Deduplication

- **Sentence embeddings:** Lightweight model (`sentence-transformers/all-MiniLM-L6-v2`) embeds ticket text (subject + body). Cosine similarity between incoming tickets is computed as \( \cos(\theta) = \frac{A \cdot B}{\|A\| \|B\|} \).
- **Sliding window:** Last **5 minutes** of tickets are kept in Redis with their embeddings. When a new ticket is processed, its embedding is compared to all in the window.
- **Master Incident rule:** If **more than 10 tickets** in the window have similarity **> 0.9** with the current ticket, the system:
  - Creates a single **Master Incident** (or links to an existing one for the same cluster).
  - **Suppresses individual alerts:** no separate high-urgency webhooks for each ticket; one webhook is sent for the master incident.
  - Activity stream events: `master_incident_created`, `ticket_linked_to_master_incident`.

### 4.2 System: Circuit Breakers & Load Balancing

- **Circuit Breaker:** All transformer (DistilBERT) calls go through a **model router**. Latency is measured per call. If a single call exceeds **500 ms** (configurable via `TRANSFORMER_LATENCY_MS`), the circuit **opens** and the system **fails over** to the **Milestone 1 baseline** (regex-based urgency). After a **cooldown** (default 60 s), the circuit moves to **half-open** and a few probe calls are allowed; if they succeed within the latency limit, the circuit **closes** again. State is stored in Redis so API and workers share the same view.
- **Skill-Based Routing:** An **agent registry** holds agents with **skill vectors** (e.g. tech=0.9, billing=0.1, legal=0.0) and **capacity** (`max_concurrent_tickets`, `current_load`). For each classified ticket, a **constraint optimization** selects the best **online** agent with **available capacity** by maximizing cosine similarity between ticket skill vector (derived from category) and agent skill vector, minus a load penalty. Assignments are stored in Redis; activity event `ticket_assigned_to_agent` is emitted.

---

## Setup

Same as Milestone 2: venv, `pip install -r requirements.txt`, **Redis** running. Optional: `WEBHOOK_URL` for high-urgency and master-incident notifications.

**New dependencies:** `sentence-transformers`, `numpy` (in `requirements.txt`).

**Optional environment variables (Milestone 3):**

| Variable | Default | Description |
|----------|---------|-------------|
| `DEDUP_SIM_THRESHOLD` | 0.9 | Cosine similarity threshold for “same” ticket cluster. |
| `DEDUP_MIN_COUNT` | 10 | Min number of similar tickets in 5 min to create a master incident. |
| `DEDUP_WINDOW_SECONDS` | 300 | Sliding window length (5 minutes). |
| `TRANSFORMER_LATENCY_MS` | 500 | Max transformer latency before circuit opens. |
| `CIRCUIT_COOLDOWN_SECONDS` | 60 | Cooldown before half-open probes. |
| `CIRCUIT_HALF_OPEN_PROBES` | 3 | Number of probe calls in half-open. |
| `ROUTING_LOAD_PENALTY_FACTOR` | 0.1 | Penalty factor for agent load in routing score. |

---

## Run (backend: API + worker)

Same as Milestone 2:

**Terminal 1 — API:**

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Worker:**

```bash
python -m app.worker
```

Leave both running. Tickets are accepted with 202, then the worker: classifies (with circuit-breaker-protected urgency), embeds, runs dedup (master incident if >10 similar in 5 min), adds to queue, routes to best agent, and emits activity events.

---

## API (Milestone 3 additions)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/incidents` | List master incidents. Query: `?limit=50`, `?status=open` or `resolved`. |
| `GET` | `/incidents/{incident_id}` | Get one master incident by id. |
| `GET` | `/health` | Health check; response includes `circuit_breaker` (state, opened_at, half_open_probes). |
| `GET` | `/metrics` | Milestone 3 metrics: circuit_breaker, master_incidents_count, online_agents_count. |
| `POST` | `/agents` | Register or update an agent (body: Agent with skill_vector, max_concurrent_tickets, etc.). |
| `GET` | `/agents` | List all agents. Query: `?online_only=true` for online with capacity only. |
| `GET` | `/agents/{agent_id}` | Get agent by id. |
| `GET` | `/assignments` | List ticket → agent assignments. Query: `?limit=100`. |
| `GET` | `/agents/{agent_id}/tickets` | List ticket_ids assigned to this agent. |

**Activity events (GET /activity):** In addition to existing events, you may see:

- `master_incident_created` — A new master incident was created (flash-flood).
- `ticket_linked_to_master_incident` — A ticket was linked to an existing master incident.
- `ticket_assigned_to_agent` — A ticket was assigned to an agent by the router.

---

## Verifying Milestone 3

### 1. Health and circuit breaker

```bash
curl http://localhost:8000/health
```

Expect `{"status":"ok","circuit_breaker":{"state":"closed",...}}` (or `open` / `half_open` after a latency spike).

### 2. Urgency (transformer or baseline)

```bash
curl -X POST http://localhost:8000/urgency-score -H "Content-Type: application/json" -d "{\"text\":\"Everything is broken ASAP\"}"
```

Returns `urgency_score` and `is_urgent`. If the transformer is slow or the circuit is open, the baseline (regex) is used automatically.

### 3. Agents and routing

Register an agent, then submit a ticket; after the worker runs, check assignments:

```bash
curl -X POST http://localhost:8000/agents -H "Content-Type: application/json" -d "{\"agent_id\":\"A1\",\"display_name\":\"Tech Agent\",\"skill_vector\":{\"tech\":0.9,\"billing\":0.1,\"legal\":0.0},\"max_concurrent_tickets\":10}"
curl -X POST http://localhost:8000/tickets -H "Content-Type: application/json" -d "{\"ticket_id\":\"T-1\",\"subject\":\"Login broken\",\"body\":\"Cannot login.\"}"
# Wait a few seconds, then:
curl http://localhost:8000/assignments
```

### 4. Master incidents

To trigger a master incident you need >10 very similar tickets within 5 minutes (e.g. same subject/body). Use batch or a script to submit many identical/similar tickets; then:

```bash
curl http://localhost:8000/incidents
```

### 5. Unit tests

```bash
pytest tests/test_milestone3.py -v
```

Covers cosine similarity, ticket skill vectors, baseline urgency, routing (with agents), dedup service (get/list incidents).

---

## Data and consistency notes

- **Activity stream** (`GET /activity`): Events are held in memory in the API process only. They are not persisted to Redis. After an API restart the activity log is empty; only events that occur after the restart are shown.
- **Agent load**: When a ticket is **popped** via `GET /tickets/next`, that ticket’s assignment is cleared and the agent’s `current_load` is decremented so capacity stays accurate across restarts.
- **Master incidents**: Spec requires “more than 10” similar tickets (i.e. 11+) in the 5-minute window before creating a master incident.

---

## Summary

| Area | Milestone 2 | Milestone 3 |
|------|-------------|-------------|
| Urgency | Transformer only | **Circuit breaker:** transformer or baseline (regex) on latency > 500 ms |
| Alerts | One webhook per high-urgency ticket | **Semantic dedup:** >10 similar in 5 min → one Master Incident, suppressed individual alerts |
| Routing | Queue by urgency only | **Skill-based:** agent registry, skill vectors, capacity; ticket assigned to best agent |
| Observability | Activity, health | **Metrics:** circuit state, incident count, online agents; activity includes master_incident_created, ticket_assigned_to_agent |

If the above work, Milestone 3 is complete. For Milestone 1 and 2 specs, see [MILESTONE1.md](MILESTONE1.md) and [MILESTONE2.md](MILESTONE2.md). For full project details, see [README.md](README.md).
