import math
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, QLinearGradient,
    QRadialGradient, QFont, QPainterPath
)


class CassetteDeckWidget(QWidget):
    """
    Precision-engineered horizontal cassette deck window (100:64 ratio) with
    trapezoid head bridge, 4 corner screws, molded ribs, rotating drive hubs,
    and dynamic magnetic tape rolls that scale with playback progress.
    """
    art_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 200)

        self._is_playing = False
        self._animations_enabled = True
        self._rotation_angle = 0.0
        self._progress = 0.0  # 0.0 to 1.0 (tape spooling ratio)
        self._pixmap = None
        self._track_info = "TYPE II • CrO2"
        self._tape_type = "TYPE II"

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_step)
        self._anim_timer.setInterval(60)

    def set_playing(self, playing):
        self._is_playing = bool(playing)
        self._sync_animation()

    def _sync_animation(self):
        if self._animations_enabled and self._is_playing and self.isVisible():
            self._anim_timer.start()
        else:
            self._anim_timer.stop()

    def set_animations_enabled(self, enabled):
        self._animations_enabled = bool(enabled)
        self._sync_animation()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_animation()

    def hideEvent(self, event):
        self._anim_timer.stop()
        super().hideEvent(event)

    def set_progress(self, progress_0_to_1):
        self._progress = max(0.0, min(1.0, float(progress_0_to_1)))
        self.update()

    def set_artwork(self, image_path_or_pixmap):
        if isinstance(image_path_or_pixmap, QPixmap):
            self._pixmap = image_path_or_pixmap
        elif image_path_or_pixmap:
            self._pixmap = QPixmap(str(image_path_or_pixmap))
        else:
            self._pixmap = None
        self.update()

    def set_track_info(self, info_text):
        self._track_info = info_text or "TYPE II • CrO2"
        self.update()

    def set_tape_type(self, tape_type):
        self._tape_type = str(tape_type or "TYPE II")
        self.update()

    def _animate_step(self):
        if self._is_playing:
            self._rotation_angle = (self._rotation_angle + 3.0) % 360.0
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.art_clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        # Target aspect ratio: 100mm wide x 64mm high (1.56 : 1)
        target_ratio = 1.56
        if w / max(1, h) > target_ratio:
            box_h = h * 0.92
            box_w = box_h * target_ratio
        else:
            box_w = w * 0.94
            box_h = box_w / target_ratio

        bx = (w - box_w) / 2.0
        by = (h - box_h) / 2.0

        # 1. Recessed Acrylic Chamber Cutout (Deep Inset Shadow into Metal)
        painter.setPen(QPen(QColor(15, 17, 20), 2))
        grad_recess = QLinearGradient(0, by, 0, by + box_h)
        grad_recess.setColorAt(0.0, QColor(8, 9, 11))
        grad_recess.setColorAt(1.0, QColor(18, 20, 24))
        painter.setBrush(grad_recess)
        painter.drawRoundedRect(QRectF(bx, by, box_w, box_h), 8, 8)

        # 2. Cassette Shell Body (Smoke Tinted Polycarbonate)
        shell_w = box_w * 0.94
        shell_h = box_h * 0.92
        sx = bx + (box_w - shell_w) / 2.0
        sy = by + (box_h - shell_h) / 2.0

        grad_shell = QLinearGradient(0, sy, 0, sy + shell_h)
        grad_shell.setColorAt(0.0, QColor(36, 38, 42))
        grad_shell.setColorAt(0.5, QColor(22, 23, 26))
        grad_shell.setColorAt(1.0, QColor(32, 34, 38))

        painter.setPen(QPen(QColor(55, 60, 68), 1.5))
        painter.setBrush(grad_shell)
        painter.drawRoundedRect(QRectF(sx, sy, shell_w, shell_h), 6, 6)

        # 4 Corner Shell Screws
        self._draw_screw(painter, sx + 8, sy + 8)
        self._draw_screw(painter, sx + shell_w - 8, sy + 8)
        self._draw_screw(painter, sx + 8, sy + shell_h - 8)
        self._draw_screw(painter, sx + shell_w - 8, sy + shell_h - 8)

        # Trapezoid Head Bridge Bump at Bottom
        bridge_w = shell_w * 0.52
        bridge_h = shell_h * 0.22
        br_x = sx + (shell_w - bridge_w) / 2.0
        br_y = sy + shell_h - bridge_h

        painter.setPen(QPen(QColor(45, 48, 54), 1))
        painter.setBrush(QColor(18, 19, 22))
        painter.drawRoundedRect(QRectF(br_x, br_y, bridge_w, bridge_h), 4, 4)

        # Guide roller holes in bridge
        painter.setPen(QPen(QColor(30, 32, 36), 1))
        painter.setBrush(QColor(8, 9, 10))
        painter.drawEllipse(QPointF(br_x + 16, br_y + bridge_h * 0.5), 4, 4)
        painter.drawEllipse(QPointF(br_x + bridge_w - 16, br_y + bridge_h * 0.5), 4, 4)

        # 3. Transparent Center Window with Beveled Acrylic Edge
        win_w = shell_w * 0.76
        win_h = shell_h * 0.56
        wx = sx + (shell_w - win_w) / 2.0
        wy = sy + shell_h * 0.16

        painter.setPen(QPen(QColor(65, 70, 78), 1.5))
        painter.setBrush(QColor(6, 8, 10, 230))
        painter.drawRoundedRect(QRectF(wx, wy, win_w, win_h), 4, 4)

        # 4. Tape Spools & Concentric Magnetic Tape Rolls
        spool_y = wy + win_h / 2.0
        spool_r = min(win_w * 0.16, win_h * 0.38)
        lx = wx + win_w * 0.24
        rx = wx + win_w * 0.76

        # Dynamic tape thickness: Left shrinks, Right grows as track progresses
        left_tape_r = spool_r + (1.0 - self._progress) * (spool_r * 0.8)
        right_tape_r = spool_r + self._progress * (spool_r * 0.8)

        # Concentric dark brown magnetic tape
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(36, 20, 14))
        painter.drawEllipse(QPointF(lx, spool_y), left_tape_r, left_tape_r)
        painter.drawEllipse(QPointF(rx, spool_y), right_tape_r, right_tape_r)

        # Rotating white hubs with drive teeth
        self._draw_hub(painter, lx, spool_y, spool_r, self._rotation_angle)
        self._draw_hub(painter, rx, spool_y, spool_r, self._rotation_angle * 1.05)

        # 5. Cassette Center Label Stripe & Typography
        label_w = win_w * 0.32
        label_h = win_h * 0.84
        label_x = wx + (win_w - label_w) / 2.0
        label_y = wy + (win_h - label_h) / 2.0

        # Retro Walkman cassette label styling
        painter.setPen(QPen(QColor(80, 85, 92), 1))
        painter.setBrush(QColor(230, 224, 210))
        painter.drawRoundedRect(QRectF(label_x, label_y, label_w, label_h), 3, 3)

        # Red / Gold Header Stripe on Cassette Label
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(180, 40, 30))
        painter.drawRect(QRectF(label_x, label_y, label_w, 6))

        painter.setFont(QFont("Monospace", 6, QFont.Bold))
        painter.setPen(QColor(20, 20, 20))
        label_text = f"SONY\nWALKMAN\n{self._tape_type}\n[90 min]"
        painter.drawText(QRectF(label_x, label_y + 8, label_w, label_h - 12), Qt.AlignCenter, label_text)

        # 6. Hard Diagonal Acrylic Specular Glare (Tricks the eye into seeing acrylic)
        glare_path = QPainterPath()
        glare_path.moveTo(wx, wy)
        glare_path.lineTo(wx + win_w * 0.45, wy)
        glare_path.lineTo(wx, wy + win_h * 0.7)
        glare_path.closeSubpath()

        glare_grad = QLinearGradient(wx, wy, wx + win_w * 0.3, wy + win_h * 0.5)
        glare_grad.setColorAt(0.0, QColor(255, 255, 255, 35))
        glare_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glare_grad)
        painter.drawPath(glare_path)

    def _draw_hub(self, painter, cx, cy, radius, angle_deg):
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(angle_deg)

        # Outer white gear hub
        painter.setPen(QPen(QColor(180, 180, 180), 1.5))
        painter.setBrush(QColor(245, 245, 245))
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # Center spindle socket
        inner_r = radius * 0.42
        painter.setPen(QPen(QColor(30, 32, 36), 1))
        painter.setBrush(QColor(14, 16, 18))
        painter.drawEllipse(QPointF(0, 0), inner_r, inner_r)

        # 6 Drive teeth
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(245, 245, 245))
        tooth_w = inner_r * 0.35
        tooth_h = inner_r * 0.35
        for _ in range(6):
            painter.rotate(60)
            painter.drawRect(QRectF(-tooth_w / 2, -inner_r - tooth_h * 0.35, tooth_w, tooth_h))

        painter.restore()

    def _draw_screw(self, painter, x, y):
        painter.setPen(QPen(QColor(70, 75, 80), 1))
        painter.setBrush(QColor(38, 40, 44))
        painter.drawEllipse(QPointF(x, y), 3, 3)
        painter.setPen(QPen(QColor(15, 17, 20), 1))
        painter.drawLine(QPointF(x - 1.5, y), QPointF(x + 1.5, y))
