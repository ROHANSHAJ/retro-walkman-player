import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QPushButton, QComboBox,
    QMenu, QFileDialog, QFrame, QSplitter, QTreeWidget, QTreeWidgetItem,
    QSlider, QInputDialog, QMessageBox, QAbstractItemView, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QIcon, QColor, QFont, QPainter, QLinearGradient

from ui.widgets.vintage_controls import VintageButton
from backend.library_organizer import SUPPORTED_EXTS, detect_language, detect_decade
from backend.metadata_manager import MetadataManager
from backend.playlist_manager import PlaylistManager
from ui.widgets.spectrum_analyzer import WinampSpectrumAnalyzer
from ui.dialogs.manual_cover_dialog import ManualCoverSelectorDialog
from ui.dialogs.manual_lyrics_dialog import ManualLyricsSelectorDialog


def get_audio_type(meta):
    """Return clean normalized audio format / codec name (e.g. MP3, FLAC, WAV)."""
    path = meta.get("path", "")
    ext = os.path.splitext(path)[1].lower()
    codec = (meta.get("codec") or "").lower()
    if ext == ".mp3" or "mp3" in codec:
        return "MP3"
    elif ext == ".flac" or "flac" in codec:
        return "FLAC"
    elif ext == ".wav" or "wav" in codec or "pcm" in codec:
        return "WAV"
    elif ext == ".ogg" or "ogg" in codec or "vorbis" in codec:
        return "OGG"
    elif ext in (".m4a", ".aac") or "aac" in codec or "alac" in codec:
        return "M4A"
    elif ext == ".opus" or "opus" in codec:
        return "OPUS"
    elif ext == ".wma" or "wma" in codec:
        return "WMA"
    elif ext:
        return ext.lstrip(".").upper()
    return "AUDIO"


class LibraryPage(QWidget):
    track_double_clicked = pyqtSignal(int)
    play_context_requested = pyqtSignal(list, int, int)
    play_next_requested = pyqtSignal(int)
    add_to_queue_requested = pyqtSignal(int)
    open_folder_requested = pyqtSignal()
    add_files_requested = pyqtSignal()
    organize_pointers_requested = pyqtSignal()
    batch_enrich_requested = pyqtSignal()
    detect_duplicates_requested = pyqtSignal()
    customize_track_requested = pyqtSignal(int)
    fetch_online_requested = pyqtSignal(int)
    remove_track_requested = pyqtSignal(int)
    font_size_changed = pyqtSignal(int)
    playlists_changed = pyqtSignal()
    track_metadata_changed = pyqtSignal(int, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlist = []
        self._default_playlist = []
        self._selected_audio_type = "ALL"
        self._type_sort_asc = True
        self._active_filter_type = "ALL"
        self._active_filter_val = None
        self._selected_row = -1

        # Customizable typography and layout scale
        self._font_size = 13
        self._row_height = 34
        self._accent = "#00f0ff"
        self._theme_key = "walkman"
        self._theme_pal = {}

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. TOP HARDWARE ACTION BEZEL (Buttons, Playlist Actions & Zoom)
        # -------------------------------------------------------------
        bar = QHBoxLayout()
        bar.setSpacing(6)

        btn_folder = VintageButton("Folder", "")
        btn_folder.setMinimumWidth(58)
        btn_folder.setToolTip("Open audio folder (replaces playlist)")
        btn_folder.clicked.connect(self.open_folder_requested.emit)

        btn_files = VintageButton("Add Files", "+")
        btn_files.setMinimumWidth(72)
        btn_files.setToolTip("Add individual files to queue")
        btn_files.clicked.connect(self.add_files_requested.emit)

        # Quick Liked Songs Filter Button
        self.btn_quick_liked = VintageButton("Favorites", "FAV", has_led=True)
        self.btn_quick_liked.setMinimumWidth(76)
        self.btn_quick_liked.setToolTip("Filter by Liked / Favorite songs")
        self.btn_quick_liked.clicked.connect(self._toggle_liked_filter)

        # New Custom Playlist Button
        btn_new_pl = VintageButton("New Playlist", "+", has_led=True)
        btn_new_pl.setMinimumWidth(88)
        btn_new_pl.set_led(True, "#a855f7")
        btn_new_pl.setToolTip("Create a new custom user playlist")
        btn_new_pl.clicked.connect(self._create_new_playlist_prompt)

        # Batch Auto-Tag & Cover Adder
        btn_batch = VintageButton("Auto-Tag", "TAG", has_led=True)
        btn_batch.setMinimumWidth(82)
        btn_batch.set_led(True, "#00f0ff")
        btn_batch.setToolTip("Universal online metadata and high-res cover fetcher")
        btn_batch.clicked.connect(self.batch_enrich_requested.emit)

        # Duplicate Detector Button
        btn_dups = VintageButton("Duplicates", "DUP", has_led=True)
        btn_dups.setMinimumWidth(80)
        btn_dups.set_led(True, "#ffaa00")
        btn_dups.setToolTip("Audit duplicate files and audio checksums")
        btn_dups.clicked.connect(self.detect_duplicates_requested.emit)

        # Virtual Library Organizer
        btn_organize = VintageButton("Organize", "ORG", has_led=True)
        btn_organize.setMinimumWidth(74)
        btn_organize.set_led(True, "#39ff14")
        btn_organize.setToolTip("Zero-copy virtual library organizer via symlinks")
        btn_organize.clicked.connect(self.organize_pointers_requested.emit)

        self._responsive_action_buttons = [
            (btn_folder, "DIR", "Folder"), (btn_files, "+", "Add Files"),
            (self.btn_quick_liked, "FAV", "Favorites"), (btn_new_pl, "+PL", "New Playlist"),
            (btn_batch, "TAG", "Auto-Tag"), (btn_dups, "DUP", "Duplicates"),
            (btn_organize, "ORG", "Organize"),
        ]

        bar.addWidget(btn_folder)
        bar.addWidget(btn_files)
        bar.addWidget(self.btn_quick_liked)
        bar.addWidget(btn_new_pl)
        bar.addWidget(btn_batch)
        bar.addWidget(btn_dups)
        bar.addWidget(btn_organize)
        bar.addStretch()

        # Customizable Library Text Size Zoom Slider
        lbl_zoom = QLabel("ZOOM:")
        lbl_zoom.setStyleSheet("color: #94a3b8; font-family: Monospace; font-size: 10px; font-weight: bold;")
        bar.addWidget(lbl_zoom)

        self.slider_font_size = QSlider(Qt.Horizontal)
        self.slider_font_size.setRange(10, 22)
        self.slider_font_size.setValue(self._font_size)
        self.slider_font_size.setFixedWidth(80)
        self.slider_font_size.setToolTip("Scale Library text size (10px — 22px)")
        self.slider_font_size.valueChanged.connect(self.set_library_font_size)
        bar.addWidget(self.slider_font_size)

        self.lbl_zoom_val = QLabel(f"{self._font_size}px")
        self.lbl_zoom_val.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 10px; font-weight: bold; min-width: 28px;")
        bar.addWidget(self.lbl_zoom_val)
        bar.addSpacing(8)

        # Audio Type Filter & Sort Dropdown Menu (All, MP3, FLAC, WAV, etc.)
        self.lbl_audio_type = QLabel("TYPE:")
        self.lbl_audio_type.setStyleSheet("color: #94a3b8; font-family: Monospace; font-size: 10px; font-weight: bold;")
        bar.addWidget(self.lbl_audio_type)

        self.combo_audio_type = QComboBox()
        self.combo_audio_type.setMinimumWidth(155)
        self.combo_audio_type.setFixedHeight(28)
        self.combo_audio_type.setToolTip("Filter or sort library by audio type (All, MP3, FLAC, WAV, etc.)")
        self._populate_audio_type_combo()
        self.combo_audio_type.currentIndexChanged.connect(self._on_audio_type_changed)
        bar.addWidget(self.combo_audio_type)
        bar.addSpacing(6)

        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Filter tracks, artists, genres...")
        self.txt_search.setFixedWidth(180)
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background: #090b0e;
                border: 1px solid #28303d;
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
                font-family: Monospace;
                font-size: 11px;
            }
            QLineEdit:focus { border: 1px solid #00f0ff; }
        """)
        self.txt_search.textChanged.connect(self._apply_all_filters)
        bar.addWidget(self.txt_search)
        self._zoom_widgets = (lbl_zoom, self.slider_font_size, self.lbl_zoom_val)

        layout.addLayout(bar)

        # -------------------------------------------------------------
        # 2. SPLITTER: LEFT PANEL (CATEGORIES + HERO COVER) + RIGHT TABLE
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)
        self._library_splitter = splitter
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #1c222b;
                width: 4px;
            }
        """)

        # LEFT PANE: Tree on Top + Hero Album Cover Bay on Bottom
        left_pane = QFrame()
        self._library_left_pane = left_pane
        left_pane.setFixedWidth(240)
        left_pane.setStyleSheet("""
            QFrame#leftPaneFrame {
                background: #090b0e;
                border: 1px solid #1c222b;
                border-radius: 6px;
            }
        """)
        left_pane.setObjectName("leftPaneFrame")
        lp_layout = QVBoxLayout(left_pane)
        lp_layout.setContentsMargins(6, 6, 6, 6)
        lp_layout.setSpacing(6)

        # Top section: Category & Playlists Tree
        cat_lbl = QLabel("VIRTUAL CATEGORIES & PLAYLISTS")
        cat_lbl.setStyleSheet("color: #718096; font-family: Monospace; font-size: 9px; font-weight: bold; padding: 2px 4px;")
        lp_layout.addWidget(cat_lbl)

        self.tree_categories = QTreeWidget()
        self.tree_categories.setHeaderHidden(True)
        self.tree_categories.setIndentation(14)
        self.tree_categories.setStyleSheet("""
            QTreeWidget {
                background: transparent;
                border: none;
                color: #cbd5e1;
                font-family: Monospace;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 3px 0;
            }
            QTreeWidget::item:selected {
                background: #1e293b;
                color: #00f0ff;
                font-weight: bold;
                border-radius: 3px;
            }
        """)
        self.tree_categories.itemClicked.connect(self._on_category_clicked)
        lp_layout.addWidget(self.tree_categories, 1)

        # Separator line
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #1a202a; margin: 2px 0;")
        lp_layout.addWidget(sep)

        # -------------------------------------------------------------
        # HERO COVER PAGE & NOW-PLAYING / SELECTED TRACK DISPLAY BOX
        # -------------------------------------------------------------
        self.cover_box = QFrame()
        self.cover_box.setStyleSheet("""
            QFrame {
                background: #0d1015;
                border: 1px solid #202734;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        cb_layout = QVBoxLayout(self.cover_box)
        cb_layout.setContentsMargins(6, 6, 6, 6)
        cb_layout.setSpacing(4)

        lbl_hero_header = QLabel("SELECTED TRACK COVER")
        lbl_hero_header.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 9px; font-weight: bold; letter-spacing: 0.5px;")
        cb_layout.addWidget(lbl_hero_header)

        # 1:1 Large Square Album Art Label
        self.cover_art_label = QLabel()
        self.cover_art_label.setFixedSize(210, 180)
        self.cover_art_label.setAlignment(Qt.AlignCenter)
        self.cover_art_label.setStyleSheet("""
            QLabel {
                background: #050608;
                border: 2px solid #202632;
                border-radius: 6px;
                color: #64748b;
                font-family: Monospace;
                font-size: 11px;
            }
        """)
        self.cover_art_label.setCursor(Qt.PointingHandCursor)
        self.cover_art_label.setToolTip("Double-click to play track • Click to preview")
        self.cover_art_label.mouseDoubleClickEvent = self._on_cover_double_clicked
        cb_layout.addWidget(self.cover_art_label, 0, Qt.AlignCenter)

        # Track Title (Large, Bold, Crisp)
        self.lbl_card_title = QLabel("Select a Track")
        self.lbl_card_title.setWordWrap(True)
        self.lbl_card_title.setStyleSheet("color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; font-weight: bold;")
        cb_layout.addWidget(self.lbl_card_title)

        # Artist & Album
        self.lbl_card_artist = QLabel("No track selected")
        self.lbl_card_artist.setStyleSheet("color: #94a3b8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px;")
        cb_layout.addWidget(self.lbl_card_artist)

        # Details pill
        self.lbl_card_details = QLabel("-- • -- • --:--")
        self.lbl_card_details.setStyleSheet("color: #ffaa00; font-family: Monospace; font-size: 10px; font-weight: bold;")
        cb_layout.addWidget(self.lbl_card_details)

        # Action button strip on card
        card_btn_row = QHBoxLayout()
        card_btn_row.setSpacing(4)

        self.btn_card_play = QPushButton("Play")
        self.btn_card_play.setFixedHeight(26)
        self.btn_card_play.setStyleSheet("""
            QPushButton {
                background: #0284c7;
                border: 1px solid #38bdf8;
                border-radius: 3px;
                color: #ffffff;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #0369a1; }
        """)
        self.btn_card_play.clicked.connect(self._on_card_play_clicked)

        self.btn_card_play_next = QPushButton("+ Next")
        self.btn_card_play_next.setFixedHeight(26)
        self.btn_card_play_next.setToolTip("Queue this track to play next")
        self.btn_card_play_next.setStyleSheet("""
            QPushButton {
                background: #0f766e;
                border: 1px solid #14b8a6;
                border-radius: 3px;
                color: #ffffff;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #115e59; }
        """)
        self.btn_card_play_next.clicked.connect(self._on_card_play_next_clicked)

        self.btn_card_like = QPushButton("LIKE")
        self.btn_card_like.setFixedHeight(26)
        self.btn_card_like.setFixedWidth(44)
        self.btn_card_like.setToolTip("Toggle Liked / Favorite status")
        self.btn_card_like.setStyleSheet("""
            QPushButton {
                background: #1e2430;
                border: 1px solid #374151;
                border-radius: 3px;
                color: #94a3b8;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #374151; }
        """)
        self.btn_card_like.clicked.connect(self._on_card_like_clicked)

        self.btn_card_add_pl = QPushButton("+ PL")
        self.btn_card_add_pl.setFixedHeight(26)
        self.btn_card_add_pl.setToolTip("Add selected track to custom playlist")
        self.btn_card_add_pl.setStyleSheet("""
            QPushButton {
                background: #7e22ce;
                border: 1px solid #c084fc;
                border-radius: 3px;
                color: #ffffff;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #6b21a8; }
        """)
        self.btn_card_add_pl.clicked.connect(self._on_card_add_playlist_clicked)

        self.btn_card_enrich = QPushButton("COVER")
        self.btn_card_enrich.setFixedHeight(26)
        self.btn_card_enrich.setFixedWidth(52)
        self.btn_card_enrich.setToolTip("Fetch online artwork for this track")
        self.btn_card_enrich.setStyleSheet("""
            QPushButton {
                background: #0d9488;
                border: 1px solid #2dd4bf;
                border-radius: 3px;
                color: #ffffff;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #0f766e; }
        """)
        self.btn_card_enrich.clicked.connect(self._on_card_enrich_clicked)

        card_btn_row.addWidget(self.btn_card_play, 2)
        card_btn_row.addWidget(self.btn_card_play_next, 2)
        card_btn_row.addWidget(self.btn_card_like)
        card_btn_row.addWidget(self.btn_card_add_pl)
        card_btn_row.addWidget(self.btn_card_enrich)
        cb_layout.addLayout(card_btn_row)

        lp_layout.addWidget(self.cover_box)
        splitter.addWidget(left_pane)

        # -------------------------------------------------------------
        # 3. RIGHT PANE: MAIN TRACKS TABLE (Customizable Font & Height)
        # -------------------------------------------------------------
        table_frame = QFrame()
        table_frame.setStyleSheet("""
            QFrame {
                background: #080a0d;
                border: 1px solid #1c222b;
                border-radius: 6px;
            }
        """)
        tf_layout = QVBoxLayout(table_frame)
        tf_layout.setContentsMargins(2, 2, 2, 2)
        tf_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "#", "FAV", "ART", "TITLE", "ARTIST", "ALBUM", "TYPE", "YEAR", "TIME"
        ])

        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Interactive)       # #
        h.setSectionResizeMode(1, QHeaderView.Interactive)       # Heart
        h.setSectionResizeMode(2, QHeaderView.Interactive)       # Art
        h.setSectionResizeMode(3, QHeaderView.Stretch)           # Title
        h.setSectionResizeMode(4, QHeaderView.Interactive)       # Artist
        h.setSectionResizeMode(5, QHeaderView.Interactive)       # Album
        h.setSectionResizeMode(6, QHeaderView.Interactive)       # Type
        h.setSectionResizeMode(7, QHeaderView.Interactive)       # Year
        h.setSectionResizeMode(8, QHeaderView.Interactive)       # Duration
        self.table.setColumnWidth(0, 32)
        self.table.setColumnWidth(1, 28)
        self.table.setColumnWidth(2, 40)
        self.table.setColumnWidth(4, 116)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 54)
        self.table.setColumnWidth(7, 54)
        self.table.setColumnWidth(8, 60)
        h.sectionClicked.connect(self._on_header_section_clicked)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(self._row_height)

        self.table.itemDoubleClicked.connect(lambda item: self._trigger_play_row(item.row()))
        self.table.itemClicked.connect(lambda item: self._on_row_selected(item.row()))
        self.table.currentCellChanged.connect(lambda r, c, pr, pc: self._on_row_selected(r))
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        tf_layout.addWidget(self.table, 1)

        # Track inspector: metadata and a live spectrum stay visible under the list.
        self.track_detail_panel = QFrame()
        self.track_detail_panel.setObjectName("trackDetailPanel")
        self.track_detail_panel.setFixedHeight(178)
        self.track_detail_panel.setStyleSheet("QFrame#trackDetailPanel { background: #11161e; border-top: 1px solid #28313d; }")
        detail_layout = QVBoxLayout(self.track_detail_panel)
        detail_layout.setContentsMargins(10, 6, 10, 7)
        detail_layout.setSpacing(4)
        detail_header = QHBoxLayout()
        self.lbl_detail_heading = QLabel("TRACK INSPECTOR  ·  AUDIO METADATA")
        self.lbl_detail_heading.setStyleSheet("color: #8c96a5; font-family: Monospace; font-size: 9px; font-weight: bold; letter-spacing: 0.7px;")
        self.lbl_detail_file = QLabel("Select a track to inspect its tags")
        self.lbl_detail_file.setStyleSheet("color: #687587; font-family: Monospace; font-size: 8px;")
        detail_header.addWidget(self.lbl_detail_heading)
        detail_header.addStretch(1)
        detail_header.addWidget(self.lbl_detail_file)
        detail_layout.addLayout(detail_header)

        detail_body = QHBoxLayout()
        detail_body.setSpacing(10)
        self.metadata_grid = QGridLayout()
        self.metadata_grid.setHorizontalSpacing(8)
        self.metadata_grid.setVerticalSpacing(2)
        self._detail_values = {}
        self._detail_keys = [
            ("Title", "title"), ("Artist", "artist"),
            ("Album", "album"), ("Album Artist", "album_artist"),
            ("Date", "year"), ("Track", "track"),
            ("Duration", "duration"), ("Codec", "codec"),
            ("Bitrate", "bitrate"), ("Sample Rate", "sample_rate"),
        ]
        for idx, (label_text, key) in enumerate(self._detail_keys):
            row, pair = divmod(idx, 2)
            label = QLabel(label_text.upper())
            label.setStyleSheet("color: #8c9bae; font-size: 9px; font-weight: 700;")
            value = QLabel("—")
            value.setMinimumWidth(68)
            value.setStyleSheet("color: #f0f4f8; font-size: 11px; font-weight: 600;")
            self.metadata_grid.addWidget(label, row, pair * 2)
            self.metadata_grid.addWidget(value, row, pair * 2 + 1)
            self._detail_values[key] = value
        comment_label = QLabel("COMMENT")
        comment_label.setStyleSheet("color: #788596; font-size: 8px; font-weight: bold;")
        self._detail_values["comment"] = QLabel("—")
        self._detail_values["comment"].setStyleSheet("color: #d7e0e9; font-size: 10px;")
        self.metadata_grid.addWidget(comment_label, 5, 0)
        self.metadata_grid.addWidget(self._detail_values["comment"], 5, 1, 1, 3)
        detail_body.addLayout(self.metadata_grid, 4)

        self.detail_spectrum = WinampSpectrumAnalyzer(bands_count=24, theme_mode="winamp")
        self.detail_spectrum.setFixedHeight(66)
        self.detail_spectrum.setMinimumWidth(190)
        self.detail_spectrum.setToolTip("Live stereo spectrum • click to switch to oscilloscope")
        detail_body.addWidget(self.detail_spectrum, 2)
        detail_layout.addLayout(detail_body, 1)
        tf_layout.addWidget(self.track_detail_panel)
        splitter.addWidget(table_frame)
        splitter.setStretchFactor(1, 4)

        layout.addWidget(splitter, 1)

        # Bottom Telemetry Bar
        self.lbl_telemetry = QLabel("LIBRARY: 0 TRACKS • PLAYLIST ENGINE ACTIVE")
        self.lbl_telemetry.setStyleSheet("color: #64748b; font-family: Monospace; font-size: 9px; font-weight: bold; padding: 2px 4px;")
        layout.addWidget(self.lbl_telemetry)

        self._apply_typography_styles()

    def resizeEvent(self, event):
        compact = event.size().width() < 1000
        narrow = event.size().width() < 820
        left_width = 184 if narrow else 200 if compact else 240
        self._library_left_pane.setFixedWidth(left_width)
        self._library_splitter.setSizes([left_width, max(240, event.size().width() - left_width - 12)])
        art_size = 148 if narrow else 164 if compact else 210
        self.cover_art_label.setFixedSize(art_size, max(126, art_size - 20))
        if 0 <= self._selected_row < len(self._playlist):
            self._update_hero_cover_card(self._playlist[self._selected_row])
        for button, compact_text, full_text in self._responsive_action_buttons:
            button.setText(compact_text if compact else full_text)
        for widget in self._zoom_widgets:
            widget.setVisible(not narrow)
        if hasattr(self, "lbl_audio_type"):
            self.lbl_audio_type.setVisible(not narrow)
        if hasattr(self, "combo_audio_type"):
            self.combo_audio_type.setFixedWidth(120 if narrow else 145 if compact else 165)
        self.txt_search.setFixedWidth(115 if narrow else 145 if compact else 180)
        super().resizeEvent(event)

    # -------------------------------------------------------------
    # TYPOGRAPHY & SCALE CUSTOMIZATION
    # -------------------------------------------------------------
    def set_library_font_size(self, size_pt):
        self._font_size = max(10, min(24, int(size_pt)))
        self._row_height = max(24, int(self._font_size * 2.4))
        self.lbl_zoom_val.setText(f"{self._font_size}px")
        self.slider_font_size.blockSignals(True)
        self.slider_font_size.setValue(self._font_size)
        self.slider_font_size.blockSignals(False)

        self._apply_typography_styles()
        self.font_size_changed.emit(self._font_size)

    def _apply_typography_styles(self):
        sz = self._font_size
        hdr_sz = max(9, sz - 2)
        row_h = self._row_height
        accent = self._accent

        self.table.verticalHeader().setDefaultSectionSize(row_h)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: #080a0d;
                border: none;
                gridline-color: #141820;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: {sz}px;
                selection-background-color: {accent};
                selection-color: #000000;
            }}
            QHeaderView::section {{
                background: #10141a;
                color: {accent};
                font-family: Monospace;
                font-size: {hdr_sz}px;
                font-weight: bold;
                padding: 6px 8px;
                border: none;
                border-bottom: 2px solid #1a222d;
            }}
            QScrollBar:vertical {{
                background: #0a0d10;
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: #252d38;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent};
            }}
        """)

        if hasattr(self, "combo_audio_type"):
            self.combo_audio_type.setStyleSheet(f"""
                QComboBox {{
                    background: #090b0e;
                    border: 1px solid #28303d;
                    border-radius: 4px;
                    padding: 3px 8px;
                    color: {accent};
                    font-family: Monospace;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QComboBox:focus {{ border: 1px solid {accent}; }}
                QComboBox::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 20px;
                    border-left: 1px solid #28303d;
                }}
                QComboBox QAbstractItemView {{
                    background: #0d1117;
                    border: 1px solid {accent};
                    color: #e2e8f0;
                    selection-background-color: #1e293b;
                    selection-color: {accent};
                    padding: 4px;
                }}
                QComboBox QAbstractItemView::item {{
                    min-height: 24px;
                    padding: 4px 8px;
                }}
            """)

        self.tree_categories.setStyleSheet(f"""
            QTreeWidget {{
                background: transparent;
                border: none;
                color: #c0cad6;
                font-family: Monospace;
                font-size: {sz - 2}px;
            }}
            QTreeWidget::item {{
                padding: 4px 0;
            }}
            QTreeWidget::item:selected {{
                background: {accent};
                color: #000000;
                font-weight: bold;
                border-radius: 3px;
            }}
            QTreeWidget::item:hover {{
                background: rgba(255, 255, 255, 0.08);
            }}
        """)

    # -------------------------------------------------------------
    # PLAYLIST & DATA POPULATION
    # -------------------------------------------------------------
    def set_playlist(self, playlist):
        self._playlist = []
        for i, meta in enumerate(playlist):
            m = dict(meta)
            if "_orig_index" not in m:
                m["_orig_index"] = i
            self._playlist.append(m)
        self._default_playlist = list(self._playlist)
        self._populate_audio_type_combo()
        self._rebuild_category_tree()
        self.refresh_table()
        if self._playlist:
            self._on_row_selected(0)

    def _populate_audio_type_combo(self):
        if not hasattr(self, "combo_audio_type"):
            return
        current_data = self.combo_audio_type.currentData() or "ALL"
        self.combo_audio_type.blockSignals(True)
        self.combo_audio_type.clear()

        counts = {}
        for item in self._playlist:
            t = get_audio_type(item)
            counts[t] = counts.get(t, 0) + 1

        total = len(self._playlist)
        self.combo_audio_type.addItem(f"All Formats ({total})" if total else "All Formats", "ALL")

        standard_formats = [
            ("MP3", "MP3 Audio (*.mp3)"),
            ("FLAC", "FLAC Lossless (*.flac)"),
            ("WAV", "WAV Lossless (*.wav)"),
            ("OGG", "OGG Vorbis (*.ogg)"),
            ("M4A", "M4A / AAC (*.m4a)"),
            ("OPUS", "OPUS Audio (*.opus)"),
            ("WMA", "WMA Audio (*.wma)"),
        ]

        for fmt, label in standard_formats:
            cnt = counts.get(fmt, 0)
            self.combo_audio_type.addItem(f"{label} ({cnt})" if total else label, fmt)

        for fmt, cnt in sorted(counts.items()):
            if fmt not in [f[0] for f in standard_formats]:
                self.combo_audio_type.addItem(f"{fmt} ({cnt})", fmt)

        self.combo_audio_type.insertSeparator(self.combo_audio_type.count())
        self.combo_audio_type.addItem("Sort: Audio Type (A → Z)", "SORT_ASC")
        self.combo_audio_type.addItem("Sort: Audio Type (Z → A)", "SORT_DESC")
        self.combo_audio_type.addItem("Reset: Playlist Order", "SORT_RESET")

        idx = self.combo_audio_type.findData(current_data)
        if idx >= 0:
            self.combo_audio_type.setCurrentIndex(idx)
        else:
            self.combo_audio_type.setCurrentIndex(0)
        self.combo_audio_type.blockSignals(False)

    def _on_audio_type_changed(self):
        data = self.combo_audio_type.currentData()
        if not data:
            return

        if data == "SORT_ASC":
            self._sort_playlist_by_type(reverse=False)
        elif data == "SORT_DESC":
            self._sort_playlist_by_type(reverse=True)
        elif data == "SORT_RESET":
            self._reset_playlist_order()
        else:
            self._selected_audio_type = data
            if data == "ALL":
                if self._active_filter_type == "AUDIO_TYPE":
                    self._active_filter_type = "ALL"
                    self._active_filter_val = None
            else:
                self._active_filter_type = "ALL"
                self._active_filter_val = None
            self._apply_all_filters()

    def _on_header_section_clicked(self, logical_index):
        if logical_index == 6:  # TYPE column
            if getattr(self, "_type_sort_asc", False):
                self._type_sort_asc = False
                self._sort_playlist_by_type(reverse=True)
            else:
                self._type_sort_asc = True
                self._sort_playlist_by_type(reverse=False)

    def _sort_playlist_by_type(self, reverse=False):
        self._playlist.sort(
            key=lambda m: (get_audio_type(m), m.get("artist", "").lower(), m.get("title", "").lower()),
            reverse=reverse
        )
        self.refresh_table()
        self._apply_all_filters()

    def _reset_playlist_order(self):
        self._playlist.sort(key=lambda m: m.get("_orig_index", 0))
        self.refresh_table()
        self._apply_all_filters()

    def set_library_filter(self, filter_type="ALL", filter_value=None):
        """Apply the header playlist selector without changing playback order."""
        self._active_filter_type = filter_type
        self._active_filter_val = filter_value
        self._apply_all_filters()

    def open_category_filter(self, filter_type, filter_value):
        """Open a browsable category from a track detail deep link."""
        self.txt_search.clear()
        self.set_library_filter(filter_type, filter_value)
        for top_index in range(self.tree_categories.topLevelItemCount()):
            parent = self.tree_categories.topLevelItem(top_index)
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                data = child.data(0, Qt.UserRole)
                if data == (filter_type, filter_value):
                    parent.setExpanded(True)
                    self.tree_categories.setCurrentItem(child)
                    child.setSelected(True)
                    return

    def _rebuild_category_tree(self):
        self.tree_categories.clear()

        # Group 1: All Tracks Root
        all_item = QTreeWidgetItem([f"ALL TRACKS ({len(self._playlist)})"])
        all_item.setData(0, Qt.UserRole, ("ALL", None))
        self.tree_categories.addTopLevelItem(all_item)

        # Group 2: SMART & CUSTOM PLAYLISTS
        liked_paths = PlaylistManager.get_liked_paths()
        liked_count = sum(1 for item in self._playlist if os.path.abspath(item.get("path", "")) in liked_paths)

        play_counts = PlaylistManager.get_most_played_map()
        most_played_count = sum(1 for item in self._playlist if play_counts.get(os.path.abspath(item.get("path", "")), 0) > 0)

        p_playlists = QTreeWidgetItem(["PLAYLISTS"])
        p_playlists.setData(0, Qt.UserRole, ("PARENT", None))

        item_liked = QTreeWidgetItem([f"Favorites ({liked_count})"])
        item_liked.setData(0, Qt.UserRole, ("PLAYLIST_LIKED", None))
        item_liked.setForeground(0, QColor("#ef4444"))
        p_playlists.addChild(item_liked)

        item_most = QTreeWidgetItem([f"Most Played ({most_played_count})"])
        item_most.setData(0, Qt.UserRole, ("PLAYLIST_MOST_PLAYED", None))
        item_most.setForeground(0, QColor("#ffaa00"))
        p_playlists.addChild(item_most)

        # Custom user playlists
        custom_pls = PlaylistManager.get_all_playlists()
        for pl_name, paths in sorted(custom_pls.items()):
            cnt = sum(1 for item in self._playlist if os.path.abspath(item.get("path", "")) in paths)
            c_pl = QTreeWidgetItem([f"{pl_name} ({cnt})"])
            c_pl.setData(0, Qt.UserRole, ("PLAYLIST_CUSTOM", pl_name))
            p_playlists.addChild(c_pl)

        # Quick action item to create playlist
        item_new = QTreeWidgetItem(["+ Create New Playlist..."])
        item_new.setData(0, Qt.UserRole, ("NEW_PLAYLIST_ACTION", None))
        item_new.setForeground(0, QColor("#a855f7"))
        p_playlists.addChild(item_new)

        self.tree_categories.addTopLevelItem(p_playlists)
        p_playlists.setExpanded(True)

        # Group 3: Categories (Format, Artist, Genre, Decade, Language)
        audio_types = {}
        artists = {}
        albums = {}
        genres = {}
        years = {}
        decades = {}
        languages = {}

        for item in self._playlist:
            t = get_audio_type(item)
            audio_types[t] = audio_types.get(t, 0) + 1

            a = item.get("artist") or "Unknown Artist"
            artists[a] = artists.get(a, 0) + 1

            album = item.get("album") or "Unknown Album"
            albums[album] = albums.get(album, 0) + 1

            g = item.get("genre") or "Unknown Genre"
            genres[g] = genres.get(g, 0) + 1

            yr = item.get("year", "")
            year_label = str(yr)[:4] if yr else "Unknown Year"
            years[year_label] = years.get(year_label, 0) + 1
            d = detect_decade(yr)
            decades[d] = decades.get(d, 0) + 1

            lang = detect_language(item)
            languages[lang] = languages.get(lang, 0) + 1

        # By Format / Audio Type
        p_types = QTreeWidgetItem([f"BY FORMAT ({len(audio_types)})"])
        p_types.setData(0, Qt.UserRole, ("PARENT", None))
        for t_name, count in sorted(audio_types.items()):
            t_item = QTreeWidgetItem([f"{t_name} ({count})"])
            t_item.setData(0, Qt.UserRole, ("AUDIO_TYPE", t_name))
            p_types.addChild(t_item)
        self.tree_categories.addTopLevelItem(p_types)

        # By Artist
        p_artist = QTreeWidgetItem([f"BY ARTIST ({len(artists)})"])
        p_artist.setData(0, Qt.UserRole, ("PARENT", None))
        for art, cnt in sorted(artists.items()):
            c = QTreeWidgetItem([f"{art} ({cnt})"])
            c.setData(0, Qt.UserRole, ("ARTIST", art))
            p_artist.addChild(c)
        self.tree_categories.addTopLevelItem(p_artist)

        p_album = QTreeWidgetItem([f"BY ALBUM ({len(albums)})"])
        p_album.setData(0, Qt.UserRole, ("PARENT", None))
        for album_name, count in sorted(albums.items(), key=lambda pair: pair[0].lower()):
            album_item = QTreeWidgetItem([f"{album_name} ({count})"])
            album_item.setData(0, Qt.UserRole, ("ALBUM", album_name))
            p_album.addChild(album_item)
        self.tree_categories.addTopLevelItem(p_album)

        p_year = QTreeWidgetItem([f"BY YEAR ({len(years)})"])
        p_year.setData(0, Qt.UserRole, ("PARENT", None))
        for year_name, count in sorted(years.items(), key=lambda pair: pair[0], reverse=True):
            year_item = QTreeWidgetItem([f"{year_name} ({count})"])
            year_item.setData(0, Qt.UserRole, ("YEAR", year_name))
            p_year.addChild(year_item)
        self.tree_categories.addTopLevelItem(p_year)

        # By Genre
        p_genre = QTreeWidgetItem([f"BY GENRE ({len(genres)})"])
        p_genre.setData(0, Qt.UserRole, ("PARENT", None))
        for gen, cnt in sorted(genres.items()):
            c = QTreeWidgetItem([f"{gen} ({cnt})"])
            c.setData(0, Qt.UserRole, ("GENRE", gen))
            p_genre.addChild(c)
        self.tree_categories.addTopLevelItem(p_genre)

        # By Decade
        p_decade = QTreeWidgetItem([f"BY DECADE ({len(decades)})"])
        p_decade.setData(0, Qt.UserRole, ("PARENT", None))
        for dec, cnt in sorted(decades.items()):
            c = QTreeWidgetItem([f"{dec} ({cnt})"])
            c.setData(0, Qt.UserRole, ("DECADE", dec))
            p_decade.addChild(c)
        self.tree_categories.addTopLevelItem(p_decade)

        # By Language
        p_lang = QTreeWidgetItem([f"BY LANGUAGE ({len(languages)})"])
        p_lang.setData(0, Qt.UserRole, ("PARENT", None))
        for lng, cnt in sorted(languages.items()):
            c = QTreeWidgetItem([f"{lng} ({cnt})"])
            c.setData(0, Qt.UserRole, ("LANGUAGE", lng))
            p_lang.addChild(c)
        self.tree_categories.addTopLevelItem(p_lang)

        all_item.setSelected(True)

    def _on_category_clicked(self, item, col):
        data = item.data(0, Qt.UserRole)
        if not data or data[0] == "PARENT":
            return

        if data[0] == "NEW_PLAYLIST_ACTION":
            self._create_new_playlist_prompt()
            return

        if data[0] == "AUDIO_TYPE":
            self._active_filter_type, self._active_filter_val = data
            idx = self.combo_audio_type.findData(data[1])
            if idx >= 0:
                self.combo_audio_type.blockSignals(True)
                self.combo_audio_type.setCurrentIndex(idx)
                self.combo_audio_type.blockSignals(False)
                self._selected_audio_type = data[1]
        elif data[0] == "ALL":
            self._active_filter_type, self._active_filter_val = data
            self.combo_audio_type.blockSignals(True)
            self.combo_audio_type.setCurrentIndex(0)
            self.combo_audio_type.blockSignals(False)
            self._selected_audio_type = "ALL"
        else:
            self._active_filter_type, self._active_filter_val = data

        self._apply_all_filters()

    def _toggle_liked_filter(self):
        if self._active_filter_type == "PLAYLIST_LIKED":
            self._active_filter_type = "ALL"
            self._active_filter_val = None
            self.btn_quick_liked.set_led(False, "#ef4444")
        else:
            self._active_filter_type = "PLAYLIST_LIKED"
            self._active_filter_val = None
            self.btn_quick_liked.set_led(True, "#ef4444")
        self._apply_all_filters()

    def _create_new_playlist_prompt(self):
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Create playlist")
        dlg.setLabelText("Give your playlist a name")
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.setMinimumWidth(410)
        dlg.setStyleSheet("""
            QInputDialog { background:#121821; }
            QLabel { color:#e7edf4; font-size:13px; font-weight:600; }
            QLineEdit { background:#080c12; color:#ffffff; border:1px solid #526174; border-radius:6px; padding:9px 10px; font-size:13px; selection-background-color:#2879b9; }
            QLineEdit:focus { border:1px solid #74bfff; }
            QPushButton { min-width:78px; padding:7px 12px; color:#e9f1f9; background:#202a37; border:1px solid #405166; border-radius:6px; }
            QPushButton:hover { background:#2b3a4d; border-color:#74bfff; }
        """)
        ok = dlg.exec_() == QInputDialog.Accepted
        name = dlg.textValue()
        if ok and name.strip():
            created = PlaylistManager.create_playlist(name.strip())
            if created:
                self._rebuild_category_tree()
                self.playlists_changed.emit()
                QMessageBox.information(self, "Playlist Created", f"Created playlist '{name.strip()}'. Right-click tracks to add songs!")
            else:
                QMessageBox.warning(self, "Notice", f"Playlist '{name.strip()}' already exists.")

    # -------------------------------------------------------------
    # FAST & NON-BLOCKING TABLE REFRESH (Handles 1000+ tracks smoothly)
    # -------------------------------------------------------------
    def refresh_table(self):
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        try:
            self.table.setRowCount(len(self._playlist))
            total_dur = 0.0
            liked_paths = PlaylistManager.get_liked_paths()

            # Pre-allocated style objects to avoid 50,000+ Python/C++ allocations
            col_fav = QColor("#f87171")
            col_dim = QColor("#475569")
            col_art = QColor("#38bdf8")
            fmt_colors = {
                "MP3": QColor("#72e6ff"),
                "FLAC": QColor("#70f0bd"),
                "WAV": QColor("#93c5fd"),
                "OGG": QColor("#fde047"),
                "M4A": QColor("#c084fc"),
                "AAC": QColor("#c084fc"),
                "OPUS": QColor("#f472b6"),
                "WMA": QColor("#fb923c")
            }
            default_fmt_col = QColor("#cbd5e1")

            for row, meta in enumerate(self._playlist):
                abs_p = meta.get("path", "")

                # 0: Track #
                self.table.setItem(row, 0, QTableWidgetItem(f"{row + 1:02d}"))

                # 1: Liked Heart / Star
                is_liked = abs_p in liked_paths
                heart_item = QTableWidgetItem("FAV" if is_liked else "-")
                heart_item.setTextAlignment(Qt.AlignCenter)
                heart_item.setForeground(col_fav if is_liked else col_dim)
                self.table.setItem(row, 1, heart_item)

                # 2: Cover Art Indicator (trust cached metadata to avoid 5,000+ disk stats)
                has_cover = bool(meta.get("artwork_path"))
                art_item = QTableWidgetItem("YES" if has_cover else "-")
                art_item.setTextAlignment(Qt.AlignCenter)
                art_item.setForeground(col_art if has_cover else col_dim)
                self.table.setItem(row, 2, art_item)

                # 3: Title
                self.table.setItem(row, 3, QTableWidgetItem(meta.get("title", "")))

                # 4: Artist
                self.table.setItem(row, 4, QTableWidgetItem(meta.get("artist", "")))

                # 5: Album
                self.table.setItem(row, 5, QTableWidgetItem(meta.get("album", "")))

                # 6: Audio Type Badge
                t_str = get_audio_type(meta)
                t_item = QTableWidgetItem(t_str)
                t_item.setTextAlignment(Qt.AlignCenter)
                t_item.setForeground(fmt_colors.get(t_str, default_fmt_col))
                self.table.setItem(row, 6, t_item)

                # 7: Year
                self.table.setItem(row, 7, QTableWidgetItem(str(meta.get("year", ""))))

                # 8: Duration
                dur = meta.get("duration", 0.0)
                total_dur += dur
                dur_str = f"{int(dur // 60):02d}:{int(dur % 60):02d}" if dur > 0 else "--:--"
                self.table.setItem(row, 8, QTableWidgetItem(dur_str))

            dur_mins = int(total_dur // 60)
            self.lbl_telemetry.setText(
                f"LIBRARY: {len(self._playlist)} TRACKS  •  TOTAL TIME: {dur_mins} MINS  •  ZERO-COPY POINTERS ACTIVE"
            )
        finally:
            self.table.setUpdatesEnabled(True)

        self._apply_all_filters()

    def update_row_meta(self, row, meta):
        if not (0 <= row < len(self._playlist)):
            return
        self._playlist[row].update(meta)
        abs_p = os.path.abspath(meta.get("path", ""))

        # Update favorite indicator
        is_liked = PlaylistManager.is_liked(abs_p)
        heart_item = QTableWidgetItem("FAV" if is_liked else "-")
        heart_item.setTextAlignment(Qt.AlignCenter)
        heart_item.setForeground(QColor("#f87171") if is_liked else QColor("#475569"))
        self.table.setItem(row, 1, heart_item)

        # Update cover indicator
        has_cover = bool(meta.get("artwork_path") and os.path.exists(meta["artwork_path"]))
        art_item = QTableWidgetItem("YES" if has_cover else "-")
        art_item.setTextAlignment(Qt.AlignCenter)
        art_item.setForeground(QColor("#38bdf8") if has_cover else QColor("#475569"))
        self.table.setItem(row, 2, art_item)

        self.table.setItem(row, 3, QTableWidgetItem(meta.get("title", "")))
        self.table.setItem(row, 4, QTableWidgetItem(meta.get("artist", "")))
        self.table.setItem(row, 5, QTableWidgetItem(meta.get("album", "")))

        # 6: Audio Type Badge
        t_str = get_audio_type(meta)
        t_item = QTableWidgetItem(t_str)
        t_item.setTextAlignment(Qt.AlignCenter)
        t_col = {
            "MP3": "#72e6ff",
            "FLAC": "#70f0bd",
            "WAV": "#93c5fd",
            "OGG": "#fde047",
            "M4A": "#c084fc",
            "AAC": "#c084fc",
            "OPUS": "#f472b6",
            "WMA": "#fb923c"
        }.get(t_str, "#cbd5e1")
        t_item.setForeground(QColor(t_col))
        font = t_item.font()
        font.setBold(True)
        t_item.setFont(font)
        self.table.setItem(row, 6, t_item)

        self.table.setItem(row, 7, QTableWidgetItem(str(meta.get("year", ""))))
        dur = meta.get("duration", 0.0)
        dur_str = f"{int(dur // 60):02d}:{int(dur % 60):02d}" if dur > 0 else "--:--"
        self.table.setItem(row, 8, QTableWidgetItem(dur_str))

        # Update card if this row is selected
        if row == self._selected_row:
            self._update_hero_cover_card(meta)

    # -------------------------------------------------------------
    # FILTERING & SELECTION
    # -------------------------------------------------------------
    def _apply_all_filters(self):
        search_q = self.txt_search.text().strip().lower()
        liked_paths = PlaylistManager.get_liked_paths() if self._active_filter_type == "PLAYLIST_LIKED" else None
        custom_paths = set(PlaylistManager.get_playlist_tracks(self._active_filter_val)) if self._active_filter_type == "PLAYLIST_CUSTOM" else None
        play_counts = PlaylistManager.get_most_played_map() if self._active_filter_type == "PLAYLIST_MOST_PLAYED" else None

        self.table.setUpdatesEnabled(False)
        try:
            for row in range(self.table.rowCount()):
                meta = self._playlist[row]
                abs_p = os.path.abspath(meta.get("path", ""))

                # 1. Search text check
                if search_q:
                    corpus = f"{meta.get('title', '')} {meta.get('artist', '')} {meta.get('album', '')} {meta.get('genre', '')} {get_audio_type(meta)}".lower()
                    if search_q not in corpus:
                        self.table.setRowHidden(row, True)
                        continue

                # 2. Audio Type Dropdown Filter check
                if self._selected_audio_type and self._selected_audio_type != "ALL":
                    if get_audio_type(meta) != self._selected_audio_type:
                        self.table.setRowHidden(row, True)
                        continue

                # 3. Category Tree Filter check
                if self._active_filter_type == "ALL":
                    self.table.setRowHidden(row, False)
                elif self._active_filter_type == "AUDIO_TYPE":
                    self.table.setRowHidden(row, get_audio_type(meta) != self._active_filter_val)
                elif self._active_filter_type == "PLAYLIST_LIKED":
                    self.table.setRowHidden(row, abs_p not in liked_paths)
                elif self._active_filter_type == "PLAYLIST_CUSTOM":
                    self.table.setRowHidden(row, abs_p not in custom_paths)
                elif self._active_filter_type == "PLAYLIST_MOST_PLAYED":
                    self.table.setRowHidden(row, play_counts.get(abs_p, 0) <= 0)
                elif self._active_filter_type == "ARTIST":
                    self.table.setRowHidden(row, meta.get("artist") != self._active_filter_val)
                elif self._active_filter_type == "ALBUM":
                    self.table.setRowHidden(row, (meta.get("album") or "Unknown Album") != self._active_filter_val)
                elif self._active_filter_type == "YEAR":
                    raw_year = meta.get("year")
                    year = str(raw_year)[:4] if raw_year else "Unknown Year"
                    self.table.setRowHidden(row, year != self._active_filter_val)
                elif self._active_filter_type == "GENRE":
                    self.table.setRowHidden(row, meta.get("genre") != self._active_filter_val)
                elif self._active_filter_type == "DECADE":
                    dec = detect_decade(meta.get("year", ""))
                    self.table.setRowHidden(row, dec != self._active_filter_val)
                elif self._active_filter_type == "LANGUAGE":
                    lng = detect_language(meta)
                    self.table.setRowHidden(row, lng != self._active_filter_val)
        finally:
            self.table.setUpdatesEnabled(True)

    def _get_real_index(self, row):
        if 0 <= row < len(self._playlist):
            return self._playlist[row].get("_orig_index", row)
        return row

    def _on_row_selected(self, row):
        if not (0 <= row < len(self._playlist)):
            return
        self._selected_row = row
        meta = self._playlist[row]
        self._update_hero_cover_card(meta)

    # -------------------------------------------------------------
    # HERO COVER BAY UPDATER
    # -------------------------------------------------------------
    def _update_hero_cover_card(self, meta):
        title = meta.get("title") or meta.get("filename") or "Unknown Track"
        artist = meta.get("artist") or "Unknown Artist"
        album = meta.get("album") or "Unknown Album"
        year = str(meta.get("year") or "")
        genre = meta.get("genre") or "Audio"
        dur = meta.get("duration", 0.0)
        dur_str = f"{int(dur // 60):02d}:{int(dur % 60):02d}" if dur > 0 else "--:--"

        abs_p = os.path.abspath(meta.get("path", ""))
        plays = PlaylistManager.get_play_count(abs_p)

        self.lbl_card_title.setText(title)
        self.lbl_card_artist.setText(f"{artist}  •  {album}")
        details_txt = f"{year} • {genre} • {dur_str}"
        if plays > 0:
            details_txt += f" • PLAYS: {plays}"
        self.lbl_card_details.setText(details_txt)
        self.lbl_detail_file.setText(meta.get("filename") or os.path.basename(meta.get("path", "")) or "Unknown file")
        self.lbl_detail_file.setToolTip(meta.get("path", ""))
        duration_text = f"{int(dur // 60):02d}:{int(dur % 60):02d}" if dur else "—"
        bitrate = meta.get("bitrate")
        sample_rate = meta.get("sample_rate")
        codec = meta.get("codec") or os.path.splitext(meta.get("path", ""))[1].lstrip(".").upper() or "—"
        values = {
            "title": title,
            "artist": artist,
            "album": album,
            "album_artist": meta.get("album_artist") or artist,
            "year": year or "—",
            "track": meta.get("track") or "—",
            "duration": duration_text,
            "codec": str(codec),
            "bitrate": f"{bitrate} kbps" if bitrate else "—",
            "sample_rate": f"{int(sample_rate):,} Hz" if sample_rate else "—",
            "comment": meta.get("comment") or "—",
        }
        for key, value in values.items():
            field = self._detail_values[key]
            field.setText(str(value))
            field.setToolTip(str(value))

        # Update Like button style
        is_liked = PlaylistManager.is_liked(abs_p)
        if is_liked:
            self.btn_card_like.setText("FAV")
            self.btn_card_like.setStyleSheet("background: #ef4444; border: 1px solid #f87171; border-radius: 3px; color: #ffffff; font-family: Monospace; font-size: 10px; font-weight: bold;")
        else:
            self.btn_card_like.setText("LIKE")
            self.btn_card_like.setStyleSheet("background: #1e2430; border: 1px solid #374151; border-radius: 3px; color: #94a3b8; font-family: Monospace; font-size: 10px; font-weight: bold;")

        # Render High-Resolution Artwork
        art_path = meta.get("artwork_path")
        if art_path and os.path.exists(art_path):
            pix = QPixmap(art_path)
            if not pix.isNull():
                scaled = pix.scaled(max(1, self.cover_art_label.width() - 8), max(1, self.cover_art_label.height() - 8), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.cover_art_label.setPixmap(scaled)
                return

        # Fallback default artwork placeholder
        self.cover_art_label.setText("NO COVER ART\n(Click COVER to Fetch)")

    def get_current_visible_sequence(self):
        """Returns list of real indices for all currently visible rows in the table in displayed order."""
        seq = []
        for r in range(self.table.rowCount()):
            if not self.table.isRowHidden(r):
                seq.append(self._get_real_index(r))
        return seq

    def _trigger_play_row(self, row):
        if not (0 <= row < self.table.rowCount()):
            return
        real_idx = self._get_real_index(row)
        visible_seq = self.get_current_visible_sequence()
        pos = visible_seq.index(real_idx) if real_idx in visible_seq else 0
        if not visible_seq:
            visible_seq = [real_idx]
            pos = 0
        self.play_context_requested.emit(visible_seq, pos, real_idx)
        self.track_double_clicked.emit(real_idx)

    def _on_cover_double_clicked(self, event):
        if 0 <= self._selected_row < len(self._playlist):
            self._trigger_play_row(self._selected_row)

    def _on_card_play_clicked(self):
        if 0 <= self._selected_row < len(self._playlist):
            self._trigger_play_row(self._selected_row)

    def _on_card_play_next_clicked(self):
        if 0 <= self._selected_row < len(self._playlist):
            real_idx = self._get_real_index(self._selected_row)
            self.play_next_requested.emit(real_idx)

    def _on_card_like_clicked(self):
        if not (0 <= self._selected_row < len(self._playlist)):
            return
        meta = self._playlist[self._selected_row]
        abs_p = os.path.abspath(meta.get("path", ""))
        is_liked = PlaylistManager.toggle_liked(abs_p)

        # Update like on card
        if is_liked:
            self.btn_card_like.setText("FAV")
            self.btn_card_like.setStyleSheet("background: #ef4444; border: 1px solid #f87171; border-radius: 3px; color: #ffffff; font-family: Monospace; font-size: 10px; font-weight: bold;")
        else:
            self.btn_card_like.setText("LIKE")
            self.btn_card_like.setStyleSheet("background: #1e2430; border: 1px solid #374151; border-radius: 3px; color: #94a3b8; font-family: Monospace; font-size: 10px; font-weight: bold;")

        # Update table cell in-place
        heart_item = QTableWidgetItem("FAV" if is_liked else "-")
        heart_item.setTextAlignment(Qt.AlignCenter)
        heart_item.setForeground(QColor("#f87171") if is_liked else QColor("#475569"))
        self.table.setItem(self._selected_row, 1, heart_item)

        # Refresh category tree counters
        self._rebuild_category_tree()

    def _on_card_add_playlist_clicked(self):
        if not (0 <= self._selected_row < len(self._playlist)):
            return
        self._show_add_to_playlist_dialog(self._selected_row)

    def _on_card_enrich_clicked(self):
        if not (0 <= self._selected_row < len(self._playlist)):
            return
        m = QMenu(self)
        m.setStyleSheet("""
            QMenu {
                background: #14171d !important;
                border: 2px solid #38bdf8 !important;
                border-radius: 6px;
                color: #ffffff !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 11px;
                padding: 6px;
            }
            QMenu::item {
                background: transparent;
                padding: 6px 20px;
                color: #e2e8f0 !important;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #0284c7 !important;
                color: #ffffff !important;
                font-weight: bold;
            }
        """)
        a_man_cov = m.addAction("Choose Cover Art Online (Select Candidate)...")
        a_auto_cov = m.addAction("Quick Auto-Fetch Artwork & Tags")
        a_man_lyr = m.addAction("Choose Lyrics Online (Select Candidate)...")
        a_edit_tag = m.addAction("Full Tag & Image Customizer...")
        act = m.exec_(self.btn_card_enrich.mapToGlobal(self.btn_card_enrich.rect().bottomLeft()))
        if act == a_man_cov:
            self._open_manual_cover_dialog(self._selected_row)
        elif act == a_auto_cov:
            self.fetch_online_requested.emit(self._selected_row)
        elif act == a_man_lyr:
            self._open_manual_lyrics_dialog(self._selected_row)
        elif act == a_edit_tag:
            self.customize_track_requested.emit(self._selected_row)

    def _open_manual_cover_dialog(self, row):
        if not (0 <= row < len(self._playlist)):
            return
        meta = self._playlist[row]
        dlg = ManualCoverSelectorDialog(meta.get("path", ""), meta, parent=self)
        dlg.metadata_applied.connect(lambda updated: self._on_manual_meta_applied(row, updated))
        dlg.exec_()

    def _on_manual_meta_applied(self, row, updated):
        if not (0 <= row < len(self._playlist)) or not updated:
            return
        self._playlist[row].update(updated)
        self.update_row_meta(row, updated)
        if self._selected_row == row:
            self._display_selected_track(row)
        self.track_metadata_changed.emit(row, updated)

    def _open_manual_lyrics_dialog(self, row):
        if not (0 <= row < len(self._playlist)):
            return
        meta = self._playlist[row]
        dlg = ManualLyricsSelectorDialog(
            meta.get("path", ""),
            meta.get("artist", ""),
            meta.get("title", ""),
            meta.get("duration", 0),
            parent=self
        )
        dlg.exec_()

    # -------------------------------------------------------------
    # CONTEXT MENUS WITH HIGH-CONTRAST READABLE STYLING
    # -------------------------------------------------------------
    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        self._selected_row = row
        meta = self._playlist[row]
        abs_p = os.path.abspath(meta.get("path", ""))
        is_liked = PlaylistManager.is_liked(abs_p)

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #14171d !important;
                border: 2px solid #38bdf8 !important;
                border-radius: 6px;
                color: #ffffff !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 11px;
                padding: 6px;
            }
            QMenu::item {
                background: transparent;
                padding: 6px 20px;
                color: #e2e8f0 !important;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #0284c7 !important;
                color: #ffffff !important;
                font-weight: bold;
            }
            QMenu::separator {
                height: 1px;
                background: #283240;
                margin: 4px 6px;
            }
        """)

        a_play = menu.addAction("Play Track Now")
        a_play_next = menu.addAction("Play Next (Queue Front)")
        a_add_queue = menu.addAction("Add to Queue")

        # Favorites toggle
        if is_liked:
            a_like = menu.addAction("Remove from Favorites")
        else:
            a_like = menu.addAction("Add to Favorites")

        # Custom Playlist Submenu
        pl_menu = menu.addMenu("Add to Custom Playlist")
        pl_menu.setStyleSheet(menu.styleSheet())
        custom_pls = PlaylistManager.get_all_playlists()
        for pl_name in sorted(custom_pls.keys()):
            act = pl_menu.addAction(f"{pl_name}")
            act.triggered.connect(lambda chk, n=pl_name, p=abs_p: self._add_track_to_playlist(n, p))

        pl_menu.addSeparator()
        a_new_pl = pl_menu.addAction("+ Create New Playlist...")
        a_new_pl.triggered.connect(lambda: self._create_new_playlist_and_add(abs_p))

        menu.addSeparator()
        a_man_cover = menu.addAction("Choose Cover Art Online (Select Candidate)...")
        a_man_lyrics = menu.addAction("Choose Lyrics Online (Select Candidate)...")
        a_fetch = menu.addAction("Quick Auto-Fetch Tags & Artwork")
        a_edit = menu.addAction("Edit Track Tags")
        menu.addSeparator()

        # Remove from active playlist if viewing a custom one
        if self._active_filter_type == "PLAYLIST_CUSTOM":
            a_del_pl = menu.addAction(f"Remove from '{self._active_filter_val}'")
        else:
            a_del_pl = None

        a_del = menu.addAction("Remove from Library Queue")

        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        real_idx = self._get_real_index(row)
        if action == a_play:
            self._trigger_play_row(row)
        elif action == a_play_next:
            self.play_next_requested.emit(real_idx)
        elif action == a_add_queue:
            self.add_to_queue_requested.emit(real_idx)
        elif action == a_like:
            self._on_card_like_clicked()
        elif action == a_man_cover:
            self._open_manual_cover_dialog(row)
        elif action == a_man_lyrics:
            self._open_manual_lyrics_dialog(row)
        elif action == a_fetch:
            self.fetch_online_requested.emit(real_idx)
        elif action == a_edit:
            self.customize_track_requested.emit(real_idx)
        elif action == a_del_pl and a_del_pl:
            PlaylistManager.remove_from_playlist(self._active_filter_val, abs_p)
            self._rebuild_category_tree()
            self._apply_all_filters()
            self.playlists_changed.emit()
        elif action == a_del:
            self.remove_track_requested.emit(real_idx)

    def _show_add_to_playlist_dialog(self, row):
        meta = self._playlist[row]
        abs_p = os.path.abspath(meta.get("path", ""))
        custom_pls = list(PlaylistManager.get_all_playlists().keys())
        options = ["Favorites"] + [f"{p}" for p in custom_pls] + ["+ Create New Playlist..."]

        choice, ok = QInputDialog.getItem(self, "Add to Playlist", "Select destination playlist:", options, 0, False)
        if ok and choice:
            if choice == "Favorites":
                PlaylistManager.set_liked(abs_p, True)
            elif choice == "+ Create New Playlist...":
                self._create_new_playlist_and_add(abs_p)
            else:
                pl_name = choice
                PlaylistManager.add_to_playlist(pl_name, abs_p)

            self._rebuild_category_tree()
            self.refresh_table()
            self.playlists_changed.emit()

    def _add_track_to_playlist(self, pl_name, abs_p):
        PlaylistManager.add_to_playlist(pl_name, abs_p)
        self._rebuild_category_tree()
        self.playlists_changed.emit()
        QMessageBox.information(self, "Added", f"Track added to playlist '{pl_name}'.")

    def _create_new_playlist_and_add(self, abs_p):
        name, ok = QInputDialog.getText(self, "New Playlist", "Enter custom playlist name:")
        if ok and name.strip():
            pl_name = name.strip()
            PlaylistManager.create_playlist(pl_name)
            PlaylistManager.add_to_playlist(pl_name, abs_p)
            self._rebuild_category_tree()
            self.refresh_table()
            self.playlists_changed.emit()

    # -------------------------------------------------------------
    # DYNAMIC HARDWARE THEME ADAPTATION
    # -------------------------------------------------------------
    def set_theme(self, theme_key, pal):
        self._theme_key = theme_key
        self._theme_pal = pal
        self._accent = pal.get("accent", "#00f0ff")
        self.detail_spectrum.set_theme_mode({"walkman": "amber", "glass": "winamp", "ipod": "silver", "vinyl": "amber", "studio_rack": "cyan"}.get(theme_key, "winamp"))

        self.lbl_zoom_val.setStyleSheet(f"color: {self._accent}; font-family: Monospace; font-size: 10px; font-weight: bold;")
        self._apply_typography_styles()
