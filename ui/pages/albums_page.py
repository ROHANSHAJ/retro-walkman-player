import os
from collections import OrderedDict

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QPushButton,
)

from ui.widgets.hero_cover_art import HeroCoverArtWindow


class AlbumsPage(QWidget):
    """Album browser backed by the current music library."""
    play_track = pyqtSignal(int)
    play_context_requested = pyqtSignal(list, int, int, str)

    def __init__(self, library=None, parent=None):
        super().__init__(parent)
        self._library = []
        self._albums = []
        self._album_icon_cache = {}
        self._build_ui()
        self.set_library(library or [])

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("ALBUMS")
        title.setStyleSheet("font-size:20px; font-weight:800; letter-spacing:1px; color:#eef4fb;")
        subtitle = QLabel("Browse records, then play a track from the album")
        subtitle.setStyleSheet("color:#93a2b5; font-size:12px;")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch(1)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search albums or artists…")
        self.txt_search.setFixedWidth(260)
        self.txt_search.textChanged.connect(self._filter_albums)
        header.addWidget(self.txt_search)
        root.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)

        left = QFrame()
        left.setStyleSheet("QFrame { background:#0c1118; border:1px solid #283341; border-radius:10px; }")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 10, 10)
        label = QLabel("YOUR ALBUMS")
        label.setStyleSheet("color:#8fa0b4; font-size:10px; font-weight:700; letter-spacing:1px; border:0; background:transparent;")
        ll.addWidget(label)
        self.album_table = QTableWidget(0, 3)
        self.album_table.setHorizontalHeaderLabels(["ALBUM", "ARTIST", "TRACKS"])
        self.album_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.album_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.album_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.album_table.setColumnWidth(1, 128)
        self.album_table.setWordWrap(False)
        self.album_table.setTextElideMode(Qt.ElideRight)
        self.album_table.verticalHeader().setVisible(False)
        self.album_table.verticalHeader().setDefaultSectionSize(58)
        self.album_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.album_table.setSelectionMode(QTableWidget.SingleSelection)
        self.album_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.album_table.currentCellChanged.connect(lambda row, *_: self._show_album(row))
        ll.addWidget(self.album_table, 1)
        splitter.addWidget(left)

        right = QFrame()
        right.setStyleSheet("QFrame { background:#0c1118; border:1px solid #283341; border-radius:10px; }")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 14, 14, 14)
        rl.setSpacing(10)
        hero = QHBoxLayout()
        self.cover = HeroCoverArtWindow(150)
        hero.addWidget(self.cover)
        info = QVBoxLayout()
        info.setSpacing(6)
        self.lbl_album = QLabel("Select an album")
        self.lbl_album.setWordWrap(True)
        self.lbl_album.setStyleSheet("color:#f3f7fb; font-size:22px; font-weight:800; background:transparent; border:0;")
        self.lbl_artist = QLabel("Album artist")
        self.lbl_artist.setStyleSheet("color:#9fb1c4; font-size:14px; background:transparent; border:0;")
        self.lbl_album_meta = QLabel("—")
        self.lbl_album_meta.setStyleSheet("color:#7f91a5; font-size:12px; background:transparent; border:0;")
        self.btn_play_first = QPushButton("Play First Track")
        self.btn_play_first.setMinimumHeight(36)
        self.btn_play_first.clicked.connect(self._play_first_track)
        info.addWidget(self.lbl_album)
        info.addWidget(self.lbl_artist)
        info.addWidget(self.lbl_album_meta)
        info.addStretch(1)
        info.addWidget(self.btn_play_first, 0, Qt.AlignLeft)
        hero.addLayout(info, 1)
        rl.addLayout(hero)

        tracks_label = QLabel("TRACKS")
        tracks_label.setStyleSheet("color:#8fa0b4; font-size:10px; font-weight:700; letter-spacing:1px; background:transparent; border:0;")
        rl.addWidget(tracks_label)
        self.track_table = QTableWidget(0, 3)
        self.track_table.setHorizontalHeaderLabels(["#", "TITLE", "DURATION"])
        self.track_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.track_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.track_table.verticalHeader().setVisible(False)
        self.track_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.track_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.track_table.itemDoubleClicked.connect(self._play_selected_track)
        rl.addWidget(self.track_table, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        root.addWidget(splitter, 1)

        self.setStyleSheet("""
            QTableWidget { background:#090d13; color:#dce5ef; border:1px solid #202b38; gridline-color:#18212c; selection-background-color:#24405b; selection-color:#fff; font-size:12px; }
            QHeaderView::section { background:#141d28; color:#9aacc0; border:0; padding:7px; font-size:10px; font-weight:700; }
            QLineEdit { background:#0b1119; color:#eef4fb; border:1px solid #334254; border-radius:7px; padding:8px 10px; }
            QPushButton { color:#eaf4fc; background:#1a2938; border:1px solid #3c5b75; border-radius:8px; padding:7px 12px; font-weight:700; }
            QPushButton:hover { background:#25415a; border-color:#79c9ee; }
        """)

    def set_library(self, library):
        self._library = list(library or [])
        grouped = OrderedDict()
        for index, meta in enumerate(self._library):
            album = (meta.get("album") or "Unknown Album").strip()
            artist = (meta.get("album_artist") or meta.get("artist") or "Unknown Artist").strip()
            key = (album.casefold(), artist.casefold())
            if key not in grouped:
                grouped[key] = {"album": album, "artist": artist, "tracks": [], "art": None, "year": ""}
            group = grouped[key]
            group["tracks"].append((index, meta))
            group["art"] = group["art"] or meta.get("artwork_path")
            group["year"] = group["year"] or str(meta.get("year") or "")[:4]
        self._albums = list(grouped.values())
        self.album_table.setUpdatesEnabled(False)
        self.album_table.blockSignals(True)
        try:
            self.album_table.setRowCount(len(self._albums))
            for row, album in enumerate(self._albums):
                art_path = album["art"]
                album_item = QTableWidgetItem(album["album"])
                if art_path and os.path.exists(art_path):
                    if art_path not in self._album_icon_cache:
                        pix = QPixmap(art_path).scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self._album_icon_cache[art_path] = QIcon(pix)
                    album_item.setIcon(self._album_icon_cache[art_path])
                else:
                    album_item.setText(album['album'])
                self.album_table.setItem(row, 0, album_item)
                self.album_table.setItem(row, 1, QTableWidgetItem(album["artist"]))
                self.album_table.setItem(row, 2, QTableWidgetItem(str(len(album["tracks"]))))
        finally:
            self.album_table.blockSignals(False)
            self.album_table.setUpdatesEnabled(True)
        if self._albums:
            self.album_table.selectRow(0)
            self._show_album(0)
        else:
            self._show_album(-1)
        self._filter_albums(self.txt_search.text())

    def open_album(self, album_name, artist=None):
        """Select and reveal a specific album from a track-detail action."""
        self.txt_search.clear()
        wanted_album = (album_name or "").strip().casefold()
        wanted_artist = (artist or "").strip().casefold()
        for row, album in enumerate(self._albums):
            if album["album"].casefold() != wanted_album:
                continue
            if wanted_artist and album["artist"].casefold() != wanted_artist:
                continue
            self.album_table.setCurrentCell(row, 0)
            self.album_table.selectRow(row)
            self._show_album(row)
            return True
        return False

    def _filter_albums(self, query):
        query = query.strip().casefold()
        for row, album in enumerate(self._albums):
            matches = query in f"{album['album']} {album['artist']}".casefold()
            self.album_table.setRowHidden(row, not matches)

    def _show_album(self, row):
        if not (0 <= row < len(self._albums)):
            self.lbl_album.setText("Select an album")
            self.lbl_artist.setText("Album artist")
            self.lbl_album_meta.setText("—")
            self.cover.set_artwork(None)
            self.track_table.setRowCount(0)
            self.btn_play_first.setEnabled(False)
            return
        album = self._albums[row]
        self.lbl_album.setText(album["album"])
        self.lbl_artist.setText(album["artist"])
        self.lbl_album_meta.setText(" • ".join(value for value in (album["year"], f"{len(album['tracks'])} tracks") if value))
        self.cover.set_artwork(album["art"])
        self.track_table.setRowCount(len(album["tracks"]))
        for track_row, (library_index, meta) in enumerate(album["tracks"]):
            number = QTableWidgetItem(str(meta.get("track") or track_row + 1))
            number.setData(Qt.UserRole, library_index)
            self.track_table.setItem(track_row, 0, number)
            self.track_table.setItem(track_row, 1, QTableWidgetItem(meta.get("title") or meta.get("filename") or "Unknown track"))
            duration = float(meta.get("duration") or 0)
            self.track_table.setItem(track_row, 2, QTableWidgetItem(f"{int(duration // 60):02d}:{int(duration % 60):02d}" if duration else "--:--"))
        self.btn_play_first.setEnabled(bool(album["tracks"]))

    def _play_selected_track(self, item):
        row = item.row()
        index_item = self.track_table.item(row, 0)
        if index_item:
            real_idx = int(index_item.data(Qt.UserRole))
            if 0 <= self.album_table.currentRow() < len(self._albums):
                album = self._albums[self.album_table.currentRow()]
                seq = [t[0] for t in album["tracks"]]
                pos = row if 0 <= row < len(seq) else (seq.index(real_idx) if real_idx in seq else 0)
                name = album.get("album") or "Album"
                self.play_context_requested.emit(seq, pos, real_idx, f"Album: {name}")
            self.play_track.emit(real_idx)

    def _play_first_track(self):
        if self.album_table.currentRow() < 0:
            return
        album = self._albums[self.album_table.currentRow()]
        tracks = album["tracks"]
        if tracks:
            seq = [t[0] for t in tracks]
            name = album.get("album") or "Album"
            self.play_context_requested.emit(seq, 0, tracks[0][0], f"Album: {name}")
            self.play_track.emit(tracks[0][0])
