from PyQt5.QtWidgets import QPushButton, QSlider, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QRadialGradient, QPainterPath, QFont


class VintageButton(QPushButton):
    """
    Tactile vintage mechanical cassette deck pushbutton with brushed metallic
    finish, beveled edges, tactile depression, and optional recessed status LED.
    """
    def __init__(self, text, icon_str="", is_accent=False, has_led=False, parent=None):
        label = f"{icon_str} {text}".strip() if icon_str else text
        super().__init__(label, parent)
        self.is_accent = is_accent
        self.has_led = has_led
        self.led_on = False
        self.led_color = QColor(255, 176, 0)
        self._liquid_glass = False
        self._glass_transparency = 30
        self.setMinimumSize(54, 38)
        self.setFont(QFont("Sans-Serif", 8, QFont.Bold))
        self.setCursor(Qt.PointingHandCursor)

    def set_led(self, state, color=None):
        self.led_on = bool(state)
        if color:
            self.led_color = QColor(color)
        self.update()

    def set_liquid_glass(self, enabled=True, transparency=None):
        self._liquid_glass = bool(enabled)
        if transparency is not None:
            self._glass_transparency = max(0, min(100, int(transparency)))
        self.update()

    def set_glass_transparency(self, transparency):
        self._glass_transparency = max(0, min(100, int(transparency)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.38)

        w = self.width()
        h = self.height()
        is_down = self.isDown() or self.isChecked()

        draw_y = 2 if is_down else 0
        draw_h = h - 2

        if self._liquid_glass:
            opacity = 1.0 - self._glass_transparency / 100.0
            fill_alpha = int(round(220 * (opacity ** 1.35)))
            crest_alpha = max(95, round(235 * opacity))
            bounds = QRectF(2, draw_y + 1, w - 4, draw_h - 2)
            corner_r = min(12.0, bounds.height() / 2.0)
            shape = QPainterPath()
            shape.addRoundedRect(bounds, corner_r, corner_r)

            # 1. Base Liquid Glass Volume & Meniscus Glare (clipped to pill)
            glass = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
            glass.setColorAt(0.0, QColor(60, 85, 110, round(fill_alpha * 0.90)))
            glass.setColorAt(0.45, QColor(30, 46, 60, fill_alpha))
            glass.setColorAt(1.0, QColor(12, 18, 26, round(fill_alpha * 0.95)))

            glare_h = bounds.height() * 0.48
            glare = QLinearGradient(bounds.left(), bounds.top(), bounds.left(), bounds.top() + glare_h)
            glare.setColorAt(0.0, QColor(255, 255, 255, round(65 * opacity)))
            glare.setColorAt(1.0, QColor(200, 240, 255, 0))

            painter.save()
            painter.setClipPath(shape)
            if fill_alpha > 0:
                painter.fillPath(shape, QBrush(glass))
            painter.fillRect(QRectF(bounds.left(), bounds.top(), bounds.width(), glare_h), QBrush(glare))
            painter.restore()

            # 3. Snell's Law Refraction Rim
            rim = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
            rim.setColorAt(0.0, QColor(255, 255, 255, crest_alpha))
            rim.setColorAt(0.35, QColor(114, 230, 255, round(crest_alpha * 0.65)))
            rim.setColorAt(1.0, QColor(0, 0, 0, int(round(180 * opacity))))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QBrush(rim), 1.2))
            painter.drawPath(shape)

            if self.has_led:
                led_pos = QPointF(bounds.left() + 10, bounds.center().y())
                if self.led_on:
                    # Glowing LED jewel with halo
                    halo = QRadialGradient(led_pos, 5.0)
                    halo.setColorAt(0.0, self.led_color)
                    halo.setColorAt(1.0, QColor(self.led_color.red(), self.led_color.green(), self.led_color.blue(), 0))
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(halo)
                    painter.drawEllipse(led_pos, 5.0, 5.0)

                    jewel = QRadialGradient(led_pos, 2.8)
                    jewel.setColorAt(0.0, QColor(255, 255, 255))
                    jewel.setColorAt(0.6, self.led_color)
                    jewel.setColorAt(1.0, self.led_color.darker(140))
                    painter.setBrush(jewel)
                    painter.drawEllipse(led_pos, 2.8, 2.8)
                else:
                    painter.setPen(QPen(QColor(10, 18, 24), 1))
                    painter.setBrush(QColor(35, 50, 60))
                    painter.drawEllipse(led_pos, 2.5, 2.5)

            painter.setFont(self.font())
            painter.setPen(QColor(255, 255, 255) if not is_down else QColor(114, 230, 255))
            txt_rect = bounds.adjusted(16 if self.has_led else 0, 0, -4, 0)
            painter.drawText(txt_rect, Qt.AlignCenter, self.text())
            return

        # Outer bezel shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(10, 12, 14))
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 1), 4, 4)

        # Brushed metal gradient
        grad = QLinearGradient(0, draw_y, 0, draw_y + draw_h)
        if self.is_accent:
            if is_down:
                grad.setColorAt(0.0, QColor(180, 80, 0))
                grad.setColorAt(1.0, QColor(220, 110, 10))
            else:
                grad.setColorAt(0.0, QColor(230, 115, 10))
                grad.setColorAt(0.5, QColor(200, 95, 0))
                grad.setColorAt(1.0, QColor(160, 70, 0))
        else:
            if is_down:
                grad.setColorAt(0.0, QColor(35, 38, 42))
                grad.setColorAt(1.0, QColor(50, 54, 60))
            else:
                grad.setColorAt(0.0, QColor(75, 80, 88))
                grad.setColorAt(0.4, QColor(55, 59, 66))
                grad.setColorAt(1.0, QColor(42, 45, 50))

        painter.setPen(QPen(QColor(90, 95, 105) if not is_down else QColor(30, 32, 36), 1))
        painter.setBrush(grad)
        painter.drawRoundedRect(QRectF(2, draw_y + 1, w - 4, draw_h - 2), 4, 4)

        # Top metallic specular highlight if not pressed
        if not is_down:
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.drawLine(QPointF(4, draw_y + 2), QPointF(w - 4, draw_y + 2))

        # Status LED dot if enabled
        if self.has_led:
            led_x = 8
            led_y = draw_y + 6
            painter.setPen(QPen(QColor(20, 20, 20), 1))
            if self.led_on:
                painter.setBrush(self.led_color)
            else:
                painter.setBrush(QColor(40, 25, 10))
            painter.drawEllipse(QPointF(led_x, led_y), 2.5, 2.5)

        # Text label
        painter.setFont(self.font())
        if self.is_accent:
            painter.setPen(QColor(255, 255, 255))
        else:
            painter.setPen(QColor(220, 225, 230) if not is_down else QColor(180, 185, 190))

        text_rect = QRectF(2, draw_y + 1, w - 4, draw_h - 2)
        painter.drawText(text_rect, Qt.AlignCenter, self.text())


class RetroSlider(QSlider):
    """
    Styled progress scrubber / volume slider with glowing track and
    knurled metallic thumb. Supports CLICK-TO-JUMP seeking instantly!
    """
    def __init__(self, orientation=Qt.Horizontal, glow_color="#ffb000", parent=None):
        super().__init__(orientation, parent)
        self.glow_color = glow_color
        self.setCursor(Qt.PointingHandCursor)
        self.apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Click directly jumps to that exact time instance
            new_val = self.minimum() + ((self.maximum() - self.minimum()) * event.x()) / max(1, self.width())
            self.setValue(int(new_val))
            self.sliderMoved.emit(int(new_val))
        super().mousePressEvent(event)

    def set_glow_color(self, hex_color):
        self.glow_color = hex_color
        self.apply_style()

    def apply_style(self):
        self.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 5px;
                background: #0f1114;
                border: 1px solid #282c32;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.glow_color};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d0d6de, stop:0.5 #8e95a0, stop:1 #585e68);
                border: 1px solid #16181b;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:0.5 #b5bbc6, stop:1 #7a808c);
            }}
        """)


class LabeledKnob(QWidget):
    """
    Compact hardware knob paired with silk-screened title label and indicator.
    """
    valueChanged = pyqtSignal(float)

    def __init__(self, title, style_mode="black", size=58, parent=None):
        super().__init__(parent)
        from ui.widgets.rotary_knob import RotaryKnob

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("color: #9aa4b2; font-family: Monospace; font-size: 9px; font-weight: bold; letter-spacing: 0.5px;")

        self.knob = RotaryKnob(style_mode=style_mode, size=size)
        self.knob.valueChanged.connect(self.valueChanged.emit)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.knob, 0, Qt.AlignCenter)

    def set_value(self, val):
        self.knob.set_value(val)

    def get_value(self):
        return self.knob.get_value()

    def set_style_mode(self, mode):
        self.knob.set_style_mode(mode)

