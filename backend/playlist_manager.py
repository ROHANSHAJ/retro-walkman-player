import os
import json
import threading

CONFIG_DIR = os.path.expanduser("~/.config/retro_walkman")
PLAYLISTS_FILE = os.path.join(CONFIG_DIR, "playlists.json")
_PLAYLIST_LOCK = threading.Lock()

os.makedirs(CONFIG_DIR, exist_ok=True)


class PlaylistManager:
    """
    Manages custom user playlists, favorites (Liked Songs), and track play-counts
    with fast in-memory caching and persistent JSON storage.
    """
    _data = None

    @classmethod
    def _load(cls):
        if cls._data is not None:
            return cls._data

        default_structure = {
            "liked": [],          # list of filepaths
            "play_counts": {},    # {filepath: count}
            "playlists": {        # {name: [filepaths]}
                "Heavy Rotation": [],
                "Late Night Hi-Fi": []
            }
        }

        if os.path.exists(PLAYLISTS_FILE):
            try:
                with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = default_structure
                    else:
                        if "liked" not in data or not isinstance(data["liked"], list):
                            data["liked"] = []
                        if "play_counts" not in data or not isinstance(data["play_counts"], dict):
                            data["play_counts"] = {}
                        if "playlists" not in data or not isinstance(data["playlists"], dict):
                            data["playlists"] = default_structure["playlists"]
                    cls._data = data
            except Exception as e:
                print(f"Error loading playlists.json: {e}")
                cls._data = default_structure
        else:
            cls._data = default_structure
            cls._save()

        return cls._data

    @classmethod
    def _save(cls, async_write=True):
        if cls._data is None:
            return
        data_to_save = dict(cls._data)

        def _do_write():
            with _PLAYLIST_LOCK:
                try:
                    tmp_path = f"{PLAYLISTS_FILE}.tmp.{threading.get_ident()}"
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        json.dump(data_to_save, f, ensure_ascii=False)
                    os.replace(tmp_path, PLAYLISTS_FILE)
                except Exception as e:
                    print(f"Error saving playlists: {e}")

        if async_write:
            threading.Thread(target=_do_write, daemon=True).start()
        else:
            _do_write()

    # -------------------------------------------------------------
    # LIKED SONGS (FAVORITES)
    # -------------------------------------------------------------
    @classmethod
    def is_liked(cls, filepath):
        if not filepath:
            return False
        data = cls._load()
        return os.path.abspath(filepath) in data["liked"]

    @classmethod
    def toggle_liked(cls, filepath):
        if not filepath:
            return False
        abs_p = os.path.abspath(filepath)
        data = cls._load()
        if abs_p in data["liked"]:
            data["liked"].remove(abs_p)
            liked = False
        else:
            data["liked"].append(abs_p)
            liked = True
        cls._save()
        return liked

    @classmethod
    def set_liked(cls, filepath, liked):
        if not filepath:
            return
        abs_p = os.path.abspath(filepath)
        data = cls._load()
        if liked and abs_p not in data["liked"]:
            data["liked"].append(abs_p)
            cls._save()
        elif not liked and abs_p in data["liked"]:
            data["liked"].remove(abs_p)
            cls._save()

    @classmethod
    def get_liked_paths(cls):
        data = cls._load()
        return set(data.get("liked", []))

    # -------------------------------------------------------------
    # PLAY COUNT & MOST PLAYED
    # -------------------------------------------------------------
    @classmethod
    def increment_play_count(cls, filepath):
        if not filepath:
            return
        abs_p = os.path.abspath(filepath)
        data = cls._load()
        data["play_counts"][abs_p] = data["play_counts"].get(abs_p, 0) + 1
        cls._save()

    @classmethod
    def get_play_count(cls, filepath):
        if not filepath:
            return 0
        abs_p = os.path.abspath(filepath)
        data = cls._load()
        return data["play_counts"].get(abs_p, 0)

    @classmethod
    def get_most_played_map(cls):
        data = cls._load()
        return dict(data.get("play_counts", {}))

    # -------------------------------------------------------------
    # CUSTOM USER PLAYLISTS
    # -------------------------------------------------------------
    @classmethod
    def get_all_playlists(cls):
        data = cls._load()
        return dict(data.get("playlists", {}))

    @classmethod
    def create_playlist(cls, name):
        name = name.strip()
        if not name:
            return False
        data = cls._load()
        if name not in data["playlists"]:
            data["playlists"][name] = []
            cls._save()
            return True
        return False

    @classmethod
    def delete_playlist(cls, name):
        data = cls._load()
        if name in data["playlists"]:
            del data["playlists"][name]
            cls._save()
            return True
        return False

    @classmethod
    def rename_playlist(cls, old_name, new_name):
        new_name = new_name.strip()
        if not new_name or old_name == new_name:
            return False
        data = cls._load()
        if old_name in data["playlists"] and new_name not in data["playlists"]:
            data["playlists"][new_name] = data["playlists"].pop(old_name)
            cls._save()
            return True
        return False

    @classmethod
    def add_to_playlist(cls, name, filepath):
        if not filepath:
            return False
        abs_p = os.path.abspath(filepath)
        data = cls._load()
        if name not in data["playlists"]:
            data["playlists"][name] = []
        if abs_p not in data["playlists"][name]:
            data["playlists"][name].append(abs_p)
            cls._save()
            return True
        return False

    @classmethod
    def remove_from_playlist(cls, name, filepath):
        if not filepath:
            return False
        abs_p = os.path.abspath(filepath)
        data = cls._load()
        if name in data["playlists"] and abs_p in data["playlists"][name]:
            data["playlists"][name].remove(abs_p)
            cls._save()
            return True
        return False

    @classmethod
    def get_playlist_tracks(cls, name):
        data = cls._load()
        return list(data["playlists"].get(name, []))
