import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont


class ClickWheel(QWidget):
    """
    Iconic tactile Click Wheel widget with center button, circular scrub support,
    and distinct quadrant action clicks (MENU, PREV, NEXT, PLAY/PAUSE).
    """
    menu_clicked = pyqtSignal()
    play_pause_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    center_clicked = pyqtSignal()
    wheel_spun = pyqtSignal(int)  # delta steps for scrubbing

    def __init__(self, color_mode="white", parent=None):
        super().__init__(parent)
        self.color_mode = color_mode  # "white" or "dark"
        self._pressed_region = None
        self._last_angle = None
        self.setFixedSize(180, 180)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        pos = event.pos()
        region = self._hit_test(pos.x(), pos.y())
        self._pressed_region = region
        self._last_angle = self._get_angle(pos.x(), pos.y())
        self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if self._last_angle is not None:
            angle = self._get_angle(pos.x(), pos.y())
            diff = angle - self._last_angle
            # Normalize wrap-around
            if diff > 180:
                diff -= 360
            elif diff < -180:
                diff += 360
            if abs(diff) >= 12:
                steps = int(diff / 12)
                self.wheel_spun.emit(steps)
                self._last_angle = angle
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        pos = event.pos()
        released_region = self._hit_test(pos.x(), pos.y())
        if self._pressed_region and self._pressed_region == released_region:
            if self._pressed_region == "CENTER":
                self.center_clicked.emit()
            elif self._pressed_region == "TOP":
                self.menu_clicked.emit()
            elif self._pressed_region == "BOTTOM":
                self.play_pause_clicked.emit()
            elif self._pressed_region == "LEFT":
                self.prev_clicked.emit()
            elif self._pressed_region == "RIGHT":
                self.next_clicked.emit()

        self._pressed_region = None
        self._last_angle = None
        self.update()
        super().mouseReleaseEvent(event)

    def _get_angle(self, x, y):
        cx, cy = self.width() / 2, self.height() / 2
        rad = math.atan2(y - cy, x - cx)
        deg = math.degrees(rad)
        return (deg + 360) % 360

    def _hit_test(self, x, y):
        cx, cy = self.width() / 2, self.height() / 2
        dx = x - cx
        dy = y - cy
        dist = math.sqrt(dx * dx + dy * dy)
        outer_r = min(cx, cy) * 0.94
        center_r = outer_r * 0.38

        if dist < center_r:
            return "CENTER"
        elif dist <= outer_r:
            angle = self._get_angle(x, y)
            # 4 quadrants: Top (45..135 up is -90), Right (-45..45), Bottom (45..135), Left (135..225)
            # atan2: Right=0, Bottom=90, Left=180, Top=270
            if 45 <= angle < 135:
                return "BOTTOM"
            elif 135 <= angle < 225:
                return "LEFT"
            elif 225 <= angle < 315:
                return "TOP"
            else:
                return "RIGHT"
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.38)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        outer_r = min(cx, cy) * 0.94
        center_r = outer_r * 0.38

        is_white = self.color_mode == "white"

        # 1. Outer Wheel Body
        painter.setPen(QPen(QColor(180, 185, 190) if is_white else QColor(30, 32, 36), 1.5))
        grad_wheel = QLinearGradient(0, cy - outer_r, 0, cy + outer_r)
        if is_white:
            grad_wheel.setColorAt(0.0, QColor(252, 252, 253))
            grad_wheel.setColorAt(1.0, QColor(228, 230, 234))
        else:
            grad_wheel.setColorAt(0.0, QColor(42, 45, 50))
            grad_wheel.setColorAt(1.0, QColor(26, 28, 32))
        painter.setBrush(grad_wheel)
        painter.drawEllipse(QPointF(cx, cy), outer_r, outer_r)

        # 2. Quadrant Labels (MENU, PLAY/PAUSE, PREV, NEXT)
        painter.setFont(QFont("Helvetica, Arial", 8, QFont.Bold))
        text_color = QColor(130, 135, 142) if is_white else QColor(160, 165, 172)
        painter.setPen(text_color)

        # MENU (Top)
        painter.drawText(QRectF(cx - 30, cy - outer_r + 8, 60, 18), Qt.AlignCenter, "MENU")
        # PLAY/PAUSE (Bottom)
        painter.drawText(QRectF(cx - 30, cy + outer_r - 26, 60, 18), Qt.AlignCenter, "> ||")
        # PREV (Left)
        painter.drawText(QRectF(cx - outer_r + 6, cy - 10, 30, 20), Qt.AlignCenter, "|<<")
        # NEXT (Right)
        painter.drawText(QRectF(cx + outer_r - 36, cy - 10, 30, 20), Qt.AlignCenter, ">>|")

        # 3. Center Button
        is_center_down = self._pressed_region == "CENTER"
        painter.setPen(QPen(QColor(190, 195, 200) if is_white else QColor(45, 48, 54), 1.5))
        grad_center = QLinearGradient(0, cy - center_r, 0, cy + center_r)
        if is_white:
            grad_center.setColorAt(0.0, QColor(235, 237, 240) if not is_center_down else QColor(215, 218, 222))
            grad_center.setColorAt(1.0, QColor(250, 252, 254) if not is_center_down else QColor(225, 228, 232))
        else:
            grad_center.setColorAt(0.0, QColor(30, 32, 36) if not is_center_down else QColor(20, 22, 25))
            grad_center.setColorAt(1.0, QColor(50, 54, 60) if not is_center_down else QColor(35, 38, 42))
        painter.setBrush(grad_center)
        painter.drawEllipse(QPointF(cx, cy), center_r, center_r)
