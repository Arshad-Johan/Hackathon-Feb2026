# How to Run and Check Milestone 1 (MVR)

Copy-paste these commands. Use **Terminal** (Mac/Linux) or **Command Prompt / PowerShell** (Windows).

---

## 1. Go to the project and create a virtual environment

```bash
cd hackathon26
python -m venv .venv
```

**Activate the virtual environment:**

- **Mac/Linux:**
  ```bash
  source .venv/bin/activate
  ```
- **Windows (Command Prompt):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```

You should see `(.venv)` at the start of your prompt.

---

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Run the API server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave this terminal open. You should see something like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 4. Check Milestone 1 (choose one way)

### Option A: Quick check in the browser

1. Open: **http://localhost:8000/docs**
2. Try **GET /health** → should return `{"status":"ok"}`
3. Try **POST /tickets** with this body:
   ```json
   {
     "ticket_id": "T-001",
     "subject": "Login broken ASAP",
     "body": "Cannot login. Need fix ASAP."
   }
   ```
   You should get a response with `"category": "Technical"`, `"is_urgent": true`, `"priority_score": 1`.
4. Try **GET /queue/size** → should show `{"size":1}`.
5. Try **GET /tickets/next** → should return the ticket you just submitted.

---

### Option B: Quick check with curl (new terminal)

Open a **second** terminal, go to the project, activate the venv, then run:

**Health check:**
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok"}`

**Submit an urgent technical ticket:**
```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","subject":"Login broken ASAP","body":"Cannot login. Need fix ASAP."}'
```
Expected: JSON with `"category":"Technical"`, `"is_urgent":true`, `"priority_score":1`

**Submit a billing ticket (not urgent):**
```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-002","subject":"Wrong invoice","body":"I was charged twice."}'
```
Expected: JSON with `"category":"Billing"`, `"is_urgent":false`, `"priority_score":0`

**Queue size:**
```bash
curl http://localhost:8000/queue/size
```
Expected: `{"size":2}`

**Get next ticket (urgent one first):**
```bash
curl http://localhost:8000/tickets/next
```
Expected: T-001 (the urgent one). Run again to get T-002.

---

### Option C: Run automated tests (new terminal)

Open a **second** terminal:

```bash
cd hackathon26
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/test_unit.py tests/test_milestone1.py -v
```

For this to work, the **server must be running** in the first terminal (step 3).  
Expected: all tests **PASSED**.

---

## 5. Stop the server

In the terminal where the server is running, press **Ctrl+C**.

---

## Summary

| Step | Command |
|------|--------|
| 1 | `cd hackathon26` → `python -m venv .venv` → activate venv |
| 2 | `pip install -r requirements.txt` |
| 3 | `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| 4 | Open http://localhost:8000/docs or run curl commands or run pytest |
| 5 | Ctrl+C to stop server |

If all of the above work, Milestone 1 is running correctly.
