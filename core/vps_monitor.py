import time
import socket
import re
from PyQt6.QtCore import QThread, pyqtSignal

class VPSMonitorThread(QThread):
    vps_metrics_updated = pyqtSignal(dict)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.running = True
        self.ssh_client = None
        self.last_cpu_stat = None

    def _get_vps_config(self):
        vps_cfg = self.config_manager.get("vps", {})
        return vps_cfg

    def measure_latency(self, host, port=22, timeout=1.5):
        """Measure true network RTT (Round Trip Time) in milliseconds."""
        if not host:
            return None
        # 1. Try TCP handshake ping (pure python, socket SYN-ACK)
        try:
            t0 = time.perf_counter()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, int(port)))
            s.close()
            latency = (time.perf_counter() - t0) * 1000.0
            return max(0.1, latency)
        except Exception:
            pass

        # 2. Fallback to system ICMP ping if TCP port was closed or filtered
        try:
            import subprocess
            res = subprocess.run(
                ['ping', str(host), '-n', '1', '-w', str(int(timeout * 1000))],
                capture_output=True,
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            out = res.stdout
            if '<1ms' in out or '< 1ms' in out or '<1 ms' in out:
                return 0.5
            m = re.search(r'(?:time|时间)[=<]?\s*(\d+)\s*ms', out, re.IGNORECASE)
            if m:
                return float(m.group(1))
            m2 = re.search(r'(\d+)\s*ms', out)
            if m2:
                return float(m2.group(1))
        except Exception:
            pass

        return None

    def query_http(self, url, timeout=3.0):
        """Query lightweight HTTP endpoint."""
        import requests
        start = time.time()
        resp = requests.get(url, timeout=timeout)
        latency = (time.time() - start) * 1000.0
        if resp.status_code == 200:
            data = resp.json()
            return {
                "status": "ONLINE",
                "ping_ms": round(latency, 1),
                "cpu_percent": float(data.get("cpu", data.get("cpu_percent", 0))),
                "mem_percent": float(data.get("mem", data.get("mem_percent", 0))),
                "mem_used_gb": float(data.get("mem_used_gb", 0)),
                "mem_total_gb": float(data.get("mem_total_gb", 0)),
                "raw": data
            }
        return {"status": "ERROR", "ping_ms": None}

    def query_ssh(self, host, port, username, password=None, key_path=None, timeout=4.0):
        """Query remote VPS via SSH without needing any software installed on VPS."""
        import paramiko

        if self.ssh_client is None:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                if key_path:
                    client.connect(host, port=port, username=username, key_filename=key_path, timeout=timeout)
                else:
                    client.connect(host, port=port, username=username, password=password, timeout=timeout)
                self.ssh_client = client
            except Exception as e:
                self.ssh_client = None
                return {
                    "status": "OFFLINE",
                    "error": str(e),
                    "ping_ms": None
                }

        # Query /proc/stat and memory via free -b (procps standard)
        cmd = "grep 'cpu ' /proc/stat; free -b 2>/dev/null || grep -E 'MemTotal|MemFree|Buffers|Cached|SReclaimable' /proc/meminfo"
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd, timeout=timeout)
            output = stdout.read().decode("utf-8", errors="ignore")
            
            # Parse CPU
            cpu_percent = 0.0
            cpu_line = re.search(r'cpu\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', output)
            if cpu_line:
                fields = [int(x) for x in cpu_line.groups()]
                user, nice, sys, idle, iowait, irq, softirq = fields
                total = sum(fields)
                busy = total - idle - iowait
                if self.last_cpu_stat:
                    prev_total, prev_busy = self.last_cpu_stat
                    d_total = total - prev_total
                    d_busy = busy - prev_busy
                    if d_total > 0:
                        cpu_percent = max(0.0, min(100.0, (d_busy / d_total) * 100.0))
                self.last_cpu_stat = (total, busy)

            # Parse Memory (aligned with Linux procps / free -m / panel calculations)
            mem_total_gb = 0.0
            mem_used_gb = 0.0
            mem_used_mb = 0.0
            mem_total_mb = 0.0
            mem_percent = 0.0

            mem_line = re.search(r'Mem:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', output)
            if mem_line:
                tot_b = int(mem_line.group(1))
                used_b = int(mem_line.group(2))
                if tot_b > 0:
                    mem_total_mb = round(tot_b / (1024.0 * 1024.0), 1)
                    mem_used_mb = round(used_b / (1024.0 * 1024.0), 1)
                    mem_total_gb = round(tot_b / (1024.0 * 1024.0 * 1024.0), 2)
                    mem_used_gb = round(used_b / (1024.0 * 1024.0 * 1024.0), 2)
                    mem_percent = round((used_b / tot_b) * 100.0, 1)
            else:
                total_kb = re.search(r'MemTotal:\s+(\d+)', output)
                free_kb = re.search(r'MemFree:\s+(\d+)', output)
                buf_kb = re.search(r'Buffers:\s+(\d+)', output)
                cached_kb = re.search(r'Cached:\s+(\d+)', output)
                srec_kb = re.search(r'SReclaimable:\s+(\d+)', output)

                if total_kb:
                    t_kb = int(total_kb.group(1))
                    f_kb = int(free_kb.group(1)) if free_kb else 0
                    b_kb = int(buf_kb.group(1)) if buf_kb else 0
                    c_kb = int(cached_kb.group(1)) if cached_kb else 0
                    s_kb = int(srec_kb.group(1)) if srec_kb else 0
                    
                    used_kb = max(0, t_kb - f_kb - b_kb - c_kb - s_kb)
                    mem_total_mb = round(t_kb / 1024.0, 1)
                    mem_used_mb = round(used_kb / 1024.0, 1)
                    mem_total_gb = round(t_kb / (1024.0 * 1024.0), 2)
                    mem_used_gb = round(used_kb / (1024.0 * 1024.0), 2)
                    if t_kb > 0:
                        mem_percent = round((used_kb / t_kb) * 100.0, 1)

            return {
                "status": "ONLINE",
                "cpu_percent": round(cpu_percent, 1),
                "mem_percent": mem_percent,
                "mem_used_gb": mem_used_gb,
                "mem_total_gb": mem_total_gb,
                "mem_used_mb": mem_used_mb,
                "mem_total_mb": mem_total_mb
            }
        except Exception as e:
            # Drop connection on error so next cycle reconnects
            try:
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None
            return {
                "status": "ERROR",
                "error": str(e),
                "ping_ms": None
            }

    def run(self):
        while self.running:
            cfg = self._get_vps_config()
            if not cfg.get("enabled", True):
                time.sleep(1.0)
                continue

            vps_type = cfg.get("type", "ping").lower()
            host = cfg.get("host", "").strip()
            port = int(cfg.get("port", 22))
            interval = max(2, int(cfg.get("refresh_interval_s", 5)))
            
            result = {
                "name": cfg.get("name", "VPS-NODE"),
                "status": "STANDBY",
                "type": vps_type,
                "ping_ms": None,
                "cpu_percent": 0.0,
                "mem_percent": 0.0,
                "mem_used_gb": 0.0,
                "mem_total_gb": 0.0,
                "timestamp": time.time()
            }

            if not host:
                result["status"] = "UNCONFIGURED"
                self.vps_metrics_updated.emit(result)
                time.sleep(interval)
                continue

            try:
                # 1. Measure true network RTT (ICMP / TCP SYN roundtrip)
                rtt = self.measure_latency(host, port)
                if rtt is not None:
                    result["ping_ms"] = round(rtt, 1)

                # 2. Query detailed metrics based on vps_type
                if vps_type == "ssh":
                    ssh_res = self.query_ssh(
                        host=host,
                        port=port,
                        username=cfg.get("username", "root"),
                        password=cfg.get("password", ""),
                        key_path=cfg.get("key_path", "")
                    )
                    result.update(ssh_res)
                    if ssh_res.get("status") == "ONLINE" and rtt is not None:
                        result["ping_ms"] = round(rtt, 1)

                elif vps_type == "http":
                    http_url = cfg.get("http_url", "")
                    if http_url:
                        http_res = self.query_http(http_url)
                        result.update(http_res)
                        if rtt is not None:
                            result["ping_ms"] = round(rtt, 1)
                    else:
                        result["status"] = "UNCONFIGURED"

                else: # ping
                    if rtt is not None:
                        result["status"] = "ONLINE"
                        result["ping_ms"] = round(rtt, 1)
                    else:
                        result["status"] = "OFFLINE"

            except Exception as e:
                result["status"] = "OFFLINE"
                result["error"] = str(e)

            self.vps_metrics_updated.emit(result)
            # Sleep in slices so stop() returns immediately without hanging
            for _ in range(int(interval * 10)):
                if not self.running:
                    break
                time.sleep(0.1)

    def stop(self):
        self.running = False
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
        self.wait(2000)
