import ctypes

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush,
    QLinearGradient, QFontMetrics
)

from ui.cyber_painter import CyberPainter, Theme, hex_to_qcolor

GWL_EXSTYLE = -20
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010


class ChronometerDigits(QWidget):
    """
    Airy 56px Light Segoe UI Variable Display chronometer with locked digit cells
    so numbers never shift horizontally on tick.
    """

    def __init__(self, initial_text="25:00", parent=None):
        super().__init__(parent)
        self._text = initial_text
        self._is_running = False
        self.setFixedHeight(66)

    def set_time(self, text: str, is_running: bool = False):
        if self._text != text or self._is_running != is_running:
            self._text = text
            self._is_running = is_running
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        if w <= 10 or h <= 10:
            return

        font = Theme.display_font(56, QFont.Weight.Light)
        painter.setFont(font)
        fm = QFontMetrics(font)

        baseline_y = (h + fm.capHeight()) * 0.5
        cell_w = 32.0
        colon_w = 14.0

        chars = list(self._text)
        total_w = sum(colon_w if ch == ":" else cell_w for ch in chars)
        cur_x = (w - total_w) * 0.5

        digit_col = hex_to_qcolor(Theme.TEXT_PRIMARY, 255)
        colon_col = hex_to_qcolor("#D4DCE8" if self._is_running else Theme.TEXT_MUTED, 255)

        for ch in chars:
            cw = colon_w if ch == ":" else cell_w
            glyph_w = fm.horizontalAdvance(ch)
            gx = cur_x + (cw - glyph_w) * 0.5
            painter.setPen(colon_col if ch == ":" else digit_col)
            dy = -0.5 if ch == ":" else 0.0
            painter.drawText(QPointF(gx, baseline_y + dy), ch)
            cur_x += cw


class FocusTimelineBar(QWidget):
    """Style B ultra-thin 3px precision rail with tonal sheen and 3x9mm vertical cap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.percent = 0.0
        self.is_running = False
        self.is_flashing = False
        self.setFixedHeight(14)

    def set_progress(self, percent: float, is_running: bool = False, is_flashing: bool = False):
        percent = max(0.0, min(100.0, float(percent)))
        if (
            abs(self.percent - percent) > 0.05
            or self.is_running != is_running
            or self.is_flashing != is_flashing
        ):
            self.percent = percent
            self.is_running = is_running
            self.is_flashing = is_flashing
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        if w <= 8:
            return

        cy = h * 0.5
        track_rect = QRectF(0.0, cy - 1.5, w, 3.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
        painter.drawRoundedRect(track_rect, 1.5, 1.5)

        pct = max(0.0, min(100.0, self.percent))
        if pct > 0.3 or self.is_running or self.is_flashing:
            if self.is_flashing and pct <= 0.3:
                fw = w
            else:
                fw = max(3.0, min(w, w * (pct / 100.0))) if pct > 0.3 else 3.0
            grad = QLinearGradient(0.0, 0.0, fw, 0.0)
            if self.is_flashing:
                grad.setColorAt(0.0, QColor("#B47924"))
                grad.setColorAt(1.0, QColor("#FAD49B"))
            elif self.is_running:
                grad.setColorAt(0.0, QColor("#5B8EC9"))
                grad.setColorAt(1.0, QColor("#DCEBFF"))
            else:
                grad.setColorAt(0.0, QColor("#6B7280"))
                grad.setColorAt(1.0, QColor("#E5E7EB"))

            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(0.0, cy - 1.5, fw, 3.0), 1.5, 1.5)

            cap_x = max(0.0, min(w - 3.0, fw - 1.5))
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawRoundedRect(QRectF(cap_x, cy - 4.5, 3.0, 9.0), 1.5, 1.5)


class CycleDotsWidget(QWidget):
    """4 subtle 5px circular dots indicating completed pomodoro cycles."""

    def __init__(self, target=4, parent=None):
        super().__init__(parent)
        self.target = max(1, int(target))
        self.completed = 0
        self.show_full = False
        self.setFixedSize(self.target * 5 + (self.target - 1) * 5, 16)

    def set_state(self, completed: int, show_full: bool = False):
        if self.completed != completed or self.show_full != show_full:
            self.completed = completed
            self.show_full = show_full
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        lit = self.target if self.show_full else (self.completed % self.target)
        cy = self.height() * 0.5
        for i in range(self.target):
            cx = 2.5 + i * 10.0
            color = hex_to_qcolor(Theme.ACCENT, 255) if i < lit else QColor(255, 255, 255, 42)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(cx, cy), 2.5, 2.5)


class StepperButton(QPushButton):
    """Quiet 34x34 frosted stepper button with crisp 1.5px vector minus/plus icon."""

    right_clicked = pyqtSignal()

    def __init__(self, kind="minus", parent=None):
        super().__init__("", parent)
        self.kind = kind
        self.setFixedSize(34, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(10, 11, 15, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.11);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.13);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
            QPushButton:pressed {
                background-color: rgba(10, 11, 15, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        col = Theme.TEXT_PRIMARY if (self.underMouse() or self.isDown()) else Theme.TEXT_SECONDARY
        pen = QPen(hex_to_qcolor(col, 255), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        cx = self.width() * 0.5
        cy = self.height() * 0.5
        arm = 4.5
        painter.drawLine(QPointF(cx - arm, cy), QPointF(cx + arm, cy))
        if self.kind == "plus":
            painter.drawLine(QPointF(cx, cy - arm), QPointF(cx, cy + arm))


class ModePillButton(QPushButton):
    """Quiet compact mode selector pill sitting in the top header row."""

    def __init__(self, text, is_active=False, parent=None):
        super().__init__(text, parent)
        self.is_active = is_active
        self.setFixedHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    def set_active(self, active: bool):
        if self.is_active != active:
            self.is_active = active
            self._apply_style()

    def _apply_style(self):
        if self.is_active:
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.14);
                    color: #F4F4F6;
                    border: none;
                    border-radius: 6px;
                    font-family: 'MiSans', 'Microsoft YaHei UI', 'Segoe UI';
                    font-weight: 500;
                    font-size: 12px;
                    padding: 0px 9px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.19);
                    color: #FFFFFF;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #969CA8;
                    border: none;
                    border-radius: 6px;
                    font-family: 'MiSans', 'Microsoft YaHei UI', 'Segoe UI';
                    font-weight: 400;
                    font-size: 12px;
                    padding: 0px 9px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.07);
                    color: #E2E5EC;
                }
            """)


class ActionButton(QPushButton):
    """Calm frosted-glass action keys (glass-white primary, glacier running, ghost secondary)."""

    def __init__(self, text, variant="secondary", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    def set_variant(self, variant: str):
        if self.variant != variant:
            self.variant = variant
            self._apply_style()

    def _apply_style(self):
        if self.variant == "primary":
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.18);
                    color: #F4F4F6;
                    border: 1px solid rgba(255, 255, 255, 0.22);
                    border-radius: 8px;
                    font-family: 'MiSans', 'Microsoft YaHei UI', 'Segoe UI';
                    font-weight: 500;
                    font-size: 14px;
                    padding: 0px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.25);
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.12);
                }
            """)
        elif self.variant == "running":
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(125, 180, 255, 0.18);
                    color: #EAF2FF;
                    border: 1px solid rgba(125, 180, 255, 0.36);
                    border-radius: 8px;
                    font-family: 'MiSans', 'Microsoft YaHei UI', 'Segoe UI';
                    font-weight: 500;
                    font-size: 14px;
                    padding: 0px 12px;
                }
                QPushButton:hover {
                    background-color: rgba(125, 180, 255, 0.26);
                    border: 1px solid rgba(125, 180, 255, 0.48);
                }
                QPushButton:pressed {
                    background-color: rgba(125, 180, 255, 0.13);
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(10, 11, 15, 0.42);
                    color: #B8BDC8;
                    border: 1px solid rgba(255, 255, 255, 0.11);
                    border-radius: 8px;
                    font-family: 'MiSans', 'Microsoft YaHei UI', 'Segoe UI';
                    font-weight: 400;
                    font-size: 14px;
                    padding: 0px 10px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    color: #F4F4F6;
                    border: 1px solid rgba(255, 255, 255, 0.18);
                }
                QPushButton:pressed {
                    background-color: rgba(10, 11, 15, 0.60);
                }
            """)


class CyberPomodoroWindow(QWidget):
    """
    Minimal Frosted Focus Chronometer anchored 8px beneath CyberHUDWindow.
    """

    session_completed = pyqtSignal(str)  # 'focus' or 'break'

    MODE_FOCUS = "focus"
    MODE_SHORT_BREAK = "short_break"
    MODE_LONG_BREAK = "long_break"

    def __init__(self, config_manager, hud_window=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.hud_window = hud_window
        self.drag_position = None

        pomo_cfg = self.config_manager.get("pomodoro", {})
        self.focus_min = int(pomo_cfg.get("focus_min", 25))
        self.short_break_min = int(pomo_cfg.get("short_break_min", 5))
        self.long_break_min = int(pomo_cfg.get("long_break_min", 15))
        self.auto_dock = pomo_cfg.get("auto_dock", True)
        self.sound_alert = pomo_cfg.get("sound_alert", True)

        self.current_mode = self.MODE_FOCUS
        self.is_running = False
        self.total_seconds = self.focus_min * 60
        self.remaining_seconds = self.total_seconds
        self.completed_pomos = 0
        self.target_pomos = 4

        self.is_flashing = False
        self.flash_step = 0
        self.flash_timer = QTimer(self)
        self.flash_timer.setInterval(250)
        self.flash_timer.timeout.connect(self._handle_flash_tick)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)

        self._init_window_flags()
        self._init_ui()
        self._sync_status_badge()
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

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 14, 16, 16)
        self.main_layout.setSpacing(10)

        # 1. Combined Quiet Header Row (28px): Mode pills left | Cycle dots + optional live dot right
        top_row = QWidget()
        top_row.setFixedHeight(28)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        self.btn_mode_focus = ModePillButton(f"专注 {self.focus_min}", is_active=True)
        self.btn_mode_focus.clicked.connect(lambda: self.switch_mode(self.MODE_FOCUS))
        top_layout.addWidget(self.btn_mode_focus)

        self.btn_mode_short = ModePillButton(f"短休 {self.short_break_min}", is_active=False)
        self.btn_mode_short.clicked.connect(lambda: self.switch_mode(self.MODE_SHORT_BREAK))
        top_layout.addWidget(self.btn_mode_short)

        self.btn_mode_long = ModePillButton(f"长休 {self.long_break_min}", is_active=False)
        self.btn_mode_long.clicked.connect(lambda: self.switch_mode(self.MODE_LONG_BREAK))
        top_layout.addWidget(self.btn_mode_long)

        top_layout.addStretch()

        self.cycle_dots = CycleDotsWidget(target=self.target_pomos)
        top_layout.addWidget(self.cycle_dots, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.lbl_state = QLabel("")
        self.lbl_state.setFont(Theme.ui_font(12, QFont.Weight.Normal))
        self.lbl_state.setContentsMargins(6, 0, 0, 0)
        self.lbl_state.hide()
        top_layout.addWidget(self.lbl_state, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addWidget(top_row)

        # 2. Airy 56px Light Chronometer Row (66px) with 34x34 flanking steppers
        time_container = QWidget()
        time_container.setFixedHeight(66)
        time_layout = QHBoxLayout(time_container)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(10)

        self.btn_dec = StepperButton(kind="minus")
        self.btn_dec.setToolTip("左键减 1 分钟 / 右键减 5 分钟")
        self.btn_dec.clicked.connect(lambda: self.adjust_time(-60))
        self.btn_dec.right_clicked.connect(lambda: self.adjust_time(-300))
        time_layout.addWidget(self.btn_dec, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.lbl_digits = ChronometerDigits("25:00")
        time_layout.addWidget(self.lbl_digits, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.btn_inc = StepperButton(kind="plus")
        self.btn_inc.setToolTip("左键加 1 分钟 / 右键加 5 分钟")
        self.btn_inc.clicked.connect(lambda: self.adjust_time(60))
        self.btn_inc.right_clicked.connect(lambda: self.adjust_time(300))
        time_layout.addWidget(self.btn_inc, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addWidget(time_container)

        # 3. Style B Ultra-thin 3px Precision Progress Rail (14px)
        self.timeline_bar = FocusTimelineBar()
        self.main_layout.addWidget(self.timeline_bar)

        # 4. Calm Frosted Controls Row (38px)
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(8)

        self.btn_start = ActionButton("开始专注", variant="primary")
        self.btn_start.clicked.connect(self.toggle_timer)
        ctrl_layout.addWidget(self.btn_start, stretch=3)

        self.btn_reset = ActionButton("重置", variant="secondary")
        self.btn_reset.clicked.connect(self.reset_timer)
        ctrl_layout.addWidget(self.btn_reset, stretch=2)

        self.btn_skip = ActionButton("跳过", variant="secondary")
        self.btn_skip.clicked.connect(self.skip_phase)
        ctrl_layout.addWidget(self.btn_skip, stretch=2)

        self.main_layout.addLayout(ctrl_layout)

    def _sync_status_badge(self):
        if self.is_running:
            if self.current_mode == self.MODE_FOCUS:
                self.lbl_state.setText("专注中")
                self.lbl_state.setStyleSheet(f"color: {Theme.ACCENT};")
            else:
                self.lbl_state.setText("休息中")
                self.lbl_state.setStyleSheet(f"color: {Theme.POSITIVE};")
            self.lbl_state.show()
        elif self.remaining_seconds < self.total_seconds:
            self.lbl_state.setText("已暂停")
            self.lbl_state.setStyleSheet(f"color: {Theme.WARNING};")
            self.lbl_state.show()
        else:
            self.lbl_state.hide()

    def adjust_time(self, delta_sec: int):
        """Adjust countdown time anytime (+/- 60s or +/- 300s). Bounds: 1 min..120 min."""
        was_untouched = (not self.is_running) and (self.remaining_seconds == self.total_seconds)
        new_sec = max(60, min(120 * 60, self.remaining_seconds + delta_sec))
        self.remaining_seconds = new_sec

        if was_untouched:
            self.total_seconds = new_sec
            mins = new_sec // 60
            if self.current_mode == self.MODE_FOCUS:
                self.focus_min = mins
                self.btn_mode_focus.setText(f"专注 {mins}")
            elif self.current_mode == self.MODE_SHORT_BREAK:
                self.short_break_min = mins
                self.btn_mode_short.setText(f"短休 {mins}")
            elif self.current_mode == self.MODE_LONG_BREAK:
                self.long_break_min = mins
                self.btn_mode_long.setText(f"长休 {mins}")
        else:
            if new_sec > self.total_seconds:
                self.total_seconds = new_sec

        self._sync_status_badge()
        self._update_display()

    def switch_mode(self, mode: str):
        """Switch between focus, short_break, and long_break."""
        self.current_mode = mode
        self.is_running = False
        self.timer.stop()
        self.btn_dec.setEnabled(True)
        self.btn_inc.setEnabled(True)

        self.btn_start.setText("开始专注" if mode == self.MODE_FOCUS else "开始休息")
        self.btn_start.set_variant("primary")

        if mode == self.MODE_FOCUS:
            self.total_seconds = self.focus_min * 60
            self.btn_mode_focus.set_active(True)
            self.btn_mode_short.set_active(False)
            self.btn_mode_long.set_active(False)
        elif mode == self.MODE_SHORT_BREAK:
            self.total_seconds = self.short_break_min * 60
            self.btn_mode_focus.set_active(False)
            self.btn_mode_short.set_active(True)
            self.btn_mode_long.set_active(False)
        else:
            self.total_seconds = self.long_break_min * 60
            self.btn_mode_focus.set_active(False)
            self.btn_mode_short.set_active(False)
            self.btn_mode_long.set_active(True)

        self.remaining_seconds = self.total_seconds
        self._sync_status_badge()
        self._update_display()

    def toggle_timer(self):
        """Start or pause the countdown timer."""
        self.btn_dec.setEnabled(True)
        self.btn_inc.setEnabled(True)

        if self.is_running:
            self.is_running = False
            self.timer.stop()
            self.btn_start.setText("继续")
            self.btn_start.set_variant("primary")
        else:
            self.is_running = True
            self.timer.start()
            self.btn_start.setText("暂停")
            self.btn_start.set_variant("running")

        self._sync_status_badge()
        self._update_display()

    def reset_timer(self):
        """Reset remaining time to current mode duration."""
        self.is_running = False
        self.timer.stop()
        self.btn_dec.setEnabled(True)
        self.btn_inc.setEnabled(True)

        if self.current_mode == self.MODE_FOCUS:
            self.total_seconds = self.focus_min * 60
            self.btn_start.setText("开始专注")
        elif self.current_mode == self.MODE_SHORT_BREAK:
            self.total_seconds = self.short_break_min * 60
            self.btn_start.setText("开始休息")
        else:
            self.total_seconds = self.long_break_min * 60
            self.btn_start.setText("开始休息")

        self.remaining_seconds = self.total_seconds
        self.btn_start.set_variant("primary")
        self._sync_status_badge()
        self._update_display()

    def skip_phase(self):
        """Skip current phase to the next scheduled phase."""
        self.timer.stop()
        self.is_running = False
        self.btn_dec.setEnabled(True)
        self.btn_inc.setEnabled(True)
        if self.current_mode == self.MODE_FOCUS:
            if (self.completed_pomos + 1) % self.target_pomos == 0:
                self.switch_mode(self.MODE_LONG_BREAK)
            else:
                self.switch_mode(self.MODE_SHORT_BREAK)
        else:
            self.switch_mode(self.MODE_FOCUS)

    def _on_tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_display()
        else:
            self._handle_completed()

    def _handle_completed(self):
        self.timer.stop()
        self.is_running = False
        self.btn_dec.setEnabled(True)
        self.btn_inc.setEnabled(True)
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
        """Briefly pulses timeline rail amber to signal completion."""
        self.is_flashing = True
        self.flash_step = 0
        self.flash_timer.start()
        self._update_display()

    def _handle_flash_tick(self):
        self.flash_step += 1
        if self.flash_step >= 10:
            self.flash_timer.stop()
            self.is_flashing = False
        self._update_display()

    def _update_display(self):
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        self.lbl_digits.set_time(f"{mins:02d}:{secs:02d}", is_running=self.is_running)

        if self.total_seconds > 0:
            elapsed = self.total_seconds - self.remaining_seconds
            pct = (elapsed / self.total_seconds) * 100.0
        else:
            pct = 0.0

        flash_on = self.is_flashing and (self.flash_step % 2 == 0)
        self.timeline_bar.set_progress(pct, is_running=self.is_running, is_flashing=flash_on)

        show_full = (
            self.completed_pomos > 0
            and self.completed_pomos % self.target_pomos == 0
            and self.current_mode == self.MODE_LONG_BREAK
        )
        self.cycle_dots.set_state(self.completed_pomos, show_full=show_full)

    def on_hud_moved(self, x, y):
        self.sync_position_with_hud()

    def sync_position_with_hud(self):
        """Anchor 8px below the main HUD window."""
        if not self.hud_window:
            return
        geo = self.hud_window.geometry()
        x = geo.x()
        y = geo.y() + geo.height() + 8
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        if self.hud_window:
            self.sync_position_with_hud()
        QTimer.singleShot(100, self.send_to_bottom)

    def send_to_bottom(self):
        """Pin window to the desktop bottom layer."""
        hwnd = int(self.winId())
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_BOTTOM,
            0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = QRectF(0, 0, self.width(), self.height())
        bg_opacity = float(self.config_manager.get("window", {}).get("bg_opacity", 0.85))
        CyberPainter.draw_instrument_frame(
            painter=painter,
            rect=rect,
            bg_opacity=bg_opacity,
            radius=14.0,
        )
