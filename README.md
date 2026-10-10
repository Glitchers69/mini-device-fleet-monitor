# Mini Device Fleet Monitor

A lightweight, robust backend application and real-time dashboard for monitoring a fleet of simulated IoT devices emitting periodic heartbeats.

---

## Table of Contents

1. [What the Project Does](#1-what-the-project-does)
2. [Design & Architecture](#2-design--architecture)
3. [Prerequisites](#3-prerequisites)
4. [How to Build](#4-how-to-build)
5. [How to Run the Application](#5-how-to-run-the-application)
6. [How to Run the Simulator](#6-how-to-run-the-simulator)
7. [How to Run the Tests](#7-how-to-run-the-tests)
8. [Example API Requests & Responses](#8-example-api-requests--responses)
9. [Assumptions](#9-assumptions)
10. [Known Limitations](#10-known-limitations)
11. [What I Would Improve with One Additional Day](#11-what-i-would-improve-with-one-additional-day)
12. [AI Usage](#12-ai-usage)

---

## 1. What the Project Does

The **Mini Device Fleet Monitor** is a REST API and operator dashboard designed to track whether a fleet of IoT edge devices is alive and functioning.

- **Registration & Ingestion**: Devices register their unique string ID and name with the backend. Devices periodically push heartbeat signals over HTTP.
- **Dynamic Liveness Tracking**: Instead of running background worker polling or storing mutable status fields in the database, the backend dynamically calculates whether each device is `ONLINE` or `OFFLINE` on every read:
  - **`ONLINE`**: A device that received a heartbeat within the last **30 seconds** relative to server time.
  - **`OFFLINE`**: A device that has never sent a heartbeat, or whose most recent heartbeat is older than 30 seconds.
- **Fleet Summary**: An aggregate endpoint reporting `total`, `online`, and `offline` counts (`total == online + offline`).
- **Interactive Device Simulator**: A standalone Python CLI tool simulating 5+ concurrent devices that can be started and stopped individually to verify state transitions.
- **Operator Dashboard**: A responsive browser interface at `/dashboard/` with auto-polling every 5 seconds, displaying real-time metrics and color-coded status badges.

---

## 2. Design & Architecture

The system follows a strict **Layered REST** architectural pattern built on Django and Django REST Framework.

```
HTTP Request
    │
    ▼
devices/urls.py          ─── Routing & trailing slash normalization
    │
    ▼
devices/views.py         ─── Thin HTTP dispatchers (status codes, errors)
    │
    ▼
devices/serializers.py   ─── Request validation & dynamic status computation
    │
    ▼
devices/models.py        ─── SQLite persistence (no business logic)
    │
    ▼
SQLite Database
```

### Architectural Invariants

1. **Single Django App Domain (`devices/`)**:
   - All domain logic, models, views, serializers, templates, and constants reside in a single `devices/` app.
   - The root `fleet_monitor/` directory contains strictly project-level configuration (`settings.py`, root `urls.py`, `wsgi.py`).
2. **Dynamic Read-Time Status Evaluation (No Stored Status)**:
   - Status is **never persisted** as a column in SQLite. Storing status risks data going stale and creates dual sources of truth or background worker dependencies.
   - Every read request evaluates `compute_status(last_heartbeat, now=None)` via `django.utils.timezone.now()`.
3. **Server Clock Authority**:
   - To guard against client clock skew, drift, or malicious timestamps, the server assigns `last_heartbeat = timezone.now()` upon receiving a heartbeat.
   - The client-provided `timestamp` is validated and stored as `last_client_timestamp` for auditability, but is never used for status computation.
4. **Single Constant for Timeout**:
   - `ONLINE_THRESHOLD_SECONDS = 30` is declared centrally in `devices/constants.py` and imported everywhere (views, serializers, tests).
5. **Zero-Django Simulator**:
   - `simulator/run.py` is fully decoupled from Django. It relies solely on the Python standard library and `requests` (no `DJANGO_SETTINGS_MODULE` or model imports).
6. **Zero Wall-Clock Sleeps in Tests**:
   - All tests run instantaneously (< 0.05s) by freezing/mocking `django.utils.timezone.now` using `unittest.mock.patch`. Zero calls to `time.sleep()` exist in the test suite.
7. **Safe URL Normalization**:
   - URLs accept both trailing and non-trailing slashes (e.g., `/devices` and `/devices/`, `/summary` and `/summary/`) using `re_path(r'^.../?$', ...)` to avoid 301 redirects on POST requests.

---

## 3. Prerequisites

- **Python**: 3.11 or higher
- **Virtual Environment Tool**: Standard `venv` (bundled with Python) or `uv`
- **Network Tooling**: `curl` or any modern web browser

---

## 4. How to Build

Clone the repository and set up a local virtual environment:

```bash
# Navigate to the project root
cd "Mini device fleet monitor"

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On macOS / Linux:
source .venv/bin/activate
# On Windows (cmd):
# .venv\Scripts\activate.bat
# On Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# Install project dependencies
pip install -r requirements.txt
```

---

## 5. How to Run the Application

Apply migrations and start the Django development server:

```bash
# 1. Apply database migrations
python manage.py migrate

# 2. Run the development server
python manage.py runserver
```

The application will be accessible at:
- **API Base URL**: `http://localhost:8000/`
- **Operator Dashboard**: `http://localhost:8000/dashboard/`

---

## 6. How to Run the Simulator

In a **separate terminal window** (with `.venv` activated), launch the device simulator:

```bash
# Activate virtual environment
source .venv/bin/activate

# Start simulator against the running server
python simulator/run.py
```

### Simulator Behavior & Controls

- On startup, the simulator registers 5 devices (`device-01` through `device-05`) with the API.
- Each device runs in its own background thread, emitting a heartbeat to `POST /devices/{id}/heartbeat` every 5 seconds.
- An interactive prompt allows you to halt individual device heartbeats to verify timeout transitions:

```text
Commands:
  stop <id>   - Stop heartbeat for a device (e.g. 'stop device-03')
  start <id>  - Resume heartbeat for a device (e.g. 'start device-03')
  list        - List managed devices and their thread status
  quit / exit - Stop all devices and exit
```

### Verifying the Transition

1. In the simulator, type: `stop device-03`.
2. Open `http://localhost:8000/dashboard/` or call `curl http://localhost:8000/devices/device-03`.
3. Within 30 seconds of stopping, `device-03` will dynamically flip from **`ONLINE`** to **`OFFLINE`**.
4. To resume, type `start device-03` in the simulator. The next heartbeat immediately restores its status to **`ONLINE`**.

---

## 7. How to Run the Tests

Execute the automated test suite using Django's test runner:

```bash
python manage.py test
```

### Test Suite Structure

The test suite consists of **32 comprehensive tests** organized across 4 dedicated modules:

| Test File | Focus Area | Key Verifications |
|:---|:---|:---|
| `tests/test_registration.py` | Registration (FR-1) | 201 Created, 409 Conflict for duplicate ID, 400 Bad Request for missing/blank fields, persistence checks |
| `tests/test_heartbeat.py` | Heartbeat Reception (FR-2) | 200 OK, 404 for unknown device, 400 for malformed timestamp/status, server-clock authority overriding client clock |
| `tests/test_status.py` | Dynamic Status (FR-3, 4, 5, 6) | `compute_status` utility tests, `GET /devices` list, `GET /devices/{id}` detail, `GET /summary` aggregate math (`total == online + offline`) |
| `tests/test_timeout.py` | Timeout Boundaries (FR-3) | Exact 30.000s inclusion (ONLINE) vs 30.001s exclusion (OFFLINE), dynamic offline transition without DB writes, zero `time.sleep()` |

All 32 tests execute in under **0.05 seconds**.

---

## 8. Example API Requests & Responses

### 1. Register a Device
```bash
curl -X POST http://localhost:8000/devices \
  -H "Content-Type: application/json" \
  -d '{"id": "device-01", "name": "Temperature Sensor Alpha"}'
```
**Response (`201 Created`):**
```json
{
  "id": "device-01",
  "name": "Temperature Sensor Alpha",
  "status": "OFFLINE",
  "last_heartbeat": null
}
```

*Duplicate registration error (`409 Conflict`):*
```json
{
  "error": "Device with ID 'device-01' already exists."
}
```

---

### 2. Send a Heartbeat
```bash
curl -X POST http://localhost:8000/devices/device-01/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-10-10T12:00:00Z",
    "status": "OK",
    "cpu_usage": 14.2,
    "signal_strength": -65
  }'
```
**Response (`200 OK`):**
```json
{
  "message": "Heartbeat received",
  "device_id": "device-01",
  "last_heartbeat": "2026-10-10T12:00:01.123456Z"
}
```

*Unknown device error (`404 Not Found`):*
```json
{
  "error": "Device with ID 'device-unknown' not found."
}
```

---

### 3. List All Devices
```bash
curl -X GET http://localhost:8000/devices
```
**Response (`200 OK`):**
```json
[
  {
    "id": "device-01",
    "name": "Temperature Sensor Alpha",
    "status": "ONLINE",
    "last_heartbeat": "2026-10-10T12:00:01.123456Z"
  },
  {
    "id": "device-02",
    "name": "Pressure Sensor Beta",
    "status": "OFFLINE",
    "last_heartbeat": "2026-10-10T11:58:10.000000Z"
  }
]
```

---

### 4. Get Device Detail
```bash
curl -X GET http://localhost:8000/devices/device-01
```
**Response (`200 OK`):**
```json
{
  "id": "device-01",
  "name": "Temperature Sensor Alpha",
  "status": "ONLINE",
  "last_heartbeat": "2026-10-10T12:00:01.123456Z"
}
```

---

### 5. Get Fleet Summary
```bash
curl -X GET http://localhost:8000/summary
```
**Response (`200 OK`):**
```json
{
  "total": 5,
  "online": 4,
  "offline": 1
}
```

---

### 6. View Operator Dashboard
Open in your browser:
```text
http://localhost:8000/dashboard/
```
Displays high-level KPI cards (Total, Online, Offline), a live auto-polling badge, and a real-time table of devices updated every 5 seconds.

---

## 9. Assumptions

1. **Small Fleet Size**: The system is designed for fleets between 5 and 100 devices for the scope of this monitor. Unpaginated list responses (`GET /devices`) are therefore standard and performant.
2. **Single-Node SQLite Deployment**: A single SQLite database file is sufficient for local development and test evaluation without external database server overhead.
3. **Permanent Registrations**: Devices do not support deregistration or deletion endpoints in v1. Once registered, they remain in the fleet registry.
4. **Binary Health State**: Liveness is binary (`ONLINE` or `OFFLINE`) governed strictly by the 30-second window. Heartbeat payload error states (e.g. `status: "ERROR"`) are recorded for auditability but do not mark a device as offline as long as the heartbeat signal itself is being transmitted.
5. **Client-Side Polling**: The dashboard uses lightweight JavaScript polling (`setInterval` + `fetch`) every 5 seconds rather than WebSockets, satisfying the real-time visibility requirement while keeping the backend infrastructure lean.

---

## 10. Known Limitations

1. **Open Authentication**: The API has no authentication or rate limiting. Any client on the network can register devices or post heartbeats.
2. **Dashboard Transport**: The operator dashboard uses HTTP polling (every 5 seconds) rather than duplex WebSockets or Server-Sent Events (SSE). Updates appear within 5 seconds rather than sub-millisecond.
3. **No Historical Time-Series Log**: The database stores only the latest heartbeat (`last_heartbeat`) per device. Past heartbeat records and time-series telemetry are overwritten rather than appended to a history table.
4. **Simulator Process Model**: The simulator runs multi-threaded within a single Python process on localhost rather than simulating distributed network latencies across separate virtual networks.

---

## 11. What I Would Improve with One Additional Day

If given an additional day to evolve this system toward production readiness, I would prioritize:

1. **WebSockets / SSE via Django Channels**:
   - Replace the 5-second polling dashboard with Server-Sent Events or WebSockets so status transitions update the browser UI instantly the exact millisecond a device times out or checks in.
2. **Time-Series Telemetry & Graphing**:
   - Store incoming `cpu_usage`, `battery_level`, and `signal_strength` telemetry points in a time-series table (or timescale DB).
   - Add interactive Chart.js sparkline visualizations in the dashboard for each device.
3. **Authentication & Token Scopes**:
   - Implement HMAC or API Token authentication for device heartbeats.
   - Implement role-based session authentication for operators accessing the dashboard.
4. **Containerization**:
   - Provide a multi-stage `Dockerfile` and `docker-compose.yml` defining the Django server, simulator, and automated test runner in isolated containers.
5. **Filtering & Pagination**:
   - Support query parameters on `GET /devices` (e.g., `?status=OFFLINE&search=Sensor&page=1`).

---

## 12. AI Usage

### Tools Used
- **Antigravity Agentic IDE** powered by **Claude 3.7 Sonnet**.
- **BMAD (Breakthrough Method for Agile AI-Assisted Development)** workflow framework for structured planning, architecture, test-driven story implementation, and traceability.

### What AI Was Used For
- Drafting the initial Product Brief and PRD from problem statement requirements.
- Establishing the Architectural Spine and strict dependency layer invariants.
- Scaffolding the incremental story breakdown across 4 agile epics.
- Authoring comprehensive unit and integration tests with mocked time fixtures.
- Generating the standalone multi-threaded simulator and responsive dashboard.

### Suggestions Changed or Rejected
1. **Background Worker Status Updates (Rejected)**:
   - *AI Suggestion*: Initially, a Celery worker or cron job was suggested to run every 10 seconds and update a `status` column on the `Device` database model.
   - *Decision*: **Rejected**. Storing a mutable status column creates dual sources of truth, risks race conditions, and requires running Redis/Celery background processes. Evaluating status dynamically at read time (`compute_status`) guaranteed 100% accurate, atomic status without background infrastructure.
2. **Client-Provided Timestamps for Status Calculation (Rejected)**:
   - *AI Suggestion*: Computing status by comparing the client's payload `timestamp` with server `now()`.
   - *Decision*: **Rejected**. Devices with skewed or un-synced system clocks would incorrectly be marked `OFFLINE` or stay `ONLINE` indefinitely. We strictly adopted **Server Clock Authority**: `received_at = timezone.now()` recorded on the server is the sole timestamp used for threshold evaluation.

### What Was Personally Verified Before Submission
- **Exact 30-Second Timeout Boundary**:
  - Personally verified that the threshold comparison in `compute_status` is inclusive at exactly 30.000s (`delta.total_seconds() <= 30.0` is `ONLINE`) and flips to `OFFLINE` at 30.001s.
- **Zero Sleep Execution**:
  - Verified that all 32 automated tests run in 0.028s using `unittest.mock.patch('django.utils.timezone.now')` with zero wall-clock `time.sleep()` delays.
- **Simulator Independence**:
  - Verified that `simulator/run.py` runs cleanly with no Django dependencies and that stopping `device-03` dynamically causes `GET /devices/device-03` to report `OFFLINE` after 30 seconds.
