import os
import time
from PyQt5.QtCore import QThread, pyqtSignal
from backend.metadata_manager import MetadataManager


class BatchMetadataWorker(QThread):
    """
    Background worker that iterates across ALL songs in the library or playlist,
    fetching high-resolution album cover artwork and tag info (title, artist, album,
    genre, year) from online databases (iTunes / MusicBrainz / LrcLib) without freezing GUI.
    """
    progress = pyqtSignal(int, int, str, bool)    # (current, total, track_title, cover_found)
    track_updated = pyqtSignal(int, dict)         # (index, updated_meta)
    finished_batch = pyqtSignal(dict)             # stats summary dict
    error = pyqtSignal(str)

    def __init__(self, playlist, force_all=False, parent=None):
        super().__init__(parent)
        self.playlist = list(playlist)
        self.force_all = force_all
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            total = len(self.playlist)
            if total == 0:
                self.finished_batch.emit({"total": 0, "updated": 0, "covers_added": 0})
                return

            stats = {
                "total": total,
                "updated": 0,
                "covers_added": 0,
                "already_complete": 0
            }

            for idx, item in enumerate(self.playlist):
                if self._is_cancelled:
                    return

                filepath = item.get("path", "")
                title = item.get("title") or os.path.splitext(item.get("filename", ""))[0]
                has_cover = bool(item.get("artwork_path") and os.path.exists(item["artwork_path"]))

                # Check if enrichment needed
                needs_enrich = self.force_all or (not has_cover) or (not item.get("artist")) or (not item.get("album"))

                if not needs_enrich:
                    stats["already_complete"] += 1
                    self.progress.emit(idx + 1, total, title, True)
                    continue

                self.progress.emit(idx + 1, total, f"Searching online: {title}...", False)

                try:
                    res = MetadataManager.fetch_online(filepath, item, write_to_disk=False)
                    if res:
                        stats["updated"] += 1
                        got_cover = bool(res.get("artwork_path") and os.path.exists(res["artwork_path"]))
                        if got_cover and not has_cover:
                            stats["covers_added"] += 1
                        self.progress.emit(idx + 1, total, f"Updated: {res.get('title', title)}", got_cover)
                        self.track_updated.emit(idx, res)
                    else:
                        self.progress.emit(idx + 1, total, f"No match: {title}", has_cover)
                except Exception as ex:
                    self.progress.emit(idx + 1, total, f"Error: {title} ({ex})", False)

                # Politeness throttle for APIs
                time.sleep(0.08)

            # Flush all overrides to disk safely in background thread once!
            MetadataManager.flush_overrides()
            self.finished_batch.emit(stats)

        except Exception as e:
            self.error.emit(str(e))
