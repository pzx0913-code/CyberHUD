from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QBrush, QFont, QColor

from ui.cyber_painter import Theme, hex_to_qcolor


class StatRow(QWidget):
    """
    Minimal remote node header: Node name left, compact ms latency + status dot + state right.
    """

    def __init__(self, tag="VPS", color=Theme.TEXT_PRIMARY, show_bar=False, parent=None):
        super().__init__(parent)
        self.tag_text = self._clean_tag(tag)
        self.detail_text = "--"
        self.value_text = "待机"
        self.status_color = Theme.WARNING
        self.show_bar = show_bar
        self.setFixedHeight(22)

    @staticmethod
    def _clean_tag(text: str) -> str:
        s = str(text).strip()
        if s.startswith("[") and s.endswith("]") and len(s) >= 2:
            s = s[1:-1].strip()
        return s

    def set_tag_text(self, text: str):
        cleaned = self._clean_tag(text)
        if self.tag_text != cleaned:
            self.tag_text = cleaned
            self.update()

    def update_stat(self, value_text: str, detail_text: str = "", percent: float = 0.0, custom_color: str = None):
        changed = False
        if self.value_text != value_text:
            self.value_text = value_text
            changed = True
        if detail_text is not None and self.detail_text != detail_text:
            self.detail_text = detail_text
            changed = True
        if custom_color and self.status_color != custom_color:
            self.status_color = custom_color
            changed = True
        if changed:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        if w <= 10 or h <= 4:
            return

        # 1. Rightmost status label
        painter.setFont(Theme.ui_font(12, QFont.Weight.Normal))
        status_w = painter.fontMetrics().horizontalAdvance(self.value_text)
        status_rect = QRectF(w - status_w, 0.0, status_w, h)
        status_qcol = hex_to_qcolor(self.status_color, 255)
        painter.setPen(status_qcol)
        painter.drawText(status_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.value_text)

        # 2. Live status dot (6px diameter, 5px left of status text)
        dot_cx = w - status_w - 5.0 - 3.0
        dot_cy = h * 0.5
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(status_qcol))
        painter.drawEllipse(QPointF(dot_cx, dot_cy), 3.0, 3.0)

        # 3. Latency detail (10px left of dot)
        detail_w = 0.0
        if self.detail_text:
            painter.setFont(Theme.display_font(13, QFont.Weight.Normal))
            detail_w = painter.fontMetrics().horizontalAdvance(self.detail_text)
            detail_right = dot_cx - 3.0 - 10.0
            detail_rect = QRectF(0.0, 0.0, max(0.0, detail_right), h)
            painter.setPen(hex_to_qcolor(Theme.TEXT_MUTED, 255))
            painter.drawText(detail_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.detail_text)

        # 4. Node Name on left
        right_reserved = status_w + 5.0 + 6.0 + (10.0 + detail_w + 10.0 if detail_w else 10.0)
        name_max_w = max(56.0, w - right_reserved)
        painter.setFont(Theme.display_font(13, QFont.Weight.Medium))
        elided_name = painter.fontMetrics().elidedText(self.tag_text, Qt.TextElideMode.ElideRight, int(name_max_w))
        painter.setPen(QColor("#E4E7EE"))
        painter.drawText(QRectF(0.0, 0.0, name_max_w, h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_name)
