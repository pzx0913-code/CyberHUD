from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont

from ui.cyber_painter import CyberPainter, Theme, hex_to_qcolor


class CyberNetRow(QWidget):
    """
    Twin side-by-side frosted speed tiles (Upload left, Download right).
    """

    def __init__(self, tag="NET", color=Theme.ACCENT, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.down_accent = color or Theme.ACCENT
        self.up_text = "0 B/s"
        self.down_text = "0 B/s"
        self.setFixedHeight(36)

    def update_speeds(self, up_text: str, down_text: str):
        changed = False
        if self.up_text != up_text:
            self.up_text = up_text
            changed = True
        if self.down_text != down_text:
            self.down_text = down_text
            changed = True
        if changed:
            self.update()

    def update_stat(self, text, *args, **kwargs):
        """Backward compatibility parser if called with formatted string."""
        if "▲" in text and "▼" in text:
            parts = text.split("▼")
            up_part = parts[0].replace("▲", "").strip()
            down_part = parts[1].strip()
            self.update_speeds(up_part, down_part)

    def _draw_arrow_up(self, painter: QPainter, cx: float, cy: float, color: QColor):
        pen = QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(cx, cy + 4.5), QPointF(cx, cy - 4.5))
        painter.drawLine(QPointF(cx - 3.0, cy - 1.2), QPointF(cx, cy - 4.5))
        painter.drawLine(QPointF(cx + 3.0, cy - 1.2), QPointF(cx, cy - 4.5))

    def _draw_arrow_down(self, painter: QPainter, cx: float, cy: float, color: QColor):
        pen = QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(cx, cy - 4.5), QPointF(cx, cy + 4.5))
        painter.drawLine(QPointF(cx - 3.0, cy + 1.2), QPointF(cx, cy + 4.5))
        painter.drawLine(QPointF(cx + 3.0, cy + 1.2), QPointF(cx, cy + 4.5))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        if w <= 20 or h <= 8:
            return

        gap = 8.0
        tile_w = (w - gap) * 0.5
        pad_x = 12.0
        cy = h * 0.5

        f_speed = Theme.display_font(14, QFont.Weight.Normal)
        painter.setFont(f_speed)

        # Left tile: Upload
        ul_rect = QRectF(0.0, 0.0, tile_w, h)
        CyberPainter.draw_tile_surface(painter, ul_rect, radius=8.0)

        self._draw_arrow_up(painter, pad_x + 4.0, cy, hex_to_qcolor(Theme.TEXT_MUTED, 255))
        painter.setPen(hex_to_qcolor(Theme.TEXT_PRIMARY, 255))
        painter.drawText(
            QRectF(pad_x + 14.0, 0.0, tile_w - pad_x * 2.0 - 14.0, h),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            self.up_text,
        )

        # Right tile: Download
        dl_left = tile_w + gap
        dl_rect = QRectF(dl_left, 0.0, tile_w, h)
        CyberPainter.draw_tile_surface(painter, dl_rect, radius=8.0)

        self._draw_arrow_down(painter, dl_left + pad_x + 4.0, cy, hex_to_qcolor(self.down_accent, 255))
        painter.setPen(hex_to_qcolor(Theme.TEXT_PRIMARY, 255))
        painter.drawText(
            QRectF(dl_left + pad_x + 14.0, 0.0, tile_w - pad_x * 2.0 - 14.0, h),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            self.down_text,
        )
