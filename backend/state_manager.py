import os
import json
import threading

STATE_FILE = os.path.expanduser("~/.config/retro_walkman/app_state.json")
_SAVE_LOCK = threading.Lock()


class StateManager:
    @staticmethod
    def load_state():
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading state: {e}")
        return {
            "playlist": [],
            "current_index": 0,
            "volume": 0.85,
            "theme": "walkman",
            "repeat_mode": "ALL",
            "is_shuffled": False,
            "active_tab": 0
        }

    @staticmethod
    def save_state(state_dict, async_write=True):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        data_to_save = dict(state_dict)

        def _do_write():
            with _SAVE_LOCK:
                try:
                    tmp_path = f"{STATE_FILE}.tmp.{threading.get_ident()}"
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        json.dump(data_to_save, f, ensure_ascii=False)
                    os.replace(tmp_path, STATE_FILE)
                except Exception as e:
                    print(f"Error saving state: {e}")

        if async_write:
            threading.Thread(target=_do_write, daemon=True).start()
        else:
            _do_write()
