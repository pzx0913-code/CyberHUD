from collections import deque
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath,
    QLinearGradient, QFont, QFontMetrics
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer

from ui.cyber_painter import Theme, hex_to_qcolor, metric_semantic_color


class TelemetryHeroCard(QWidget):
    """
    Horizontal-split CPU hero band:
    - Left column: quiet CPU label + airy 36px Light Segoe UI Variable readout.
    - Right column: calm open hairline Bezier waveform with faint gradient wash.
    """

    def __init__(self, tag="CPU", max_points=36, line_color=Theme.ACCENT, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.max_points = max_points
        self.base_color = line_color
        self.history = deque([0.0] * max_points, maxlen=max_points)
        self.value_text = "0%"
        self.detail_text = ""
        self.current_percent = 0.0
        self.display_percent = 0.0

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._step_anim)

        self.setFixedHeight(68)

    def _step_anim(self):
        diff = self.current_percent - self.display_percent
        if abs(diff) <= 0.25:
            self.display_percent = self.current_percent
            self._anim_timer.stop()
        else:
            self.display_percent += diff * 0.28
        self.update()

    def add_point(self, val: float):
        """Compatibility helper to append a sample directly."""
        self.update_data(val, animate=False)

    def update_data(self, percent: float, value_text: str = None, detail_text: str = None, animate: bool = True):
        percent = max(0.0, min(100.0, float(percent)))
        self.current_percent = percent
        self.history.append(percent)

        if value_text is not None:
            self.value_text = value_text
        else:
            self.value_text = f"{round(percent)}%"

        if detail_text is not None:
            self.detail_text = detail_text

        if not animate:
            self._anim_timer.stop()
            self.display_percent = percent
        elif not self._anim_timer.isActive():
            self._anim_timer.start()

        self.update()

    def flush_animation(self):
        self._anim_timer.stop()
        self.display_percent = self.current_percent
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        if w <= 20 or h <= 10:
            return

        # 1. Left Column (x = 0..88): Quiet label top + 36px Light display number
        painter.setFont(Theme.ui_font(13, QFont.Weight.Medium))
        painter.setPen(hex_to_qcolor(Theme.TEXT_SECONDARY, 255))
        painter.drawText(QRectF(0.0, 2.0, 88.0, 18.0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.tag)

        num_str = self.value_text[:-1] if self.value_text.endswith("%") else self.value_text
        has_pct = self.value_text.endswith("%")

        f_big = Theme.display_font(36, QFont.Weight.Light)
        f_unit = Theme.display_font(16, QFont.Weight.Light)
        fm_big = QFontMetrics(f_big)

        baseline_y = 56.0
        num_w = fm_big.horizontalAdvance(num_str)
        val_col = hex_to_qcolor(
            metric_semantic_color(self.current_percent, Theme.TEXT_PRIMARY), 255
        )

        painter.setFont(f_big)
        painter.setPen(val_col)
        painter.drawText(QPointF(0.0, baseline_y), num_str)

        if has_pct:
            painter.setFont(f_unit)
            painter.setPen(hex_to_qcolor(Theme.TEXT_MUTED, 255))
            painter.drawText(QPointF(num_w + 0.5, baseline_y), "%")

        # 2. Right Column (x = 92..w-4, y = 6..58): Minimalist Hairline Curve
        trace_left = 92.0
        trace_right = w - 4.0
        trace_top = 6.0
        trace_bottom = 58.0
        trace_w = max(24.0, trace_right - trace_left)
        trace_h = trace_bottom - trace_top

        # Faint 50% dotted hairline & bottom hairline
        mid_y = trace_top + trace_h * 0.5
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0, Qt.PenStyle.DotLine))
        painter.drawLine(QPointF(trace_left, mid_y), QPointF(trace_right, mid_y))

        painter.setPen(QPen(QColor(255, 255, 255, 26), 1.0))
        painter.drawLine(QPointF(trace_left, trace_bottom), QPointF(trace_right, trace_bottom))

        inner_pad_y = 3.5
        usable_h = max(8.0, trace_h - inner_pad_y * 2.0)

        pts_val = list(self.history)
        if len(pts_val) < self.max_points:
            pts_val = [0.0] * (self.max_points - len(pts_val)) + pts_val
        if pts_val:
            pts_val[-1] = self.display_percent

        n = len(pts_val)
        step_x = trace_w / max(1, n - 1)
        coords = []
        for i, v in enumerate(pts_val):
            px = trace_left + i * step_x
            raw_py = trace_top + inner_pad_y + (1.0 - max(0.0, min(100.0, float(v))) / 100.0) * usable_h
            py = max(trace_top + 2.5, min(trace_bottom - 2.5, raw_py))
            coords.append(QPointF(px, py))

        active_hex = metric_semantic_color(self.current_percent, self.base_color)
        line_col = hex_to_qcolor(active_hex, 240)

        if len(coords) >= 2:
            curve = QPainterPath(coords[0])
            for i in range(1, len(coords)):
                p0 = coords[i - 1]
                p1 = coords[i]
                cx = (p0.x() + p1.x()) * 0.5
                curve.cubicTo(QPointF(cx, p0.y()), QPointF(cx, p1.y()), p1)

            fill_path = QPainterPath(curve)
            fill_path.lineTo(coords[-1].x(), trace_bottom)
            fill_path.lineTo(coords[0].x(), trace_bottom)
            fill_path.closeSubpath()

            fill_grad = QLinearGradient(0.0, trace_top, 0.0, trace_bottom)
            fill_grad.setColorAt(0.0, hex_to_qcolor(active_hex, 28))
            fill_grad.setColorAt(1.0, hex_to_qcolor(active_hex, 0))
            painter.fillPath(fill_path, QBrush(fill_grad))

            painter.setPen(QPen(line_col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(curve)

            last_pt = coords[-1]
            painter.setPen(QPen(hex_to_qcolor(Theme.BG_PANEL, 230), 1.0))
            painter.setBrush(QBrush(line_col))
            painter.drawEllipse(last_pt, 2.5, 2.5)


WaveChart = TelemetryHeroCard
