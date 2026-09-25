import sys
import os
import time
import ctypes

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QApplication, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush

from ui.cyber_painter import CyberPainter, hex_to_qcolor
from ui.widgets.cyber_mech_bar import CyberMechBar

GWL_EXSTYLE = -20
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

class CyberButton(QPushButton):
    """Custom high-tech cyberpunk styled push button supporting right-click."""
    right_clicked = pyqtSignal()

    def __init__(self, text, primary_color="#00F3FF", is_active=False, font_size=13, parent=None):
        super().__init__(text, parent)
        self.primary_color = primary_color
        self.is_active = is_active
        self.font_size = font_size
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def set_active(self, active: bool):
        self.is_active = active
        self._update_style()

    def set_color(self, color_str: str):
        self.primary_color = color_str
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _update_style(self):
        c = self.primary_color
        fs = self.font_size
        if self.is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c}33;
                    color: #FFFFFF;
                    border: 1px solid {c};
                    font-family: 'Consolas', monospace;
                    font-weight: bold;
                    font-size: {fs}px;
                    padding: 4px 6px;
                    border-radius: 3px;
                }}
                QPushButton:hover {{
                    background-color: {c}66;
                    border: 1px solid #FFFFFF;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #0E1424EE;
                    color: #FFFFFF;
                    border: 1px solid {c}88;
                    font-family: 'Consolas', monospace;
                    font-weight: bold;
                    font-size: {fs}px;
                    padding: 4px 6px;
                    border-radius: 3px;
                }}
                QPushButton:hover {{
                    background-color: {c}33;
                    color: #FFFFFF;
                    border: 1px solid {c};
                }}
                QPushButton:pressed {{
                    background-color: {c}55;
                }}
            """)

class CyberPomodoroWindow(QWidget):
    """
    Dedicated Cyberpunk Floating Pomodoro Focus Widget.
    Sits right underneath the CyberHUD window with matching sci-fi aesthetics.
    Features bilateral time adjustment buttons and enlarged legible typography.
    """
    session_completed = pyqtSignal(str) # 'focus' or 'break'

    MODE_FOCUS = "focus"
    MODE_SHORT_BREAK = "short_break"
    MODE_LONG_BREAK = "long_break"

    def __init__(self, config_manager, hud_window=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.hud_window = hud_window
        self.drag_position = None

        # Pomodoro settings
        pomo_cfg = self.config_manager.get("pomodoro", {})
        self.focus_min = int(pomo_cfg.get("focus_min", 25))
        self.short_break_min = int(pomo_cfg.get("short_break_min", 5))
        self.long_break_min = int(pomo_cfg.get("long_break_min", 15))
        self.auto_dock = pomo_cfg.get("auto_dock", True)
        self.sound_alert = pomo_cfg.get("sound_alert", True)

        # State
        self.current_mode = self.MODE_FOCUS
        self.is_running = False
        self.total_seconds = self.focus_min * 60
        self.remaining_seconds = self.total_seconds
        self.completed_pomos = 0
        self.target_pomos = 4

        # Visual Flash Alert
        self.is_flashing = False
        self.flash_step = 0
        self.flash_timer = QTimer(self)
        self.flash_timer.setInterval(250)
        self.flash_timer.timeout.connect(self._handle_flash_tick)

        # 1-second Engine Timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)

        self._init_window_flags()
        self._init_ui()
        self._update_display()

        if self.hud_window:
            self.hud_window.position_changed.connect(self.on_hud_moved)

    def _init_window_flags(self):
        self.setWindowTitle("CyberPomodoro")
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

        # Main Layout (Spacious and balanced)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 14, 16, 16)
        self.main_layout.setSpacing(12)

        # 1. Header (Title + Mode LED - Enlarged Fonts)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_title = QLabel("FOCUS.TMR // CYBER-POMO")
        self.lbl_title.setStyleSheet("""
            QLabel {
                color: #00F3FF;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 14px;
                letter-spacing: 1px;
            }
        """)
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()

        self.lbl_led = QLabel("● STANDBY")
        self.lbl_led.setStyleSheet("color: #FFB800; font-family: 'Consolas'; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(self.lbl_led)
        self.main_layout.addLayout(header_layout)

        # 2. Mode Selector Pills (Font size 13px, Height 32px)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(6)
        
        self.btn_mode_focus = CyberButton(f"{self.focus_min}M 专注", primary_color="#00F3FF", is_active=True, font_size=13)
        self.btn_mode_focus.setFixedHeight(32)
        self.btn_mode_focus.clicked.connect(lambda: self.switch_mode(self.MODE_FOCUS))
        mode_layout.addWidget(self.btn_mode_focus)

        self.btn_mode_short = CyberButton(f"{self.short_break_min:02d}M 短休", primary_color="#00FF88", is_active=False, font_size=13)
        self.btn_mode_short.setFixedHeight(32)
        self.btn_mode_short.clicked.connect(lambda: self.switch_mode(self.MODE_SHORT_BREAK))
        mode_layout.addWidget(self.btn_mode_short)

        self.btn_mode_long = CyberButton(f"{self.long_break_min:02d}M 长休", primary_color="#B026FF", is_active=False, font_size=13)
        self.btn_mode_long.setFixedHeight(32)
        self.btn_mode_long.clicked.connect(lambda: self.switch_mode(self.MODE_LONG_BREAK))
        mode_layout.addWidget(self.btn_mode_long)

        self.main_layout.addLayout(mode_layout)

        # 3. Big Digital Timer Display with Bilateral Adjust Buttons
        time_container = QHBoxLayout()
        time_container.setContentsMargins(4, 2, 4, 2)
        time_container.setSpacing(10)
        
        # Left Button (Decrease time: 1 min per click)
        self.btn_dec = CyberButton("◀", primary_color="#00F3FF", is_active=False, font_size=16)
        self.btn_dec.setFixedSize(38, 38)
        self.btn_dec.setToolTip("左键减 1 分钟 / 右键快捷减 5 分钟")
        self.btn_dec.clicked.connect(lambda: self.adjust_time(-60))
        self.btn_dec.right_clicked.connect(lambda: self.adjust_time(-300))
        time_container.addWidget(self.btn_dec, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Center Digits (Enlarged to 48px bold Consolas)
        self.lbl_digits = QLabel("25:00")
        self.lbl_digits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_digits.setStyleSheet(self._digit_style("#00F3FF"))
        time_container.addWidget(self.lbl_digits, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)

        # Right Button (Increase time: 1 min per click)
        self.btn_inc = CyberButton("▶", primary_color="#00F3FF", is_active=False, font_size=16)
        self.btn_inc.setFixedSize(38, 38)
        self.btn_inc.setToolTip("左键加 1 分钟 / 右键快捷加 5 分钟")
        self.btn_inc.clicked.connect(lambda: self.adjust_time(60))
        self.btn_inc.right_clicked.connect(lambda: self.adjust_time(300))
        time_container.addWidget(self.btn_inc, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addLayout(time_container)

        # 4. Cyber Countdown Progress Bar
        self.bar_progress = CyberMechBar(tag="FOCUS", rail_color="#00F3FF", blade_color="#00F3FF")
        self.main_layout.addWidget(self.bar_progress)

        # 5. Controls Row (Start/Pause, Reset, Skip - Enlarged Fonts 14px, Height 34px)
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        self.btn_start = CyberButton("▶ 开始专注", primary_color="#00F3FF", is_active=True, font_size=14)
        self.btn_start.setFixedHeight(34)
        self.btn_start.clicked.connect(self.toggle_timer)
        ctrl_layout.addWidget(self.btn_start, stretch=3)

        self.btn_reset = CyberButton("↺ 重置", primary_color="#FFB800", is_active=False, font_size=14)
        self.btn_reset.setFixedHeight(34)
        self.btn_reset.clicked.connect(self.reset_timer)
        ctrl_layout.addWidget(self.btn_reset, stretch=2)

        self.btn_skip = CyberButton(">> 跳过", primary_color="#FF0055", is_active=False, font_size=14)
        self.btn_skip.setFixedHeight(34)
        self.btn_skip.clicked.connect(self.skip_phase)
        ctrl_layout.addWidget(self.btn_skip, stretch=2)

        self.main_layout.addLayout(ctrl_layout)

    def adjust_time(self, delta_sec: int):
        """
        Adjusts the countdown time by delta_sec (+/- 60s).
        Minimum: 60s (1 min), Maximum: 120 min.
        """
        new_sec = max(60, min(120 * 60, self.remaining_seconds + delta_sec))
        self.remaining_seconds = new_sec

        # Fix: When not running, adjusting time sets initial total duration (progress stays 0%)
        if not self.is_running:
            self.total_seconds = new_sec
        else:
            if new_sec > self.total_seconds:
                self.total_seconds = new_sec

        self._update_display()

    def switch_mode(self, mode: str):
        """Switches the session mode (focus / short_break / long_break)."""
        self.current_mode = mode
        self.is_running = False
        self.timer.stop()
        self.btn_start.setText("▶ 开始" if mode == self.MODE_FOCUS else "▶ 开始休息")
        self.btn_start.set_active(True)

        if mode == self.MODE_FOCUS:
            self.total_seconds = self.focus_min * 60
            color = "#00F3FF"
            self.bar_progress.rail_color = color
            self.bar_progress.blade_color = color
            self.bar_progress.tag = "FOCUS"
            self.bar_progress.update()
            self.btn_mode_focus.set_active(True)
            self.btn_mode_short.set_active(False)
            self.btn_mode_long.set_active(False)
            self.lbl_digits.setStyleSheet(self._digit_style(color))
            self.lbl_led.setText("● FOCUS READY")
            self.lbl_led.setStyleSheet("color: #00F3FF; font-family: 'Consolas'; font-size: 12px; font-weight: bold;")
            self.btn_dec.set_color(color)
            self.btn_inc.set_color(color)
        elif mode == self.MODE_SHORT_BREAK:
            self.total_seconds = self.short_break_min * 60
            color = "#00FF88"
            self.bar_progress.rail_color = color
            self.bar_progress.blade_color = color
            self.bar_progress.tag = "REST"
            self.bar_progress.update()
            self.btn_mode_focus.set_active(False)
            self.btn_mode_short.set_active(True)
            self.btn_mode_long.set_active(False)
            self.lbl_digits.setStyleSheet(self._digit_style(color))
            self.lbl_led.setText("● SHORT BREAK")
            self.lbl_led.setStyleSheet("color: #00FF88; font-family: 'Consolas'; font-size: 12px; font-weight: bold;")
            self.btn_dec.set_color("#00F3FF")
            self.btn_inc.set_color("#00F3FF")
        else: # long_break
            self.total_seconds = self.long_break_min * 60
            color = "#B026FF"
            self.bar_progress.rail_color = color
            self.bar_progress.blade_color = color
            self.bar_progress.tag = "LONG"
            self.bar_progress.update()
            self.btn_mode_focus.set_active(False)
            self.btn_mode_short.set_active(False)
            self.btn_mode_long.set_active(True)
            self.lbl_digits.setStyleSheet(self._digit_style(color))
            self.lbl_led.setText("● LONG BREAK")
            self.lbl_led.setStyleSheet("color: #B026FF; font-family: 'Consolas'; font-size: 12px; font-weight: bold;")
            self.btn_dec.set_color("#00F3FF")
            self.btn_inc.set_color("#00F3FF")

        self.remaining_seconds = self.total_seconds
        self._update_display()

    def _digit_style(self, color_hex):
        return f"""
            QLabel {{
                color: {color_hex};
                font-family: 'Consolas', 'Lucida Console', monospace;
                font-weight: bold;
                font-size: 48px;
                letter-spacing: 3px;
                margin-top: -2px;
                margin-bottom: -4px;
            }}
        """

    def toggle_timer(self):
        """Starts or pauses the timer."""
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            self.btn_start.setText("▶ 继续")
            self.lbl_led.setText("● PAUSED")
            self.lbl_led.setStyleSheet("color: #FFB800; font-family: 'Consolas'; font-size: 12px; font-weight: bold;")
        else:
            self.is_running = True
            self.timer.start()
            self.btn_start.setText("|| 暂停")
            tag = "● FOCUSING" if self.current_mode == self.MODE_FOCUS else "● RESTING"
            c = "#00F3FF" if self.current_mode == self.MODE_FOCUS else "#00FF88"
            self.lbl_led.setText(tag)
            self.lbl_led.setStyleSheet(f"color: {c}; font-family: 'Consolas'; font-size: 12px; font-weight: bold;")

    def reset_timer(self):
        """Resets the remaining time to current mode duration."""
        self.is_running = False
        self.timer.stop()
        if self.current_mode == self.MODE_FOCUS:
            self.total_seconds = self.focus_min * 60
        elif self.current_mode == self.MODE_SHORT_BREAK:
            self.total_seconds = self.short_break_min * 60
        else:
            self.total_seconds = self.long_break_min * 60
        self.remaining_seconds = self.total_seconds
        self.btn_start.setText("▶ 开始")
        self.lbl_led.setText("● RESET")
        self.lbl_led.setStyleSheet("color: #FFB800; font-family: 'Consolas'; font-size: 12px; font-weight: bold;")
        self._update_display()

    def skip_phase(self):
        """Skips current phase to the next one."""
        self.timer.stop()
        self.is_running = False
        if self.current_mode == self.MODE_FOCUS:
            if (self.completed_pomos + 1) % self.target_pomos == 0:
                self.switch_mode(self.MODE_LONG_BREAK)
            else:
                self.switch_mode(self.MODE_SHORT_BREAK)
        else:
            self.switch_mode(self.MODE_FOCUS)

    def _on_tick(self):
        """Called every second when running."""
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_display()
        else:
            self._handle_completed()

    def _handle_completed(self):
        self.timer.stop()
        self.is_running = False
        self._trigger_flash_alert()

        if self.sound_alert:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        if self.current_mode == self.MODE_FOCUS:
            self.completed_pomos += 1
            self.session_completed.emit("focus")
            if self.completed_pomos % self.target_pomos == 0:
                self.switch_mode(self.MODE_LONG_BREAK)
            else:
                self.switch_mode(self.MODE_SHORT_BREAK)
        else:
            self.session_completed.emit("break")
            self.switch_mode(self.MODE_FOCUS)

    def _trigger_flash_alert(self):
        """Flashes the border in neon gold/amber for 3 seconds."""
        self.is_flashing = True
        self.flash_step = 0
        self.flash_timer.start()

    def _handle_flash_tick(self):
        self.flash_step += 1
        self.update()
        if self.flash_step >= 12:
            self.flash_timer.stop()
            self.is_flashing = False
            self.update()

    def _update_display(self):
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        self.lbl_digits.setText(f"{mins:02d}:{secs:02d}")

        if self.total_seconds > 0:
            elapsed = self.total_seconds - self.remaining_seconds
            pct = (elapsed / self.total_seconds) * 100.0
        else:
            pct = 0.0

        rem_str = f"{round(pct)}%"
        self.bar_progress.update_data(percent=pct, value_text=rem_str, detail_text=f"{mins}m {secs}s")

    def on_hud_moved(self, x, y):
        self.sync_position_with_hud()

    def sync_position_with_hud(self):
        """Firmly locks this window directly below the main HUD window."""
        if not self.hud_window:
            return
        geo = self.hud_window.geometry()
        x = geo.x()
        y = geo.y() + geo.height() + 10
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        if self.hud_window:
            self.sync_position_with_hud()
        QTimer.singleShot(100, self.send_to_bottom)

    def send_to_bottom(self):
        """Pins the window to the desktop bottom layer (interactive, but behind active apps)."""
        hwnd = int(self.winId())
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_BOTTOM,
            0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = QRectF(0, 0, self.width(), self.height())
        
        bg_opacity = self.config_manager.get("window", {}).get("bg_opacity", 0.45)
        
        # 固定边框为统一的赛博青蓝 (#00F3FF)，与上方 HUD 主窗口保持严格视觉一致
        border_color = "#00F3FF"

        CyberPainter.draw_cyber_frame(
            painter=painter,
            rect=rect,
            bg_color="#0B0E17",
            border_color=border_color,
            cut=16.0,
            bg_opacity=bg_opacity
        )

