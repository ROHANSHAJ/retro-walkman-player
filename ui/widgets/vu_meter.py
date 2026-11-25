from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont


class StereoVUMeter(QWidget):
    """
    Vintage Hi-Fi stereo LED bar-graph VU meter with peak indicators.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setMinimumWidth(160)

        self._level_l = 0.0
        self._level_r = 0.0
        self._peak_l = 0.0
        self._peak_r = 0.0

    def set_levels(self, l_val, r_val):
        self._level_l = max(0.0, min(1.0, float(l_val)))
        self._level_r = max(0.0, min(1.0, float(r_val)))

        self._peak_l = max(self._level_l, self._peak_l * 0.96)
        self._peak_r = max(self._level_r, self._peak_r * 0.96)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Recessed background
        painter.setPen(QPen(QColor(40, 45, 50), 1))
        painter.setBrush(QColor(12, 14, 16))
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 4, 4)

        # Labels L and R
        painter.setFont(QFont("Monospace", 7, QFont.Bold))
        painter.setPen(QColor(160, 165, 170))
        painter.drawText(6, int(h * 0.42), "L")
        painter.drawText(6, int(h * 0.88), "R")

        meter_x = 22
        meter_w = w - meter_x - 8
        bar_h = (h - 10) / 2

        self._draw_bar(painter, meter_x, 3, meter_w, bar_h, self._level_l, self._peak_l)
        self._draw_bar(painter, meter_x, 5 + bar_h, meter_w, bar_h, self._level_r, self._peak_r)

    def _draw_bar(self, painter, x, y, width, height, level, peak):
        segments = 24
        seg_w = (width - (segments - 1) * 2) / segments
        lit_count = int(level * segments)
        peak_idx = int(peak * segments)

        for i in range(segments):
            seg_x = x + i * (seg_w + 2)
            ratio = i / float(segments)

            # Colors based on volume zone
            if ratio < 0.65:
                # Normal: Retro Green
                lit_col = QColor(40, 240, 60)
                unlit_col = QColor(10, 45, 15, 80)
            elif ratio < 0.85:
                # Warning: Warm Amber
                lit_col = QColor(255, 180, 0)
                unlit_col = QColor(50, 35, 5, 80)
            else:
                # Clip / Peak: Crimson Red
                lit_col = QColor(255, 40, 40)
                unlit_col = QColor(55, 10, 10, 80)

            is_lit = (i < lit_count) or (i == peak_idx and peak_idx > 0)
            painter.setPen(Qt.NoPen)
            painter.setBrush(lit_col if is_lit else unlit_col)
            painter.drawRoundedRect(QRectF(seg_x, y, seg_w, height), 1, 1)
