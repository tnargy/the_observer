TRD.md

# "The Observer" Phase 1 MVP – Technical Reference Document (TRD)

**Companion to:** Observer_Phase1_VibeCodePRD.md  
**Purpose:** Detailed technical specs for when you're actually coding  
**Use this when:** "Wait, what should this API return?" or "How do I structure the database?"

---

## Quick Navigation

- [1. Agent Specifications](#1-agent-specifications)
- [2. Collector API Reference](#2-collector-api-reference)
- [3. Database Schema](#3-database-schema)
- [4. WebSocket Events](#4-websocket-events)
- [5. Component Architecture (React)](#5-component-architecture-react)
- [6. Environment Variables](#6-environment-variables)
- [7. File Structure](#7-file-structure)
- [8. Error Handling](#8-error-handling)
- [9. Testing Checklist](#9-testing-checklist)

---

## 1. Agent Specifications

### 1.1 Agent File Structure

```
observer-agent/
├── agent.py              # Main entry point
├── requirements.txt      # pip install -r requirements.txt
├── .env                  # Configuration (not in git)
├── .env.example          # Template (in git)
├── agent.uuid            # Generated on first run
└── metrics_buffer.json   # Local buffer (if server down)
```

### 1.2 Agent Lifecycle

```
┌─ Start ─┐
│         │
├─ Load .env config
│
├─ Generate/Load UUID from agent.uuid file
│  (If file doesn't exist: create new UUID, save to file)
│
├─ Every 2 seconds (OBSERVER_INTERVAL):
│  ├─ Collect metrics (CPU, RAM, Disk, Network)
│  ├─ Create JSON payload
│  ├─ POST to server
│  │  ├─ Success (200) → clear local buffer
│  │  └─ Failure → add to local buffer
│  │
│  └─ If local buffer has items and server responds:
│      └─ Send last 10 buffered metrics
│
└─ On Ctrl+C → Graceful shutdown, log it
```

### 1.3 Agent Configuration (.env)

```env
# Required
OBSERVER_SERVER=https://localhost:5000
OBSERVER_AGENT_ID=my-laptop

# Optional (defaults shown)
OBSERVER_INTERVAL=2
OBSERVER_BUFFER_SIZE=100
OBSERVER_VERIFY_SSL=false
OBSERVER_LOG_LEVEL=INFO
```

**Behavior:**
- If `OBSERVER_SERVER` not set → exit with error message
- If `OBSERVER_AGENT_ID` not set → use hostname (from `socket.gethostname()`)
- If `.env` file missing → look for env vars, exit if OBSERVER_SERVER not found

### 1.4 Agent Metric Collection

**Metrics collected every cycle:**

```python
{
    "agent_id": "my-laptop",           # From config or hostname
    "timestamp": 1234567890,           # Unix seconds (int)
    "metrics": {
        "cpu_percent": 45.2,           # 0-100, float
        "memory_percent": 62.1,        # 0-100, float
        "disk_percent": 78.5,          # 0-100, float (root mount)
        "network_in_bytes_per_sec": 102400,    # int, bytes/sec
        "network_out_bytes_per_sec": 51200     # int, bytes/sec
    }
}
```

**Collection code:**

```python
import psutil
import time
from collections import deque

class MetricsCollector:
    def __init__(self):
        self.last_net_in = 0
        self.last_net_out = 0
        self.last_time = time.time()
    
    def collect(self):
        """Collect all metrics and return dict"""
        now = time.time()
        time_delta = now - self.last_time
        
        # CPU (percent over last interval)
        cpu = psutil.cpu_percent(interval=0.1)
        
        # Memory (percent)
        mem = psutil.virtual_memory().percent
        
        # Disk (percent, root mount)
        disk = psutil.disk_usage('/').percent
        
        # Network (bytes/sec)
        net_io = psutil.net_io_counters()
        net_in_delta = net_io.bytes_recv - self.last_net_in
        net_out_delta = net_io.bytes_sent - self.last_net_out
        net_in_per_sec = int(net_in_delta / time_delta) if time_delta > 0 else 0
        net_out_per_sec = int(net_out_delta / time_delta) if time_delta > 0 else 0
        
        self.last_net_in = net_io.bytes_recv
        self.last_net_out = net_io.bytes_sent
        self.last_time = now
        
        return {
            "cpu_percent": round(cpu, 2),
            "memory_percent": round(mem, 2),
            "disk_percent": round(disk, 2),
            "network_in_bytes_per_sec": net_in_per_sec,
            "network_out_bytes_per_sec": net_out_per_sec,
        }
```

### 1.5 Agent HTTP POST

**Endpoint:** `POST {OBSERVER_SERVER}/api/metrics`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
    "agent_id": "my-laptop",
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

**Expected Responses:**

| Status | Body | Meaning | Agent Action |
|--------|------|---------|--------------|
| 200 | `{"status": "ok"}` | Success | Clear buffer, continue |
| 400 | `{"error": "invalid json"}` | Bad request | Log error, retry next cycle |
| 500 | `{"error": "server error"}` | Server error | Buffer metric, retry |
| Connection Error | (none) | Network down | Buffer metric, retry |
| Timeout (10s) | (none) | Server slow | Buffer metric, retry |

**Agent retry logic:**

```python
import requests
import time
import json

class MetricsClient:
    def __init__(self, server_url, agent_id, buffer_size=100):
        self.server_url = server_url
        self.agent_id = agent_id
        self.buffer = deque(maxlen=buffer_size)
        self.session = requests.Session()
        self.session.verify = False  # Self-signed cert
    
    def send_metrics(self, metrics_dict):
        """Try to send metrics, buffer if fail"""
        payload = {
            "agent_id": self.agent_id,
            "timestamp": int(time.time()),
            "metrics": metrics_dict
        }
        
        try:
            response = self.session.post(
                f"{self.server_url}/api/metrics",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                self.flush_buffer()  # Send buffered metrics
                print(f"✅ Metrics sent")
                return True
            else:
                print(f"⚠️  Server returned {response.status_code}")
                self.buffer.append(payload)
                return False
        
        except requests.Timeout:
            print(f"⚠️  Request timeout")
            self.buffer.append(payload)
            return False
        except Exception as e:
            print(f"⚠️  Error: {e}")
            self.buffer.append(payload)
            return False
    
    def flush_buffer(self):
        """Try to send buffered metrics"""
        if not self.buffer:
            return
        
        for payload in list(self.buffer)[-10:]:  # Last 10
            try:
                self.session.post(
                    f"{self.server_url}/api/metrics",
                    json=payload,
                    timeout=5
                )
                self.buffer.remove(payload)
            except:
                pass  # Keep in buffer for next time
```

### 1.6 Agent Main Loop

```python
import os
import time
from dotenv import load_dotenv

# Load config
load_dotenv()
SERVER = os.getenv('OBSERVER_SERVER')
AGENT_ID = os.getenv('OBSERVER_AGENT_ID', socket.gethostname())
INTERVAL = int(os.getenv('OBSERVER_INTERVAL', 2))

if not SERVER:
    print("ERROR: OBSERVER_SERVER not set in .env")
    exit(1)

# Initialize
collector = MetricsCollector()
client = MetricsClient(SERVER, AGENT_ID)

print(f"🚀 Starting agent: {AGENT_ID}")
print(f"📍 Server: {SERVER}")
print(f"⏱️  Interval: {INTERVAL}s")

try:
    while True:
        metrics = collector.collect()
        client.send_metrics(metrics)
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\n👋 Shutting down gracefully")
    exit(0)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    exit(1)
```

---

## 2. Collector API Reference

### 2.1 POST /api/metrics

**Purpose:** Agent sends metrics here (called every 2 seconds per agent)

**Request:**
```http
POST /api/metrics
Content-Type: application/json

{
    "agent_id": "my-laptop",
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

**Response (200 OK):**
```json
{
    "status": "ok"
}
```

**Response (400 Bad Request):**
```json
{
    "error": "invalid json or missing fields"
}
```

**Response (500 Server Error):**
```json
{
    "error": "database error"
}
```

**Collector logic:**

```python
@app.route('/api/metrics', methods=['POST'])
def post_metrics():
    """Receive metrics from agent"""
    try:
        data = request.json
        
        # Validate required fields
        if not data or 'agent_id' not in data or 'metrics' not in data:
            return {'error': 'missing fields'}, 400
        
        agent_id = data['agent_id']
        metrics = data['metrics']
        timestamp = data.get('timestamp', int(time.time()))
        
        # Store in database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO metrics 
            (agent_id, timestamp, cpu_percent, memory_percent, disk_percent, 
             network_in_bytes, network_out_bytes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            agent_id,
            timestamp,
            metrics.get('cpu_percent'),
            metrics.get('memory_percent'),
            metrics.get('disk_percent'),
            metrics.get('network_in_bytes_per_sec'),
            metrics.get('network_out_bytes_per_sec')
        ))
        conn.commit()
        
        # Update in-memory registry
        agents_registry[agent_id] = {
            'last_seen': datetime.now(),
            'status': 'online',
            'metrics': metrics
        }
        
        # Broadcast to dashboards
        socketio.emit('metric_update', {
            'agent_id': agent_id,
            'metrics': metrics,
            'status': 'online',
            'timestamp': timestamp
        }, broadcast=True)
        
        return {'status': 'ok'}, 200
    
    except Exception as e:
        print(f"Error: {e}")
        return {'error': 'server error'}, 500
```

---

### 2.2 GET /api/agents

**Purpose:** Dashboard asks for all agents + their current status

**Request:**
```http
GET /api/agents
```

**Response (200 OK):**
```json
[
    {
        "id": "my-laptop",
        "status": "online",
        "metrics": {
            "cpu_percent": 45.2,
            "memory_percent": 62.1,
            "disk_percent": 78.5,
            "network_in_bytes_per_sec": 102400,
            "network_out_bytes_per_sec": 51200
        },
        "last_seen": "2025-03-05T10:30:45.123Z"
    },
    {
        "id": "raspberrypi",
        "status": "offline",
        "metrics": null,
        "last_seen": "2025-03-05T10:15:00.000Z"
    }
]
```

**Collector logic:**

```python
@app.route('/api/agents', methods=['GET'])
def get_agents():
    """Return all agents + their status"""
    result = []
    now = datetime.now()
    
    for agent_id, info in agents_registry.items():
        seconds_since = (now - info['last_seen']).total_seconds()
        status = 'online' if seconds_since < 10 else 'offline'
        
        result.append({
            'id': agent_id,
            'status': status,
            'metrics': info['metrics'] if status == 'online' else None,
            'last_seen': info['last_seen'].isoformat()
        })
    
    return jsonify(result), 200
```

---

### 2.3 GET /api/agents/{agent_id}/metrics

**Purpose:** Dashboard asks for historical metrics (for charts)

**Request:**
```http
GET /api/agents/my-laptop/metrics?hours=1
```

**Query Parameters:**
| Param | Type | Default | Range |
|-------|------|---------|-------|
| hours | int | 1 | 1-24 |

**Response (200 OK):**
```json
[
    {
        "timestamp": 1234567890,
        "cpu_percent": 45.2,
        "memory_percent": 62.1,
        "disk_percent": 78.5,
        "network_in_bytes_per_sec": 102400,
        "network_out_bytes_per_sec": 51200
    },
    {
        "timestamp": 1234567892,
        "cpu_percent": 46.1,
        "memory_percent": 62.3,
        "disk_percent": 78.5,
        "network_in_bytes_per_sec": 105200,
        "network_out_bytes_per_sec": 52100
    }
]
```

**Response (404 Not Found):**
```json
{
    "error": "agent not found"
}
```

**Collector logic:**

```python
@app.route('/api/agents/<agent_id>/metrics', methods=['GET'])
def get_agent_metrics(agent_id):
    """Return historical metrics for agent"""
    hours = request.args.get('hours', 1, type=int)
    hours = max(1, min(24, hours))  # Clamp 1-24
    
    cutoff_time = int(time.time()) - (hours * 3600)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, cpu_percent, memory_percent, disk_percent, 
               network_in_bytes, network_out_bytes
        FROM metrics
        WHERE agent_id = %s AND timestamp > %s
        ORDER BY timestamp ASC
        LIMIT 3600
    """, (agent_id, cutoff_time))
    
    rows = cursor.fetchall()
    if not rows:
        return {'error': 'agent not found or no data'}, 404
    
    result = [{
        'timestamp': row[0],
        'cpu_percent': row[1],
        'memory_percent': row[2],
        'disk_percent': row[3],
        'network_in_bytes_per_sec': row[4],
        'network_out_bytes_per_sec': row[5]
    } for row in rows]
    
    return jsonify(result), 200
```

---

## 3. Database Schema

### 3.1 Full Schema

```sql
-- Agents table (who's connected)
CREATE TABLE agents (
    id VARCHAR(255) PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
    last_seen TIMESTAMP,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Metrics table (the actual data)
CREATE TABLE metrics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    timestamp BIGINT NOT NULL,              -- Unix seconds
    cpu_percent FLOAT,
    memory_percent FLOAT,
    disk_percent FLOAT,
    network_in_bytes BIGINT,               -- bytes/sec
    network_out_bytes BIGINT,              -- bytes/sec
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    INDEX idx_agent_timestamp (agent_id, timestamp DESC),
    INDEX idx_timestamp (timestamp)
);
```

### 3.2 init.sql (For Docker)

```sql
-- Create database
CREATE DATABASE observer;

-- Create tables
CREATE TABLE agents (
    id VARCHAR(255) PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
    last_seen TIMESTAMP,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE metrics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    timestamp BIGINT NOT NULL,
    cpu_percent FLOAT,
    memory_percent FLOAT,
    disk_percent FLOAT,
    network_in_bytes BIGINT,
    network_out_bytes BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_agent_timestamp ON metrics(agent_id, timestamp DESC);
CREATE INDEX idx_timestamp ON metrics(timestamp);
```

### 3.3 Python: Connect to Database

```python
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import os

# Connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 5,
    os.getenv('DATABASE_URL', 'postgresql://observer:password@localhost:5432/observer')
)

def get_db():
    """Get a connection from the pool"""
    return db_pool.getconn()

def release_db(conn):
    """Return a connection to the pool"""
    db_pool.putconn(conn)

@contextmanager
def db_context():
    """Context manager for database operations"""
    conn = get_db()
    try:
        yield conn
    finally:
        release_db(conn)

# Usage:
# with db_context() as conn:
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM agents")
#     rows = cursor.fetchall()
```

---

## 4. WebSocket Events

### 4.1 WebSocket Connection

**When:** Dashboard connects to the Collector

```python
@socketio.on('connect')
def handle_connect():
    """Client connected, send initial data"""
    print(f"Dashboard connected: {request.sid}")
    
    # Send all current agents
    agents_list = []
    for agent_id, info in agents_registry.items():
        seconds_since = (datetime.now() - info['last_seen']).total_seconds()
        agents_list.append({
            'id': agent_id,
            'status': 'online' if seconds_since < 10 else 'offline',
            'metrics': info['metrics'] if seconds_since < 10 else None,
            'last_seen': info['last_seen'].isoformat()
        })
    
    emit('connected', {'agents': agents_list})
```

### 4.2 metric_update Event

**When:** Agent sends metrics (broadcasted to all clients)

```python
# Sent by Collector:
socketio.emit('metric_update', {
    'agent_id': 'my-laptop',
    'metrics': {
        'cpu_percent': 45.2,
        'memory_percent': 62.1,
        'disk_percent': 78.5,
        'network_in_bytes_per_sec': 102400,
        'network_out_bytes_per_sec': 51200
    },
    'status': 'online',
    'timestamp': 1234567890
}, broadcast=True)
```

**React listens:**
```jsx
socket.on('metric_update', (data) => {
    // Update agent card or chart
    setAgents(prev => ({
        ...prev,
        [data.agent_id]: {
            ...prev[data.agent_id],
            metrics: data.metrics,
            status: data.status,
            last_seen: new Date().toISOString()
        }
    }));
});
```

### 4.3 Offline Detection

**Background job (runs every 10 seconds):**

```python
def check_offline_agents():
    """Mark agents offline if no metric in 10 seconds"""
    now = datetime.now()
    for agent_id, info in agents_registry.items():
        seconds_since = (now - info['last_seen']).total_seconds()
        
        if seconds_since > 10 and info['status'] != 'offline':
            info['status'] = 'offline'
            socketio.emit('agent_offline', {
                'agent_id': agent_id,
                'last_seen': info['last_seen'].isoformat()
            }, broadcast=True)

# Schedule to run every 10 seconds
scheduler = BackgroundScheduler()
scheduler.add_job(check_offline_agents, 'interval', seconds=10)
scheduler.start()
```

---

## 5. Component Architecture (React)

### 5.1 File Structure

```
dashboard/
├── src/
│   ├── App.jsx                      # Router + main layout
│   ├── App.css
│   ├── pages/
│   │   ├── Login.jsx                # Login page
│   │   ├── Dashboard.jsx            # Fleet overview
│   │   └── ServerDetail.jsx         # Detail view with charts
│   ├── components/
│   │   ├── ServerCard.jsx           # Card component
│   │   ├── MetricsChart.jsx         # Recharts wrapper
│   │   └── Header.jsx               # Top bar with logout
│   ├── hooks/
│   │   ├── useSocket.js             # WebSocket connection
│   │   └── useAuth.js               # Authentication state
│   ├── utils/
│   │   ├── api.js                   # API calls (fetch)
│   │   ├── formatters.js            # Format bytes, time, etc
│   │   └── socket.js                # Socket.IO setup
│   └── index.css                    # Tailwind imports
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

### 5.2 useSocket Hook

```jsx
// hooks/useSocket.js
import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

export function useSocket() {
    const [socket, setSocket] = useState(null);
    const [connected, setConnected] = useState(false);
    
    useEffect(() => {
        const newSocket = io(
            import.meta.env.VITE_API_URL || 'http://localhost:5000',
            {
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 5000,
                reconnectionAttempts: 5
            }
        );
        
        newSocket.on('connect', () => {
            console.log('Connected to server');
            setConnected(true);
        });
        
        newSocket.on('disconnect', () => {
            console.log('Disconnected from server');
            setConnected(false);
        });
        
        setSocket(newSocket);
        
        return () => newSocket.close();
    }, []);
    
    return { socket, connected };
}
```

### 5.3 ServerCard Component

```jsx
// components/ServerCard.jsx
import React from 'react';
import { formatBytes, formatTime } from '../utils/formatters';

export function ServerCard({ agent, onClick }) {
    const isOnline = agent.status === 'online';
    
    return (
        <div
            onClick={onClick}
            className={`
                p-4 rounded border cursor-pointer transition
                ${isOnline 
                    ? 'bg-slate-700 border-slate-600 hover:border-blue-500' 
                    : 'bg-slate-800 border-slate-700'
                }
            `}
        >
            <div className="flex justify-between items-center mb-2">
                <h3 className="text-lg font-bold text-white">{agent.id}</h3>
                <span className={`
                    inline-block w-3 h-3 rounded-full
                    ${isOnline ? 'bg-green-500' : 'bg-red-500'}
                `}></span>
            </div>
            
            <div className="text-sm text-gray-400 mb-3">
                Last seen: {formatTime(agent.last_seen)}
            </div>
            
            {isOnline ? (
                <div className="space-y-1 text-sm text-gray-300">
                    <div>CPU: {agent.metrics.cpu_percent.toFixed(1)}%</div>
                    <div>RAM: {agent.metrics.memory_percent.toFixed(1)}%</div>
                    <div>Disk: {agent.metrics.disk_percent.toFixed(1)}%</div>
                    <div className="text-xs text-gray-400 mt-2">
                        ↓ {formatBytes(agent.metrics.network_in_bytes_per_sec)}/s
                        {' '}
                        ↑ {formatBytes(agent.metrics.network_out_bytes_per_sec)}/s
                    </div>
                </div>
            ) : (
                <div className="text-sm text-gray-500">No data</div>
            )}
        </div>
    );
}
```

### 5.4 MetricsChart Component

```jsx
// components/MetricsChart.jsx
import React, { useState, useEffect } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { api } from '../utils/api';

export function MetricsChart({ agentId }) {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        setLoading(true);
        api.getAgentMetrics(agentId, 1)  // 1 hour
            .then(metrics => {
                // Format for Recharts
                const formatted = metrics.map(m => ({
                    timestamp: m.timestamp * 1000,  // Convert to ms for x-axis
                    time: new Date(m.timestamp * 1000).toLocaleTimeString(),
                    cpu: m.cpu_percent,
                    memory: m.memory_percent,
                    disk: m.disk_percent,
                    networkIn: m.network_in_bytes_per_sec,
                    networkOut: m.network_out_bytes_per_sec
                }));
                setData(formatted);
            })
            .finally(() => setLoading(false));
    }, [agentId]);
    
    if (loading) return <div>Loading chart...</div>;
    if (data.length === 0) return <div>No data yet</div>;
    
    return (
        <div className="space-y-6">
            {/* CPU Chart */}
            <div>
                <h3 className="text-white mb-2">CPU Usage</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9CA3AF" />
                        <YAxis domain={[0, 100]} stroke="#9CA3AF" />
                        <Tooltip contentStyle={{ backgroundColor: '#1F2937' }} />
                        <Line
                            type="monotone"
                            dataKey="cpu"
                            stroke="#3B82F6"
                            dot={false}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
            
            {/* RAM Chart */}
            <div>
                <h3 className="text-white mb-2">Memory Usage</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9CA3AF" />
                        <YAxis domain={[0, 100]} stroke="#9CA3AF" />
                        <Tooltip contentStyle={{ backgroundColor: '#1F2937' }} />
                        <Line
                            type="monotone"
                            dataKey="memory"
                            stroke="#10B981"
                            dot={false}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
            
            {/* Disk Chart */}
            <div>
                <h3 className="text-white mb-2">Disk Usage</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9CA3AF" />
                        <YAxis domain={[0, 100]} stroke="#9CA3AF" />
                        <Tooltip contentStyle={{ backgroundColor: '#1F2937' }} />
                        <Line
                            type="monotone"
                            dataKey="disk"
                            stroke="#F59E0B"
                            dot={false}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
            
            {/* Network Chart */}
            <div>
                <h3 className="text-white mb-2">Network I/O</h3>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9CA3AF" />
                        <YAxis stroke="#9CA3AF" />
                        <Tooltip contentStyle={{ backgroundColor: '#1F2937' }} />
                        <Legend />
                        <Line
                            type="monotone"
                            dataKey="networkIn"
                            stroke="#06B6D4"
                            name="Download"
                            dot={false}
                            isAnimationActive={false}
                        />
                        <Line
                            type="monotone"
                            dataKey="networkOut"
                            stroke="#EC4899"
                            name="Upload"
                            dot={false}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
```

### 5.5 API Utils

```javascript
// utils/api.js
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export const api = {
    getAgents: async () => {
        const response = await fetch(`${API_URL}/api/agents`);
        if (!response.ok) throw new Error('Failed to fetch agents');
        return response.json();
    },
    
    getAgentMetrics: async (agentId, hours = 1) => {
        const response = await fetch(
            `${API_URL}/api/agents/${agentId}/metrics?hours=${hours}`
        );
        if (!response.ok) throw new Error('Failed to fetch metrics');
        return response.json();
    },
    
    login: async (username, password) => {
        const response = await fetch(`${API_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
            credentials: 'include'
        });
        if (!response.ok) throw new Error('Login failed');
        return response.json();
    },
    
    logout: async () => {
        await fetch(`${API_URL}/api/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    }
};
```

### 5.6 Formatters

```javascript
// utils/formatters.js
export function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

export function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 10) return 'Just now';
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
}

export function formatPercent(value) {
    return value ? `${value.toFixed(1)}%` : 'N/A';
}
```

---

## 6. Environment Variables

### 6.1 Agent (.env)

```env
# Required
OBSERVER_SERVER=https://localhost:5000

# Optional
OBSERVER_AGENT_ID=my-laptop
OBSERVER_INTERVAL=2
OBSERVER_BUFFER_SIZE=100
OBSERVER_VERIFY_SSL=false
OBSERVER_LOG_LEVEL=INFO
```

### 6.2 Collector (.env)

```env
# Flask
FLASK_ENV=development
FLASK_DEBUG=true
SECRET_KEY=dev-secret-change-in-production

# Database
DATABASE_URL=postgresql://observer:password@localhost:5432/observer

# Security
VERIFY_SSL=false

# Logging
LOG_LEVEL=INFO
```

### 6.3 Dashboard (.env)

```env
VITE_API_URL=http://localhost:5000
```

---

## 7. File Structure

```
observer/
├── collector/
│   ├── app.py                       # Flask app
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── agent/
│   ├── agent.py                     # Main agent code
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── dashboard/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── utils/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── docker-compose.yml
├── init.sql
├── README.md
├── .gitignore
└── LICENSE
```

---

## 8. Error Handling

### 8.1 Agent Error Handling

```python
# Level 1: Metric collection errors
try:
    metrics = collector.collect()
except Exception as e:
    print(f"❌ Failed to collect metrics: {e}")
    # Skip this cycle, try again next cycle

# Level 2: Network errors
try:
    client.send_metrics(metrics)
except requests.Timeout:
    print(f"⚠️  Server timeout, buffering metric")
    # Buffer it, don't crash
except Exception as e:
    print(f"⚠️  Network error: {e}")
    # Buffer it, continue

# Level 3: Fatal errors
if not SERVER:
    print("❌ OBSERVER_SERVER not configured")
    exit(1)  # Fail fast on config errors
```

### 8.2 Collector Error Handling

```python
# Always return JSON
try:
    # Process request
    return {'status': 'ok'}, 200
except ValueError as e:
    return {'error': str(e)}, 400  # Client error
except Exception as e:
    print(f"❌ Server error: {e}")
    return {'error': 'server error'}, 500  # Server error
```

### 8.3 React Error Handling

```jsx
// API calls have try-catch
try {
    const agents = await api.getAgents();
    setAgents(agents);
} catch (error) {
    console.error('Failed to fetch agents:', error);
    setError('Failed to load agents');  // Show to user
}

// WebSocket disconnection
socket.on('disconnect', () => {
    setConnected(false);
    setError('Connection lost');
});
```

---

## 9. Testing Checklist

### 9.1 Agent Testing

- [ ] Agent starts without errors
- [ ] Agent generates metrics every 2 seconds
- [ ] Agent prints metrics to console
- [ ] Network test: Collector offline → agent buffers metrics
- [ ] Network test: Collector comes back → buffered metrics send
- [ ] Agent doesn't crash on invalid Collector response
- [ ] Agent memory stays < 50MB over 1 hour
- [ ] Agent CPU stays < 1% on idle machine

### 9.2 Collector Testing

- [ ] Collector starts without errors
- [ ] POST /api/metrics accepts valid JSON
- [ ] POST /api/metrics rejects invalid JSON with 400
- [ ] GET /api/agents returns all connected agents
- [ ] GET /api/agents/{id}/metrics returns 1 hour of data
- [ ] Offline detection: agent marked offline after 10s no metric
- [ ] WebSocket: new client gets initial agents
- [ ] WebSocket: metric broadcasts to all clients
- [ ] Database: metrics persist after server restart

### 9.3 Dashboard Testing

- [ ] Login with hardcoded credentials works
- [ ] Fleet overview shows all agents
- [ ] Offline agent shows 🔴 red
- [ ] Online agent shows 🟢 green
- [ ] Click agent card → detail view opens
- [ ] Detail view shows 4 charts
- [ ] Charts update in real-time (no refresh needed)
- [ ] Logout clears session

### 9.4 Integration Testing

- [ ] Start all 3 services with docker-compose
- [ ] Agent auto-registers with Collector
- [ ] Dashboard connects to Collector via WebSocket
- [ ] Send metric from agent → appears on dashboard < 2 seconds
- [ ] Restart Collector → agent reconnects and continues
- [ ] Run for 1 hour without crashes

---

## 10. Common Patterns

### 10.1 Database Operations

```python
# Pattern: Use context manager
from contextlib import contextmanager

@contextmanager
def get_cursor():
    conn = get_db()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        release_db(conn)

# Usage:
with get_cursor() as cursor:
    cursor.execute("INSERT INTO metrics ...")
```

### 10.2 React State Updates from WebSocket

```jsx
// Pattern: Update state when metric arrives
socket.on('metric_update', (data) => {
    setAgents(prev => ({
        ...prev,
        [data.agent_id]: {
            ...prev[data.agent_id],
            metrics: data.metrics,
            status: data.status,
            last_seen: new Date().toISOString()
        }
    }));
});
```

### 10.3 Retrying with Backoff

```python
# Pattern: Exponential backoff
import time

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)
```

---

**End of TRD**

Use this document when coding. Keep it open. Reference the APIs, schemas, and patterns when you're unsure.

Happy coding! 🚀
