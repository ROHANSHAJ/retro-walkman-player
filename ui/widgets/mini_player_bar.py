import os
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QPixmap, QFont, QPainter, QPainterPath, QColor, QPen
from ui.widgets.vintage_controls import RetroSlider


def create_default_art_pixmap(size=58, accent="#00f0ff"):
    """
    Renders a clean, modern vector hi-fi vinyl disc emblem for tracks without covers.
    Avoids low-res or platform-dependent emoji fallbacks.
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Dark rounded container
    p.setPen(QPen(QColor("#242c38"), 1))
    p.setBrush(QColor("#11151c"))
    p.drawRoundedRect(1, 1, size - 2, size - 2, 6, 6)

    cx, cy = size / 2.0, size / 2.0
    # Outer groove rings
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#1e2530"), 1.2))
    p.drawEllipse(QRectF(cx - 20, cy - 20, 40, 40))
    p.setPen(QPen(QColor("#283241"), 1.0))
    p.drawEllipse(QRectF(cx - 14, cy - 14, 28, 28))

    # Center label dot with theme accent
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(accent))
    p.drawEllipse(QRectF(cx - 6, cy - 6, 12, 12))

    # Spindle hole
    p.setBrush(QColor("#11151c"))
    p.drawEllipse(QRectF(cx - 2, cy - 2, 4, 4))
    p.end()
    return pix


class VolumeIconWidget(QWidget):
    """
    Crisp vector-drawn speaker icon with dynamic audio wave arcs and mute state.
    Eliminates distorted or platform-inconsistent emoji fonts. Clickable to toggle mute.
    """
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._volume = 0.85
        self._muted = False
        self._accent = "#00f0ff"
        self._is_hovered = False
        self.setToolTip("Click to mute / unmute")

    def set_volume(self, vol):
        self._volume = max(0.0, min(1.0, float(vol)))
        self._muted = (self._volume == 0.0)
        self.update()

    def set_muted(self, muted):
        self._muted = bool(muted)
        self.update()

    def set_accent(self, accent):
        self._accent = accent
        self.update()

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        color = QColor(self._accent if self._is_hovered else ("#94a3b8" if not self._muted and self._volume > 0 else "#64748b"))
        if self._is_hovered and (self._muted or self._volume == 0):
            color = QColor("#ef4444")

        # Vector speaker body
        body = QPainterPath()
        body.moveTo(3, 8)
        body.lineTo(6, 8)
        body.lineTo(11, 4)
        body.lineTo(11, 18)
        body.lineTo(6, 14)
        body.lineTo(3, 14)
        body.closeSubpath()
        painter.fillPath(body, color)

        if self._muted or self._volume <= 0.01:
            x_pen = QPen(QColor("#ef4444" if not self._is_hovered else "#f87171"), 1.6, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(x_pen)
            painter.drawLine(14, 8, 19, 14)
            painter.drawLine(14, 14, 19, 8)
        else:
            arc_pen = QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(QRectF(7, 6, 9, 10), -50 * 16, 100 * 16)
            if self._volume > 0.5:
                painter.drawArc(QRectF(6, 3, 14, 16), -55 * 16, 110 * 16)

        painter.end()


class MiniPlayerBar(QWidget):
    play_pause_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    rewind_clicked = pyqtSignal()
    fast_forward_clicked = pyqtSignal()
    seek_moved = pyqtSignal(int)
    seek_released = pyqtSignal()
    volume_changed = pyqtSignal(float)
    lyrics_toggle_clicked = pyqtSignal()
    art_clicked = pyqtSignal()
    shuffle_clicked = pyqtSignal()
    repeat_clicked = pyqtSignal()
    queue_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(78)
        self.setMaximumHeight(88)
        self._user_seeking = False
        self._accent = "#ffb000"
        self._has_custom_art = False
        self._pre_mute_vol = 85
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Left: Album Art Thumbnail
        self.lbl_art = QLabel()
        self.lbl_art.setFixedSize(58, 58)
        self.lbl_art.setStyleSheet("background: #14171a; border: 1px solid #303640; border-radius: 6px;")
        self.lbl_art.setAlignment(Qt.AlignCenter)
        self.lbl_art.setCursor(Qt.PointingHandCursor)
        self.lbl_art.mousePressEvent = lambda e: self.art_clicked.emit()
        layout.addWidget(self.lbl_art)

        # Track Title & Artist
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.setAlignment(Qt.AlignVCenter)

        self.lbl_title = QLabel("No Song Playing")
        self.lbl_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 700;")
        self.lbl_artist = QLabel("Select a track from the library")
        self.lbl_artist.setStyleSheet("color: #aab7c6; font-size: 12px;")
        self.lbl_title.setMinimumWidth(150)
        self.lbl_title.setMaximumWidth(340)
        self.lbl_artist.setMaximumWidth(340)

        info_col.addWidget(self.lbl_title)
        info_col.addWidget(self.lbl_artist)
        layout.addLayout(info_col, 2)

        # Center: Transport Controls & Scrubber
        center_col = QVBoxLayout()
        center_col.setSpacing(2)
        center_col.setAlignment(Qt.AlignCenter)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)
        ctrl_row.setAlignment(Qt.AlignCenter)

        self.btn_prev = QPushButton("|<")
        self.btn_prev.setFixedSize(36, 32)
        self.btn_prev.setToolTip("Previous track (Z)")
        self.btn_prev.clicked.connect(self.prev_clicked.emit)

        self.btn_rewind = QPushButton("<<")
        self.btn_rewind.setFixedSize(36, 32)
        self.btn_rewind.setToolTip("Seek backward 10 seconds")
        self.btn_rewind.clicked.connect(self.rewind_clicked.emit)

        self.btn_play = QPushButton(">")
        self.btn_play.setFixedSize(42, 36)
        self.btn_play.setToolTip("Play / Pause (Space)")
        self.btn_play.clicked.connect(self.play_pause_clicked.emit)

        self.btn_stop = QPushButton("[]")
        self.btn_stop.setFixedSize(36, 32)
        self.btn_stop.setToolTip("Stop playback (X)")
        self.btn_stop.clicked.connect(self.stop_clicked.emit)

        self.btn_fast_forward = QPushButton(">>")
        self.btn_fast_forward.setFixedSize(36, 32)
        self.btn_fast_forward.setToolTip("Seek forward 10 seconds")
        self.btn_fast_forward.clicked.connect(self.fast_forward_clicked.emit)

        self.btn_next = QPushButton(">|")
        self.btn_next.setFixedSize(36, 32)
        self.btn_next.setToolTip("Next track (B)")
        self.btn_next.clicked.connect(self.next_clicked.emit)

        ctrl_row.addWidget(self.btn_prev)
        ctrl_row.addWidget(self.btn_rewind)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_stop)
        ctrl_row.addWidget(self.btn_fast_forward)
        ctrl_row.addWidget(self.btn_next)
        self._transport_buttons = [self.btn_prev, self.btn_rewind, self.btn_play, self.btn_stop, self.btn_fast_forward, self.btn_next]
        center_col.addLayout(ctrl_row)

        # Scrubber row
        scrub_row = QHBoxLayout()
        scrub_row.setSpacing(8)

        self.lbl_curr = QLabel("00:00")
        self.lbl_curr.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 10px; font-weight: bold;")
        self.slider_pos = RetroSlider(Qt.Horizontal, "#00f0ff")
        self.slider_pos.setRange(0, 1000)
        self.slider_pos.sliderPressed.connect(self._on_seek_pressed)
        self.slider_pos.sliderReleased.connect(self._on_seek_released)
        self.slider_pos.valueChanged.connect(self._on_seek_moved)

        self.lbl_total = QLabel("00:00")
        self.lbl_total.setStyleSheet("color: #8c96a4; font-family: Monospace; font-size: 10px; font-weight: bold;")

        scrub_row.addWidget(self.lbl_curr)
        scrub_row.addWidget(self.slider_pos, 1)
        scrub_row.addWidget(self.lbl_total)
        center_col.addLayout(scrub_row)

        layout.addLayout(center_col, 4)

        # Right: Repeat, shuffle, queue, lyrics, volume
        right_row = QHBoxLayout()
        right_row.setSpacing(8)
        right_row.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.btn_repeat = QPushButton("REP")
        self.btn_repeat.setFixedHeight(30)
        self.btn_repeat.setToolTip("Cycle repeat mode (All, 1, Off)")
        self.btn_repeat.clicked.connect(self.repeat_clicked.emit)
        right_row.addWidget(self.btn_repeat)

        self.btn_shuffle = QPushButton("SHUF")
        self.btn_shuffle.setFixedHeight(30)
        self.btn_shuffle.setToolTip("Toggle shuffle playback")
        self.btn_shuffle.clicked.connect(self.shuffle_clicked.emit)
        right_row.addWidget(self.btn_shuffle)

        self.btn_queue = QPushButton("QUEUE")
        self.btn_queue.setFixedHeight(30)
        self.btn_queue.setToolTip("Open playback queue drawer")
        self.btn_queue.clicked.connect(self.queue_clicked.emit)
        right_row.addWidget(self.btn_queue)

        self.btn_lyrics = QPushButton("LYRICS")
        self.btn_lyrics.setObjectName("btnLyrics")
        self.btn_lyrics.setToolTip("Toggle Lyrics & Karaoke Teleprompter")
        self.btn_lyrics.setMinimumWidth(68)
        self.btn_lyrics.setFixedHeight(30)
        self.btn_lyrics.clicked.connect(self.lyrics_toggle_clicked.emit)
        right_row.addWidget(self.btn_lyrics)

        self.vol_icon = VolumeIconWidget()
        self.vol_icon.clicked.connect(self._toggle_mute)

        self.slider_vol = RetroSlider(Qt.Horizontal, "#00f0ff")
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(85)
        self.slider_vol.setFixedWidth(80)
        self.slider_vol.valueChanged.connect(self._on_vol_changed)

        right_row.addWidget(self.vol_icon)
        right_row.addWidget(self.slider_vol)

        layout.addLayout(right_row, 2)

        self.setStyleSheet("""
            MiniPlayerBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #22262c, stop:0.06 #1a1c20, stop:1 #101214);
                border-top: 2px solid #2e343e;
            }
        """)
        self.lbl_art.setPixmap(create_default_art_pixmap(58, self._accent))
        self.set_theme(self._accent)

    def _on_vol_changed(self, val):
        self.vol_icon.set_volume(val / 100.0)
        self.volume_changed.emit(val / 100.0)

    def _toggle_mute(self):
        cur = self.slider_vol.value()
        if cur > 0:
            self._pre_mute_vol = cur
            self.slider_vol.setValue(0)
        else:
            self.slider_vol.setValue(getattr(self, "_pre_mute_vol", 80))

    def set_track_info(self, title, artist, art_path=None, album=None):
        self.lbl_title.setText(title or "No Song Playing")
        self.lbl_artist.setText(" • ".join(value for value in (artist, album) if value) or "Select a track from the library")
        self.lbl_title.setToolTip(title or "No Song Playing")
        self.lbl_artist.setToolTip(self.lbl_artist.text())
        if art_path:
            from ui.widgets.hero_cover_art import _COVER_CACHE
            cache_key = (str(art_path), 58, 58)
            if cache_key in _COVER_CACHE:
                self._has_custom_art = True
                self.lbl_art.setPixmap(_COVER_CACHE[cache_key])
                return
            elif os.path.exists(art_path):
                pix = QPixmap(art_path)
                if not pix.isNull():
                    self._has_custom_art = True
                    scaled = pix.scaled(58, 58, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    _COVER_CACHE[cache_key] = scaled
                    self.lbl_art.setPixmap(scaled)
                    return
        self._has_custom_art = False
        self.lbl_art.setPixmap(create_default_art_pixmap(58, self._accent))

    def set_playing_state(self, is_playing):
        self.btn_play.setText("||" if is_playing else ">")

    def set_modes(self, repeat_mode="ALL", shuffled=False):
        self.btn_repeat.setText({"ALL": "REP", "ONE": "REP 1", "OFF": "REP"}.get(repeat_mode, "REP"))
        self.btn_repeat.setToolTip(f"Repeat mode: {repeat_mode.lower()}")
        self.btn_shuffle.setProperty("active", bool(shuffled))
        self.btn_repeat.setProperty("active", repeat_mode != "OFF")
        self.btn_shuffle.style().unpolish(self.btn_shuffle)
        self.btn_shuffle.style().polish(self.btn_shuffle)
        self.btn_repeat.style().unpolish(self.btn_repeat)
        self.btn_repeat.style().polish(self.btn_repeat)

    def set_theme(self, accent):
        self._accent = accent
        self.lbl_curr.setStyleSheet(f"color: {accent}; font-family: Monospace; font-size: 10px; font-weight: bold;")
        self.slider_pos.set_glow_color(accent)
        self.slider_vol.set_glow_color(accent)
        self.vol_icon.set_accent(accent)
        if not self._has_custom_art:
            self.lbl_art.setPixmap(create_default_art_pixmap(58, accent))

        for button in self._transport_buttons:
            is_primary = button is self.btn_play
            button.setStyleSheet(f"""
                QPushButton {{
                    background: {accent if is_primary else 'rgba(255,255,255,8)'};
                    border: 1px solid {'#e8f7ff' if is_primary else '#3a4654'};
                    border-radius: {'18px' if is_primary else '10px'};
                    color: {'#08131b' if is_primary else '#eef6fc'};
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "DejaVu Sans", sans-serif;
                    font-size: {'17px' if is_primary else '13px'};
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {'#ffffff' if is_primary else 'rgba(255,255,255,15)'};
                    border-color: {accent};
                    color: {'#08131b' if is_primary else '#ffffff'};
                }}
                QPushButton:pressed {{
                    background: {'#dcecf4' if is_primary else '#253442'};
                }}
            """)
        self.setStyleSheet(f"""
            MiniPlayerBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #20252d, stop:0.07 #171b22, stop:1 #0c1015);
                border-top: 1px solid #38414e;
            }}
            MiniPlayerBar QPushButton {{
                background: #1b222c;
                border: 1px solid #364252;
                border-radius: 5px;
                min-width: 28px;
                min-height: 30px;
                color: #d8e2ec;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "DejaVu Sans", sans-serif;
                font-size: 13px;
                font-weight: bold;
            }}
            MiniPlayerBar QPushButton:hover {{ border-color: {accent}; color: {accent}; }}
            MiniPlayerBar QPushButton[active="true"] {{ background: {accent}; color: #0a1015; border-color: {accent}; }}
            MiniPlayerBar QPushButton#btnLyrics {{
                background: #18222d;
                border: 1px solid #0088cc;
                border-radius: 4px;
                min-width: 64px;
                padding: 0 8px;
                color: #00d0ff;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "DejaVu Sans", sans-serif;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            MiniPlayerBar QPushButton#btnLyrics:hover {{
                background: #0088cc;
                color: #ffffff;
                border-color: #00aaff;
            }}
        """)

    def update_position(self, pos_sec, dur_sec):
        if not self._user_seeking:
            if dur_sec > 0:
                val = int((pos_sec / dur_sec) * 1000)
                self.slider_pos.setValue(val)
            self.lbl_curr.setText(f"{int(pos_sec // 60):02d}:{int(pos_sec % 60):02d}")
            if dur_sec > 0:
                self.lbl_total.setText(f"{int(dur_sec // 60):02d}:{int(dur_sec % 60):02d}")

    def _on_seek_pressed(self):
        self._user_seeking = True

    def _on_seek_released(self):
        self._user_seeking = False
        self.seek_released.emit()

    def _on_seek_moved(self, val):
        if self._user_seeking:
            self.seek_moved.emit(val)

