import os
import math
import random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QFrame, QPushButton, QSizePolicy, QGridLayout, QComboBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer
from PyQt5.QtGui import (
    QPixmap, QFont, QColor, QPainter, QLinearGradient, QRadialGradient,
    QBrush, QPen, QPainterPath
)

from ui.widgets.seven_segment import SevenSegmentDisplay, RetroMarquee
from ui.widgets.cassette_deck import CassetteDeckWidget
from ui.widgets.vu_meter import StereoVUMeter
from ui.widgets.analog_vu_meter import DualStereoAnalogVUMeter
from ui.widgets.vinyl_widget import VinylTurntableWidget
from ui.widgets.hero_cover_art import HeroCoverArtWindow
from ui.widgets.rotary_knob import RotaryKnob
from ui.widgets.click_wheel import ClickWheel
from ui.widgets.vintage_controls import VintageButton, RetroSlider, LabeledKnob
from ui.widgets.spectrum_analyzer import WinampSpectrumAnalyzer

_FROST_TILE = None


def get_frost_tile():
    """Cached 64x64 micro-stipple noise texture for realistic sandblasted frosted glass."""
    global _FROST_TILE
    if _FROST_TILE is None:
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        rnd = random.Random(42)
        for _ in range(180):
            x = rnd.randint(0, 63)
            y = rnd.randint(0, 63)
            alpha = rnd.randint(8, 28)
            p.setPen(QColor(255, 255, 255, alpha))
            p.drawPoint(x, y)
        p.end()
        _FROST_TILE = pix
    return _FROST_TILE


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to view track details and browse similar tracks")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class LiquidGlassFrame(QFrame):
    """
    Physical Liquid Glass chassis material with Snell's Law refraction,
    superellipse volume profiling, adjustable diffuse frosting, and chromatic dispersion.
    Inspired by ryohsuke1231/liquid-glass and kotikotprojects/pyqt-liquidglass.
    """
    def __init__(self, radius=20, kind="body", parent=None):
        super().__init__(parent)
        self.radius = radius
        self.kind = kind
        self._transparency = 30
        self._frosting = 40
        self._shimmer_phase = 0.0
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

    def set_transparency(self, value):
        value = max(0, min(100, int(value)))
        if value != self._transparency:
            self._transparency = value
            self.update()

    def set_frosting(self, value):
        value = max(0, min(100, int(value)))
        if value != self._frosting:
            self._frosting = value
            self.update()

    def set_shimmer_phase(self, phase):
        self._shimmer_phase = float(phase) % 1.0
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.width() < 4 or self.height() < 4:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.HighQualityAntialiasing)
        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        w, h = bounds.width(), bounds.height()

        shape = QPainterPath()
        shape.addRoundedRect(bounds, self.radius, self.radius)
        painter.setClipPath(shape)

        clarity = 1.0 - self._transparency / 100.0
        tint_alpha = int(round(225 * (clarity ** 1.35)))

        # 1. Snell's Law Volumetric Depth Profiling (simulating thicker dome center, thin edges)
        apex_x = bounds.left() + w * 0.38
        apex_y = bounds.top() + h * 0.30
        rad_vol = QRadialGradient(apex_x, apex_y, max(w, h) * 0.82)
        if self.kind == "screen":
            # Deep OLED crystal display under flush liquid glass lens
            scr_center = min(255, int(tint_alpha * 1.15))
            rad_vol.setColorAt(0.0, QColor(22, 32, 42, scr_center))
            rad_vol.setColorAt(0.35, QColor(12, 18, 24, tint_alpha))
            rad_vol.setColorAt(0.75, QColor(6, 10, 14, tint_alpha))
            rad_vol.setColorAt(1.0, QColor(2, 4, 6, tint_alpha))
        else:
            # Main Hi-Fi Liquid Glass Chassis Body
            rad_vol.setColorAt(0.0, QColor(58, 80, 100, tint_alpha))
            rad_vol.setColorAt(0.28, QColor(36, 52, 66, tint_alpha))
            rad_vol.setColorAt(0.65, QColor(20, 30, 40, tint_alpha))
            rad_vol.setColorAt(0.88, QColor(12, 18, 25, tint_alpha))
            rad_vol.setColorAt(1.0, QColor(7, 11, 16, tint_alpha))
        if tint_alpha > 0:
            painter.fillPath(shape, QBrush(rad_vol))

        # 1.5 Frosted Surface Diffusion (Sandblasted micro-texture + diffuse light scattering veil)
        if self._frosting > 1:
            frost_ratio = self._frosting / 100.0
            veil_alpha = int(75 * frost_ratio)
            painter.fillRect(bounds.toRect(), QColor(215, 235, 248, veil_alpha))
            tile = get_frost_tile()
            tile_opacity = min(1.0, 0.20 + 0.80 * frost_ratio)
            painter.save()
            painter.setOpacity(tile_opacity)
            painter.drawTiledPixmap(bounds.toRect(), tile)
            painter.restore()

        # 2. Ambient Surface Meniscus Glare (Overhead soft sky reflection)
        glare_h = h * 0.52
        glare = QLinearGradient(bounds.left(), bounds.top(), bounds.left(), bounds.top() + glare_h)
        top_alpha = int(round((46 if self.kind == "body" else 32) * max(0.15, clarity)))
        glare.setColorAt(0.0, QColor(255, 255, 255, min(255, top_alpha + 24)))
        glare.setColorAt(0.22, QColor(240, 250, 255, top_alpha))
        glare.setColorAt(0.60, QColor(220, 245, 255, int(round(8 * clarity))))
        glare.setColorAt(1.0, QColor(200, 240, 255, 0))
        painter.fillRect(QRectF(bounds.left(), bounds.top(), w, glare_h), QBrush(glare))

        # 3. Dynamic Swept Caustic Reflection Wave (when audio is playing)
        band_x = -w * 0.35 + self._shimmer_phase * w * 1.7
        sheen = QLinearGradient(band_x, 0, band_x + w * 0.24, 0)
        sheen.setColorAt(0.0, QColor(114, 230, 255, 0))
        sheen.setColorAt(0.35, QColor(180, 245, 255, 30))
        sheen.setColorAt(0.50, QColor(255, 255, 255, 60))
        sheen.setColorAt(0.65, QColor(114, 230, 255, 40))
        sheen.setColorAt(1.0, QColor(114, 230, 255, 0))
        refl = QPainterPath()
        refl.moveTo(band_x, 0)
        refl.lineTo(band_x + w * 0.14, 0)
        refl.lineTo(band_x + w * 0.40, h)
        refl.lineTo(band_x + w * 0.26, h)
        refl.closeSubpath()
        painter.fillPath(refl, QBrush(sheen))

        # 4. Snell's Law Refraction Meniscus Rim (Outer Specular Crest)
        # Even at 100% transparency, clear glass retains its crisp specular edge refraction
        crest_alpha = max(115, round(235 * clarity))
        outer_rim = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        outer_rim.setColorAt(0.0, QColor(255, 255, 255, crest_alpha))
        outer_rim.setColorAt(0.30, QColor(225, 248, 255, round(crest_alpha * 0.72)))
        outer_rim.setColorAt(0.65, QColor(114, 230, 255, round(crest_alpha * 0.45)))
        outer_rim.setColorAt(1.0, QColor(0, 0, 0, int(round(180 * clarity))))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QBrush(outer_rim), 1.5))
        painter.drawPath(shape)

        # 5. Inset Chromatic Dispersion Fringe (2.5px inside)
        disp_alpha = int(round(165 * clarity))
        if disp_alpha > 0:
            inner_bounds = bounds.adjusted(2.5, 2.5, -2.5, -2.5)
            inner_shape = QPainterPath()
            inner_shape.addRoundedRect(inner_bounds, max(2, self.radius - 2), max(2, self.radius - 2))
            inner_rim = QLinearGradient(inner_bounds.topLeft(), inner_bounds.bottomRight())
            inner_rim.setColorAt(0.0, QColor(114, 230, 255, disp_alpha))
            inner_rim.setColorAt(0.40, QColor(180, 240, 255, round(disp_alpha * 0.55)))
            inner_rim.setColorAt(0.75, QColor(60, 140, 180, round(disp_alpha * 0.25)))
            inner_rim.setColorAt(1.0, QColor(10, 20, 30, int(round(160 * clarity))))
            painter.setPen(QPen(QBrush(inner_rim), 1.0))
            painter.drawPath(inner_shape)

        # 6. Bevel Shelf Contour Line (5px inside)
        shelf_alpha = int(round(40 * clarity))
        if shelf_alpha > 0:
            shelf_bounds = bounds.adjusted(5.0, 5.0, -5.0, -5.0)
            shelf_shape = QPainterPath()
            shelf_shape.addRoundedRect(shelf_bounds, max(2, self.radius - 5), max(2, self.radius - 5))
            painter.setPen(QPen(QColor(255, 255, 255, shelf_alpha), 0.7))
            painter.drawPath(shelf_shape)


class LiquidGlassPillButton(QPushButton):
    """
    Liquid glass capsule button based on Snell's law refraction
    and surface tension meniscus curvature (ryohsuke1231/liquid-glass).
    """
    def __init__(self, text, icon_str="", parent=None):
        label = f"{icon_str} {text}".strip() if icon_str else text
        super().__init__(label, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self._hovered = False
        self._transparency = 30
        self.setFont(QFont("Segoe UI", 11, QFont.Bold))

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def set_transparency(self, val):
        self._transparency = max(0, min(100, int(val)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        is_down = self.isDown()
        radius = h / 2.0

        draw_y = 1.5 if is_down else 0.0
        bounds = QRectF(1.5, draw_y + 1.0, w - 3.0, h - 2.5)

        shape = QPainterPath()
        shape.addRoundedRect(bounds, radius, radius)

        clarity = 1.0 - self._transparency / 100.0
        tint_alpha = int(round(200 * (clarity ** 1.3)))

        # 1. Base Liquid Glass Volume & Glare (clipped strictly to pill capsule)
        body = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        if self._hovered:
            body.setColorAt(0.0, QColor(65, 95, 120, min(255, tint_alpha + 45)))
            body.setColorAt(0.4, QColor(42, 65, 84, min(255, tint_alpha + 35)))
            body.setColorAt(0.85, QColor(20, 32, 42, tint_alpha))
            body.setColorAt(1.0, QColor(10, 16, 22, tint_alpha))
        else:
            body.setColorAt(0.0, QColor(48, 62, 74, tint_alpha))
            body.setColorAt(0.4, QColor(30, 42, 52, tint_alpha))
            body.setColorAt(0.85, QColor(16, 24, 32, tint_alpha))
            body.setColorAt(1.0, QColor(8, 12, 17, tint_alpha))

        glare_h = bounds.height() * 0.48
        glare = QLinearGradient(bounds.left(), bounds.top(), bounds.left(), bounds.top() + glare_h)
        glare_alpha = int(round((75 if self._hovered else 50) * max(0.2, clarity)))
        glare.setColorAt(0.0, QColor(255, 255, 255, min(255, glare_alpha + 30)))
        glare.setColorAt(0.3, QColor(230, 250, 255, glare_alpha))
        glare.setColorAt(1.0, QColor(200, 240, 255, 0))
        glare_rect = QRectF(bounds.left(), bounds.top(), bounds.width(), glare_h)

        painter.save()
        painter.setClipPath(shape)
        if tint_alpha > 0 or self._hovered:
            painter.fillPath(shape, QBrush(body))
        painter.fillRect(glare_rect, QBrush(glare))
        painter.restore()

        # 2. Snell's Law Refractive Meniscus Crest (unclipped outer rim)
        crest_alpha = 245 if self._hovered else 210
        rim = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        rim.setColorAt(0.0, QColor(255, 255, 255, crest_alpha))
        rim.setColorAt(0.35, QColor(215, 245, 255, round(crest_alpha * 0.75)))
        rim.setColorAt(0.70, QColor(114, 230, 255, round(crest_alpha * 0.45)))
        rim.setColorAt(1.0, QColor(0, 0, 0, int(round(180 * clarity))))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QBrush(rim), 1.3))
        painter.drawPath(shape)

        # 3. Inset Chromatic Caustic Fringe (2px inside)
        inner = bounds.adjusted(2, 2, -2, -2)
        inner_shape = QPainterPath()
        inner_shape.addRoundedRect(inner, max(2, radius - 2), max(2, radius - 2))
        inner_rim = QLinearGradient(inner.topLeft(), inner.bottomRight())
        inner_rim.setColorAt(0.0, QColor(114, 230, 255, int(round((160 if self._hovered else 95) * max(0.2, clarity)))))
        inner_rim.setColorAt(0.5, QColor(180, 240, 255, int(round(60 * clarity))))
        inner_rim.setColorAt(1.0, QColor(10, 20, 30, int(round(120 * clarity))))
        painter.setPen(QPen(QBrush(inner_rim), 0.9))
        painter.drawPath(inner_shape)

        # 4. Crisp Razor-Sharp Glyphs with optical glow
        painter.setFont(self.font())
        txt_col = QColor("#8cecff" if self._hovered else "#ffffff") if not is_down else QColor("#38d8f8")
        painter.setPen(txt_col)
        painter.drawText(bounds, Qt.AlignCenter, self.text())


# Helper for 4 faceplate hex screws
def draw_faceplate_screws(painter, w, h):
    painter.setPen(QPen(QColor(80, 85, 92), 1))
    painter.setBrush(QColor(32, 35, 40))
    for x, y in [(14, 14), (w - 14, 14), (14, h - 14), (w - 14, h - 14)]:
        painter.drawEllipse(QPointF(x, y), 4, 4)
        painter.setPen(QPen(QColor(15, 17, 20), 1))
        painter.drawLine(QPointF(x - 2, y), QPointF(x + 2, y))
        painter.setPen(QPen(QColor(80, 85, 92), 1))


class ThemeMotionOverlay(QWidget):
    """Low-cost animated accent sweep shared by every hardware skin."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._accent = QColor("#72e6ff")
        self._enabled = True
        self._playing = False
        self._phase = 0.0
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._step)

    def set_accent(self, color):
        self._accent = QColor(color)
        self.update()

    def set_motion_state(self, enabled, playing):
        self._enabled = bool(enabled)
        self._playing = bool(playing)
        if self._enabled and self._playing and self.isVisible():
            self._timer.start()
        else:
            self._timer.stop()
            self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if self._enabled and self._playing:
            self._timer.start()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _step(self):
        self._phase = (self._phase + 0.02) % 2.0
        self.update()

    def paintEvent(self, event):
        if not self._enabled or not self._playing:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        color = QColor(self._accent)
        color.setAlpha(38)
        painter.setPen(QPen(color, 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(3, 3, max(0, w - 6), max(0, h - 6)), 12, 12)

        travel = self._phase if self._phase <= 1 else 2 - self._phase
        x = 8 + travel * max(0, w - 92)
        sweep = QColor(self._accent)
        sweep.setAlpha(190)
        painter.setPen(Qt.NoPen)
        painter.setBrush(sweep)
        painter.drawRoundedRect(QRectF(x, 3, 72, 2), 1, 1)


# -------------------------------------------------------------
# 1. RETRO WALKMAN CASSETTE CHASSIS (THEME 1 - Sony WM-EX)
# -------------------------------------------------------------
class WalkmanDeckView(QWidget):
    art_clicked = pyqtSignal()
    track_details_clicked = pyqtSignal()
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    rew_clicked = pyqtSignal()
    ff_clicked = pyqtSignal()
    seek_moved = pyqtSignal(int)
    volume_changed = pyqtSignal(float)

    def __init__(self, theme_key="amber", parent=None):
        super().__init__(parent)
        self.theme_key = theme_key
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(8)

        # Brushed Anodized Metal Faceplate Chassis
        chassis = QFrame()
        chassis.setObjectName("walkmanChassis")
        chassis.setStyleSheet("""
            #walkmanChassis {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2b2d30, stop:0.03 #242629, stop:0.97 #1c1e21, stop:1 #131416);
                border-top: 1px solid rgba(255, 255, 255, 0.12);
                border-bottom: 2px solid rgba(0, 0, 0, 0.85);
                border-left: 1px solid rgba(255, 255, 255, 0.06);
                border-right: 1px solid rgba(0, 0, 0, 0.6);
                border-radius: 8px;
            }
        """)
        c_layout = QVBoxLayout(chassis)
        c_layout.setContentsMargins(18, 12, 18, 12)
        c_layout.setSpacing(8)

        # Top Bezel Header: Silk-Screened Brand Typography + Dolby & Mega Bass LEDs
        top_hdr = QHBoxLayout()
        brand_lbl = QLabel("SONY WALKMAN WM-EX  •  AUTO REVERSE  •  DOLBY B-C NR")
        brand_lbl.setStyleSheet("color: #b8bcc2; font-family: Monospace; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        
        self.btn_megabass = VintageButton("MEGA BASS", has_led=True)
        self.btn_megabass.setFixedHeight(26)
        self.btn_megabass.set_led(False, "#ffaa00")
        
        self.combo_dolby = QComboBox()
        self.combo_dolby.addItems(["DOLBY OFF", "DOLBY B", "DOLBY C"])
        self.combo_dolby.setToolTip("Select Dolby noise reduction mode")
        self.combo_dolby.setFixedWidth(112)
        self.combo_dolby.setStyleSheet("QComboBox { color:#dce3eb; background:#171a1e; border:1px solid #555b63; padding:4px; font: bold 9px monospace; } QComboBox QAbstractItemView { background:#171a1e; color:#dce3eb; }")

        self.combo_tape = QComboBox()
        self.combo_tape.addItems(["TYPE I · NORMAL", "TYPE II · CrO₂", "TYPE IV · METAL"])
        self.combo_tape.setToolTip("Select cassette tape formulation")
        self.combo_tape.setFixedWidth(145)
        self.combo_tape.setStyleSheet("QComboBox { color:#dce3eb; background:#171a1e; border:1px solid #555b63; padding:4px; font: bold 9px monospace; } QComboBox QAbstractItemView { background:#171a1e; color:#dce3eb; }")

        self.status_led = QLabel("[STOPPED]")
        self.status_led.setStyleSheet("color: #707680; font-family: Monospace; font-size: 11px; font-weight: bold;")

        top_hdr.addWidget(brand_lbl)
        top_hdr.addStretch()
        top_hdr.addWidget(self.btn_megabass)
        top_hdr.addWidget(self.combo_tape)
        top_hdr.addWidget(self.combo_dolby)
        top_hdr.addSpacing(10)
        top_hdr.addWidget(self.status_led)
        c_layout.addLayout(top_hdr)

        # Main Row: (Left 38% Dedicated Album Cover Bay) + (Right 62% VFD + Cassette Window)
        main_row = QHBoxLayout()
        main_row.setSpacing(16)

        # Left Column: Dedicated Recessed Jewel Case Album Cover Window
        left_bay = QVBoxLayout()
        left_bay.setAlignment(Qt.AlignCenter)
        self.cover_window = HeroCoverArtWindow(size=250)
        self.cover_window.clicked.connect(self.art_clicked.emit)
        sub_lbl = QLabel("HIGH-FIDELITY STEREO CASSETTE DECK")
        sub_lbl.setStyleSheet("color: #707680; font-family: Monospace; font-size: 9px; font-weight: bold; margin-top: 4px;")
        sub_lbl.setAlignment(Qt.AlignCenter)

        left_bay.addWidget(self.cover_window)
        left_bay.addWidget(sub_lbl)
        main_row.addLayout(left_bay, 38)

        # Right Column: Split Vertically (Top: VFD Telemetry, Bottom: Horizontal Cassette Window)
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        # Top ~35%: VFD Telemetry Window (Recessed dark-tinted acrylic panel)
        vfd_panel = QFrame()
        vfd_panel.setStyleSheet("""
            QFrame {
                background: #080a0c;
                border: 2px solid #16181d;
                border-top: 2px solid #040506;
                border-radius: 6px;
            }
        """)
        vfd_layout = QVBoxLayout(vfd_panel)
        vfd_layout.setContentsMargins(10, 6, 10, 6)
        vfd_layout.setSpacing(4)

        # Compact proportion-locked 7-Segment Timer + VU Meter
        vfd_top = QHBoxLayout()
        self.seven_seg = SevenSegmentDisplay(self.theme_key)
        self.vu_meter = StereoVUMeter()
        vfd_top.addWidget(self.seven_seg)
        vfd_top.addWidget(self.vu_meter, 1)
        vfd_layout.addLayout(vfd_top)

        # Scrolling Marquee Ticker
        self.marquee = RetroMarquee("SONY STEREO CASSETTE PLAYER READY", self.theme_key)
        self.marquee.setToolTip("Click the current track display for details")
        self.marquee.clicked.connect(self.track_details_clicked.emit)
        vfd_layout.addWidget(self.marquee)
        right_col.addWidget(vfd_panel, 2)

        # Bottom ~65%: Horizontal Mechanical Cassette Window (100:64 ratio)
        self.cassette_deck = CassetteDeckWidget()
        self.combo_tape.currentIndexChanged.connect(lambda index: self.cassette_deck.set_tape_type(("TYPE I", "TYPE II", "TYPE IV")[index]))
        self.cassette_deck.set_tape_type("TYPE I")
        self.cassette_deck.art_clicked.connect(self.art_clicked.emit)
        right_col.addWidget(self.cassette_deck, 3)

        main_row.addLayout(right_col, 62)
        c_layout.addLayout(main_row, 1)

        # Bottom Deck Strip: Scrubber + Mechanical Buttons + Multi-Knobs
        scrub_row = QHBoxLayout()
        self.lbl_curr = QLabel("00:00")
        self.lbl_curr.setStyleSheet("color: #ffb000; font-family: Monospace; font-size: 11px; font-weight: bold;")
        self.tape_slider = RetroSlider(Qt.Horizontal, "#ffb000")
        self.tape_slider.setRange(0, 1000)
        self.tape_slider.sliderMoved.connect(self.seek_moved.emit)
        self.lbl_total = QLabel("00:00")
        self.lbl_total.setStyleSheet("color: #8c929a; font-family: Monospace; font-size: 11px; font-weight: bold;")

        scrub_row.addWidget(self.lbl_curr)
        scrub_row.addWidget(self.tape_slider, 1)
        scrub_row.addWidget(self.lbl_total)
        c_layout.addLayout(scrub_row)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)

        b_prev = VintageButton("PREV", "|<")
        b_prev.clicked.connect(self.prev_clicked.emit)

        b_rew = VintageButton("REW", "<<")
        b_rew.clicked.connect(self.rew_clicked.emit)

        self.btn_play = VintageButton("PLAY", ">", is_accent=True, has_led=True)
        self.btn_play.clicked.connect(self.play_clicked.emit)

        self.btn_pause = VintageButton("PAUSE", "||", has_led=True)
        self.btn_pause.clicked.connect(self.pause_clicked.emit)

        b_stop = VintageButton("STOP", "[]")
        b_stop.clicked.connect(self.stop_clicked.emit)

        b_ff = VintageButton("F.FWD", ">>")
        b_ff.clicked.connect(self.ff_clicked.emit)

        b_next = VintageButton("NEXT", ">|")
        b_next.clicked.connect(self.next_clicked.emit)

        ctrl_row.addWidget(b_prev)
        ctrl_row.addWidget(b_rew)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_pause)
        ctrl_row.addWidget(b_stop)
        ctrl_row.addWidget(b_ff)
        ctrl_row.addWidget(b_next)
        ctrl_row.addStretch()

        # Multi-Knobs: Tone + Balance + Master Level Volume Knob
        self.knob_tone = LabeledKnob("TONE", style_mode="black", size=50)
        self.knob_tone.set_value(0.65)
        self.knob_bal = LabeledKnob("BALANCE", style_mode="black", size=50)
        self.knob_bal.set_value(0.50)

        vol_box = QVBoxLayout()
        vol_box.setAlignment(Qt.AlignCenter)
        vol_lbl = QLabel("VOLUME")
        vol_lbl.setStyleSheet("color: #b8bcc2; font-family: Monospace; font-size: 9px; font-weight: bold;")
        vol_lbl.setAlignment(Qt.AlignCenter)
        self.vol_knob = RotaryKnob(style_mode="black", size=60)
        self.vol_knob.valueChanged.connect(self.volume_changed.emit)
        vol_box.addWidget(vol_lbl)
        vol_box.addWidget(self.vol_knob)

        ctrl_row.addWidget(self.knob_tone)
        ctrl_row.addWidget(self.knob_bal)
        ctrl_row.addLayout(vol_box)

        c_layout.addLayout(ctrl_row)
        root.addWidget(chassis)

    def set_theme(self, theme_key):
        self.theme_key = theme_key
        self.seven_seg.set_theme(theme_key)
        self.marquee.set_theme(theme_key)

    def set_animations_enabled(self, enabled):
        self.cassette_deck.set_animations_enabled(enabled)
        self.marquee.set_animations_enabled(enabled)


# -------------------------------------------------------------
# 2. GLASS HI-FI PLAYER CHASSIS (THEME 2)
# -------------------------------------------------------------
class GlassHiFiDeckView(QWidget):
    art_clicked = pyqtSignal()
    track_details_clicked = pyqtSignal()
    play_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    change_next_clicked = pyqtSignal()
    glass_frosting_changed = pyqtSignal(int)
    seek_moved = pyqtSignal(int)
    volume_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._transparency = 30
        self._frosting = 40
        self._animations_enabled = True
        self._playing = False
        self._shimmer_phase = 0.0
        self._reflection_timer = QTimer(self)
        self._reflection_timer.setInterval(70)
        self._reflection_timer.timeout.connect(self._advance_reflection)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)

        # Layered smoked-glass chassis with cool illuminated edge trim
        chassis = LiquidGlassFrame(radius=22, kind="body")
        self.chassis = chassis
        chassis.setObjectName("dapChassis")
        c_layout = QHBoxLayout(chassis)
        c_layout.setContentsMargins(18, 14, 18, 14)
        c_layout.setSpacing(18)

        # Left Display (56% width): OLED Deep Black under Flush Glass
        screen_frame = LiquidGlassFrame(radius=14, kind="screen")
        self.screen_frame = screen_frame
        screen_frame.setObjectName("glassScreen")
        s_layout = QVBoxLayout(screen_frame)
        s_layout.setContentsMargins(12, 8, 12, 8)
        s_layout.setSpacing(6)

        # Slim Top Status Bar
        top_bar = QHBoxLayout()
        badge = QLabel("LIQUID GLASS AUDIO  •  HI-RES DECK")
        badge.setStyleSheet("color: #8cecff; font-family: Monospace; font-size: 10px; font-weight: bold;")
        vol_info = QLabel("SNELL REFRACTION  •  192 kHz / 24-BIT")
        vol_info.setStyleSheet("color: #7caebe; font-family: Monospace; font-size: 10px; font-weight: bold;")
        top_bar.addWidget(badge)
        top_bar.addStretch()
        top_bar.addWidget(vol_info)
        s_layout.addLayout(top_bar)

        # Hero 1:1 Square Album Cover
        art_box = QHBoxLayout()
        art_box.setAlignment(Qt.AlignCenter)
        self.cover_art = HeroCoverArtWindow(size=210)
        self.cover_art.is_liquid_glass = True
        self.cover_art.clicked.connect(self.art_clicked.emit)
        art_box.addWidget(self.cover_art)
        s_layout.addLayout(art_box)

        # Track Info Hierarchy Directly on OLED Black
        self.lbl_title = ClickableLabel("Track Title")
        self.lbl_title.clicked.connect(self.track_details_clicked.emit)
        self.lbl_title.setStyleSheet("color: #ffffff; background:transparent; border:0; font-size: 18px; font-weight: 700;")
        self.lbl_artist_album = QLabel("Artist Name — Album")
        self.lbl_artist_album.setStyleSheet("color: #b1dce9; background:transparent; border:0; font-size: 14px;")
        self.lbl_title.setWordWrap(True)
        self.lbl_artist_album.setWordWrap(True)
        s_layout.addWidget(self.lbl_title)
        s_layout.addWidget(self.lbl_artist_album)

        # Winamp-inspired phosphor spectrum on the smoked-glass status screen
        spectrum_label = QLabel("PHOSPHOR SPECTRUM  ·  16 BANDS")
        spectrum_label.setStyleSheet("color: #76b8c8; font-family: Monospace; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        s_layout.addWidget(spectrum_label)
        self.spectrum = WinampSpectrumAnalyzer(bands_count=16, theme_mode="winamp")
        self.spectrum.setFixedHeight(58)
        s_layout.addWidget(self.spectrum)

        # Precision Seek Bar with Track Timing
        scrub_row = QHBoxLayout()
        self.lbl_curr = QLabel("00:00")
        self.lbl_curr.setStyleSheet("color: #8cecff; font-family: Monospace; font-size: 10px; font-weight: bold;")
        self.slider_pos = RetroSlider(Qt.Horizontal, "#72e6ff")
        self.slider_pos.setRange(0, 1000)
        self.slider_pos.sliderMoved.connect(self.seek_moved.emit)
        self.lbl_total = QLabel("00:00")
        self.lbl_total.setStyleSheet("color: #5e8494; font-family: Monospace; font-size: 10px; font-weight: bold;")

        scrub_row.addWidget(self.lbl_curr)
        scrub_row.addWidget(self.slider_pos, 1)
        scrub_row.addWidget(self.lbl_total)
        s_layout.addLayout(scrub_row)

        # Spotify / YT Music style interactive Up Next bar
        next_bar = QHBoxLayout()
        next_bar.setContentsMargins(2, 2, 2, 2)
        next_bar.setSpacing(6)
        lbl_next_tag = QLabel("UP NEXT:")
        lbl_next_tag.setStyleSheet("color: #72e6ff; font-family: Monospace; font-size: 9px; font-weight: bold;")
        self.lbl_up_next = QLabel("Queue Empty")
        self.lbl_up_next.setStyleSheet("color: #c2e9f6; font-size: 11px; font-weight: 500;")
        self.lbl_up_next.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.btn_change_next = QPushButton("CHANGE")
        self.btn_change_next.setCursor(Qt.PointingHandCursor)
        self.btn_change_next.setStyleSheet("""
            QPushButton {
                background: rgba(114, 230, 255, 0.15);
                border: 1px solid rgba(114, 230, 255, 0.5);
                border-radius: 9px;
                color: #8cecff;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background: rgba(114, 230, 255, 0.35);
                border-color: #8cecff;
                color: #ffffff;
            }
        """)
        self.btn_change_next.clicked.connect(self.change_next_clicked.emit)
        next_bar.addWidget(lbl_next_tag)
        next_bar.addWidget(self.lbl_up_next, 1)
        next_bar.addWidget(self.btn_change_next)
        s_layout.addLayout(next_bar)

        s_layout.addStretch(1)

        c_layout.addWidget(screen_frame, 56)

        # Right Control Surface (44% width): Knurled Jog Wheel, Multi-Knobs & Multi-Buttons with LEDs
        ctrl_col = QVBoxLayout()
        ctrl_col.setAlignment(Qt.AlignCenter)
        ctrl_col.setSpacing(12)

        # Oversized Machined Rotary Jog Dial (104px) with Snell's law refraction
        wheel_box = QVBoxLayout()
        wheel_box.setAlignment(Qt.AlignCenter)
        self.knob = RotaryKnob(style_mode="liquid_glass", size=104)
        self.knob.valueChanged.connect(self.volume_changed.emit)
        dial_lbl = QLabel("VOLUME / JOG DIAL")
        dial_lbl.setStyleSheet("color: #8bbdcc; font-family: Monospace; font-size: 9px; font-weight: bold;")
        dial_lbl.setAlignment(Qt.AlignCenter)

        wheel_box.addWidget(self.knob, 0, Qt.AlignCenter)
        wheel_box.addWidget(dial_lbl, 0, Qt.AlignCenter)
        ctrl_col.addLayout(wheel_box)

        # Tactile bass, treble and glass frosting trims on the glass control rail
        knobs_row = QHBoxLayout()
        knobs_row.setSpacing(8)
        self.knob_bass = LabeledKnob("BASS", style_mode="liquid_glass", size=48)
        self.knob_bass.set_value(0.6)
        self.knob_treble = LabeledKnob("TREBLE", style_mode="liquid_glass", size=48)
        self.knob_treble.set_value(0.7)
        self.knob_frost = LabeledKnob("FROST", style_mode="liquid_glass", size=48)
        self.knob_frost.set_value(0.4)
        self.knob_frost.valueChanged.connect(self._on_frost_knob_changed)
        knobs_row.addWidget(self.knob_bass)
        knobs_row.addWidget(self.knob_treble)
        knobs_row.addWidget(self.knob_frost)
        ctrl_col.addLayout(knobs_row)

        # Multi-Buttons with Status LEDs (Gain, DSD Direct, Balanced)
        btn_led_row = QHBoxLayout()
        btn_led_row.setSpacing(6)
        self.btn_gain = VintageButton("GAIN", has_led=True)
        self.btn_gain.set_liquid_glass(True)
        self.btn_gain.set_led(False, "#ff806e")
        self.btn_dsd = VintageButton("DSD", has_led=True)
        self.btn_dsd.set_liquid_glass(True)
        self.btn_dsd.set_led(False, "#70f0bd")
        self.lbl_balanced_output = QLabel("4.4 mm BALANCED OUTPUT")
        self.lbl_balanced_output.setStyleSheet("color: #70f0bd; font-family: Monospace; font-size: 8px; font-weight: bold;")

        btn_led_row.addWidget(self.btn_gain)
        btn_led_row.addWidget(self.btn_dsd)
        btn_led_row.addWidget(self.lbl_balanced_output, 1)
        ctrl_col.addLayout(btn_led_row)

        # Liquid Glass Transport Capsule Pill Buttons
        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(8)

        self.btn_prev = LiquidGlassPillButton("<<")
        self.btn_prev.setFixedSize(54, 40)
        self.btn_prev.clicked.connect(self.prev_clicked.emit)

        self.btn_play = LiquidGlassPillButton("> ||")
        self.btn_play.setFixedHeight(40)
        self.btn_play.clicked.connect(self.play_clicked.emit)

        self.btn_next = LiquidGlassPillButton(">>")
        self.btn_next.setFixedSize(54, 40)
        self.btn_next.clicked.connect(self.next_clicked.emit)

        btn_grid.addWidget(self.btn_prev)
        btn_grid.addWidget(self.btn_play, 1)
        btn_grid.addWidget(self.btn_next)
        ctrl_col.addLayout(btn_grid)

        # Laser-Etched Physical Branding
        laser_lbl = QLabel("GLASS AUDIO  •  HI-RES PLAYER")
        laser_lbl.setStyleSheet("color: #78bbcf; font-family: Monospace; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        laser_lbl.setAlignment(Qt.AlignCenter)
        ctrl_col.addWidget(laser_lbl)

        c_layout.addLayout(ctrl_col, 44)
        root.addWidget(chassis)
        self.set_glass_transparency(30)

    def _advance_reflection(self):
        self._shimmer_phase = (self._shimmer_phase + 0.009) % 1.0
        self.chassis.set_shimmer_phase(self._shimmer_phase)
        self.screen_frame.set_shimmer_phase(self._shimmer_phase)

    def _sync_reflection_animation(self):
        if self._animations_enabled and self._playing and self.isVisible():
            self._reflection_timer.start()
        else:
            self._reflection_timer.stop()

    def set_animations_enabled(self, enabled):
        self._animations_enabled = bool(enabled)
        self._sync_reflection_animation()

    def set_playing_state(self, playing):
        self._playing = bool(playing)
        self._sync_reflection_animation()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_reflection_animation()

    def hideEvent(self, event):
        self._reflection_timer.stop()
        super().hideEvent(event)

    def set_glass_transparency(self, percent):
        self._transparency = max(0, min(100, int(percent)))
        self.chassis.set_transparency(self._transparency)
        self.screen_frame.set_transparency(self._transparency)
        self.btn_gain.set_glass_transparency(self._transparency)
        self.btn_dsd.set_glass_transparency(self._transparency)
        self.btn_prev.set_transparency(self._transparency)
        self.btn_play.set_transparency(self._transparency)
        self.btn_next.set_transparency(self._transparency)
        clear = 1.0 - self._transparency / 100.0
        fill = round(190 * clear)
        edge = max(62, round(205 * clear))
        self.slider_pos.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: rgba(10, 18, 26, {max(140, fill + 30)});
                border: 1px solid rgba(114, 230, 255, {edge});
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(114, 230, 255, 220), stop:1 rgba(180, 245, 255, 250));
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 250), stop:0.5 rgba(180, 240, 255, 220), stop:1 rgba(80, 170, 210, 200));
                border: 1px solid rgba(255, 255, 255, 240);
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 4px;
            }}
        """)

    def set_track_info(self, title, artist, album, art_path):
        self.lbl_title.setText(title or "Hi-Fi Track")
        self.lbl_artist_album.setText(f"{artist or 'Audiophile'} — {album or 'Lossless'}")
        self.cover_art.set_artwork(art_path)

    def _on_frost_knob_changed(self, val):
        frost_pct = int(round(val * 100))
        self.set_glass_frosting(frost_pct)
        self.glass_frosting_changed.emit(frost_pct)

    def set_glass_frosting(self, percent):
        self._frosting = max(0, min(100, int(percent)))
        self.chassis.set_frosting(self._frosting)
        self.screen_frame.set_frosting(self._frosting)
        if hasattr(self, 'knob_frost'):
            self.knob_frost.blockSignals(True)
            self.knob_frost.set_value(self._frosting / 100.0)
            self.knob_frost.blockSignals(False)

    def set_up_next_info(self, title, artist=""):
        if not title:
            self.lbl_up_next.setText("Queue Empty")
        else:
            txt = f"{title} • {artist}" if artist else title
            self.lbl_up_next.setText(txt)


# -------------------------------------------------------------
# 3. IPOD CLASSIC VERTICAL INTERFACE (THEME 3)
#    Strictly vertical portrait player centered in the view,
#    flanked by Winamp-inspired 30-Pin Hi-Fi Dock Telemetry & Controls
# -------------------------------------------------------------
class IPodDeckView(QWidget):
    art_clicked = pyqtSignal()
    track_details_clicked = pyqtSignal()
    play_pause_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    wheel_spun = pyqtSignal(int)
    seek_moved = pyqtSignal(int)
    volume_changed = pyqtSignal(float)
    menu_action_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(14)

        # =============================================================
        # LEFT WING: 30-PIN DOCK DIGITAL LINE-OUT & SPECTRUM ANALYZER (~280px)
        # =============================================================
        self.left_dock = QFrame()
        left_dock = self.left_dock
        left_dock.setMinimumWidth(170)
        left_dock.setMaximumWidth(280)
        left_dock.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1c22, stop:1 #0e1014);
                border: 1px solid #2d3340;
                border-radius: 12px;
            }
        """)
        ld_layout = QVBoxLayout(left_dock)
        ld_layout.setContentsMargins(12, 12, 12, 12)
        ld_layout.setSpacing(10)

        hdr_dock = QLabel("APPLE 30-PIN UNIVERSAL DOCK")
        hdr_dock.setWordWrap(True)
        hdr_dock.setStyleSheet("color: #0070e0; font-family: Monospace; font-size: 10px; font-weight: bold; letter-spacing: 0.5px;")
        ld_layout.addWidget(hdr_dock)

        sub_dock = QLabel("DIRECT LINE OUT • 24-BIT/96kHz")
        sub_dock.setWordWrap(True)
        sub_dock.setStyleSheet("color: #718096; font-family: Monospace; font-size: 9px; font-weight: bold;")
        ld_layout.addWidget(sub_dock)

        # Winamp 16-Band Spectrum Analyzer in Silver/Blue theme
        ld_layout.addWidget(QLabel("DOCK SPECTRUM ANALYZER", styleSheet="color: #a0aec0; font-family: Monospace; font-size: 9px; font-weight: bold;"))
        self.spectrum = WinampSpectrumAnalyzer(bands_count=16, theme_mode="silver")
        self.spectrum.setFixedHeight(80)
        ld_layout.addWidget(self.spectrum)

        # Stereo VU Level Meter
        ld_layout.addWidget(QLabel("STEREO LINE LEVEL", styleSheet="color: #a0aec0; font-family: Monospace; font-size: 9px; font-weight: bold;"))
        self.vu_meter = StereoVUMeter()
        self.vu_meter.setFixedHeight(24)
        ld_layout.addWidget(self.vu_meter)

        # Multi-Buttons with Status LEDs
        ld_layout.addWidget(QLabel("DOCK DSP MODES", styleSheet="color: #718096; font-family: Monospace; font-size: 9px; font-weight: bold;"))
        
        self.lbl_lineout = QLabel("30-PIN LINE OUT")
        self.lbl_lineout.setStyleSheet("color: #70f0bd; font-family: Monospace; font-size: 9px; font-weight: bold;")
        
        self.btn_bass_boost = VintageButton("BASS BOOSTER", has_led=True)
        self.btn_bass_boost.set_led(False, "#0070e0")

        self.btn_acoustic = VintageButton("ACOUSTIC DSP", has_led=True)
        self.btn_acoustic.set_led(False, "#ffaa00")

        ld_layout.addWidget(self.lbl_lineout)
        ld_layout.addWidget(self.btn_bass_boost)
        ld_layout.addWidget(self.btn_acoustic)

        ld_layout.addStretch()
        root.addWidget(left_dock)

        # =============================================================
        # CENTER: AUTHENTIC VERTICAL IPOD CLASSIC CHASSIS (Fixed ~380px)
        # =============================================================
        ipod_container = QVBoxLayout()
        ipod_container.setAlignment(Qt.AlignCenter)

        self.ipod_chassis = QFrame()
        self.ipod_chassis.setMinimumWidth(320)
        self.ipod_chassis.setMaximumWidth(380)
        self.ipod_chassis.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.ipod_chassis.setObjectName("ipodVerticalChassis")
        self.ipod_chassis.setStyleSheet("""
            #ipodVerticalChassis {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f4f5f7, stop:0.04 #e8ebf0, stop:0.96 #d0d5de, stop:1 #bcc2cd);
                border-top: 2px solid #ffffff;
                border-left: 2px solid #ffffff;
                border-bottom: 3px solid #6c7582;
                border-right: 3px solid #6c7582;
                border-radius: 24px;
            }
        """)
        ipod_layout = QVBoxLayout(self.ipod_chassis)
        ipod_layout.setContentsMargins(18, 16, 18, 18)
        ipod_layout.setSpacing(12)

        # -------------------------------------------------------------
        # TOP ~50%: Classic iPod Color LCD Screen
        # -------------------------------------------------------------
        screen = QFrame()
        screen.setMinimumHeight(160)
        screen.setMaximumHeight(270)
        screen.setStyleSheet("""
            QFrame {
                background: #fbfbfb;
                border: 2px solid #7c8594;
                border-radius: 10px;
            }
        """)
        s_layout = QVBoxLayout(screen)
        s_layout.setContentsMargins(10, 8, 10, 8)
        s_layout.setSpacing(6)

        # Status Bar
        status_bar = QFrame()
        status_bar.setFixedHeight(22)
        status_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f0f0, stop:1 #c4c4c4);
                border-bottom: 1px solid #9c9c9c;
                border-radius: 3px;
            }
        """)
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(6, 0, 6, 0)
        self.lbl_play_state = QLabel(">")
        self.lbl_play_state.setStyleSheet("color: #202020; font-size: 10px; font-weight: bold;")
        np_title = QLabel("Now Playing")
        np_title.setStyleSheet("color: #202020; font-size: 11px; font-weight: bold;")
        bat = QLabel("[///]")
        bat.setStyleSheet("color: #107520; font-family: Monospace; font-size: 9px; font-weight: bold;")
        sb_layout.addWidget(self.lbl_play_state)
        sb_layout.addStretch()
        sb_layout.addWidget(np_title)
        sb_layout.addStretch()
        sb_layout.addWidget(bat)
        s_layout.addWidget(status_bar)

        # Classic menu list beside Now Playing art and track information.
        mid_content = QHBoxLayout()
        mid_content.setSpacing(7)

        self.menu_list = QListWidget()
        self.menu_list.addItems(["Music", "Videos", "Photos", "Podcasts", "Extras", "Settings", "Shuffle Songs", "Now Playing"])
        self.menu_list.setCurrentRow(0)
        self.menu_list.setMaximumWidth(116)
        self.menu_list.setStyleSheet("QListWidget { background:#f8f8f8; border:0; color:#222; font-size:10px; } QListWidget::item { padding:3px 5px; } QListWidget::item:selected { background:#087bd1; color:white; }")
        self.menu_list.itemDoubleClicked.connect(lambda item: self.menu_action_requested.emit(item.text()))
        mid_content.addWidget(self.menu_list, 1)

        self.cover_art = HeroCoverArtWindow(size=76)
        self.cover_art.clicked.connect(self.art_clicked.emit)
        mid_content.addWidget(self.cover_art)

        text_col = QVBoxLayout()
        text_col.setAlignment(Qt.AlignVCenter)
        text_col.setSpacing(3)

        self.lbl_title = ClickableLabel("Track Title")
        self.lbl_title.clicked.connect(self.track_details_clicked.emit)
        self.lbl_title.setStyleSheet("color: #1a1a1a; font-size: 10px; font-weight: bold;")
        self.lbl_artist = QLabel("Artist Name")
        self.lbl_artist.setStyleSheet("color: #404040; font-size: 9px; font-weight: 500;")
        self.lbl_album = QLabel("Album Title")
        self.lbl_album.setStyleSheet("color: #707070; font-size: 8px;")
        self.lbl_index = QLabel("1 of 12")
        self.lbl_index.setStyleSheet("color: #909090; font-size: 10px; margin-top: 2px;")

        text_col.addWidget(self.lbl_title)
        text_col.addWidget(self.lbl_artist)
        text_col.addWidget(self.lbl_album)
        text_col.addWidget(self.lbl_index)
        mid_content.addLayout(text_col, 1)

        s_layout.addLayout(mid_content, 1)

        # Apple Aqua Blue Scrubber Slider
        scrub_row = QHBoxLayout()
        self.lbl_curr = QLabel("00:00")
        self.lbl_curr.setStyleSheet("color: #202020; font-family: Monospace; font-size: 10px; font-weight: bold;")
        self.slider_pos = RetroSlider(Qt.Horizontal, "#0070e0")
        self.slider_pos.setRange(0, 1000)
        self.slider_pos.sliderMoved.connect(self.seek_moved.emit)
        self.lbl_rem = QLabel("-00:00")
        self.lbl_rem.setStyleSheet("color: #707070; font-family: Monospace; font-size: 10px; font-weight: bold;")

        scrub_row.addWidget(self.lbl_curr)
        scrub_row.addWidget(self.slider_pos, 1)
        scrub_row.addWidget(self.lbl_rem)
        s_layout.addLayout(scrub_row)

        ipod_layout.addWidget(screen)

        # -------------------------------------------------------------
        # BOTTOM ~50%: Iconic Centered Tactile Click Wheel (210px)
        # -------------------------------------------------------------
        wheel_container = QVBoxLayout()
        wheel_container.setAlignment(Qt.AlignCenter)
        self.click_wheel = ClickWheel(color_mode="white")
        self.click_wheel.setFixedSize(160, 160)
        self.click_wheel.play_pause_clicked.connect(self.play_pause_clicked.emit)
        self.click_wheel.center_clicked.connect(self.play_pause_clicked.emit)
        self.click_wheel.prev_clicked.connect(self.prev_clicked.emit)
        self.click_wheel.next_clicked.connect(self.next_clicked.emit)
        self.click_wheel.wheel_spun.connect(self.wheel_spun.emit)
        wheel_container.addWidget(self.click_wheel, 0, Qt.AlignCenter)

        ipod_layout.addLayout(wheel_container)

        ipod_container.addWidget(self.ipod_chassis)
        root.addLayout(ipod_container, 0)

        # =============================================================
        # RIGHT WING: HARDWARE DOCK CONTROLS & MULTI-KNOBS (~280px)
        # =============================================================
        self.right_dock = QFrame()
        right_dock = self.right_dock
        right_dock.setMinimumWidth(170)
        right_dock.setMaximumWidth(280)
        right_dock.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1c22, stop:1 #0e1014);
                border: 1px solid #2d3340;
                border-radius: 12px;
            }
        """)
        rd_layout = QVBoxLayout(right_dock)
        rd_layout.setContentsMargins(12, 12, 12, 12)
        rd_layout.setSpacing(10)

        hdr_ctrl = QLabel("DOCK MASTER CONTROLS")
        hdr_ctrl.setWordWrap(True)
        hdr_ctrl.setStyleSheet("color: #0070e0; font-family: Monospace; font-size: 10px; font-weight: bold; letter-spacing: 0.5px;")
        rd_layout.addWidget(hdr_ctrl)

        # Master Line Out Volume Knob
        vol_box = QVBoxLayout()
        vol_box.setAlignment(Qt.AlignCenter)
        vol_lbl = QLabel("LINE OUT LEVEL")
        vol_lbl.setStyleSheet("color: #a0aec0; font-family: Monospace; font-size: 9px; font-weight: bold;")
        vol_lbl.setAlignment(Qt.AlignCenter)
        self.knob_vol = RotaryKnob(style_mode="silver", size=70)
        self.knob_vol.valueChanged.connect(self.volume_changed.emit)
        vol_box.addWidget(self.knob_vol, 0, Qt.AlignCenter)
        vol_box.addWidget(vol_lbl, 0, Qt.AlignCenter)
        rd_layout.addLayout(vol_box)

        # Multi-Knobs: Bass & Treble Dock EQ
        dock_knobs = QHBoxLayout()
        dock_knobs.setSpacing(10)
        self.knob_bass = LabeledKnob("BASS", style_mode="silver", size=52)
        self.knob_bass.set_value(0.65)
        self.knob_treble = LabeledKnob("TREBLE", style_mode="silver", size=52)
        self.knob_treble.set_value(0.70)
        dock_knobs.addWidget(self.knob_bass)
        dock_knobs.addWidget(self.knob_treble)
        rd_layout.addLayout(dock_knobs)

        # Multi-Buttons with Status LEDs
        rd_layout.addWidget(QLabel("PLAYBACK MODES", styleSheet="color: #718096; font-family: Monospace; font-size: 9px; font-weight: bold;"))
        self.btn_repeat = VintageButton("REPEAT ALL", has_led=True)
        self.btn_repeat.set_led(True, "#0070e0")

        self.btn_shuffle = VintageButton("SHUFFLE SONGS", has_led=True)
        self.btn_shuffle.set_led(False, "#39ff14")

        self.btn_hold = VintageButton("HOLD SWITCH", has_led=True)
        self.btn_hold.set_led(False, "#ff4444")

        rd_layout.addWidget(self.btn_repeat)
        rd_layout.addWidget(self.btn_shuffle)
        rd_layout.addWidget(self.btn_hold)

        rd_layout.addStretch()
        root.addWidget(right_dock)

    def resizeEvent(self, event):
        # Shrink the sidecar docks on compact windows while keeping their controls available.
        compact = self.width() < 1000
        dock_width = 154 if compact else 280
        self.left_dock.setMaximumWidth(dock_width)
        self.right_dock.setMaximumWidth(dock_width)
        self.ipod_chassis.setMaximumWidth(350 if compact else 380)
        super().resizeEvent(event)

    def set_track_info(self, title, artist, album, art_path):
        self.lbl_title.setText(title or "Unknown Title")
        self.lbl_artist.setText(artist or "Unknown Artist")
        self.lbl_album.setText(album or "Unknown Album")
        self.cover_art.set_artwork(art_path)


# -------------------------------------------------------------
# 4. VINYL LP TURNTABLE DECK (THEME 4 - Direct-Drive Hi-Fi)
# -------------------------------------------------------------
class VinylTurntableDeckView(QWidget):
    art_clicked = pyqtSignal()
    track_details_clicked = pyqtSignal()
    play_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    seek_moved = pyqtSignal(int)
    volume_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)

        # Brushed Gunmetal / Walnut Direct-Drive Plinth
        plinth = QFrame()
        plinth.setObjectName("turntablePlinth")
        plinth.setStyleSheet("""
            #turntablePlinth {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #23272d, stop:1 #131518);
                border: 2px solid #3c424c;
                border-radius: 12px;
            }
        """)
        p_layout = QHBoxLayout(plinth)
        p_layout.setContentsMargins(18, 14, 18, 14)
        p_layout.setSpacing(20)

        # Left 50%: Platter Rim with Dotted Strobe Ring & Spinning 33 RPM Vinyl
        self.turntable = VinylTurntableWidget()
        self.turntable.art_clicked.connect(self.art_clicked.emit)
        p_layout.addWidget(self.turntable, 50)

        # Right 50%: "Now Spinning" LP Album Jacket + Controls
        right_deck = QVBoxLayout()
        right_deck.setSpacing(10)

        # Hero Album Jacket (Leaning on physical shelf)
        jacket_box = QHBoxLayout()
        jacket_box.setAlignment(Qt.AlignCenter)
        self.cover_art = HeroCoverArtWindow(size=210)
        self.cover_art.clicked.connect(self.art_clicked.emit)
        jacket_box.addWidget(self.cover_art)
        right_deck.addLayout(jacket_box)

        # Clean Track Readout Directly on Metal Plinth
        self.lbl_title = ClickableLabel("Vinyl Track Title")
        self.lbl_title.clicked.connect(self.track_details_clicked.emit)
        self.lbl_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold;")
        self.lbl_artist = QLabel("Artist Name")
        self.lbl_artist.setStyleSheet("color: #ffaa00; font-size: 12px;")
        right_deck.addWidget(self.lbl_title)
        right_deck.addWidget(self.lbl_artist)

        # Stereo VU Meter in Warm Amber
        self.vu_meter = StereoVUMeter()
        self.vu_meter.setFixedHeight(22)
        right_deck.addWidget(self.vu_meter)

        # Warm Amber Scrubber Track with Timestamps
        scrub_row = QHBoxLayout()
        self.lbl_curr = QLabel("00:00")
        self.lbl_curr.setStyleSheet("color: #ffaa00; font-family: Monospace; font-size: 10px; font-weight: bold;")
        self.slider_pos = RetroSlider(Qt.Horizontal, "#ffaa00")
        self.slider_pos.setRange(0, 1000)
        self.slider_pos.sliderMoved.connect(self.seek_moved.emit)
        self.lbl_total = QLabel("00:00")
        self.lbl_total.setStyleSheet("color: #8c826a; font-family: Monospace; font-size: 10px; font-weight: bold;")

        scrub_row.addWidget(self.lbl_curr)
        scrub_row.addWidget(self.slider_pos, 1)
        scrub_row.addWidget(self.lbl_total)
        right_deck.addLayout(scrub_row)

        # Multi-Knobs: Pitch / Speed 33-45 + Anti-Skate + Master Gain
        knobs_row = QHBoxLayout()
        knobs_row.setSpacing(8)
        self.knob_pitch = LabeledKnob("PITCH", style_mode="gold", size=50)
        self.knob_pitch.set_value(0.5)
        self.knob_skate = LabeledKnob("ANTI-SKATE", style_mode="gold", size=50)
        self.knob_skate.set_value(0.3)
        self.knob_gain = LabeledKnob("GAIN", style_mode="gold", size=50)
        self.knob_gain.set_value(0.85)
        self.knob_gain.valueChanged.connect(self.volume_changed.emit)

        knobs_row.addWidget(self.knob_pitch)
        knobs_row.addWidget(self.knob_skate)
        knobs_row.addWidget(self.knob_gain)
        right_deck.addLayout(knobs_row)

        # Multi-Buttons with Status LEDs + Transport Controls
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)

        b_prev = VintageButton("PREV", "|<")
        b_prev.clicked.connect(self.prev_clicked.emit)

        self.btn_play = VintageButton("START / STOP", ">", is_accent=True, has_led=True)
        self.btn_play.clicked.connect(self.play_clicked.emit)

        b_next = VintageButton("NEXT", ">|")
        b_next.clicked.connect(self.next_clicked.emit)

        self.btn_phono = VintageButton("PHONO PREAMP", has_led=True)
        self.btn_phono.set_led(False, "#ffaa00")

        ctrl_row.addWidget(b_prev)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(b_next)
        ctrl_row.addWidget(self.btn_phono)

        right_deck.addLayout(ctrl_row)
        p_layout.addLayout(right_deck, 50)

        root.addWidget(plinth)

    def set_track_info(self, title, artist, art_path):
        self.lbl_title.setText(title or "Unknown")
        self.lbl_artist.setText(artist or "Unknown")
        self.cover_art.set_artwork(art_path)
        self.turntable.set_artwork(art_path)


# -------------------------------------------------------------
# 5. STUDIO HI-FI RACKMOUNT CHASSIS (THEME 5 - 19" Studio Preamp)
# -------------------------------------------------------------
class StudioHiFiRackDeckView(QWidget):
    art_clicked = pyqtSignal()
    track_details_clicked = pyqtSignal()
    play_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    seek_moved = pyqtSignal(int)
    volume_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)

        # 19" Rackmount Faceplate with Hex Bolts
        rack = QFrame()
        rack.setObjectName("studioRack")
        rack.setStyleSheet("""
            #studioRack {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #24272c, stop:0.04 #1e2025, stop:0.96 #16181b, stop:1 #0e1012);
                border: 2px solid #3a404a;
                border-radius: 8px;
            }
        """)
        r_layout = QHBoxLayout(rack)
        r_layout.setContentsMargins(16, 12, 16, 12)
        r_layout.setSpacing(16)

        # Left Section (30% width): Dedicated 1:1 Square Cover Window + Spectrum Analyzer
        left_sec = QVBoxLayout()
        left_sec.setAlignment(Qt.AlignCenter)
        left_sec.setSpacing(6)

        self.cover_art = HeroCoverArtWindow(size=180)
        self.cover_art.clicked.connect(self.art_clicked.emit)
        sub_lbl = QLabel("MONITORING SOURCE A")
        sub_lbl.setStyleSheet("color: #707884; font-family: Monospace; font-size: 9px; font-weight: bold;")
        sub_lbl.setAlignment(Qt.AlignCenter)

        left_sec.addWidget(self.cover_art, 0, Qt.AlignCenter)
        left_sec.addWidget(sub_lbl, 0, Qt.AlignCenter)

        # 16-Band Studio Spectrum Analyzer
        self.spectrum = WinampSpectrumAnalyzer(bands_count=16, theme_mode="cyan")
        self.spectrum.setFixedHeight(68)
        left_sec.addWidget(self.spectrum)

        r_layout.addLayout(left_sec, 30)

        # Center Section (46% width): Dual Illuminated VU Meters + Telemetry Strip
        center_sec = QVBoxLayout()
        center_sec.setSpacing(8)

        top_brand = QLabel("MCINTOSH / NEVE SPEC  •  STUDIO MASTER RACK 1000")
        top_brand.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 10px; font-weight: bold;")
        center_sec.addWidget(top_brand)

        # Dual Large Illuminated Analog VU Meters with Warm Tungsten Backlighting
        self.twin_vu = DualStereoAnalogVUMeter()
        center_sec.addWidget(self.twin_vu)

        # Compact Recessed OLED/VFD Readout Strip
        vfd_strip = QFrame()
        vfd_strip.setStyleSheet("background: #080a0c; border: 1px solid #1c222a; border-radius: 6px; padding: 6px;")
        vfd_layout = QVBoxLayout(vfd_strip)
        vfd_layout.setSpacing(3)

        self.lbl_title = ClickableLabel("Track Title")
        self.lbl_title.clicked.connect(self.track_details_clicked.emit)
        self.lbl_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        self.lbl_artist_album = QLabel("Artist Name — Album")
        self.lbl_artist_album.setStyleSheet("color: #00f0ff; font-size: 11px;")

        scrub_row = QHBoxLayout()
        self.lbl_curr = QLabel("00:00")
        self.lbl_curr.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 10px; font-weight: bold;")
        self.slider_pos = RetroSlider(Qt.Horizontal, "#00f0ff")
        self.slider_pos.setRange(0, 1000)
        self.slider_pos.sliderMoved.connect(self.seek_moved.emit)
        self.lbl_total = QLabel("00:00")
        self.lbl_total.setStyleSheet("color: #607080; font-family: Monospace; font-size: 10px; font-weight: bold;")

        scrub_row.addWidget(self.lbl_curr)
        scrub_row.addWidget(self.slider_pos, 1)
        scrub_row.addWidget(self.lbl_total)

        vfd_layout.addWidget(self.lbl_title)
        vfd_layout.addWidget(self.lbl_artist_album)
        vfd_layout.addLayout(scrub_row)
        center_sec.addWidget(vfd_strip)

        r_layout.addLayout(center_sec, 46)

        # Right Section (24% width): Multi-Knobs, Multi-Buttons with LEDs & Master Gain
        right_sec = QVBoxLayout()
        right_sec.setAlignment(Qt.AlignCenter)
        right_sec.setSpacing(10)

        # Multi-Knobs: Bass & Treble Rack Preamp Dials
        rack_knobs = QHBoxLayout()
        rack_knobs.setSpacing(8)
        self.knob_bass = LabeledKnob("BASS", style_mode="black", size=48)
        self.knob_bass.set_value(0.60)
        self.knob_treble = LabeledKnob("TREBLE", style_mode="black", size=48)
        self.knob_treble.set_value(0.65)
        rack_knobs.addWidget(self.knob_bass)
        rack_knobs.addWidget(self.knob_treble)
        right_sec.addLayout(rack_knobs)

        # Master Gain Dial
        gain_box = QVBoxLayout()
        gain_box.setAlignment(Qt.AlignCenter)
        self.knob = RotaryKnob(style_mode="black", size=84)
        self.knob.valueChanged.connect(self.volume_changed.emit)
        gain_lbl = QLabel("MASTER GAIN")
        gain_lbl.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 9px; font-weight: bold;")
        gain_lbl.setAlignment(Qt.AlignCenter)
        gain_box.addWidget(self.knob, 0, Qt.AlignCenter)
        gain_box.addWidget(gain_lbl, 0, Qt.AlignCenter)
        right_sec.addLayout(gain_box)

        # Multi-Buttons with Status LEDs
        sw_led_row = QHBoxLayout()
        sw_led_row.setSpacing(4)
        self.btn_loudness = VintageButton("LOUD", has_led=True)
        self.btn_loudness.set_led(True, "#00f0ff")
        self.btn_subsonic = VintageButton("SUBSONIC", has_led=True)
        self.btn_subsonic.set_led(False, "#ffaa00")
        self.btn_mute = VintageButton("MUTE", has_led=True)
        self.btn_mute.set_led(False, "#ff4444")

        sw_led_row.addWidget(self.btn_loudness)
        sw_led_row.addWidget(self.btn_subsonic)
        sw_led_row.addWidget(self.btn_mute)
        right_sec.addLayout(sw_led_row)

        # Backlit Rackmount Transport Switches
        sw_row = QHBoxLayout()
        b_prev = VintageButton("|<")
        b_prev.clicked.connect(self.prev_clicked.emit)
        self.btn_play = VintageButton(">||", is_accent=True, has_led=True)
        self.btn_play.clicked.connect(self.play_clicked.emit)
        b_next = VintageButton(">|")
        b_next.clicked.connect(self.next_clicked.emit)

        sw_row.addWidget(b_prev)
        sw_row.addWidget(self.btn_play)
        sw_row.addWidget(b_next)
        right_sec.addLayout(sw_row)

        r_layout.addLayout(right_sec, 24)
        root.addWidget(rack)

    def set_track_info(self, title, artist, album, art_path):
        self.lbl_title.setText(title or "Unknown")
        self.lbl_artist_album.setText(f"{artist or 'Unknown'} — {album or 'Master'}")
        self.cover_art.set_artwork(art_path)


# -------------------------------------------------------------
# MASTER CONTAINER FOR THE 5 HARDWARE THEMES
# -------------------------------------------------------------
class PlayerDeckPage(QWidget):
    art_clicked = pyqtSignal()
    track_details_requested = pyqtSignal()
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    change_next_requested = pyqtSignal()
    glass_frosting_changed = pyqtSignal(int)
    rew_clicked = pyqtSignal()
    ff_clicked = pyqtSignal()
    seek_moved = pyqtSignal(int)
    volume_changed = pyqtSignal(float)
    library_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        # 0: Walkman Cassette
        self.walkman = WalkmanDeckView()
        self.walkman.art_clicked.connect(self.art_clicked.emit)
        self.walkman.track_details_clicked.connect(self.track_details_requested.emit)
        self.walkman.play_clicked.connect(self.play_clicked.emit)
        self.walkman.pause_clicked.connect(self.pause_clicked.emit)
        self.walkman.stop_clicked.connect(self.stop_clicked.emit)
        self.walkman.prev_clicked.connect(self.prev_clicked.emit)
        self.walkman.next_clicked.connect(self.next_clicked.emit)
        self.walkman.rew_clicked.connect(self.rew_clicked.emit)
        self.walkman.ff_clicked.connect(self.ff_clicked.emit)
        self.walkman.seek_moved.connect(self.seek_moved.emit)
        self.walkman.volume_changed.connect(self.volume_changed.emit)
        self.stack.addWidget(self.walkman)

        # 1: Glass Player
        self.glass = GlassHiFiDeckView()
        self.glass.art_clicked.connect(self.art_clicked.emit)
        self.glass.track_details_clicked.connect(self.track_details_requested.emit)
        self.glass.play_clicked.connect(self.play_clicked.emit)
        self.glass.prev_clicked.connect(self.prev_clicked.emit)
        self.glass.next_clicked.connect(self.next_clicked.emit)
        self.glass.change_next_clicked.connect(self.change_next_requested.emit)
        self.glass.glass_frosting_changed.connect(self.glass_frosting_changed.emit)
        self.glass.seek_moved.connect(self.seek_moved.emit)
        self.glass.volume_changed.connect(self.volume_changed.emit)
        self.stack.addWidget(self.glass)

        # 2: iPod Classic (Vertical Interface!)
        self.ipod = IPodDeckView()
        self.ipod.art_clicked.connect(self.art_clicked.emit)
        self.ipod.track_details_clicked.connect(self.track_details_requested.emit)
        self.ipod.play_pause_clicked.connect(self.play_clicked.emit)
        self.ipod.prev_clicked.connect(self.prev_clicked.emit)
        self.ipod.next_clicked.connect(self.next_clicked.emit)
        self.ipod.wheel_spun.connect(lambda s: self.rew_clicked.emit() if s < 0 else self.ff_clicked.emit())
        self.ipod.click_wheel.menu_clicked.connect(self.library_requested.emit)
        self.ipod.menu_action_requested.connect(lambda action: self.library_requested.emit() if action == "Music" else None)
        self.ipod.seek_moved.connect(self.seek_moved.emit)
        self.ipod.volume_changed.connect(self.volume_changed.emit)
        self.stack.addWidget(self.ipod)

        # 3: Vinyl Turntable
        self.vinyl = VinylTurntableDeckView()
        self.vinyl.art_clicked.connect(self.art_clicked.emit)
        self.vinyl.track_details_clicked.connect(self.track_details_requested.emit)
        self.vinyl.play_clicked.connect(self.play_clicked.emit)
        self.vinyl.prev_clicked.connect(self.prev_clicked.emit)
        self.vinyl.next_clicked.connect(self.next_clicked.emit)
        self.vinyl.seek_moved.connect(self.seek_moved.emit)
        self.vinyl.volume_changed.connect(self.volume_changed.emit)
        self.stack.addWidget(self.vinyl)

        # 4: Studio Rack
        self.studio = StudioHiFiRackDeckView()
        self.studio.art_clicked.connect(self.art_clicked.emit)
        self.studio.track_details_clicked.connect(self.track_details_requested.emit)
        self.studio.play_clicked.connect(self.play_clicked.emit)
        self.studio.prev_clicked.connect(self.prev_clicked.emit)
        self.studio.next_clicked.connect(self.next_clicked.emit)
        self.studio.seek_moved.connect(self.seek_moved.emit)
        self.studio.volume_changed.connect(self.volume_changed.emit)
        self.stack.addWidget(self.studio)

        layout.addWidget(self.stack)
        self._animations_enabled = True
        self._is_playing = False
        self.motion_overlay = ThemeMotionOverlay(self)
        self.motion_overlay.setGeometry(self.rect())
        self.motion_overlay.set_accent("#72e6ff")
        self.motion_overlay.hide()  # Strictly hidden for opaque hardware skins

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "motion_overlay"):
            self.motion_overlay.setGeometry(self.rect())
            if self.motion_overlay.isVisible():
                self.motion_overlay.raise_()

    def switch_theme(self, theme_key):
        mapping = {"walkman": 0, "glass": 1, "ipod": 2, "vinyl": 3, "studio_rack": 4}
        idx = mapping.get(theme_key, 0)
        self.stack.setCurrentIndex(idx)
        self._update_deck_track_info(idx)
        # Strictly isolate liquid glass shimmer overlay to the Glass Hi-Fi Deck
        if theme_key == "glass":
            self.motion_overlay.set_accent("#72e6ff")
            self.motion_overlay.show()
            self.motion_overlay.raise_()
            self.motion_overlay.set_motion_state(self._animations_enabled, self._is_playing)
        else:
            self.motion_overlay.hide()
            self.motion_overlay.set_motion_state(False, False)

    def set_glass_transparency(self, percent):
        self.glass.set_glass_transparency(percent)

    def set_glass_frosting(self, percent):
        self.glass.set_glass_frosting(percent)

    def set_up_next_info(self, title, artist=""):
        self.glass.set_up_next_info(title, artist)

    def set_animations_enabled(self, enabled):
        self._animations_enabled = bool(enabled)
        self.walkman.set_animations_enabled(enabled)
        self.glass.set_animations_enabled(enabled)
        self.glass.spectrum.set_animations_enabled(enabled)
        self.ipod.spectrum.set_animations_enabled(enabled)
        self.vinyl.turntable.set_animations_enabled(enabled)
        self.studio.spectrum.set_animations_enabled(enabled)
        self.studio.twin_vu.set_animations_enabled(enabled)
        if self.stack.currentIndex() == 1:
            self.motion_overlay.set_motion_state(self._animations_enabled, self._is_playing)
        else:
            self.motion_overlay.set_motion_state(False, False)

    def set_track_info(self, meta):
        self._last_meta = dict(meta) if meta else {}
        self._update_deck_track_info(self.stack.currentIndex())

    def _update_deck_track_info(self, idx):
        if not hasattr(self, "_last_meta") or not self._last_meta:
            return
        meta = self._last_meta
        title = meta.get("title", "")
        artist = meta.get("artist", "")
        album = meta.get("album", "")
        art_path = meta.get("artwork_path")

        if idx == 0:  # Walkman
            self.walkman.cover_window.set_artwork(art_path)
            self.walkman.cassette_deck.set_artwork(art_path)
            self.walkman.marquee.set_text(f"{artist} - {title}")
        elif idx == 1:  # Glass Player
            self.glass.set_track_info(title, artist, album, art_path)
        elif idx == 2:  # iPod
            self.ipod.set_track_info(title, artist, album, art_path)
        elif idx == 3:  # Vinyl
            self.vinyl.set_track_info(title, artist, art_path)
        elif idx == 4:  # Studio Rack
            self.studio.set_track_info(title, artist, album, art_path)

    def set_playing_state(self, is_playing):
        self._is_playing = bool(is_playing)
        if self.stack.currentIndex() == 1:
            self.motion_overlay.set_motion_state(self._animations_enabled, self._is_playing)
        else:
            self.motion_overlay.set_motion_state(False, False)
        # Walkman
        self.walkman.cassette_deck.set_playing(is_playing)
        self.walkman.status_led.setText("[PLAYING]" if is_playing else "[STOPPED]")
        self.walkman.btn_play.set_led(is_playing, "#39ff14")
        self.walkman.btn_pause.set_led(not is_playing and is_playing is not None, "#ffaa00")

        # Glass Player
        self.glass.btn_play.setText("||" if is_playing else ">")
        self.glass.set_playing_state(is_playing)
        self.glass.spectrum.set_playing(is_playing)

        # iPod
        self.ipod.lbl_play_state.setText(">" if is_playing else "||")
        self.ipod.spectrum.set_playing(is_playing)

        # Vinyl
        self.vinyl.turntable.set_playing(is_playing)
        self.vinyl.btn_play.set_led(is_playing, "#ffaa00")

        # Studio
        self.studio.btn_play.set_led(is_playing, "#00f0ff")
        self.studio.spectrum.set_playing(is_playing)

    def update_position(self, pos_sec, dur_sec):
        # Walkman
        self.walkman.seven_seg.set_time(pos_sec)
        self.walkman.lbl_curr.setText(f"{int(pos_sec // 60):02d}:{int(pos_sec % 60):02d}")
        if dur_sec > 0:
            val = int((pos_sec / dur_sec) * 1000)
            self.walkman.tape_slider.blockSignals(True)
            self.walkman.tape_slider.setValue(val)
            self.walkman.tape_slider.blockSignals(False)
            self.walkman.lbl_total.setText(f"{int(dur_sec // 60):02d}:{int(dur_sec % 60):02d}")
            self.walkman.cassette_deck.set_progress(pos_sec / dur_sec)

            # Glass Player
            self.glass.slider_pos.blockSignals(True)
            self.glass.slider_pos.setValue(val)
            self.glass.slider_pos.blockSignals(False)
            self.glass.lbl_curr.setText(f"{int(pos_sec // 60):02d}:{int(pos_sec % 60):02d}")
            self.glass.lbl_total.setText(f"{int(dur_sec // 60):02d}:{int(dur_sec % 60):02d}")

            # iPod
            self.ipod.slider_pos.blockSignals(True)
            self.ipod.slider_pos.setValue(val)
            self.ipod.slider_pos.blockSignals(False)
            self.ipod.lbl_curr.setText(f"{int(pos_sec // 60):02d}:{int(pos_sec % 60):02d}")
            rem = max(0, int(dur_sec - pos_sec))
            self.ipod.lbl_rem.setText(f"-{int(rem // 60):02d}:{int(rem % 60):02d}")

            # Vinyl
            self.vinyl.slider_pos.blockSignals(True)
            self.vinyl.slider_pos.setValue(val)
            self.vinyl.slider_pos.blockSignals(False)
            self.vinyl.lbl_curr.setText(f"{int(pos_sec // 60):02d}:{int(pos_sec % 60):02d}")
            self.vinyl.lbl_total.setText(f"{int(dur_sec // 60):02d}:{int(dur_sec % 60):02d}")

            # Studio
            self.studio.slider_pos.blockSignals(True)
            self.studio.slider_pos.setValue(val)
            self.studio.slider_pos.blockSignals(False)
            self.studio.lbl_curr.setText(f"{int(pos_sec // 60):02d}:{int(pos_sec % 60):02d}")
            self.studio.lbl_total.setText(f"{int(dur_sec // 60):02d}:{int(dur_sec % 60):02d}")

    def update_levels(self, l_val, r_val):
        self.walkman.vu_meter.set_levels(l_val, r_val)
        self.studio.twin_vu.set_levels(l_val, r_val)
        if hasattr(self.studio, 'spectrum'):
            self.studio.spectrum.set_levels(l_val, r_val)
        if hasattr(self.ipod, 'spectrum'):
            self.ipod.spectrum.set_levels(l_val, r_val)
        if hasattr(self.ipod, 'vu_meter'):
            self.ipod.vu_meter.set_levels(l_val, r_val)
        self.glass.spectrum.set_levels(l_val, r_val)
        if hasattr(self.vinyl, 'vu_meter'):
            self.vinyl.vu_meter.set_levels(l_val, r_val)
