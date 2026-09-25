import time
import warnings
warnings.filterwarnings("ignore")
import psutil
from PyQt6.QtCore import QThread, pyqtSignal

# NVML initialization attempt
HAS_NVML = False
try:
    import pynvml
    pynvml.nvmlInit()
    HAS_NVML = True
except Exception as e:
    print(f"[LocalMonitor] NVML init failed or not available: {e}")

class LocalMonitorThread(QThread):
    metrics_updated = pyqtSignal(dict)

    def __init__(self, interval_ms=1000, parent=None):
        super().__init__(parent)
        self.interval_sec = max(0.2, interval_ms / 1000.0)
        self.running = True
        self.last_net_bytes = None
        self.last_net_time = None
        self.nvml_device = None
        self.gpu_name = "NVIDIA GPU"
        self._init_gpu()

    def _init_gpu(self):
        global HAS_NVML
        if HAS_NVML:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                if device_count > 0:
                    self.nvml_device = pynvml.nvmlDeviceGetHandleByIndex(0)
                    raw_name = pynvml.nvmlDeviceGetName(self.nvml_device)
                    if isinstance(raw_name, bytes):
                        raw_name = raw_name.decode("utf-8")
                    self.gpu_name = raw_name
            except Exception as e:
                print(f"[LocalMonitor] Failed to get GPU handle: {e}")
                self.nvml_device = None

    def get_gpu_metrics(self):
        if not self.nvml_device:
            return {
                "name": "GPU N/A",
                "temp": 0,
                "util": 0,
                "mem_used_gb": 0.0,
                "mem_total_gb": 0.0,
                "available": False
            }
        try:
            temp = pynvml.nvmlDeviceGetTemperature(self.nvml_device, pynvml.NVML_TEMPERATURE_GPU)
            rates = pynvml.nvmlDeviceGetUtilizationRates(self.nvml_device)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.nvml_device)
            return {
                "name": self.gpu_name,
                "temp": int(temp),
                "util": int(rates.gpu),
                "mem_used_gb": round(mem_info.used / (1024 ** 3), 1),
                "mem_total_gb": round(mem_info.total / (1024 ** 3), 1),
                "available": True
            }
        except Exception as e:
            return {
                "name": self.gpu_name,
                "temp": 0,
                "util": 0,
                "mem_used_gb": 0.0,
                "mem_total_gb": 0.0,
                "available": False
            }

    def run(self):
        # Primer psutil cpu_percent
        psutil.cpu_percent(interval=None)
        
        while self.running:
            start_time = time.time()
            
            # 1. CPU
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # 2. Memory
            mem = psutil.virtual_memory()
            ram_used_gb = mem.used / (1024 ** 3)
            ram_total_gb = mem.total / (1024 ** 3)
            ram_percent = mem.percent
            
            # 3. Network Speed
            net_io = psutil.net_io_counters()
            curr_time = time.time()
            upload_speed = 0.0
            download_speed = 0.0
            
            if self.last_net_bytes is not None and self.last_net_time is not None:
                dt = curr_time - self.last_net_time
                if dt > 0:
                    sent_bytes = net_io.bytes_sent - self.last_net_bytes[0]
                    recv_bytes = net_io.bytes_recv - self.last_net_bytes[1]
                    upload_speed = max(0.0, sent_bytes / dt)
                    download_speed = max(0.0, recv_bytes / dt)
            
            self.last_net_bytes = (net_io.bytes_sent, net_io.bytes_recv)
            self.last_net_time = curr_time
            
            # 4. GPU (RTX 5060 Ti)
            gpu_data = self.get_gpu_metrics()
            
            metrics = {
                "cpu": {
                    "percent": round(cpu_percent, 1),
                },
                "ram": {
                    "percent": round(ram_percent, 1),
                    "used_gb": round(ram_used_gb, 1),
                    "total_gb": round(ram_total_gb, 1)
                },
                "gpu": gpu_data,
                "net": {
                    "up_bps": upload_speed,
                    "down_bps": download_speed
                },
                "timestamp": curr_time
            }
            
            self.metrics_updated.emit(metrics)
            
            # Sleep remainder of interval in 100ms slices for responsive stop
            elapsed = time.time() - start_time
            sleep_time = max(0.05, self.interval_sec - elapsed)
            slices = int(sleep_time / 0.1)
            for _ in range(slices):
                if not self.running:
                    break
                time.sleep(0.1)
            rem = sleep_time - (slices * 0.1)
            if rem > 0 and self.running:
                time.sleep(rem)

    def stop(self):
        self.running = False
        self.wait(1500)
        global HAS_NVML
        if HAS_NVML:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass

