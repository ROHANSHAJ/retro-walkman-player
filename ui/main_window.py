import os
import random
import subprocess
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStackedWidget, QPushButton, QComboBox, QFileDialog, QMessageBox,
    QButtonGroup, QFrame, QSystemTrayIcon, QMenu, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QTimer
from PyQt5.QtGui import QIcon, QFont, QDragEnterEvent, QDropEvent, QColor, QKeySequence, QPainter
from PyQt5.QtWidgets import QShortcut

from backend.audio_engine import AudioEngine, EQ_PRESETS
from backend.metadata_manager import MetadataManager, MetadataFetchWorker
from backend.library_organizer import SUPPORTED_EXTS
from backend.state_manager import StateManager
from backend.folder_loader import FolderLoaderWorker
from backend.mpris_service import MPRIS2Service
from backend.notification_manager import NotificationManager
from backend.playlist_manager import PlaylistManager

from ui.pages.player_deck_page import PlayerDeckPage
from ui.dialogs.player_track_details import PlayerTrackDetailsDialog
from ui.pages.lyrics_page import LyricsPage
from ui.pages.library_page import LibraryPage
from ui.pages.albums_page import AlbumsPage
from ui.pages.playlists_page import PlaylistsPage
from ui.pages.equalizer_page import EqualizerPage
from ui.pages.settings_page import SettingsPage, THEME_OPTIONS

from ui.dialogs.metadata_editor import MetadataEditorDialog
from ui.dialogs.organizer_dialog import OrganizerDialog
from ui.dialogs.library_scanner_hud import LibraryScannerHUD
from ui.dialogs.loading_dialog import LoadingScanDialog
from ui.dialogs.batch_enrich_dialog import BatchEnrichDialog
from ui.dialogs.duplicate_resolver_dialog import DuplicateResolverDialog
from ui.widgets.splash_screen import BootSplashScreen
from ui.widgets.mini_player_bar import MiniPlayerBar
from ui.widgets.spectrum_analyzer import WinampSpectrumAnalyzer


THEME_PALETTES = {
    "walkman": {
        "accent": "#ffb000",
        "bg": "#111318",
        "top_bezel": "#191b21",
        "tab_active": "#ffb000",
        "tab_text": "#121417",
        "text_primary": "#e4e8f0",
        "text_secondary": "#a0a6b2"
    },
    "glass": {
        "accent": "#72e6ff",
        "bg": "#0a1018",
        "top_bezel": "#111a24",
        "tab_active": "#72e6ff",
        "tab_text": "#071018",
        "text_primary": "#eefaff",
        "text_secondary": "#8eb4c5"
    },
    "ipod": {
        "accent": "#0070e0",
        "bg": "#10141b",
        "top_bezel": "#1b222d",
        "tab_active": "#0070e0",
        "tab_text": "#ffffff",
        "text_primary": "#ffffff",
        "text_secondary": "#a4a8b2"
    },
    "vinyl": {
        "accent": "#ffa020",
        "bg": "#171311",
        "top_bezel": "#211a16",
        "tab_active": "#ffa020",
        "tab_text": "#141518",
        "text_primary": "#ffffff",
        "text_secondary": "#b09870"
    },
    "studio_rack": {
        "accent": "#70f0bd",
        "bg": "#0d1112",
        "top_bezel": "#151c1b",
        "tab_active": "#70f0bd",
        "tab_text": "#0c1016",
        "text_primary": "#ffffff",
        "text_secondary": "#7c8896"
    }
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Default to completely opaque; WA_TranslucentBackground is only enabled if 'glass' skin is active
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowTitle("RETRO WALKMAN PRO  •  HI-FI HARDWARE DECK")
        self.resize(1100, 720)
        self.setMinimumSize(740, 520)
        self.setAcceptDrops(True)

        self._icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "retro_walkman.png")
        if os.path.exists(self._icon_path):
            self.setWindowIcon(QIcon(self._icon_path))

        # Audio engine initialization
        self._audio = AudioEngine(self)
        self._connect_audio_engine()

        # Desktop Integration (MPRIS2, Notifications, System Tray)
        self._notifications = NotificationManager(self)
        self._mpris = MPRIS2Service(self)
        self._connect_mpris_service()
        self._setup_system_tray()

        # State restoration
        saved_state = StateManager.load_state()
        self._playlist = saved_state.get("playlist", [])
        self._current_index = saved_state.get("current_index", -1)
        self._active_theme = saved_state.get("theme", "walkman")
        if self._active_theme == "dap_gold":  # migrate older saved preference to classic walkman
            self._active_theme = "walkman"
        self._repeat_mode = saved_state.get("repeat_mode", "ALL")
        self._is_shuffled = saved_state.get("is_shuffled", False)
        self._glass_transparency = int(saved_state.get("glass_transparency", 30))
        self._glass_frosting = int(saved_state.get("glass_frosting", 40))
        self._animations_enabled = bool(saved_state.get("animations_enabled", True))
        self._user_queue = []
        self._active_play_order = []
        self._order_pos = 0
        self._active_context_name = "All Tracks"
        self._bg_workers = []
        self._deferred_state_save_timer = QTimer(self)
        self._deferred_state_save_timer.setSingleShot(True)
        self._deferred_state_save_timer.setInterval(350)
        self._deferred_state_save_timer.timeout.connect(self._persist_state)
        saved_volume = saved_state.get("volume", 0.85)
        self._audio.set_volume(saved_volume)

        self._build_hardware_frame()
        self._install_keyboard_shortcuts()
        self.statusBar().showMessage("Ctrl+Space  Play / Pause     Ctrl+O  Add tracks     Ctrl+1–7  Switch pages")
        self.statusBar().setVisible(False)
        self._wire_hardware_deck_dsp()
        self._update_top_transport_styles()
        self._apply_global_theme(self._active_theme)
        self.page_settings.set_glass_transparency(self._glass_transparency)
        self.page_settings.set_glass_frosting(self._glass_frosting)
        self.page_settings.set_animations_enabled(self._animations_enabled)
        self.page_deck.set_glass_transparency(self._glass_transparency)
        self.page_deck.set_glass_frosting(self._glass_frosting)
        self.page_deck.set_animations_enabled(self._animations_enabled)

        # Restore saved font size
        saved_font_sz = saved_state.get("library_font_size", 13)
        self.page_library.set_library_font_size(saved_font_sz)
        self.page_settings.set_library_font_size(saved_font_sz)

        # Restore saved playlist into library
        if self._playlist:
            self.page_library.set_playlist(self._playlist)
            self._refresh_collection_pages()
            idx = max(0, min(self._current_index, len(self._playlist) - 1))
            self.load_track(idx, auto_start=False)

    def _connect_audio_engine(self):
        self._audio.position_changed.connect(self._on_position_changed)
        self._audio.state_changed.connect(self._on_state_changed)
        self._audio.track_finished.connect(self._on_track_finished)
        self._audio.audio_level.connect(self._on_audio_level)
        self._audio.error_occurred.connect(lambda err: QMessageBox.warning(self, "Audio Error", err))

    def _connect_mpris_service(self):
        self._mpris.play_requested.connect(self._audio.play)
        self._mpris.pause_requested.connect(self._audio.pause)
        self._mpris.play_pause_requested.connect(self._audio.toggle_play_pause)
        self._mpris.stop_requested.connect(self._audio.stop)
        self._mpris.next_requested.connect(self.play_next)
        self._mpris.prev_requested.connect(self.play_previous)
        self._mpris.seek_requested.connect(lambda offset: self._audio.seek_relative(offset))
        self._mpris.raise_requested.connect(self._restore_from_tray)
        self._mpris.quit_requested.connect(QApplication.instance().quit)

    def _setup_system_tray(self):
        self.tray = QSystemTrayIcon(self)
        if os.path.exists(self._icon_path):
            self.tray.setIcon(QIcon(self._icon_path))
        self.tray.setToolTip("Retro Walkman Pro — Hi-Fi Deck")

        tray_menu = QMenu(self)
        tray_menu.setStyleSheet("""
            QMenu {
                background: #121418;
                border: 1px solid #28303c;
                color: #e2e8f0;
                font-family: Monospace;
                font-size: 11px;
            }
            QMenu::item:selected { background: #0088cc; color: #ffffff; }
        """)

        a_play = tray_menu.addAction("Play / Pause")
        a_play.triggered.connect(self._on_play_pause_clicked)

        a_next = tray_menu.addAction("Next Track")
        a_next.triggered.connect(self.play_next)

        a_prev = tray_menu.addAction("Previous Track")
        a_prev.triggered.connect(self.play_previous)

        tray_menu.addSeparator()

        a_restore = tray_menu.addAction("Show / Restore Window")
        a_restore.triggered.connect(self._restore_from_tray)

        a_quit = tray_menu.addAction("Quit Retro Walkman")
        a_quit.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _wire_hardware_deck_dsp(self):
        """
        Actively wires up physical deck dials and buttons to real GStreamer DSP filters.
        """
        # 1. Walkman Deck
        self.page_deck.walkman.knob_tone.valueChanged.connect(lambda v: self._audio.set_tone(v, 1.0 - v))
        self.page_deck.walkman.knob_bal.valueChanged.connect(lambda v: self._audio.set_panning((v - 0.5) * 2.0))
        self.page_deck.walkman.btn_megabass.clicked.connect(self._toggle_walkman_megabass)
        self.page_deck.walkman.combo_dolby.currentIndexChanged.connect(lambda mode: self._audio.set_dolby_nr(mode > 0))

        # 2. Smoked-glass hi-fi player
        self.page_deck.glass.knob_bass.valueChanged.connect(lambda v: self._audio.set_eq_band(0, (v - 0.5) * 16.0))
        self.page_deck.glass.knob_treble.valueChanged.connect(lambda v: self._audio.set_eq_band(9, (v - 0.5) * 16.0))
        self.page_deck.glass.btn_gain.clicked.connect(self._toggle_dap_gain)
        self.page_deck.glass.btn_dsd.clicked.connect(self._toggle_dap_direct)

        # 3. iPod Classic
        self.page_deck.ipod.knob_bass.valueChanged.connect(lambda v: self._audio.set_eq_band(1, (v - 0.5) * 14.0))
        self.page_deck.ipod.knob_treble.valueChanged.connect(lambda v: self._audio.set_eq_band(8, (v - 0.5) * 14.0))
        self.page_deck.ipod.btn_bass_boost.clicked.connect(self._toggle_ipod_bass)
        self.page_deck.ipod.btn_acoustic.clicked.connect(self._toggle_ipod_acoustic)
        self.page_deck.ipod.btn_repeat.clicked.connect(self._cycle_repeat)
        self.page_deck.ipod.btn_shuffle.clicked.connect(self._toggle_shuffle)
        self.page_deck.ipod.btn_hold.clicked.connect(self._toggle_ipod_hold)

        # 4. Vinyl Turntable
        self.page_deck.vinyl.knob_pitch.valueChanged.connect(lambda v: self._audio.set_playback_rate(0.85 + v * 0.30))
        self.page_deck.vinyl.knob_skate.valueChanged.connect(self.page_deck.vinyl.turntable.set_anti_skate)
        self.page_deck.vinyl.turntable.set_anti_skate(self.page_deck.vinyl.knob_skate.get_value())
        self.page_deck.vinyl.btn_phono.clicked.connect(self._toggle_vinyl_phono)

        # 5. Studio Rack
        self.page_deck.studio.knob_bass.valueChanged.connect(lambda v: self._audio.set_eq_band(1, (v - 0.5) * 16.0))
        self.page_deck.studio.knob_treble.valueChanged.connect(lambda v: self._audio.set_eq_band(8, (v - 0.5) * 16.0))
        self.page_deck.studio.btn_mute.clicked.connect(self._toggle_studio_mute)
        self.page_deck.studio.btn_loudness.clicked.connect(self._toggle_studio_loudness)
        self.page_deck.studio.btn_subsonic.clicked.connect(self._toggle_studio_subsonic)

        # 6. Lyrics Teleprompter Station
        self.page_lyrics.knob_vocal.valueChanged.connect(lambda v: self._audio.set_vocal_boost((v - 0.5) * 14.0))
        self.page_lyrics.knob_ambience.valueChanged.connect(lambda v: self._audio.set_panning((v - 0.5) * 1.5))

    def _toggle_walkman_megabass(self):
        b = self.page_deck.walkman.btn_megabass
        b.set_led(not b.led_on, "#ffaa00")
        self._audio.set_mega_bass(b.led_on)

    def _toggle_dap_gain(self):
        b = self.page_deck.glass.btn_gain
        b.set_led(not b.led_on, "#ff5500")
        self._audio.set_preamp_gain(4.0 if b.led_on else 0.0)

    def _set_named_eq_preset(self, name):
        self._audio.set_eq_preset(name)
        if hasattr(self, "page_eq"):
            self.page_eq.preset_combo.setCurrentText(name)
        if hasattr(self, "page_settings"):
            self.page_settings.combo_dsp_preset.setCurrentText(name)

    def _toggle_dap_direct(self):
        button = self.page_deck.glass.btn_dsd
        enabled = not button.led_on
        button.set_led(enabled, "#70f0bd")
        self._set_named_eq_preset("Flat" if enabled else "B&O Signature (HP Victus)")

    def _toggle_ipod_bass(self):
        button = self.page_deck.ipod.btn_bass_boost
        enabled = not button.led_on
        button.set_led(enabled, "#0070e0")
        self._audio.set_mega_bass(enabled)

    def _toggle_ipod_acoustic(self):
        button = self.page_deck.ipod.btn_acoustic
        enabled = not button.led_on
        button.set_led(enabled, "#ffaa00")
        self._set_named_eq_preset("Jazz" if enabled else "Flat")

    def _toggle_ipod_hold(self):
        button = self.page_deck.ipod.btn_hold
        locked = not button.led_on
        button.set_led(locked, "#ff4444")
        ipod = self.page_deck.ipod
        for control in (ipod.click_wheel, ipod.knob_vol, ipod.knob_bass,
                        ipod.knob_treble, ipod.btn_bass_boost, ipod.btn_acoustic,
                        ipod.btn_repeat, ipod.btn_shuffle):
            control.setEnabled(not locked)
        button.setText("HOLD ON" if locked else "HOLD SWITCH")

    def _toggle_studio_loudness(self):
        button = self.page_deck.studio.btn_loudness
        enabled = not button.led_on
        button.set_led(enabled, "#00f0ff")
        self._set_named_eq_preset("B&O Signature (HP Victus)" if enabled else "Flat")

    def _toggle_studio_subsonic(self):
        button = self.page_deck.studio.btn_subsonic
        enabled = not button.led_on
        button.set_led(enabled, "#00f0ff")
        preset = "Subsonic / Turntable Rumble Cut" if enabled else "Flat"
        self._set_named_eq_preset(preset)

    def _toggle_vinyl_phono(self):
        b = self.page_deck.vinyl.btn_phono
        b.set_led(not b.led_on, "#ffaa00")
        self._audio.set_phono_preamp(b.led_on)

    def _toggle_studio_mute(self):
        b = self.page_deck.studio.btn_mute
        b.set_led(not b.led_on, "#ff4444")
        self._audio.set_preamp_gain(-20.0 if b.led_on else 0.0)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._active_theme == "glass":
            clarity = self._glass_transparency / 100.0
            alpha = max(0, min(255, round(255 * (1.0 - clarity))))
            painter.fillRect(self.rect(), QColor(10, 16, 24, alpha))
        else:
            pal = THEME_PALETTES.get(self._active_theme, THEME_PALETTES["walkman"])
            painter.fillRect(self.rect(), QColor(pal["bg"]))

    def _build_hardware_frame(self):
        central = QWidget(self)
        central.setObjectName("centralWidget")
        central.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------------------------------------------------------
        # 1. Music navigation and compact hardware status strip
        # ---------------------------------------------------------
        self.top_bezel = QFrame()
        self.top_bezel.setMinimumHeight(76)
        self.top_bezel.setObjectName("topBezel")
        tb_layout = QVBoxLayout(self.top_bezel)
        tb_layout.setContentsMargins(14, 5, 14, 5)
        tb_layout.setSpacing(4)
        brand_row = QHBoxLayout()
        brand_row.setSpacing(7)
        nav_row = QHBoxLayout()
        nav_row.setSpacing(5)

        self.logo_lbl = QLabel("RETRO WALKMAN")
        self.logo_lbl.setStyleSheet("color: #d5dce6; font-family: Monospace; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        brand_row.addWidget(self.logo_lbl)

        self.btn_music = QPushButton("MUSIC")
        self.btn_music.setToolTip("Open your music library")
        self.btn_music.clicked.connect(lambda: self._switch_page(2))
        brand_row.addWidget(self.btn_music)

        self.combo_playlist = QComboBox()
        self.combo_playlist.setObjectName("playlistSelector")
        self.combo_playlist.setMinimumWidth(126)
        self.combo_playlist.setMaximumWidth(190)
        self.combo_playlist.setToolTip("Choose a library view or custom playlist")
        self.combo_playlist.setAccessibleName("Playlist selector")
        self._refresh_playlist_selector()
        self.combo_playlist.currentIndexChanged.connect(self._on_playlist_view_changed)
        brand_row.addWidget(self.combo_playlist)

        self.btn_new_playlist = QPushButton("+ NEW PLAYLIST")
        self.btn_new_playlist.clicked.connect(self._create_playlist_from_header)
        brand_row.addWidget(self.btn_new_playlist)

        self.btn_menu = QPushButton("MENU")
        self.btn_menu.setToolTip("Open library and application actions")
        self.app_menu = QMenu(self)
        self.app_menu.addAction("Add Folder…", self._open_folder_dialog)
        self.app_menu.addAction("Add Files…", self._open_files_dialog)
        self.app_menu.addSeparator()
        self.app_menu.addAction("Music Library", lambda: self._switch_page(2))
        self.app_menu.addAction("Lyrics", lambda: self._switch_page(1))
        self.app_menu.addAction("Equalizer", lambda: self._switch_page(3))
        self.app_menu.addAction("Settings", lambda: self._switch_page(4))
        self.app_menu.addAction("Albums", lambda: self._switch_page(5))
        self.app_menu.addAction("Playlists", lambda: self._switch_page(6))
        self.app_menu.addSeparator()
        self.app_menu.addAction("Quit Retro Walkman", QApplication.instance().quit)
        self.btn_menu.clicked.connect(lambda: self.app_menu.exec_(self.btn_menu.mapToGlobal(self.btn_menu.rect().bottomLeft())))
        brand_row.addWidget(self.btn_menu)

        brand_row.addStretch(1)

        self.top_spectrum = WinampSpectrumAnalyzer(bands_count=24, theme_mode="winamp", parent=self)
        self.top_spectrum.setFixedSize(132, 34)
        self.top_spectrum.setToolTip("Live stereo spectrum • click to switch to oscilloscope")
        brand_row.addWidget(self.top_spectrum)

        self.lbl_theme_title = QLabel("SKIN")
        self.lbl_theme_title.setStyleSheet("color: #8b95a4; font-family: Monospace; font-size: 9px; font-weight: bold;")
        brand_row.addWidget(self.lbl_theme_title)

        self.combo_theme = QComboBox()
        self.combo_theme.setMinimumWidth(142)
        self.combo_theme.setMaximumWidth(205)
        for title, key, _ in THEME_OPTIONS:
            self.combo_theme.addItem(title, key)
        init_idx = self.combo_theme.findData(self._active_theme)
        if init_idx >= 0:
            self.combo_theme.setCurrentIndex(init_idx)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_combo_changed)
        brand_row.addWidget(self.combo_theme)

        # App workspace navigation
        self.tab_group = QButtonGroup(self)
        self.tab_buttons = []
        tab_defs = [
            ("PLAYER DECK", 0),
            ("LYRICS", 1),
            ("LIBRARY", 2),
            ("EQUALIZER", 3),
            ("SETUP", 4),
            ("ALBUMS", 5),
            ("PLAYLISTS", 6),
        ]

        for label, idx in tab_defs:
            btn = QPushButton(label)
            btn.setToolTip(f"Open {label.title()} page (Ctrl+{idx + 1})")
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            self.tab_group.addButton(btn)
            self.tab_buttons.append(btn)
            nav_row.addWidget(btn)
        tb_layout.addLayout(brand_row)
        tb_layout.addLayout(nav_row)

        root.addWidget(self.top_bezel)

        # ---------------------------------------------------------
        # 2. MAIN CENTER STACKED DISPLAY
        # ---------------------------------------------------------
        self.pages_stack = QStackedWidget()

        # Page 0: Hardware Player Deck
        self.page_deck = PlayerDeckPage(self)
        self.page_deck.library_requested.connect(lambda: self._switch_page(2))
        self.page_deck.art_clicked.connect(self._on_customize_current)
        self.page_deck.track_details_requested.connect(self._open_current_track_details)
        self.page_deck.play_clicked.connect(self._on_play_pause_clicked)
        self.page_deck.pause_clicked.connect(self._audio.pause)
        self.page_deck.stop_clicked.connect(self._audio.stop)
        self.page_deck.prev_clicked.connect(self.play_previous)
        self.page_deck.next_clicked.connect(self.play_next)
        self.page_deck.rew_clicked.connect(lambda: self._audio.seek_relative(-10))
        self.page_deck.ff_clicked.connect(lambda: self._audio.seek_relative(10))
        self.page_deck.seek_moved.connect(self._on_seek_moved)
        self.page_deck.volume_changed.connect(self._on_volume_changed)
        self.page_deck.change_next_requested.connect(self._open_queue_drawer)
        self.page_deck.glass_frosting_changed.connect(self._set_glass_frosting)
        self.pages_stack.addWidget(self.page_deck)

        # Page 1: Synchronized Lyrics Station
        self.page_lyrics = LyricsPage(self)
        self.page_lyrics.seek_requested.connect(self._audio.seek)
        self.page_lyrics.slider_seek_moved.connect(self._on_seek_moved)
        self.page_lyrics.art_clicked.connect(self._on_customize_current)
        self.pages_stack.addWidget(self.page_lyrics)

        # Page 2: Music Library & Queue (with Category Explorer, Batch Auto-Tag & Duplicate Resolver)
        self.page_library = LibraryPage(self)
        self.page_library.play_context_requested.connect(self._on_play_context_requested)
        self.page_library.play_next_requested.connect(self._on_play_next_requested)
        self.page_library.add_to_queue_requested.connect(self._on_add_to_queue_requested)
        self.page_library.playlists_changed.connect(self._refresh_playlists)
        self.page_library.open_folder_requested.connect(self._open_folder_dialog)
        self.page_library.add_files_requested.connect(self._open_files_dialog)
        self.page_library.organize_pointers_requested.connect(self._open_organizer_dialog)
        self.page_library.batch_enrich_requested.connect(self._open_batch_enrich_dialog)
        self.page_library.detect_duplicates_requested.connect(self._open_duplicate_resolver)
        self.page_library.customize_track_requested.connect(self._open_editor_for_row)
        self.page_library.fetch_online_requested.connect(self._fetch_row_online)
        self.page_library.track_metadata_changed.connect(self._on_metadata_updated)
        self.page_library.remove_track_requested.connect(self._remove_track)
        self.pages_stack.addWidget(self.page_library)

        # Page 3: 10-Band Graphic Equalizer with B&O profiles
        self.page_eq = EqualizerPage(self)
        self.page_eq.band_changed.connect(self._audio.set_eq_band)
        self.page_eq.preset_selected.connect(self._audio.set_eq_preset)
        self.page_eq.volume_changed.connect(self._on_volume_changed)
        self.pages_stack.addWidget(self.page_eq)

        # Page 4: Setup & Settings
        self.page_settings = SettingsPage(self)
        self.page_settings.theme_changed.connect(self._apply_global_theme)
        self.page_settings.glass_transparency_changed.connect(self._set_glass_transparency)
        self.page_settings.glass_frosting_changed.connect(self._set_glass_frosting)
        self.page_settings.animations_toggled.connect(self._set_theme_animations)
        self.page_settings.led_color_changed.connect(self.page_deck.walkman.set_theme)
        self.page_settings.audio_output_changed.connect(self._audio.set_audio_output)
        self.page_settings.dsp_preset_changed.connect(lambda p: (self._audio.set_eq_preset(p), self.page_eq.preset_combo.setCurrentText(p)))
        self.page_settings.mega_bass_toggled.connect(self._audio.set_mega_bass)
        self.page_settings.dolby_nr_toggled.connect(self._audio.set_dolby_nr)
        self.page_settings.phono_toggled.connect(self._audio.set_phono_preamp)
        self.page_settings.vocal_boost_toggled.connect(self._audio.set_vocal_boost)
        self.page_settings.pitch_changed.connect(self._audio.set_playback_rate)
        self.page_settings.preamp_changed.connect(self._audio.set_preamp_gain)
        self.page_settings.panning_changed.connect(self._audio.set_panning)
        self.page_settings.lyrics_autoscroll_toggled.connect(lambda on: setattr(self.page_lyrics, "_auto_scroll_enabled", on))
        self.page_settings.lyrics_glow_toggled.connect(lambda on: (setattr(self.page_lyrics, "_karaoke_glow_enabled", on), [w.set_karaoke_glow(on) for w in self.page_lyrics._line_widgets]))
        self.page_settings.lyrics_font_size_changed.connect(lambda sz: (setattr(self.page_lyrics, "_font_size", sz), [w.set_font_size(sz) for w in self.page_lyrics._line_widgets]))
        self.page_settings.lyrics_offset_changed.connect(lambda off: setattr(self.page_lyrics, "_sync_offset", off))
        self.page_settings.organize_pointers_requested.connect(self._open_organizer_dialog)
        self.page_settings.batch_enrich_requested.connect(self._open_batch_enrich_dialog)
        self.page_settings.detect_duplicates_requested.connect(self._open_duplicate_resolver)
        self.page_settings.library_font_size_changed.connect(self.page_library.set_library_font_size)
        self.page_settings.library_row_height_changed.connect(lambda h: self.page_library.table.verticalHeader().setDefaultSectionSize(h))
        self.page_settings.playlists_updated.connect(self._refresh_playlists)
        self.page_settings.chk_show_cover_bay.toggled.connect(self.page_library.cover_box.setVisible)
        self.page_library.font_size_changed.connect(self.page_settings.set_library_font_size)
        self.pages_stack.addWidget(self.page_settings)

        self.page_albums = AlbumsPage(self._playlist, self)
        self.page_albums.play_track.connect(lambda row: self.load_track(row, auto_start=True))
        self.page_albums.play_context_requested.connect(self._on_play_context_requested)
        self.pages_stack.addWidget(self.page_albums)

        self.page_playlists = PlaylistsPage(self._playlist, self)
        self.page_playlists.play_track.connect(lambda row: self.load_track(row, auto_start=True))
        self.page_playlists.play_context_requested.connect(self._on_play_context_requested)
        self.page_playlists.browse_library.connect(self._browse_music_for_playlist_add)
        self.page_playlists.playlists_changed.connect(self._refresh_playlists)
        self.pages_stack.addWidget(self.page_playlists)

        root.addWidget(self.pages_stack, 1)

        # Persistent reference-style transport strip
        self.mini_player = MiniPlayerBar(self)
        self.mini_player.play_pause_clicked.connect(self._on_play_pause_clicked)
        self.mini_player.prev_clicked.connect(self.play_previous)
        self.mini_player.next_clicked.connect(self.play_next)
        self.mini_player.stop_clicked.connect(self._audio.stop)
        self.mini_player.rewind_clicked.connect(lambda: self._audio.seek_relative(-10))
        self.mini_player.fast_forward_clicked.connect(lambda: self._audio.seek_relative(10))
        self.mini_player.seek_moved.connect(self._on_seek_moved)
        self.mini_player.volume_changed.connect(self._on_volume_changed)
        self.mini_player.lyrics_toggle_clicked.connect(lambda: self._switch_page(1))
        self.mini_player.art_clicked.connect(self._on_customize_current)
        self.mini_player.shuffle_clicked.connect(self._toggle_shuffle)
        self.mini_player.repeat_clicked.connect(self._cycle_repeat)
        self.mini_player.queue_clicked.connect(self._open_queue_drawer)
        self.mini_player.slider_vol.blockSignals(True)
        self.mini_player.slider_vol.setValue(int(self._audio.get_volume() * 100))
        self.mini_player.slider_vol.blockSignals(False)
        root.addWidget(self.mini_player)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, "combo_playlist"):
            return
        compact = event.size().width() < 1000
        narrow = event.size().width() < 820
        self.top_spectrum.setVisible(not compact)
        self.lbl_theme_title.setVisible(not compact)
        self.logo_lbl.setVisible(not narrow)
        self.combo_playlist.setMaximumWidth(132 if compact else 190)
        self.combo_theme.setMaximumWidth(150 if compact else 205)
        self.btn_music.setText("LIB" if narrow else "MUSIC")
        self.btn_music.setToolTip("Open your music library")
        self.btn_new_playlist.setText("+ LIST" if compact else "+ NEW PLAYLIST")
        self.btn_new_playlist.setToolTip("Create a playlist")
        self.btn_menu.setText("OPT" if narrow else "MENU")

    def _switch_page(self, index):
        self.pages_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == index)
        self._persist_state()

    def _install_keyboard_shortcuts(self):
        """Keep common playback and navigation actions within easy reach."""
        shortcuts = [
            ("Ctrl+Space", self._on_play_pause_clicked),
            ("Ctrl+Right", self.play_next),
            ("Ctrl+Left", self.play_previous),
            ("Ctrl+O", self._open_files_dialog),
            ("Ctrl+L", lambda: self._switch_page(2)),
            ("Ctrl+1", lambda: self._switch_page(0)),
            ("Ctrl+2", lambda: self._switch_page(1)),
            ("Ctrl+3", lambda: self._switch_page(2)),
            ("Ctrl+4", lambda: self._switch_page(3)),
            ("Ctrl+5", lambda: self._switch_page(4)),
            ("Ctrl+6", lambda: self._switch_page(5)),
            ("Ctrl+7", lambda: self._switch_page(6)),
        ]
        self._shortcuts = []
        for sequence, callback in shortcuts:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _refresh_playlist_selector(self):
        if not hasattr(self, "combo_playlist"):
            return
        current = self.combo_playlist.currentData()
        self.combo_playlist.blockSignals(True)
        self.combo_playlist.clear()
        self.combo_playlist.addItem("Default", None)
        for name in sorted(PlaylistManager.get_all_playlists()):
            self.combo_playlist.addItem(name, name)
        index = self.combo_playlist.findData(current)
        self.combo_playlist.setCurrentIndex(index if index >= 0 else 0)
        self.combo_playlist.blockSignals(False)

    def _refresh_collection_pages(self):
        if hasattr(self, "page_library"):
            self.page_library._rebuild_category_tree()
        if hasattr(self, "page_albums"):
            self.page_albums.set_library(self._playlist)
        if hasattr(self, "page_playlists"):
            self.page_playlists.set_library(self._playlist)
        self._refresh_playlist_selector()

    def _refresh_playlists(self):
        if hasattr(self, "page_library"):
            self.page_library._rebuild_category_tree()
        if hasattr(self, "page_playlists"):
            self.page_playlists.refresh_playlists()
        self._refresh_playlist_selector()

    def _on_playlist_view_changed(self, index):
        if not hasattr(self, "page_library"):
            return
        playlist_name = self.combo_playlist.itemData(index)
        if playlist_name:
            self.page_library.set_library_filter("PLAYLIST_CUSTOM", playlist_name)
        else:
            self.page_library.set_library_filter("ALL", None)
        self._switch_page(2)

    def _browse_music_for_playlist_add(self):
        self.combo_playlist.blockSignals(True)
        default_index = self.combo_playlist.findData(None)
        if default_index >= 0:
            self.combo_playlist.setCurrentIndex(default_index)
        self.combo_playlist.blockSignals(False)
        self.page_library.set_library_filter("ALL", None)
        self._switch_page(2)

    def _create_playlist_from_header(self):
        self._switch_page(2)
        self.page_library._create_new_playlist_prompt()
        self._refresh_playlist_selector()

    def _on_theme_combo_changed(self, idx):
        key = self.combo_theme.itemData(idx) if idx >= 0 else self.combo_theme.currentData()
        self._apply_global_theme(key)

    def _set_glass_transparency(self, value):
        self._glass_transparency = max(0, min(100, int(value)))
        self.page_deck.set_glass_transparency(self._glass_transparency)
        self.page_settings.set_glass_transparency(self._glass_transparency)
        self._deferred_state_save_timer.start()

    def _set_glass_frosting(self, value):
        self._glass_frosting = max(0, min(100, int(value)))
        self.page_deck.set_glass_frosting(self._glass_frosting)
        self.page_settings.set_glass_frosting(self._glass_frosting)
        self._deferred_state_save_timer.start()

    def _open_current_track_details(self):
        if not (0 <= self._current_index < len(self._playlist)):
            QMessageBox.information(self, "No track selected", "Load a track to view its details and browse related music.")
            return
        dialog = PlayerTrackDetailsDialog(self._playlist[self._current_index], self._playlist, self)
        dialog.playlists_changed.connect(self._refresh_playlists)
        dialog.open_catalog_requested.connect(self._open_catalog_from_track_details)
        dialog.play_track_requested.connect(self._play_path_from_track_details)
        dialog.exec_()

    def _open_catalog_from_track_details(self, field, value, artist):
        if field == "album":
            self.page_albums.set_library(self._playlist)
            self.page_albums.open_album(value, artist)
            self._switch_page(5)
            return

        filter_type = {"artist": "ARTIST", "genre": "GENRE"}.get(field)
        if filter_type:
            self.page_library.open_category_filter(filter_type, value)
            self._switch_page(2)

    def _play_path_from_track_details(self, path):
        wanted_path = os.path.abspath(path)
        for index, track in enumerate(self._playlist):
            if os.path.abspath(track.get("path", "")) == wanted_path:
                self.load_track(index, auto_start=True)
                return

    def _set_theme_animations(self, enabled):
        self._animations_enabled = bool(enabled)
        self.page_deck.set_animations_enabled(self._animations_enabled)
        self._deferred_state_save_timer.start()

    def _apply_global_theme(self, theme_key):
        self._active_theme = theme_key
        pal = THEME_PALETTES.get(theme_key, THEME_PALETTES["walkman"])

        # Main window and central widgets are strictly 100% opaque to guarantee
        # crisp X11 rendering and eliminate multi-page ghosting and crashes.
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        if self.centralWidget():
            self.centralWidget().setAttribute(Qt.WA_TranslucentBackground, False)

        window_background = pal["bg"]

        # Switch Player Deck hardware skin
        self.page_deck.switch_theme(theme_key)

        # Update combobox selection if not in sync
        c_idx = self.combo_theme.findData(theme_key)
        if c_idx >= 0 and self.combo_theme.currentIndex() != c_idx:
            self.combo_theme.blockSignals(True)
            self.combo_theme.setCurrentIndex(c_idx)
            self.combo_theme.blockSignals(False)

        # Global Unified Styling across all windows & subpages
        self.setStyleSheet(f"""
            QMainWindow, QWidget#centralWidget, QStackedWidget {{
                background-color: {window_background};
            }}
            QWidget {{ color: {pal['text_primary']}; }}
            #topBezel {{
                background: {pal['top_bezel']};
                border-bottom: 2px solid rgba(0, 0, 0, 0.7);
            }}
            #topBezel QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3036, stop:0.5 #22252a, stop:1 #181a1d);
                border: 1px solid #3c424c;
                border-radius: 4px;
                padding: 4px 9px;
                color: #b0b6c2;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
            }}
            #topBezel QPushButton:hover {{
                background: #363c46;
                color: #ffffff;
            }}
            #topBezel QPushButton:checked {{
                background: {pal['tab_active']};
                border: 1px solid {pal['tab_active']};
                color: {pal['tab_text']};
                font-weight: bold;
            }}
            QComboBox {{
                background: #14171d !important;
                border: 1px solid #394656 !important;
                border-radius: 4px;
                padding: 4px 10px;
                color: #ffffff !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 11px;
                font-weight: bold;
            }}
            QComboBox:focus {{ border: 1px solid #91b5cd !important; outline: none; }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #28303c;
            }}
            QComboBox QAbstractItemView {{
                background-color: #12151b !important;
                border: 2px solid {pal['accent']} !important;
                border-radius: 6px;
                padding: 4px;
                color: #ffffff !important;
                selection-background-color: {pal['accent']} !important;
                selection-color: {pal['tab_text']} !important;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                background-color: #12151b !important;
                color: {pal['text_primary']} !important;
                min-height: 28px;
                padding: 4px 10px;
                border-radius: 3px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #1e293b !important;
                color: {pal['accent']} !important;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {pal['accent']} !important;
                color: {pal['tab_text']} !important;
                font-weight: bold;
            }}
            QComboBox QAbstractItemView::viewport,
            QComboBox QListView {{
                background-color: #121821 !important;
                color: {pal['text_primary']} !important;
            }}
            QComboBox QListView::item {{
                background-color: #121821 !important;
                color: {pal['text_primary']} !important;
                min-height: 28px;
                padding: 5px 9px;
            }}
            QComboBox QListView::item:hover {{
                background-color: #273342 !important;
                color: #ffffff !important;
            }}
            QComboBox QListView::item:selected {{
                background-color: {pal['accent']} !important;
                color: {pal['tab_text']} !important;
                font-weight: bold;
            }}
            /* Keep native confirmation and information dialogs legible even
               when the desktop platform supplies a light dialog surface. */
            QMessageBox, QInputDialog {{
                background-color: #111720 !important;
                color: #eef4fb !important;
                border: 1px solid #405064;
            }}
            QMessageBox QLabel, QInputDialog QLabel {{
                background: transparent !important;
                color: #eef4fb !important;
                font-size: 12px;
                min-width: 220px;
            }}
            QMessageBox QPushButton, QInputDialog QPushButton {{
                min-width: 76px;
                padding: 6px 12px;
                background: #243244 !important;
                color: #f2f6fb !important;
                border: 1px solid #52677f;
                border-radius: 6px;
            }}
            QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {{
                background: #31465c !important;
                border-color: {pal['accent']} !important;
            }}
            QInputDialog QLineEdit {{
                background: #080c12 !important;
                color: #ffffff !important;
                border: 1px solid #52677f;
                padding: 5px;
            }}
            QMenu {{
                background-color: #14171d !important;
                border: 2px solid {pal['accent']} !important;
                border-radius: 6px;
                color: #ffffff !important;
                padding: 6px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 11px;
            }}
            QMenu::item {{
                background: transparent;
                padding: 6px 24px;
                color: #ffffff !important;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {pal['accent']} !important;
                color: {pal['tab_text']} !important;
                font-weight: bold;
            }}
            QMenu::separator {{
                height: 1px;
                background: #283240;
                margin: 4px 6px;
            }}
            QPushButton:focus, QSlider:focus {{
                outline: 2px solid {pal['accent']};
                outline-offset: 1px;
            }}
            QToolTip {{
                background: #171b22;
                color: #f4f6fa;
                border: 1px solid {pal['accent']};
                padding: 5px 8px;
            }}
        """)

        # Sync lyrics theme and accent color
        self.page_lyrics.set_theme(theme_key, pal)
        if hasattr(self, "mini_player"):
            self.mini_player.set_theme(pal["accent"])
        spectrum_mode = {
            "walkman": "amber", "glass": "winamp", "ipod": "silver",
            "vinyl": "amber", "studio_rack": "cyan"
        }.get(theme_key, "winamp")
        self.top_spectrum.set_theme_mode(spectrum_mode)
        if hasattr(self.page_library, "set_theme"):
            self.page_library.set_theme(theme_key, pal)
        if hasattr(self.page_eq, "set_theme"):
            self.page_eq.set_theme(theme_key, pal)
        if hasattr(self.page_settings, "set_theme"):
            self.page_settings.set_theme(theme_key, pal)
        self.update()
        if self.centralWidget():
            self.centralWidget().update()
        self._persist_state()

    def _persist_state(self):
        state = {
            "playlist": self._playlist,
            "current_index": self._current_index,
            "volume": self._audio.get_volume(),
            "theme": self._active_theme,
            "repeat_mode": self._repeat_mode,
            "is_shuffled": self._is_shuffled,
            "active_tab": self.pages_stack.currentIndex(),
            "library_font_size": getattr(self.page_library, "_font_size", 13),
            "glass_transparency": self._glass_transparency,
            "glass_frosting": self._glass_frosting,
            "animations_enabled": self._animations_enabled,
        }
        StateManager.save_state(state)

    # ---------------------------------------------------------
    # NON-BLOCKING ASYNC FOLDER LOADER WITH SCAN HUD
    # ---------------------------------------------------------
    def _open_folder_dialog(self):
        d = QFileDialog.getExistingDirectory(self, "Open Music Folder", os.path.expanduser("~/Music"))
        if d:
            self._start_async_folder_loader([d], clear_first=True)

    def _open_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio Files", os.path.expanduser("~/Music"),
            "Audio Files (*.mp3 *.flac *.wav *.ogg *.m4a *.aac *.opus *.wma)"
        )
        if files:
            self._start_async_folder_loader(files, clear_first=False)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self._start_async_folder_loader(paths, clear_first=False)

    def _add_paths(self, paths, clear_first=False):
        self._start_async_folder_loader(paths, clear_first=clear_first)

    def _start_async_folder_loader(self, paths, clear_first=False):
        hud = LoadingScanDialog("INGESTING AUDIO DIRECTORY", parent=self)

        self.loader_thread = FolderLoaderWorker(paths, parent=self)
        self.loader_thread.progress.connect(hud.set_progress)

        def on_finished(items):
            hud.accept()
            if clear_first:
                self._playlist.clear()
                self._current_index = -1

            self._playlist.extend(items)
            self.page_library.set_playlist(self._playlist)
            self._refresh_collection_pages()
            self._persist_state()

            if self._current_index == -1 and self._playlist:
                self.load_track(0, auto_start=True)

        def on_error(err):
            hud.reject()
            QMessageBox.warning(self, "Load Error", f"Could not load folder: {err}")

        self.loader_thread.finished.connect(on_finished)
        self.loader_thread.error.connect(on_error)
        self.loader_thread.start()
        hud.exec_()

    def load_track(self, index, auto_start=False):
        if not (0 <= index < len(self._playlist)):
            return

        self._current_index = index
        if self._active_play_order and index in self._active_play_order:
            self._order_pos = self._active_play_order.index(index)
        meta = self._playlist[index]

        # 1. Fast Load Audio (gapless READY transition without pipeline teardown)
        dur = meta.get("duration", 0.0)
        self._audio.load(meta["path"], known_duration=dur, auto_start=auto_start)

        # 2. Update Hardware Player Deck (active skin only, pre-scaled artwork cache)
        self.page_deck.set_track_info(meta)
        self.mini_player.set_track_info(meta.get("title"), meta.get("artist"), meta.get("artwork_path"), meta.get("album"))

        # 3. Load Synced Lyrics (lazy if tab is hidden)
        self.page_lyrics.load_track(meta)

        # 4. Broadcast to MPRIS D-Bus (GNOME Shell, Lock Screen, Media Keys)
        art_path = meta.get("artwork_path")
        self._mpris.update_track(meta.get("title"), meta.get("artist"), meta.get("album"), art_path, dur)

        # 5. Native Desktop Notification
        self._notifications.notify_track(meta.get("title"), meta.get("artist"), meta.get("album"), art_path)

        # 6. Update Library Play-Count & Selected Cover Card (only if visible)
        try:
            from backend.playlist_manager import PlaylistManager
            PlaylistManager.increment_play_count(meta["path"])
            if hasattr(self.page_library, "isVisible") and self.page_library.isVisible():
                if hasattr(self.page_library, "_on_row_selected"):
                    self.page_library._on_row_selected(index)
        except Exception:
            pass

        # Debounced background state save instead of freezing UI thread
        self._deferred_state_save_timer.start()
        self._update_up_next_display()

        # Warm up cover art cache for the upcoming song in memory
        self._preload_upcoming_track()

    def _preload_upcoming_track(self):
        nxt_idx = self._get_upcoming_track_index()
        if nxt_idx is not None and 0 <= nxt_idx < len(self._playlist):
            nxt_meta = self._playlist[nxt_idx]
            art_p = nxt_meta.get("artwork_path")
            if art_p and os.path.exists(art_p):
                from ui.widgets.hero_cover_art import _COVER_CACHE
                for sz in (58, 202, 212, 252):
                    key = (art_p, sz, sz)
                    if key not in _COVER_CACHE:
                        try:
                            from PyQt5.QtGui import QPixmap
                            raw = QPixmap(art_p)
                            if not raw.isNull():
                                from PyQt5.QtCore import Qt
                                scaled = raw.scaled(sz, sz, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                                cx = max(0, (scaled.width() - sz) // 2)
                                cy = max(0, (scaled.height() - sz) // 2)
                                _COVER_CACHE[key] = scaled.copy(cx, cy, sz, sz)
                        except Exception:
                            pass

    def _on_play_pause_clicked(self):
        if self._current_index == -1 and self._playlist:
            self.load_track(0, auto_start=True)
        else:
            self._audio.toggle_play_pause()

    def play_next(self):
        if not self._playlist:
            return

        # 1. User priority queue takes precedence (Spotify / YT Music queue logic)
        if self._user_queue:
            nxt = self._user_queue.pop(0)
            if nxt in self._active_play_order:
                self._order_pos = self._active_play_order.index(nxt)
            self.load_track(nxt, auto_start=True)
            return

        # 2. Sequence playback along active filtered/sorted list (e.g. FLAC -> next FLAC)
        if self._active_play_order:
            if self._is_shuffled:
                self._order_pos = random.randint(0, len(self._active_play_order) - 1)
                nxt = self._active_play_order[self._order_pos]
            else:
                self._order_pos += 1
                if self._order_pos >= len(self._active_play_order):
                    if self._repeat_mode in ["ALL", "ONE"]:
                        self._order_pos = 0
                        nxt = self._active_play_order[0]
                    else:
                        self._audio.stop()
                        self._update_up_next_display()
                        return
                else:
                    nxt = self._active_play_order[self._order_pos]
            self.load_track(nxt, auto_start=True)
            return

        # 3. Fallback standard playlist sequence
        if self._is_shuffled:
            nxt = random.randint(0, len(self._playlist) - 1)
        else:
            nxt = self._current_index + 1
            if nxt >= len(self._playlist):
                if self._repeat_mode in ["ALL", "ONE"]:
                    nxt = 0
                else:
                    self._audio.stop()
                    self._update_up_next_display()
                    return
        self.load_track(nxt, auto_start=True)

    def play_previous(self):
        if not self._playlist:
            return

        if self._active_play_order:
            if self._is_shuffled:
                self._order_pos = random.randint(0, len(self._active_play_order) - 1)
            else:
                self._order_pos = (self._order_pos - 1) % len(self._active_play_order)
            nxt = self._active_play_order[self._order_pos]
            self.load_track(nxt, auto_start=True)
            return

        if self._is_shuffled:
            nxt = random.randint(0, len(self._playlist) - 1)
        else:
            nxt = self._current_index - 1
            if nxt < 0:
                nxt = len(self._playlist) - 1
        self.load_track(nxt, auto_start=True)

    def _on_play_context_requested(self, visible_seq, pos, real_idx, context_name=None):
        self._active_play_order = list(visible_seq)
        self._order_pos = pos
        if context_name:
            self._active_context_name = str(context_name)
        elif hasattr(self, 'page_library') and hasattr(self.page_library, 'combo_audio_type'):
            fmt = self.page_library.combo_audio_type.currentData()
            if fmt and fmt not in ("ALL", "SORT_RESET", None):
                self._active_context_name = f"Library ({fmt})"
            else:
                self._active_context_name = "Library"
        else:
            self._active_context_name = "Library"
        self.load_track(real_idx, auto_start=True)
        self._update_up_next_display()

    def _on_play_next_requested(self, real_idx):
        if real_idx in self._user_queue:
            self._user_queue.remove(real_idx)
        self._user_queue.insert(0, real_idx)
        self._update_up_next_display()
        if 0 <= real_idx < len(self._playlist):
            t = self._playlist[real_idx].get("title", "Track")
            self.statusBar().showMessage(f"Playing Next: {t}", 3000)

    def _on_add_to_queue_requested(self, real_idx):
        if real_idx not in self._user_queue:
            self._user_queue.append(real_idx)
        self._update_up_next_display()
        if 0 <= real_idx < len(self._playlist):
            t = self._playlist[real_idx].get("title", "Track")
            self.statusBar().showMessage(f"Added to Queue: {t}", 3000)

    def _open_queue_drawer(self):
        from ui.dialogs.queue_drawer import QueueDrawerDialog
        dlg = QueueDrawerDialog(self, parent=self)
        dlg.exec_()

    def get_now_playing_track(self):
        if 0 <= self._current_index < len(self._playlist):
            return self._playlist[self._current_index]
        return None

    def get_upcoming_sequence_indices(self, limit=25):
        if not self._active_play_order and not self._playlist:
            return []
        seq = self._active_play_order if self._active_play_order else list(range(len(self._playlist)))
        curr_pos = self._order_pos if self._active_play_order else self._current_index
        upcoming = []
        n = len(seq)
        for i in range(1, min(limit + 1, n)):
            idx_pos = curr_pos + i
            if idx_pos < n:
                upcoming.append(seq[idx_pos])
            elif self._repeat_mode in ["ALL", "ONE"]:
                upcoming.append(seq[idx_pos % n])
        return upcoming

    def play_track_from_user_queue(self, real_idx, queue_pos):
        if 0 <= queue_pos < len(self._user_queue):
            self._user_queue.pop(queue_pos)
        self.load_track(real_idx, auto_start=True)
        self._update_up_next_display()

    def move_user_queue(self, from_pos, to_pos):
        if 0 <= from_pos < len(self._user_queue) and 0 <= to_pos < len(self._user_queue):
            item = self._user_queue.pop(from_pos)
            self._user_queue.insert(to_pos, item)
            self._update_up_next_display()

    def remove_from_user_queue(self, pos):
        if 0 <= pos < len(self._user_queue):
            self._user_queue.pop(pos)
            self._update_up_next_display()

    def clear_user_queue(self):
        self._user_queue.clear()
        self._update_up_next_display()

    def play_track_now(self, real_idx):
        if real_idx in self._active_play_order:
            self._order_pos = self._active_play_order.index(real_idx)
        self.load_track(real_idx, auto_start=True)
        self._update_up_next_display()

    def queue_track_next(self, real_idx):
        if real_idx in self._user_queue:
            self._user_queue.remove(real_idx)
        self._user_queue.insert(0, real_idx)
        self._update_up_next_display()

    def _get_upcoming_track_index(self):
        if self._user_queue:
            return self._user_queue[0]
        if self._active_play_order:
            if self._order_pos + 1 < len(self._active_play_order):
                return self._active_play_order[self._order_pos + 1]
            elif self._repeat_mode in ["ALL", "ONE"] and len(self._active_play_order) > 0:
                return self._active_play_order[0]
        elif self._playlist:
            nxt = self._current_index + 1
            if nxt < len(self._playlist):
                return nxt
            elif self._repeat_mode in ["ALL", "ONE"]:
                return 0
        return None

    def _update_up_next_display(self):
        nxt_idx = self._get_upcoming_track_index()
        if nxt_idx is not None and 0 <= nxt_idx < len(self._playlist):
            meta = self._playlist[nxt_idx]
            t = meta.get("title", "Unknown")
            a = meta.get("artist", "")
            self.page_deck.set_up_next_info(t, a)
        else:
            self.page_deck.set_up_next_info("Queue Empty", "")

    def _toggle_shuffle(self):
        self._is_shuffled = not self._is_shuffled
        self._update_top_transport_styles()
        self._persist_state()

    def _cycle_repeat(self):
        modes = ["ALL", "ONE", "OFF"]
        try:
            curr_idx = modes.index(self._repeat_mode)
            self._repeat_mode = modes[(curr_idx + 1) % len(modes)]
        except ValueError:
            self._repeat_mode = "ALL"
        self._update_top_transport_styles()
        self._persist_state()

    def _update_top_transport_styles(self):
        """Synchronize the always-visible transport strip and live spectrum."""
        if hasattr(self, "mini_player"):
            is_playing = self._audio.is_playing() if hasattr(self, "_audio") else False
            self.mini_player.set_playing_state(is_playing)
            self.mini_player.set_modes(self._repeat_mode, self._is_shuffled)
        if hasattr(self, "top_spectrum"):
            self.top_spectrum.set_playing(self._audio.is_playing() if hasattr(self, "_audio") else False)

    def _on_track_finished(self):
        if self._repeat_mode == "ONE":
            self._audio.seek(0)
            self._audio.play()
        else:
            self.play_next()

    def _on_position_changed(self, pos_sec, dur_sec):
        self.page_deck.update_position(pos_sec, dur_sec)
        self.page_lyrics.update_position(pos_sec, dur_sec)
        self.mini_player.update_position(pos_sec, dur_sec)
        self._mpris.update_position(pos_sec)

    def _on_seek_moved(self, val):
        dur = self._audio.get_duration()
        if dur > 0:
            target = (val / 1000.0) * dur
            self._audio.seek(target)

    def _on_volume_changed(self, val):
        self._audio.set_volume(val)
        if hasattr(self, "mini_player"):
            self.mini_player.slider_vol.blockSignals(True)
            self.mini_player.slider_vol.setValue(int(val * 100))
            self.mini_player.slider_vol.blockSignals(False)
        self._mpris.update_volume(val)
        self._persist_state()

    def _on_state_changed(self, state):
        is_playing = (state == "PLAYING")
        self.page_deck.set_playing_state(is_playing)
        self.page_library.detail_spectrum.set_playing(is_playing)
        self._mpris.update_playback_status(state)
        self._update_top_transport_styles()

    def _on_audio_level(self, l_val, r_val):
        self.page_deck.update_levels(l_val, r_val)
        self.page_lyrics.update_levels(l_val, r_val)
        self.page_eq.update_levels(l_val, r_val)
        self.page_library.detail_spectrum.set_levels(l_val, r_val)
        self.top_spectrum.set_levels(l_val, r_val)

    def _on_customize_current(self):
        if 0 <= self._current_index < len(self._playlist):
            self._open_editor_for_row(self._current_index)

    def _open_editor_for_row(self, row):
        meta = self._playlist[row]
        dlg = MetadataEditorDialog(meta["path"], meta, parent=self)
        dlg.metadata_saved.connect(lambda updated: self._on_metadata_updated(row, updated))
        dlg.exec_()

    def _on_metadata_updated(self, row, updated):
        if not (0 <= row < len(self._playlist)):
            return
        self._playlist[row].update(updated)
        if hasattr(self.page_library, "update_row_meta"):
            self.page_library.update_row_meta(row, updated)
        else:
            self.page_library.refresh_table()

        if row == self._current_index:
            self.page_deck.set_track_info(updated)
            self.mini_player.set_track_info(updated.get("title"), updated.get("artist"), updated.get("artwork_path"), updated.get("album"))
            self.page_lyrics.load_track(updated)
            if hasattr(self, "_mpris") and self._mpris:
                try:
                    self._mpris.update_track(
                        updated.get("title"), updated.get("artist"), updated.get("album"),
                        updated.get("artwork_path"), updated.get("duration", 0.0)
                    )
                except Exception:
                    pass
        self._refresh_collection_pages()
        self._persist_state()

    def _fetch_row_online(self, row):
        if not (0 <= row < len(self._playlist)):
            return
        meta = self._playlist[row]
        worker = MetadataFetchWorker(meta["path"], meta, parent=None)
        self._bg_workers.append(worker)
        worker.finished.connect(lambda: self._bg_workers.remove(worker) if worker in self._bg_workers else None)
        worker.fetched.connect(lambda updated: self._on_metadata_updated(row, updated))
        worker.start()

    def _remove_track(self, row):
        if 0 <= row < len(self._playlist):
            del self._playlist[row]
            self.page_library.set_playlist(self._playlist)
            self._refresh_collection_pages()
            self._persist_state()

    def _open_organizer_dialog(self):
        cur_dir = None
        if self._playlist and self._current_index >= 0:
            cur_dir = os.path.dirname(self._playlist[self._current_index]["path"])
        if not cur_dir or not os.path.exists(cur_dir):
            cur_dir = os.path.expanduser("~/Music")
        tgt_dir = os.path.join(cur_dir, "Virtual_Library")
        hud = LibraryScannerHUD(source_dir=cur_dir, target_dir=tgt_dir, parent=self)
        hud.library_organized.connect(lambda target_dir: self._start_async_folder_loader([target_dir], clear_first=True))
        hud.exec_()

    def _open_batch_enrich_dialog(self):
        dlg = BatchEnrichDialog(self._playlist, self, parent=self)
        dlg.batch_finished.connect(lambda: (self.page_library._rebuild_category_tree(), self.page_library.refresh_table(), self._persist_state()))
        dlg.exec_()

    def _open_duplicate_resolver(self):
        dlg = DuplicateResolverDialog(self._playlist, parent=self)
        dlg.duplicates_purged.connect(self._on_duplicates_purged)
        dlg.exec_()

    def _on_duplicates_purged(self, indexes_to_remove):
        if not indexes_to_remove:
            return
        current_track_path = None
        if 0 <= self._current_index < len(self._playlist):
            current_track_path = self._playlist[self._current_index].get("path")

        remove_set = set(indexes_to_remove)
        self._playlist = [track for i, track in enumerate(self._playlist) if i not in remove_set]

        # Keep current playing track position valid
        if current_track_path:
            matching = [i for i, t in enumerate(self._playlist) if t.get("path") == current_track_path]
            self._current_index = matching[0] if matching else (0 if self._playlist else -1)
        else:
            self._current_index = min(max(0, self._current_index), len(self._playlist) - 1) if self._playlist else -1

        self._user_queue = [i for i in self._user_queue if i not in remove_set]
        self._active_play_order = list(range(len(self._playlist)))
        self._order_pos = self._current_index if self._current_index >= 0 else 0
        self._active_context_name = "All Tracks"

        self.page_library.set_playlist(self._playlist)
        self._refresh_collection_pages()
        self._persist_state()
        self._update_up_next_display()
        QMessageBox.information(self, "Duplicates Purged", f"Removed {len(indexes_to_remove)} redundant track(s).")

    def closeEvent(self, event):
        # Wait for any active background workers to safely stop
        for w in list(self._bg_workers):
            if hasattr(w, "isRunning") and w.isRunning():
                w.wait(500)

        if hasattr(self, "page_lyrics") and hasattr(self.page_lyrics, "stop_worker"):
            self.page_lyrics.stop_worker()

        # Background playback support: if music is playing, minimize to tray
        if self._audio.is_playing() and hasattr(self, 'tray') and self.tray.isVisible():
            self.hide()
            self.tray.showMessage(
                "Retro Walkman Pro",
                "Playing in background. Click tray icon to restore.",
                QSystemTrayIcon.Information, 2000
            )
            event.ignore()
        else:
            self._persist_state()
            event.accept()
