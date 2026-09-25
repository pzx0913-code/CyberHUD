from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath, QLinearGradient, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF

def parse_color(c_str, alpha=None):
    if isinstance(c_str, QColor):
        c = QColor(c_str)
        if alpha is not None:
            c.setAlpha(int(alpha))
        return c
    c_str = str(c_str).strip()
    if c_str.startswith("rgba(") and c_str.endswith(")"):
        parts = c_str[5:-1].split(",")
        if len(parts) == 4:
            r = int(parts[0].strip())
            g = int(parts[1].strip())
            b = int(parts[2].strip())
            a_val = float(parts[3].strip())
            a = int(a_val * 255) if a_val <= 1.0 else int(a_val)
            c = QColor(r, g, b, a)
            if alpha is not None:
                c.setAlpha(int(alpha))
            return c
    elif c_str.startswith("rgb(") and c_str.endswith(")"):
        parts = c_str[4:-1].split(",")
        if len(parts) == 3:
            r = int(parts[0].strip())
            g = int(parts[1].strip())
            b = int(parts[2].strip())
            c = QColor(r, g, b)
            if alpha is not None:
                c.setAlpha(int(alpha))
            return c
    c = QColor(c_str)
    if alpha is not None:
        c.setAlpha(int(alpha))
    return c

def hex_to_qcolor(hex_str, alpha=255):
    return parse_color(hex_str, alpha)

class CyberPainter:
    """Helper utilities for rendering Cyberpunk HUD elements."""

    @staticmethod
    def get_chamfered_path(rect: QRectF, cut=20.0):
        """Creates a polygon path with 45-degree chamfered corners."""
        path = QPainterPath()
        x = rect.x()
        y = rect.y()
        w = rect.width()
        h = rect.height()

        path.moveTo(x + cut, y)
        path.lineTo(x + w - cut, y)
        path.lineTo(x + w, y + cut)
        path.lineTo(x + w, y + h - cut)
        path.lineTo(x + w - cut, y + h)
        path.lineTo(x + cut, y + h)
        path.lineTo(x, y + h - cut)
        path.lineTo(x, y + cut)
        path.closeSubpath()
        return path

    @staticmethod
    def draw_cyber_frame(painter: QPainter, rect: QRectF, bg_color="#0A0D18", border_color="#00F3FF", cut=20.0, bg_opacity=0.65):
        """Renders cyberpunk chamfered panel with neon borders and corner brackets."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        path = CyberPainter.get_chamfered_path(rect, cut)
        
        # 1. Background fill (independent opacity: text & borders remain solid)
        bg_alpha = int(255 * max(0.0, min(1.0, bg_opacity)))
        if bg_alpha > 0:
            bg = hex_to_qcolor(bg_color, bg_alpha)
            painter.fillPath(path, QBrush(bg))

        # 2. Outer Glow
        glow_pen = QPen(hex_to_qcolor(border_color, 55), 4.0)
        painter.setPen(glow_pen)
        painter.drawPath(path)

        # 3. Main Sharp Border (Always solid neon)
        main_pen = QPen(hex_to_qcolor(border_color, 230), 2.0)
        painter.setPen(main_pen)
        painter.drawPath(path)

        # 4. Corner Decal Accents (Tech brackets)
        accent_pen = QPen(hex_to_qcolor(border_color, 255), 3.0)
        painter.setPen(accent_pen)
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        arm = 16.0

        # Top-Left bracket
        painter.drawLine(QPointF(x + cut, y), QPointF(x + cut + arm, y))
        painter.drawLine(QPointF(x, y + cut), QPointF(x, y + cut + arm))

        # Bottom-Right bracket
        painter.drawLine(QPointF(x + w - cut - arm, y + h), QPointF(x + w - cut, y + h))
        painter.drawLine(QPointF(x + w, y + h - cut - arm), QPointF(x + w, y + h - cut))

        # 5. Header Decorative Notches
        notch_pen = QPen(hex_to_qcolor("#FF0055", 220), 2.0)
        painter.setPen(notch_pen)
        notch_x = x + w - cut - 52
        painter.drawLine(QPointF(notch_x, y + 4), QPointF(notch_x + 14, y + 4))
        painter.drawLine(QPointF(notch_x + 18, y + 4), QPointF(notch_x + 26, y + 4))

    @staticmethod
    def draw_segmented_bar(painter: QPainter, rect: QRectF, percent: float, color="#00F3FF", warning_color="#FFB800", danger_color="#FF0055", total_segments=22):
        """Draws high-tech Cyberpunk Plasma Energy Blades with calibration ticks and laser core."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        percent = max(0.0, min(100.0, percent))
        
        # Multi-stage color shifting
        active_color = color
        if percent >= 85.0:
            active_color = danger_color
        elif percent >= 65.0:
            active_color = warning_color

        active_count = int(round((percent / 100.0) * total_segments))
        
        x = rect.x()
        y = rect.y()
        w = rect.width()
        h = rect.height()
        
        bar_h = max(10.0, h - 4.5)  # leave 4.5px at bottom for micro calibration ruler
        seg_gap = 3.2
        seg_w = (w - (total_segments - 1) * seg_gap) / total_segments
        slant = 4.0

        # 1. Micro Calibration Ruler & End Brackets underneath
        ruler_y = y + bar_h + 2.5
        ruler_pen = QPen(hex_to_qcolor("#1B2942", 170), 1.0)
        painter.setPen(ruler_pen)
        painter.drawLine(QPointF(x, ruler_y), QPointF(x + w + slant, ruler_y))

        # Calibration tick marks at 0%, 25%, 50%, 75%, 100%
        tick_pen = QPen(hex_to_qcolor("#2E4368", 220), 1.0)
        painter.setPen(tick_pen)
        for pct in [0.0, 0.25, 0.5, 0.75, 1.0]:
            tx = x + pct * w + (pct * slant)
            painter.drawLine(QPointF(tx, ruler_y - 1.5), QPointF(tx, ruler_y + 2.5))

        # Outer framing brackets on left & right ends
        bracket_pen = QPen(hex_to_qcolor(color, 110), 1.2)
        painter.setPen(bracket_pen)
        painter.drawLine(QPointF(x - 2, y + 1), QPointF(x - 2, y + bar_h - 1))
        painter.drawLine(QPointF(x + w + slant + 2, y + 1), QPointF(x + w + slant + 2, y + bar_h - 1))

        # 2. Draw Plasma Energy Cells
        for i in range(total_segments):
            sx = x + i * (seg_w + seg_gap)
            sy = y

            # Angled sci-fi blade polygon
            seg_path = QPainterPath()
            seg_path.moveTo(sx + slant, sy)
            seg_path.lineTo(sx + seg_w + slant, sy)
            seg_path.lineTo(sx + seg_w, sy + bar_h)
            seg_path.lineTo(sx, sy + bar_h)
            seg_path.closeSubpath()

            if i < active_count:
                is_head = (i == active_count - 1)
                
                # Active cell body gradient
                grad = QLinearGradient(sx, sy, sx, sy + bar_h)
                if is_head:
                    grad.setColorAt(0.0, hex_to_qcolor("#FFFFFF", 255))
                    grad.setColorAt(0.35, hex_to_qcolor(active_color, 255))
                    grad.setColorAt(1.0, hex_to_qcolor(active_color, 210))
                else:
                    grad.setColorAt(0.0, hex_to_qcolor(active_color, 230))
                    grad.setColorAt(0.5, hex_to_qcolor(active_color, 255))
                    grad.setColorAt(1.0, hex_to_qcolor(active_color, 180))
                
                painter.fillPath(seg_path, QBrush(grad))

                # Neon sharp cell border
                cell_border_pen = QPen(hex_to_qcolor(active_color, 255), 1.0)
                painter.setPen(cell_border_pen)
                painter.drawPath(seg_path)

                # Inner laser core filament (Horizontal energized plasma line)
                laser_y = sy + bar_h * 0.5
                laser_pen = QPen(hex_to_qcolor("#FFFFFF", 240 if is_head else 160), 1.2)
                painter.setPen(laser_pen)
                painter.drawLine(QPointF(sx + slant * 0.5 + 1.5, laser_y), QPointF(sx + seg_w + slant * 0.5 - 1.5, laser_y))

                # Outer bloom glow for head segment
                if is_head:
                    bloom_pen = QPen(hex_to_qcolor(active_color, 100), 2.8)
                    painter.setPen(bloom_pen)
                    painter.drawPath(seg_path)

            else:
                # Inactive dark slot
                painter.fillPath(seg_path, QBrush(hex_to_qcolor("#0B111D", 140)))
                painter.setPen(QPen(hex_to_qcolor("#1A263D", 140), 1.0))
                painter.drawPath(seg_path)

                # Dim uncharged conduit slot hairline
                dim_y = sy + bar_h * 0.5
                painter.setPen(QPen(hex_to_qcolor("#18243A", 110), 1.0))
                painter.drawLine(QPointF(sx + slant * 0.5 + 2.0, dim_y), QPointF(sx + seg_w + slant * 0.5 - 2.0, dim_y))
