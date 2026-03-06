#!/usr/bin/env python3
import os
import time
import socket
import json
from collections import deque

from dotenv import load_dotenv
import requests
import psutil


class MetricsCollector:
    def __init__(self):
        net_io = psutil.net_io_counters()
        self.last_net_in = net_io.bytes_recv
        self.last_net_out = net_io.bytes_sent
        self.last_time = time.time()

    def collect(self):
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


class MetricsClient:
    def __init__(self, server_url, agent_id, buffer_size=100, verify_ssl=False):
        self.server_url = server_url.rstrip('/')
        self.agent_id = agent_id
        self.buffer = deque(maxlen=buffer_size)
        self.session = requests.Session()
        self.session.verify = verify_ssl

    def send_metrics(self, metrics_dict):
        payload = {
            "agent_id": self.agent_id,
            "timestamp": int(time.time()),
            "metrics": metrics_dict,
        }

        try:
            response = self.session.post(f"{self.server_url}/api/metrics", json=payload, timeout=5)
            if response.status_code == 200:
                print("✅ Metrics sent")
                self.flush_buffer()
                return True
            else:
                print(f"⚠️  Server returned {response.status_code}")
                self.buffer.append(payload)
                return False

        except requests.Timeout:
            print("⚠️  Request timeout")
            self.buffer.append(payload)
            return False
        except requests.RequestException as e:
            print(f"⚠️  Network error: {e}")
            self.buffer.append(payload)
            return False

    def flush_buffer(self):
        if not self.buffer:
            return

        to_send = list(self.buffer)[-10:]
        for payload in to_send:
            try:
                r = self.session.post(f"{self.server_url}/api/metrics", json=payload, timeout=5)
                if r.status_code == 200:
                    try:
                        self.buffer.remove(payload)
                    except ValueError:
                        pass
            except Exception:
                pass


def main():
    load_dotenv()
    SERVER = os.getenv('OBSERVER_SERVER')
    AGENT_ID = os.getenv('OBSERVER_AGENT_ID') or socket.gethostname()
    INTERVAL = int(os.getenv('OBSERVER_INTERVAL', '2'))
    BUFFER_SIZE = int(os.getenv('OBSERVER_BUFFER_SIZE', '100'))
    VERIFY_SSL = os.getenv('OBSERVER_VERIFY_SSL', 'false').lower() in ('true', '1')

    if not SERVER:
        print("ERROR: OBSERVER_SERVER not set in .env")
        raise SystemExit(1)

    collector = MetricsCollector()
    client = MetricsClient(SERVER, AGENT_ID, buffer_size=BUFFER_SIZE, verify_ssl=VERIFY_SSL)

    print(f"🚀 Starting agent: {AGENT_ID}")
    print(f"📍 Server: {SERVER}")
    print(f"⏱️  Interval: {INTERVAL}s")

    try:
        while True:
            metrics = collector.collect()
            print(json.dumps({"agent_id": AGENT_ID, "metrics": metrics, "ts": int(time.time())}))
            client.send_metrics(metrics)
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully")
        raise SystemExit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


if __name__ == '__main__':
    main()
