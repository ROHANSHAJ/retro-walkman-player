from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QTextEdit, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.dialogs.library_scanner_hud import RadarScanWidget
from backend.batch_metadata_worker import BatchMetadataWorker


class BatchEnrichDialog(QDialog):
    """
    Holographic HUD dialog for batch fetching missing metadata and high-resolution
    album covers for ALL tracks in the user's library simultaneously.
    """
    batch_finished = pyqtSignal()

    def __init__(self, playlist, main_window, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self.main_window = main_window
        self.worker = None

        self.setWindowTitle("BATCH METADATA & COVER ENRICHER")
        self.setFixedSize(560, 420)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #14171d, stop:0.5 #0c0f13, stop:1 #06080a);
                border: 2px solid #00f0ff;
                border-radius: 10px;
            }
            QLabel {
                color: #b0c0d0;
                font-family: Monospace;
            }
            QTextEdit {
                background: #080a0d;
                border: 1px solid #1c2430;
                border-radius: 6px;
                color: #39ff14;
                font-family: Monospace;
                font-size: 10px;
            }
            QProgressBar {
                background: #080c10;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                text-align: center;
                color: #00f0ff;
                font-family: Monospace;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0088aa, stop:0.5 #00f0ff, stop:1 #39ff14);
                border-radius: 3px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Top Header
        top_row = QHBoxLayout()
        self.radar = RadarScanWidget()
        top_row.addWidget(self.radar)

        hdr_info = QVBoxLayout()
        hdr_info.setSpacing(4)
        t_lbl = QLabel("UNIVERSAL AUTO-TAG & COVER FETCHER")
        t_lbl.setStyleSheet("color: #00f0ff; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        sub_lbl = QLabel("Queries iTunes Search API & MusicBrainz to enrich all library songs.")
        sub_lbl.setStyleSheet("color: #718096; font-size: 10px;")

        self.lbl_stats = QLabel(f"SONGS IN QUEUE: {len(self.playlist)}  •  COVERS ADDED: 0")
        self.lbl_stats.setStyleSheet("color: #ffaa00; font-size: 10px; font-weight: bold;")

        hdr_info.addWidget(t_lbl)
        hdr_info.addWidget(sub_lbl)
        hdr_info.addWidget(self.lbl_stats)
        top_row.addLayout(hdr_info, 1)
        layout.addLayout(top_row)

        # Options
        self.chk_force = QCheckBox("Force re-scan tracks that already have cover artwork")
        self.chk_force.setStyleSheet("color: #a0aec0; font-family: Monospace; font-size: 10px;")
        layout.addWidget(self.chk_force)

        # Progress bar & current status
        self.lbl_status = QLabel("Ready to enrich library. Click 'Start Batch Fetch' below.")
        self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Real-time console log
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box, 1)

        # Bottom Button Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_start = QPushButton("START BATCH FETCH")
        self.btn_start.setFixedHeight(34)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: #0088cc;
                border: 1px solid #00f0ff;
                border-radius: 5px;
                color: #ffffff;
                font-family: Monospace;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background: #00a8e8; }
        """)
        self.btn_start.clicked.connect(self._start_enrichment)

        self.btn_close = QPushButton("CLOSE")
        self.btn_close.setFixedHeight(34)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: #1c2430;
                border: 1px solid #3c4858;
                border-radius: 5px;
                color: #cbd5e1;
                font-family: Monospace;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background: #2c3848; color: #ffffff; }
        """)
        self.btn_close.clicked.connect(self._on_close)

        btn_row.addWidget(self.btn_start, 2)
        btn_row.addWidget(self.btn_close, 1)
        layout.addLayout(btn_row)

    def _start_enrichment(self):
        if not self.playlist:
            self.lbl_status.setText("Library is empty. Load songs first.")
            return

        self.btn_start.setEnabled(False)
        self.chk_force.setEnabled(False)
        self.lbl_status.setText("Connecting to online music databases...")
        self.log_box.append(">>> INITIALIZING BATCH ONLINE ENRICHMENT ENGINE...")

        self.worker = BatchMetadataWorker(self.playlist, force_all=self.chk_force.isChecked(), parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.track_updated.connect(self._on_track_updated)
        self.worker.finished_batch.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_error(self, err_msg):
        self.btn_start.setEnabled(True)
        self.lbl_status.setText(f"Batch halted: {err_msg}")
        self.log_box.append(f"[!] Error encountered: {err_msg}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)
        super().closeEvent(event)

    def _on_progress(self, curr, total, msg, got_cover):
        pct = int((curr / float(total)) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"Processing ({curr}/{total}): {msg}")
        icon = "[ART]" if got_cover else "[TAG]"
        self.log_box.append(f"[{curr:02d}/{total:02d}] {icon} {msg}")

        # Keep log box responsive by capping block count
        doc = self.log_box.document()
        if doc.blockCount() > 80:
            cursor = self.log_box.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

        # Let Qt process any pending UI repaints so OS never flags 'Not Responding'
        if curr % 5 == 0:
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

    def _on_track_updated(self, idx, updated_meta):
        if 0 <= idx < len(self.playlist):
            self.playlist[idx].update(updated_meta)
            if hasattr(self.main_window, "page_library") and hasattr(self.main_window.page_library, "update_row_meta"):
                self.main_window.page_library.update_row_meta(idx, updated_meta)
            if idx == self.main_window._current_index:
                self.main_window.page_deck.set_track_info(updated_meta)
                self.main_window.page_lyrics.load_track(updated_meta)

    def _on_finished(self, stats):
        self.btn_start.setText("COMPLETED")
        self.btn_start.setEnabled(True)
        self.lbl_status.setText(f"Batch completed! Updated {stats['updated']} tracks, added {stats['covers_added']} new covers.")
        self.lbl_stats.setText(f"TOTAL: {stats['total']}  •  UPDATED: {stats['updated']}  •  COVERS: {stats['covers_added']}")
        self.log_box.append(f"\n=== BATCH SUMMARY ===\n[OK] Total tracks: {stats['total']}\n[OK] Successfully updated: {stats['updated']}\n[OK] Covers added: {stats['covers_added']}")
        self.batch_finished.emit()

    def _on_close(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)
        self.accept()
