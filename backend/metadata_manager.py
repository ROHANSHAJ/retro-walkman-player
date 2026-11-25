import os
import json
import hashlib
import subprocess
import re
import urllib.parse
import urllib.request
import requests
from PyQt5.QtCore import QObject, pyqtSignal, QThread


CACHE_DIR = os.path.expanduser("~/.cache/retro_walkman")
ART_CACHE_DIR = os.path.join(CACHE_DIR, "artwork")
CONFIG_DIR = os.path.expanduser("~/.config/retro_walkman")
OVERRIDES_FILE = os.path.join(CONFIG_DIR, "overrides.json")
META_CACHE_FILE = os.path.join(CACHE_DIR, "meta_cache.json")

os.makedirs(ART_CACHE_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)


class MetadataFetchWorker(QThread):
    """
    Background worker thread to fetch artwork and metadata from the internet
    without freezing the GUI.
    """
    fetched = pyqtSignal(dict)  # emits updated metadata dict
    failed = pyqtSignal(str, str)  # filepath, error msg

    def __init__(self, filepath, current_meta, query_override=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.meta = dict(current_meta)
        self.query_override = query_override

    def run(self):
        try:
            result = MetadataManager.fetch_online(
                self.filepath,
                self.meta,
                self.query_override
            )
            if result:
                self.fetched.emit(result)
            else:
                self.failed.emit(self.filepath, "No matching online track or cover art found.")
        except Exception as e:
            self.failed.emit(self.filepath, str(e))


class CoverSearchWorker(QThread):
    """
    Background worker that fetches multiple candidate releases and album artwork
    options from iTunes & MusicBrainz for manual selection by the user.
    """
    candidates_ready = pyqtSignal(list)
    search_failed = pyqtSignal(str)

    def __init__(self, filepath, current_meta, query=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.meta = dict(current_meta)
        self.query = query

    def run(self):
        try:
            candidates = MetadataManager.search_online_candidates(self.filepath, self.meta, self.query)
            self.candidates_ready.emit(candidates)
        except Exception as e:
            self.search_failed.emit(str(e))


class MetadataManager:
    """
    Extracts embedded ID3/Vorbis/MP4 tags and cover art via ffprobe/ffmpeg,
    handles online artwork/tag fetching from iTunes/MusicBrainz, and manages
    user overrides.
    """
    _cached_overrides = None
    _overrides_dirty = False
    _meta_cache = None
    _meta_cache_dirty = False

    @classmethod
    def get_meta_cache(cls):
        if cls._meta_cache is None:
            if os.path.exists(META_CACHE_FILE):
                try:
                    with open(META_CACHE_FILE, "r", encoding="utf-8") as f:
                        cls._meta_cache = json.load(f)
                except Exception:
                    cls._meta_cache = {}
            else:
                cls._meta_cache = {}
        return cls._meta_cache

    @classmethod
    def save_cache(cls):
        if not cls._meta_cache_dirty or cls._meta_cache is None:
            return
        try:
            tmp_path = META_CACHE_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(cls._meta_cache, f, ensure_ascii=False)
            os.replace(tmp_path, META_CACHE_FILE)
            cls._meta_cache_dirty = False
        except Exception as e:
            print(f"Error saving meta_cache: {e}")

    @classmethod
    def get_overrides(cls):
        if cls._cached_overrides is None:
            if os.path.exists(OVERRIDES_FILE):
                try:
                    with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
                        cls._cached_overrides = json.load(f)
                except Exception:
                    cls._cached_overrides = {}
            else:
                cls._cached_overrides = {}
        return cls._cached_overrides

    @classmethod
    def save_override(cls, filepath, data, write_to_disk=True):
        overrides = cls.get_overrides()
        overrides[os.path.abspath(filepath)] = data
        cls._overrides_dirty = True
        if write_to_disk:
            cls.flush_overrides()

    @classmethod
    def flush_overrides(cls):
        if not cls._overrides_dirty or cls._cached_overrides is None:
            return
        try:
            tmp_path = OVERRIDES_FILE + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(cls._cached_overrides, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, OVERRIDES_FILE)
            cls._overrides_dirty = False
        except Exception as e:
            print(f"Error flushing overrides: {e}")

    @classmethod
    def extract_metadata(cls, filepath):
        """
        Extracts tags, duration, and embedded thumbnail from the audio file.
        Checks persistent metadata cache and user overrides first.
        """
        abs_path = os.path.abspath(filepath)
        overrides = cls.get_overrides()
        custom = overrides.get(abs_path, {})

        # Fast cache check by mtime
        mtime = 0.0
        try:
            st = os.stat(abs_path)
            mtime = st.st_mtime
        except Exception:
            pass

        cache = cls.get_meta_cache()
        if abs_path in cache and cache[abs_path].get("_mtime") == mtime:
            cached_meta = dict(cache[abs_path])
            for k in ["title", "artist", "album", "year", "genre", "track"]:
                if custom.get(k):
                    cached_meta[k] = custom[k]
            if custom.get("artwork_path"):
                cached_meta["artwork_path"] = custom["artwork_path"]
            cached_meta["is_custom"] = bool(custom)
            return cached_meta

        meta = {
            "path": abs_path,
            "filename": os.path.basename(filepath),
            "title": "",
            "artist": "",
            "album_artist": "",
            "album": "",
            "year": "",
            "genre": "",
            "track": "",
            "duration": 0.0,
            "bitrate": 0,
            "sample_rate": 0,
            "codec": "",
            "comment": "",
            "artwork_path": None,
            "is_custom": bool(custom)
        }

        # 1. ffprobe extraction
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                abs_path
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if proc.returncode == 0 and proc.stdout:
                data = json.loads(proc.stdout)
                fmt = data.get("format", {})
                tags = fmt.get("tags", {})
                # Lowercase tag keys for normalization
                norm_tags = {k.lower(): v for k, v in tags.items()}

                meta["duration"] = float(fmt.get("duration", 0.0))
                meta["bitrate"] = int(fmt.get("bit_rate", 0)) // 1000

                meta["title"] = norm_tags.get("title") or norm_tags.get("song") or ""
                meta["artist"] = norm_tags.get("artist") or norm_tags.get("album_artist") or ""
                meta["album_artist"] = norm_tags.get("album_artist") or norm_tags.get("albumartist") or ""
                meta["album"] = norm_tags.get("album") or ""
                meta["year"] = norm_tags.get("date") or norm_tags.get("year") or norm_tags.get("originalyear") or ""
                if meta["year"] and len(meta["year"]) >= 4:
                    meta["year"] = meta["year"][:4]
                meta["genre"] = norm_tags.get("genre") or ""
                meta["track"] = norm_tags.get("track") or ""
                meta["comment"] = norm_tags.get("comment") or norm_tags.get("description") or ""

                # Check for embedded artwork in video streams
                streams = data.get("streams", [])
                audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
                meta["sample_rate"] = int(audio_stream.get("sample_rate") or 0)
                meta["codec"] = audio_stream.get("codec_name") or fmt.get("format_name", "")
                has_art_stream = any(s.get("codec_type") == "video" for s in streams)
                if has_art_stream:
                    art_path = cls._extract_embedded_art(abs_path)
                    if art_path and os.path.exists(art_path):
                        meta["artwork_path"] = art_path

        except Exception as e:
            print(f"Metadata extraction error for {abs_path}: {e}")

        # Fallback title from filename if empty
        if not meta["title"]:
            base = os.path.splitext(meta["filename"])[0]
            # Strip leading track numbers like "01. ", "01 - "
            cleaned = re.sub(r"^\d+[\s\.\-_]+", "", base)
            if " - " in cleaned:
                parts = cleaned.split(" - ", 1)
                meta["artist"] = meta["artist"] or parts[0].strip()
                meta["title"] = parts[1].strip()
            else:
                meta["title"] = cleaned or base

        if not meta["artist"]:
            meta["artist"] = "Unknown Artist"
        if not meta["album"]:
            meta["album"] = "Unknown Album"
        if not meta["year"]:
            meta["year"] = "Unknown Year"
        if not meta["genre"]:
            meta["genre"] = "Unknown Genre"

        # Check for folder album art (cover.jpg, folder.jpg) if no embedded art
        if not meta["artwork_path"]:
            meta["artwork_path"] = cls._find_folder_art(os.path.dirname(abs_path))

        # Store in persistent cache
        meta_to_cache = dict(meta)
        meta_to_cache["_mtime"] = mtime
        cache[abs_path] = meta_to_cache
        cls._meta_cache_dirty = True

        # Apply any manual overrides
        for k in ["title", "artist", "album", "year", "genre", "track"]:
            if custom.get(k):
                meta[k] = custom[k]
        if custom.get("artwork_path") and os.path.exists(custom["artwork_path"]):
            meta["artwork_path"] = custom["artwork_path"]

        return meta

    @classmethod
    def _extract_embedded_art(cls, abs_path):
        key = hashlib.md5(abs_path.encode("utf-8")).hexdigest()
        dest = os.path.join(ART_CACHE_DIR, f"embed_{key}.jpg")
        if os.path.exists(dest) and os.path.getsize(dest) > 100:
            return dest
        try:
            cmd = [
                "ffmpeg", "-y", "-v", "quiet",
                "-i", abs_path,
                "-an", "-vcodec", "copy",
                dest
            ]
            subprocess.run(cmd, timeout=4)
            if os.path.exists(dest) and os.path.getsize(dest) > 100:
                return dest
        except Exception:
            pass
        return None

    @classmethod
    def _find_folder_art(cls, folder_path):
        candidates = ["cover.jpg", "cover.png", "folder.jpg", "folder.png", "album.jpg", "front.jpg", "front.png"]
        for c in candidates:
            p = os.path.join(folder_path, c)
            if os.path.exists(p) and os.path.getsize(p) > 100:
                return p
        return None

    @classmethod
    def fetch_online(cls, filepath, current_meta, query_override=None, write_to_disk=True):
        """
        Universal online thumbnail and song info fetcher using iTunes Search API.
        Returns updated metadata dictionary including high-res cover art.
        """
        abs_path = os.path.abspath(filepath)
        search_query = query_override
        if not search_query:
            artist = current_meta.get("artist", "")
            title = current_meta.get("title", "")
            if artist == "Unknown Artist":
                artist = ""
            search_query = f"{artist} {title}".strip()
            if not search_query:
                base = os.path.splitext(os.path.basename(filepath))[0]
                search_query = re.sub(r"^\d+[\s\.\-_]+", "", base)

        # 1. Search iTunes Store
        try:
            url = "https://itunes.apple.com/search"
            params = {
                "term": search_query,
                "entity": "song",
                "limit": 3
            }
            res = requests.get(url, params=params, timeout=7)
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                if results:
                    item = results[0]
                    updated = dict(current_meta)

                    # Only overwrite if previously unknown or query was explicit
                    if query_override or current_meta.get("title", "").lower() in ["", "unknown"]:
                        updated["title"] = item.get("trackName", updated.get("title"))
                    if query_override or current_meta.get("artist", "").lower() in ["", "unknown artist"]:
                        updated["artist"] = item.get("artistName", updated.get("artist"))
                    if query_override or current_meta.get("album", "").lower() in ["", "unknown album"]:
                        updated["album"] = item.get("collectionName", updated.get("album"))
                    if query_override or current_meta.get("year", "").lower() in ["", "unknown year"]:
                        rel_date = item.get("releaseDate", "")
                        if rel_date:
                            updated["year"] = rel_date[:4]
                    if query_override or current_meta.get("genre", "").lower() in ["", "unknown genre"]:
                        updated["genre"] = item.get("primaryGenreName", updated.get("genre"))

                    # Download high-res artwork (up to 1000x1000)
                    art_url = item.get("artworkUrl100")
                    if art_url:
                        hi_res_url = art_url.replace("100x100bb", "1000x1000bb")
                        art_cache_path = cls._download_art(hi_res_url, abs_path)
                        if art_cache_path:
                            updated["artwork_path"] = art_cache_path

                    # Save automatically into overrides
                    cls.save_override(abs_path, updated, write_to_disk=write_to_disk)
                    return updated
        except Exception as e:
            print(f"Online fetch error via iTunes: {e}")

        # 2. Fallback to MusicBrainz / CoverArtArchive if needed
        try:
            mb_url = "https://musicbrainz.org/ws/2/recording/"
            mb_params = {
                "query": search_query,
                "fmt": "json",
                "limit": 1
            }
            headers = {"User-Agent": "RetroWalkman/1.0 (rohan@ubuntu)"}
            res2 = requests.get(mb_url, params=mb_params, headers=headers, timeout=6)
            if res2.status_code == 200:
                recs = res2.json().get("recordings", [])
                if recs:
                    rec = recs[0]
                    updated = dict(current_meta)
                    updated["title"] = rec.get("title", updated.get("title"))
                    artist_credit = rec.get("artist-credit", [])
                    if artist_credit:
                        updated["artist"] = artist_credit[0].get("name", updated.get("artist"))
                    releases = rec.get("releases", [])
                    if releases:
                        rel = releases[0]
                        updated["album"] = rel.get("title", updated.get("album"))
                        rel_id = rel.get("id")
                        if rel_id:
                            cover_url = f"https://coverartarchive.org/release/{rel_id}/front"
                            art_cache_path = cls._download_art(cover_url, abs_path)
                            if art_cache_path:
                                updated["artwork_path"] = art_cache_path
                    cls.save_override(abs_path, updated, write_to_disk=write_to_disk)
                    return updated
        except Exception:
            pass

        return None

    @classmethod
    def _download_art(cls, url, filepath):
        if not url or not filepath:
            return None
        try:
            os.makedirs(ART_CACHE_DIR, exist_ok=True)
            key = hashlib.md5(str(filepath).encode("utf-8", errors="ignore")).hexdigest()
            dest = os.path.join(ART_CACHE_DIR, f"web_{key}.jpg")

            candidates = [url]
            if "1000x1000bb" in url:
                candidates.append(url.replace("1000x1000bb", "600x600bb"))
                candidates.append(url.replace("1000x1000bb", "100x100bb"))

            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            for target_url in candidates:
                try:
                    r = requests.get(target_url, headers=headers, timeout=6, allow_redirects=True)
                    if r.status_code == 200 and len(r.content) > 500:
                        is_jpeg = r.content[:2] == b'\xff\xd8'
                        is_png = r.content[:4] == b'\x89PNG'
                        is_webp = (r.content[:4] == b'RIFF' and b'WEBP' in r.content[:16])
                        if is_jpeg or is_png or is_webp or b'JFIF' in r.content[:30] or b'Exif' in r.content[:30]:
                            with open(dest, "wb") as f:
                                f.write(r.content)
                            return dest
                except Exception:
                    continue
        except Exception as e:
            print(f"Failed to download artwork: {e}")
        return None

    @classmethod
    def search_online_candidates(cls, filepath, current_meta, query=None):
        """
        Queries iTunes Search API (and fallback) to return up to 12 release candidates
        for the user to manually inspect and select artwork / tags from.
        """
        search_query = query
        if not search_query:
            artist = current_meta.get("artist", "")
            title = current_meta.get("title", "")
            if artist == "Unknown Artist":
                artist = ""
            search_query = f"{artist} {title}".strip()
            if not search_query:
                base = os.path.splitext(os.path.basename(filepath))[0]
                search_query = re.sub(r"^\d+[\s\.\-_]+", "", base)

        candidates = []
        seen_art = set()

        # 1. Query iTunes Store
        try:
            url = "https://itunes.apple.com/search"
            params = {
                "term": search_query,
                "entity": "song",
                "limit": 12
            }
            res = requests.get(url, params=params, timeout=7)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("results", []):
                    art_100 = item.get("artworkUrl100") or ""
                    if not art_100:
                        continue
                    if art_100 in seen_art:
                        continue
                    seen_art.add(art_100)

                    rel_date = item.get("releaseDate", "")
                    year = rel_date[:4] if rel_date else ""
                    dur = (item.get("trackTimeMillis", 0) or 0) / 1000.0

                    candidates.append({
                        "source": "iTunes",
                        "title": item.get("trackName") or "",
                        "artist": item.get("artistName") or "",
                        "album": item.get("collectionName") or "",
                        "year": year,
                        "genre": item.get("primaryGenreName") or "",
                        "duration": dur,
                        "preview_url": art_100,
                        "hi_res_url": art_100.replace("100x100bb", "1000x1000bb")
                    })
        except Exception as e:
            print(f"iTunes candidates search error: {e}")

        return candidates

    @classmethod
    def apply_selected_candidate(cls, filepath, current_meta, candidate, update_tags=True):
        """
        Downloads the chosen high-res cover artwork, optionally updates tags,
        and saves the result into overrides.
        """
        abs_path = os.path.abspath(filepath)
        updated = dict(current_meta)

        if update_tags:
            if candidate.get("title"):
                updated["title"] = candidate["title"]
            if candidate.get("artist"):
                updated["artist"] = candidate["artist"]
            if candidate.get("album"):
                updated["album"] = candidate["album"]
            if candidate.get("year"):
                updated["year"] = candidate["year"]
            if candidate.get("genre"):
                updated["genre"] = candidate["genre"]

        hi_res_url = candidate.get("hi_res_url") or candidate.get("preview_url")
        if hi_res_url:
            art_path = cls._download_art(hi_res_url, abs_path)
            if art_path:
                updated["artwork_path"] = art_path

        cls.save_override(abs_path, updated, write_to_disk=True)
        return updated
