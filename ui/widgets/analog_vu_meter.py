import math
from PyQt5.QtWidgets import QWidget, QHBoxLayout
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient, QFont, QPainterPath


class SingleAnalogVUMeter(QWidget):
    """
    Realistic backlit analog needle VU meter with logarithmic dB scale,
    warm incandescent lamp illumination, and damped needle ballistics.
    """
    def __init__(self, channel_label="LEFT", parent=None):
        super().__init__(parent)
        self.channel_label = channel_label
        self._animations_enabled = True
        self._target_level = 0.0
        self._needle_pos = 0.0  # 0.0 (left -20dB) to 1.0 (right +3dB)
        self.setMinimumSize(140, 90)

        self._phys_timer = QTimer(self)
        self._phys_timer.timeout.connect(self._physics_step)
        self._phys_timer.setInterval(50)  # 20 FPS is sufficient for a meter needle

    def showEvent(self, event):
        super().showEvent(event)
        if self._animations_enabled and abs(self._target_level - self._needle_pos) > 0.002:
            self._phys_timer.start()

    def hideEvent(self, event):
        self._phys_timer.stop()
        super().hideEvent(event)

    def set_level(self, level_0_to_1):
        self._target_level = max(0.0, min(1.0, float(level_0_to_1)))
        if self._animations_enabled and self.isVisible() and abs(self._target_level - self._needle_pos) > 0.002:
            self._phys_timer.start()
        elif not self._animations_enabled:
            self._needle_pos = self._target_level
            self.update()

    def set_animations_enabled(self, enabled):
        self._animations_enabled = bool(enabled)
        if not self._animations_enabled:
            self._phys_timer.stop()
            self._needle_pos = self._target_level
            self.update()
        elif self.isVisible() and abs(self._target_level - self._needle_pos) > 0.002:
            self._phys_timer.start()

    def _physics_step(self):
        # Damped spring needle movement
        diff = self._target_level - self._needle_pos
        self._needle_pos += diff * 0.28
        self.update()
        if abs(diff) <= 0.002:
            self._needle_pos = self._target_level
            self._phys_timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Outer Bezel
        painter.setPen(QPen(QColor(32, 36, 42), 2))
        painter.setBrush(QColor(16, 18, 22))
        painter.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 8, 8)

        # 2. Warm Backlit Meter Face (Vintage Cream/Amber Lamp Glow)
        face_rect = QRectF(6, 6, w - 12, h - 12)
        lamp_grad = QRadialGradient(w / 2, h * 0.85, w * 0.7)
        lamp_grad.setColorAt(0.0, QColor(255, 238, 180, 240))
        lamp_grad.setColorAt(0.6, QColor(240, 215, 140, 220))
        lamp_grad.setColorAt(1.0, QColor(190, 160, 90, 200))

        painter.setPen(QPen(QColor(80, 70, 45), 1.5))
        painter.setBrush(lamp_grad)
        painter.drawRoundedRect(face_rect, 6, 6)

        # Pivot point for the needle near bottom center
        pivot_x = w / 2.0
        pivot_y = h * 0.96
        meter_radius = h * 0.85

        # 3. Curved Scale Arc & Tick Marks
        # Needle sweeps from -48 degrees to +48 degrees
        start_angle = -48.0
        end_angle = 48.0
        total_span = end_angle - start_angle

        # Draw Scale Arc
        arc_rect = QRectF(pivot_x - meter_radius, pivot_y - meter_radius, meter_radius * 2, meter_radius * 2)
        painter.setPen(QPen(QColor(40, 35, 25), 1.5))
        # Black normal zone: -20dB to 0dB (-48 to +16 deg)
        # Red peak zone: 0dB to +3dB (+16 to +48 deg)
        painter.setPen(QPen(QColor(40, 35, 25), 2))
        painter.drawArc(arc_rect, int((90 - 16) * 16), int((16 - (-48)) * 16))
        painter.setPen(QPen(QColor(210, 30, 20), 2.5))
        painter.drawArc(arc_rect, int((90 - 48) * 16), int((48 - 16) * 16))

        # dB Ticks
        ticks = [
            (-20, 0.0, "-20"),
            (-10, 0.25, "-10"),
            (-5, 0.45, "-5"),
            (-3, 0.58, "-3"),
            (-1, 0.72, "-1"),
            (0, 0.80, "0"),
            (1, 0.87, "+1"),
            (2, 0.94, "+2"),
            (3, 1.0, "+3")
        ]

        painter.setFont(QFont("Arial, Helvetica", 6, QFont.Bold))
        for db, frac, lbl in ticks:
            angle_deg = start_angle + frac * total_span
            rad = math.radians(angle_deg - 90)
            inner_r = meter_radius - (6 if lbl else 4)
            outer_r = meter_radius

            x1 = pivot_x + inner_r * math.cos(rad)
            y1 = pivot_y + inner_r * math.sin(rad)
            x2 = pivot_x + outer_r * math.cos(rad)
            y2 = pivot_y + outer_r * math.sin(rad)

            is_red = db >= 0
            painter.setPen(QPen(QColor(210, 30, 20) if is_red else QColor(40, 35, 25), 1.5 if lbl else 1))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # Number text
            if lbl:
                tx = pivot_x + (inner_r - 7) * math.cos(rad)
                ty = pivot_y + (inner_r - 7) * math.sin(rad)
                painter.setPen(QColor(210, 30, 20) if is_red else QColor(50, 45, 35))
                painter.drawText(QRectF(tx - 10, ty - 5, 20, 10), Qt.AlignCenter, lbl)

        # Labels: VU and Channel
        painter.setFont(QFont("Arial, Helvetica", 7, QFont.Bold))
        painter.setPen(QColor(60, 50, 35))
        painter.drawText(QRectF(pivot_x - 20, pivot_y * 0.48, 40, 14), Qt.AlignCenter, "VU")
        painter.setFont(QFont("Monospace", 6, QFont.Bold))
        painter.drawText(QRectF(pivot_x - 30, pivot_y * 0.62, 60, 12), Qt.AlignCenter, self.channel_label)

        # 4. Needle Indicator
        cur_angle = start_angle + self._needle_pos * total_span
        cur_rad = math.radians(cur_angle - 90)
        tip_x = pivot_x + (meter_radius - 2) * math.cos(cur_rad)
        tip_y = pivot_y + (meter_radius - 2) * math.sin(cur_rad)

        # Needle shadow
        painter.setPen(QPen(QColor(0, 0, 0, 60), 1.5))
        painter.drawLine(QPointF(pivot_x + 1, pivot_y + 1), QPointF(tip_x + 1, tip_y + 1))

        # Thin black needle
        painter.setPen(QPen(QColor(25, 20, 15), 1.5))
        painter.drawLine(QPointF(pivot_x, pivot_y), QPointF(tip_x, tip_y))

        # 5. Pivot Hub Cap
        painter.setPen(QPen(QColor(40, 35, 25), 1))
        painter.setBrush(QColor(20, 18, 15))
        painter.drawEllipse(QPointF(pivot_x, pivot_y), 8, 8)
        painter.setBrush(QColor(180, 160, 110))
        painter.drawEllipse(QPointF(pivot_x, pivot_y), 3.5, 3.5)


class DualStereoAnalogVUMeter(QWidget):
    """
    Twin stereo pair of analog VU meters (Left & Right).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self.setMinimumWidth(300)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        self.meter_l = SingleAnalogVUMeter("LEFT (CH 1)")
        self.meter_r = SingleAnalogVUMeter("RIGHT (CH 2)")

        layout.addWidget(self.meter_l)
        layout.addWidget(self.meter_r)

    def set_levels(self, l_val, r_val):
        self.meter_l.set_level(l_val)
        self.meter_r.set_level(r_val)

    def set_animations_enabled(self, enabled):
        self.meter_l.set_animations_enabled(enabled)
        self.meter_r.set_animations_enabled(enabled)
