# The Observer

A distributed system that monitors your computers and servers in real time via a web dashboard. Run a lightweight agent on each machine; a central collector stores metrics in PostgreSQL; a React dashboard shows live status and charts.

**Phase 1 MVP** · Personal learning project · Not a business product.

---

## Features

- **Agent ("Ghost")** — Collects CPU, RAM, disk, and network metrics every 2 seconds; buffers locally when the server is down and retries when it’s back.
- **Collector ("Brain")** — Flask server that receives metrics, stores them in PostgreSQL, and broadcasts updates over WebSockets.
- **Dashboard ("Lens")** — React (Vite) UI with a fleet overview, server cards, and per-agent detail views with 1-hour line charts (Recharts).
- **Real-time** — WebSocket updates so the dashboard refreshes without manual reload.
- **Simple auth** — Single hardcoded username/password for the dashboard (Phase 1).
- **Docker Compose** — One-command run for Postgres, collector, and dashboard.

### In scope (Phase 1)

| In scope | Out of scope (Phase 2+) |
|----------|-------------------------|
| 4 metrics: CPU, RAM, disk, network I/O | Email/Slack alerts |
| Metrics every 2s, buffering on failure | Multiple users |
| PostgreSQL storage | Configurable thresholds |
| Live server cards + 1-hour charts | HA/clustering, anomaly detection |
| WebSocket live updates | Historical data &gt; 7 days |

---

## Tech stack

| Layer | Technology |
|-------|------------|
| **Agent** | Python 3.8+, `psutil`, `requests` |
| **Collector** | Flask, Flask-SocketIO |
| **Database** | PostgreSQL |
| **Frontend** | React (Vite), Tailwind CSS, Recharts |
| **Deployment** | Docker Compose |

---

## Quick start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Or: Python 3.8+, Node 18+, PostgreSQL (for local dev)

### Run with Docker Compose

```bash
git clone <your-repo-url>
cd the_observer

docker-compose up
```

- **Dashboard:** http://localhost:8080  
- **Collector API:** http://localhost:5000  
- **PostgreSQL:** localhost:5432 (user `observer`, db `observer`)

Default dashboard login: `admin` / `demo` (hardcoded for Phase 1).

### Run the agent on a machine to monitor

```bash
cd observer-agent
cp .env.example .env
# Edit .env: set OBSERVER_SERVER (e.g. http://your-server:5000) and optional OBSERVER_AGENT_ID
pip install -r requirements.txt
python agent.py
```

---

## Project structure

```
observer/
├── observer-agent/                 # Python agent (metrics collection)
│   ├── agent.py
│   ├── requirements.txt
│   └── .env.example
├── collector/             # Flask API + WebSocket
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/             # React (Vite) UI
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── init.sql               # PostgreSQL schema
├── PRD.md                 # Product requirements
├── TRD.md                 # Technical reference (APIs, schema, patterns)
└── README.md
```

---

## Configuration

### Agent (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OBSERVER_SERVER` | Yes | — | Collector URL (e.g. `http://localhost:5000`) |
| `OBSERVER_AGENT_ID` | No | hostname | Identifier for this agent |
| `OBSERVER_INTERVAL` | No | `2` | Seconds between metric submissions |
| `OBSERVER_BUFFER_SIZE` | No | `100` | Max metrics to buffer when server is down |

### Collector (`.env`)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `FLASK_ENV` | `development` or `production` |
| `SECRET_KEY` | Flask secret (change in production) |

### Dashboard (`.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Collector base URL (e.g. `http://localhost:5000`) |

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/metrics` | Agent submits metrics (JSON body) |
| `GET` | `/api/agents` | List all agents and latest metrics |
| `GET` | `/api/agents/{id}/metrics?hours=1` | Historical metrics for charts (1–24 hours) |

WebSocket: connect to the collector; events include `metric_update` (broadcast when an agent sends metrics) and `connected` (initial agent list). See [TRD.md](TRD.md) for full API and WebSocket details.

---

## Deployment

- **Local:** `docker-compose up` → use http://localhost:8080.
- **Home server / Raspberry Pi:** Copy repo, run `docker-compose up -d`, open `http://<host>:8080`.
- **VPS (e.g. DigitalOcean, Linode):** Install Docker, clone repo, `docker-compose up -d`, open `http://<droplet-ip>:8080`.

Ensure the collector is reachable on port 5000 from any machine running the agent, and set `OBSERVER_SERVER` accordingly.

---

## Documentation

- **[PRD.md](PRD.md)** — Product scope, features, weekly breakdown, success criteria.
- **[TRD.md](TRD.md)** — Technical reference: agent spec, collector API, DB schema, WebSocket events, React structure, env vars, testing checklist.

---

## License

See [LICENSE](LICENSE) if present.
