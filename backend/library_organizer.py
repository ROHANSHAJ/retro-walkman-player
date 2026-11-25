import os
import re
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from .metadata_manager import MetadataManager

SUPPORTED_EXTS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".opus", ".wma"}


def sanitize_filename(name):
    if not name or not str(name).strip():
        return "Unknown"
    cleaned = re.sub(r'[/\\:*?"<>|]', '_', str(name).strip())
    return cleaned[:120]


def detect_language(meta):
    """
    Infers song language using Unicode scripts and tag heuristics:
    - Hindi / Indic (Devanagari \u0900-\u097F)
    - Japanese (Hiragana/Katakana/Kanji \u3040-\u30FF, \u4E00-\u9FFF)
    - Korean (Hangul \uAC00-\uD7AF)
    - Russian / Cyrillic (\u0400-\u04FF)
    - Arabic / Urdu (\u0600-\u06FF)
    - Spanish / Latin (from genre/tags)
    - Instrumental
    - English / International
    """
    text_corpus = f"{meta.get('title', '')} {meta.get('artist', '')} {meta.get('album', '')} {meta.get('genre', '')}"
    genre_lower = str(meta.get('genre', '')).lower()

    if any(k in genre_lower for k in ["instrumental", "soundtrack", "ost", "ambient", "lo-fi", "synthwave"]):
        if not meta.get("lyrics"):
            return "Instrumental / Ambient"

    if re.search(r'[\u0900-\u097F]', text_corpus):
        return "Hindi / Bollywood"
    if re.search(r'[\u3040-\u30FF\u4E00-\u9FFF]', text_corpus):
        return "Japanese"
    if re.search(r'[\uAC00-\uD7AF]', text_corpus):
        return "Korean"
    if re.search(r'[\u0400-\u04FF]', text_corpus):
        return "Russian / Slavic"
    if re.search(r'[\u0600-\u06FF]', text_corpus):
        return "Arabic / Urdu"

    if any(k in genre_lower for k in ["latin", "salsa", "reggaeton", "spanish", "flamenco"]):
        return "Spanish / Latin"
    if any(k in genre_lower for k in ["french", "chanson"]):
        return "French"
    if any(k in genre_lower for k in ["k-pop", "kpop"]):
        return "Korean"
    if any(k in genre_lower for k in ["j-pop", "jpop", "anime"]):
        return "Japanese"

    return "English / International"


def detect_decade(year_str):
    try:
        yr = int(re.search(r'\b(19\d\d|20\d\d)\b', str(year_str)).group(1))
        decade_start = (yr // 10) * 10
        return f"{decade_start}s"
    except Exception:
        return "Unknown Decade"


class OrganizerWorker(QThread):
    progress = pyqtSignal(int, int, str)  # (current, total, status_message)
    finished_summary = pyqtSignal(dict)   # statistics dict
    error = pyqtSignal(str)

    def __init__(self, source_dir, target_dir, group_by_artist=True, group_by_year=True,
                 group_by_genre=True, group_by_language=True, group_by_decade=True, parent=None):
        super().__init__(parent)
        self.source_dir = os.path.abspath(source_dir)
        self.target_dir = os.path.abspath(target_dir)
        self.group_by_artist = group_by_artist
        self.group_by_year = group_by_year
        self.group_by_genre = group_by_genre
        self.group_by_language = group_by_language
        self.group_by_decade = group_by_decade
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            stats = {
                "scanned_files": 0,
                "symlinks_created": 0,
                "symlinks_skipped": 0,
                "target_dir": self.target_dir,
                "by_artist_dir": None,
                "by_year_dir": None,
                "by_genre_dir": None,
                "by_language_dir": None,
                "by_decade_dir": None
            }

            audio_files = []
            for root, dirs, files in os.walk(self.source_dir):
                if self._is_cancelled:
                    return
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_EXTS:
                        audio_files.append(os.path.join(root, f))

            total = len(audio_files)
            if total == 0:
                self.error.emit(f"No supported audio files found in: {self.source_dir}")
                return

            os.makedirs(self.target_dir, exist_ok=True)

            artist_root = os.path.join(self.target_dir, "By_Artist")
            year_root = os.path.join(self.target_dir, "By_Year")
            genre_root = os.path.join(self.target_dir, "By_Genre")
            lang_root = os.path.join(self.target_dir, "By_Language")
            decade_root = os.path.join(self.target_dir, "By_Decade")

            if self.group_by_artist:
                os.makedirs(artist_root, exist_ok=True)
                stats["by_artist_dir"] = artist_root
            if self.group_by_year:
                os.makedirs(year_root, exist_ok=True)
                stats["by_year_dir"] = year_root
            if self.group_by_genre:
                os.makedirs(genre_root, exist_ok=True)
                stats["by_genre_dir"] = genre_root
            if self.group_by_language:
                os.makedirs(lang_root, exist_ok=True)
                stats["by_language_dir"] = lang_root
            if self.group_by_decade:
                os.makedirs(decade_root, exist_ok=True)
                stats["by_decade_dir"] = decade_root

            for idx, src_file in enumerate(audio_files, 1):
                if self._is_cancelled:
                    return

                stats["scanned_files"] += 1
                meta = MetadataManager.extract_metadata(src_file)

                artist = sanitize_filename(meta.get("artist") or "Unknown Artist")
                album = sanitize_filename(meta.get("album") or "Unknown Album")
                year = sanitize_filename(meta.get("year") or "Unknown Year")
                genre = sanitize_filename(meta.get("genre") or "Unknown Genre")
                title = sanitize_filename(meta.get("title") or os.path.splitext(meta["filename"])[0])
                lang = sanitize_filename(detect_language(meta))
                decade = sanitize_filename(detect_decade(year))
                ext = os.path.splitext(src_file)[1]

                self.progress.emit(idx, total, f"Linking: {title} ({artist})")

                def make_link(target_path):
                    if os.path.islink(target_path) or os.path.exists(target_path):
                        stats["symlinks_skipped"] += 1
                        return
                    try:
                        os.symlink(src_file, target_path)
                        stats["symlinks_created"] += 1
                    except Exception as e:
                        pass

                # 1. By Artist
                if self.group_by_artist:
                    dest_dir = os.path.join(artist_root, artist, album)
                    os.makedirs(dest_dir, exist_ok=True)
                    make_link(os.path.join(dest_dir, f"{title}{ext}"))

                # 2. By Year
                if self.group_by_year:
                    dest_dir = os.path.join(year_root, year)
                    os.makedirs(dest_dir, exist_ok=True)
                    make_link(os.path.join(dest_dir, f"{artist} - {title}{ext}"))

                # 3. By Genre
                if self.group_by_genre:
                    dest_dir = os.path.join(genre_root, genre)
                    os.makedirs(dest_dir, exist_ok=True)
                    make_link(os.path.join(dest_dir, f"{artist} - {title}{ext}"))

                # 4. By Language
                if self.group_by_language:
                    dest_dir = os.path.join(lang_root, lang)
                    os.makedirs(dest_dir, exist_ok=True)
                    make_link(os.path.join(dest_dir, f"{artist} - {title}{ext}"))

                # 5. By Decade
                if self.group_by_decade:
                    dest_dir = os.path.join(decade_root, decade)
                    os.makedirs(dest_dir, exist_ok=True)
                    make_link(os.path.join(dest_dir, f"{artist} - {title}{ext}"))

            self.finished_summary.emit(stats)

        except Exception as e:
            self.error.emit(str(e))
