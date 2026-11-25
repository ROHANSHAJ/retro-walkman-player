from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QFont


class BootSplashScreen(QWidget):
    """
    Premium boot animation & hardware diagnostic splash screen.
    """
    boot_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(520, 320)

        self._step = 0
        self._steps = [
            "INITIALIZING RETRO WALKMAN PRO OS v2.4...",
            "LOADING GSTREAMER 1.0 AUDIO CORE...",
            "CALIBRATING 10-BAND STUDIO EQUALIZER DSP...",
            "INITIALIZING UNIVERSAL ARTWORK & METADATA CACHE...",
            "SYNCHRONIZING LRCLIB KARAOKE ENGINE...",
            "RETRO HARDWARE THEMES READY • BOOT COMPLETE"
        ]

        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_step)
        self._timer.start(160)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("RETRO WALKMAN PRO")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 20px; font-weight: bold; letter-spacing: 3px;")

        sub = QLabel("HI-FI STEREO CASSETTE & LOSSLESS AUDIO ENGINE")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #ffaa00; font-family: Monospace; font-size: 10px; font-weight: bold; letter-spacing: 2px;")

        self.lbl_status = QLabel(self._steps[0])
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #39ff14; font-family: Monospace; font-size: 11px;")

        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setRange(0, len(self._steps))
        self.progress.setValue(1)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background: #0d1117;
                border: 1px solid #1f2937;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00f0ff, stop:1 #39ff14);
                border-radius: 3px;
            }
        """)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addSpacing(16)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.progress)
        layout.addStretch()

    def _advance_step(self):
        self._step += 1
        if self._step < len(self._steps):
            self.lbl_status.setText(self._steps[self._step])
            self.progress.setValue(self._step + 1)
        else:
            self._timer.stop()
            self.boot_finished.emit()
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Dark glass chassis with cyan rim lighting
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(18, 22, 28, 245))
        grad.setColorAt(1.0, QColor(8, 10, 14, 250))

        painter.setPen(QColor(0, 240, 255, 180))
        painter.setBrush(grad)
        painter.drawRoundedRect(2, 2, self.width() - 4, self.height() - 4, 14, 14)
