from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainter
from ui.cyber_painter import CyberPainter

class CyberBar(QWidget):
    def __init__(self, color="#00F3FF", warning_color="#FFB800", danger_color="#FF0055", segments=22, parent=None):
        super().__init__(parent)
        self.value = 0.0
        self.color = color
        self.warning_color = warning_color
        self.danger_color = danger_color
        self.segments = segments
        self.setFixedHeight(20)

    def set_value(self, val):
        val = max(0.0, min(100.0, float(val)))
        if abs(self.value - val) > 0.1:
            self.value = val
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = QRectF(0, 0, self.width(), self.height())
        CyberPainter.draw_segmented_bar(
            painter,
            rect,
            self.value,
            color=self.color,
            warning_color=self.warning_color,
            danger_color=self.danger_color,
            total_segments=self.segments
        )
