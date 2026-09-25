import sys
import ctypes
import warnings
warnings.filterwarnings("ignore")

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu,
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox,
    QDialogButtonBox, QPushButton, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QAction, QIcon, QFont

from ui.cyber_painter import CyberPainter, hex_to_qcolor
from ui.widgets.cyber_mech_bar import CyberMechBar
from ui.widgets.stat_row import StatRow
from ui.widgets.cyber_net_row import CyberNetRow

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

def format_speed(bps):
    """Format bytes per second into human readable string."""
    if bps < 1024:
        return f"{bps:.0f} B/s"
    elif bps < 1024 * 1024:
        return f"{bps / 1024:.1f} KB/s"
    elif bps < 1024 * 1024 * 1024:
        return f"{bps / (1024 * 1024):.2f} MB/s"
    else:
        return f"{bps / (1024 * 1024 * 1024):.2f} GB/s"

class VPSConfigDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("VPS 探针设置 // REMOTE NODE CONFIG")
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #0E131F;
                color: #FFFFFF;
                border: 1px solid #00F3FF;
            }
            QLabel {
                color: #00F3FF;
                font-family: 'Consolas', monospace;
                font-size: 13px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #161F33;
                color: #FFFFFF;
                border: 1px solid #2A3E66;
                padding: 6px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #00F3FF;
            }
            QPushButton {
                background-color: #1A2640;
                color: #00F3FF;
                border: 1px solid #00F3FF;
                padding: 7px 16px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #00F3FF;
                color: #0E131F;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        vps_cfg = self.config_manager.get("vps", {})
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        
        self.combo_type = QComboBox()
        self.combo_type.addItems(["SSH (直连探针, 免装服务端)", "HTTP (API 模式)", "PING (TCP 延迟模式)"])
        current_type = vps_cfg.get("type", "ssh").lower()
        if current_type == "http":
            self.combo_type.setCurrentIndex(1)
        elif current_type == "ping":
            self.combo_type.setCurrentIndex(2)
        else:
            self.combo_type.setCurrentIndex(0)
        form.addRow("探针模式:", self.combo_type)

        self.edit_name = QLineEdit(vps_cfg.get("name", "VPS-NODE-01"))
        form.addRow("节点名称:", self.edit_name)

        self.edit_host = QLineEdit(vps_cfg.get("host", ""))
        self.edit_host.setPlaceholderText("例如: 123.45.67.89 或域名")
        form.addRow("主机/IP:", self.edit_host)

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(int(vps_cfg.get("port", 22)))
        form.addRow("SSH端口:", self.spin_port)

        self.edit_user = QLineEdit(vps_cfg.get("username", "root"))
        form.addRow("SSH用户:", self.edit_user)

        self.edit_pass = QLineEdit(vps_cfg.get("password", ""))
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pass.setPlaceholderText("SSH密码 (若用密钥留空)")
        form.addRow("SSH密码:", self.edit_pass)

        self.edit_key = QLineEdit(vps_cfg.get("key_path", ""))
        self.edit_key.setPlaceholderText("私钥路径 (选填, 如 id_rsa)")
        form.addRow("私钥路径:", self.edit_key)

        self.edit_http = QLineEdit(vps_cfg.get("http_url", ""))
        self.edit_http.setPlaceholderText("http://vps-ip:9876/status")
        form.addRow("HTTP接口:", self.edit_http)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save_and_close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _save_and_close(self):
        idx = self.combo_type.currentIndex()
        vps_type = "ssh" if idx == 0 else ("http" if idx == 1 else "ping")
        
        self.config_manager.set("vps", "type", vps_type)
        self.config_manager.set("vps", "name", self.edit_name.text().strip())
        self.config_manager.set("vps", "host", self.edit_host.text().strip())
        self.config_manager.set("vps", "port", self.spin_port.value())
        self.config_manager.set("vps", "username", self.edit_user.text().strip())
        self.config_manager.set("vps", "password", self.edit_pass.text())
        self.config_manager.set("vps", "key_path", self.edit_key.text().strip())
        self.config_manager.set("vps", "http_url", self.edit_http.text().strip())
        self.accept()

class CyberHUDWindow(QWidget):
    position_changed = pyqtSignal(int, int)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.drag_position = None
        self.is_in_drag_mode = False

        self._init_window_flags()
        self._init_ui()
        self._load_saved_geometry()

        # Drag mode auto-restore timer
        self.drag_mode_timer = QTimer(self)
        self.drag_mode_timer.setSingleShot(True)
        self.drag_mode_timer.timeout.connect(self.exit_drag_mode)

    def _init_window_flags(self):
        self.setWindowTitle("CyberHUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def _init_ui(self):
        w_cfg = self.config_manager.get("window", {})
        self.setFixedWidth(w_cfg.get("width", 330))

        # Overall window stays 100% solid opacity so texts & bars are always crisp and non-faded
        self.setWindowOpacity(1.0)

        # Main Layout (增加垂直行间距：每一条隔开一点)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 2)
        
        self.lbl_title = QLabel("SYS.MON // MECHA-HUD")
        self.lbl_title.setStyleSheet("""
            QLabel {
                color: #00F3FF;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 14px;
                letter-spacing: 2px;
            }
        """)
        header_layout.addWidget(self.lbl_title)
        
        header_layout.addStretch()

        self.lbl_status_led = QLabel("● DESKTOP")
        self.lbl_status_led.setStyleSheet("""
            QLabel {
                color: #00FF88;
                font-family: 'Consolas', monospace;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        header_layout.addWidget(self.lbl_status_led)
        self.main_layout.addLayout(header_layout)

        # 1. CPU (霓虹电粉 #FF007F)
        self.bar_cpu = CyberMechBar(tag="CPU", rail_color="#FF007F", blade_color="#FF007F")
        self.main_layout.addWidget(self.bar_cpu)

        # 2. RAM (神经电紫 #B026FF)
        self.bar_ram = CyberMechBar(tag="RAM", rail_color="#B026FF", blade_color="#B026FF")
        self.main_layout.addWidget(self.bar_ram)

        # 3. GPU (矩阵高能绿 #00FF66)
        self.bar_gpu = CyberMechBar(tag="RTX 5060 Ti", rail_color="#00FF66", blade_color="#00FF66")
        self.main_layout.addWidget(self.bar_gpu)

        # 4. Network (Fixed-column speed indicators)
        self.row_net = CyberNetRow(tag="NET", color="#00F3FF")
        self.main_layout.addWidget(self.row_net)

        # Divider for VPS Node
        self.vps_divider = QLabel("── [REMOTE NODE: VPS] ──")
        self.vps_divider.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vps_divider.setStyleSheet("""
            QLabel {
                color: #FF0055;
                font-family: 'Consolas', monospace;
                font-weight: bold;
                font-size: 11px;
                margin-top: 4px;
                margin-bottom: 2px;
            }
        """)
        self.main_layout.addWidget(self.vps_divider)

        # VPS Container Widget
        self.vps_widget = QWidget()
        vps_layout = QVBoxLayout(self.vps_widget)
        vps_layout.setContentsMargins(0, 0, 0, 0)
        vps_layout.setSpacing(10)

        self.row_vps_status = StatRow(tag="VPS", color="#00F3FF", show_bar=False)
        vps_layout.addWidget(self.row_vps_status)

        self.bar_vps_cpu = CyberMechBar(tag="V-CPU", rail_color="#FF3366", blade_color="#FF3366")
        vps_layout.addWidget(self.bar_vps_cpu)

        self.bar_vps_ram = CyberMechBar(tag="V-RAM", rail_color="#FF3366", blade_color="#FF3366")
        vps_layout.addWidget(self.bar_vps_ram)

        self.main_layout.addWidget(self.vps_widget)

    def _load_saved_geometry(self):
        w_cfg = self.config_manager.get("window", {})
        x = w_cfg.get("x", 80)
        y = w_cfg.get("y", 80)
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(80, self.apply_desktop_mode)

    def set_bg_opacity(self, val):
        """Adjusts the background frame opacity while keeping text and bars 100% solid."""
        val = max(0.0, min(1.0, float(val)))
        self.config_manager.set("window", "bg_opacity", round(val, 2))
        self.update()

    def apply_desktop_mode(self):
        """Pin to bottom once and enable click-through without repeating timers."""
        self.send_to_bottom()
        self.enable_click_through()

    def enable_click_through(self):
        """Enable Windows Click-Through (clicks pass completely through)."""
        hwnd = int(self.winId())
        extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            extended_style | WS_EX_TRANSPARENT | WS_EX_LAYERED
        )
        self.lbl_status_led.setText("● DESKTOP")
        self.lbl_status_led.setStyleSheet("color: #00FF88; font-family: 'Consolas'; font-size: 11px;")

    def send_to_bottom(self):
        """Pins the window to the bottom level of all normal windows."""
        hwnd = int(self.winId())
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_BOTTOM,
            0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
        )

    # --- Temporary Drag Mode (triggered only from Tray) ---
    def enter_drag_mode(self, duration_sec=15):
        """Temporarily allow dragging so the user can move the window."""
        self.is_in_drag_mode = True
        hwnd = int(self.winId())
        extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, extended_style & ~WS_EX_TRANSPARENT)
        self.lbl_status_led.setText("● 拖拽移动中...")
        self.lbl_status_led.setStyleSheet("color: #FFB800; font-family: 'Consolas'; font-size: 11px;")
        self.drag_mode_timer.start(duration_sec * 1000)

    def exit_drag_mode(self):
        """Restore permanent pass-through and bottom layer."""
        self.is_in_drag_mode = False
        self.drag_mode_timer.stop()
        self.apply_desktop_mode()

    # --- Mouse Events (active only when in temporary drag mode) ---
    def mousePressEvent(self, event):
        if self.is_in_drag_mode and event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_in_drag_mode and event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.is_in_drag_mode and event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            self._magnetic_snap()
            self._save_position()
            self.exit_drag_mode()
            event.accept()

    def _magnetic_snap(self, snap_dist=25):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        pos = self.pos()
        x = pos.x()
        y = pos.y()
        w = self.width()
        h = self.height()

        if abs(x - geo.left()) < snap_dist:
            x = geo.left() + 4
        elif abs(x + w - geo.right()) < snap_dist:
            x = geo.right() - w - 4

        if abs(y - geo.top()) < snap_dist:
            y = geo.top() + 4
        elif abs(y + h - geo.bottom()) < snap_dist:
            y = geo.bottom() - h - 4

        self.move(x, y)

    def _save_position(self):
        pos = self.pos()
        self.config_manager.set("window", "x", pos.x())
        self.config_manager.set("window", "y", pos.y())

    def moveEvent(self, event):
        super().moveEvent(event)
        self.position_changed.emit(self.x(), self.y())

    # --- Metrics Updates ---
    def update_local_metrics(self, data):
        # 1. CPU
        cpu_p = data["cpu"]["percent"]
        self.bar_cpu.update_data(percent=cpu_p, value_text=f"{round(cpu_p)}%")

        # 2. RAM
        ram_p = data["ram"]["percent"]
        ram_used = data["ram"]["used_gb"]
        ram_tot = data["ram"]["total_gb"]
        self.bar_ram.update_data(
            percent=ram_p,
            value_text=f"{round(ram_p)}%",
            detail_text=f"{ram_used:.1f}G / {ram_tot:.1f}G"
        )

        # 3. GPU
        gpu = data["gpu"]
        if gpu.get("available", False):
            temp = gpu["temp"]
            util = gpu["util"]
            self.bar_gpu.update_data(
                percent=util,
                value_text=f"{round(util)}%",
                detail_text=f"{temp}°C"
            )
        else:
            self.bar_gpu.update_data(percent=0, value_text="OFF", detail_text="OFFLINE")

        # 4. Net (淡蓝色统一数字，固定列不抖动)
        up_s = format_speed(data["net"]["up_bps"])
        down_s = format_speed(data["net"]["down_bps"])
        self.row_net.update_speeds(up_s, down_s)

    def update_vps_metrics(self, data):
        status = data.get("status", "STANDBY")
        name = data.get("name", "VPS")
        ping = data.get("ping_ms")

        if ping is not None:
            ping_str = "<1ms" if ping < 1.0 else f"{round(ping)}ms"
        else:
            ping_str = "--"
        status_color = "#00FF88" if status == "ONLINE" else ("#FFB800" if status == "STANDBY" else "#FF0055")
        
        self.row_vps_status.set_tag_text(f"[{name}]")
        self.row_vps_status.update_stat(status, detail_text=f"RTT: {ping_str}", custom_color="#00F3FF")

        v_cpu = data.get("cpu_percent", 0.0)
        self.bar_vps_cpu.update_data(percent=v_cpu, value_text=f"{round(v_cpu)}%")

        v_ram = data.get("mem_percent", 0.0)
        v_used_mb = data.get("mem_used_mb", 0.0)
        v_tot_mb = data.get("mem_total_mb", 0.0)
        v_used_gb = data.get("mem_used_gb", 0.0)
        v_tot_gb = data.get("mem_total_gb", 0.0)

        if v_tot_mb > 0 and v_tot_mb < 1500:
            detail = f"{round(v_used_mb)}M / {round(v_tot_mb)}M"
        elif v_tot_gb > 0:
            detail = f"{v_used_gb:.1f}G / {v_tot_gb:.1f}G"
        else:
            detail = ""
        self.bar_vps_ram.update_data(percent=v_ram, value_text=f"{round(v_ram)}%", detail_text=detail)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = QRectF(0, 0, self.width(), self.height())
        bg_opacity = float(self.config_manager.get("window", {}).get("bg_opacity", 0.65))
        CyberPainter.draw_cyber_frame(
            painter,
            rect,
            bg_color="#0A0E18",
            border_color="#00F3FF",
            cut=16.0,
            bg_opacity=bg_opacity
        )

    def open_vps_config(self):
        dlg = VPSConfigDialog(self.config_manager, self)
        dlg.exec()
