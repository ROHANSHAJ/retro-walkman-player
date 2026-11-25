import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QFrame, QSplitter, QMessageBox, QAbstractItemView,
    QProgressBar, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont

from backend.lyrics_manager import LyricsManager, LyricsSearchWorker


class ManualLyricsSelectorDialog(QDialog):
    """
    Dialog allowing the user to search online lyrics on LrcLib, inspect all candidate
    matches (synced vs plain, different albums/versions), preview the raw timestamps,
    and manually pick which lyrics version to apply to the current track.
    """
    lyrics_applied = pyqtSignal(list, bool)  # (parsed_lines, is_synced)

    def __init__(self, filepath, artist, title, duration=0, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.artist = artist or ""
        self.title = title or ""
        self.duration = duration
        self._candidates = []
        self._search_worker = None

        self.setWindowTitle("MANUAL LYRICS SELECTOR  •  LRCLIB CANDIDATES")
        self.resize(860, 560)
        self.setMinimumSize(740, 480)

        self._build_ui()
        self._start_search()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #0f1217;
                border: 2px solid #00f0ff;
                border-radius: 8px;
            }
            QLabel {
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QLineEdit {
                background: #080a0d;
                border: 1px solid #38bdf8;
                border-radius: 4px;
                padding: 6px 10px;
                color: #ffffff;
                font-family: Monospace;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 2px solid #00f0ff;
            }
            QTableWidget {
                background: #080a0d;
                border: 1px solid #1e2633;
                border-radius: 5px;
                gridline-color: #141a24;
                color: #cbd5e1;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 11px;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background: #12161f;
                color: #00f0ff;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #1a222d;
            }
            QTextEdit {
                background: #06080b;
                border: 1px solid #1e2633;
                border-radius: 5px;
                color: #38bdf8;
                font-family: Monospace;
                font-size: 11px;
                line-height: 1.4;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #252c38, stop:0.5 #1a202a, stop:1 #12161e);
                border: 1px solid #3d4a5c;
                border-radius: 4px;
                padding: 6px 14px;
                color: #e2e8f0;
                font-family: Monospace;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2e3746;
                color: #ffffff;
                border: 1px solid #00f0ff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # 1. Header Bar
        hdr = QHBoxLayout()
        title_lbl = QLabel("SELECT LYRICS VERSION FROM FETCHED CANDIDATES")
        title_lbl.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 12px; font-weight: bold; letter-spacing: 0.8px;")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        layout.addLayout(hdr)

        # 2. Search Toolbar
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        lbl_q = QLabel("Search:")
        lbl_q.setStyleSheet("color: #94a3b8; font-family: Monospace; font-size: 11px; font-weight: bold;")
        search_row.addWidget(lbl_q)

        init_query = f"{self.artist} {self.title}".strip()
        self.txt_query = QLineEdit(init_query)
        self.txt_query.setPlaceholderText("Enter Artist and Track Title to search online...")
        self.txt_query.returnPressed.connect(self._start_search)
        search_row.addWidget(self.txt_query, 1)

        self.btn_search = QPushButton("Search LrcLib")
        self.btn_search.setStyleSheet("background: #0284c7; border: 1px solid #38bdf8; color: #ffffff;")
        self.btn_search.clicked.connect(self._start_search)
        search_row.addWidget(self.btn_search)

        layout.addLayout(search_row)

        self.lbl_status = QLabel("Searching online candidates...")
        self.lbl_status.setStyleSheet("color: #eab308; font-family: Monospace; font-size: 10px;")
        layout.addWidget(self.lbl_status)

        # 3. Main Splitter: Left Candidates Table + Right Live Lyrics Preview
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1c222b; width: 4px; }")

        # Left Candidates Table
        left_box = QFrame()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        t_lbl = QLabel("CANDIDATE RELEASES FOUND:")
        t_lbl.setStyleSheet("color: #718096; font-family: Monospace; font-size: 9px; font-weight: bold;")
        left_layout.addWidget(t_lbl)

        self.table_candidates = QTableWidget()
        self.table_candidates.setColumnCount(5)
        self.table_candidates.setHorizontalHeaderLabels(["TYPE", "TITLE", "ARTIST", "ALBUM", "DURATION"])
        h = self.table_candidates.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_candidates.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_candidates.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_candidates.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_candidates.verticalHeader().setVisible(False)
        self.table_candidates.currentCellChanged.connect(lambda r, c, pr, pc: self._on_candidate_selected(r))
        self.table_candidates.itemDoubleClicked.connect(lambda item: self._apply_selection())
        left_layout.addWidget(self.table_candidates)
        splitter.addWidget(left_box)

        # Right Live Preview Box
        right_box = QFrame()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        p_lbl = QLabel("LYRICS PREVIEW (TIMESTAMPS & TEXT):")
        p_lbl.setStyleSheet("color: #718096; font-family: Monospace; font-size: 9px; font-weight: bold;")
        right_layout.addWidget(p_lbl)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        right_layout.addWidget(self.preview_text)
        splitter.addWidget(right_box)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # 4. Bottom Action Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_apply = QPushButton("APPLY SELECTED LYRICS TO TRACK")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00b4d8, stop:0.5 #0096c7, stop:1 #0077b6);
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #ffffff;
                font-family: Monospace;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #00b4d8; }
            QPushButton:disabled { background: #1a222d; border: 1px solid #2d3748; color: #64748b; }
        """)
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self._apply_selection)

        btn_cancel = QPushButton("CANCEL")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_apply)
        layout.addLayout(btn_row)

    def _start_search(self):
        query = self.txt_query.text().strip()
        if not query:
            self.lbl_status.setText("Please enter a track name or artist to search.")
            return

        self.btn_search.setEnabled(False)
        self.lbl_status.setText(f"Searching LrcLib for '{query}'...")
        self.lbl_status.setStyleSheet("color: #38bdf8;")
        self.table_candidates.setRowCount(0)
        self.preview_text.clear()
        self.btn_apply.setEnabled(False)

        if self._search_worker and self._search_worker.isRunning():
            try:
                self._search_worker.results_ready.disconnect()
                self._search_worker.search_failed.disconnect()
            except Exception:
                pass

        self._search_worker = LyricsSearchWorker(query, parent=None)
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.search_failed.connect(self._on_search_failed)
        self._search_worker.start()

    def _on_search_results(self, candidates):
        self.btn_search.setEnabled(True)
        self._candidates = candidates
        self.table_candidates.setRowCount(len(candidates))

        if not candidates:
            self.lbl_status.setText("No matching lyrics found. Try tweaking your search query above.")
            self.lbl_status.setStyleSheet("color: #ef4444;")
            return

        self.lbl_status.setText(f"Found {len(candidates)} lyric candidate(s). Click any row to preview, then click Apply.")
        self.lbl_status.setStyleSheet("color: #22c55e;")

        for row, c in enumerate(candidates):
            # Type item
            is_synced = c.get("is_synced", False)
            type_item = QTableWidgetItem("SYNCED" if is_synced else "PLAIN")
            type_item.setTextAlignment(Qt.AlignCenter)
            type_item.setForeground(QColor("#22c55e") if is_synced else QColor("#eab308"))
            self.table_candidates.setItem(row, 0, type_item)

            self.table_candidates.setItem(row, 1, QTableWidgetItem(c.get("trackName", "")))
            self.table_candidates.setItem(row, 2, QTableWidgetItem(c.get("artistName", "")))
            self.table_candidates.setItem(row, 3, QTableWidgetItem(c.get("albumName", "")))

            dur = c.get("duration", 0.0)
            dur_str = f"{int(dur // 60):02d}:{int(dur % 60):02d}" if dur > 0 else "--:--"
            dur_item = QTableWidgetItem(dur_str)
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.table_candidates.setItem(row, 4, dur_item)

        self.table_candidates.selectRow(0)
        self._on_candidate_selected(0)

    def _on_search_failed(self, err):
        self.btn_search.setEnabled(True)
        self.lbl_status.setText(f"Search failed: {err}")
        self.lbl_status.setStyleSheet("color: #ef4444;")

    def _on_candidate_selected(self, row):
        if not (0 <= row < len(self._candidates)):
            self.preview_text.clear()
            self.btn_apply.setEnabled(False)
            return

        c = self._candidates[row]
        raw = c.get("syncedLyrics") or c.get("plainLyrics") or ""
        self.preview_text.setPlainText(raw)
        self.btn_apply.setEnabled(bool(raw.strip()))

    def _apply_selection(self):
        row = self.table_candidates.currentRow()
        if not (0 <= row < len(self._candidates)):
            return

        c = self._candidates[row]
        raw = c.get("syncedLyrics") or c.get("plainLyrics") or ""
        is_synced = c.get("is_synced", False)

        if not raw.strip():
            QMessageBox.warning(self, "Empty Lyrics", "The selected candidate contains no lyrics text.")
            return

        # Apply and save into local cache
        parsed, synced = LyricsManager.apply_selected_lyrics(
            self.filepath,
            self.artist or c.get("artistName", ""),
            self.title or c.get("trackName", ""),
            raw,
            is_synced
        )

        self.lyrics_applied.emit(parsed, synced)
        self.accept()

    def closeEvent(self, event):
        if self._search_worker and self._search_worker.isRunning():
            try:
                self._search_worker.results_ready.disconnect()
                self._search_worker.search_failed.disconnect()
            except Exception:
                pass
        super().closeEvent(event)
