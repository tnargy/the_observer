PRD.md

# "The Observer" Phase 1 MVP
## A Personal Learning Project (Not a Business)

**Timeline:** 8–12 weeks part-time (10 hrs/week)  
**Goal:** Ship a working distributed monitoring system you actually use  
**Philosophy:** Done is better than perfect. Scope cuts are good. Ship fast, learn forever.

---

## Overview

**What You're Building:**
A system that monitors your computers/servers in real-time on a web dashboard.

**What It Does:**
1. Python agent runs on each computer and sends it metrics (CPU, RAM, disk, network)
2. Flask server collects those metrics and stores them
3. React dashboard shows all your computers + live charts
4. You deploy it and actually use it to monitor your own machines

**Why It's Great to Build:**
- Distributed system (agent ↔ server)
- Real-time updates (WebSockets)
- Full-stack (Python backend, React frontend)
- You'll actually use it when you're done
- Everything fits in your brain (not massive enterprise crud)

---

## Phase 1 Scope (What You're Shipping)

### What's IN Scope
✅ Agent collects 4 metrics: CPU %, RAM %, Disk %, Network I/O  
✅ Agent sends metrics to server every 2 seconds  
✅ Flask server stores metrics in PostgreSQL  
✅ Dashboard shows live server cards with status + metrics  
✅ Click a server → see 1-hour real-time line chart  
✅ WebSocket real-time updates (no refresh button needed)  
✅ Simple auth (one hardcoded username/password)  
✅ Docker Compose setup (one command to run everything)  
✅ Deploy to a real server and use it for a week  

### What's OUT of Scope (Phase 2+)
❌ Email/Slack alerts (Phase 2)  
❌ Multiple users (Phase 2)  
❌ Configurable thresholds (Phase 2)  
❌ HA/clustering (Phase 2+)  
❌ Anomaly detection (Phase 2+)  
❌ Historical data > 7 days (too much for MVP)  

### What's Explicitly Not Important (Don't Waste Time)
⚠️ Beautiful UI (make it functional, not pretty)  
⚠️ Perfect security (you're monitoring your own servers, not running it for strangers)  
⚠️ Scalability beyond 10 agents (you don't have 10 servers yet)  
⚠️ Fancy error handling (basic "it crashed" is fine)  
⚠️ Comprehensive documentation (README + 1 setup guide)  

---

## Technical Stack (Simple Version)

| Layer | Technology | Why |
|-------|-----------|-----|
| **Agent** | Python 3.8+ | Simple, psutil library, you know it |
| **Collector** | Flask + Flask-SocketIO | Lightweight, easy to understand |
| **Database** | PostgreSQL | One query language, robust |
| **Frontend** | React (Vite) | Modern, you've probably used it |
| **Charts** | Recharts | Works out-of-box, minimal setup |
| **Deployment** | Docker Compose | One file, everything runs |
| **Styling** | Tailwind CSS | Utility-first, minimal CSS writing |

---

## Honest Feature List

### Agent ("Ghost")
- **What it does:**
  - Every 2 seconds: measure CPU %, RAM %, Disk %, Network bytes/sec
  - Every 2 seconds: POST JSON to server at `https://localhost:5000/api/metrics`
  - If server is down: buffer last 100 metrics locally, retry when server comes back
  - Log what it's doing to console (or file)

- **What it collects:**
  ```python
  {
    "agent_id": "my-laptop",  # hostname or UUID
    "timestamp": 1234567890,
    "metrics": {
      "cpu_percent": 45.2,
      "memory_percent": 62.1,
      "disk_percent": 78.5,
      "network_in_bytes_per_sec": 102400,
      "network_out_bytes_per_sec": 51200
    }
  }
  ```

- **Config:** Just environment variables
  ```env
  OBSERVER_SERVER=https://localhost:5000
  OBSERVER_AGENT_ID=my-laptop
  OBSERVER_INTERVAL=2  # seconds
  ```

- **No fancy stuff:**
  - No API key rotation (hardcode it, or use simple bearer token)
  - No local file encryption
  - No agent auto-update
  - Just works, logs errors, retries on fail

### Collector ("Brain")

- **What it does:**
  - Listens on `https://localhost:5000`
  - `/api/metrics` endpoint: accepts metric POST, stores in DB
  - `/api/agents` endpoint: returns list of all agents + latest metrics
  - `/api/agents/{id}/metrics?hours=1` endpoint: returns 1 hour of metrics for 1 agent
  - Maintains "live registry" in memory: which agents are online/offline right now
  - Broadcasts updates via WebSocket to all connected dashboards

- **Agent Status Logic:**
  - If metric received in last 10 seconds → agent is **online**
  - If last metric > 10 seconds ago → agent is **offline**
  - Very simple, no fancy exponential backoff

- **Database (PostgreSQL):**
  ```sql
  CREATE TABLE agents (
    id VARCHAR(255) PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
    last_seen TIMESTAMP,
    registered_at TIMESTAMP
  );

  CREATE TABLE metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    agent_id VARCHAR(255),
    timestamp BIGINT,
    cpu_percent FLOAT,
    memory_percent FLOAT,
    disk_percent FLOAT,
    network_in_bytes BIGINT,
    network_out_bytes BIGINT,
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    INDEX (agent_id, timestamp DESC)
  );
  ```

- **WebSocket:**
  - When agent sends metric → broadcast to all dashboard clients
  - Payload:
    ```json
    {
      "type": "metric_update",
      "agent_id": "my-laptop",
      "metrics": { ... },
      "status": "online"
    }
    ```

- **No fancy stuff:**
  - No rate limiting (you're the only user)
  - No input validation beyond "is it JSON?"
  - No auth checks (hardcoded password on dashboard is enough)
  - Keep it simple

### Dashboard ("Lens")

- **Fleet Overview Page:**
  - Grid of server cards (2–3 per row, responsive)
  - Each card shows:
    - Server name (hostname)
    - Status: 🟢 online or 🔴 offline
    - Current CPU % (e.g., "45%")
    - Current RAM % (e.g., "62%")
    - Current Disk % (e.g., "78%")
    - Last updated ("2 seconds ago")
  - Click card → open detailed view

- **Detailed Server View:**
  - Header: Server name, status, IP, last seen
  - 4 line charts (1 hour of data):
    - CPU % over time
    - RAM % over time
    - Disk % over time
    - Network I/O bytes/sec over time
  - That's it. No alerts, no settings, no fancy stuff.

- **Navigation:**
  - "Dashboard" button → back to fleet overview
  - "Refresh" button (manual, for now)
  - Dark mode toggle (just swap Tailwind colors)

- **Auth:**
  - Login page with username/password
  - Hardcoded: username = `admin`, password = `demo` (seriously)
  - Session cookie, expires after 1 hour
  - If logged out, redirect to login

- **No fancy stuff:**
  - No animations
  - No tooltips
  - No drag-and-drop
  - No custom theme builder
  - Functional > pretty

---

## Tech Details (Copy/Paste Friendly)

### Agent Setup
```bash
# Install dependencies
pip install psutil requests python-dotenv

# Create agent.py
# Code below...

# Create .env file
OBSERVER_SERVER=https://localhost:5000
OBSERVER_AGENT_ID=my-laptop
OBSERVER_INTERVAL=2

# Run it
python agent.py
```

**Agent pseudocode:**
```python
import psutil
import requests
import json
import time
from datetime import datetime

OBSERVER_SERVER = os.getenv("OBSERVER_SERVER", "https://localhost:5000")
OBSERVER_AGENT_ID = os.getenv("OBSERVER_AGENT_ID", socket.gethostname())
OBSERVER_INTERVAL = int(os.getenv("OBSERVER_INTERVAL", 2))

local_buffer = []  # Keep last 100 metrics if server is down

while True:
    metrics = {
        "agent_id": OBSERVER_AGENT_ID,
        "timestamp": int(time.time()),
        "metrics": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "network_in_bytes_per_sec": get_network_bytes_in(),  # helper
            "network_out_bytes_per_sec": get_network_bytes_out(),  # helper
        }
    }
    
    # Try to send
    try:
        response = requests.post(
            f"{OBSERVER_SERVER}/api/metrics",
            json=metrics,
            timeout=5,
            verify=False  # Self-signed cert, OK for local
        )
        if response.status_code == 200:
            local_buffer = []  # Clear buffer on success
            print(f"✅ Sent metrics at {datetime.now()}")
        else:
            local_buffer.append(metrics)
    except Exception as e:
        print(f"❌ Failed to send: {e}")
        local_buffer.append(metrics)
    
    # If we have buffered metrics and server is back, send them
    if local_buffer and can_reach_server():
        for buffered in local_buffer[-10:]:  # Last 10
            requests.post(f"{OBSERVER_SERVER}/api/metrics", json=buffered)
    
    time.sleep(OBSERVER_INTERVAL)
```

### Collector Setup
```bash
# Install dependencies
pip install flask flask-socketio python-socketio python-engineio psycopg2-binary

# Create collector.py
# Code below...

# Run it
export DATABASE_URL="postgresql://postgres:password@localhost:5432/observer"
python -m flask --app collector run --host 0.0.0.0 --port 5000
```

**Collector pseudocode:**
```python
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room
import psycopg2
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-secret'  # Hardcoded for now
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory registry
agents_registry = {}

@app.route('/api/metrics', methods=['POST'])
def post_metrics():
    """Agent sends metrics here"""
    data = request.json
    agent_id = data.get('agent_id')
    
    # Store in DB
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO metrics (agent_id, timestamp, cpu_percent, memory_percent, disk_percent, network_in_bytes, network_out_bytes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        agent_id,
        data['timestamp'],
        data['metrics']['cpu_percent'],
        data['metrics']['memory_percent'],
        data['metrics']['disk_percent'],
        data['metrics']['network_in_bytes_per_sec'],
        data['metrics']['network_out_bytes_per_sec'],
    ))
    conn.commit()
    conn.close()
    
    # Update registry
    agents_registry[agent_id] = {
        'last_seen': datetime.now(),
        'status': 'online',
        'metrics': data['metrics']
    }
    
    # Broadcast to all connected dashboards
    socketio.emit('metric_update', {
        'agent_id': agent_id,
        'metrics': data['metrics'],
        'status': 'online'
    }, broadcast=True)
    
    return {'status': 'ok'}, 200

@app.route('/api/agents', methods=['GET'])
def get_agents():
    """Dashboard asks: give me all agents + their status"""
    result = []
    for agent_id, info in agents_registry.items():
        result.append({
            'id': agent_id,
            'status': 'online' if (datetime.now() - info['last_seen']).seconds < 10 else 'offline',
            'metrics': info['metrics'],
            'last_seen': info['last_seen'].isoformat()
        })
    return jsonify(result), 200

@app.route('/api/agents/<agent_id>/metrics', methods=['GET'])
def get_agent_metrics(agent_id):
    """Dashboard asks: give me 1 hour of metrics for this agent"""
    hours = request.args.get('hours', 1, type=int)
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, cpu_percent, memory_percent, disk_percent, network_in_bytes, network_out_bytes
        FROM metrics
        WHERE agent_id = %s AND timestamp > %s
        ORDER BY timestamp DESC
        LIMIT 1800
    """, (agent_id, int(time.time()) - (hours * 3600)))
    
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'timestamp': row[0],
        'cpu_percent': row[1],
        'memory_percent': row[2],
        'disk_percent': row[3],
        'network_in_bytes': row[4],
        'network_out_bytes': row[5],
    } for row in rows]), 200

@socketio.on('connect')
def handle_connect():
    """Dashboard connected, subscribe to updates"""
    print("Dashboard connected")
    emit('initial_data', {
        'agents': [
            {
                'id': aid,
                'status': 'online' if (datetime.now() - info['last_seen']).seconds < 10 else 'offline',
                'metrics': info['metrics']
            }
            for aid, info in agents_registry.items()
        ]
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```

### Dashboard Setup
```bash
# Create React app
npm create vite@latest observer-dashboard -- --template react
cd observer-dashboard

# Install dependencies
npm install recharts tailwindcss socket.io-client axios

# Create components/pages
# Code below...

# Run dev server
npm run dev
```

**Dashboard structure:**
```
src/
  components/
    ServerCard.jsx        # One server card
    ServerDetail.jsx      # Detail view with charts
    Dashboard.jsx         # Fleet overview
    Login.jsx             # Login page
  App.jsx                 # Router
  socket.js              # WebSocket setup
```

**Key component (ServerCard.jsx):**
```jsx
export function ServerCard({ agent }) {
  return (
    <div className="bg-slate-700 p-4 rounded border border-slate-600 cursor-pointer hover:border-blue-500">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-bold">{agent.id}</h3>
        <span className={`inline-block w-3 h-3 rounded-full ${
          agent.status === 'online' ? 'bg-green-500' : 'bg-red-500'
        }`}></span>
      </div>
      <div className="text-sm text-gray-300 mb-3">
        Last seen: {formatTime(agent.last_seen)}
      </div>
      <div className="space-y-1 text-sm">
        <div>CPU: {agent.metrics.cpu_percent.toFixed(1)}%</div>
        <div>RAM: {agent.metrics.memory_percent.toFixed(1)}%</div>
        <div>Disk: {agent.metrics.disk_percent.toFixed(1)}%</div>
        <div>↓ {formatBytes(agent.metrics.network_in_bytes_per_sec)}/s ↑ {formatBytes(agent.metrics.network_out_bytes_per_sec)}/s</div>
      </div>
    </div>
  );
}
```

---

## Docker Compose (Just Copy This)

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: observer
      POSTGRES_PASSWORD: password
      POSTGRES_DB: observer
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "observer"]
      interval: 5s
      timeout: 5s
      retries: 5

  collector:
    build: ./collector
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: "postgresql://observer:password@postgres:5432/observer"
      FLASK_ENV: development
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./collector:/app
    command: python -m flask --app app run --host 0.0.0.0 --port 5000

  dashboard:
    build: ./dashboard
    ports:
      - "3000:5173"
    volumes:
      - ./dashboard/src:/app/src
    command: npm run dev

volumes:
  postgres_data:
```

**init.sql:**
```sql
CREATE TABLE IF NOT EXISTS agents (
  id VARCHAR(255) PRIMARY KEY,
  hostname VARCHAR(255),
  ip_address VARCHAR(45),
  last_seen TIMESTAMP,
  registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metrics (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agent_id VARCHAR(255) NOT NULL,
  timestamp BIGINT NOT NULL,
  cpu_percent FLOAT,
  memory_percent FLOAT,
  disk_percent FLOAT,
  network_in_bytes BIGINT,
  network_out_bytes BIGINT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
  INDEX idx_agent_timestamp (agent_id, timestamp DESC)
);
```

---

## Weekly Breakdown (8 Weeks)

### Week 1: Setup & Planning
- [ ] Clone/create GitHub repo
- [ ] Read Flask docs (1 hour)
- [ ] Read React docs (1 hour)
- [ ] Sketch agent/collector/dashboard on paper (30 min)
- [ ] Set up local dev environment (Python, Node, Docker) (2 hours)
- **Time: 5 hours**

### Week 2: Agent MVP
- [ ] Create `agent.py` that collects CPU, RAM, Disk using psutil
- [ ] Print metrics to console (test it works)
- [ ] Create `.env` config file
- [ ] Test on your laptop: watch metrics print every 2 seconds
- **Time: 5 hours**

### Week 3: Agent → Flask
- [ ] Create Flask app with `/api/metrics` endpoint
- [ ] Agent POSTs to Flask (receive & print)
- [ ] Test: agent sends, Flask receives, prints data
- **Time: 5 hours**

### Week 4: Database
- [ ] Install PostgreSQL locally (or use Docker)
- [ ] Create tables (agents, metrics)
- [ ] Flask stores metrics in DB instead of printing
- [ ] Test: agent sends, Flask stores, check database
- **Time: 5 hours**

### Week 5: React Dashboard & API
- [ ] Create React app with Vite
- [ ] Create `/api/agents` endpoint (returns list of agents + latest metrics)
- [ ] Create Dashboard.jsx that fetches and displays agent cards
- [ ] Test: Start Flask, start React, see cards appear
- **Time: 6 hours**

### Week 6: Charts
- [ ] Create `/api/agents/{id}/metrics` endpoint (1-hour history)
- [ ] Create ServerDetail.jsx with Recharts line charts
- [ ] Click card → see charts (4 charts: CPU, RAM, Disk, Network)
- [ ] Test: Click different servers, see different charts
- **Time: 6 hours**

### Week 7: WebSocket & Polish
- [ ] Add Socket.IO to Flask
- [ ] Agent metric → broadcast to all connected dashboards
- [ ] Test: Change metric on agent → see update on dashboard instantly (no refresh)
- [ ] Add simple login (hardcoded username/password)
- [ ] Fix any obvious bugs
- **Time: 6 hours**

### Week 8: Docker & Deploy
- [ ] Create Dockerfile for Flask
- [ ] Create Dockerfile for React (build then serve)
- [ ] Create docker-compose.yml (Flask + React + Postgres)
- [ ] Test: `docker-compose up` → everything works
- [ ] Deploy to a real server (Linode, DigitalOcean, or Raspberry Pi at home)
- [ ] Run for 1 week, make sure it actually monitors your machines
- **Time: 6 hours**

**Total: ~44 hours (roughly 11 weeks at 4 hrs/week, or 6 weeks at 7 hrs/week)**

---

## Things That WILL Be Annoying (Accept It)

✅ **Expect these problems, they're normal:**

- WebSocket connection drops sometimes → just reload (phase 2: auto-reconnect)
- Database gets big → delete old metrics manually (phase 2: auto-cleanup)
- Agent crashes → restart it manually (phase 2: systemd restart)
- UI is ugly → that's fine, it works (phase 2: prettier)
- Auth is hardcoded → only you use it anyway (phase 2: proper auth)
- Agent sometimes buffers → metrics are delayed but don't drop (phase 2: optimize)
- No alerts → you just watch the dashboard (phase 2: email alerts)
- No multi-user → one password for everyone (phase 2: separate users)

These are all **Phase 2 problems.** Not your problem right now.

---

## Success Criteria (You Know You're Done When...)

✅ Agent runs on your laptop, collects metrics every 2 seconds  
✅ Flask receives metrics without crashing  
✅ Dashboard shows your laptop's card with live CPU/RAM/Disk  
✅ Click card → see 1-hour charts update in real-time  
✅ Deploy to a real server with Docker Compose  
✅ Leave it running for 1 week, it doesn't crash  
✅ You actually check it once a day (proof you made something useful)  

If you hit all of these, **Phase 1 is complete.** Celebrate! 🎉

---

## Deployment (Pick One)

### Option A: Local Only (Easiest)
```bash
docker-compose up
# Everything runs on localhost:3000
```

### Option B: Raspberry Pi / Home Server (Fun)
```bash
# SSH to your Pi
scp -r observer pi@192.168.1.100:~/observer
ssh pi@192.168.1.100

# On the Pi:
cd ~/observer
docker-compose up -d

# Visit http://192.168.1.100:3000 from any device
```

### Option C: DigitalOcean / Linode (If You Have $5/month)
```bash
# Create $5/month Ubuntu droplet
# SSH in, install Docker
curl https://get.docker.com | sh

# Clone repo and run
git clone <your-repo>
cd observer
docker-compose up -d

# Visit your-droplet-ip:3000
```

---

## After Week 8: What's Next?

✅ **You have a working distributed system. That's impressive.**

**Option 1: Stop Here**
- You learned everything you wanted
- You have a cool project on GitHub
- Move on to next idea

**Option 2: Phase 2 (If You're Having Fun)**
- Add email/Slack alerts
- Add proper authentication
- Add more metrics (CPU per core, process list, etc.)
- Add historical data cleanup
- Make UI actually nice

**Option 3: Deploy for Real**
- Run it for friends/family's servers
- Get their feedback
- Iterate based on use

---

## A Few Rules (To Keep You Shipping)

1. **Done > Perfect:** A working dashboard in week 7 beats a perfect dashboard in week 15.
2. **Scope cuts are good:** If something feels hard, punt to Phase 2. Seriously.
3. **Make it work first, optimize later:** Ugly code that works > beautiful code that doesn't.
4. **Deploy early:** Week 7, not week 20. Real deployment catches bugs.
5. **You're the user:** Build what YOU want to monitor, not what you think people want.

---

## Honest Expectations

**You will:**
- Learn Flask, React, WebSockets, PostgreSQL, Docker well
- Write code that actually works
- Build something you use
- Have a great portfolio project
- Hit annoying bugs that make you think
- Deploy something real

**You won't:**
- Build a perfect product
- Understand everything (some mystery is OK)
- Have fancy error handling
- Get everything right the first time
- Be done in 4 weeks (it's 8)

**That's all fine.** Learning > perfection.

---

## Let's Go

```bash
# Right now:
mkdir observer
cd observer
git init

# This week:
# Read 2 hours of Flask + React docs
# Sketch on paper
# Set up environment

# Next week:
# Write agent.py that collects metrics

# 8 weeks later:
# You're running a distributed monitoring system on your own machines
# You learned more than 90% of online tutorials teach
# You have something genuinely cool to show people
```

That's it. That's the whole thing.

Ship it. 🚀

---

**Version:** 1.0  
**Status:** Ready to vibe code  
**Last Updated:** Today  
**Next Phase:** Phase 2 (if you're still having fun)
