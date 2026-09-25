import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient, QFont, QFontMetrics
)
from ui.cyber_painter import parse_color, hex_to_qcolor

class CyberMechBar(QWidget):
    """
    Cyberpunk Mecha Dual-Rail Gauge Bar.
    - Clean vertical separation between Tag label and circular radial ticks (no overlap).
    - Full-width mecha blade track spanning to the right edge.
    - Active blades solidly fill the entire cell and MATCH the progress bar's theme color.
    - Center percentage number in light blue (#00F3FF) matching the border.
    - Stepped chamfered mecha tail frame on the right.
    """
    def __init__(self, tag="CPU", detail="", rail_color=None, blade_color=None, color=None, parent=None, **kwargs):
        super().__init__(parent)
        self.tag = tag
        self.detail = detail
        self.value_text = "0%"
        self.percent = 0.0
        
        # Theme rail & tick color (e.g. #FF8833 for orange, #FF3366 for pink)
        self.rail_color = rail_color or color or "#FF8833"
        # Lit blades match the bar's theme color!
        self.blade_color = blade_color or self.rail_color
        self.total_blades = 18
        self.setFixedHeight(70)                                     # Spacious height for enlarged dial and separated rails

    def _get_body_color(self, hex_color):
        """Calibrates tube body darkness so white-hot core filament has equal punch across all colors."""
        c = hex_to_qcolor(hex_color)
        lum = 0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()
        if lum > 135:
            factor = 135.0 / lum
            return hex_to_qcolor(f"#{int(c.red() * factor):02x}{int(c.green() * factor):02x}{int(c.blue() * factor):02x}", 255)
        return hex_to_qcolor(hex_color, 255)

    def update_data(self, percent: float, value_text: str = None, detail_text: str = None):
        percent = max(0.0, min(100.0, float(percent)))
        changed = False
        if abs(self.percent - percent) > 0.1:
            self.percent = percent
            changed = True
        
        new_val_text = value_text if value_text is not None else f"{round(percent)}%"
        if self.value_text != new_val_text:
            self.value_text = new_val_text
            changed = True
            
        if detail_text is not None and self.detail != detail_text:
            self.detail = detail_text
            changed = True
            
        if changed:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # --- 0. Top Label Row: Tag & Detail (Clear separation above dial) ---
        # Tag text at y = 12
        painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        painter.setPen(hex_to_qcolor(self.rail_color, 240))
        painter.drawText(QPointF(4, 12), f"[{self.tag}]")

        # Detail text in matching light blue (#00F3FF)
        if self.detail:
            painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            painter.setPen(hex_to_qcolor("#00F3FF", 220))
            painter.drawText(QRectF(60, 0, w - 66, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.detail)

        # --- Geometry Setup (Enlarged Circular Dial) ---
        gauge_y_center = 43.0
        circle_cx = 26.0
        outer_r = 19.5
        inner_r = 16.0

        # --- 1. Left Concentric Circle Core ---
        # A. Outer circular ring (Dim warm theme color)
        outer_ring_pen = QPen(hex_to_qcolor(self.rail_color, 110), 1.4)
        painter.setPen(outer_ring_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(circle_cx, gauge_y_center), outer_r, outer_r)

        # B. Top-Left Arc Radial Ticks (9 ticks, 102° to 180°) with glowing neon bloom
        tick_count = 9
        start_angle = 102.0
        end_angle = 180.0
        for i in range(tick_count):
            deg = start_angle + i * ((end_angle - start_angle) / (tick_count - 1))
            rad = math.radians(deg)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            p1 = QPointF(circle_cx + (outer_r + 1.2) * cos_a, gauge_y_center - (outer_r + 1.2) * sin_a)
            p2 = QPointF(circle_cx + (outer_r + 4.8) * cos_a, gauge_y_center - (outer_r + 4.8) * sin_a)
            
            # Bloom halo
            painter.setPen(QPen(hex_to_qcolor(self.rail_color, 65), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(p1, p2)
            # Saturated core
            painter.setPen(QPen(hex_to_qcolor(self.rail_color, 255), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(p1, p2)
            # White-hot tip highlight
            painter.setPen(QPen(hex_to_qcolor('#FFFFFF', 200), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine((p1 + p2) * 0.5, p2)

        # C. Inner Dark Disc Fill & Border (with subtle ambient glow behind text)
        disc_glow = QLinearGradient(circle_cx - inner_r, gauge_y_center, circle_cx + inner_r, gauge_y_center)
        disc_glow.setColorAt(0.0, hex_to_qcolor("#03070D", 255))
        disc_glow.setColorAt(0.5, hex_to_qcolor(self.rail_color, 45))
        disc_glow.setColorAt(1.0, hex_to_qcolor("#03070D", 255))
        painter.setBrush(QBrush(disc_glow))
        inner_pen = QPen(hex_to_qcolor(self.rail_color, 180), 1.3)
        painter.setPen(inner_pen)
        painter.drawEllipse(QPointF(circle_cx, gauge_y_center), inner_r, inner_r)

        # D. Center Percentage Text (Delicate 9pt font with cyan neon bloom)
        font_size = 9 if len(self.value_text) <= 3 else 8
        painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
        text_rect = QRectF(circle_cx - inner_r, gauge_y_center - inner_r, inner_r * 2, inner_r * 2)
        
        # Soft cyan text bloom
        painter.setPen(hex_to_qcolor("#00F3FF", 55))
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            painter.drawText(text_rect.translated(dx, dy), Qt.AlignmentFlag.AlignCenter, self.value_text)
            
        # Crisp light text
        painter.setPen(hex_to_qcolor("#E0FFFF", 255))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.value_text)

        # --- 2. Track & Slashes (一条条发光斜线) ---
        bar_start_x = circle_cx + inner_r + 5.0
        bar_y_top = gauge_y_center - 7.5
        bar_y_bottom = gauge_y_center + 7.5
        bar_h = bar_y_bottom - bar_y_top
        tail_w = 34.0
        available_track_w = max(120.0, w - bar_start_x - tail_w - 6.0)

        slant = 7.5
        slash_w = 4.2
        slash_gap = 5.2
        total_slashes = int(available_track_w / (slash_w + slash_gap))
        actual_gap = (available_track_w - total_slashes * slash_w) / max(1, total_slashes - 1)

        # Outer mecha track frame with aerodynamic fin tail
        x_tail_end = bar_start_x + available_track_w + tail_w
        track_path = QPainterPath()
        track_path.moveTo(bar_start_x + slant - 2.0, bar_y_top - 1.2)
        track_path.lineTo(x_tail_end, bar_y_top - 1.2)
        track_path.lineTo(x_tail_end - 9.0, bar_y_top + 4.2)
        track_path.lineTo(x_tail_end - 28.0, bar_y_top + 4.2)
        track_path.lineTo(x_tail_end - 38.0, bar_y_bottom + 1.2)
        track_path.lineTo(bar_start_x - 2.0, bar_y_bottom + 1.2)
        track_path.closeSubpath()

        # Translucent frosted mecha track frame (透明磨砂机甲底槽)
        track_grad = QLinearGradient(bar_start_x, bar_y_top, bar_start_x + available_track_w, bar_y_bottom)
        track_grad.setColorAt(0.0, hex_to_qcolor("#08121E", 55))
        track_grad.setColorAt(1.0, hex_to_qcolor("#0E1C2E", 70))
        painter.setBrush(QBrush(track_grad))
        painter.setPen(QPen(hex_to_qcolor("#223B58", 85), 1.0))
        painter.drawPath(track_path)

        # Floating upper and lower decorative neon tubes (with radiant bloom!)
        rail_body_col = self._get_body_color(self.rail_color)
        rail_top_y = bar_y_top - 6.5
        rail_top_len = available_track_w * 0.60
        p_top_start = QPointF(bar_start_x - 1.0, rail_top_y)
        p_top_end = QPointF(bar_start_x + rail_top_len, rail_top_y)

        # Top rail bloom halo
        painter.setPen(QPen(hex_to_qcolor(self.rail_color, 45), 5.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p_top_start, p_top_end)
        # Top rail neon body
        painter.setPen(QPen(rail_body_col, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p_top_start, p_top_end)
        # Top rail white-hot core filament
        painter.setPen(QPen(hex_to_qcolor('#FFFFFF', 230), 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p_top_start, QPointF(bar_start_x + rail_top_len - 4.0, rail_top_y))

        # Bottom rail
        rail_bottom_y = bar_y_bottom + 6.5
        rail_bottom_len = available_track_w * 0.42
        p_bot_start = QPointF(bar_start_x - 1.0, rail_bottom_y)
        p_bot_end = QPointF(bar_start_x + rail_bottom_len, rail_bottom_y)

        # Bottom rail bloom halo
        painter.setPen(QPen(hex_to_qcolor(self.rail_color, 45), 5.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p_bot_start, p_bot_end)
        # Bottom rail neon body
        painter.setPen(QPen(rail_body_col, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p_bot_start, p_bot_end)
        # Bottom rail white-hot core filament
        painter.setPen(QPen(hex_to_qcolor('#FFFFFF', 230), 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p_bot_start, QPointF(bar_start_x + rail_bottom_len - 4.0, rail_bottom_y))

        # --- 3. Luminous Neon Tube Slashes (有光晕发光霓虹灯管) ---
        active_count = int(round((self.percent / 100.0) * total_slashes))
        blade_body_col = self._get_body_color(self.blade_color)

        # Pass 1: Soft radiant bloom halos for all active neon slashes
        for i in range(active_count):
            sx = bar_start_x + 1.5 + i * (slash_w + actual_gap)
            p_t = QPointF(sx + slash_w * 0.5 + slant, bar_y_top + 1.0)
            p_b = QPointF(sx + slash_w * 0.5, bar_y_bottom - 1.0)
            
            # Wide outer bloom
            painter.setPen(QPen(hex_to_qcolor(self.blade_color, 40), 8.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(p_t, p_b)
            # Mid-layer aura
            painter.setPen(QPen(hex_to_qcolor(self.blade_color, 95), 5.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(p_t, p_b)

        # Pass 2: Draw tube bodies and white-hot filaments (or inactive slots)
        for i in range(total_slashes):
            sx = bar_start_x + 1.5 + i * (slash_w + actual_gap)
            s_path = QPainterPath()
            s_path.moveTo(sx + slant, bar_y_top + 1.0)
            s_path.lineTo(sx + slash_w + slant, bar_y_top + 1.0)
            s_path.lineTo(sx + slash_w, bar_y_bottom - 1.0)
            s_path.lineTo(sx, bar_y_bottom - 1.0)
            s_path.closeSubpath()

            p_t = QPointF(sx + slash_w * 0.5 + slant, bar_y_top + 1.5)
            p_b = QPointF(sx + slash_w * 0.5, bar_y_bottom - 1.5)

            if i < active_count:
                # Saturated neon tube body
                painter.setBrush(QBrush(blade_body_col))
                painter.setPen(QPen(blade_body_col, 1.0))
                painter.drawPath(s_path)
                
                # White-hot plasma core filament
                painter.setPen(QPen(hex_to_qcolor('#FFFFFF', 255), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(p_t, p_b)
            else:
                # Inactive translucent frosted slash slot (透明磨砂未激活暗格)
                painter.setBrush(QBrush(hex_to_qcolor('#0D1B2A', 40)))
                painter.setPen(QPen(hex_to_qcolor('#1C324A', 70), 1.0))
                painter.drawPath(s_path)
