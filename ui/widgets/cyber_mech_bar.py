from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics

from ui.cyber_painter import CyberPainter, Theme, hex_to_qcolor, metric_semantic_color


class CyberMechBar(QWidget):
    """
    Style C Integrated Tinted-Fill Metric Tile.
    - layout_mode="row": Full-width 42px metric row (label left, detail + % right).
    - layout_mode="tile": Side-by-side 54px compact tile (label + detail top, 20px % bottom).
    """

    def __init__(
        self,
        tag="内存",
        detail="",
        layout_mode=None,
        compact=False,
        accent_mode="neutral",
        rail_color=None,
        blade_color=None,
        color=None,
        parent=None,
        **kwargs,
    ):
        super().__init__(parent)
        self.tag = tag
        self.detail = detail
        self.layout_mode = layout_mode if layout_mode in ("row", "tile") else ("tile" if compact else "row")
        self.accent_mode = accent_mode
        self.value_text = "0%"
        self.percent = 0.0
        self.display_percent = 0.0

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._step_anim)

        self.setFixedHeight(56 if self.layout_mode == "tile" else 44)

    def _step_anim(self):
        diff = self.percent - self.display_percent
        if abs(diff) <= 0.25:
            self.display_percent = self.percent
            self._anim_timer.stop()
        else:
            self.display_percent += diff * 0.28
        self.update()

    def set_tag(self, tag: str):
        if self.tag != tag:
            self.tag = tag
            self.update()

    def update_data(self, percent: float, value_text: str = None, detail_text: str = None, animate: bool = True):
        percent = max(0.0, min(100.0, float(percent)))
        changed = False

        if abs(self.percent - percent) > 0.05:
            self.percent = percent
            changed = True

        new_val_text = value_text if value_text is not None else f"{round(percent)}%"
        if self.value_text != new_val_text:
            self.value_text = new_val_text
            changed = True

        if detail_text is not None and self.detail != detail_text:
            self.detail = detail_text
            changed = True

        if not animate:
            self._anim_timer.stop()
            if abs(self.display_percent - self.percent) > 0.05:
                self.display_percent = self.percent
                changed = True
        elif changed and abs(self.percent - self.display_percent) > 0.25:
            if not self._anim_timer.isActive():
                self._anim_timer.start()

        if changed:
            self.update()

    def flush_animation(self):
        self._anim_timer.stop()
        self.display_percent = self.percent
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        if w <= 10 or h <= 10:
            return

        CyberPainter.draw_integrated_fill(painter, QRectF(0.0, 0.0, w, h), self.display_percent, radius=8.0)

        if self.layout_mode == "tile":
            self._paint_tile(painter, w, h)
        else:
            self._paint_row(painter, w, h)

    def _paint_row(self, painter: QPainter, w: float, h: float):
        pad_x = 12.0
        pct_col_w = 46.0
        content_h = h - 7.0

        f_num = Theme.display_font(18, QFont.Weight.Normal)
        f_unit = Theme.display_font(12, QFont.Weight.Normal)
        fm_num = QFontMetrics(f_num)
        fm_unit = QFontMetrics(f_unit)
        baseline_y = (content_h + fm_num.capHeight()) * 0.5 + 1.0

        val_str = self.value_text
        if val_str.endswith("%"):
            num_str = val_str[:-1]
            unit_w = fm_unit.horizontalAdvance("%")
            num_w = fm_num.horizontalAdvance(num_str)
            pct_hex = metric_semantic_color(self.percent, Theme.TEXT_PRIMARY)

            painter.setFont(f_unit)
            painter.setPen(hex_to_qcolor(Theme.TEXT_MUTED, 255))
            painter.drawText(QPointF(w - pad_x - unit_w, baseline_y), "%")

            painter.setFont(f_num)
            painter.setPen(hex_to_qcolor(pct_hex, 255))
            painter.drawText(QPointF(w - pad_x - unit_w - 0.5 - num_w, baseline_y), num_str)
        else:
            f_txt = Theme.ui_font(13, QFont.Weight.Normal)
            painter.setFont(f_txt)
            painter.setPen(hex_to_qcolor(Theme.TEXT_MUTED, 255))
            tw = painter.fontMetrics().horizontalAdvance(val_str)
            painter.drawText(QPointF(w - pad_x - tw, baseline_y), val_str)

        detail_w = 0.0
        if self.detail:
            f_det = Theme.display_font(13, QFont.Weight.Normal)
            painter.setFont(f_det)
            detail_w = painter.fontMetrics().horizontalAdvance(self.detail)
            detail_x = max(pad_x + 48.0, w - pad_x - pct_col_w - 10.0 - detail_w)
            painter.setPen(hex_to_qcolor(Theme.TEXT_MUTED, 255))
            painter.drawText(QPointF(detail_x, baseline_y), self.detail)

        label_max_w = max(56.0, w - pad_x * 2.0 - pct_col_w - (detail_w + 20.0 if detail_w else 10.0))
        painter.setFont(Theme.ui_font(14, QFont.Weight.Normal))
        label_elided = painter.fontMetrics().elidedText(self.tag, Qt.TextElideMode.ElideRight, int(label_max_w))
        painter.setPen(QColor("#E8EAEF"))
        painter.drawText(QPointF(pad_x, baseline_y), label_elided)

    def _paint_tile(self, painter: QPainter, w: float, h: float):
        pad_x = 12.0

        # Top row (y = 6..21): tag left, detail right
        painter.setFont(Theme.display_font(11, QFont.Weight.Normal))
        det_w = 0.0
        max_det_w = max(0.0, w - pad_x * 2.0 - 44.0)
        if self.detail:
            det_elided = painter.fontMetrics().elidedText(self.detail, Qt.TextElideMode.ElideRight, int(max_det_w))
            det_w = painter.fontMetrics().horizontalAdvance(det_elided)
            painter.setPen(hex_to_qcolor(Theme.TEXT_MUTED, 255))
            painter.drawText(QRectF(pad_x, 6.0, w - pad_x * 2.0, 15.0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, det_elided)

        tag_max_w = max(32.0, w - pad_x * 2.0 - (det_w + 8.0 if det_w else 0.0))
        painter.setFont(Theme.ui_font(12, QFont.Weight.Normal))
        tag_elided = painter.fontMetrics().elidedText(self.tag, Qt.TextElideMode.ElideRight, int(tag_max_w))
        painter.setPen(hex_to_qcolor(Theme.TEXT_SECONDARY, 255))
        painter.drawText(QRectF(pad_x, 6.0, tag_max_w, 15.0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, tag_elided)

        # Bottom row above 2.5px rail: 20px Regular display figure + 0.5px + 12px %
        val_str = self.value_text
        baseline_y = 43.0
        if val_str.endswith("%"):
            num_str = val_str[:-1]
            f_num = Theme.display_font(20, QFont.Weight.Normal)
            f_unit = Theme.display_font(12, QFont.Weight.Normal)
            fm_num = QFontMetrics(f_num)
            num_w = fm_num.horizontalAdvance(num_str)
            pct_hex = metric_semantic_color(self.percent, Theme.TEXT_PRIMARY)

            painter.setFont(f_num)
            painter.setPen(hex_to_qcolor(pct_hex, 255))
            painter.drawText(QPointF(pad_x, baseline_y), num_str)

            painter.setFont(f_unit)
            painter.setPen(hex_to_qcolor(Theme.TEXT_MUTED, 255))
            painter.drawText(QPointF(pad_x + num_w + 0.5, baseline_y), "%")
        else:
            painter.setFont(Theme.ui_font(15, QFont.Weight.Normal))
            painter.setPen(hex_to_qcolor(Theme.TEXT_MUTED, 255))
            painter.drawText(QPointF(pad_x, baseline_y), val_str)
