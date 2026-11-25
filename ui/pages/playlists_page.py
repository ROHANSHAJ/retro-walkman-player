import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QPushButton,
    QInputDialog, QMessageBox,
)

from backend.playlist_manager import PlaylistManager


class PlaylistsPage(QWidget):
    """Manage custom playlists and play or remove their tracks."""
    play_track = pyqtSignal(int)
    play_context_requested = pyqtSignal(list, int, int, str)
    browse_library = pyqtSignal()
    playlists_changed = pyqtSignal()

    def __init__(self, library=None, parent=None):
        super().__init__(parent)
        self._library = list(library or [])
        self._path_to_index = {}
        self._build_ui()
        self.set_library(self._library)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("PLAYLISTS")
        title.setStyleSheet("font-size:20px; font-weight:800; letter-spacing:1px; color:#eef4fb;")
        subtitle = QLabel("Create collections, manage tracks, and start playback")
        subtitle.setStyleSheet("color:#93a2b5; font-size:12px;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch(1)
        self.btn_add_songs = QPushButton("+ Browse Music to Add")
        self.btn_add_songs.setToolTip("Open Music Library, then right-click a track and choose Add to Playlist")
        self.btn_add_songs.clicked.connect(self.browse_library.emit)
        header.addWidget(self.btn_add_songs)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(12)
        left = QFrame()
        left.setFixedWidth(280)
        left.setStyleSheet("QFrame { background:#0c1118; border:1px solid #283341; border-radius:10px; }")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 10, 10)
        ll.setSpacing(8)
        label = QLabel("YOUR COLLECTIONS")
        label.setStyleSheet("color:#8fa0b4; font-size:10px; font-weight:700; letter-spacing:1px; background:transparent; border:0;")
        ll.addWidget(label)
        self.playlist_list = QListWidget()
        self.playlist_list.currentItemChanged.connect(lambda current, previous: self._show_playlist(current))
        ll.addWidget(self.playlist_list, 1)
        actions = QHBoxLayout()
        self.btn_create = QPushButton("+ New")
        self.btn_rename = QPushButton("Rename")
        self.btn_delete = QPushButton("Delete")
        self.btn_create.setFixedWidth(74)
        self.btn_rename.setFixedWidth(86)
        self.btn_delete.setFixedWidth(72)
        self.btn_create.clicked.connect(self._create_playlist)
        self.btn_rename.clicked.connect(self._rename_playlist)
        self.btn_delete.clicked.connect(self._delete_playlist)
        actions.addWidget(self.btn_create)
        actions.addWidget(self.btn_rename)
        actions.addWidget(self.btn_delete)
        ll.addLayout(actions)
        body.addWidget(left)

        right = QFrame()
        right.setStyleSheet("QFrame { background:#0c1118; border:1px solid #283341; border-radius:10px; }")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 14, 14, 14)
        rl.setSpacing(10)
        title_row = QHBoxLayout()
        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        self.lbl_playlist = QLabel("Select a playlist")
        self.lbl_playlist.setStyleSheet("color:#f3f7fb; font-size:20px; font-weight:800; background:transparent; border:0;")
        self.lbl_playlist_count = QLabel("—")
        self.lbl_playlist_count.setStyleSheet("color:#8fa0b4; font-size:12px; background:transparent; border:0;")
        info_col.addWidget(self.lbl_playlist)
        info_col.addWidget(self.lbl_playlist_count)
        title_row.addLayout(info_col)
        title_row.addStretch(1)
        self.btn_play_all = QPushButton("Play First Track")
        self.btn_play_all.clicked.connect(self._play_first_track)
        title_row.addWidget(self.btn_play_all)
        self.btn_remove_track = QPushButton("Remove track")
        self.btn_remove_track.clicked.connect(self._remove_selected_track)
        title_row.addWidget(self.btn_remove_track)
        rl.addLayout(title_row)
        self.lbl_empty = QLabel("This playlist is empty. Add tracks from Music Library using a track’s Add to Playlist menu.")
        self.lbl_empty.setWordWrap(True)
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setStyleSheet("color:#8495a8; background:#0a1017; border:1px dashed #344354; border-radius:8px; padding:14px; font-size:13px;")
        rl.addWidget(self.lbl_empty)
        self.track_table = QTableWidget(0, 4)
        self.track_table.setHorizontalHeaderLabels(["#", "TITLE", "ARTIST", "ALBUM"])
        self.track_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.track_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.track_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.track_table.setColumnWidth(2, 150)
        self.track_table.setColumnWidth(3, 170)
        self.track_table.verticalHeader().setVisible(False)
        self.track_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.track_table.setSelectionMode(QTableWidget.SingleSelection)
        self.track_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.track_table.itemDoubleClicked.connect(self._play_track_row)
        rl.addWidget(self.track_table, 1)
        body.addWidget(right, 1)
        root.addLayout(body, 1)

        self.setStyleSheet("""
            QTableWidget { background:#090d13; color:#dce5ef; border:1px solid #202b38; gridline-color:#18212c; selection-background-color:#24405b; selection-color:#fff; font-size:12px; }
            QHeaderView::section { background:#141d28; color:#9aacc0; border:0; padding:7px; font-size:10px; font-weight:700; }
            QListWidget { background:#090d13; color:#dce5ef; border:1px solid #202b38; border-radius:7px; padding:4px; font-size:12px; }
            QListWidget::item { padding:10px 8px; border-bottom:1px solid #18212c; }
            QListWidget::item:selected { background:#24405b; color:#fff; border-radius:5px; }
            QPushButton { color:#eaf4fc; background:#1a2938; border:1px solid #3c5b75; border-radius:8px; padding:6px 6px; font-size:12px; font-weight:700; }
            QPushButton:hover { background:#25415a; border-color:#79c9ee; }
            QPushButton:disabled { color:#718096; background:#151a21; border-color:#283341; }
        """)

    def set_library(self, library):
        self._library = list(library or [])
        self._path_to_index = {os.path.abspath(meta.get("path", "")): i for i, meta in enumerate(self._library) if meta.get("path")}
        self.refresh_playlists()

    def refresh_playlists(self, preserve_name=None):
        current = preserve_name or (self.playlist_list.currentItem().data(Qt.UserRole) if self.playlist_list.currentItem() else None)
        self.playlist_list.blockSignals(True)
        self.playlist_list.clear()
        for name, paths in sorted(PlaylistManager.get_all_playlists().items(), key=lambda pair: pair[0].casefold()):
            count = sum(1 for path in paths if os.path.abspath(path) in self._path_to_index)
            item = QListWidgetItem(f"{name}   ·   {count}")
            item.setData(Qt.UserRole, name)
            self.playlist_list.addItem(item)
        row = next((i for i in range(self.playlist_list.count()) if self.playlist_list.item(i).data(Qt.UserRole) == current), 0 if self.playlist_list.count() else -1)
        if row >= 0:
            self.playlist_list.setCurrentRow(row)
        self.playlist_list.blockSignals(False)
        self._show_playlist(self.playlist_list.currentItem())

    def _selected_name(self):
        item = self.playlist_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _show_playlist(self, item):
        name = item.data(Qt.UserRole) if item else None
        paths = PlaylistManager.get_playlist_tracks(name) if name else []
        tracks = [(self._path_to_index[os.path.abspath(path)], self._library[self._path_to_index[os.path.abspath(path)]]) for path in paths if os.path.abspath(path) in self._path_to_index]
        self.lbl_playlist.setText(name or "No playlists yet")
        self.lbl_playlist_count.setText(f"{len(tracks)} tracks" if name else "Create a playlist to start a collection")
        self.track_table.setUpdatesEnabled(False)
        self.track_table.setRowCount(len(tracks))
        for row, (library_index, meta) in enumerate(tracks):
            n = QTableWidgetItem(str(row + 1))
            n.setData(Qt.UserRole, library_index)
            n.setData(Qt.UserRole + 1, meta.get("path", ""))
            self.track_table.setItem(row, 0, n)
            self.track_table.setItem(row, 1, QTableWidgetItem(meta.get("title") or meta.get("filename") or "Unknown track"))
            self.track_table.setItem(row, 2, QTableWidgetItem(meta.get("artist") or "Unknown artist"))
            self.track_table.setItem(row, 3, QTableWidgetItem(meta.get("album") or "Unknown album"))
        self.track_table.setUpdatesEnabled(True)
        enabled = bool(name)
        self.lbl_empty.setVisible(enabled and not tracks)
        self.btn_rename.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)
        self.btn_play_all.setEnabled(bool(tracks))
        self.btn_remove_track.setEnabled(enabled and bool(tracks))

    def _name_dialog(self, title, label, text=""):
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextValue(text)
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet("QInputDialog { background:#121821; } QLabel { color:#e7edf4; font-size:13px; font-weight:600; } QLineEdit { background:#080c12; color:#fff; border:1px solid #526174; border-radius:6px; padding:9px; font-size:13px; } QPushButton { min-width:76px; padding:7px 12px; color:#e9f1f9; background:#202a37; border:1px solid #405166; border-radius:6px; }")
        return dialog.textValue() if dialog.exec_() == QInputDialog.Accepted else None

    def _create_playlist(self):
        name = self._name_dialog("Create playlist", "Give your playlist a name")
        if name and name.strip():
            if PlaylistManager.create_playlist(name.strip()):
                self.refresh_playlists(name.strip())
                self.playlists_changed.emit()
            else:
                QMessageBox.information(self, "Playlist exists", "Choose a different name for this playlist.")

    def _rename_playlist(self):
        old = self._selected_name()
        if not old:
            return
        new = self._name_dialog("Rename playlist", "Enter a new playlist name", old)
        if new and new.strip():
            if PlaylistManager.rename_playlist(old, new.strip()):
                self.refresh_playlists(new.strip())
                self.playlists_changed.emit()
            else:
                QMessageBox.information(self, "Name unavailable", "That playlist name is already in use.")

    def _delete_playlist(self):
        name = self._selected_name()
        if not name:
            return
        answer = QMessageBox.question(self, "Delete playlist", f"Delete ‘{name}’? The audio files will stay in your library.", QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer == QMessageBox.Yes:
            PlaylistManager.delete_playlist(name)
            self.refresh_playlists()
            self.playlists_changed.emit()

    def _play_track_row(self, item):
        row = item.row()
        n = self.track_table.item(row, 0)
        if n:
            real_idx = int(n.data(Qt.UserRole))
            seq = []
            for r in range(self.track_table.rowCount()):
                it = self.track_table.item(r, 0)
                if it:
                    seq.append(int(it.data(Qt.UserRole)))
            pos = row if 0 <= row < len(seq) else (seq.index(real_idx) if real_idx in seq else 0)
            name = self._selected_name() or "Playlist"
            self.play_context_requested.emit(seq, pos, real_idx, f"Playlist: {name}")
            self.play_track.emit(real_idx)

    def _play_first_track(self):
        if self.track_table.rowCount():
            n = self.track_table.item(0, 0)
            if n:
                real_idx = int(n.data(Qt.UserRole))
                seq = []
                for r in range(self.track_table.rowCount()):
                    it = self.track_table.item(r, 0)
                    if it:
                        seq.append(int(it.data(Qt.UserRole)))
                name = self._selected_name() or "Playlist"
                self.play_context_requested.emit(seq, 0, real_idx, f"Playlist: {name}")
                self.play_track.emit(real_idx)

    def _remove_selected_track(self):
        name = self._selected_name()
        row = self.track_table.currentRow()
        if not name or row < 0:
            return
        n = self.track_table.item(row, 0)
        path = n.data(Qt.UserRole + 1) if n else None
        if path:
            PlaylistManager.remove_from_playlist(name, path)
            self.refresh_playlists(name)
            self.playlists_changed.emit()
