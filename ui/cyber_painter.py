from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath, QLinearGradient, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF


class Theme:
    """Native frosted-glass & Apple iStat-inspired design tokens."""

    # Surfaces
    BG_PANEL = "#111215"
    BG_DIALOG = "#141518"
    BG_RECESSED = "#0D0E11"
    BG_RAISED = "#1B1D22"
    BG_RAISED_ALT = "#242730"
    BG_RAISED_HOVER = "#262932"

    # Frosted Borders & Tints
    TILE_DARK_BASE = (10, 11, 15, 86)
    TILE_BG = (255, 255, 255, 10)
    TILE_BORDER = (255, 255, 255, 22)
    BORDER_OUTER = (255, 255, 255, 24)
    BORDER_OUTER_CLEAR = (255, 255, 255, 38)
    BORDER_RULE = (255, 255, 255, 16)
    TOP_HIGHLIGHT = (255, 255, 255, 16)

    # Text Roles
    TEXT_PRIMARY = "#F4F4F6"
    TEXT_SECONDARY = "#C4C9D4"
    TEXT_MUTED = "#969CA8"

    # Accent & Meters
    ACCENT = "#7DB4FF"
    METER_NEUTRAL = "#94AFD4"

    # Semantic (meaning only)
    POSITIVE = "#4EC28B"
    WARNING = "#E6A23C"
    DANGER = "#E55353"

    # Typography
    FONT_UI = "MiSans"
    FONT_UI_CJK = "Microsoft YaHei UI"
    FONT_DISPLAY = "Segoe UI Variable Display"

    @staticmethod
    def ui_font(size_px: int = 13, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        f = QFont()
        f.setFamilies([Theme.FONT_UI, Theme.FONT_UI_CJK, "Segoe UI Variable Text", "Segoe UI"])
        f.setPixelSize(size_px)
        f.setWeight(weight)
        return f

    @staticmethod
    def display_font(size_px: int = 18, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        f = QFont()
        f.setFamilies([Theme.FONT_DISPLAY, Theme.FONT_UI, "Segoe UI"])
        f.setPixelSize(size_px)
        f.setWeight(weight)
        return f

    @staticmethod
    def num_font(size_px: int = 18, weight: QFont.Weight = QFont.Weight.Normal, condensed: bool = False) -> QFont:
        return Theme.display_font(size_px=size_px, weight=weight)

    @staticmethod
    def mono_font(size_px: int = 14, weight: QFont.Weight = QFont.Weight.Normal, condensed: bool = False) -> QFont:
        return Theme.display_font(size_px=size_px, weight=weight)


def parse_color(c_str, alpha=None):
    """Parse hex, rgb(), rgba(), tuple, or QColor into a QColor with optional alpha."""
    if isinstance(c_str, QColor):
        c = QColor(c_str)
        if alpha is not None:
            c.setAlpha(int(alpha))
        return c
    if isinstance(c_str, tuple) and len(c_str) in (3, 4):
        c = QColor(*c_str)
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


def metric_semantic_color(percent: float, base_color: str = Theme.TEXT_PRIMARY) -> str:
    """Return semantic warning/danger color only above load thresholds."""
    if percent >= 90.0:
        return Theme.DANGER
    if percent >= 75.0:
        return Theme.WARNING
    return base_color


class CyberPainter:
    """Native frosted-glass widget rendering utilities."""

    @staticmethod
    def draw_instrument_frame(painter: QPainter, rect: QRectF, bg_opacity: float = 0.85, radius: float = 14.0):
        """Render clean frosted charcoal surface with 14px corners and hairline catch."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bg_opacity = max(0.0, min(1.0, float(bg_opacity)))

        r = rect.adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)

        bg_alpha = int(255 * bg_opacity)
        if bg_alpha > 0:
            painter.fillPath(path, QBrush(hex_to_qcolor(Theme.BG_PANEL, bg_alpha)))

        if bg_opacity <= 0.02:
            border_rgba = (255, 255, 255, 22)
        elif bg_opacity < 0.45:
            border_rgba = Theme.BORDER_OUTER_CLEAR
        else:
            border_rgba = Theme.BORDER_OUTER

        painter.setPen(QPen(QColor(*border_rgba), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        if bg_opacity > 0.1:
            highlight_alpha = int(min(16, 8 + 10 * bg_opacity))
            painter.setPen(QPen(QColor(255, 255, 255, highlight_alpha), 1.0))
            painter.drawLine(
                QPointF(r.left() + radius, r.top() + 1.0),
                QPointF(r.right() - radius, r.top() + 1.0),
            )

    @staticmethod
    def draw_cyber_frame(
        painter: QPainter,
        rect: QRectF,
        bg_color=Theme.BG_PANEL,
        border_color=Theme.TEXT_PRIMARY,
        cut=14.0,
        bg_opacity=0.85,
    ):
        """Compatibility wrapper delegating to the native frosted frame."""
        CyberPainter.draw_instrument_frame(painter, rect, bg_opacity=bg_opacity, radius=14.0)

    @staticmethod
    def draw_tile_surface(painter: QPainter, rect: QRectF, radius: float = 8.0):
        """Render consistent smoked-frosted tile backing so metrics remain legible over any wallpaper."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        outer = rect.adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(*Theme.TILE_DARK_BASE)))
        painter.drawRoundedRect(outer, radius, radius)

        painter.setBrush(QBrush(QColor(*Theme.TILE_BG)))
        painter.setPen(QPen(QColor(*Theme.TILE_BORDER), 1.0))
        painter.drawRoundedRect(outer, radius, radius)

    @staticmethod
    def draw_integrated_fill(painter: QPainter, rect: QRectF, percent: float, radius: float = 8.0):
        """Render feathered tonal metric tile with clean inset 2.5px bottom precision rail."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pct = max(0.0, min(100.0, float(percent)))

        CyberPainter.draw_tile_surface(painter, rect, radius=radius)

        # 1. Soft feathered tonal wash inside clipped rounded tile (zero hard vertical cliff)
        if pct > 0.5:
            inner = rect.adjusted(1.0, 1.0, -1.0, -1.0)
            inner_r = max(2.0, radius - 1.0)
            clip_path = QPainterPath()
            clip_path.addRoundedRect(inner, inner_r, inner_r)

            painter.save()
            painter.setClipPath(clip_path)

            wash_w = max(8.0, inner.width() * (pct / 100.0))
            if pct >= 90.0:
                c0, c1, c2 = QColor(229, 83, 83, 14), QColor(229, 83, 83, 36), QColor(229, 83, 83, 0)
            elif pct >= 75.0:
                c0, c1, c2 = QColor(230, 162, 60, 12), QColor(230, 162, 60, 30), QColor(230, 162, 60, 0)
            else:
                c0, c1, c2 = QColor(148, 175, 212, 8), QColor(148, 175, 212, 20), QColor(148, 175, 212, 0)

            wash_grad = QLinearGradient(inner.left(), inner.top(), inner.left() + wash_w, inner.top())
            wash_grad.setColorAt(0.0, c0)
            wash_grad.setColorAt(0.82, c1)
            wash_grad.setColorAt(1.0, c2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(wash_grad))
            painter.drawRect(QRectF(inner.left(), inner.top(), wash_w, inner.height()))
            painter.restore()

        # 2. Dedicated inset 2.5px bottom precision rail (unclipped at 1% & 100%)
        pad_x = 10.0
        rail_x = rect.left() + pad_x
        rail_w = max(8.0, rect.width() - pad_x * 2.0)
        rail_h = 2.5
        rail_y = rect.bottom() - 6.0
        rail_r = 1.25

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
        painter.drawRoundedRect(QRectF(rail_x, rail_y, rail_w, rail_h), rail_r, rail_r)

        if pct > 0.2:
            fill_w = min(rail_w, max(3.5, rail_w * (pct / 100.0)))
            rail_grad = QLinearGradient(rail_x, rail_y, rail_x + fill_w, rail_y)
            if pct >= 90.0:
                rail_grad.setColorAt(0.0, QColor("#C83E3E"))
                rail_grad.setColorAt(1.0, QColor("#F57373"))
            elif pct >= 75.0:
                rail_grad.setColorAt(0.0, QColor("#C27D1E"))
                rail_grad.setColorAt(1.0, QColor("#F5B95A"))
            else:
                rail_grad.setColorAt(0.0, QColor("#5B8EC9"))
                rail_grad.setColorAt(1.0, QColor("#93C5FD"))
            painter.setBrush(QBrush(rail_grad))
            painter.drawRoundedRect(QRectF(rail_x, rail_y, fill_w, rail_h), rail_r, rail_r)

    @staticmethod
    def draw_segmented_bar(
        painter: QPainter,
        rect: QRectF,
        percent: float,
        color=Theme.ACCENT,
        warning_color=Theme.WARNING,
        danger_color=Theme.DANGER,
        total_segments=20,
    ):
        """Draw Style B ultra-thin precision rail (fallback utility)."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pct = max(0.0, min(100.0, float(percent)))
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        cy = y + h * 0.5

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
        painter.drawRoundedRect(QRectF(x, cy - 1.5, w, 3.0), 1.5, 1.5)

        if pct > 0.2:
            fw = max(3.0, w * (pct / 100.0))
            col = danger_color if pct >= 90 else (warning_color if pct >= 75 else color)
            painter.setBrush(QBrush(hex_to_qcolor(col, 230)))
            painter.drawRoundedRect(QRectF(x, cy - 1.5, fw, 3.0), 1.5, 1.5)
