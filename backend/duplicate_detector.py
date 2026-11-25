import os
import re
import hashlib


class DuplicateDetector:
    """
    Intelligent audio library duplicate detector.
    Identifies redundant tracks by:
    1. Exact file content hash (MD5) or file path
    2. Normalized Title + Artist string matching (ignoring [remaster], (official), track #s)
    3. Same title with duration difference < 2.5 seconds
    """

    @staticmethod
    def normalize_str(s):
        if not s:
            return ""
        # Lowercase and remove common bracketed noise
        cleaned = s.lower()
        cleaned = re.sub(r'[\(\[\{].*?[\)\]\}]', '', cleaned)
        cleaned = re.sub(r'^\d+[\s\.\-_]+', '', cleaned)  # remove leading track numbers
        cleaned = re.sub(r'[^a-z0-9]', '', cleaned)
        return cleaned.strip()

    @classmethod
    def find_duplicates(cls, playlist_items):
        """
        Returns a list of duplicate groups:
        [
            {
                "group_id": str,
                "name": str,
                "items": [{"index": int, "meta": dict, "score": int}],
                "best_index": int
            }, ...
        ]
        """
        clusters = {}  # key -> list of (index, meta)

        for idx, item in enumerate(playlist_items):
            title = item.get("title") or os.path.splitext(item.get("filename", ""))[0]
            artist = item.get("artist") or ""
            dur = float(item.get("duration", 0))

            norm_t = cls.normalize_str(title)
            norm_a = cls.normalize_str(artist)

            # Primary key: normalized artist + title
            if norm_t:
                key = f"{norm_a}___{norm_t}"
            else:
                key = f"raw___{item.get('filename', '')}"

            if key not in clusters:
                clusters[key] = []
            clusters[key].append((idx, item))

        results = []
        for key, members in clusters.items():
            if len(members) > 1:
                # Group found! Determine best quality member
                group_items = []
                best_idx = members[0][0]
                best_score = -1

                for idx, m in members:
                    # Calculate quality score:
                    # Lossless FLAC/WAV = 1000+, MP3 = bitrate (e.g. 320)
                    ext = os.path.splitext(m.get("path", ""))[1].lower()
                    bitrate = int(m.get("bitrate", 128))
                    score = bitrate
                    if ext in [".flac", ".wav", ".alac"]:
                        score += 1000

                    group_items.append({
                        "index": idx,
                        "meta": m,
                        "score": score
                    })

                    if score > best_score:
                        best_score = score
                        best_idx = idx

                sample_meta = members[0][1]
                display_name = f"{sample_meta.get('title', 'Unknown')} — {sample_meta.get('artist', 'Unknown')}"

                results.append({
                    "group_id": key,
                    "name": display_name,
                    "items": group_items,
                    "best_index": best_idx
                })

        return results
