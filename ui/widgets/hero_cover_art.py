import os
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap, QLinearGradient,
    QPainterPath, QFont
)


_COVER_CACHE = {}  # (path, w, h) -> QPixmap


class HeroCoverArtWindow(QWidget):
    """
    Recessed Hi-Fi Jewel Case / Glass Art Window showcasing an unobstructed,
    crisp 1:1 square album cover with an authentic recessed bezel, subtle
    top inner shadow, and faint corner diagonal glass sheen.
    """
    clicked = pyqtSignal()

    def __init__(self, size=260, parent=None):
        super().__init__(parent)
        self.display_size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self._cached_cropped_pixmap = None
        self.is_liquid_glass = False

    def set_artwork(self, image_path_or_pixmap):
        target_w = self.width() - 8
        target_h = self.height() - 8
        if target_w <= 0 or target_h <= 0:
            target_w = self.display_size - 8
            target_h = self.display_size - 8

        if isinstance(image_path_or_pixmap, QPixmap):
            self._cached_cropped_pixmap = self._crop_and_scale(image_path_or_pixmap, target_w, target_h)
        elif image_path_or_pixmap:
            path_str = str(image_path_or_pixmap)
            cache_key = (path_str, target_w, target_h)
            if cache_key in _COVER_CACHE:
                self._cached_cropped_pixmap = _COVER_CACHE[cache_key]
            elif os.path.exists(path_str):
                raw = QPixmap(path_str)
                if not raw.isNull():
                    cropped = self._crop_and_scale(raw, target_w, target_h)
                    _COVER_CACHE[cache_key] = cropped
                    if len(_COVER_CACHE) > 100:
                        # Keep cache bounded
                        _COVER_CACHE.pop(next(iter(_COVER_CACHE)))
                    self._cached_cropped_pixmap = cropped
                else:
                    self._cached_cropped_pixmap = None
            else:
                self._cached_cropped_pixmap = None
        else:
            self._cached_cropped_pixmap = None
        self.update()

    def _crop_and_scale(self, pix, tw, th):
        if not pix or pix.isNull():
            return None
        scaled = pix.scaled(tw, th, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        cx = max(0, (scaled.width() - tw) // 2)
        cy = max(0, (scaled.height() - th) // 2)
        return scaled.copy(cx, cy, tw, th)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        # 1. Outer Bezel (Liquid Glass meniscus vs Dark Recessed metal)
        if self.is_liquid_glass:
            rim = QLinearGradient(0, 0, w, h)
            rim.setColorAt(0.0, QColor(255, 255, 255, 210))
            rim.setColorAt(0.35, QColor(114, 230, 255, 120))
            rim.setColorAt(1.0, QColor(0, 0, 0, 180))
            painter.setPen(QPen(QBrush(rim), 1.5))
            painter.setBrush(QColor(10, 16, 22, 220))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 12, 12)
            corner_r = 10
        else:
            painter.setPen(QPen(QColor(12, 14, 16), 2))
            painter.setBrush(QColor(8, 9, 11))
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 6, 6)
            corner_r = 4

        art_rect = QRectF(4, 4, w - 8, h - 8)

        # 2. Draw Crisp Unobstructed Album Artwork from pre-computed cache
        if self._cached_cropped_pixmap and not self._cached_cropped_pixmap.isNull():
            path = QPainterPath()
            path.addRoundedRect(art_rect, corner_r, corner_r)
            painter.save()
            painter.setClipPath(path)
            painter.drawPixmap(int(art_rect.x()), int(art_rect.y()), self._cached_cropped_pixmap)
            painter.restore()
        else:
            # High-end jewel case placeholder
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(18, 20, 24))
            painter.drawRoundedRect(art_rect, corner_r, corner_r)

            painter.setPen(QColor(90, 95, 105))
            painter.setFont(QFont("Monospace", 9, QFont.Bold))
            painter.drawText(art_rect, Qt.AlignCenter, "NO ALBUM ART\n[Click to Add]")

        # 3. Subtle Inner Shadow at the Top Edge
        top_shadow = QLinearGradient(0, 4, 0, 16)
        top_shadow.setColorAt(0.0, QColor(0, 0, 0, 140))
        top_shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(top_shadow)
        painter.drawRoundedRect(QRectF(4, 4, w - 8, 14), 4, 4)

        # 4. Faint 5% Diagonal Glass Sheen in Top-Right Corner (Never muddies art)
        glare_path = QPainterPath()
        glare_path.moveTo(w - 70, 4)
        glare_path.lineTo(w - 4, 4)
        glare_path.lineTo(w - 4, 70)
        glare_path.closeSubpath()

        glare_grad = QLinearGradient(w - 70, 4, w - 4, 70)
        glare_grad.setColorAt(0.0, QColor(255, 255, 255, 28))
        glare_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glare_grad)
        painter.drawPath(glare_path)

        # Bottom Catch-Light Rim (1px bright light catching edge)
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawLine(QPointF(4, h - 3), QPointF(w - 4, h - 3))
