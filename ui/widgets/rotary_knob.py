import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QConicalGradient, QRadialGradient, QLinearGradient, QFont


class RotaryKnob(QWidget):
    """
    Realistic brushed-metal rotary jog dial / volume knob with knurled grip,
    concentric lathe reflections, indicator dot, and optional LED tick ring.
    Supports mouse dragging and mouse-wheel rotation.
    """
    valueChanged = pyqtSignal(float)  # 0.0 to 1.0

    def __init__(self, style_mode="gold", size=80, parent=None):
        super().__init__(parent)
        self.style_mode = style_mode  # "gold", "black", "silver", "cyan", or "amber" hardware finish
        self._value = 0.8
        self._is_dragging = False
        self._last_y = 0
        self.setFixedSize(size, size)
        self.setCursor(Qt.SizeVerCursor)

    def set_style_mode(self, mode):
        self.style_mode = mode
        self.update()

    def set_value(self, val_0_to_1):
        clamped = max(0.0, min(1.0, float(val_0_to_1)))
        if abs(self._value - clamped) > 0.001:
            self._value = clamped
            self.update()

    def get_value(self):
        return self._value

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._last_y = event.y()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            dy = self._last_y - event.y()
            self._last_y = event.y()
            step = dy / 120.0
            new_val = max(0.0, min(1.0, self._value + step))
            if new_val != self._value:
                self._value = new_val
                self.valueChanged.emit(self._value)
                self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 1200.0
        new_val = max(0.0, min(1.0, self._value + delta))
        if new_val != self._value:
            self._value = new_val
            self.valueChanged.emit(self._value)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.38)

        w = self.width()
        h = self.height()
        size = min(w, h)
        cx = w / 2
        cy = h / 2
        r = size * 0.42

        # 1. Outer Tick Ring (LEDs)
        total_ticks = 24
        start_angle = 135
        span_angle = 270
        lit_ticks = int(self._value * total_ticks)

        for i in range(total_ticks):
            frac = i / float(total_ticks - 1)
            angle_deg = start_angle + frac * span_angle
            angle_rad = math.radians(angle_deg)
            tx = cx + (r * 1.14) * math.cos(angle_rad)
            ty = cy + (r * 1.14) * math.sin(angle_rad)

            is_lit = i <= lit_ticks
            if is_lit:
                if self.style_mode == "gold":
                    tick_col = QColor(255, 190, 40)
                elif self.style_mode == "black":
                    tick_col = QColor(0, 240, 255)
                elif self.style_mode in ("cyan", "liquid_glass"):
                    tick_col = QColor(0, 240, 255)
                else:
                    tick_col = QColor(255, 80, 80)
            else:
                tick_col = QColor(30, 50, 65, 90) if self.style_mode in ("cyan", "liquid_glass") else QColor(40, 44, 50, 100)

            painter.setPen(Qt.NoPen)
            painter.setBrush(tick_col)
            painter.drawEllipse(QPointF(tx, ty), 2.2, 2.2)

        # 2. Outer Bezel / Shadow
        if self.style_mode in ("cyan", "liquid_glass"):
            # Circular liquid glass well with Snell's law refraction rim
            well_rim = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
            well_rim.setColorAt(0.0, QColor(255, 255, 255, 140))
            well_rim.setColorAt(0.5, QColor(114, 230, 255, 60))
            well_rim.setColorAt(1.0, QColor(0, 0, 0, 190))
            painter.setPen(QPen(QBrush(well_rim), 1.5))
            painter.setBrush(QColor(8, 14, 20, 220))
            painter.drawEllipse(QPointF(cx, cy), r, r)
        else:
            painter.setPen(QPen(QColor(15, 17, 20), 2))
            painter.setBrush(QColor(25, 28, 32))
            painter.drawEllipse(QPointF(cx, cy), r, r)

        # 3. Knob Face
        painter.save()
        painter.translate(cx, cy)

        if self.style_mode in ("cyan", "liquid_glass"):
            # Smoked liquid glass dome with Snell's law refraction
            inner_r = r * 0.88
            rad_body = QRadialGradient(0, -inner_r * 0.28, inner_r * 1.15)
            rad_body.setColorAt(0.0, QColor(70, 105, 135, 220))
            rad_body.setColorAt(0.35, QColor(35, 55, 72, 235))
            rad_body.setColorAt(0.75, QColor(16, 26, 36, 250))
            rad_body.setColorAt(1.0, QColor(8, 13, 18, 255))
            painter.setBrush(rad_body)

            # Circular Snell's law refraction crest
            rim_grad = QLinearGradient(-inner_r, -inner_r, inner_r, inner_r)
            rim_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
            rim_grad.setColorAt(0.35, QColor(180, 240, 255, 150))
            rim_grad.setColorAt(0.70, QColor(114, 230, 255, 90))
            rim_grad.setColorAt(1.0, QColor(0, 0, 0, 200))
            painter.setPen(QPen(QBrush(rim_grad), 1.3))
            painter.drawEllipse(QPointF(0, 0), inner_r, inner_r)

            # Inset knurled glass flutes (fine radial ticks etched beneath glass)
            painter.setPen(QPen(QColor(255, 255, 255, 32), 1))
            for flute_idx in range(18):
                f_rad = math.radians(flute_idx * 20.0)
                fx1 = (inner_r * 0.74) * math.cos(f_rad)
                fy1 = (inner_r * 0.74) * math.sin(f_rad)
                fx2 = (inner_r * 0.88) * math.cos(f_rad)
                fy2 = (inner_r * 0.88) * math.sin(f_rad)
                painter.drawLine(QPointF(fx1, fy1), QPointF(fx2, fy2))

            # Center Liquid Cap
            cap_r = inner_r * 0.50
            rad_cap = QRadialGradient(0, -cap_r * 0.2, cap_r)
            rad_cap.setColorAt(0.0, QColor(90, 130, 160, 200))
            rad_cap.setColorAt(0.6, QColor(22, 36, 48, 230))
            rad_cap.setColorAt(1.0, QColor(10, 16, 22, 255))
            painter.setBrush(rad_cap)
            painter.setPen(QPen(QColor(255, 255, 255, 60), 0.8))
            painter.drawEllipse(QPointF(0, 0), cap_r, cap_r)

            # Indicator Pip: Electric Cyan Glowing Jewel
            cur_angle_deg = start_angle + self._value * span_angle
            cur_rad = math.radians(cur_angle_deg)
            pip_x = (inner_r * 0.70) * math.cos(cur_rad)
            pip_y = (inner_r * 0.70) * math.sin(cur_rad)

            # Jewel glow halo
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 240, 255, 60))
            painter.drawEllipse(QPointF(pip_x, pip_y), 5.5, 5.5)

            # Jewel core
            jewel = QRadialGradient(pip_x, pip_y, 3.2)
            jewel.setColorAt(0.0, QColor(255, 255, 255))
            jewel.setColorAt(0.5, QColor(114, 230, 255))
            jewel.setColorAt(1.0, QColor(0, 200, 255))
            painter.setBrush(jewel)
            painter.setPen(QPen(QColor(4, 15, 21), 1))
            painter.drawEllipse(QPointF(pip_x, pip_y), 3.2, 3.2)
            painter.restore()
            return

        # Conical metallic reflection gradient
        conical = QConicalGradient(0, 0, 0)
        if self.style_mode == "gold":
            conical.setColorAt(0.0, QColor(220, 185, 110))
            conical.setColorAt(0.25, QColor(160, 130, 70))
            conical.setColorAt(0.5, QColor(240, 210, 140))
            conical.setColorAt(0.75, QColor(150, 120, 60))
            conical.setColorAt(1.0, QColor(220, 185, 110))
        elif self.style_mode == "black":
            conical.setColorAt(0.0, QColor(50, 55, 62))
            conical.setColorAt(0.25, QColor(24, 26, 30))
            conical.setColorAt(0.5, QColor(68, 74, 84))
            conical.setColorAt(0.75, QColor(22, 24, 28))
            conical.setColorAt(1.0, QColor(50, 55, 62))
        else: # silver
            conical.setColorAt(0.0, QColor(210, 215, 222))
            conical.setColorAt(0.25, QColor(130, 135, 142))
            conical.setColorAt(0.5, QColor(235, 240, 245))
            conical.setColorAt(0.75, QColor(120, 125, 132))
            conical.setColorAt(1.0, QColor(210, 215, 222))

        painter.setPen(QPen(QColor(30, 32, 36), 1))
        painter.setBrush(conical)
        inner_r = r * 0.88
        painter.drawEllipse(QPointF(0, 0), inner_r, inner_r)

        # Center depression cap
        cap_r = inner_r * 0.52
        rad_cap = QRadialGradient(0, 0, cap_r)
        if self.style_mode == "gold":
            rad_cap.setColorAt(0.0, QColor(200, 165, 95))
            rad_cap.setColorAt(1.0, QColor(130, 100, 50))
        elif self.style_mode == "black":
            rad_cap.setColorAt(0.0, QColor(36, 39, 44))
            rad_cap.setColorAt(1.0, QColor(18, 20, 23))
        else:
            rad_cap.setColorAt(0.0, QColor(180, 185, 192))
            rad_cap.setColorAt(1.0, QColor(110, 115, 122))

        painter.setPen(QPen(QColor(20, 22, 25), 1))
        painter.setBrush(rad_cap)
        painter.drawEllipse(QPointF(0, 0), cap_r, cap_r)

        # 4. Indicator Needle / Pip
        cur_angle_deg = start_angle + self._value * span_angle
        cur_rad = math.radians(cur_angle_deg)
        pip_x = (inner_r * 0.72) * math.cos(cur_rad)
        pip_y = (inner_r * 0.72) * math.sin(cur_rad)

        painter.setPen(QPen(QColor(10, 12, 14), 1))
        if self.style_mode == "gold":
            painter.setBrush(QColor(255, 60, 20))
        elif self.style_mode == "black":
            painter.setBrush(QColor(0, 240, 255))
        else:
            painter.setBrush(QColor(255, 40, 40))

        painter.drawEllipse(QPointF(pip_x, pip_y), 3.5, 3.5)

        painter.restore()
