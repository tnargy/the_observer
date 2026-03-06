import os
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, Float, String, DateTime, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Load env
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable required")

OFFLINE_SECONDS = int(os.getenv('OFFLINE_SECONDS', '10'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# In-memory registry for quick status + last metrics
agents_registry = {}


class Agent(Base):
    __tablename__ = 'agents'
    id = Column(String(255), primary_key=True)
    hostname = Column(String(255))
    ip_address = Column(String(45))
    last_seen = Column(DateTime)
    registered_at = Column(DateTime, default=datetime.utcnow)


class Metric(Base):
    __tablename__ = 'metrics'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    agent_id = Column(String(255), ForeignKey('agents.id'), nullable=False)
    timestamp = Column(BigInteger, nullable=False)  # unix seconds
    cpu_percent = Column(Float)
    memory_percent = Column(Float)
    disk_percent = Column(Float)
    network_in_bytes = Column(BigInteger)
    network_out_bytes = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship('Agent')


# Indexes for performance (match TRD)
Index('idx_agent_timestamp', Metric.agent_id, Metric.timestamp)
Index('idx_timestamp', Metric.timestamp)


def to_iso(dt):
    return dt.isoformat() if dt else None


@app.route('/api/metrics', methods=['POST'])
def post_metrics():
    try:
        data = request.get_json()
        if not data or 'agent_id' not in data or 'metrics' not in data:
            return jsonify({'error': 'missing fields'}), 400

        agent_id = data['agent_id']
        metrics = data['metrics']
        timestamp = data.get('timestamp', int(time.time()))

        session = SessionLocal()

        # Ensure agent exists
        agent = session.query(Agent).get(agent_id)
        if not agent:
            agent = Agent(id=agent_id, hostname=agent_id, last_seen=datetime.utcnow())
            session.add(agent)
        else:
            agent.last_seen = datetime.utcnow()

        # Insert metric
        metric = Metric(
            agent_id=agent_id,
            timestamp=int(timestamp),
            cpu_percent=metrics.get('cpu_percent'),
            memory_percent=metrics.get('memory_percent'),
            disk_percent=metrics.get('disk_percent'),
            network_in_bytes=metrics.get('network_in_bytes_per_sec'),
            network_out_bytes=metrics.get('network_out_bytes_per_sec')
        )
        session.add(metric)
        session.commit()

        # Update registry
        agents_registry[agent_id] = {
            'last_seen': datetime.utcnow(),
            'status': 'online',
            'metrics': metrics
        }

        # Broadcast via socket
        socketio.emit('metric_update', {
            'agent_id': agent_id,
            'metrics': metrics,
            'status': 'online',
            'timestamp': int(timestamp)
        }, broadcast=True)

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        app.logger.exception('Error processing /api/metrics')
        return jsonify({'error': 'server error'}), 500


@app.route('/api/agents', methods=['GET'])
def get_agents():
    now = datetime.utcnow()
    result = []
    for agent_id, info in agents_registry.items():
        seconds_since = (now - info['last_seen']).total_seconds()
        status = 'online' if seconds_since < OFFLINE_SECONDS else 'offline'

        result.append({
            'id': agent_id,
            'status': status,
            'metrics': info['metrics'] if status == 'online' else None,
            'last_seen': info['last_seen'].isoformat()
        })

    return jsonify(result), 200


@app.route('/api/agents/<agent_id>/metrics', methods=['GET'])
def get_agent_metrics(agent_id):
    try:
        hours = int(request.args.get('hours', 1))
    except ValueError:
        hours = 1
    hours = max(1, min(24, hours))

    cutoff_time = int(time.time()) - (hours * 3600)

    session = SessionLocal()
    rows = session.query(Metric).filter(
        Metric.agent_id == agent_id,
        Metric.timestamp > cutoff_time
    ).order_by(Metric.timestamp.asc()).limit(3600).all()

    if not rows:
        return jsonify({'error': 'agent not found or no data'}), 404

    result = []
    for r in rows:
        result.append({
            'timestamp': r.timestamp,
            'cpu_percent': r.cpu_percent,
            'memory_percent': r.memory_percent,
            'disk_percent': r.disk_percent,
            'network_in_bytes_per_sec': r.network_in_bytes,
            'network_out_bytes_per_sec': r.network_out_bytes
        })

    return jsonify(result), 200


@socketio.on('connect')
def handle_connect():
    app.logger.info(f'Dashboard connected')
    # Send current agents
    agents_list = []
    now = datetime.utcnow()
    for agent_id, info in agents_registry.items():
        seconds_since = (now - info['last_seen']).total_seconds()
        status = 'online' if seconds_since < OFFLINE_SECONDS else 'offline'
        agents_list.append({
            'id': agent_id,
            'status': status,
            'metrics': info['metrics'] if status == 'online' else None,
            'last_seen': info['last_seen'].isoformat()
        })

    socketio.emit('connected', {'agents': agents_list})


def check_offline_agents_loop():
    while True:
        now = datetime.utcnow()
        for agent_id, info in list(agents_registry.items()):
            seconds_since = (now - info['last_seen']).total_seconds()
            if seconds_since > OFFLINE_SECONDS and info.get('status') != 'offline':
                info['status'] = 'offline'
                socketio.emit('agent_offline', {
                    'agent_id': agent_id,
                    'last_seen': info['last_seen'].isoformat()
                }, broadcast=True)
        time.sleep(OFFLINE_SECONDS)


def start_background_thread():
    t = threading.Thread(target=check_offline_agents_loop, daemon=True)
    t.start()


if __name__ == '__main__':
    # Create tables if they don't exist
    Base.metadata.create_all(engine)
    start_background_thread()
    socketio.run(app, host='0.0.0.0', port=5000)
