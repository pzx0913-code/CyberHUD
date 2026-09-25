from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ui.widgets.cyber_bar import CyberBar

class StatRow(QWidget):
    def __init__(self, tag="CPU", color="#00F3FF", show_bar=True, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.color = color
        self.show_bar = show_bar
        self.current_color = "#FFFFFF"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 6)
        layout.setSpacing(5)

        # Header Row: [TAG]    [Detail]  [Main Value]
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Tag label
        self.lbl_tag = QLabel(f"[{self.tag}]")
        self.lbl_tag.setWordWrap(False)
        self.lbl_tag.setStyleSheet(f"""
            QLabel {{
                color: {self.color};
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        header_layout.addWidget(self.lbl_tag)

        # Detail text (e.g. 8.6G / 31.8G or 38°C)
        self.lbl_detail = QLabel("")
        self.lbl_detail.setWordWrap(False)
        self.lbl_detail.setStyleSheet("""
            QLabel {{
                color: #A0B3C6;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 12px;
            }}
        """)
        header_layout.addWidget(self.lbl_detail)

        header_layout.addStretch()

        # Primary value label (e.g. 35.8%)
        self.lbl_value = QLabel("0.0%")
        self.lbl_value.setWordWrap(False)
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_value.setStyleSheet("""
            QLabel {{
                color: #FFFFFF;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-weight: bold;
                font-size: 14px;
            }}
        """)
        header_layout.addWidget(self.lbl_value)

        layout.addLayout(header_layout)

        # Optional Cyber Bar
        if self.show_bar:
            self.bar = CyberBar(color=self.color)
            layout.addWidget(self.bar)
        else:
            self.bar = None

    def set_tag_text(self, text):
        self.lbl_tag.setText(text)
        self.lbl_tag.setMinimumWidth(self.lbl_tag.fontMetrics().horizontalAdvance(text) + 8)

    def update_stat(self, value_text, detail_text="", percent=0.0, custom_color=None):
        if self.lbl_value.text() != value_text:
            self.lbl_value.setText(value_text)
            self.lbl_value.setMinimumWidth(self.lbl_value.fontMetrics().horizontalAdvance(value_text) + 8)
        if detail_text and self.lbl_detail.text() != detail_text:
            self.lbl_detail.setText(detail_text)
            self.lbl_detail.setMinimumWidth(self.lbl_detail.fontMetrics().horizontalAdvance(detail_text) + 8)
        if self.bar:
            self.bar.set_value(percent)
        if custom_color and custom_color != self.current_color:
            self.current_color = custom_color
            self.lbl_value.setStyleSheet(f"""
                QLabel {{
                    color: {custom_color};
                    font-family: 'Consolas', 'Segoe UI', monospace;
                    font-weight: bold;
                    font-size: 16px;
                }}
            """)

