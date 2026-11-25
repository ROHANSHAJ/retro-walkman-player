import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, QRadialGradient,
    QConicalGradient, QLinearGradient, QPainterPath
)


class VinylTurntableWidget(QWidget):
    """
    Realistic animated vinyl turntable record with micro-grooves, light sheen,
    center album art sticker, and a pivoting tonearm with needle.
    """
    art_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)

        self._is_playing = False
        self._animations_enabled = True
        self._rotation_angle = 0.0
        self._pixmap = None
        self._tonearm_angle = 18.0  # 18 deg = on record, 0 deg = parked
        self._anti_skate = 0.5

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_step)
        self._anim_timer.setInterval(50)

    def set_playing(self, playing):
        self._is_playing = bool(playing)
        self._sync_animation()

    def _sync_animation(self):
        if self._animations_enabled and self.isVisible() and (self._is_playing or self._tonearm_angle > 4.0):
            self._anim_timer.start()
        else:
            self._anim_timer.stop()

    def set_animations_enabled(self, enabled):
        self._animations_enabled = bool(enabled)
        if not self._animations_enabled:
            self._anim_timer.stop()
            self._tonearm_angle = 24.0 if self._is_playing else 0.0
            self.update()
        else:
            self._sync_animation()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_animation()

    def hideEvent(self, event):
        self._anim_timer.stop()
        super().hideEvent(event)

    def set_artwork(self, image_path_or_pixmap):
        if isinstance(image_path_or_pixmap, QPixmap):
            self._pixmap = image_path_or_pixmap
        elif image_path_or_pixmap:
            self._pixmap = QPixmap(str(image_path_or_pixmap))
        else:
            self._pixmap = None
        self.update()

    def set_anti_skate(self, value):
        self._anti_skate = max(0.0, min(1.0, float(value)))
        self.update()

    def _animate_step(self):
        if self._is_playing:
            self._rotation_angle = (self._rotation_angle + 2.2) % 360.0
            # Tonearm moves down onto record
            if self._tonearm_angle < 24.0:
                self._tonearm_angle += 0.8
            self.update()
        else:
            # Tonearm moves back to rest
            if self._tonearm_angle > 4.0:
                self._tonearm_angle -= 0.8
                self.update()
            else:
                self._sync_animation()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.art_clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        size = min(w, h)
        cx = w * 0.44
        cy = h / 2.0
        record_r = size * 0.42

        # 1. Turntable Platter Base Shadow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(8, 10, 12, 180))
        painter.drawEllipse(QPointF(cx + 4, cy + 4), record_r + 4, record_r + 4)

        # 2. Vinyl Record Disc (Black Vinyl with Light Sheen)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._rotation_angle)

        # Base black acrylic record
        painter.setPen(QPen(QColor(30, 32, 36), 1.5))
        painter.setBrush(QColor(14, 15, 17))
        painter.drawEllipse(QPointF(0, 0), record_r, record_r)

        # Vinyl Light Sheen (Conical Dual Reflection Wings)
        conical = QConicalGradient(0, 0, 45)
        conical.setColorAt(0.0, QColor(255, 255, 255, 45))
        conical.setColorAt(0.25, QColor(0, 0, 0, 10))
        conical.setColorAt(0.5, QColor(255, 255, 255, 45))
        conical.setColorAt(0.75, QColor(0, 0, 0, 10))
        conical.setColorAt(1.0, QColor(255, 255, 255, 45))

        painter.setPen(Qt.NoPen)
        painter.setBrush(conical)
        painter.drawEllipse(QPointF(0, 0), record_r, record_r)

        # Concentric Micro-Grooves
        groove_pen = QPen(QColor(45, 48, 54, 70), 0.8)
        painter.setPen(groove_pen)
        painter.setBrush(Qt.NoBrush)
        step = record_r * 0.05
        cur_r = record_r * 0.45
        while cur_r < record_r * 0.95:
            painter.drawEllipse(QPointF(0, 0), cur_r, cur_r)
            cur_r += step

        # 3. Center Label Sticker with Album Art Thumbnail
        label_r = record_r * 0.38
        if self._pixmap and not self._pixmap.isNull():
            path = QPainterPath()
            path.addEllipse(QPointF(0, 0), label_r, label_r)
            painter.save()
            painter.setClipPath(path)
            scaled = self._pixmap.scaled(
                int(label_r * 2), int(label_r * 2),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            painter.drawPixmap(int(-label_r), int(-label_r), scaled)
            painter.restore()
        else:
            # Vintage LP Record Label
            painter.setPen(QPen(QColor(220, 180, 80), 1.5))
            painter.setBrush(QColor(210, 50, 40))
            painter.drawEllipse(QPointF(0, 0), label_r, label_r)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(painter.font())
            painter.drawText(QRectF(-label_r, -label_r, label_r * 2, label_r * 2), Qt.AlignCenter, "STEREO\n33 RPM")

        # Center Spindle Hole
        spindle_r = record_r * 0.06
        painter.setPen(QPen(QColor(180, 185, 190), 1.5))
        painter.setBrush(QColor(24, 26, 30))
        painter.drawEllipse(QPointF(0, 0), spindle_r, spindle_r)

        painter.restore()

        # 4. Tonearm Assembly (Pivot, Chrome Arm, Cartridge & Stylus)
        tonearm_pivot_x = w * 0.88
        tonearm_pivot_y = h * 0.22

        painter.save()
        painter.translate(tonearm_pivot_x, tonearm_pivot_y)
        # Bias the stylus angle subtly with the anti-skate control.
        painter.rotate(self._tonearm_angle + (self._anti_skate - 0.5) * 3.0)

        # Chrome Tonearm Rod
        painter.setPen(QPen(QColor(210, 215, 225), 3.5, Qt.SolidLine, Qt.RoundCap))
        arm_len = size * 0.58
        painter.drawLine(QPointF(0, 0), QPointF(-arm_len * 0.65, arm_len * 0.75))

        # Stylus Cartridge (Black / Red Headshell)
        head_x = -arm_len * 0.65
        head_y = arm_len * 0.75
        painter.setPen(QPen(QColor(20, 22, 26), 1))
        painter.setBrush(QColor(230, 40, 30))
        painter.drawRoundedRect(QRectF(head_x - 12, head_y - 6, 24, 12), 2, 2)

        # Pivot Base Gimbal
        painter.setPen(QPen(QColor(60, 65, 75), 2))
        painter.setBrush(QColor(36, 40, 48))
        painter.drawEllipse(QPointF(0, 0), 16, 16)
        painter.setBrush(QColor(200, 205, 215))
        painter.drawEllipse(QPointF(0, 0), 7, 7)

        painter.restore()
