import os
import subprocess
import threading
from PyQt5.QtCore import QObject, QTimer


class NotificationManager(QObject):
    """
    Sends native desktop notifications via notify-send on song change,
    complete with album artwork thumbnails, track title, artist, and album.
    Debounced and threaded to keep UI track-skipping instantaneous.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = True
        self._pending_info = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(700)
        self._timer.timeout.connect(self._dispatch_notify)

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)

    def notify_track(self, title, artist, album, art_path=None):
        if not self._enabled:
            return
        self._pending_info = (title, artist, album, art_path)
        self._timer.start()

    def _dispatch_notify(self):
        if not self._pending_info or not self._enabled:
            return
        title, artist, album, art_path = self._pending_info
        self._pending_info = None

        def _run():
            title_str = title or "Unknown Title"
            body = f"{artist or 'Unknown Artist'}\n{album or 'Retro Walkman'}"
            cmd = [
                "notify-send",
                "-a", "Retro Walkman Pro",
                "-h", "string:desktop-entry:retro-walkman",
                "-t", "3500"
            ]
            if art_path and os.path.exists(art_path):
                cmd.extend(["-i", os.path.abspath(art_path)])
            else:
                icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "retro_walkman.png")
                if os.path.exists(icon_path):
                    cmd.extend(["-i", icon_path])
            cmd.extend([title_str, body])
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()
