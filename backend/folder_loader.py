import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QThread, pyqtSignal
from backend.library_organizer import SUPPORTED_EXTS
from backend.metadata_manager import MetadataManager


class FolderLoaderWorker(QThread):
    progress = pyqtSignal(int, int, str)       # current, total, current_file
    finished = pyqtSignal(list)               # list of extracted metadata dicts
    error = pyqtSignal(str)

    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.paths = paths
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            discovered_files = []
            for p in self.paths:
                if self._is_cancelled:
                    return
                if os.path.isdir(p):
                    for root, _, files in os.walk(p):
                        for f in sorted(files):
                            if self._is_cancelled:
                                return
                            ext = os.path.splitext(f)[1].lower()
                            if ext in SUPPORTED_EXTS:
                                discovered_files.append(os.path.join(root, f))
                elif os.path.isfile(p):
                    ext = os.path.splitext(p)[1].lower()
                    if ext in SUPPORTED_EXTS:
                        discovered_files.append(p)

            total = len(discovered_files)
            if total == 0:
                self.finished.emit([])
                return

            results = [None] * total
            completed_count = 0
            last_emit_time = 0.0

            # Parallel metadata extraction across CPU cores
            max_workers = min(12, max(2, (os.cpu_count() or 4) * 2))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_idx = {
                    executor.submit(MetadataManager.extract_metadata, fp): (idx, fp)
                    for idx, fp in enumerate(discovered_files)
                }

                for future in as_completed(future_to_idx):
                    if self._is_cancelled:
                        executor.shutdown(wait=False, cancel_futures=True)
                        return

                    idx, fp = future_to_idx[future]
                    try:
                        meta = future.result()
                    except Exception:
                        meta = {
                            "path": os.path.abspath(fp),
                            "filename": os.path.basename(fp),
                            "title": os.path.splitext(os.path.basename(fp))[0],
                            "artist": "Unknown Artist",
                            "album": "Unknown Album",
                            "year": "",
                            "genre": "",
                            "duration": 0.0,
                            "bitrate": 0,
                            "artwork_path": None,
                        }

                    results[idx] = meta
                    completed_count += 1

                    now = time.monotonic()
                    # Throttle progress emissions to prevent Qt event loop congestion
                    if now - last_emit_time >= 0.05 or completed_count == total:
                        last_emit_time = now
                        fname = os.path.basename(fp)
                        self.progress.emit(completed_count, total, fname)

            # Persist newly cached metadata
            MetadataManager.save_cache()

            valid_results = [r for r in results if r is not None]
            self.finished.emit(valid_results)
        except Exception as e:
            self.error.emit(str(e))
