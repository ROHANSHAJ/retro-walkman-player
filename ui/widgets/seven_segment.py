from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF, QFont


THEMES = {
    "amber": {
        "name": "Walkman Amber",
        "lit": QColor(255, 176, 0),
        "unlit": QColor(50, 35, 5, 80),
        "glow": QColor(255, 176, 0, 70),
        "bg": QColor(14, 12, 10),
        "text": "#ffb000"
    },
    "cyan": {
        "name": "Hi-Fi Cyan (VFD)",
        "lit": QColor(0, 240, 255),
        "unlit": QColor(0, 50, 58, 80),
        "glow": QColor(0, 240, 255, 70),
        "bg": QColor(8, 16, 18),
        "text": "#00f0ff"
    },
    "green": {
        "name": "Vintage Green",
        "lit": QColor(57, 255, 20),
        "unlit": QColor(10, 50, 8, 80),
        "glow": QColor(57, 255, 20, 70),
        "bg": QColor(8, 16, 8),
        "text": "#39ff14"
    },
    "red": {
        "name": "Studio Red",
        "lit": QColor(255, 45, 45),
        "unlit": QColor(55, 10, 10, 80),
        "glow": QColor(255, 45, 45, 70),
        "bg": QColor(18, 8, 8),
        "text": "#ff2d2d"
    }
}

# Bitmask segments: A, B, C, D, E, F, G
# 0bGFEDCBA
DIGIT_MAP = {
    '0': 0b0111111,
    '1': 0b0000110,
    '2': 0b1011011,
    '3': 0b1001111,
    '4': 0b1100110,
    '5': 0b1101101,
    '6': 0b1111101,
    '7': 0b0000111,
    '8': 0b1111111,
    '9': 0b1101111,
    '-': 0b1000000,
    ' ': 0b0000000,
    'E': 0b1111001,
    'r': 0b1010000,
    'o': 0b1011100,
    'P': 0b1110011,
    'L': 0b0111000,
    'A': 0b1110111,
    'Y': 0b1101110,
    't': 0b1111000,
}


class SevenSegmentDigit(QWidget):
    """
    Crisp vector-rendered single 7-segment digit with authentic
    trapezoid bevels and unlit phosphor ghosting.
    """
    def __init__(self, char='0', theme_key="amber", parent=None):
        super().__init__(parent)
        self._char = char
        self._theme_key = theme_key
        self.setFixedSize(18, 30)

    def set_char(self, char):
        if self._char != char:
            self._char = char
            self.update()

    def set_theme(self, theme_key):
        self._theme_key = theme_key
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        theme = THEMES.get(self._theme_key, THEMES["amber"])
        lit_color = theme["lit"]
        unlit_color = theme["unlit"]

        # Slight slant for authentic 7-seg italic look
        painter.translate(w * 0.1, 0)
        usable_w = w * 0.8
        usable_h = h

        # Calculate segment proportions
        t = max(2.5, usable_w * 0.17)  # segment thickness
        gap = max(1.0, t * 0.18)

        mask = DIGIT_MAP.get(str(self._char), 0b0000000)

        # Segment A (top)
        self._draw_h_seg(painter, t, 0, usable_w - t, t, mask & 0b0000001, lit_color, unlit_color, gap)
        # Segment B (top-right)
        self._draw_v_seg(painter, usable_w - t, t, usable_w, usable_h / 2, mask & 0b0000010, lit_color, unlit_color, gap)
        # Segment C (bottom-right)
        self._draw_v_seg(painter, usable_w - t, usable_h / 2, usable_w, usable_h - t, mask & 0b0000100, lit_color, unlit_color, gap)
        # Segment D (bottom)
        self._draw_h_seg(painter, t, usable_h - t, usable_w - t, usable_h, mask & 0b0001000, lit_color, unlit_color, gap)
        # Segment E (bottom-left)
        self._draw_v_seg(painter, 0, usable_h / 2, t, usable_h - t, mask & 0b0010000, lit_color, unlit_color, gap)
        # Segment F (top-left)
        self._draw_v_seg(painter, 0, t, t, usable_h / 2, mask & 0b0100000, lit_color, unlit_color, gap)
        # Segment G (middle)
        self._draw_h_seg(painter, t, (usable_h - t) / 2, usable_w - t, (usable_h + t) / 2, mask & 0b1000000, lit_color, unlit_color, gap)

    def _draw_h_seg(self, painter, x1, y1, x2, y2, is_lit, lit_col, unlit_col, gap):
        painter.setPen(Qt.NoPen)
        painter.setBrush(lit_col if is_lit else unlit_col)
        h = y2 - y1
        mid_y = (y1 + y2) / 2
        poly = QPolygonF([
            QPointF(x1 + gap, mid_y),
            QPointF(x1 + h / 2 + gap, y1),
            QPointF(x2 - h / 2 - gap, y1),
            QPointF(x2 - gap, mid_y),
            QPointF(x2 - h / 2 - gap, y2),
            QPointF(x1 + h / 2 + gap, y2),
        ])
        painter.drawPolygon(poly)

    def _draw_v_seg(self, painter, x1, y1, x2, y2, is_lit, lit_col, unlit_col, gap):
        painter.setPen(Qt.NoPen)
        painter.setBrush(lit_col if is_lit else unlit_col)
        w = x2 - x1
        mid_x = (x1 + x2) / 2
        poly = QPolygonF([
            QPointF(mid_x, y1 + gap),
            QPointF(x2, y1 + w / 2 + gap),
            QPointF(x2, y2 - w / 2 - gap),
            QPointF(mid_x, y2 - gap),
            QPointF(x1, y2 - w / 2 - gap),
            QPointF(x1, y1 + w / 2 + gap),
        ])
        painter.drawPolygon(poly)


class SevenSegmentColon(QWidget):
    def __init__(self, theme_key="amber", parent=None):
        super().__init__(parent)
        self._theme_key = theme_key
        self._lit = True
        self.setFixedSize(8, 30)

    def set_theme(self, theme_key):
        self._theme_key = theme_key
        self.update()

    def set_lit(self, lit):
        if self._lit != lit:
            self._lit = lit
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        theme = THEMES.get(self._theme_key, THEMES["amber"])
        color = theme["lit"] if self._lit else theme["unlit"]

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        r = 2.0
        cx = w / 2
        painter.drawEllipse(QPointF(cx, h * 0.35), r, r)
        painter.drawEllipse(QPointF(cx, h * 0.65), r, r)


class SevenSegmentDisplay(QWidget):
    """
    Compact, proportion-locked 7-segment digital time readout (MM:SS) with glowing glass bezel.
    """
    def __init__(self, theme_key="amber", parent=None):
        super().__init__(parent)
        self._theme_key = theme_key
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(3)

        self.d_min10 = SevenSegmentDigit('0', theme_key)
        self.d_min1 = SevenSegmentDigit('0', theme_key)
        self.colon = SevenSegmentColon(theme_key)
        self.d_sec10 = SevenSegmentDigit('0', theme_key)
        self.d_sec1 = SevenSegmentDigit('0', theme_key)

        layout.addStretch()
        layout.addWidget(self.d_min10)
        layout.addWidget(self.d_min1)
        layout.addWidget(self.colon)
        layout.addWidget(self.d_sec10)
        layout.addWidget(self.d_sec1)
        layout.addStretch()

    def set_time(self, seconds):
        sec = max(0, int(seconds))
        mins = min(99, sec // 60)
        rem_sec = sec % 60

        m_str = f"{mins:02d}"
        s_str = f"{rem_sec:02d}"

        self.d_min10.set_char(m_str[0])
        self.d_min1.set_char(m_str[1])
        self.d_sec10.set_char(s_str[0])
        self.d_sec1.set_char(s_str[1])

    def set_theme(self, theme_key):
        self._theme_key = theme_key
        self.d_min10.set_theme(theme_key)
        self.d_min1.set_theme(theme_key)
        self.colon.set_theme(theme_key)
        self.d_sec10.set_theme(theme_key)
        self.d_sec1.set_theme(theme_key)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        theme = THEMES.get(self._theme_key, THEMES["amber"])

        # Dark recessed LCD/VFD glass background
        painter.setPen(QPen(QColor(50, 55, 60), 1.5))
        painter.setBrush(theme["bg"])
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        painter.drawRoundedRect(r, 6, 6)

        # Subtle inner top shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 90))
        painter.drawRoundedRect(QRectF(2, 2, self.width() - 4, 8), 4, 4)


class RetroMarquee(QWidget):
    """
    Scrolling retro dot-matrix / LED text banner for Track Title, Artist,
    and format stats.
    """
    clicked = pyqtSignal()

    def __init__(self, text="RETRO WALKMAN STEREO", theme_key="amber", parent=None):
        super().__init__(parent)
        self._text = text
        self._theme_key = theme_key
        self._offset = 0
        self._animations_enabled = True
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(60)

    def set_text(self, text):
        self._text = text or "READY"
        self._offset = 0
        self.update()
        self._sync_animation()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_theme(self, theme_key):
        self._theme_key = theme_key
        self.update()

    def set_animations_enabled(self, enabled):
        self._animations_enabled = bool(enabled)
        self._sync_animation()

    def _sync_animation(self):
        text_width = self.fontMetrics().horizontalAdvance(f"  ***  {self._text}  ***  ")
        if self._animations_enabled and self.isVisible() and text_width > self.width():
            self._timer.start()
        else:
            self._timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_animation()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_animation()

    def _tick(self):
        self._offset += 1.5
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        theme = THEMES.get(self._theme_key, THEMES["amber"])

        # Beveled display slot
        painter.setPen(QPen(QColor(40, 45, 50), 1))
        painter.setBrush(theme["bg"])
        painter.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 4, 4)

        painter.setFont(QFont("Monospace", 9, QFont.Bold))
        painter.setPen(theme["lit"])

        full_str = f"  ***  {self._text}  ***  "
        fm = painter.fontMetrics()
        str_w = fm.horizontalAdvance(full_str)
        if str_w <= 0:
            str_w = 1

        x = -(self._offset % str_w)
        while x < self.width():
            painter.drawText(int(x), int(self.height() * 0.7), full_str)
            x += str_w
