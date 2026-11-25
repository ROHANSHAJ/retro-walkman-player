import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from backend.metadata_manager import MetadataManager, MetadataFetchWorker
from ui.dialogs.manual_cover_dialog import ManualCoverSelectorDialog


class MetadataEditorDialog(QDialog):
    metadata_saved = pyqtSignal(dict)

    def __init__(self, filepath, current_meta, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.meta = dict(current_meta)
        self.selected_art_path = self.meta.get("artwork_path")

        self.setWindowTitle("Customize Song Info & Thumbnail")
        self.setFixedSize(580, 540)
        self.setStyleSheet("""
            QDialog {
                background: #1e2024;
                color: #e0e4e8;
            }
            QLabel {
                color: #b0b6bc;
                font-size: 11px;
                font-weight: bold;
            }
            QLineEdit {
                background: #141618;
                border: 1px solid #383c44;
                border-radius: 4px;
                padding: 6px 8px;
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #ffb000;
            }
            QPushButton {
                background: #2e3238;
                border: 1px solid #454a54;
                border-radius: 4px;
                padding: 6px 14px;
                color: #e0e4e8;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3e444c;
            }
            QPushButton:pressed {
                background: #202226;
            }
        """)

        self._build_ui()
        self._populate_fields()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header
        hdr = QLabel("CUSTOMIZE TRACK METADATA & ARTWORK")
        hdr.setStyleSheet("color: #ffb000; font-size: 13px; font-weight: bold;")
        layout.addWidget(hdr)

        # Top row: Artwork preview + artwork action buttons
        art_layout = QHBoxLayout()
        self.art_label = QLabel()
        self.art_label.setFixedSize(110, 110)
        self.art_label.setStyleSheet("border: 1px solid #3e444c; background: #121416; border-radius: 6px;")
        self.art_label.setAlignment(Qt.AlignCenter)
        art_layout.addWidget(self.art_label)

        art_btn_layout = QVBoxLayout()
        self.btn_select_cover = QPushButton("Search & Pick Cover Online...")
        self.btn_select_cover.setStyleSheet("background: #0d9488; border: 1px solid #14b8a6; color: #ffffff;")
        self.btn_select_cover.clicked.connect(self._open_manual_cover_selector)
        self.btn_browse_art = QPushButton("Choose Image File...")
        self.btn_browse_art.clicked.connect(self._browse_image)
        self.btn_clear_art = QPushButton("Clear Artwork")
        self.btn_clear_art.clicked.connect(self._clear_image)

        art_btn_layout.addWidget(self.btn_select_cover)
        art_btn_layout.addWidget(self.btn_browse_art)
        art_btn_layout.addWidget(self.btn_clear_art)
        art_btn_layout.addStretch()
        art_layout.addLayout(art_btn_layout)
        art_layout.addStretch()
        layout.addLayout(art_layout)

        # Internet fetch section
        fetch_box = QFrame()
        fetch_box.setStyleSheet("background: #16181b; border: 1px solid #2d3138; border-radius: 6px; padding: 6px;")
        fetch_layout = QHBoxLayout(fetch_box)
        fetch_layout.setContentsMargins(6, 6, 6, 6)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search artist / song online...")
        self.btn_manual_search = QPushButton("Pick Candidate...")
        self.btn_manual_search.setStyleSheet("background: #d97706; border: 1px solid #f59e0b; color: #ffffff;")
        self.btn_manual_search.clicked.connect(self._open_manual_cover_selector)
        self.btn_fetch_online = QPushButton("Quick Auto-Fetch")
        self.btn_fetch_online.setStyleSheet("background: #0077aa; border: 1px solid #0099cc; color: #ffffff;")
        self.btn_fetch_online.clicked.connect(self._fetch_online)

        fetch_layout.addWidget(self.txt_search, 1)
        fetch_layout.addWidget(self.btn_manual_search)
        fetch_layout.addWidget(self.btn_fetch_online)
        layout.addWidget(fetch_box)

        # Metadata fields
        grid = QGridLayout()
        grid.setSpacing(8)

        grid.addWidget(QLabel("Title:"), 0, 0)
        self.txt_title = QLineEdit()
        grid.addWidget(self.txt_title, 0, 1)

        grid.addWidget(QLabel("Artist:"), 1, 0)
        self.txt_artist = QLineEdit()
        grid.addWidget(self.txt_artist, 1, 1)

        grid.addWidget(QLabel("Album:"), 2, 0)
        self.txt_album = QLineEdit()
        grid.addWidget(self.txt_album, 2, 1)

        grid.addWidget(QLabel("Year:"), 3, 0)
        self.txt_year = QLineEdit()
        grid.addWidget(self.txt_year, 3, 1)

        grid.addWidget(QLabel("Genre:"), 4, 0)
        self.txt_genre = QLineEdit()
        grid.addWidget(self.txt_genre, 4, 1)

        layout.addLayout(grid)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Save & Apply")
        self.btn_save.setStyleSheet("background: #ffb000; color: #1a1c1e; font-size: 12px;")
        self.btn_save.clicked.connect(self._save)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def _populate_fields(self):
        self.txt_title.setText(self.meta.get("title", ""))
        self.txt_artist.setText(self.meta.get("artist", ""))
        self.txt_album.setText(self.meta.get("album", ""))
        self.txt_year.setText(str(self.meta.get("year", "")))
        self.txt_genre.setText(self.meta.get("genre", ""))

        default_search = f"{self.meta.get('artist', '')} {self.meta.get('title', '')}".strip()
        self.txt_search.setText(default_search)

        self._update_art_preview(self.selected_art_path)

    def _update_art_preview(self, path):
        if path and os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                scaled = pix.scaled(106, 106, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.art_label.setPixmap(scaled)
                return
        self.art_label.setText("No Art")

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "", "Images (*.jpg *.jpeg *.png *.webp)"
        )
        if path:
            self.selected_art_path = path
            self._update_art_preview(path)

    def _clear_image(self):
        self.selected_art_path = None
        self._update_art_preview(None)

    def _open_manual_cover_selector(self):
        query = self.txt_search.text().strip() or f"{self.txt_artist.text()} {self.txt_title.text()}".strip()
        current_meta = {
            "title": self.txt_title.text().strip(),
            "artist": self.txt_artist.text().strip(),
            "album": self.txt_album.text().strip(),
            "year": self.txt_year.text().strip(),
            "genre": self.txt_genre.text().strip(),
            "path": self.filepath,
            "artwork_path": self.selected_art_path
        }
        dlg = ManualCoverSelectorDialog(self.filepath, current_meta, query=query, parent=self)
        dlg.metadata_applied.connect(self._on_candidate_applied)
        dlg.exec_()

    def _on_candidate_applied(self, updated):
        if not updated:
            return
        if updated.get("title"):
            self.txt_title.setText(updated["title"])
        if updated.get("artist"):
            self.txt_artist.setText(updated["artist"])
        if updated.get("album"):
            self.txt_album.setText(updated["album"])
        if updated.get("year"):
            self.txt_year.setText(str(updated["year"]))
        if updated.get("genre"):
            self.txt_genre.setText(updated["genre"])
        if updated.get("artwork_path"):
            self.selected_art_path = updated["artwork_path"]
            self._update_art_preview(self.selected_art_path)

    def _fetch_online(self):
        term = self.txt_search.text().strip()
        if not term:
            term = f"{self.txt_artist.text()} {self.txt_title.text()}".strip()

        self.btn_fetch_online.setText("Fetching...")
        self.btn_fetch_online.setEnabled(False)

        self.worker = MetadataFetchWorker(self.filepath, self.meta, query_override=term, parent=self)
        self.worker.fetched.connect(self._on_online_fetched)
        self.worker.failed.connect(self._on_online_failed)
        self.worker.start()

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.wait(1000)
        super().closeEvent(event)

    def reject(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.wait(1000)
        super().reject()

    def _on_online_fetched(self, updated_meta):
        self.btn_fetch_online.setText("Fetch from Internet")
        self.btn_fetch_online.setEnabled(True)

        self.meta.update(updated_meta)
        self.txt_title.setText(updated_meta.get("title", ""))
        self.txt_artist.setText(updated_meta.get("artist", ""))
        self.txt_album.setText(updated_meta.get("album", ""))
        self.txt_year.setText(str(updated_meta.get("year", "")))
        self.txt_genre.setText(updated_meta.get("genre", ""))

        if updated_meta.get("artwork_path"):
            self.selected_art_path = updated_meta["artwork_path"]
            self._update_art_preview(self.selected_art_path)

        QMessageBox.information(self, "Success", "Metadata & high-res artwork fetched successfully!")

    def _on_online_failed(self, filepath, err):
        self.btn_fetch_online.setText("Fetch from Internet")
        self.btn_fetch_online.setEnabled(True)
        QMessageBox.warning(self, "Fetch Notice", f"Could not fetch online metadata: {err}")

    def _save(self):
        self.meta["title"] = self.txt_title.text().strip()
        self.meta["artist"] = self.txt_artist.text().strip()
        self.meta["album"] = self.txt_album.text().strip()
        self.meta["year"] = self.txt_year.text().strip()
        self.meta["genre"] = self.txt_genre.text().strip()
        self.meta["artwork_path"] = self.selected_art_path

        MetadataManager.save_override(self.filepath, self.meta)
        self.metadata_saved.emit(self.meta)
        self.accept()
