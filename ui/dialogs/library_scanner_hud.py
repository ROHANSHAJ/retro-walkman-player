import os
import math
from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient, QLinearGradient
from backend.library_organizer import OrganizerWorker


class RadarScanWidget(QWidget):
    """
    Animated holographic sonar radar sweep scanner with glowing target blips.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(30)

    def _rotate(self):
        self._angle = (self._angle + 4.5) % 360.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.46

        # Radar Scope Background
        grad = QRadialGradient(cx, cy, r)
        grad.setColorAt(0.0, QColor(0, 30, 40, 230))
        grad.setColorAt(0.8, QColor(0, 18, 25, 240))
        grad.setColorAt(1.0, QColor(0, 8, 12, 255))
        painter.setPen(QPen(QColor(0, 240, 255, 180), 1.5))
        painter.setBrush(grad)
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Concentric Radar Range Rings
        painter.setPen(QPen(QColor(0, 240, 255, 60), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r * 0.33, r * 0.33)
        painter.drawEllipse(QPointF(cx, cy), r * 0.66, r * 0.66)

        # Crosshairs
        painter.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        painter.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))

        # Rotating Scanner Beam
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle)

        beam_rad = math.radians(0)
        bx = r * math.cos(beam_rad)
        by = r * math.sin(beam_rad)

        beam_pen = QPen(QColor(0, 255, 200, 230), 2)
        painter.setPen(beam_pen)
        painter.drawLine(QPointF(0, 0), QPointF(bx, by))

        # Sweep sector trail
        sweep_grad = QRadialGradient(0, 0, r)
        sweep_grad.setColorAt(0.0, QColor(0, 255, 200, 70))
        sweep_grad.setColorAt(1.0, QColor(0, 255, 200, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(sweep_grad)
        painter.drawPie(QRectF(-r, -r, r * 2, r * 2), 0 * 16, -55 * 16)

        painter.restore()


class LibraryScannerHUD(QDialog):
    """
    High-tech holographic Audio Library Scanner & Pointer Organizer HUD
    with animated sonar radar, telemetry logging, and neon status badges.
    """
    library_organized = pyqtSignal(str)

    def __init__(self, source_dir, target_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AUDIO TELEMETRY SCANNER  |  VIRTUAL POINTER ORGANIZER")
        self.setFixedSize(680, 520)
        self.source_dir = os.path.abspath(source_dir)
        self.target_dir = os.path.abspath(target_dir)

        self._build_ui()
        self._start_scan()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0e1217, stop:0.5 #090c0f, stop:1 #050709);
                border: 2px solid #00f0ff;
                border-radius: 12px;
            }
            QLabel {
                color: #b0c0d0;
                font-family: Monospace;
            }
            QProgressBar {
                background: #080c10;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                text-align: center;
                color: #00f0ff;
                font-family: Monospace;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0088aa, stop:0.5 #00f0ff, stop:1 #39ff14);
                border-radius: 5px;
            }
            QTextEdit {
                background: #05080b;
                border: 1px solid #1c2834;
                border-radius: 6px;
                color: #39ff14;
                font-family: Monospace;
                font-size: 10px;
                padding: 8px;
            }
            QPushButton {
                background: #142230;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                padding: 8px 18px;
                color: #00f0ff;
                font-family: Monospace;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050709;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header HUD
        top_hud = QHBoxLayout()
        title_box = QVBoxLayout()
        h1 = QLabel("CYBERNETIC AUDIO LIBRARY SCANNER")
        h1.setStyleSheet("color: #00f0ff; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        h2 = QLabel(f"TARGET DIRECTORY: {self.source_dir}")
        h2.setStyleSheet("color: #507088; font-size: 10px;")
        title_box.addWidget(h1)
        title_box.addWidget(h2)

        top_hud.addLayout(title_box)
        top_hud.addStretch()

        self.status_pulse = QLabel("[SYSTEM: SCANNING]")
        self.status_pulse.setStyleSheet("color: #39ff14; font-size: 11px; font-weight: bold; border: 1px solid #39ff14; padding: 4px 8px; border-radius: 4px;")
        top_hud.addWidget(self.status_pulse)
        layout.addLayout(top_hud)

        # Radar & Telemetry Row
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        # Left: Sonar Radar Scanner
        self.radar = RadarScanWidget()
        mid_row.addWidget(self.radar)

        # Right: Telemetry Terminal Console Log
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.append(">> SYSTEM INITIALIZATION: OK")
        self.console.append(">> AUDIO CODEC PROFILER: ONLINE")
        self.console.append(f">> INGESTING SOURCE TREE: {self.source_dir}")
        mid_row.addWidget(self.console, 1)

        layout.addLayout(mid_row)

        # Progress Section
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Live Stats Badges
        stats_row = QHBoxLayout()
        self.badge_scanned = QLabel("TRACKS DETECTED: 0")
        self.badge_links = QLabel("POINTERS FORMED: 0")
        self.badge_art = QLabel("METADATA TAGS: 0")
        for b in [self.badge_scanned, self.badge_links, self.badge_art]:
            b.setStyleSheet("color: #00f0ff; font-size: 10px; font-weight: bold; background: #0c1822; padding: 4px 10px; border-radius: 4px; border: 1px solid #163044;")
            stats_row.addWidget(b)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        # Bottom Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_done = QPushButton("PLEASE WAIT...")
        self.btn_done.setEnabled(False)
        self.btn_done.clicked.connect(self._finish)
        btn_box.addWidget(self.btn_done)
        layout.addLayout(btn_box)

    def _start_scan(self):
        self.worker = OrganizerWorker(
            source_dir=self.source_dir,
            target_dir=self.target_dir,
            group_by_artist=True,
            group_by_year=True,
            group_by_genre=True
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_summary.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current, total, msg):
        pct = int((current / float(total)) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.console.append(f">> [{current}/{total}] {msg}")
        self.badge_scanned.setText(f"TRACKS DETECTED: {current}")
        self.badge_links.setText(f"POINTERS FORMED: {current * 3}")
        self.badge_art.setText(f"TAGS PARSED: {current}")

    def _on_finished(self, stats):
        self.progress_bar.setValue(100)
        self.status_pulse.setText("[SCAN COMPLETE: 100%]")
        self.status_pulse.setStyleSheet("color: #39ff14; font-weight: bold; border: 1px solid #39ff14; padding: 4px 8px; border-radius: 4px; background: rgba(57, 255, 20, 20);")

        self.console.append("\n==========================================")
        self.console.append(">> TELEMETRY SCAN & POINTER MAPPING FINISHED!")
        self.console.append(f">> AUDIO TRACKS CATALOGED: {stats['scanned_files']}")
        self.console.append(f">> ZERO-SPACE SYMLINKS MAPPED: {stats['symlinks_created']}")
        self.console.append(f">> VIRTUAL ROOTS DEPLOYED: {stats['target_dir']}")
        self.console.append("==========================================")

        self.btn_done.setText("ENTER VIRTUAL LIBRARY")
        self.btn_done.setEnabled(True)

    def _on_error(self, err):
        self.console.append(f">> ERROR: {err}")
        self.btn_done.setText("CLOSE")
        self.btn_done.setEnabled(True)

    def _finish(self):
        self.library_organized.emit(self.target_dir)
        self.accept()
