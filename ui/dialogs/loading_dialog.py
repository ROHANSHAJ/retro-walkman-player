from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient
from ui.dialogs.library_scanner_hud import RadarScanWidget


class LoadingScanDialog(QDialog):
    """
    Sleek animated holographic loading & scanning modal HUD.
    """
    def __init__(self, title="SCANNING AUDIO REPOSITORY", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setFixedSize(480, 220)
        self.setWindowTitle(title)
        self._build_ui(title)

    def _build_ui(self, title):
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #14181f, stop:0.5 #0c1015, stop:1 #06080a);
                border: 2px solid #00f0ff;
                border-radius: 10px;
            }
            QLabel {
                color: #b0c0d0;
                font-family: Monospace;
            }
            QProgressBar {
                background: #080c10;
                border: 1px solid #00f0ff;
                border-radius: 5px;
                text-align: center;
                color: #00f0ff;
                font-family: Monospace;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0088aa, stop:0.5 #00f0ff, stop:1 #39ff14);
                border-radius: 4px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        # Left: Sonar Radar Scanner
        self.radar = RadarScanWidget()
        layout.addWidget(self.radar)

        # Right: Progress & Status
        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.setAlignment(Qt.AlignVCenter)

        self.lbl_header = QLabel(f"{title}")
        self.lbl_header.setStyleSheet("color: #00f0ff; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        right_col.addWidget(self.lbl_header)

        self.lbl_status = QLabel("Analyzing directory structure...")
        self.lbl_status.setStyleSheet("color: #39ff14; font-size: 11px;")
        right_col.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setValue(0)
        right_col.addWidget(self.progress_bar)

        self.lbl_counter = QLabel("TRACKS: 0 / 0")
        self.lbl_counter.setStyleSheet("color: #8c9ba8; font-size: 10px;")
        right_col.addWidget(self.lbl_counter)

        layout.addLayout(right_col, 1)

    def set_progress(self, current, total, filename):
        pct = int((current / float(total)) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"Ingesting: {filename[:36]}...")
        self.lbl_counter.setText(f"TRACKS PARSED: {current} / {total}")
