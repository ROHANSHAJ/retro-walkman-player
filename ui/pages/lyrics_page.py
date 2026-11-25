import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QFrame, QFileDialog, QMessageBox, QGridLayout,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF, QSize
from PyQt5.QtGui import QFont, QColor, QPainter, QLinearGradient, QPen

from backend.lyrics_manager import LyricsManager, LyricsFetchWorker
from ui.widgets.hero_cover_art import HeroCoverArtWindow
from ui.widgets.spectrum_analyzer import WinampSpectrumAnalyzer
from ui.widgets.vu_meter import StereoVUMeter
from ui.widgets.vintage_controls import VintageButton, RetroSlider, LabeledKnob
from ui.dialogs.manual_lyrics_dialog import ManualLyricsSelectorDialog


class LyricsLineWidget(QLabel):
    clicked = pyqtSignal(float)  # timestamp in seconds

    def __init__(self, timestamp, text, parent=None):
        super().__init__(text or "...", parent)
        self.timestamp = timestamp
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setCursor(Qt.PointingHandCursor)
        self._font_size = 18
        self._lyrics_selector = None
        self._is_active = False
        self._accent_color = "#00f0ff"
        self._karaoke_glow = True
        self.apply_style()

    def set_font_size(self, size_pt):
        self._font_size = max(11, min(32, int(size_pt)))
        self.apply_style()

    def set_karaoke_glow(self, enable_glow):
        self._karaoke_glow = bool(enable_glow)
        self.apply_style()

    def set_active(self, is_active, accent_color=None):
        self._is_active = bool(is_active)
        if accent_color:
            self._accent_color = accent_color
        self.apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.timestamp)
        super().mousePressEvent(event)

    def sizeHint(self):
        fm = self.fontMetrics()
        parent_w = 420
        if self.parentWidget() and self.parentWidget().width() > 100:
            parent_w = max(240, self.parentWidget().width() - 40)
        elif self.width() > 80:
            parent_w = self.width()

        rect = fm.boundingRect(0, 0, parent_w, 4000, Qt.AlignCenter | Qt.TextWordWrap, self.text())
        pad_v = 28 if self._is_active else 12
        pad_h = 32 if self._is_active else 20
        return QSize(min(parent_w, rect.width() + pad_h), rect.height() + pad_v)

    def minimumSizeHint(self):
        return self.sizeHint()

    def apply_style(self):
        font_family = "DejaVu Sans"
        if self._is_active:
            # Active Playing Line: Dramatically POPS OUT with bold pure white text,
            # larger scale (+7px), and radiant phosphor text bloom (ZERO boxes/borders)
            active_size = self._font_size + 7
            f = QFont(font_family, active_size, QFont.Bold)
            f.setStyleHint(QFont.SansSerif)
            self.setFont(f)
            self.setStyleSheet(f"""
                QLabel {{
                    color: #ffffff;
                    font-size: {active_size}px;
                    font-weight: 800;
                    letter-spacing: 0.5px;
                    background: transparent;
                    border: none;
                    padding: 8px 16px;
                }}
            """)
            if self._karaoke_glow:
                glow = QGraphicsDropShadowEffect(self)
                glow.setBlurRadius(24)
                glow.setColor(QColor(self._accent_color))
                glow.setOffset(0, 0)
                self.setGraphicsEffect(glow)
            else:
                self.setGraphicsEffect(None)
        else:
            # Inactive Lines: Soft dimmed silver-gray typography in clean rows, zero boxes, zero borders
            self.setGraphicsEffect(None)
            f = QFont(font_family, self._font_size, QFont.Normal)
            f.setStyleHint(QFont.SansSerif)
            self.setFont(f)
            self.setStyleSheet(f"""
                QLabel {{
                    color: #64748b;
                    font-size: {self._font_size}px;
                    font-weight: 500;
                    background: transparent;
                    border: none;
                    padding: 4px 12px;
                }}
                QLabel:hover {{
                    color: #cbd5e1;
                    background: transparent;
                    border: none;
                }}
            """)

        self.updateGeometry()
        if self.parentWidget():
            self.parentWidget().updateGeometry()
            if self.parentWidget().layout():
                self.parentWidget().layout().activate()


class LyricsPage(QWidget):
    """
    Winamp & Hardware Studio inspired Hi-Fi Karaoke Station.
    Combines:
    - Left Column: Hero Cover Art (1:1), Track Codec Specs, Winamp Spectrum Analyzer, Stereo VU Meter
    - Center Column: Recessed Studio Teleprompter Visor, Smooth Auto-Scrolling Karaoke, Live Timing Calibration & Mini Scrubber
    - Right Column: Hardware DSP Rack with Multi-Knobs, Multi-Buttons with Status LEDs, and Peak Level Ladders
    """
    seek_requested = pyqtSignal(float)
    slider_seek_moved = pyqtSignal(int)
    art_clicked = pyqtSignal()
    play_pause_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lines = []  # list of (timestamp, text)
        self._line_widgets = []
        self._active_idx = -1
        self._current_track = {}
        self._accent_color = "#00f0ff"
        self._sync_offset = 0.0  # seconds offset (negative = lyrics earlier, positive = later)
        self._auto_scroll_enabled = True
        self._karaoke_glow_enabled = True
        self._vocal_enhance_enabled = False
        self._font_size = 15

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(8)

        # -------------------------------------------------------------
        # 1. TOP HARDWARE SUB-BEZEL (Title, Sync Badge & Quick Action Buttons)
        # -------------------------------------------------------------
        top_bar = QFrame()
        top_bar.setFixedHeight(34)
        top_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1e24, stop:1 #101317);
                border: 1px solid #2d333d;
                border-radius: 5px;
            }
        """)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 2, 10, 2)
        tb_layout.setSpacing(10)

        self.lbl_title = QLabel("HI-FI KARAOKE & TELEPROMPTER")
        self.lbl_title.setStyleSheet("color: #e2e8f0; font-family: Monospace; font-size: 11px; font-weight: bold; letter-spacing: 1px;")

        self.lbl_status = QLabel("NO TIMESTAMPS LOADED")
        self.lbl_status.setStyleSheet("color: #718096; font-family: Monospace; font-size: 10px; font-weight: bold;")

        tb_layout.addWidget(self.lbl_title)
        tb_layout.addWidget(self.lbl_status)
        tb_layout.addStretch()

        self.btn_fetch = QPushButton("Search Online Lyrics")
        self.btn_fetch.setStyleSheet("""
            QPushButton {
                background: #18222d;
                border: 1px solid #0088cc;
                border-radius: 4px;
                padding: 3px 10px;
                color: #00d0ff;
                font-family: Monospace;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover { background: #0088cc; color: #ffffff; }
        """)
        self.btn_fetch.clicked.connect(self._manual_fetch)

        self.btn_load_file = QPushButton("Open .LRC File")
        self.btn_load_file.setStyleSheet("""
            QPushButton {
                background: #1b2028;
                border: 1px solid #3d4654;
                border-radius: 4px;
                padding: 3px 10px;
                color: #b0bac8;
                font-family: Monospace;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover { background: #2d3644; color: #ffffff; }
        """)
        self.btn_load_file.clicked.connect(self._open_local_lrc_file)

        tb_layout.addWidget(self.btn_fetch)
        tb_layout.addWidget(self.btn_load_file)
        root.addWidget(top_bar)

        # -------------------------------------------------------------
        # 2. MAIN 3-COLUMN HI-FI CHASSIS (LEFT, CENTER, RIGHT)
        # -------------------------------------------------------------
        main_columns = QHBoxLayout()
        main_columns.setSpacing(10)

        # =============================================================
        # COLUMN 1: LEFT WING — MEDIA & WINAMP TELEMETRY DECK (~260px)
        # =============================================================
        col_left = QFrame()
        self._lyrics_left = col_left
        col_left.setFixedWidth(260)
        col_left.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16191f, stop:1 #0c0e12);
                border: 1px solid #282f3a;
                border-radius: 8px;
            }
        """)
        l_layout = QVBoxLayout(col_left)
        l_layout.setContentsMargins(10, 10, 10, 10)
        l_layout.setSpacing(8)

        # Section 1: Hero Cover Art Window (200x200 1:1 Recessed Bezel)
        self.cover_art = HeroCoverArtWindow(size=220)
        self.cover_art.clicked.connect(self.art_clicked.emit)
        l_layout.addWidget(self.cover_art, 0, Qt.AlignCenter)

        # Section 2: Winamp Codec Badges & Telemetry Box
        codec_box = QFrame()
        codec_box.setStyleSheet("""
            QFrame {
                background: #090b0e;
                border: 1px solid #1c222b;
                border-radius: 5px;
                padding: 4px;
            }
            QLabel {
                font-family: Monospace;
                font-size: 9px;
            }
        """)
        cb_layout = QGridLayout(codec_box)
        cb_layout.setContentsMargins(6, 4, 6, 4)
        cb_layout.setHorizontalSpacing(8)
        cb_layout.setVerticalSpacing(2)

        self.lbl_fmt = QLabel("FMT: MP3 AUDIO")
        self.lbl_fmt.setStyleSheet("color: #38bdf8; font-weight: bold;")
        self.lbl_rate = QLabel("RATE: 320 KBPS")
        self.lbl_rate.setStyleSheet("color: #38bdf8; font-weight: bold;")
        self.lbl_freq = QLabel("FREQ: 44.1 kHz")
        self.lbl_freq.setStyleSheet("color: #a3e635; font-weight: bold;")
        self.lbl_chan = QLabel("CH: STEREO")
        self.lbl_chan.setStyleSheet("color: #facc15; font-weight: bold;")

        cb_layout.addWidget(self.lbl_fmt, 0, 0)
        cb_layout.addWidget(self.lbl_rate, 0, 1)
        cb_layout.addWidget(self.lbl_freq, 1, 0)
        cb_layout.addWidget(self.lbl_chan, 1, 1)
        l_layout.addWidget(codec_box)

        # Section 3: Winamp 16-Band Spectrum Analyzer
        l_layout.addWidget(QLabel("WINAMP DSP SPECTRUM", styleSheet="color: #64748b; font-family: Monospace; font-size: 9px; font-weight: bold;"))
        self.spectrum = WinampSpectrumAnalyzer(bands_count=16, theme_mode="cyan")
        self.spectrum.setFixedHeight(68)
        l_layout.addWidget(self.spectrum)

        # Section 4: Dual Stereo Peak VU Meter
        l_layout.addWidget(QLabel("STEREO AUDIO LEVEL", styleSheet="color: #64748b; font-family: Monospace; font-size: 9px; font-weight: bold;"))
        self.vu_meter = StereoVUMeter()
        self.vu_meter.setFixedHeight(24)
        l_layout.addWidget(self.vu_meter)

        # Fill the lower media bay with readable Now Playing details.
        self.track_info_card = QFrame()
        self.track_info_card.setStyleSheet("QFrame { background: rgba(20, 27, 36, 210); border: 1px solid #2b3746; border-radius: 8px; }")
        info_layout = QVBoxLayout(self.track_info_card)
        info_layout.setContentsMargins(10, 9, 10, 9)
        info_layout.setSpacing(5)
        self.lbl_now_title = QLabel("No track selected")
        self.lbl_now_title.setWordWrap(True)
        self.lbl_now_title.setStyleSheet("color:#f2f6fb; font-size:15px; font-weight:700; background:transparent; border:0;")
        self.lbl_now_artist = QLabel("Choose a song to show lyrics")
        self.lbl_now_artist.setWordWrap(True)
        self.lbl_now_artist.setStyleSheet("color:#9eafc2; font-size:12px; background:transparent; border:0;")
        info_layout.addWidget(self.lbl_now_title)
        info_layout.addWidget(self.lbl_now_artist)
        l_layout.addWidget(self.track_info_card)

        l_layout.addStretch(1)
        main_columns.addWidget(col_left)

        # =============================================================
        # COLUMN 2: CENTER — RECESSED STUDIO TELEPROMPTER VISOR
        # =============================================================
        col_center = QFrame()
        col_center.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f1216, stop:0.5 #080a0c, stop:1 #050608);
                border: 2px solid #1f2630;
                border-radius: 8px;
            }
        """)
        c_layout = QVBoxLayout(col_center)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(6)

        # Teleprompter Calibration Sub-Bar
        calib_bar = QHBoxLayout()
        calib_bar.setContentsMargins(4, 0, 4, 0)
        calib_bar.setSpacing(6)

        self.lbl_sync_mode = QLabel("SYNC CALIBRATION:")
        self.lbl_sync_mode.setStyleSheet("color: #718096; font-family: Monospace; font-size: 9px; font-weight: bold;")
        calib_bar.addWidget(self.lbl_sync_mode)

        self.btn_sub_offset = QPushButton("-0.5s")
        self.btn_sub_offset.setFixedSize(50, 22)
        self.btn_sub_offset.setStyleSheet("background: #181d24; border: 1px solid #333d4b; border-radius: 3px; color: #a0aec0; font-family: Monospace; font-size: 9px; font-weight: bold;")
        self.btn_sub_offset.clicked.connect(lambda: self._adjust_offset(-0.5))

        self.lbl_offset_val = QLabel("OFFSET: +0.0s")
        self.lbl_offset_val.setStyleSheet("color: #38bdf8; font-family: Monospace; font-size: 9px; font-weight: bold;")

        self.btn_add_offset = QPushButton("+0.5s")
        self.btn_add_offset.setFixedSize(50, 22)
        self.btn_add_offset.setStyleSheet("background: #181d24; border: 1px solid #333d4b; border-radius: 3px; color: #a0aec0; font-family: Monospace; font-size: 9px; font-weight: bold;")
        self.btn_add_offset.clicked.connect(lambda: self._adjust_offset(+0.5))

        self.btn_reset_offset = QPushButton("RESET")
        self.btn_reset_offset.setFixedSize(48, 22)
        self.btn_reset_offset.setStyleSheet("background: #181d24; border: 1px solid #333d4b; border-radius: 3px; color: #718096; font-family: Monospace; font-size: 9px;")
        self.btn_reset_offset.clicked.connect(self._reset_offset)

        calib_bar.addWidget(self.btn_sub_offset)
        calib_bar.addWidget(self.lbl_offset_val)
        calib_bar.addWidget(self.btn_add_offset)
        calib_bar.addWidget(self.btn_reset_offset)
        calib_bar.addStretch()

        self.lbl_interactive_hint = QLabel("Click any line to seek instantly")
        self.lbl_interactive_hint.setStyleSheet("color: #4a5568; font-family: Monospace; font-size: 9px; font-style: italic;")
        calib_bar.addWidget(self.lbl_interactive_hint)

        c_layout.addLayout(calib_bar)

        # Main Scrolling Lyrics Container
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background: #080a0d;
                border: 1px solid #161c22;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                background: #0a0d10;
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

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent; border: none;")
        self.lines_layout = QVBoxLayout(self.content_widget)
        self.lines_layout.setAlignment(Qt.AlignCenter)
        self.lines_layout.setContentsMargins(16, 50, 16, 50)
        self.lines_layout.setSpacing(14)

        self.scroll.setWidget(self.content_widget)
        c_layout.addWidget(self.scroll, 1)

        # Bottom Mini Scrubber & Transport Strip
        scrub_strip = QHBoxLayout()
        scrub_strip.setSpacing(8)

        self.lbl_curr = QLabel("00:00")
        self.lbl_curr.setStyleSheet("color: #94a3b8; font-family: Monospace; font-size: 10px; font-weight: bold;")

        self.mini_slider = RetroSlider(Qt.Horizontal, glow_color=self._accent_color)
        self.mini_slider.setRange(0, 1000)
        self.mini_slider.sliderMoved.connect(self._on_slider_moved)

        self.lbl_total = QLabel("00:00")
        self.lbl_total.setStyleSheet("color: #64748b; font-family: Monospace; font-size: 10px; font-weight: bold;")

        scrub_strip.addWidget(self.lbl_curr)
        scrub_strip.addWidget(self.mini_slider, 1)
        scrub_strip.addWidget(self.lbl_total)
        c_layout.addLayout(scrub_strip)

        main_columns.addWidget(col_center, 1)

        # =============================================================
        # COLUMN 3: RIGHT WING — HARDWARE DSP & MULTI-CONTROL RACK (~250px)
        # =============================================================
        col_right = QFrame()
        self._lyrics_right = col_right
        col_right.setFixedWidth(250)
        col_right.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16191f, stop:1 #0c0e12);
                border: 1px solid #282f3a;
                border-radius: 8px;
            }
        """)
        r_layout = QVBoxLayout(col_right)
        r_layout.setContentsMargins(10, 10, 10, 10)
        r_layout.setSpacing(8)

        hdr_dsp = QLabel("HARDWARE DSP MATRIX")
        hdr_dsp.setAlignment(Qt.AlignCenter)
        hdr_dsp.setStyleSheet("color: #94a3b8; font-family: Monospace; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        r_layout.addWidget(hdr_dsp)

        # Section 1: Multi Knobs Grid (2x2 rotary dials)
        knobs_frame = QFrame()
        knobs_frame.setStyleSheet("background: #090b0e; border: 1px solid #1c222b; border-radius: 6px; padding: 4px;")
        kf_layout = QGridLayout(knobs_frame)
        kf_layout.setContentsMargins(4, 6, 4, 6)
        kf_layout.setSpacing(6)

        self.knob_vocal = LabeledKnob("VOCAL", style_mode="black", size=54)
        self.knob_vocal.set_value(0.7)

        self.knob_font = LabeledKnob("FONT SIZE", style_mode="black", size=54)
        self.knob_font.set_value(0.4)
        self.knob_font.valueChanged.connect(self._on_font_knob_changed)

        self.knob_ambience = LabeledKnob("AMBIENCE", style_mode="black", size=54)
        self.knob_ambience.set_value(0.3)

        self.knob_gain = LabeledKnob("MONITOR", style_mode="black", size=54)
        self.knob_gain.set_value(0.85)

        kf_layout.addWidget(self.knob_vocal, 0, 0)
        kf_layout.addWidget(self.knob_font, 0, 1)
        kf_layout.addWidget(self.knob_ambience, 1, 0)
        kf_layout.addWidget(self.knob_gain, 1, 1)
        r_layout.addWidget(knobs_frame)

        # Section 2: Multi Buttons with Status LEDs
        r_layout.addWidget(QLabel("KARAOKE TELEMETRY SWITCHES", styleSheet="color: #64748b; font-family: Monospace; font-size: 9px; font-weight: bold;"))

        # Button 1: Auto-Scroll Toggle with Green LED
        self.btn_autoscroll = VintageButton("AUTO-SCROLL", has_led=True)
        self.btn_autoscroll.set_led(True, "#39ff14")
        self.btn_autoscroll.clicked.connect(self._toggle_autoscroll)
        r_layout.addWidget(self.btn_autoscroll)

        # Button 2: Karaoke Neon Text Glow Toggle with Amber LED
        self.btn_glow = VintageButton("KARAOKE GLOW", has_led=True)
        self.btn_glow.set_led(True, "#ffaa00")
        self.btn_glow.clicked.connect(self._toggle_karaoke_glow)
        r_layout.addWidget(self.btn_glow)

        # Button 3: Vocal Enhance DSP Filter with Cyan LED
        self.btn_vocal_enhance = VintageButton("VOCAL ENHANCE", has_led=True)
        self.btn_vocal_enhance.set_led(False, "#00f0ff")
        self.btn_vocal_enhance.clicked.connect(self._toggle_vocal_enhance)
        r_layout.addWidget(self.btn_vocal_enhance)

        # Section 3: Ballistic Peak Meter & dB Scale
        peak_frame = QFrame()
        peak_frame.setStyleSheet("background: #090b0e; border: 1px solid #1c222b; border-radius: 5px; padding: 6px;")
        pf_layout = QHBoxLayout(peak_frame)
        pf_layout.setContentsMargins(6, 4, 6, 4)
        pf_layout.setSpacing(6)

        self.led_clip = QLabel("CLIP")
        self.led_clip.setStyleSheet("color: #4a1515; font-family: Monospace; font-size: 8px; font-weight: bold;")
        self.led_0db = QLabel("0dB")
        self.led_0db.setStyleSheet("color: #4a3510; font-family: Monospace; font-size: 8px; font-weight: bold;")
        self.led_6db = QLabel("-6dB")
        self.led_6db.setStyleSheet("color: #104515; font-family: Monospace; font-size: 8px; font-weight: bold;")
        self.led_12db = QLabel("-12dB")
        self.led_12db.setStyleSheet("color: #104515; font-family: Monospace; font-size: 8px; font-weight: bold;")

        pf_layout.addWidget(self.led_clip)
        pf_layout.addWidget(self.led_0db)
        pf_layout.addWidget(self.led_6db)
        pf_layout.addWidget(self.led_12db)
        r_layout.addWidget(peak_frame)

        r_layout.addStretch()
        self._lyrics_right_scroll = QScrollArea()
        self._lyrics_right_scroll.setWidgetResizable(True)
        self._lyrics_right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._lyrics_right_scroll.setFrameShape(QFrame.NoFrame)
        self._lyrics_right_scroll.setStyleSheet("QScrollArea { background:transparent; border:none; } QScrollBar:vertical { width:6px; background:#0d1116; } QScrollBar::handle:vertical { background:#394656; border-radius:3px; }")
        self._lyrics_right_scroll.setWidget(col_right)
        main_columns.addWidget(self._lyrics_right_scroll)

        root.addLayout(main_columns, 1)

        self._show_placeholder("No song loaded. Play a track to load synchronized lyrics.")

    def set_theme(self, theme_key, pal):
        accent = pal.get("accent", "#00f0ff")
        self._accent_color = accent

        # Spectrum analyzer theme mode
        if theme_key == "walkman":
            self.spectrum.set_theme_mode("amber")
            knob_mode = "black"
        elif theme_key == "glass":
            self.spectrum.set_theme_mode("cyan")
            knob_mode = "cyan"
        elif theme_key == "ipod":
            self.spectrum.set_theme_mode("silver")
            knob_mode = "silver"
        elif theme_key == "vinyl":
            self.spectrum.set_theme_mode("amber")
            knob_mode = "black"
        else: # studio_rack
            self.spectrum.set_theme_mode("cyan")
            knob_mode = "black"

        # Update knobs style mode
        self.knob_vocal.set_style_mode(knob_mode)
        self.knob_font.set_style_mode(knob_mode)
        self.knob_ambience.set_style_mode(knob_mode)
        self.knob_gain.set_style_mode(knob_mode)

        # Update mini slider glow
        self.mini_slider.set_glow_color(accent)

        # Update active lyric line
        if 0 <= self._active_idx < len(self._line_widgets):
            self._line_widgets[self._active_idx].set_active(True, self._accent_color)

    def set_accent_color(self, hex_color):
        self._accent_color = hex_color
        self.mini_slider.set_glow_color(hex_color)
        if 0 <= self._active_idx < len(self._line_widgets):
            self._line_widgets[self._active_idx].set_active(True, self._accent_color)

    def _show_placeholder(self, msg):
        self._clear_lines()
        lbl = QLabel(msg)
        lbl.setStyleSheet("color: #64748b; font-size: 13px; font-style: italic;")
        lbl.setAlignment(Qt.AlignCenter)
        self.lines_layout.addWidget(lbl)

    def _clear_lines(self):
        def _clear_layout(layout):
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
                    w.deleteLater()
                sub = item.layout()
                if sub:
                    _clear_layout(sub)
        _clear_layout(self.lines_layout)
        self._line_widgets.clear()
        self._active_idx = -1

    def load_track(self, meta_dict):
        self._current_track = dict(meta_dict)
        if not self.isVisible():
            self._lyrics_dirty = True
            return
        self._apply_current_track()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_lyrics_dirty", False) and getattr(self, "_current_track", None):
            self._lyrics_dirty = False
            self._apply_current_track()

    def _apply_current_track(self):
        if not self._current_track:
            return
        meta_dict = self._current_track
        artist = meta_dict.get("artist", "")
        title = meta_dict.get("title", "")
        album = meta_dict.get("album", "")
        art_path = meta_dict.get("artwork_path")

        # Update title & cover
        self.lbl_title.setText(f"{title} — {artist}".upper() if title else "HI-FI KARAOKE & TELEPROMPTER")
        self.cover_art.set_artwork(art_path)
        self.lbl_now_title.setText(title or meta_dict.get("filename") or "Unknown track")
        self.lbl_now_artist.setText(" • ".join(value for value in (artist, album) if value) or "Unknown artist")

        # Update codec badges
        ext = os.path.splitext(meta_dict.get("filename", ""))[1].replace(".", "").upper()
        self.lbl_fmt.setText(f"FMT: {ext or 'MP3'}")
        bitrate = meta_dict.get("bitrate", 320)
        self.lbl_rate.setText(f"RATE: {bitrate}k")

        # Fetch or load lyrics
        filepath = meta_dict.get("path", "")
        duration = meta_dict.get("duration", 0)

        lines, is_synced = LyricsManager.get_lyrics(filepath, artist, title, duration)
        if lines:
            self._populate_lyrics(lines, is_synced)
        else:
            self.lbl_status.setText("FETCHING ONLINE LYRICS...")
            self.lbl_status.setStyleSheet("color: #eab308; font-family: Monospace; font-size: 10px; font-weight: bold;")
            if hasattr(self, "_fetch_worker") and self._fetch_worker:
                try:
                    self._fetch_worker.lyrics_ready.disconnect()
                    self._fetch_worker.lyrics_failed.disconnect()
                except Exception:
                    pass
            self._fetch_worker = LyricsFetchWorker(filepath, artist, title, duration, parent=None)
            self._fetch_worker.lyrics_ready.connect(self._populate_lyrics)
            self._fetch_worker.lyrics_failed.connect(lambda err: self._show_placeholder(f"Lyrics unavailable: {err}"))
            self._fetch_worker.start()

    def stop_worker(self):
        if hasattr(self, "_fetch_worker") and self._fetch_worker and self._fetch_worker.isRunning():
            self._fetch_worker.wait(500)

    def _populate_lyrics(self, lines, is_synced):
        self._clear_lines()
        self._lines = lines

        if not lines:
            self._show_placeholder("No lyrics text available for this track.")
            self.lbl_status.setText("EMPTY")
            self.lbl_status.setStyleSheet("color: #718096; font-family: Monospace; font-size: 10px;")
            return

        if is_synced:
            self.lbl_status.setText("SYNCHRONIZED (LRC)")
            self.lbl_status.setStyleSheet("color: #22c55e; font-family: Monospace; font-size: 10px; font-weight: bold;")
        else:
            self.lbl_status.setText("STATIC TEXT (UNSYNCED)")
            self.lbl_status.setStyleSheet("color: #f59e0b; font-family: Monospace; font-size: 10px;")

        for ts, text in lines:
            lw = LyricsLineWidget(ts, text, parent=self.content_widget)
            lw.set_font_size(self._font_size)
            lw.set_karaoke_glow(self._karaoke_glow_enabled)
            lw.clicked.connect(self.seek_requested.emit)
            self.lines_layout.addWidget(lw)
            self._line_widgets.append(lw)

    def update_position(self, pos_sec, dur_sec=0):
        # Update mini slider & time labels
        if dur_sec > 0:
            val = int((pos_sec / float(dur_sec)) * 1000)
            self.mini_slider.blockSignals(True)
            self.mini_slider.setValue(val)
            self.mini_slider.blockSignals(False)
            self.lbl_curr.setText(f"{int(pos_sec // 60):02d}:{int(pos_sec % 60):02d}")
            self.lbl_total.setText(f"{int(dur_sec // 60):02d}:{int(dur_sec % 60):02d}")

        if not self._lines or not self._line_widgets:
            return

        # Apply calibration offset
        calibrated_pos = max(0.0, pos_sec + self._sync_offset)

        # Find active line
        active_idx = -1
        for i, (ts, text) in enumerate(self._lines):
            if ts <= calibrated_pos:
                active_idx = i
            else:
                break

        if active_idx != self._active_idx:
            # Demote previous
            if 0 <= self._active_idx < len(self._line_widgets):
                self._line_widgets[self._active_idx].set_active(False)

            self._active_idx = active_idx

            # Promote current
            if 0 <= active_idx < len(self._line_widgets):
                target_w = self._line_widgets[active_idx]
                target_w.set_active(True, self._accent_color)

                # Smoothly auto-scroll to center line
                if self._auto_scroll_enabled:
                    scroll_bar = self.scroll.verticalScrollBar()
                    target_y = target_w.pos().y()
                    viewport_h = self.scroll.viewport().height()
                    scroll_to = max(0, target_y - (viewport_h // 2) + (target_w.height() // 2))
                    scroll_bar.setValue(scroll_to)

    def update_levels(self, l_val, r_val):
        self.vu_meter.set_levels(l_val, r_val)
        self.spectrum.set_levels(l_val, r_val)
        self.spectrum.set_playing(True)

        avg = (l_val + r_val) / 2.0
        # Light up peak LEDs based on avg level
        self.led_12db.setStyleSheet("color: #22c55e; font-family: Monospace; font-size: 8px; font-weight: bold;" if avg > 0.15 else "color: #104515; font-family: Monospace; font-size: 8px;")
        self.led_6db.setStyleSheet("color: #84cc16; font-family: Monospace; font-size: 8px; font-weight: bold;" if avg > 0.40 else "color: #204510; font-family: Monospace; font-size: 8px;")
        self.led_0db.setStyleSheet("color: #eab308; font-family: Monospace; font-size: 8px; font-weight: bold;" if avg > 0.70 else "color: #4a3510; font-family: Monospace; font-size: 8px;")
        self.led_clip.setStyleSheet("color: #ef4444; font-family: Monospace; font-size: 8px; font-weight: bold;" if avg > 0.90 else "color: #4a1515; font-family: Monospace; font-size: 8px;")

    def _adjust_offset(self, delta):
        self._sync_offset += delta
        sign = "+" if self._sync_offset >= 0 else ""
        self.lbl_offset_val.setText(f"OFFSET: {sign}{self._sync_offset:.1f}s")

    def _reset_offset(self):
        self._sync_offset = 0.0
        self.lbl_offset_val.setText("OFFSET: +0.0s")

    def _on_font_knob_changed(self, val):
        # Maps 0.0-1.0 to 12px-28px
        self._font_size = int(12 + val * 16)
        for w in self._line_widgets:
            w.set_font_size(self._font_size)

    def _toggle_autoscroll(self):
        self._auto_scroll_enabled = not self._auto_scroll_enabled
        self.btn_autoscroll.set_led(self._auto_scroll_enabled, "#39ff14" if self._auto_scroll_enabled else "#444444")

    def _toggle_karaoke_glow(self):
        self._karaoke_glow_enabled = not self._karaoke_glow_enabled
        self.btn_glow.set_led(self._karaoke_glow_enabled, "#ffaa00" if self._karaoke_glow_enabled else "#444444")
        for w in self._line_widgets:
            w.set_karaoke_glow(self._karaoke_glow_enabled)

    def _toggle_vocal_enhance(self):
        self._vocal_enhance_enabled = not self._vocal_enhance_enabled
        self.btn_vocal_enhance.set_led(self._vocal_enhance_enabled, "#00f0ff" if self._vocal_enhance_enabled else "#444444")

    def _on_slider_moved(self, val):
        self.slider_seek_moved.emit(val)

    def _manual_fetch(self):
        if not self._current_track:
            QMessageBox.information(self, "No Track", "Please play a track first.")
            return
        artist = self._current_track.get("artist", "")
        title = self._current_track.get("title", "")
        duration = self._current_track.get("duration", 0)
        filepath = self._current_track.get("path", "")

        # Search explicitly and let the user choose among versions/releases.
        if hasattr(self, "_fetch_worker") and self._fetch_worker and self._fetch_worker.isRunning():
            try:
                self._fetch_worker.lyrics_ready.disconnect()
                self._fetch_worker.lyrics_failed.disconnect()
            except Exception:
                pass
        self._lyrics_selector = ManualLyricsSelectorDialog(filepath, artist, title, duration, self)
        self._lyrics_selector.lyrics_applied.connect(self._populate_lyrics)
        self._lyrics_selector.exec_()

    def resizeEvent(self, event):
        width = event.size().width()
        if width < 900:
            left_width, right_width, art_size = 184, 174, 154
        elif width < 1200:
            left_width, right_width, art_size = 218, 210, 188
        else:
            left_width, right_width, art_size = 260, 250, 220
        self._lyrics_left.setFixedWidth(left_width)
        self._lyrics_right.setFixedWidth(right_width)
        self._lyrics_right_scroll.setFixedWidth(right_width)
        self.cover_art.setFixedSize(art_size, art_size)
        self.lbl_interactive_hint.setVisible(width >= 900)
        self.lbl_sync_mode.setText("SYNC CALIBRATION:" if width >= 900 else "SYNC:")
        super().resizeEvent(event)

    def _open_local_lrc_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select .LRC Lyrics File", os.path.expanduser("~/Music"), "LRC Lyrics Files (*.lrc *.txt)"
        )
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                parsed = LyricsManager.parse_lrc(content)
                if parsed:
                    self._populate_lyrics(parsed, is_synced=True)
                else:
                    QMessageBox.warning(self, "Invalid LRC", "Could not parse timestamps from this file.")
            except Exception as e:
                QMessageBox.warning(self, "Read Error", str(e))
