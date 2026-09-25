#!/usr/bin/env python3
"""
Cyber HUD - Lightweight VPS HTTP Agent
A zero-dependency standalone status server for Linux VPS.
Usage:
    python3 mini_agent.py [PORT]
Default port is 9876.
"""

import sys
import json
import time
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9876

class MetricsCollector:
    last_cpu = None

    @classmethod
    def get_cpu(cls):
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            fields = [int(x) for x in re.findall(r'\d+', line)[:7]]
            total = sum(fields)
            idle = fields[3] + fields[4]
            busy = total - idle
            if cls.last_cpu:
                prev_total, prev_busy = cls.last_cpu
                dt = total - prev_total
                db = busy - prev_busy
                cls.last_cpu = (total, busy)
                if dt > 0:
                    return round((db / dt) * 100.0, 1)
            cls.last_cpu = (total, busy)
            return 0.0
        except Exception:
            return 0.0

    @classmethod
    def get_memory(cls):
        try:
            with open("/proc/meminfo", "r") as f:
                content = f.read()
            t = int(re.search(r'MemTotal:\s+(\d+)', content).group(1))
            a_match = re.search(r'MemAvailable:\s+(\d+)', content)
            a = int(a_match.group(1)) if a_match else int(re.search(r'MemFree:\s+(\d+)', content).group(1))
            used = max(0, t - a)
            return {
                "mem_percent": round((used / t) * 100.0, 1),
                "mem_used_gb": round(used / (1024 * 1024), 2),
                "mem_total_gb": round(t / (1024 * 1024), 2)
            }
        except Exception:
            return {"mem_percent": 0.0, "mem_used_gb": 0.0, "mem_total_gb": 0.0}

class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/", "/status"]:
            cpu = MetricsCollector.get_cpu()
            mem = MetricsCollector.get_memory()
            payload = {
                "status": "ONLINE",
                "cpu": cpu,
                "mem": mem["mem_percent"],
                "mem_used_gb": mem["mem_used_gb"],
                "mem_total_gb": mem["mem_total_gb"],
                "server_time": time.time()
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence access logs
        return

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), StatusHandler)
    print(f"[Cyber HUD Agent] Listening on 0.0.0.0:{PORT} ...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping agent...")
        server.server_close()
