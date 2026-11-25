import math
import random
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QTimer
from PyQt5.QtGui import QPainter, QColor, QLinearGradient


class WaveformVisualizer(QWidget):
    """
    Dynamic live audio waveform / frequency spectrum visualizer widget
    reacting smoothly to playback dynamics and audio levels.
    """
    def __init__(self, bars_count=36, glow_color="#00f0ff", parent=None):
        super().__init__(parent)
        self.bars_count = bars_count
        self.glow_color = glow_color
        self._is_playing = False
        self._master_level = 0.0

        # Bar heights (0.0 to 1.0) and targets
        self._bars = [0.05] * self.bars_count
        self._targets = [0.05] * self.bars_count
        self.setFixedHeight(48)
        self.setMinimumWidth(180)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_step)
        self._timer.start(35)  # ~30 FPS

    def set_playing(self, playing):
        self._is_playing = bool(playing)

    def set_level(self, level_0_to_1):
        self._master_level = max(0.0, min(1.0, float(level_0_to_1)))

    def set_glow_color(self, hex_color):
        self.glow_color = hex_color
        self.update()

    def _animate_step(self):
        for i in range(self.bars_count):
            if self._is_playing:
                # Dynamic spectrum generation weighted by audio level
                # Lower index = bass, mid = vocals, high = treble
                freq_weight = math.sin((i / float(self.bars_count)) * math.pi)
                rand_flux = random.uniform(0.3, 1.0)
                target = (self._master_level * 0.7 + 0.3) * freq_weight * rand_flux
                self._targets[i] = max(0.08, min(1.0, target))
            else:
                self._targets[i] = 0.04

            # Smooth interpolation
            self._bars[i] += (self._targets[i] - self._bars[i]) * 0.35

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        bar_spacing = 2.5
        total_spacing = bar_spacing * (self.bars_count - 1)
        bar_w = max(2.0, (w - total_spacing) / self.bars_count)
        mid_y = h / 2.0

        # Gradient along height
        grad = QLinearGradient(0, 0, 0, h)
        accent = QColor(self.glow_color)
        grad.setColorAt(0.0, accent)
        grad.setColorAt(0.5, QColor(accent.red(), accent.green(), accent.blue(), 230))
        grad.setColorAt(1.0, QColor(accent.red() // 2, accent.green() // 2, accent.blue() // 2, 100))

        painter.setPen(Qt.NoPen)
        painter.setBrush(grad)

        for i in range(self.bars_count):
            x = i * (bar_w + bar_spacing)
            bar_h = max(3.0, self._bars[i] * h * 0.88)
            y = mid_y - (bar_h / 2.0)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), bar_w / 2.0, bar_w / 2.0)
