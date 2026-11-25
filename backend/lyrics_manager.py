import os
import re
import hashlib
import requests
from PyQt5.QtCore import QObject, pyqtSignal, QThread

LYRICS_CACHE_DIR = os.path.expanduser("~/.cache/retro_walkman/lyrics")
os.makedirs(LYRICS_CACHE_DIR, exist_ok=True)


class LyricsFetchWorker(QThread):
    lyrics_ready = pyqtSignal(list, bool)  # (parsed_lines, is_synced)
    lyrics_failed = pyqtSignal(str)

    def __init__(self, filepath, artist, title, duration=0, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.artist = artist or ""
        self.title = title or ""
        self.duration = duration

    def run(self):
        try:
            lines, is_synced = LyricsManager.get_lyrics(self.filepath, self.artist, self.title, self.duration)
            if lines:
                self.lyrics_ready.emit(lines, is_synced)
            else:
                self.lyrics_failed.emit("No lyrics found for this song.")
        except Exception as e:
            self.lyrics_failed.emit(str(e))


class LyricsSearchWorker(QThread):
    """
    Background worker that queries LrcLib online candidate versions
    so the user can manually inspect and choose which lyric release to apply.
    """
    results_ready = pyqtSignal(list)
    search_failed = pyqtSignal(str)

    def __init__(self, query, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        try:
            candidates = LyricsManager.search_lyrics_candidates(self.query)
            self.results_ready.emit(candidates)
        except Exception as e:
            self.search_failed.emit(str(e))


class LyricsManager:
    """
    Handles local .lrc parsing, online synchronized lyrics fetching from LrcLib,
    caching, and real-time active lyric matching.
    """

    @classmethod
    def get_lyrics(cls, filepath, artist, title, duration=0):
        """
        Returns (parsed_lines, is_synced).
        parsed_lines is a list of tuples: (timestamp_seconds, text).
        """
        # 1. Check local .lrc alongside the file
        local_lrc = cls._find_local_lrc(filepath)
        if local_lrc:
            try:
                with open(local_lrc, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                    parsed = cls.parse_lrc(content)
                    if parsed:
                        return parsed, True
            except Exception as e:
                print(f"Error reading local .lrc: {e}")

        # 2. Check disk cache
        cache_file = cls._get_cache_path(artist, title)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    parsed = cls.parse_lrc(content)
                    if parsed:
                        return parsed, True
            except Exception:
                pass

        # 3. Fetch from LrcLib API
        return cls._fetch_lrclib(artist, title, duration, cache_file)

    @classmethod
    def _find_local_lrc(cls, filepath):
        if not filepath:
            return None
        base = os.path.splitext(filepath)[0]
        candidates = [
            base + ".lrc",
            base + ".LRC",
            os.path.join(os.path.dirname(filepath), "Lyrics", os.path.basename(base) + ".lrc")
        ]
        for c in candidates:
            if os.path.exists(c) and os.path.getsize(c) > 10:
                return c
        return None

    @classmethod
    def _get_cache_path(cls, artist, title):
        key = hashlib.md5(f"{artist.lower()}_{title.lower()}".encode("utf-8")).hexdigest()
        return os.path.join(LYRICS_CACHE_DIR, f"{key}.lrc")

    @classmethod
    def _fetch_lrclib(cls, artist, title, duration, cache_file):
        headers = {"User-Agent": "RetroWalkmanPro/2.0 (linux; pyqt5)"}

        clean_artist = artist if artist.lower() not in ["unknown artist", "unknown", ""] else ""
        clean_title = title if title.lower() not in ["unknown title", "unknown", ""] else ""

        if not clean_title:
            return [], False

        # Attempt 1: Exact get
        try:
            params = {"track_name": clean_title}
            if clean_artist:
                params["artist_name"] = clean_artist
            if duration > 0:
                params["duration"] = int(duration)

            res = requests.get("https://lrclib.net/api/get", params=params, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json()
                synced = data.get("syncedLyrics")
                plain = data.get("plainLyrics")
                if synced:
                    cls._save_cache(cache_file, synced)
                    return cls.parse_lrc(synced), True
                elif plain:
                    return cls._wrap_plain(plain), False
        except Exception:
            pass

        # Attempt 2: Search endpoint
        try:
            q = f"{clean_artist} {clean_title}".strip()
            res = requests.get("https://lrclib.net/api/search", params={"q": q}, headers=headers, timeout=6)
            if res.status_code == 200:
                items = res.json()
                if items and isinstance(items, list):
                    for item in items[:3]:
                        synced = item.get("syncedLyrics")
                        if synced:
                            cls._save_cache(cache_file, synced)
                            return cls.parse_lrc(synced), True
                    # If no synced, try first plain
                    plain = items[0].get("plainLyrics")
                    if plain:
                        return cls._wrap_plain(plain), False
        except Exception:
            pass

        return [], False

    @classmethod
    def search_lyrics_candidates(cls, query):
        """
        Queries LrcLib search API and returns list of candidate matches
        for the user to manually inspect and pick from.
        """
        headers = {"User-Agent": "RetroWalkmanPro/2.0 (linux; pyqt5)"}
        try:
            res = requests.get("https://lrclib.net/api/search", params={"q": query.strip()}, headers=headers, timeout=7)
            if res.status_code == 200:
                raw_items = res.json()
                candidates = []
                if isinstance(raw_items, list):
                    for item in raw_items:
                        synced = item.get("syncedLyrics")
                        plain = item.get("plainLyrics")
                        if not synced and not plain:
                            continue
                        candidates.append({
                            "id": item.get("id"),
                            "trackName": item.get("trackName") or "Unknown Track",
                            "artistName": item.get("artistName") or "Unknown Artist",
                            "albumName": item.get("albumName") or "",
                            "duration": float(item.get("duration") or 0.0),
                            "is_synced": bool(synced),
                            "syncedLyrics": synced or "",
                            "plainLyrics": plain or ""
                        })
                return candidates
        except Exception as e:
            print(f"Error searching lyrics candidates: {e}")
        return []

    @classmethod
    def apply_selected_lyrics(cls, filepath, artist, title, raw_lyrics, is_synced):
        """
        Saves user-selected lyrics into cache and beside file if writable, and returns parsed lines.
        """
        cache_file = cls._get_cache_path(artist, title)
        cls._save_cache(cache_file, raw_lyrics)

        # Also attempt to save .lrc next to file if writable
        if is_synced and filepath and os.path.exists(filepath):
            try:
                side_lrc = os.path.splitext(filepath)[0] + ".lrc"
                with open(side_lrc, "w", encoding="utf-8") as f:
                    f.write(raw_lyrics)
            except Exception:
                pass

        if is_synced:
            return cls.parse_lrc(raw_lyrics), True
        else:
            return cls._wrap_plain(raw_lyrics), False

    @staticmethod
    def _save_cache(filepath, content):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Error saving lyrics cache: {e}")

    @staticmethod
    def parse_lrc(content):
        """
        Parses standard .lrc file text into sorted list of (seconds, text).
        Handles formats like [01:23.45] or [01:23] or multiple timestamps [00:10][00:20]text
        """
        pattern = re.compile(r"\[(\d{1,2}):(\d{2}(?:\.\d{1,3})?)\]")
        lines = []

        for raw_line in content.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            matches = list(pattern.finditer(raw_line))
            if not matches:
                continue

            text = pattern.sub("", raw_line).strip()
            for m in matches:
                mins = int(m.group(1))
                secs = float(m.group(2))
                timestamp = mins * 60.0 + secs
                lines.append((timestamp, text))

        lines.sort(key=lambda x: x[0])
        return lines

    @staticmethod
    def _wrap_plain(plain_text):
        """
        Converts un-synced plain text lyrics into dummy timestamped lines spaced evenly.
        """
        lines = []
        for idx, line in enumerate(plain_text.splitlines()):
            t = line.strip()
            if t:
                lines.append((float(idx * 3.5), t))
        return lines

    @staticmethod
    def get_active_index(parsed_lines, current_seconds):
        """
        Finds the line index currently active at current_seconds.
        """
        if not parsed_lines:
            return -1

        active = -1
        for idx, (ts, text) in enumerate(parsed_lines):
            if current_seconds >= ts:
                active = idx
            else:
                break
        return active
