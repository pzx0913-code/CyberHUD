import ctypes
import warnings
warnings.filterwarnings("ignore")

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox,
    QAbstractSpinBox, QDialogButtonBox, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QBrush, QPen, QFont, QFontMetrics

from ui.cyber_painter import CyberPainter, Theme, hex_to_qcolor
from ui.widgets.wave_chart import TelemetryHeroCard
from ui.widgets.cyber_mech_bar import CyberMechBar
from ui.widgets.cyber_net_row import CyberNetRow
from ui.widgets.stat_row import StatRow

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010


def format_speed(bps):
    """Format bytes per second into compact fixed-precision string."""
    try:
        bps = max(0.0, float(bps))
    except Exception:
        bps = 0.0
    if bps < 1024:
        return f"{bps:.0f} B/s"
    elif bps < 1024 * 1024:
        kb = bps / 1024.0
        return f"{kb:.0f} KB/s" if kb >= 100.0 else f"{kb:.1f} KB/s"
    elif bps < 1024 * 1024 * 1024:
        mb = bps / (1024.0 * 1024.0)
        return f"{mb:.1f} MB/s" if mb >= 100.0 else f"{mb:.2f} MB/s"
    else:
        return f"{bps / (1024.0 * 1024.0 * 1024.0):.2f} GB/s"


def _clean_gpu_name(raw_name: str) -> str:
    """Shorten verbose vendor prefixes while keeping the actual hardware model."""
    if not raw_name:
        return "GPU"
    s = str(raw_name).strip()
    for prefix in ("NVIDIA GeForce ", "NVIDIA ", "AMD Radeon ", "Intel(R) ", "Intel "):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s or "GPU"


def _nonneg_float(val) -> float:
    """Convert a metric value to a non-negative float, defaulting to 0.0."""
    try:
        return max(0.0, float(val)) if val is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


class StatusDotBadge(QWidget):
    """Custom-painted 6px live status dot paired with crisp quiet label."""

    def __init__(self, text="穿透", dot_color=Theme.POSITIVE, text_color=Theme.TEXT_MUTED, parent=None):
        super().__init__(parent)
        self._text = text
        self._dot_color = dot_color
        self._text_color = text_color
        self.setFixedHeight(20)
        self._sync_width()

    def _sync_width(self):
        font = Theme.ui_font(12, QFont.Weight.Normal)
        w = QFontMetrics(font).horizontalAdvance(self._text) + 14
        self.setFixedWidth(max(38, w))

    def set_status(self, text: str, dot_color: str, text_color: str = Theme.TEXT_MUTED):
        self._text = text
        self._dot_color = dot_color
        self._text_color = text_color
        self._sync_width()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        font = Theme.ui_font(12, QFont.Weight.Normal)
        painter.setFont(font)

        tw = painter.fontMetrics().horizontalAdvance(self._text)
        dot_cx = w - tw - 6.0 - 3.0
        dot_cy = h * 0.5

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(hex_to_qcolor(self._dot_color, 255)))
        painter.drawEllipse(QPointF(dot_cx, dot_cy), 3.0, 3.0)

        painter.setPen(hex_to_qcolor(self._text_color, 255))
        painter.drawText(QRectF(0.0, 0.0, w, h), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)


class InstrumentComboBox(QComboBox):
    """QComboBox with a custom-painted crisp 1.5px vector chevron."""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(hex_to_qcolor(Theme.TEXT_SECONDARY, 255), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        cx = float(self.width()) - 15.0
        cy = float(self.height()) * 0.5
        painter.drawLine(QPointF(cx - 3.5, cy - 1.5), QPointF(cx, cy + 2.0))
        painter.drawLine(QPointF(cx, cy + 2.0), QPointF(cx + 3.5, cy - 1.5))


class VPSConfigDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("VPS 探针设置")
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #141518;
                color: #F4F4F6;
            }
            QLabel {
                color: #B0B5C0;
                font-family: 'MiSans', 'Microsoft YaHei UI', 'Segoe UI';
                font-size: 13px;
                font-weight: 400;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: rgba(255, 255, 255, 0.05);
                color: #F4F4F6;
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 8px;
                padding: 7px 10px;
                font-family: 'Segoe UI Variable Display', 'MiSans', 'Microsoft YaHei UI';
                font-size: 13px;
                selection-background-color: rgba(125, 180, 255, 0.25);
            }
            QComboBox {
                padding-right: 28px;
            }
            QSpinBox {
                padding-left: 7px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid rgba(125, 180, 255, 0.65);
                background-color: rgba(255, 255, 255, 0.07);
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1C21;
                color: #F4F4F6;
                border: 1px solid rgba(255, 255, 255, 0.12);
                selection-background-color: #262932;
                selection-color: #F4F4F6;
                outline: none;
            }
            QPushButton#primaryBtn {
                background-color: #E8EAEE;
                color: #111215;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-family: 'MiSans', 'Microsoft YaHei UI', 'Segoe UI';
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton#primaryBtn:hover {
                background-color: #FFFFFF;
            }
            QPushButton#primaryBtn:pressed {
                background-color: #D2D6DC;
            }
            QPushButton#secondaryBtn {
                background-color: rgba(255, 255, 255, 0.05);
                color: #B0B5C0;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 8px 18px;
                font-family: 'MiSans', 'Microsoft YaHei UI', 'Segoe UI';
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton#secondaryBtn:hover {
                background-color: rgba(255, 255, 255, 0.10);
                color: #F4F4F6;
                border: 1px solid rgba(255, 255, 255, 0.16);
            }
        """)
        self._init_ui()

    def _init_ui(self):
        vps_cfg = self.config_manager.get("vps", {})
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.combo_type = InstrumentComboBox()
        self.combo_type.addItems(["SSH 直连探针（免装服务端）", "HTTP 接口模式", "TCP / ICMP 延迟模式"])
        current_type = vps_cfg.get("type", "ssh").lower()
        if current_type == "http":
            self.combo_type.setCurrentIndex(1)
        elif current_type == "ping":
            self.combo_type.setCurrentIndex(2)
        else:
            self.combo_type.setCurrentIndex(0)
        form.addRow("探针模式", self.combo_type)

        self.edit_name = QLineEdit(vps_cfg.get("name", "VPS-NODE-01"))
        form.addRow("节点名称", self.edit_name)

        self.edit_host = QLineEdit(vps_cfg.get("host", ""))
        self.edit_host.setPlaceholderText("例如 123.45.67.89")
        form.addRow("主机 / IP", self.edit_host)

        self.spin_port = QSpinBox()
        self.spin_port.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_port.lineEdit().setTextMargins(0, 0, 0, 0)
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(int(vps_cfg.get("port", 22)))
        form.addRow("SSH 端口", self.spin_port)

        self.edit_user = QLineEdit(vps_cfg.get("username", "root"))
        form.addRow("SSH 用户", self.edit_user)

        self.edit_pass = QLineEdit(vps_cfg.get("password", ""))
        self.edit_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pass.setPlaceholderText("使用密钥可留空")
        form.addRow("SSH 密码", self.edit_pass)

        self.edit_key = QLineEdit(vps_cfg.get("key_path", ""))
        self.edit_key.setPlaceholderText("选填，例如 id_rsa")
        form.addRow("私钥路径", self.edit_key)

        self.edit_http = QLineEdit(vps_cfg.get("http_url", ""))
        self.edit_http.setPlaceholderText("http://ip:9876/status")
        form.addRow("HTTP 接口", self.edit_http)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("保存配置")
        ok_btn.setObjectName("primaryBtn")
        cancel_btn = btns.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("取消")
        cancel_btn.setObjectName("secondaryBtn")
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
        self.setWindowOpacity(1.0)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 14, 16, 16)
        self.main_layout.setSpacing(8)

        # 1. Quiet Header (20px)
        header_widget = QWidget()
        header_widget.setFixedHeight(20)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.lbl_title = QLabel("本机")
        self.lbl_title.setFont(Theme.ui_font(12, QFont.Weight.Medium))
        self.lbl_title.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        header_layout.addWidget(self.lbl_title)

        header_layout.addStretch()

        self.status_indicator = StatusDotBadge("穿透", Theme.POSITIVE, Theme.TEXT_MUTED)
        header_layout.addWidget(self.status_indicator)
        self.main_layout.addWidget(header_widget)

        # 2. Horizontal-Split CPU Hero Band
        self.hero_cpu = TelemetryHeroCard(tag="CPU", max_points=36, line_color=Theme.ACCENT)
        self.bar_cpu = self.hero_cpu
        self.main_layout.addWidget(self.hero_cpu)

        # 3. Full-width Style C Integrated-Fill Rows (内存 & GPU)
        self.bar_ram = CyberMechBar(tag="内存", layout_mode="row")
        self.main_layout.addWidget(self.bar_ram)

        self.bar_gpu = CyberMechBar(tag="GPU", layout_mode="row")
        self.main_layout.addWidget(self.bar_gpu)

        # 4. Twin Frosted Network Speed Tiles
        self.row_net = CyberNetRow(color=Theme.ACCENT)
        self.main_layout.addWidget(self.row_net)

        # 5. Remote VPS Block (asymmetric 2-column grid separated cleanly by 6px top space)
        self.vps_widget = QWidget()
        vps_layout = QVBoxLayout(self.vps_widget)
        vps_layout.setContentsMargins(0, 6, 0, 0)
        vps_layout.setSpacing(8)

        self.row_vps_status = StatRow(tag="VPS", show_bar=False)
        vps_layout.addWidget(self.row_vps_status)

        vps_tiles_row = QHBoxLayout()
        vps_tiles_row.setContentsMargins(0, 0, 0, 0)
        vps_tiles_row.setSpacing(8)

        self.bar_vps_cpu = CyberMechBar(tag="CPU", layout_mode="tile")
        vps_tiles_row.addWidget(self.bar_vps_cpu, stretch=1)

        self.bar_vps_ram = CyberMechBar(tag="内存", layout_mode="tile")
        vps_tiles_row.addWidget(self.bar_vps_ram, stretch=1)

        vps_layout.addLayout(vps_tiles_row)

        self.bar_vps_disk = CyberMechBar(tag="磁盘", layout_mode="row")
        vps_layout.addWidget(self.bar_vps_disk)

        self.main_layout.addWidget(self.vps_widget)

    def _load_saved_geometry(self):
        w_cfg = self.config_manager.get("window", {})
        x = int(w_cfg.get("x", 80))
        y = int(w_cfg.get("y", 80))
        hud_w = int(w_cfg.get("width", 330))

        screens = QApplication.screens()
        if screens:
            in_bounds = False
            for scr in screens:
                g = scr.availableGeometry()
                if g.left() - 20 <= x <= g.right() - 80 and g.top() - 20 <= y <= g.bottom() - 120:
                    in_bounds = True
                    break
            if not in_bounds:
                g = (QApplication.primaryScreen() or screens[0]).availableGeometry()
                x = max(g.left() + 4, min(x, g.right() - hud_w - 4))
                y = max(g.top() + 4, min(y, g.bottom() - 320))
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(80, self.apply_desktop_mode)

    def set_bg_opacity(self, val):
        """Adjust background panel opacity while keeping text and tiles crisp."""
        val = max(0.0, min(1.0, float(val)))
        self.config_manager.set("window", "bg_opacity", round(val, 2))
        self.update()

    def apply_desktop_mode(self):
        """Pin to bottom once and apply configured click-through setting."""
        self.send_to_bottom()
        w_cfg = self.config_manager.get("window", {})
        if w_cfg.get("click_through", True):
            self.enable_click_through()
        else:
            self.disable_click_through()

    def enable_click_through(self):
        """Enable Windows Click-Through (clicks pass completely through)."""
        hwnd = int(self.winId())
        extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            extended_style | WS_EX_TRANSPARENT | WS_EX_LAYERED,
        )
        self.status_indicator.set_status("穿透", Theme.POSITIVE, Theme.TEXT_MUTED)

    def disable_click_through(self):
        """Disable Windows Click-Through (window can be clicked and dragged)."""
        hwnd = int(self.winId())
        extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            (extended_style & ~WS_EX_TRANSPARENT) | WS_EX_LAYERED,
        )
        self.status_indicator.set_status("可拖", Theme.ACCENT, Theme.TEXT_PRIMARY)

    def send_to_bottom(self):
        """Pins the window to the bottom level of all normal windows."""
        hwnd = int(self.winId())
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_BOTTOM,
            0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE,
        )

    def enter_drag_mode(self, duration_sec=15):
        """Temporarily allow dragging so the user can move the window."""
        self.is_in_drag_mode = True
        hwnd = int(self.winId())
        extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, extended_style & ~WS_EX_TRANSPARENT)
        self.status_indicator.set_status("移动中", Theme.WARNING, Theme.WARNING)
        self.drag_mode_timer.start(duration_sec * 1000)

    def exit_drag_mode(self):
        """Restore configured click-through state."""
        self.is_in_drag_mode = False
        self.drag_mode_timer.stop()
        self.apply_desktop_mode()

    def mousePressEvent(self, event):
        can_drag = self.is_in_drag_mode or (not self.config_manager.get("window", {}).get("click_through", True))
        if can_drag and event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        can_drag = self.is_in_drag_mode or (not self.config_manager.get("window", {}).get("click_through", True))
        if can_drag and event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        can_drag = self.is_in_drag_mode or (not self.config_manager.get("window", {}).get("click_through", True))
        if can_drag and event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            self._magnetic_snap()
            self._save_position()
            if self.is_in_drag_mode:
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_changed.emit(self.x(), self.y())

    # --- Metrics Updates ---
    def update_local_metrics(self, data, animate=True):
        cpu_p = data["cpu"]["percent"]
        self.hero_cpu.update_data(percent=cpu_p, value_text=f"{round(cpu_p)}%", animate=animate)

        ram_p = data["ram"]["percent"]
        ram_used = data["ram"]["used_gb"]
        ram_tot = data["ram"]["total_gb"]
        self.bar_ram.update_data(
            percent=ram_p,
            value_text=f"{round(ram_p)}%",
            detail_text=f"{ram_used:.1f} / {ram_tot:.1f} GB",
            animate=animate,
        )

        gpu = data["gpu"]
        if gpu.get("available", False):
            self.bar_gpu.set_tag(_clean_gpu_name(gpu.get("name", "GPU")))
            temp = gpu["temp"]
            util = gpu["util"]
            self.bar_gpu.update_data(
                percent=util,
                value_text=f"{round(util)}%",
                detail_text=f"{temp}°C",
                animate=animate,
            )
        else:
            self.bar_gpu.set_tag("GPU")
            self.bar_gpu.update_data(percent=0, value_text="离线", detail_text="未检测到", animate=animate)

        up_s = format_speed(data["net"]["up_bps"])
        down_s = format_speed(data["net"]["down_bps"])
        self.row_net.update_speeds(up_s, down_s)

    def update_vps_metrics(self, data, animate=True):
        raw_status = str(data.get("status", "STANDBY")).upper()
        name = data.get("name", "VPS")
        ping = data.get("ping_ms")

        status_map = {
            "ONLINE": ("在线", Theme.POSITIVE),
            "STANDBY": ("待机", Theme.WARNING),
            "OFFLINE": ("离线", Theme.DANGER),
            "ERROR": ("异常", Theme.DANGER),
            "UNCONFIGURED": ("未配置", Theme.TEXT_MUTED),
        }
        status_label, status_color = status_map.get(raw_status, (raw_status, Theme.WARNING))

        if raw_status not in ("ONLINE", "STANDBY") or ping is None or ping <= 0.0:
            ping_str = "--"
        elif ping < 1.0:
            ping_str = "<1 ms"
        else:
            ping_str = f"{round(ping)} ms"

        self.row_vps_status.set_tag_text(name)
        self.row_vps_status.update_stat(status_label, detail_text=ping_str, custom_color=status_color)

        no_metrics = raw_status in ("OFFLINE", "ERROR", "UNCONFIGURED") or str(data.get("type", "")).lower() == "ping"
        if no_metrics:
            self.bar_vps_cpu.update_data(percent=0.0, value_text="--", animate=animate)
            self.bar_vps_ram.update_data(percent=0.0, value_text="--", detail_text="", animate=animate)
            self.bar_vps_disk.update_data(percent=0.0, value_text="--", detail_text="", animate=animate)
            return

        v_cpu = _nonneg_float(data.get("cpu_percent"))
        self.bar_vps_cpu.update_data(percent=v_cpu, value_text=f"{round(v_cpu)}%", animate=animate)

        v_ram = _nonneg_float(data.get("mem_percent"))
        v_used_mb = _nonneg_float(data.get("mem_used_mb"))
        v_tot_mb = _nonneg_float(data.get("mem_total_mb"))
        v_used_gb = _nonneg_float(data.get("mem_used_gb"))
        v_tot_gb = _nonneg_float(data.get("mem_total_gb"))

        if v_tot_mb > 0 and v_tot_mb < 1500:
            detail = f"{round(v_used_mb)}/{round(v_tot_mb)}M"
        elif v_tot_gb > 0:
            detail = f"{v_used_gb:.1f}/{v_tot_gb:.1f}G"
        else:
            detail = ""
        self.bar_vps_ram.update_data(percent=v_ram, value_text=f"{round(v_ram)}%", detail_text=detail, animate=animate)

        d_pct = min(100.0, _nonneg_float(data.get("disk_percent")))
        d_used_gb = _nonneg_float(data.get("disk_used_gb"))
        d_tot_gb = _nonneg_float(data.get("disk_total_gb"))

        if d_tot_gb > 0:
            if d_tot_gb >= 1024.0:
                disk_detail = f"{d_used_gb / 1024.0:.1f} / {d_tot_gb / 1024.0:.1f} TB"
            elif d_tot_gb < 1.0:
                disk_detail = f"{round(d_used_gb * 1024)} / {round(d_tot_gb * 1024)} MB"
            else:
                disk_detail = f"{d_used_gb:.1f} / {d_tot_gb:.1f} GB"
            disk_val = f"{round(d_pct)}%"
        else:
            disk_detail = ""
            d_pct = 0.0
            disk_val = "0%"

        self.bar_vps_disk.update_data(
            percent=d_pct,
            value_text=disk_val,
            detail_text=disk_detail,
            animate=animate,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = QRectF(0, 0, self.width(), self.height())
        bg_opacity = float(self.config_manager.get("window", {}).get("bg_opacity", 0.85))
        CyberPainter.draw_instrument_frame(
            painter,
            rect,
            bg_opacity=bg_opacity,
            radius=14.0,
        )

    def open_vps_config(self):
        dlg = VPSConfigDialog(self.config_manager, self)
        dlg.exec()
