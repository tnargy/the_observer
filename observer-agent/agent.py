#!/usr/bin/env python3
"""Lightweight agent that collects system metrics and POSTs them to the
collector service."""

import os
import time
import socket
import json
import logging
import uuid
import tempfile
import random
from pathlib import Path
from collections import deque

from dotenv import load_dotenv
import requests
import psutil


class MetricsCollector:
    """Collects CPU, memory, disk and network metrics using psutil."""

    def __init__(self):
        net_io = psutil.net_io_counters()
        self.last_net_in = net_io.bytes_recv
        self.last_net_out = net_io.bytes_sent
        self.last_time = time.time()

    def collect(self):
        """Return a dict with current metrics.

        Network rates are computed as bytes/sec since last call.
        """
        now = time.time()
        time_delta = now - self.last_time if now - self.last_time > 0 else 1

        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent

        net_io = psutil.net_io_counters()
        net_in_delta = net_io.bytes_recv - self.last_net_in
        net_out_delta = net_io.bytes_sent - self.last_net_out
        net_in_per_sec = int(net_in_delta / time_delta)
        net_out_per_sec = int(net_out_delta / time_delta)

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


# --- Safe persistence helpers ---
DEFAULT_STORAGE_DIR = Path(os.getenv('OBSERVER_STORAGE_DIR', Path(__file__).parent))
DEFAULT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

def _atomic_write_json(path: Path, obj):
    path_parent = path.parent
    with tempfile.NamedTemporaryFile('w', dir=str(path_parent), delete=False) as tf:
        json.dump(obj, tf)
        tf.flush()
        os.fsync(tf.fileno())
        tmpname = tf.name
    os.replace(tmpname, str(path))
    try:
        os.chmod(str(path), 0o600)
    except Exception:
        pass


def _atomic_write_text(path: Path, text: str):
    path_parent = path.parent
    with tempfile.NamedTemporaryFile('w', dir=str(path_parent), delete=False) as tf:
        tf.write(text)
        tf.flush()
        os.fsync(tf.fileno())
        tmpname = tf.name
    os.replace(tmpname, str(path))
    try:
        os.chmod(str(path), 0o600)
    except Exception:
        pass


def load_or_create_uuid(path: Path) -> str:
    try:
        if path.exists():
            data = path.read_text().strip()
            if data:
                return data
    except Exception:
        try:
            path.rename(path.with_suffix('.corrupt'))
        except Exception:
            pass

    u = str(uuid.uuid4())
    try:
        _atomic_write_text(path, u)
    except Exception:
        pass
    return u


def load_buffer_list(path: Path, maxlen: int):
    if not path.exists():
        return []
    try:
        with path.open('r') as f:
            data = json.load(f)
        if not isinstance(data, list):
            try:
                path.rename(path.with_suffix('.corrupt'))
            except Exception:
                pass
            return []
        return data[-maxlen:]
    except Exception:
        try:
            path.rename(path.with_suffix('.corrupt'))
        except Exception:
            pass
        return []


def save_buffer_list(path: Path, buffer_list):
    try:
        _atomic_write_json(path, buffer_list)
    except Exception:
        # Best-effort: ignore persistence failures
        pass


class MetricsClient:
    """HTTP client that posts metrics to the collector and buffers failures."""

    def __init__(self, server_url, agent_id, buffer_size=100, verify_ssl=False, buffer_path: Path = None):
        self.server_url = server_url.rstrip('/')
        self.agent_id = agent_id
        self.buffer_size = int(buffer_size)
        # Determine buffer path
        self.buffer_path = Path(buffer_path) if buffer_path else (DEFAULT_STORAGE_DIR / 'metrics_buffer.json')

        # Load persisted buffer (best-effort)
        existing = load_buffer_list(self.buffer_path, self.buffer_size)
        self.buffer = deque(existing, maxlen=self.buffer_size)

        self.session = requests.Session()
        self.session.verify = verify_ssl

    def send_metrics(self, metrics_dict):
        """POST metrics to the collector. Uses exponential backoff + jitter on transient failures.

        If all attempts fail, the payload is appended to the persistent buffer.
        """
        payload = {
            "agent_id": self.agent_id,
            "timestamp": int(time.time()),
            "metrics": metrics_dict,
        }

        max_retries = int(os.getenv('OBSERVER_SEND_RETRIES', '3'))
        base = float(os.getenv('OBSERVER_BACKOFF_BASE', '1'))

        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.post(
                    f"{self.server_url}/api/metrics",
                    json=payload,
                    timeout=5,
                )
                if response.status_code == 200:
                    print("✅ Metrics sent")
                    try:
                        self.flush_buffer()
                    finally:
                        save_buffer_list(self.buffer_path, list(self.buffer))
                    return True

                # For 4xx we don't retry except maybe 429, but keep simple: retry if server error
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    print(f"⚠️  Server returned {response.status_code}; dropping payload")
                    return False

                print(f"⚠️  Server returned {response.status_code}; will retry (attempt {attempt})")

            except requests.RequestException as exc:
                print(f"⚠️  Network error: {exc}; attempt {attempt}")

            # Backoff before next attempt (if not last)
            if attempt < max_retries:
                backoff = base * (2 ** (attempt - 1))
                jitter = random.uniform(0, backoff * 0.5)
                sleep_for = backoff + jitter
                time.sleep(sleep_for)

        # All attempts failed; buffer payload
        print("⚠️  All retries failed; buffering payload")
        self.buffer.append(payload)
        save_buffer_list(self.buffer_path, list(self.buffer))
        return False

    def flush_buffer(self):
        """Attempt to resend up to the last 10 buffered metrics."""
        if not self.buffer:
            return
        to_send = list(self.buffer)[-10:]
        removed_any = False
        for payload in to_send:
            try:
                r = self.session.post(
                    f"{self.server_url}/api/metrics",
                    json=payload,
                    timeout=5,
                )
                if r.status_code == 200:
                    try:
                        self.buffer.remove(payload)
                        removed_any = True
                    except ValueError:
                        pass
            except requests.RequestException:
                # Keep payload in buffer for next attempt
                pass

        if removed_any:
            save_buffer_list(self.buffer_path, list(self.buffer))


def main():
    """Entry point for the agent CLI.

    Reads configuration from environment or `.env` and runs the collection
    loop until interrupted.
    """
    load_dotenv()
    server = os.getenv('OBSERVER_SERVER')
    env_agent = os.getenv('OBSERVER_AGENT_ID')
    interval = int(os.getenv('OBSERVER_INTERVAL', '2'))
    buffer_size = int(os.getenv('OBSERVER_BUFFER_SIZE', '100'))
    verify_ssl = os.getenv('OBSERVER_VERIFY_SSL', 'false').lower() in ('true', '1')

    # Storage paths
    storage_dir = Path(os.getenv('OBSERVER_STORAGE_DIR', DEFAULT_STORAGE_DIR))
    storage_dir.mkdir(parents=True, exist_ok=True)
    uuid_path = storage_dir / 'agent.uuid'
    buffer_path = storage_dir / 'metrics_buffer.json'

    if env_agent:
        agent_id = env_agent
    else:
        agent_id = load_or_create_uuid(uuid_path)

    if not server:
        print("ERROR: OBSERVER_SERVER not set in .env")
        raise SystemExit(1)

    # Configure logging
    logging.basicConfig(level=os.getenv('OBSERVER_LOG_LEVEL', 'INFO'))
    logger = logging.getLogger('observer-agent')

    collector = MetricsCollector()
    client = MetricsClient(server, agent_id, buffer_size=buffer_size, verify_ssl=verify_ssl, buffer_path=buffer_path)

    print(f"🚀 Starting agent: {agent_id}")
    print(f"📍 Server: {server}")
    print(f"⏱️  Interval: {interval}s")

    try:
        while True:
            # Metric collection: non-fatal, skip this cycle on failure
            try:
                metrics = collector.collect()
            except Exception:
                logger.exception('Failed to collect metrics; skipping this cycle')
                time.sleep(interval)
                continue

            print(json.dumps({"agent_id": agent_id, "metrics": metrics, "ts": int(time.time())}))

            # Send metrics; network errors are handled inside MetricsClient,
            # but guard against unexpected exceptions here.
            try:
                client.send_metrics(metrics)
            except Exception:
                logger.exception('Unexpected error while sending metrics; payload buffered if possible')

            time.sleep(interval)

    except KeyboardInterrupt as exc:
        print("\n👋 Shutting down gracefully")
        raise SystemExit(0) from exc
    except Exception:
        logger.exception('Unexpected fatal error; exiting')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
