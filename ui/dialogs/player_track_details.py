import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QListWidget, QListWidgetItem, QComboBox, QInputDialog, QMessageBox
)

from backend.playlist_manager import PlaylistManager


class PlayerTrackDetailsDialog(QDialog):
    playlists_changed = pyqtSignal()
    open_catalog_requested = pyqtSignal(str, str, str)
    play_track_requested = pyqtSignal(str)

    FILTER_FIELDS = (
        ("artist", "Artist"),
        ("album_artist", "Album artist"),
        ("album", "Album"),
        ("genre", "Genre"),
        ("year", "Year"),
    )

    def __init__(self, current_track, library, parent=None):
        super().__init__(parent)
        self.current_track = current_track or {}
        self.library = list(library or [])
        self._active_filter = None
        self.setWindowTitle("Track details · Browse your library")
        self.setMinimumSize(650, 650)
        self.resize(760, 760)
        self.setStyleSheet("""
            QDialog { background: rgba(13, 20, 29, 248); color: #edf5fb; }
            QLabel { color: #edf5fb; background: transparent; }
            QLabel#title { font-size: 20px; font-weight: 750; }
            QLabel#subtitle { color: #a8bdcc; font-size: 13px; }
            QLabel#eyebrow { color: #82dff2; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
            QFrame#glassCard { background: rgba(39, 59, 75, 215); border: 1px solid rgba(196, 235, 248, 90); border-radius: 12px; }
            QPushButton { background: rgba(40, 58, 73, 230); color: #eef8fc; border: 1px solid #547184; border-radius: 8px; padding: 8px 11px; font-weight: 650; }
            QPushButton:hover { background: rgba(61, 94, 115, 245); border-color: #8cecff; }
            QPushButton#filterButton { text-align: left; padding: 9px 12px; }
            QPushButton#primary { background: #8cecff; color: #0b1820; border: 1px solid #c5f5ff; font-weight: 750; }
            QPushButton#primary:hover { background: #baf4ff; }
            QPushButton:disabled { background: #1b2630; color: #748795; border-color: #344450; }
            QListWidget { background: rgba(5, 11, 17, 235); color: #edf5fb; border: 1px solid #364d5e; border-radius: 8px; padding: 5px; }
            QListWidget::item { padding: 8px; border-radius: 5px; }
            QListWidget::item:hover { background: #1e3040; }
            QListWidget::indicator { width: 16px; height: 16px; background: #121d28; border: 1px solid #829bac; border-radius: 4px; }
            QListWidget::indicator:checked { background: #8cecff; border: 1px solid #c5f5ff; }
            QComboBox { background: #101a24; color: #edf5fb; border: 1px solid #557284; border-radius: 7px; padding: 8px; }
            QComboBox QAbstractItemView { background: #101a24; color: #edf5fb; selection-background-color: #316278; selection-color: white; border: 1px solid #557284; }
            QComboBox QAbstractItemView::item { background: #101a24; color: #edf5fb; min-height: 28px; padding: 5px 9px; }
            QComboBox QAbstractItemView::item:selected { background: #316278; color: white; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        header = QHBoxLayout()
        artwork = QLabel()
        artwork.setFixedSize(96, 96)
        artwork.setAlignment(Qt.AlignCenter)
        artwork.setStyleSheet("background: rgba(6,12,18,200); border:1px solid #486273; border-radius:10px;")
        art_path = self.current_track.get("artwork_path")
        if art_path and os.path.exists(art_path):
            pixmap = QPixmap(art_path)
            if not pixmap.isNull():
                artwork.setPixmap(pixmap.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if not artwork.pixmap():
            artwork.setText("AUDIO")
            artwork.setStyleSheet(artwork.styleSheet() + " font-size: 14px; font-weight: bold; color: #82dff2;")
        header.addWidget(artwork)
        title_col = QVBoxLayout()
        eyebrow = QLabel("NOW PLAYING · TRACK DETAILS")
        eyebrow.setObjectName("eyebrow")
        title = QLabel(self._value(self.current_track, "title", "Unknown track"))
        title.setObjectName("title")
        title.setWordWrap(True)
        subtitle = QLabel("{}  ·  {}".format(
            self._value(self.current_track, "artist", "Unknown artist"),
            self._value(self.current_track, "album", "Unknown album"),
        ))
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        title_col.addWidget(eyebrow)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        title_col.addStretch(1)
        header.addLayout(title_col, 1)
        root.addLayout(header)

        detail_card = QFrame()
        detail_card.setObjectName("glassCard")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(14, 12, 14, 12)
        detail_layout.setSpacing(6)
        detail_heading = QLabel("DETAILS · CLICK A VALUE TO BROWSE MATCHING TRACKS")
        detail_heading.setObjectName("eyebrow")
        detail_layout.addWidget(detail_heading)
        self.filter_buttons = []
        for key, label in self.FILTER_FIELDS:
            value = self._value(self.current_track, key, "")
            normalized_value = value.casefold()
            if (not value or value in ("—", "Unknown")
                    or normalized_value.startswith(("unknown ", "not set", "n/a"))):
                continue
            button = QPushButton(f"{label}     {value}     ›")
            button.setObjectName("filterButton")
            button.clicked.connect(lambda checked=False, field=key, val=value: self._browse(field, val))
            detail_layout.addWidget(button)
            self.filter_buttons.append(button)
        extra = QLabel("Genre and artist tags come from your audio file metadata. Update missing tags in the library editor.")
        extra.setWordWrap(True)
        extra.setStyleSheet("color: #9eb1bf; font-size: 11px;")
        detail_layout.addWidget(extra)
        root.addWidget(detail_card)

        self.lbl_results = QLabel("Choose an artist, album, genre, or year above to find matching tracks.")
        self.lbl_results.setObjectName("eyebrow")
        self.lbl_results.setWordWrap(True)
        root.addWidget(self.lbl_results)

        self.results = QListWidget()
        self.results.setMinimumHeight(190)
        self.results.itemDoubleClicked.connect(self._play_result)
        root.addWidget(self.results, 1)

        catalog_actions = QHBoxLayout()
        self.btn_open_album = QPushButton("Open album page")
        self.btn_open_artist = QPushButton("Open artist page")
        self.btn_open_genre = QPushButton("Open genre page")
        self.btn_open_album.setEnabled(self._usable(self._value(self.current_track, "album", "")))
        self.btn_open_artist.setEnabled(self._usable(self._value(self.current_track, "artist", "")))
        self.btn_open_genre.setEnabled(self._usable(self._value(self.current_track, "genre", "")))
        self.btn_open_album.clicked.connect(lambda: self._open_catalog("album"))
        self.btn_open_artist.clicked.connect(lambda: self._open_catalog("artist"))
        self.btn_open_genre.clicked.connect(lambda: self._open_catalog("genre"))
        catalog_actions.addWidget(self.btn_open_album)
        catalog_actions.addWidget(self.btn_open_artist)
        catalog_actions.addWidget(self.btn_open_genre)
        root.addLayout(catalog_actions)

        actions = QHBoxLayout()
        self.playlist_combo = QComboBox()
        self._refresh_playlists()
        btn_new = QPushButton("+ New playlist")
        btn_new.clicked.connect(self._create_playlist)
        self.btn_add = QPushButton("Add selected tracks")
        self.btn_add.setObjectName("primary")
        self.btn_add.clicked.connect(self._add_selected)
        self.btn_add.setEnabled(bool(self.playlist_combo.count()))
        actions.addWidget(QLabel("Add to"))
        actions.addWidget(self.playlist_combo, 1)
        actions.addWidget(btn_new)
        actions.addWidget(self.btn_add)
        root.addLayout(actions)

        footer = QHBoxLayout()
        self.lbl_selection = QLabel("0 tracks selected")
        self.lbl_selection.setStyleSheet("color:#a8bdcc; font-size:11px;")
        self.results.itemChanged.connect(self._update_selection_count)
        footer.addWidget(self.lbl_selection)
        footer.addStretch(1)
        close = QPushButton("Done")
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        root.addLayout(footer)
        self._update_selection_count()

    @staticmethod
    def _value(meta, key, fallback="—"):
        value = meta.get(key)
        if key == "year" and not value:
            value = meta.get("date")
        if key == "genre" and not value:
            value = meta.get("genres")
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(part) for part in value if part)
        if key == "duration" and isinstance(value, (int, float)):
            value = f"{int(value) // 60}:{int(value) % 60:02d}"
        return str(value).strip() if value not in (None, "") else fallback

    @staticmethod
    def _usable(value):
        return bool(value) and value != "—" and not value.casefold().startswith(("unknown ", "n/a", "not set"))

    def _browse(self, field, value):
        self._active_filter = (field, str(value).strip().casefold())
        label = dict((key, name) for key, name in self.FILTER_FIELDS)[field]
        matches = []
        for track in self.library:
            candidate = self._value(track, field, "").casefold()
            if candidate == self._active_filter[1]:
                matches.append(track)
        self.lbl_results.setText(f"{label.upper()} · {value}    —    {len(matches)} matching tracks · select one or more")
        self.results.blockSignals(True)
        self.results.clear()
        for track in matches:
            title = self._value(track, "title", os.path.basename(track.get("path", "Track")))
            artist = self._value(track, "artist", "Unknown artist")
            album = self._value(track, "album", "Unknown album")
            item = QListWidgetItem(f"{title}     ·     {artist}     ·     {album}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, track.get("path", ""))
            self.results.addItem(item)
        self.results.blockSignals(False)
        self._update_selection_count()

    def _open_catalog(self, field):
        value = self._value(self.current_track, field, "")
        album_artist = self._value(
            self.current_track, "album_artist",
            self._value(self.current_track, "artist", ""),
        )
        if self._usable(value):
            self.open_catalog_requested.emit(field, value, album_artist)
            self.accept()

    def _play_result(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self.play_track_requested.emit(str(path))
            self.accept()

    def _refresh_playlists(self, preserve=None):
        previous = preserve or self.playlist_combo.currentText() if hasattr(self, "playlist_combo") else preserve
        if not hasattr(self, "playlist_combo"):
            return
        self.playlist_combo.clear()
        self.playlist_combo.addItems(sorted(PlaylistManager.get_all_playlists(), key=str.casefold))
        if previous:
            idx = self.playlist_combo.findText(previous)
            if idx >= 0:
                self.playlist_combo.setCurrentIndex(idx)
        if hasattr(self, "btn_add"):
            if hasattr(self, "lbl_selection"):
                self._update_selection_count()
            else:
                self.btn_add.setEnabled(False)

    def _create_playlist(self):
        name, accepted = QInputDialog.getText(self, "New playlist", "Name your playlist:")
        if not accepted or not name.strip():
            return
        name = name.strip()
        if not PlaylistManager.create_playlist(name):
            QMessageBox.information(self, "Playlist exists", "Choose a different playlist name.")
            return
        self._refresh_playlists(name)
        self.playlists_changed.emit()

    def _update_selection_count(self, *_):
        count = sum(self.results.item(i).checkState() == Qt.Checked for i in range(self.results.count()))
        self.lbl_selection.setText(f"{count} track{'s' if count != 1 else ''} selected")
        self.btn_add.setEnabled(count > 0 and self.playlist_combo.count() > 0)

    def _add_selected(self):
        name = self.playlist_combo.currentText()
        if not name:
            QMessageBox.information(self, "Choose a playlist", "Create or select a playlist first.")
            return
        selected = [
            self.results.item(i).data(Qt.UserRole)
            for i in range(self.results.count())
            if self.results.item(i).checkState() == Qt.Checked
        ]
        added = sum(1 for path in selected if path and PlaylistManager.add_to_playlist(name, path))
        self.playlists_changed.emit()
        QMessageBox.information(self, "Tracks added", f"Added {added} track(s) to ‘{name}’.")
