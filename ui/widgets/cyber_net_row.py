from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

class CyberNetRow(QWidget):
    """
    Fixed-column network speed telemetry row.
    Locks the positions of ▲ Upload and ▼ Download columns to prevent
    horizontal jittering as numeric values change.
    """
    def __init__(self, tag="NET", color="#00F3FF", parent=None):
        super().__init__(parent)
        self.tag = tag
        self.color = color
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 6)
        layout.setSpacing(0)

        # 1. Left Tag: [NET] (pinned at x=0..54)
        self.lbl_tag = QLabel(f"[{self.tag}]")
        self.lbl_tag.setFixedWidth(54)
        self.lbl_tag.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        layout.addWidget(self.lbl_tag)

        # 2. Upload Column (pinned at x=54..176)
        self.up_widget = QWidget()
        self.up_widget.setFixedWidth(122)
        up_layout = QHBoxLayout(self.up_widget)
        up_layout.setContentsMargins(0, 0, 0, 0)
        up_layout.setSpacing(6)

        self.lbl_up_icon = QLabel("▲")
        self.lbl_up_icon.setFixedWidth(12)
        self.lbl_up_icon.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        up_layout.addWidget(self.lbl_up_icon)

        self.lbl_up_speed = QLabel("0 B/s")
        self.lbl_up_speed.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        up_layout.addWidget(self.lbl_up_speed)
        layout.addWidget(self.up_widget)

        # 3. Download Column (pinned at x=176..298)
        self.down_widget = QWidget()
        self.down_widget.setFixedWidth(122)
        down_layout = QHBoxLayout(self.down_widget)
        down_layout.setContentsMargins(0, 0, 0, 0)
        down_layout.setSpacing(6)

        self.lbl_down_icon = QLabel("▼")
        self.lbl_down_icon.setFixedWidth(12)
        self.lbl_down_icon.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        down_layout.addWidget(self.lbl_down_icon)

        self.lbl_down_speed = QLabel("0 B/s")
        self.lbl_down_speed.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        down_layout.addWidget(self.lbl_down_speed)
        layout.addWidget(self.down_widget)

    def update_speeds(self, up_text: str, down_text: str):
        if self.lbl_up_speed.text() != up_text:
            self.lbl_up_speed.setText(up_text)
        if self.lbl_down_speed.text() != down_text:
            self.lbl_down_speed.setText(down_text)

    def update_stat(self, text, *args, **kwargs):
        """Backward compatibility parser if called with formatted string."""
        if "▲" in text and "▼" in text:
            parts = text.split("▼")
            up_part = parts[0].replace("▲", "").strip()
            down_part = parts[1].strip()
            self.update_speeds(up_part, down_part)
