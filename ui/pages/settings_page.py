import os
import shutil
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QCheckBox, QSlider, QScrollArea,
    QFileDialog, QMessageBox, QGridLayout, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPalette, QColor
from backend.metadata_manager import ART_CACHE_DIR
from backend.lyrics_manager import LYRICS_CACHE_DIR
from backend.audio_engine import EQ_PRESETS, AudioEngine
from backend.playlist_manager import PlaylistManager


THEME_OPTIONS = [
    ("Classic Walkman Cassette", "walkman", "Retro 80s Sony Walkman style with motorized tape spools and 7-segment display"),
    ("Liquid Glass Hi-Fi Deck", "glass", "Liquid smoked glass, dynamic edge refraction, and clean hi-res audio display"),
    ("iPod Classic Click Wheel", "ipod", "Vertical portrait handheld DAP with iconic circular Click Wheel and 30-Pin Hi-Fi Dock wings"),
    ("Vinyl LP Turntable Deck", "vinyl", "Direct-drive 33 RPM spinning vinyl record with micro-grooves, tonearm, and phono preamp"),
    ("Hi-Fi Studio Rack (Dual Analog VU)", "studio_rack", "19-inch studio faceplate with glowing rotary volume dial and twin analog needle VU meters")
]


class SettingsPage(QWidget):
    theme_changed = pyqtSignal(str)
    led_color_changed = pyqtSignal(str)
    cover_mode_changed = pyqtSignal(str)
    audio_output_changed = pyqtSignal(str, str, int)  # driver, device, buffer_ms
    dsp_preset_changed = pyqtSignal(str)
    mega_bass_toggled = pyqtSignal(bool)
    dolby_nr_toggled = pyqtSignal(bool)
    phono_toggled = pyqtSignal(bool)
    vocal_boost_toggled = pyqtSignal(bool)
    pitch_changed = pyqtSignal(float)
    preamp_changed = pyqtSignal(float)
    panning_changed = pyqtSignal(float)
    lyrics_autoscroll_toggled = pyqtSignal(bool)
    lyrics_glow_toggled = pyqtSignal(bool)
    lyrics_font_size_changed = pyqtSignal(int)
    lyrics_offset_changed = pyqtSignal(float)
    mpris_toggled = pyqtSignal(bool)
    notifications_toggled = pyqtSignal(bool)
    tray_toggled = pyqtSignal(bool)
    organize_pointers_requested = pyqtSignal()
    add_folder_requested = pyqtSignal()
    batch_enrich_requested = pyqtSignal()
    detect_duplicates_requested = pyqtSignal()
    library_font_size_changed = pyqtSignal(int)
    library_row_height_changed = pyqtSignal(int)
    playlists_updated = pyqtSignal()
    glass_transparency_changed = pyqtSignal(int)
    glass_frosting_changed = pyqtSignal(int)
    animations_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._accent = "#00f0ff"
        self._bg_card = "#12151a"
        self._border_card = "#222730"
        self._text_color = "#e2e8f0"
        self._sub_text = "#8c96a5"
        self._cards = []
        self._header_labels = []

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Top Page Header
        top_bar = QHBoxLayout()
        self.lbl_main_title = QLabel("SYSTEM CONFIGURATION & AUDIOPHILE SETTINGS")
        self.lbl_main_title.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        top_bar.addWidget(self.lbl_main_title)
        top_bar.addStretch()

        btn_defaults = QPushButton("RESTORE DEFAULTS")
        btn_defaults.setStyleSheet("""
            QPushButton {
                background: #1a1e24;
                border: 1px solid #363e4c;
                border-radius: 4px;
                padding: 4px 12px;
                color: #a0aec0;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background: #28303c; color: #ffffff; }
        """)
        btn_defaults.clicked.connect(self._reset_defaults)
        top_bar.addWidget(btn_defaults)
        root.addLayout(top_bar)

        # Scrollable Configuration Workspace
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #0d1014;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #252d38;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3b4656;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(4, 4, 12, 20)
        c_layout.setSpacing(14)

        # =============================================================
        # 1. AUDIO PIPELINE & HARDWARE OUTPUT SINK
        # =============================================================
        card_audio = self._create_card("AUDIO PIPELINE & HARDWARE OUTPUT SINK")
        ca_layout = QGridLayout(card_audio)
        ca_layout.setContentsMargins(16, 14, 16, 14)
        ca_layout.setHorizontalSpacing(14)
        ca_layout.setVerticalSpacing(10)

        # Output Device Sink (scanned via pactl)
        ca_layout.addWidget(QLabel("AUDIO OUTPUT DEVICE SINK:"), 0, 0)
        self.combo_device = QComboBox()
        self._populate_audio_sinks()
        self.combo_device.currentIndexChanged.connect(self._emit_audio_output)
        ca_layout.addWidget(self.combo_device, 0, 1)

        # Audio Driver / Pipeline Backend
        ca_layout.addWidget(QLabel("AUDIO DRIVER PIPELINE:"), 1, 0)
        self.combo_driver = QComboBox()
        self.combo_driver.addItem("PulseAudio Pipeline (pulsesink — Recommended)", "pulsesink")
        self.combo_driver.addItem("Direct ALSA Hardware (alsasink)", "alsasink")
        self.combo_driver.addItem("GStreamer Auto-Detect (autoaudiosink)", "autoaudiosink")
        self.combo_driver.currentIndexChanged.connect(self._emit_audio_output)
        ca_layout.addWidget(self.combo_driver, 1, 1)

        # Latency / Buffer
        ca_layout.addWidget(QLabel("BUFFER TIME / LATENCY:"), 2, 0)
        self.combo_buffer = QComboBox()
        self.combo_buffer.addItem("Ultra-Low Latency (25ms — Pro Audio)", 25)
        self.combo_buffer.addItem("Studio & Gaming (50ms)", 50)
        self.combo_buffer.addItem("Hi-Fi Standard Buffer (100ms)", 100)
        self.combo_buffer.addItem("Audiophile Smooth Buffer (250ms)", 250)
        self.combo_buffer.setCurrentIndex(2)
        self.combo_buffer.currentIndexChanged.connect(self._emit_audio_output)
        ca_layout.addWidget(self.combo_buffer, 2, 1)

        # Hardware Test Chime
        btn_test_audio = QPushButton("Play Test Chime")
        btn_test_audio.setFixedWidth(160)
        btn_test_audio.clicked.connect(self._play_test_chime)
        ca_layout.addWidget(btn_test_audio, 3, 1)

        c_layout.addWidget(card_audio)

        # =============================================================
        # 2. BANG & OLUFSEN (HP VICTUS) & HARDWARE DSP MASTER SOUND
        # =============================================================
        card_dsp = self._create_card("BANG & OLUFSEN (HP VICTUS) & HARDWARE DSP")
        cd_layout = QGridLayout(card_dsp)
        cd_layout.setContentsMargins(16, 14, 16, 14)
        cd_layout.setHorizontalSpacing(14)
        cd_layout.setVerticalSpacing(10)

        cd_layout.addWidget(QLabel("MASTER DSP SOUND PROFILE:"), 0, 0)
        self.combo_dsp_preset = QComboBox()
        for p in EQ_PRESETS.keys():
            self.combo_dsp_preset.addItem(p)
        self.combo_dsp_preset.setCurrentText("B&O Signature (HP Victus)")
        self.combo_dsp_preset.currentTextChanged.connect(self.dsp_preset_changed.emit)
        cd_layout.addWidget(self.combo_dsp_preset, 0, 1)

        # Toggles Row
        toggles_layout = QHBoxLayout()
        self.chk_mega_bass = QCheckBox("Mega Bass (+9dB)")
        self.chk_mega_bass.toggled.connect(self.mega_bass_toggled.emit)
        toggles_layout.addWidget(self.chk_mega_bass)

        self.chk_dolby = QCheckBox("Dolby B/C Tape NR")
        self.chk_dolby.toggled.connect(self.dolby_nr_toggled.emit)
        toggles_layout.addWidget(self.chk_dolby)

        self.chk_phono = QCheckBox("Phono Preamp (RIAA)")
        self.chk_phono.toggled.connect(self.phono_toggled.emit)
        toggles_layout.addWidget(self.chk_phono)

        self.chk_vocal = QCheckBox("Vocal Boost Filter")
        self.chk_vocal.toggled.connect(self.vocal_boost_toggled.emit)
        toggles_layout.addWidget(self.chk_vocal)
        cd_layout.addLayout(toggles_layout, 1, 0, 1, 2)

        # Preamp Master Gain
        cd_layout.addWidget(QLabel("PREAMP MASTER GAIN:"), 2, 0)
        p_row = QHBoxLayout()
        self.slider_preamp = QSlider(Qt.Horizontal)
        self.slider_preamp.setRange(-12, 12)
        self.slider_preamp.setValue(0)
        self.lbl_preamp_val = QLabel("0.0 dB")
        self.lbl_preamp_val.setFixedWidth(50)
        self.slider_preamp.valueChanged.connect(self._on_preamp_slider)
        p_row.addWidget(self.slider_preamp)
        p_row.addWidget(self.lbl_preamp_val)
        cd_layout.addLayout(p_row, 2, 1)

        # Stereo Panning
        cd_layout.addWidget(QLabel("STEREO PANNING BALANCE:"), 3, 0)
        pan_row = QHBoxLayout()
        self.slider_pan = QSlider(Qt.Horizontal)
        self.slider_pan.setRange(-100, 100)
        self.slider_pan.setValue(0)
        self.lbl_pan_val = QLabel("CENTER")
        self.lbl_pan_val.setFixedWidth(50)
        self.slider_pan.valueChanged.connect(self._on_pan_slider)
        pan_row.addWidget(self.slider_pan)
        pan_row.addWidget(self.lbl_pan_val)
        cd_layout.addLayout(pan_row, 3, 1)

        # Playback Pitch / Varispeed
        cd_layout.addWidget(QLabel("TAPE / VINYL VARISPEED (PITCH):"), 4, 0)
        pitch_row = QHBoxLayout()
        self.slider_pitch = QSlider(Qt.Horizontal)
        self.slider_pitch.setRange(80, 120)
        self.slider_pitch.setValue(100)
        self.lbl_pitch_val = QLabel("1.00x")
        self.lbl_pitch_val.setFixedWidth(50)
        self.slider_pitch.valueChanged.connect(self._on_pitch_slider)
        btn_reset_pitch = QPushButton("1.0x")
        btn_reset_pitch.setFixedWidth(40)
        btn_reset_pitch.clicked.connect(lambda: self.slider_pitch.setValue(100))
        pitch_row.addWidget(self.slider_pitch)
        pitch_row.addWidget(self.lbl_pitch_val)
        pitch_row.addWidget(btn_reset_pitch)
        cd_layout.addLayout(pitch_row, 4, 1)

        c_layout.addWidget(card_dsp)

        # =============================================================
        # 3. HARDWARE DECK THEMES & SKEUOMORPHIC VISUALS
        # =============================================================
        card_theme = self._create_card("HARDWARE DECK THEMES & SKEUOMORPHIC VISUALS")
        ct_layout = QGridLayout(card_theme)
        ct_layout.setContentsMargins(16, 14, 16, 14)
        ct_layout.setHorizontalSpacing(14)
        ct_layout.setVerticalSpacing(10)

        ct_layout.addWidget(QLabel("ACTIVE HARDWARE THEME:"), 0, 0)
        self.combo_theme = QComboBox()
        for title, key, _ in THEME_OPTIONS:
            self.combo_theme.addItem(title, key)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_selected)
        ct_layout.addWidget(self.combo_theme, 0, 1)

        self.lbl_theme_desc = QLabel(THEME_OPTIONS[0][2])
        self.lbl_theme_desc.setStyleSheet("color: #00f0ff; font-size: 11px; font-style: italic;")
        ct_layout.addWidget(self.lbl_theme_desc, 1, 0, 1, 2)

        ct_layout.addWidget(QLabel("VFD / 7-SEGMENT ACCENT COLOR:"), 2, 0)
        self.combo_led = QComboBox()
        self.combo_led.addItem("Walkman Amber (Warm Glow)", "amber")
        self.combo_led.addItem("Cyan VFD (Fluorescent Hi-Fi)", "cyan")
        self.combo_led.addItem("Vintage Emerald (LCD Watch)", "green")
        self.combo_led.addItem("Studio Red (Rackmount)", "red")
        self.combo_led.addItem("Champagne Gold (Audiophile DAP)", "gold")
        self.combo_led.currentIndexChanged.connect(lambda: self.led_color_changed.emit(self.combo_led.currentData()))
        ct_layout.addWidget(self.combo_led, 2, 1)

        ct_layout.addWidget(QLabel("ALBUM ART DISPLAY STYLE:"), 3, 0)
        self.combo_art = QComboBox()
        self.combo_art.addItem("Recessed Jewel Case Window (Walkman & Studio)", "badge")
        self.combo_art.addItem("Full High-Res Artwork Card (Modern DAP)", "full")
        self.combo_art.addItem("Spinning Vinyl Record (Vinyl Groove)", "vinyl")
        self.combo_art.currentIndexChanged.connect(lambda: self.cover_mode_changed.emit(self.combo_art.currentData()))
        ct_layout.addWidget(self.combo_art, 3, 1)

        # Visual checkboxes
        vis_row = QHBoxLayout()
        self.chk_specular = QCheckBox("Acrylic Specular Glass Glare")
        self.chk_specular.setChecked(True)
        vis_row.addWidget(self.chk_specular)

        self.chk_peak_caps = QCheckBox("Spectrum Falling Peak Caps")
        self.chk_peak_caps.setChecked(True)
        vis_row.addWidget(self.chk_peak_caps)
        ct_layout.addLayout(vis_row, 4, 0, 1, 2)

        ct_layout.addWidget(QLabel("GLASS TRANSPARENCY (100% = CLEAR):"), 5, 0)
        glass_row = QHBoxLayout()
        self.slider_glass_transparency = QSlider(Qt.Horizontal)
        self.slider_glass_transparency.setRange(0, 100)
        self.slider_glass_transparency.setValue(30)
        self.slider_glass_transparency.setToolTip("0% is opaque; 100% makes the glass surfaces fully transparent")
        self.lbl_glass_transparency = QLabel("30%")
        self.lbl_glass_transparency.setFixedWidth(48)
        self.slider_glass_transparency.valueChanged.connect(self._on_glass_transparency_changed)
        glass_row.addWidget(self.slider_glass_transparency, 1)
        glass_row.addWidget(self.lbl_glass_transparency)
        ct_layout.addLayout(glass_row, 5, 1)

        ct_layout.addWidget(QLabel("GLASS FROSTING EFFECT:"), 6, 0)
        frost_row = QHBoxLayout()
        self.slider_glass_frost = QSlider(Qt.Horizontal)
        self.slider_glass_frost.setRange(0, 100)
        self.slider_glass_frost.setValue(40)
        self.slider_glass_frost.setToolTip("Adjust sandblasted frosted matte scattering (0% = clear glass, 100% = dense frost)")
        self.lbl_glass_frost = QLabel("40%")
        self.lbl_glass_frost.setFixedWidth(48)
        self.slider_glass_frost.valueChanged.connect(self._on_glass_frost_changed)
        frost_row.addWidget(self.slider_glass_frost, 1)
        frost_row.addWidget(self.lbl_glass_frost)
        ct_layout.addLayout(frost_row, 6, 1)

        self.chk_theme_animations = QCheckBox("Hardware animations during playback")
        self.chk_theme_animations.setChecked(True)
        self.chk_theme_animations.setToolTip("Animate the cassette, record, level meters, spectra, and theme light sweep")
        self.chk_theme_animations.toggled.connect(self.animations_toggled.emit)
        ct_layout.addWidget(self.chk_theme_animations, 7, 0, 1, 2)

        # A live visual preview makes this setting understandable even while a
        # non-glass hardware theme (for example Walkman) is selected.
        self.glass_preview = QFrame()
        self.glass_preview.setObjectName("glassPreviewBackdrop")
        self.glass_preview.setMinimumHeight(54)
        self.glass_preview.setStyleSheet(
            "QFrame#glassPreviewBackdrop { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #33383d, stop:0.38 #9b8778, stop:0.65 #6c747b, stop:1 #c3c4c2); "
            "border: 1px solid #45596d; border-radius: 8px; }"
        )
        preview_layout = QHBoxLayout(self.glass_preview)
        preview_layout.setContentsMargins(10, 8, 10, 8)
        self.glass_preview_panel = QLabel("GLASS · LIVE PREVIEW")
        self.glass_preview_panel.setAlignment(Qt.AlignCenter)
        self.glass_preview_panel.setMinimumHeight(34)
        self.glass_preview_panel.setStyleSheet(
            "background: rgba(52, 59, 65, 178); color: #f4fbff; "
            "border: 1px solid rgba(255, 255, 255, 150); border-radius: 6px; "
            "font-weight: 700; letter-spacing: 1px;"
        )
        preview_layout.addWidget(self.glass_preview_panel)
        ct_layout.addWidget(QLabel("LIVE GLASS PREVIEW:"), 8, 0)
        ct_layout.addWidget(self.glass_preview, 8, 1)

        c_layout.addWidget(card_theme)

        # =============================================================
        # 4. LYRICS & KARAOKE TELEPROMPTER ENGINE
        # =============================================================
        card_lyrics = self._create_card("LYRICS & KARAOKE TELEPROMPTER ENGINE")
        cl_layout = QGridLayout(card_lyrics)
        cl_layout.setContentsMargins(16, 14, 16, 14)
        cl_layout.setHorizontalSpacing(14)
        cl_layout.setVerticalSpacing(10)

        chk_lyrics_row = QHBoxLayout()
        self.chk_autoscroll = QCheckBox("Auto-Scroll to Active Lyric Row")
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.toggled.connect(self.lyrics_autoscroll_toggled.emit)
        chk_lyrics_row.addWidget(self.chk_autoscroll)

        self.chk_glow = QCheckBox("Karaoke Phosphor Neon Bloom Glow")
        self.chk_glow.setChecked(True)
        self.chk_glow.toggled.connect(self.lyrics_glow_toggled.emit)
        chk_lyrics_row.addWidget(self.chk_glow)

        self.chk_auto_lrc = QCheckBox("Auto-Fetch Missing Lyrics via LrcLib")
        self.chk_auto_lrc.setChecked(True)
        chk_lyrics_row.addWidget(self.chk_auto_lrc)
        cl_layout.addLayout(chk_lyrics_row, 0, 0, 1, 2)

        # Base Font Size
        cl_layout.addWidget(QLabel("BASE TYPOGRAPHIC FONT SIZE:"), 1, 0)
        font_row = QHBoxLayout()
        self.slider_font = QSlider(Qt.Horizontal)
        self.slider_font.setRange(11, 28)
        self.slider_font.setValue(15)
        self.lbl_font_val = QLabel("15 px (Active: 22 px)")
        self.lbl_font_val.setFixedWidth(130)
        self.slider_font.valueChanged.connect(self._on_font_slider)
        font_row.addWidget(self.slider_font)
        font_row.addWidget(self.lbl_font_val)
        cl_layout.addLayout(font_row, 1, 1)

        # Default Sync Offset
        cl_layout.addWidget(QLabel("DEFAULT SYNC CALIBRATION OFFSET:"), 2, 0)
        offset_row = QHBoxLayout()
        self.slider_offset = QSlider(Qt.Horizontal)
        self.slider_offset.setRange(-20, 20)
        self.slider_offset.setValue(0)
        self.lbl_offset_val = QLabel("0.0 s")
        self.lbl_offset_val.setFixedWidth(50)
        self.slider_offset.valueChanged.connect(self._on_offset_slider)
        btn_reset_offset = QPushButton("Reset")
        btn_reset_offset.setFixedWidth(50)
        btn_reset_offset.clicked.connect(lambda: self.slider_offset.setValue(0))
        offset_row.addWidget(self.slider_offset)
        offset_row.addWidget(self.lbl_offset_val)
        offset_row.addWidget(btn_reset_offset)
        cl_layout.addLayout(offset_row, 2, 1)

        c_layout.addWidget(card_lyrics)

        # =============================================================
        # 5. LIBRARY & ZERO-COPY ORGANIZER
        # =============================================================
        card_lib = self._create_card("LIBRARY & ZERO-COPY ORGANIZER")
        clib_layout = QGridLayout(card_lib)
        clib_layout.setContentsMargins(16, 14, 16, 14)
        clib_layout.setHorizontalSpacing(14)
        clib_layout.setVerticalSpacing(10)

        clib_layout.addWidget(QLabel("ZERO-COPY POINTER DIRECTORY:"), 0, 0)
        ptr_row = QHBoxLayout()
        default_ptr = os.path.expanduser("~/Music/Virtual_Library")
        self.lbl_ptr_path = QLabel(default_ptr)
        self.lbl_ptr_path.setStyleSheet("color: #39ff14; font-family: Monospace; font-size: 11px;")
        btn_organize_now = QPushButton("Organize Now")
        btn_organize_now.clicked.connect(self.organize_pointers_requested.emit)
        ptr_row.addWidget(self.lbl_ptr_path)
        ptr_row.addStretch()
        ptr_row.addWidget(btn_organize_now)
        clib_layout.addLayout(ptr_row, 0, 1)

        # Batch tools
        clib_layout.addWidget(QLabel("QUICK BATCH OPERATIONS:"), 1, 0)
        ops_row = QHBoxLayout()
        btn_enrich_all = QPushButton("Auto-Tag & Covers (All Songs)")
        btn_enrich_all.clicked.connect(self.batch_enrich_requested.emit)
        btn_audit_dups = QPushButton("Audit Duplicates")
        btn_audit_dups.clicked.connect(self.detect_duplicates_requested.emit)
        ops_row.addWidget(btn_enrich_all)
        ops_row.addWidget(btn_audit_dups)
        ops_row.addStretch()
        clib_layout.addLayout(ops_row, 1, 1)

        # Storage & Cache Management
        clib_layout.addWidget(QLabel("STORAGE CACHE DIRECTORIES:"), 2, 0)
        cache_row = QHBoxLayout()
        btn_open_art = QPushButton("Artwork Cache")
        btn_open_art.clicked.connect(lambda: subprocess.run(["xdg-open", ART_CACHE_DIR]))
        btn_open_lrc = QPushButton("Lyrics Cache")
        btn_open_lrc.clicked.connect(lambda: subprocess.run(["xdg-open", LYRICS_CACHE_DIR]))
        btn_clear_art = QPushButton("Purge Artwork")
        btn_clear_art.clicked.connect(self._clear_art_cache)
        btn_clear_lrc = QPushButton("Purge Lyrics")
        btn_clear_lrc.clicked.connect(self._clear_lyrics_cache)

        cache_row.addWidget(btn_open_art)
        cache_row.addWidget(btn_open_lrc)
        cache_row.addWidget(btn_clear_art)
        cache_row.addWidget(btn_clear_lrc)
        cache_row.addStretch()
        clib_layout.addLayout(cache_row, 2, 1)

        c_layout.addWidget(card_lib)

        # =============================================================
        # 6. MUSIC LIBRARY & UI TYPOGRAPHY SCALE (CUSTOMIZABLE UI)
        # =============================================================
        card_scale = self._create_card("MUSIC LIBRARY & UI TYPOGRAPHY SCALE")
        cscale_layout = QGridLayout(card_scale)
        cscale_layout.setContentsMargins(16, 14, 16, 14)
        cscale_layout.setHorizontalSpacing(14)
        cscale_layout.setVerticalSpacing(10)

        # Library Table Font Size
        cscale_layout.addWidget(QLabel("LIBRARY TABLE FONT SIZE:"), 0, 0)
        lib_font_row = QHBoxLayout()
        self.slider_lib_font = QSlider(Qt.Horizontal)
        self.slider_lib_font.setRange(10, 24)
        self.slider_lib_font.setValue(13)
        self.lbl_lib_font_val = QLabel("13 px")
        self.lbl_lib_font_val.setFixedWidth(60)
        self.slider_lib_font.valueChanged.connect(self._on_lib_font_slider)
        btn_reset_lib_font = QPushButton("Reset")
        btn_reset_lib_font.setFixedWidth(50)
        btn_reset_lib_font.clicked.connect(lambda: self.slider_lib_font.setValue(13))
        lib_font_row.addWidget(self.slider_lib_font)
        lib_font_row.addWidget(self.lbl_lib_font_val)
        lib_font_row.addWidget(btn_reset_lib_font)
        cscale_layout.addLayout(lib_font_row, 0, 1)

        # Library Row Height
        cscale_layout.addWidget(QLabel("LIBRARY TABLE ROW HEIGHT:"), 1, 0)
        row_h_layout = QHBoxLayout()
        self.slider_lib_row_h = QSlider(Qt.Horizontal)
        self.slider_lib_row_h.setRange(24, 54)
        self.slider_lib_row_h.setValue(34)
        self.lbl_lib_row_h_val = QLabel("34 px")
        self.lbl_lib_row_h_val.setFixedWidth(60)
        self.slider_lib_row_h.valueChanged.connect(self._on_lib_row_h_slider)
        btn_reset_row_h = QPushButton("Reset")
        btn_reset_row_h.setFixedWidth(50)
        btn_reset_row_h.clicked.connect(lambda: self.slider_lib_row_h.setValue(34))
        row_h_layout.addWidget(self.slider_lib_row_h)
        row_h_layout.addWidget(self.lbl_lib_row_h_val)
        row_h_layout.addWidget(btn_reset_row_h)
        cscale_layout.addLayout(row_h_layout, 1, 1)

        # UI Toggles
        scale_chk_row = QHBoxLayout()
        self.chk_show_cover_bay = QCheckBox("Show Hero Album Cover & Details Bay in Music Library")
        self.chk_show_cover_bay.setChecked(True)
        scale_chk_row.addWidget(self.chk_show_cover_bay)
        cscale_layout.addLayout(scale_chk_row, 2, 0, 1, 2)

        c_layout.addWidget(card_scale)

        # =============================================================
        # 7. CUSTOM PLAYLISTS & FAVORITES MANAGEMENT
        # =============================================================
        card_playlists = self._create_card("PLAYLISTS & FAVORITES MANAGEMENT")
        cpl_layout = QGridLayout(card_playlists)
        cpl_layout.setContentsMargins(16, 14, 16, 14)
        cpl_layout.setHorizontalSpacing(14)
        cpl_layout.setVerticalSpacing(10)

        cpl_layout.addWidget(QLabel("MANAGE CUSTOM PLAYLISTS:"), 0, 0)
        pl_ops_row = QHBoxLayout()
        self.combo_manage_playlists = QComboBox()
        self._populate_playlists_combo()
        btn_new_pl = QPushButton("Create New")
        btn_new_pl.clicked.connect(self._create_playlist_dialog)
        btn_del_pl = QPushButton("Delete Selected")
        btn_del_pl.clicked.connect(self._delete_playlist_dialog)
        btn_clear_liked = QPushButton("Clear Liked Songs")
        btn_clear_liked.clicked.connect(self._clear_liked_dialog)

        pl_ops_row.addWidget(self.combo_manage_playlists, 2)
        pl_ops_row.addWidget(btn_new_pl)
        pl_ops_row.addWidget(btn_del_pl)
        pl_ops_row.addWidget(btn_clear_liked)
        cpl_layout.addLayout(pl_ops_row, 0, 1)

        c_layout.addWidget(card_playlists)

        # =============================================================
        # 8. LINUX DESKTOP & SYSTEM INTEGRATION
        # =============================================================
        card_sys = self._create_card("LINUX DESKTOP & SYSTEM INTEGRATION")
        csys_layout = QVBoxLayout(card_sys)
        csys_layout.setContentsMargins(16, 14, 16, 14)
        csys_layout.setSpacing(10)

        self.chk_mpris = QCheckBox("Enable MPRIS2 D-Bus Interface (Lock Screen, Notification Shade & Media Keys)")
        self.chk_mpris.setChecked(True)
        self.chk_mpris.toggled.connect(self.mpris_toggled.emit)
        csys_layout.addWidget(self.chk_mpris)

        self.chk_notify = QCheckBox("Show Native Desktop Notifications (notify-send) on Song Change with Album Art")
        self.chk_notify.setChecked(True)
        self.chk_notify.toggled.connect(self.notifications_toggled.emit)
        csys_layout.addWidget(self.chk_notify)

        self.chk_tray = QCheckBox("Minimize to System Tray on Window Close (Continue Background Playback)")
        self.chk_tray.setChecked(True)
        self.chk_tray.toggled.connect(self.tray_toggled.emit)
        csys_layout.addWidget(self.chk_tray)

        self.chk_autoplay_next = QCheckBox("Auto-play Next Track in Folder / Playlist upon Completion (Continuous Playback)")
        self.chk_autoplay_next.setChecked(True)
        csys_layout.addWidget(self.chk_autoplay_next)

        c_layout.addWidget(card_sys)
        c_layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

    def _create_card(self, title_text):
        card = QFrame()
        card.setObjectName("settingsCard")
        self._cards.append(card)

        # Title banner inside card
        header = QLabel(title_text)
        header.setObjectName("cardHeader")
        self._header_labels.append(header)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        header_frame = QFrame()
        header_frame.setObjectName("cardHeaderFrame")
        hf_layout = QHBoxLayout(header_frame)
        hf_layout.setContentsMargins(14, 6, 14, 6)
        hf_layout.addWidget(header)
        card_layout.addWidget(header_frame)

        content_frame = QFrame()
        content_frame.setObjectName("cardContentFrame")
        card_layout.addWidget(content_frame, 1)

        return content_frame

    def _populate_audio_sinks(self):
        self.combo_device.blockSignals(True)
        self.combo_device.clear()
        sinks = AudioEngine.get_available_sinks()
        for sink_id, desc in sinks:
            self.combo_device.addItem(desc, sink_id)
        self.combo_device.blockSignals(False)

    def _emit_audio_output(self):
        driver = self.combo_driver.currentData()
        device = self.combo_device.currentData() or "default"
        buffer_ms = self.combo_buffer.currentData() or 100
        self.audio_output_changed.emit(driver, device, buffer_ms)

    def _play_test_chime(self):
        # Play a soft system chime or test tone using aplay/paplay/gst
        try:
            subprocess.Popen(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"], stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _on_preamp_slider(self, val):
        self.lbl_preamp_val.setText(f"{val:+.1f} dB")
        self.preamp_changed.emit(float(val))

    def _on_pan_slider(self, val):
        if val == 0:
            txt = "CENTER"
        elif val < 0:
            txt = f"L {abs(val)}%"
        else:
            txt = f"R {val}%"
        self.lbl_pan_val.setText(txt)
        self.panning_changed.emit(val / 100.0)

    def _on_pitch_slider(self, val):
        rate = val / 100.0
        self.lbl_pitch_val.setText(f"{rate:.2f}x")
        self.pitch_changed.emit(rate)

    def _on_font_slider(self, val):
        self.lbl_font_val.setText(f"{val} px (Active: {val + 7} px)")
        self.lyrics_font_size_changed.emit(val)

    def _on_offset_slider(self, val):
        sec = val / 10.0
        self.lbl_offset_val.setText(f"{sec:+.1f} s")
        self.lyrics_offset_changed.emit(sec)

    def _on_theme_selected(self, idx):
        key = self.combo_theme.currentData()
        self.lbl_theme_desc.setText(THEME_OPTIONS[idx][2])
        self.theme_changed.emit(key)

    def _on_glass_transparency_changed(self, value):
        self.lbl_glass_transparency.setText(f"{value}%")
        self._update_glass_preview()
        self.glass_transparency_changed.emit(value)

    def _on_glass_frost_changed(self, value):
        self.lbl_glass_frost.setText(f"{value}%")
        self._update_glass_preview()
        self.glass_frosting_changed.emit(value)

    def _update_glass_preview(self):
        trans_val = max(0, min(100, int(self.slider_glass_transparency.value())))
        frost_val = max(0, min(100, int(self.slider_glass_frost.value())))
        alpha = round(255 * (100 - trans_val) / 100)
        # Frosted effect in CSS: lighten the tinted backdrop and strengthen rim
        r = int(52 + 35 * (frost_val / 100.0))
        g = int(59 + 45 * (frost_val / 100.0))
        b = int(65 + 60 * (frost_val / 100.0))
        border_alpha = min(255, int(140 + 100 * (frost_val / 100.0)))
        self.glass_preview_panel.setStyleSheet(
            f"background: rgba({r}, {g}, {b}, {alpha}); color: #f4fbff; "
            f"border: 1px solid rgba(255, 255, 255, {border_alpha}); border-radius: 6px; "
            "font-weight: 700; letter-spacing: 1px;"
        )

    def set_glass_transparency(self, value):
        self.slider_glass_transparency.blockSignals(True)
        self.slider_glass_transparency.setValue(max(0, min(100, int(value))))
        self.lbl_glass_transparency.setText(f"{self.slider_glass_transparency.value()}%")
        self._update_glass_preview()
        self.slider_glass_transparency.blockSignals(False)

    def set_glass_frosting(self, value):
        self.slider_glass_frost.blockSignals(True)
        self.slider_glass_frost.setValue(max(0, min(100, int(value))))
        self.lbl_glass_frost.setText(f"{self.slider_glass_frost.value()}%")
        self._update_glass_preview()
        self.slider_glass_frost.blockSignals(False)

    def set_animations_enabled(self, enabled):
        self.chk_theme_animations.blockSignals(True)
        self.chk_theme_animations.setChecked(bool(enabled))
        self.chk_theme_animations.blockSignals(False)

    def _clear_art_cache(self):
        if os.path.exists(ART_CACHE_DIR):
            shutil.rmtree(ART_CACHE_DIR, ignore_errors=True)
            os.makedirs(ART_CACHE_DIR, exist_ok=True)
            QMessageBox.information(self, "Cache Cleared", "High-resolution artwork cache has been cleared.")

    def _clear_lyrics_cache(self):
        if os.path.exists(LYRICS_CACHE_DIR):
            shutil.rmtree(LYRICS_CACHE_DIR, ignore_errors=True)
            os.makedirs(LYRICS_CACHE_DIR, exist_ok=True)
            QMessageBox.information(self, "Cache Cleared", "Synchronized lyrics (.LRC) cache has been cleared.")

    def _reset_defaults(self):
        self.combo_driver.setCurrentIndex(0)
        self.combo_buffer.setCurrentIndex(2)
        self.combo_dsp_preset.setCurrentText("B&O Signature (HP Victus)")
        self.chk_mega_bass.setChecked(False)
        self.chk_dolby.setChecked(False)
        self.chk_phono.setChecked(False)
        self.chk_vocal.setChecked(False)
        self.slider_preamp.setValue(0)
        self.slider_pan.setValue(0)
        self.slider_pitch.setValue(100)
        self.slider_font.setValue(15)
        self.slider_offset.setValue(0)
        self.chk_autoscroll.setChecked(True)
        self.chk_glow.setChecked(True)
        self.chk_mpris.setChecked(True)
        self.chk_notify.setChecked(True)
        self.chk_tray.setChecked(True)
        QMessageBox.information(self, "Settings Reset", "All hardware and audio settings have been restored to defaults.")

    def _on_lib_font_slider(self, val):
        self.lbl_lib_font_val.setText(f"{val} px")
        self.slider_lib_row_h.setValue(max(24, int(val * 2.4)))
        self.library_font_size_changed.emit(val)

    def _on_lib_row_h_slider(self, val):
        self.lbl_lib_row_h_val.setText(f"{val} px")
        self.library_row_height_changed.emit(val)

    def set_library_font_size(self, val):
        self.slider_lib_font.blockSignals(True)
        self.slider_lib_font.setValue(val)
        self.lbl_lib_font_val.setText(f"{val} px")
        self.slider_lib_font.blockSignals(False)
        self.slider_lib_row_h.setValue(max(24, int(val * 2.4)))

    def _populate_playlists_combo(self):
        self.combo_manage_playlists.clear()
        pls = PlaylistManager.get_all_playlists()
        for name in sorted(pls.keys()):
            cnt = len(pls[name])
            self.combo_manage_playlists.addItem(f"{name} ({cnt} tracks)", name)

    def _create_playlist_dialog(self):
        name, ok = QInputDialog.getText(self, "Create Custom Playlist", "Enter playlist name:")
        if ok and name.strip():
            created = PlaylistManager.create_playlist(name.strip())
            if created:
                self._populate_playlists_combo()
                self.playlists_updated.emit()
                QMessageBox.information(self, "Playlist Created", f"Created playlist '{name.strip()}'.")
            else:
                QMessageBox.warning(self, "Notice", f"Playlist '{name.strip()}' already exists.")

    def _delete_playlist_dialog(self):
        name = self.combo_manage_playlists.currentData()
        if not name:
            return
        res = QMessageBox.question(self, "Delete Playlist", f"Are you sure you want to delete playlist '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            PlaylistManager.delete_playlist(name)
            self._populate_playlists_combo()
            self.playlists_updated.emit()

    def _clear_liked_dialog(self):
        res = QMessageBox.question(self, "Clear Liked Songs", "Remove all tracks from your Liked Favorites list?", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            PlaylistManager._load()["liked"].clear()
            PlaylistManager._save()
            self.playlists_updated.emit()
            QMessageBox.information(self, "Favorites Cleared", "Liked Songs list has been emptied.")

    def set_theme(self, theme_key, pal):
        """
        Dynamically themes the entire Settings Console to perfectly match
        the active hardware player chassis (Walkman, DAP Gold, iPod, Vinyl, Studio Rack)
        with 100% visible high-contrast menus, combobox dropdowns, and items.
        """
        accent = pal.get("accent", "#00f0ff")
        bg_card = pal.get("top_bezel", "#16191f")
        text_primary = pal.get("text_primary", "#ffffff")
        text_sec = pal.get("text_secondary", "#a0aec0")
        selected_text = pal.get("tab_text", "#ffffff")

        selected_index = self.combo_theme.findData(theme_key)
        if selected_index >= 0:
            self.combo_theme.blockSignals(True)
            self.combo_theme.setCurrentIndex(selected_index)
            self.combo_theme.blockSignals(False)
            self.lbl_theme_desc.setText(THEME_OPTIONS[selected_index][2])

        self.lbl_main_title.setStyleSheet(f"color: {accent}; font-family: Monospace; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        self.lbl_theme_desc.setStyleSheet(f"color: {accent}; font-size: 11px; font-style: italic;")

        # Card & Container Styling
        card_qss = f"""
            QFrame#settingsCard {{
                background: {bg_card};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 8px;
            }}
            QFrame#cardHeaderFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.05), stop:1 rgba(0, 0, 0, 0.25));
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom: 1px solid rgba(0, 0, 0, 0.4);
            }}
            QLabel#cardHeader {{
                color: {accent};
                font-family: Monospace;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 0.8px;
            }}
            QLabel {{
                color: {text_primary};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 11px;
                font-weight: 500;
            }}
            QComboBox {{
                background: #14171d !important;
                border: 1px solid {accent} !important;
                border-radius: 5px;
                padding: 6px 12px;
                color: #ffffff !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 11px;
                font-weight: bold;
            }}
            QComboBox:focus {{
                border: 2px solid {accent} !important;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid #2d3644;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {accent};
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #12151b !important;
                border: 2px solid {accent} !important;
                border-radius: 6px;
                padding: 4px;
                color: #ffffff !important;
                selection-background-color: {accent} !important;
                selection-color: {selected_text} !important;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                background-color: #12151b !important;
                color: #ffffff !important;
                min-height: 28px;
                padding: 6px 10px;
                border-radius: 3px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #1e293b !important;
                color: {accent} !important;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {accent} !important;
                color: {selected_text} !important;
                font-weight: bold;
            }}
            QMenu {{
                background-color: #14171d !important;
                border: 2px solid {accent} !important;
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
                background-color: {accent} !important;
                color: {selected_text} !important;
                font-weight: bold;
            }}
            QMenu::separator {{
                height: 1px;
                background: #283240;
                margin: 4px 6px;
            }}
            QCheckBox {{
                color: {text_primary};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 11px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                background: #0d1014;
                border: 1px solid #3d495a;
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background: {accent};
                border: 1px solid {accent};
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #252c38, stop:0.5 #1a202a, stop:1 #12161e);
                border: 1px solid #3d4a5c;
                border-top: 1px solid #5a6b82;
                border-radius: 4px;
                padding: 5px 12px;
                color: #e2e8f0;
                font-family: Monospace;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #2e3746;
                color: #ffffff;
                border: 1px solid {accent};
            }}
            QSlider::groove:horizontal {{
                height: 5px;
                background: #0a0d10;
                border: 1px solid #222a36;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e2e8f0, stop:1 #94a3b8);
                border: 1px solid #000000;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 3px;
            }}
        """
        self.setStyleSheet(card_qss)

        # A combo popup is a separate view on some desktop styles. Setting
        # only the parent QSS can leave that native popup with a white system
        # palette, so apply the active theme directly to every popup view too.
        popup_bg = QColor("#171d26")
        popup_text = QColor(text_primary)
        popup_selected = QColor(accent)
        popup_selected_text = QColor(selected_text)
        for combo in self.findChildren(QComboBox):
            palette = combo.palette()
            palette.setColor(QPalette.Base, popup_bg)
            palette.setColor(QPalette.Window, popup_bg)
            palette.setColor(QPalette.Text, popup_text)
            palette.setColor(QPalette.WindowText, popup_text)
            palette.setColor(QPalette.Highlight, popup_selected)
            palette.setColor(QPalette.HighlightedText, popup_selected_text)
            combo.setPalette(palette)

            popup = combo.view()
            popup.setPalette(palette)
            popup.setStyleSheet(f"""
                QListView {{
                    background-color: #171d26;
                    color: {text_primary};
                    border: 1px solid {accent};
                    outline: none;
                    padding: 4px;
                }}
                QListView::item {{
                    background-color: #171d26;
                    color: {text_primary};
                    min-height: 30px;
                    padding: 5px 9px;
                    border-radius: 3px;
                }}
                QListView::item:hover {{
                    background-color: #273342;
                    color: #ffffff;
                }}
                QListView::item:selected {{
                    background-color: {accent};
                    color: {selected_text};
                    font-weight: 700;
                }}
                QScrollBar:vertical {{
                    width: 9px;
                    background: #11161e;
                    margin: 2px;
                }}
                QScrollBar::handle:vertical {{
                    background: #536174;
                    border-radius: 4px;
                    min-height: 24px;
                }}
            """)
