import math
import random
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, QFont, QPainterPath
)


class WinampSpectrumAnalyzer(QWidget):
    """
    Iconic Winamp-style 16-band audio spectrum analyzer & oscilloscope.
    Features:
    - 16 discrete frequency bars with segmented phosphor LEDs
    - Ballistic peak-hold indicators with smooth gravitational decay
    - Toggleable Oscilloscope wave mode
    - Recessed Hi-Fi dark visor frame with grid reticle and theme glow
    """
    def __init__(self, bands_count=16, theme_mode="winamp", parent=None):
        super().__init__(parent)
        self.bands_count = bands_count
        self.theme_mode = theme_mode  # "winamp", "cyan", "amber", "gold", "silver"
        self._mode = "bars"  # "bars" or "oscilloscope"

        self._level_l = 0.0
        self._level_r = 0.0
        self._is_playing = False
        self._animations_enabled = True

        # Band values (0.0 to 1.0) and peak hold values
        self._band_values = [0.05] * self.bands_count
        self._band_peaks = [0.05] * self.bands_count
        self._peak_decay_speeds = [0.015] * self.bands_count

        # Oscilloscope points
        self._osc_points = [0.0] * 64

        self.setMinimumHeight(64)
        self.setMinimumWidth(160)
        self.setCursor(Qt.PointingHandCursor)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_physics)
        self._timer.setInterval(50)  # 20 FPS keeps the display smooth with less redraw work

    def set_playing(self, is_playing):
        self._is_playing = bool(is_playing)
        self._sync_timer()

    def _sync_timer(self):
        if self._animations_enabled and self.isVisible() and self._is_playing:
            self._timer.start()
        else:
            self._timer.stop()

    def set_animations_enabled(self, enabled):
        self._animations_enabled = bool(enabled)
        self._sync_timer()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def set_levels(self, l_val, r_val):
        self._level_l = max(0.0, min(1.0, float(l_val)))
        self._level_r = max(0.0, min(1.0, float(r_val)))

    def set_theme_mode(self, mode):
        self.theme_mode = mode
        self.update()

    def toggle_mode(self):
        self._mode = "oscilloscope" if self._mode == "bars" else "bars"
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_mode()
        super().mousePressEvent(event)

    def _update_physics(self):
        avg_level = (self._level_l + self._level_r) / 2.0
        if not self._is_playing:
            avg_level = 0.0

        for i in range(self.bands_count):
            if self._is_playing and avg_level > 0.01:
                # Frequency distribution: bass (bands 0-3), mids (4-9), highs (10-15)
                norm_idx = i / float(self.bands_count - 1)
                # Realistic music frequency curve (weighted toward punchy bass and mids)
                if norm_idx < 0.25:
                    weight = 1.15 * math.sin(norm_idx * math.pi * 2 + 0.2)
                elif norm_idx < 0.65:
                    weight = 0.95 * math.cos((norm_idx - 0.25) * math.pi)
                else:
                    weight = 0.70 * (1.0 - norm_idx * 0.4)

                jitter = random.uniform(0.75, 1.25)
                target = avg_level * weight * jitter
                target = max(0.06, min(0.98, target))
            else:
                target = 0.04

            # Attack / decay for bars
            if target > self._band_values[i]:
                self._band_values[i] += (target - self._band_values[i]) * 0.6  # Fast attack
            else:
                self._band_values[i] -= (self._band_values[i] - target) * 0.25  # Smooth decay

            # Peak hold logic with gravity
            if self._band_values[i] >= self._band_peaks[i]:
                self._band_peaks[i] = self._band_values[i]
                self._peak_decay_speeds[i] = 0.012
            else:
                self._band_peaks[i] = max(0.04, self._band_peaks[i] - self._peak_decay_speeds[i])
                self._peak_decay_speeds[i] += 0.003  # Accelerating gravity

        # Update oscilloscope wave
        if self._mode == "oscilloscope":
            for j in range(len(self._osc_points)):
                if self._is_playing and avg_level > 0.01:
                    freq = 3.0 + (avg_level * 4.0)
                    phase = (j / float(len(self._osc_points))) * math.pi * 2.0 * freq
                    noise = random.uniform(-0.15, 0.15)
                    self._osc_points[j] = math.sin(phase) * (avg_level * 0.85) + noise
                else:
                    self._osc_points[j] = 0.0

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Outer Dark Recessed Chassis Bay
        painter.setPen(QPen(QColor(24, 28, 34), 1))
        painter.setBrush(QColor(8, 10, 13))
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 4, 4)

        # Subtle dark glass inner shadow
        top_shade = QLinearGradient(0, 1, 0, 12)
        top_shade.setColorAt(0.0, QColor(0, 0, 0, 160))
        top_shade.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(top_shade)
        painter.drawRoundedRect(QRectF(2, 2, w - 4, 10), 3, 3)

        # 2. Scope Reticle / Grid Lines
        painter.setPen(QPen(QColor(22, 28, 36, 120), 1, Qt.DotLine))
        # Draw 3 horizontal grid lines
        for r_y in [h * 0.25, h * 0.50, h * 0.75]:
            painter.drawLine(QPointF(4, r_y), QPointF(w - 4, r_y))

        # Mode Indicator in top-right
        painter.setFont(QFont("Monospace", 6, QFont.Bold))
        painter.setPen(QColor(90, 100, 115))
        painter.drawText(QRectF(w - 74, 3, 70, 12), Qt.AlignRight, "SCOPE" if self._mode == "oscilloscope" else "SPECTRUM")

        # 3. Draw Visualizer Mode
        inner_rect = QRectF(6, 12, w - 12, h - 16)
        if self._mode == "oscilloscope":
            self._draw_oscilloscope(painter, inner_rect)
        else:
            self._draw_spectrum_bars(painter, inner_rect)

    def _draw_oscilloscope(self, painter, rect):
        pts = self._osc_points
        n = len(pts)
        if n < 2:
            return

        mid_y = rect.center().y()
        amp_h = rect.height() * 0.44

        path = QPainterPath()
        step_x = rect.width() / float(n - 1)

        for i, val in enumerate(pts):
            px = rect.x() + i * step_x
            py = mid_y - (val * amp_h)
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)

        # Glow line
        accent = self._get_accent_color()
        glow_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 90), 3)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        core_pen = QPen(accent, 1.5)
        painter.setPen(core_pen)
        painter.drawPath(path)

    def _draw_spectrum_bars(self, painter, rect):
        n = self.bands_count
        spacing = 2.0
        total_spacing = spacing * (n - 1)
        bar_w = max(2.5, (rect.width() - total_spacing) / float(n))

        num_segments = 14
        seg_gap = 1.0
        seg_h = max(1.5, (rect.height() - (num_segments - 1) * seg_gap) / float(num_segments))

        for i in range(n):
            bx = rect.x() + i * (bar_w + spacing)
            val = self._band_values[i]
            lit_segments = int(val * num_segments)
            peak_val = self._band_peaks[i]
            peak_seg = int(peak_val * num_segments)

            # Draw discrete LED segments from bottom to top
            for s in range(num_segments):
                sy = (rect.bottom() - (s + 1) * (seg_h + seg_gap))
                is_lit = (s <= lit_segments)
                ratio = s / float(num_segments)

                col = self._get_segment_color(ratio, is_lit)
                painter.setPen(Qt.NoPen)
                painter.setBrush(col)
                painter.drawRect(QRectF(bx, sy, bar_w, seg_h))

            # Draw falling peak hold cap
            if peak_seg > 0:
                cap_y = (rect.bottom() - (peak_seg + 1) * (seg_h + seg_gap))
                cap_col = self._get_peak_cap_color()
                painter.setBrush(cap_col)
                painter.drawRect(QRectF(bx, cap_y, bar_w, 1.8))

    def _get_segment_color(self, ratio, is_lit):
        if self.theme_mode == "winamp":
            if ratio < 0.60:
                return QColor(46, 204, 64) if is_lit else QColor(16, 50, 22, 100)
            elif ratio < 0.85:
                return QColor(255, 170, 0) if is_lit else QColor(50, 36, 10, 100)
            else:
                return QColor(255, 50, 50) if is_lit else QColor(60, 15, 15, 100)
        elif self.theme_mode == "cyan":
            if ratio < 0.75:
                return QColor(0, 240, 255) if is_lit else QColor(0, 45, 55, 100)
            else:
                return QColor(255, 60, 120) if is_lit else QColor(55, 15, 30, 100)
        elif self.theme_mode == "gold":
            if ratio < 0.80:
                return QColor(240, 195, 75) if is_lit else QColor(50, 40, 15, 100)
            else:
                return QColor(255, 75, 40) if is_lit else QColor(60, 20, 12, 100)
        elif self.theme_mode == "amber":
            if ratio < 0.75:
                return QColor(255, 165, 0) if is_lit else QColor(55, 35, 8, 100)
            else:
                return QColor(255, 50, 50) if is_lit else QColor(60, 15, 15, 100)
        else: # silver / blue
            if ratio < 0.75:
                return QColor(0, 140, 255) if is_lit else QColor(10, 35, 60, 100)
            else:
                return QColor(255, 255, 255) if is_lit else QColor(60, 60, 60, 100)

    def _get_peak_cap_color(self):
        if self.theme_mode == "winamp":
            return QColor(255, 255, 255)
        elif self.theme_mode == "cyan":
            return QColor(200, 255, 255)
        elif self.theme_mode == "gold":
            return QColor(255, 240, 180)
        elif self.theme_mode == "amber":
            return QColor(255, 220, 120)
        else:
            return QColor(255, 255, 255)

    def _get_accent_color(self):
        if self.theme_mode == "cyan":
            return QColor(0, 240, 255)
        elif self.theme_mode == "gold":
            return QColor(240, 195, 75)
        elif self.theme_mode == "amber":
            return QColor(255, 165, 0)
        else:
            return QColor(46, 204, 64)
