from collections import deque
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient
from PyQt6.QtCore import Qt, QPointF, QRectF
from ui.cyber_painter import hex_to_qcolor

class WaveChart(QWidget):
    def __init__(self, max_points=38, line_color="#00F3FF", parent=None):
        super().__init__(parent)
        self.max_points = max_points
        self.line_color = line_color
        self.history = deque([0.0] * max_points, maxlen=max_points)
        self.setFixedHeight(76)

    def add_point(self, val):
        val = max(0.0, min(100.0, float(val)))
        self.history.append(val)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        # 1. Subtle Cyber Background Grid
        grid_pen = QPen(hex_to_qcolor("#1B2A4A", 80), 0.9, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        painter.drawLine(0, int(h * 0.5), w, int(h * 0.5))

        # 2. Build curve path
        pts = list(self.history)
        step_x = w / max(1, (self.max_points - 1))
        
        path = QPainterPath()
        first_pt = QPointF(0, h - (pts[0] / 100.0) * (h - 10) - 5)
        path.moveTo(first_pt)

        points = []
        for i, val in enumerate(pts):
            px = i * step_x
            py = h - (val / 100.0) * (h - 10) - 5
            pt = QPointF(px, py)
            points.append(pt)
            if i > 0:
                path.lineTo(pt)

        # 3. Fill Gradient under the line
        fill_path = QPainterPath(path)
        fill_path.lineTo(w, h)
        fill_path.lineTo(0, h)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, hex_to_qcolor(self.line_color, 110))
        grad.setColorAt(1.0, hex_to_qcolor(self.line_color, 0))
        painter.fillPath(fill_path, QBrush(grad))

        # 4. Neon Outer Glow Line
        glow_pen = QPen(hex_to_qcolor(self.line_color, 90), 4.2)
        painter.setPen(glow_pen)
        painter.drawPath(path)

        # 5. Crisp Front Line
        front_pen = QPen(hex_to_qcolor(self.line_color, 255), 2.4)
        painter.setPen(front_pen)
        painter.drawPath(path)

        # 6. Glowing dot at latest point
        if points:
            last_pt = points[-1]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(hex_to_qcolor(self.line_color, 150)))
            painter.drawEllipse(last_pt, 6.0, 6.0)
            painter.setBrush(QBrush(hex_to_qcolor("#FFFFFF", 255)))
            painter.drawEllipse(last_pt, 3.0, 3.0)
