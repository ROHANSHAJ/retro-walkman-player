import os
import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSplitter, QMessageBox, QAbstractItemView,
    QCheckBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QFont, QPixmap, QIcon

from backend.metadata_manager import MetadataManager, CoverSearchWorker


class ThumbnailDownloadWorker(QThread):
    thumbnail_loaded = pyqtSignal(str, bytes) # (url, bytes)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            r = requests.get(self.url, timeout=5)
            if r.status_code == 200:
                self.thumbnail_loaded.emit(self.url, r.content)
        except Exception:
            pass


class ManualCoverSelectorDialog(QDialog):
    """
    Dialog allowing the user to search iTunes & MusicBrainz for candidate releases,
    preview multiple album cover choices, and manually pick which cover artwork
    and tags to apply to the song.
    """
    metadata_applied = pyqtSignal(dict)  # emits updated metadata dict

    def __init__(self, filepath, current_meta, query=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.meta = dict(current_meta)
        self.query = query or f"{self.meta.get('artist', '')} {self.meta.get('title', '')}".strip()
        self._candidates = []
        self._thumb_cache = {}
        self._active_workers = []

        self.setWindowTitle("MANUAL COVER ART & METADATA SELECTOR")
        self.resize(920, 580)
        self.setMinimumSize(780, 500)

        self._build_ui()
        self._start_search()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #0f1217;
                border: 2px solid #ffaa00;
                border-radius: 8px;
            }
            QLabel {
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QLineEdit {
                background: #080a0d;
                border: 1px solid #f59e0b;
                border-radius: 4px;
                padding: 6px 10px;
                color: #ffffff;
                font-family: Monospace;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 2px solid #fbbf24;
            }
            QTableWidget {
                background: #080a0d;
                border: 1px solid #1e2633;
                border-radius: 5px;
                gridline-color: #141a24;
                color: #cbd5e1;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 11px;
                selection-background-color: #b45309;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background: #141820;
                color: #ffaa00;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #1e2838;
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
                border: 1px solid #ffaa00;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # 1. Header Bar
        hdr = QHBoxLayout()
        title_lbl = QLabel("SELECT ALBUM COVER & TAGS FROM FETCHED RELEASES")
        title_lbl.setStyleSheet("color: #ffaa00; font-family: Monospace; font-size: 12px; font-weight: bold; letter-spacing: 0.8px;")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        layout.addLayout(hdr)

        # 2. Search Toolbar
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        lbl_q = QLabel("Search:")
        lbl_q.setStyleSheet("color: #94a3b8; font-family: Monospace; font-size: 11px; font-weight: bold;")
        search_row.addWidget(lbl_q)

        self.txt_query = QLineEdit(self.query)
        self.txt_query.setPlaceholderText("Enter Artist, Song Title, or Album to search online...")
        self.txt_query.returnPressed.connect(self._start_search)
        search_row.addWidget(self.txt_query, 1)

        self.btn_search = QPushButton("Search Releases")
        self.btn_search.setStyleSheet("background: #d97706; border: 1px solid #fbbf24; color: #ffffff;")
        self.btn_search.clicked.connect(self._start_search)
        search_row.addWidget(self.btn_search)

        layout.addLayout(search_row)

        self.lbl_status = QLabel("Searching online candidates...")
        self.lbl_status.setStyleSheet("color: #eab308; font-family: Monospace; font-size: 10px;")
        layout.addWidget(self.lbl_status)

        # 3. Splitter: Left Candidate Table + Right Hero Cover Preview
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1c222b; width: 4px; }")

        # Left Candidate Table
        left_box = QFrame()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        t_lbl = QLabel("CANDIDATE ALBUMS & COVERS FOUND:")
        t_lbl.setStyleSheet("color: #718096; font-family: Monospace; font-size: 9px; font-weight: bold;")
        left_layout.addWidget(t_lbl)

        self.table_candidates = QTableWidget()
        self.table_candidates.setColumnCount(5)
        self.table_candidates.setHorizontalHeaderLabels(["ALBUM / RELEASE", "TRACK TITLE", "ARTIST", "YEAR", "GENRE"])
        h = self.table_candidates.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_candidates.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_candidates.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_candidates.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_candidates.verticalHeader().setVisible(False)
        self.table_candidates.verticalHeader().setDefaultSectionSize(40)
        self.table_candidates.currentCellChanged.connect(lambda r, c, pr, pc: self._on_candidate_selected(r))
        self.table_candidates.itemDoubleClicked.connect(lambda item: self._apply_selection())
        left_layout.addWidget(self.table_candidates)
        splitter.addWidget(left_box)

        # Right Hero Cover Preview Panel
        right_box = QFrame()
        right_box.setFixedWidth(280)
        right_box.setStyleSheet("background: #0a0d12; border: 1px solid #1c2330; border-radius: 6px; padding: 10px;")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        p_lbl = QLabel("SELECTED COVER PREVIEW:")
        p_lbl.setStyleSheet("color: #ffaa00; font-family: Monospace; font-size: 9px; font-weight: bold;")
        right_layout.addWidget(p_lbl)

        # Large 220x220 preview label
        self.cover_preview_label = QLabel()
        self.cover_preview_label.setFixedSize(240, 240)
        self.cover_preview_label.setAlignment(Qt.AlignCenter)
        self.cover_preview_label.setStyleSheet("""
            QLabel {
                background: #040507;
                border: 2px solid #2a3444;
                border-radius: 6px;
                color: #64748b;
                font-family: Monospace;
                font-size: 11px;
            }
        """)
        right_layout.addWidget(self.cover_preview_label, 0, Qt.AlignCenter)

        self.lbl_cand_title = QLabel("Select an album cover")
        self.lbl_cand_title.setWordWrap(True)
        self.lbl_cand_title.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        right_layout.addWidget(self.lbl_cand_title)

        self.lbl_cand_details = QLabel("--")
        self.lbl_cand_details.setWordWrap(True)
        self.lbl_cand_details.setStyleSheet("color: #94a3b8; font-size: 11px;")
        right_layout.addWidget(self.lbl_cand_details)
        right_layout.addStretch()

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        # 4. Bottom Row
        bot_row = QHBoxLayout()
        bot_row.setSpacing(10)

        self.chk_update_tags = QCheckBox("Also update track Title, Artist, Album & Year tags")
        self.chk_update_tags.setChecked(True)
        self.chk_update_tags.setStyleSheet("color: #cbd5e1; font-family: Monospace; font-size: 11px;")
        bot_row.addWidget(self.chk_update_tags)
        bot_row.addStretch()

        btn_cancel = QPushButton("CANCEL")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)
        bot_row.addWidget(btn_cancel)

        self.btn_apply = QPushButton("APPLY SELECTED COVER & TAGS")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f59e0b, stop:0.5 #d97706, stop:1 #b45309);
                border: 1px solid #fbbf24;
                border-radius: 4px;
                color: #ffffff;
                font-family: Monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 16px;
            }
            QPushButton:hover { background: #fbbf24; color: #1a1003; }
            QPushButton:disabled { background: #1a222d; border: 1px solid #2d3748; color: #64748b; }
        """)
        self.btn_apply.setEnabled(False)
        self.btn_apply.clicked.connect(self._apply_selection)
        bot_row.addWidget(self.btn_apply)

        layout.addLayout(bot_row)

    def _start_search(self):
        query = self.txt_query.text().strip()
        if not query:
            self.lbl_status.setText("Please enter artist or track name to search.")
            return

        self.btn_search.setEnabled(False)
        self.lbl_status.setText(f"Searching online releases for '{query}'...")
        self.lbl_status.setStyleSheet("color: #38bdf8;")
        self.table_candidates.setRowCount(0)
        self.btn_apply.setEnabled(False)
        self.cover_preview_label.setText("Searching...")

        self.search_worker = CoverSearchWorker(self.filepath, self.meta, query=query, parent=None)
        self.search_worker.candidates_ready.connect(self._on_search_results)
        self.search_worker.search_failed.connect(self._on_search_failed)
        self.search_worker.start()

    def _on_search_results(self, candidates):
        self.btn_search.setEnabled(True)
        self._candidates = candidates
        self.table_candidates.setRowCount(len(candidates))

        if not candidates:
            self.lbl_status.setText("No matching releases found. Try modifying your search query above.")
            self.lbl_status.setStyleSheet("color: #ef4444;")
            self.cover_preview_label.setText("No Results")
            return

        self.lbl_status.setText(f"Found {len(candidates)} release candidates with album artwork. Click any row to preview!")
        self.lbl_status.setStyleSheet("color: #22c55e;")

        for row, c in enumerate(candidates):
            self.table_candidates.setItem(row, 0, QTableWidgetItem(c.get("album", "")))
            self.table_candidates.setItem(row, 1, QTableWidgetItem(c.get("title", "")))
            self.table_candidates.setItem(row, 2, QTableWidgetItem(c.get("artist", "")))
            self.table_candidates.setItem(row, 3, QTableWidgetItem(str(c.get("year", ""))))
            self.table_candidates.setItem(row, 4, QTableWidgetItem(c.get("genre", "")))

            # Start background thumbnail download for icon
            p_url = c.get("preview_url")
            if p_url:
                self._download_thumbnail(row, p_url)

        self.table_candidates.selectRow(0)
        self._on_candidate_selected(0)

    def _download_thumbnail(self, row, url):
        if url in self._thumb_cache:
            pix = self._thumb_cache[url]
            icon = QIcon(pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            item = self.table_candidates.item(row, 0)
            if item:
                item.setIcon(icon)
            return

        worker = ThumbnailDownloadWorker(url, parent=None)
        self._active_workers.append(worker)

        def on_loaded(u, b):
            pix = QPixmap()
            pix.loadFromData(b)
            if not pix.isNull():
                self._thumb_cache[u] = pix
                icon = QIcon(pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item = self.table_candidates.item(row, 0)
                if item:
                    item.setIcon(icon)
            if worker in self._active_workers:
                self._active_workers.remove(worker)

        worker.thumbnail_loaded.connect(on_loaded)
        worker.start()

    def _on_search_failed(self, err):
        self.btn_search.setEnabled(True)
        self.lbl_status.setText(f"Search failed: {err}")
        self.lbl_status.setStyleSheet("color: #ef4444;")

    def _on_candidate_selected(self, row):
        if not (0 <= row < len(self._candidates)):
            self.btn_apply.setEnabled(False)
            return

        c = self._candidates[row]
        self.lbl_cand_title.setText(c.get("album") or c.get("title") or "Unknown Release")
        self.lbl_cand_details.setText(f"{c.get('artist', '')} • {c.get('year', '')} • {c.get('genre', '')}")
        self.btn_apply.setEnabled(True)

        # Show thumbnail preview while hi-res downloads or from cache
        p_url = c.get("preview_url")
        if p_url and p_url in self._thumb_cache:
            pix = self._thumb_cache[p_url]
            self.cover_preview_label.setPixmap(pix.scaled(236, 236, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.cover_preview_label.setText("Loading Cover Preview...")
            if p_url:
                w = ThumbnailDownloadWorker(p_url, parent=None)
                self._active_workers.append(w)
                w.thumbnail_loaded.connect(lambda u, b: (
                    setattr(self, 'pix', QPixmap()),
                    self.pix.loadFromData(b),
                    self.cover_preview_label.setPixmap(self.pix.scaled(236, 236, Qt.KeepAspectRatio, Qt.SmoothTransformation)) if not self.pix.isNull() else None,
                    self._active_workers.remove(w) if w in self._active_workers else None
                ))
                w.start()

    def _apply_selection(self):
        row = self.table_candidates.currentRow()
        if not (0 <= row < len(self._candidates)):
            return

        c = self._candidates[row]
        self.btn_apply.setEnabled(False)
        self.btn_apply.setText("Downloading Artwork...")
        QApplication.processEvents()

        updated = MetadataManager.apply_selected_candidate(
            self.filepath,
            self.meta,
            c,
            update_tags=self.chk_update_tags.isChecked()
        )

        self.metadata_applied.emit(updated)
        self.accept()

    def closeEvent(self, event):
        if hasattr(self, 'search_worker') and self.search_worker and self.search_worker.isRunning():
            try:
                self.search_worker.candidates_ready.disconnect()
            except Exception:
                pass
        super().closeEvent(event)
