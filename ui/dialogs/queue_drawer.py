import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QLineEdit, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QColor, QFont


class QueueTrackItemWidget(QFrame):
    play_clicked = pyqtSignal()
    move_up_clicked = pyqtSignal()
    move_down_clicked = pyqtSignal()
    remove_clicked = pyqtSignal()
    make_next_clicked = pyqtSignal()

    def __init__(self, track_meta, index_label="", is_user_queue=False, is_upcoming=False, parent=None):
        super().__init__(parent)
        self.track_meta = track_meta
        self.setFixedHeight(38)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("queueItem")
        self.setStyleSheet("""
            #queueItem {
                background: #111622;
                border: 1px solid #1c2636;
                border-radius: 5px;
            }
            #queueItem:hover {
                background: #182232;
                border-color: #2b3d56;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 8, 2)
        layout.setSpacing(10)

        # 1. Clean Monospace Index / Position Badge
        badge_lbl = QLabel(index_label)
        badge_lbl.setFixedWidth(24)
        badge_lbl.setAlignment(Qt.AlignCenter)
        badge_lbl.setStyleSheet("color: #64748b; font-family: Monospace; font-size: 10px; font-weight: bold;")
        layout.addWidget(badge_lbl)

        # 2. Track Title & Artist in compact hierarchy
        info_col = QVBoxLayout()
        info_col.setSpacing(0)
        info_col.setAlignment(Qt.AlignVCenter)

        title = track_meta.get("title") or track_meta.get("filename") or "Unknown Track"
        artist = track_meta.get("artist") or "Unknown Artist"

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #f1f5f9; font-size: 11px; font-weight: 600;")
        artist_lbl = QLabel(artist)
        artist_lbl.setStyleSheet("color: #94a3b8; font-size: 9px;")

        info_col.addWidget(title_lbl)
        info_col.addWidget(artist_lbl)
        layout.addLayout(info_col, 1)

        # 3. Track Duration
        dur_s = int(float(track_meta.get("duration") or 0))
        dur_str = f"{dur_s // 60:02d}:{dur_s % 60:02d}" if dur_s > 0 else "--:--"
        dur_lbl = QLabel(dur_str)
        dur_lbl.setStyleSheet("color: #64748b; font-family: Monospace; font-size: 10px;")
        layout.addWidget(dur_lbl)

        # 4. Audio Quality Pill (FLAC, MP3, etc.)
        ext = os.path.splitext(track_meta.get("filename", ""))[1].lstrip(".").upper() or "AUDIO"
        fmt_lbl = QLabel(ext)
        fmt_lbl.setStyleSheet("""
            background: rgba(56, 189, 248, 0.08);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 3px;
            color: #38bdf8;
            font-family: Monospace;
            font-size: 9px;
            font-weight: bold;
            padding: 1px 5px;
        """)
        layout.addWidget(fmt_lbl)

        # 5. Sleek & Compact Action Buttons
        if is_user_queue:
            btn_up = QPushButton("▲")
            btn_up.setFixedSize(18, 20)
            btn_up.setToolTip("Move up in priority queue")
            btn_up.clicked.connect(self.move_up_clicked.emit)

            btn_down = QPushButton("▼")
            btn_down.setFixedSize(18, 20)
            btn_down.setToolTip("Move down in priority queue")
            btn_down.clicked.connect(self.move_down_clicked.emit)

            btn_play = QPushButton("▶")
            btn_play.setFixedSize(22, 22)
            btn_play.setToolTip("Play now")
            btn_play.clicked.connect(self.play_clicked.emit)

            btn_remove = QPushButton("✕")
            btn_remove.setFixedSize(20, 22)
            btn_remove.setToolTip("Remove from queue")
            btn_remove.clicked.connect(self.remove_clicked.emit)

            for b in [btn_up, btn_down]:
                b.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        color: #64748b;
                        font-size: 8px;
                    }
                    QPushButton:hover { color: #38bdf8; }
                """)
            btn_play.setStyleSheet("""
                QPushButton {
                    background: rgba(2, 132, 199, 0.2);
                    border: 1px solid #0284c7;
                    border-radius: 3px;
                    color: #38bdf8;
                    font-size: 9px;
                }
                QPushButton:hover { background: #0284c7; color: #ffffff; }
            """)
            btn_remove.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #64748b;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { color: #ef4444; }
            """)

            layout.addWidget(btn_up)
            layout.addWidget(btn_down)
            layout.addWidget(btn_play)
            layout.addWidget(btn_remove)
        elif is_upcoming:
            btn_make_next = QPushButton("+ NEXT")
            btn_make_next.setFixedHeight(22)
            btn_make_next.setToolTip("Prioritize: play next after current song finishes")
            btn_make_next.setStyleSheet("""
                QPushButton {
                    background: rgba(56, 189, 248, 0.08);
                    border: 1px solid rgba(56, 189, 248, 0.25);
                    border-radius: 3px;
                    color: #7dd3fc;
                    font-family: Monospace;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 0 6px;
                }
                QPushButton:hover {
                    background: #0284c7;
                    border-color: #38bdf8;
                    color: #ffffff;
                }
            """)
            btn_make_next.clicked.connect(self.make_next_clicked.emit)

            btn_play = QPushButton("▶")
            btn_play.setFixedSize(22, 22)
            btn_play.setToolTip("Play immediately")
            btn_play.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: 1px solid #23354b;
                    border-radius: 3px;
                    color: #94a3b8;
                    font-size: 9px;
                }
                QPushButton:hover {
                    background: #0284c7;
                    border-color: #38bdf8;
                    color: #ffffff;
                }
            """)
            btn_play.clicked.connect(self.play_clicked.emit)

            layout.addWidget(btn_make_next)
            layout.addWidget(btn_play)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.play_clicked.emit()
        super().mouseDoubleClickEvent(event)


class QueueDrawerDialog(QDialog):
    """
    Modern Spotify & YouTube Music style Playback Queue & Up Next console.
    Provides complete control over what song plays next, reordering,
    priority insertion, and seamless continuation along the active filtered view.
    """
    track_selected = pyqtSignal(int)
    play_next_requested = pyqtSignal(int)
    add_to_queue_requested = pyqtSignal(int)

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setWindowTitle("Playback Queue & Up Next")
        self.resize(520, 640)
        self.setMinimumSize(460, 520)
        self._build_ui()
        self.refresh_queue()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #0b0f15;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QScrollArea { border: none; background: #0b0f15; }
            QWidget#queueContainer { background: #0b0f15; border: none; }
            QScrollBar:vertical {
                background: #0d121a;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #253346;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover { background: #3b82f6; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. Top Header Bar
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_lbl = QLabel("PLAYBACK QUEUE & UP NEXT")
        title_lbl.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 13px; font-weight: bold; letter-spacing: 1px;")

        self.lbl_context = QLabel("CONTEXT: All Tracks")
        self.lbl_context.setStyleSheet("color: #94a3b8; font-family: Monospace; font-size: 10px;")

        title_box.addWidget(title_lbl)
        title_box.addWidget(self.lbl_context)
        hdr.addLayout(title_box, 1)

        btn_close = QPushButton("X")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #1e2532;
                border: 1px solid #334155;
                border-radius: 14px;
                color: #94a3b8;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background: #ef4444; color: #ffffff; border-color: #ef4444; }
        """)
        btn_close.clicked.connect(self.close)
        hdr.addWidget(btn_close)
        layout.addLayout(hdr)

        # 2. Currently Playing Card
        self.now_playing_box = QFrame()
        self.now_playing_box.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #131b26, stop:1 #1c2738);
                border: 1px solid #2563eb;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        np_layout = QHBoxLayout(self.now_playing_box)
        np_layout.setContentsMargins(10, 8, 10, 8)
        np_layout.setSpacing(12)

        self.np_art = QLabel()
        self.np_art.setFixedSize(48, 48)
        self.np_art.setStyleSheet("background: #090d13; border: 1px solid #334155; border-radius: 4px;")
        self.np_art.setAlignment(Qt.AlignCenter)
        np_layout.addWidget(self.np_art)

        np_info = QVBoxLayout()
        np_info.setSpacing(2)

        np_badge = QLabel("NOW PLAYING")
        np_badge.setStyleSheet("color: #38bdf8; font-family: Monospace; font-size: 9px; font-weight: bold;")
        self.np_title = QLabel("No track playing")
        self.np_title.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        self.np_artist = QLabel("Select a track to start playback")
        self.np_artist.setStyleSheet("color: #94a3b8; font-size: 10px;")

        np_info.addWidget(np_badge)
        np_info.addWidget(self.np_title)
        np_info.addWidget(self.np_artist)
        np_layout.addLayout(np_info, 1)

        layout.addWidget(self.now_playing_box)

        # 3. Main Scroll Area for Queues
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("queueScroll")
        scroll.setStyleSheet("""
            #queueScroll { background: #0b0f15; border: none; }
            QScrollBar:horizontal { height: 0px; }
        """)
        container = QWidget()
        container.setObjectName("queueContainer")
        container.setStyleSheet("#queueContainer { background: #0b0f15; border: none; }")
        self.c_layout = QVBoxLayout(container)
        self.c_layout.setContentsMargins(0, 0, 4, 0)
        self.c_layout.setSpacing(14)

        # Section A: User Priority Queue (Play Next)
        sec_user_hdr = QHBoxLayout()
        lbl_user_q = QLabel("PLAYING NEXT (USER PRIORITY QUEUE)")
        lbl_user_q.setStyleSheet("color: #f59e0b; font-family: Monospace; font-size: 11px; font-weight: bold;")
        sec_user_hdr.addWidget(lbl_user_q)
        sec_user_hdr.addStretch()

        self.btn_clear_user_q = QPushButton("Clear Queue")
        self.btn_clear_user_q.setStyleSheet("""
            QPushButton {
                background: #1e2430;
                border: 1px solid #475569;
                border-radius: 3px;
                color: #cbd5e1;
                font-family: Monospace;
                font-size: 9px;
                padding: 2px 8px;
            }
            QPushButton:hover { background: #b91c1c; color: #ffffff; border-color: #ef4444; }
        """)
        self.btn_clear_user_q.clicked.connect(self._clear_user_queue)
        sec_user_hdr.addWidget(self.btn_clear_user_q)
        self.c_layout.addLayout(sec_user_hdr)

        self.user_q_container = QVBoxLayout()
        self.user_q_container.setSpacing(4)
        self.c_layout.addLayout(self.user_q_container)

        # Section B: Up Next from Active Sequence (FLAC, MP3, Playlist, etc.)
        sec_seq_hdr = QHBoxLayout()
        self.lbl_seq_title = QLabel("UP NEXT FROM CURRENT VIEW")
        self.lbl_seq_title.setStyleSheet("color: #38bdf8; font-family: Monospace; font-size: 11px; font-weight: bold;")
        sec_seq_hdr.addWidget(self.lbl_seq_title)
        sec_seq_hdr.addStretch()
        self.c_layout.addLayout(sec_seq_hdr)

        self.seq_container = QVBoxLayout()
        self.seq_container.setSpacing(4)
        self.c_layout.addLayout(self.seq_container)

        self.c_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        # 4. Bottom Quick Finder / Filter to Insert Any Song
        bottom_box = QFrame()
        bottom_box.setStyleSheet("background: #0f141d; border: 1px solid #1e293b; border-radius: 6px; padding: 4px;")
        b_layout = QHBoxLayout(bottom_box)
        b_layout.setContentsMargins(6, 4, 6, 4)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Quick find song to play next or add to queue...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background: #070a0e;
                border: 1px solid #334155;
                border-radius: 4px;
                color: #ffffff;
                font-size: 11px;
                padding: 4px 8px;
            }
            QLineEdit:focus { border-color: #38bdf8; }
        """)
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        b_layout.addWidget(self.txt_search, 1)

        self.search_results_container = QVBoxLayout()
        layout.addWidget(bottom_box)
        layout.addLayout(self.search_results_container)

    def refresh_queue(self):
        # 1. Update Now Playing Card
        cur_track = self.main_window.get_now_playing_track()
        if cur_track:
            self.np_title.setText(cur_track.get("title") or cur_track.get("filename") or "Unknown Track")
            self.np_artist.setText(cur_track.get("artist") or "Unknown Artist")
            art_path = cur_track.get("artwork_path")
            if art_path and os.path.exists(art_path):
                pix = QPixmap(art_path)
                if not pix.isNull():
                    self.np_art.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                else:
                    self.np_art.setText("AUDIO")
            else:
                self.np_art.setText("AUDIO")
        else:
            self.np_title.setText("No song playing")
            self.np_artist.setText("Select a song from library")
            self.np_art.setText("AUDIO")

        # Context header
        ctx_name = getattr(self.main_window, "_active_context_name", "All Tracks")
        self.lbl_context.setText(f"ACTIVE PLAYBACK CONTEXT: {ctx_name.upper()}")
        self.lbl_seq_title.setText(f"UP NEXT FROM CURRENT VIEW ({ctx_name.upper()})")

        # 2. Render User Priority Queue
        self._clear_layout(self.user_q_container)
        user_queue = getattr(self.main_window, "_user_queue", [])
        playlist = getattr(self.main_window, "_playlist", [])

        if not user_queue:
            empty_lbl = QLabel("No priority songs queued. Click '+ NEXT' or right-click any track in the Library.")
            empty_lbl.setStyleSheet("color: #64748b; font-style: italic; font-size: 10px; padding: 6px 4px;")
            self.user_q_container.addWidget(empty_lbl)
            self.btn_clear_user_q.setEnabled(False)
        else:
            self.btn_clear_user_q.setEnabled(True)
            for i, real_idx in enumerate(user_queue):
                if 0 <= real_idx < len(playlist):
                    meta = playlist[real_idx]
                    w = QueueTrackItemWidget(meta, index_label=f"#{i+1}", is_user_queue=True, parent=self)
                    w.play_clicked.connect(lambda idx=real_idx, pos=i: self._on_play_user_queue_track(idx, pos))
                    w.move_up_clicked.connect(lambda pos=i: self._on_move_user_queue(pos, pos - 1))
                    w.move_down_clicked.connect(lambda pos=i: self._on_move_user_queue(pos, pos + 1))
                    w.remove_clicked.connect(lambda pos=i: self._on_remove_user_queue(pos))
                    self.user_q_container.addWidget(w)

        # 3. Render Upcoming Active Sequence
        self._clear_layout(self.seq_container)
        upcoming_indices = self.main_window.get_upcoming_sequence_indices(limit=25)
        if not upcoming_indices:
            empty_seq = QLabel("End of playback sequence.")
            empty_seq.setStyleSheet("color: #64748b; font-style: italic; font-size: 10px; padding: 6px 4px;")
            self.seq_container.addWidget(empty_seq)
        else:
            for i, real_idx in enumerate(upcoming_indices):
                if 0 <= real_idx < len(playlist):
                    meta = playlist[real_idx]
                    w = QueueTrackItemWidget(meta, index_label=f"{i+1:02d}", is_upcoming=True, parent=self)
                    w.play_clicked.connect(lambda idx=real_idx: self._on_play_sequence_track(idx))
                    w.make_next_clicked.connect(lambda idx=real_idx: self._on_make_track_next(idx))
                    self.seq_container.addWidget(w)

    def _on_play_user_queue_track(self, real_idx, queue_pos):
        self.main_window.play_track_from_user_queue(real_idx, queue_pos)
        self.refresh_queue()

    def _on_move_user_queue(self, from_pos, to_pos):
        self.main_window.move_user_queue(from_pos, to_pos)
        self.refresh_queue()

    def _on_remove_user_queue(self, pos):
        self.main_window.remove_from_user_queue(pos)
        self.refresh_queue()

    def _clear_user_queue(self):
        self.main_window.clear_user_queue()
        self.refresh_queue()

    def _on_play_sequence_track(self, real_idx):
        self.main_window.play_track_now(real_idx)
        self.refresh_queue()

    def _on_make_track_next(self, real_idx):
        self.main_window.queue_track_next(real_idx)
        self.refresh_queue()

    def _on_search_text_changed(self, text):
        self._clear_layout(self.search_results_container)
        q = text.strip().lower()
        if not q or len(q) < 2:
            return

        playlist = getattr(self.main_window, "_playlist", [])
        matches = []
        for idx, meta in enumerate(playlist):
            title = (meta.get("title") or meta.get("filename") or "").lower()
            artist = (meta.get("artist") or "").lower()
            if q in title or q in artist:
                matches.append((idx, meta))
                if len(matches) >= 5:
                    break

        for real_idx, meta in matches:
            w = QueueTrackItemWidget(meta, index_label="+", is_upcoming=True, parent=self)
            w.play_clicked.connect(lambda idx=real_idx: (self.main_window.play_track_now(idx), self.refresh_queue()))
            w.make_next_clicked.connect(lambda idx=real_idx: (self.main_window.queue_track_next(idx), self.refresh_queue()))
            self.search_results_container.addWidget(w)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
