import os
import math
import subprocess
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


# Tuned EQ Presets including Bang & Olufsen / HP Audio profiles
EQ_PRESETS = {
    "Flat": [0.0] * 10,
    "B&O Signature (HP Victus)": [5.0, 4.0, 2.5, 0.5, 1.0, 1.5, 2.5, 3.5, 4.5, 5.0],
    "B&O Spatial Immersion": [4.0, 3.0, 1.5, 1.0, 2.0, 3.0, 3.5, 4.0, 5.0, 5.5],
    "B&O Cinema & Vocal": [6.0, 5.0, 2.0, 0.0, 2.5, 3.5, 3.0, 2.5, 3.5, 4.0],
    "Rock": [4.5, 3.5, 2.0, -1.0, -0.5, 1.0, 2.5, 3.5, 4.0, 4.5],
    "Pop": [-1.5, 1.0, 3.0, 3.5, 2.0, -1.0, -1.5, -1.5, 1.0, 2.0],
    "Jazz": [3.0, 2.0, 1.0, 1.5, -1.5, -1.5, 0.0, 1.5, 2.5, 3.0],
    "Mega Bass / Sub Boost": [8.0, 7.0, 5.5, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "Subsonic / Turntable Rumble Cut": [-10.0, -8.0, -4.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "Vocal / Clarity": [-2.0, -1.0, 0.0, 2.5, 4.0, 4.5, 3.0, 1.5, 0.5, -0.5],
    "Club / Dance": [5.5, 4.5, 2.0, 0.0, 0.0, 0.0, 2.0, 3.5, 4.5, 5.0],
    "Electronic / Synthwave": [6.0, 5.0, 3.0, 0.5, -0.5, 1.0, 2.5, 4.0, 5.0, 5.5]
}


class AudioEngine(QObject):
    """
    GStreamer & PulseAudio high-fidelity audio engine with 10-band hardware EQ,
    audiopanorama stereo balancing, preamp gain stage, real-time peak level metering,
    playback pitch/rate scaling, and EOS auto-advance.
    """
    position_changed = pyqtSignal(float, float)  # (current_sec, duration_sec)
    state_changed = pyqtSignal(str)             # "PLAYING", "PAUSED", "STOPPED"
    track_finished = pyqtSignal()               # Auto-play next song trigger
    audio_level = pyqtSignal(float, float)      # (left_level 0..1, right_level 0..1)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        Gst.init(None)

        self._player = Gst.ElementFactory.make("playbin", "retro_walkman_playbin")
        self._eq = None
        self._pan = None
        self._preamp = None
        self._driver = "pulsesink"
        self._device = "default"
        self._buffer_time_ms = 100
        self._setup_audio_sink()

        self._bus = self._player.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._on_bus_message)

        self._current_path = None
        self._duration = 0.0
        self._state = "STOPPED"
        self._volume = 0.85
        self._player.set_property("volume", self._volume)

        # GLib mainloop dispatcher timer for Gst events inside Qt
        self._glib_timer = QTimer(self)
        self._glib_timer.timeout.connect(self._pump_glib)
        self._glib_timer.start(25)

        # Polling timer for smooth position updates
        self._pos_timer = QTimer(self)
        self._pos_timer.timeout.connect(self._poll_position)
        self._pos_timer.start(80)

        self._decay_l = 0.0
        self._decay_r = 0.0
        self._current_eq_preset = "B&O Signature (HP Victus)"
        self._eq_gains = list(EQ_PRESETS["B&O Signature (HP Victus)"])
        self._panning = 0.0
        self._preamp_db = 0.0
        self._mega_bass_enabled = False
        self._dolby_nr_enabled = False
        self._phono_enabled = False
        self._playback_rate = 1.0

        # Apply initial preset
        for idx, g in enumerate(self._eq_gains):
            self.set_eq_band(idx, g)

    def _setup_audio_sink(self):
        sink_el = "pulsesink"
        if self._driver == "alsasink":
            sink_el = "alsasink"
        elif self._driver == "autoaudiosink":
            sink_el = "autoaudiosink"
        else:
            sink_el = "pulsesink"
            if self._device and self._device != "default":
                sink_el = f'pulsesink device="{self._device}"'

        buf_ns = int(self._buffer_time_ms * 1000000)
        sink_recipes = [
            f"equalizer-10bands name=walkman_eq ! audiopanorama name=walkman_pan ! volume name=walkman_preamp ! level name=walkman_level interval=40000000 ! {sink_el}",
            "equalizer-10bands name=walkman_eq ! audiopanorama name=walkman_pan ! volume name=walkman_preamp ! level name=walkman_level interval=40000000 ! pulsesink",
            "equalizer-10bands name=walkman_eq ! audiopanorama name=walkman_pan ! volume name=walkman_preamp ! level name=walkman_level interval=40000000 ! autoaudiosink",
            "level name=walkman_level interval=40000000 ! autoaudiosink"
        ]

        for recipe in sink_recipes:
            try:
                sink_bin = Gst.parse_bin_from_description(recipe, True)
                self._eq = sink_bin.get_by_name("walkman_eq")
                self._pan = sink_bin.get_by_name("walkman_pan")
                self._preamp = sink_bin.get_by_name("walkman_preamp")
                self._player.set_property("audio-sink", sink_bin)
                print(f"AudioEngine: Initialized sink pipeline ({recipe.split('!')[-1].strip()})")
                break
            except Exception as e:
                continue

        # Re-apply current DSP parameters to new sink elements
        if hasattr(self, '_eq_gains'):
            for idx, g in enumerate(self._eq_gains):
                self.set_eq_band(idx, g)
        if hasattr(self, '_panning'):
            self.set_panning(self._panning)
        if hasattr(self, '_preamp_db'):
            self.set_preamp_gain(self._preamp_db)

    @staticmethod
    def get_available_sinks():
        """Returns list of (sink_id, display_name) for available PulseAudio/ALSA audio output sinks."""
        sinks = [("default", "System Default PulseAudio Output")]
        try:
            out = subprocess.check_output(["pactl", "list", "sinks"], text=True, timeout=2)
            cur_name = None
            cur_desc = None
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("Name:"):
                    cur_name = line.split(":", 1)[1].strip()
                elif line.startswith("Description:"):
                    cur_desc = line.split(":", 1)[1].strip()
                    if cur_name and cur_desc:
                        desc = cur_desc
                        if any(k in cur_name or k in cur_desc for k in ["HiFi", "Family", "Generic", "Victus"]):
                            desc += " [HP Victus B&O Hardware]"
                        sinks.append((cur_name, desc))
                        cur_name = None
                        cur_desc = None
        except Exception:
            pass
        return sinks

    def get_audio_output(self):
        return {
            "driver": self._driver,
            "device": self._device,
            "buffer_time_ms": self._buffer_time_ms
        }

    def set_audio_output(self, driver="pulsesink", device="default", buffer_time_ms=100):
        """Switches the audio sink dynamically, preserving playback state if playing."""
        was_playing = (self._state == "PLAYING")
        curr_pos = self.get_position()
        self._player.set_state(Gst.State.NULL)
        
        self._driver = driver
        self._device = device
        self._buffer_time_ms = int(buffer_time_ms)
        self._setup_audio_sink()
        
        if self._current_path:
            self._player.set_property("uri", f"file://{os.path.abspath(self._current_path)}")
            if was_playing:
                self.play()
                self.seek(curr_pos)

    def set_eq_band(self, band_idx, gain_db):
        gain_db = max(-24.0, min(12.0, float(gain_db)))
        if 0 <= band_idx < 10:
            self._eq_gains[band_idx] = gain_db
            if self._eq:
                try:
                    self._eq.set_property(f"band{band_idx}", gain_db)
                except Exception as e:
                    pass

    def get_eq_gains(self):
        return list(self._eq_gains)

    def set_eq_preset(self, preset_name):
        if preset_name in EQ_PRESETS:
            self._current_eq_preset = preset_name
            gains = EQ_PRESETS[preset_name]
            for idx, g in enumerate(gains):
                self.set_eq_band(idx, g)

    def set_panning(self, pan_val):
        """
        -1.0 = 100% Left, 0.0 = Center, +1.0 = 100% Right
        """
        self._panning = max(-1.0, min(1.0, float(pan_val)))
        if self._pan:
            try:
                self._pan.set_property("panorama", self._panning)
            except Exception:
                pass

    def set_preamp_gain(self, db_val):
        """
        Adjusts hardware preamp gain from -24dB to +12dB.
        """
        self._preamp_db = max(-24.0, min(12.0, float(db_val)))
        if self._preamp:
            try:
                linear = math.pow(10.0, self._preamp_db / 20.0)
                self._preamp.set_property("volume", linear)
            except Exception:
                pass

    def set_tone(self, bass_norm, treble_norm):
        """
        Adjusts low shelf (31Hz, 62Hz) and high shelf (8kHz, 16kHz) from normalized 0.0-1.0 dials.
        """
        # Map 0.0-1.0 to -12dB to +12dB
        bass_db = (bass_norm - 0.5) * 24.0
        treble_db = (treble_norm - 0.5) * 24.0

        self.set_eq_band(0, bass_db)
        self.set_eq_band(1, bass_db * 0.8)
        self.set_eq_band(8, treble_db * 0.8)
        self.set_eq_band(9, treble_db)

    def set_mega_bass(self, enabled):
        self._mega_bass_enabled = bool(enabled)
        boost = 7.5 if self._mega_bass_enabled else 0.0
        self.set_eq_band(0, self._eq_gains[0] + boost)
        self.set_eq_band(1, self._eq_gains[1] + boost * 0.7)

    def set_dolby_nr(self, enabled):
        self._dolby_nr_enabled = bool(enabled)
        # Cuts high frequency tape hiss by 3.5dB
        cut = -3.5 if self._dolby_nr_enabled else 0.0
        self.set_eq_band(9, self._eq_gains[9] + cut)

    def set_phono_preamp(self, enabled):
        self._phono_enabled = bool(enabled)
        # Classic warm RIAA phono pre-amplification curve
        if self._phono_enabled:
            self.set_eq_band(0, 6.0)
            self.set_eq_band(1, 4.5)
            self.set_eq_band(2, 2.0)
            self.set_eq_band(8, -1.0)
            self.set_eq_band(9, -2.5)
        else:
            self.set_eq_preset(self._current_eq_preset)

    def set_vocal_boost(self, boost_db):
        """
        Boosts 1kHz, 2kHz, and 4kHz voice presence bands (used by lyrics teleprompter vocal knob).
        """
        boost = max(-6.0, min(10.0, float(boost_db)))
        self.set_eq_band(5, self._eq_gains[5] + boost)
        self.set_eq_band(6, self._eq_gains[6] + boost * 0.9)
        self.set_eq_band(7, self._eq_gains[7] + boost * 0.6)

    def set_playback_rate(self, rate_0_8_to_1_2):
        """
        Adjusts playback rate/pitch (e.g. vinyl pitch knob 33 to 45 RPM).
        """
        self._playback_rate = max(0.8, min(1.25, float(rate_0_8_to_1_2)))
        if self._state == "PLAYING" and self._duration > 0:
            success_pos, pos_ns = self._player.query_position(Gst.Format.TIME)
            pos_ns = pos_ns if success_pos else 0
            self._player.seek(
                self._playback_rate,
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                Gst.SeekType.SET, pos_ns,
                Gst.SeekType.NONE, 0
            )

    def _pump_glib(self):
        ctx = GLib.MainContext.default()
        count = 0
        while ctx.pending() and count < 15:
            ctx.iteration(False)
            count += 1

    def _on_bus_message(self, bus, msg):
        msg_type = msg.type
        if msg_type == Gst.MessageType.EOS:
            self._state = "STOPPED"
            self.state_changed.emit(self._state)
            self.track_finished.emit()

        elif msg_type == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            self._state = "STOPPED"
            self.state_changed.emit(self._state)
            self.error_occurred.emit(str(err))

        elif msg_type == Gst.MessageType.ELEMENT:
            s = msg.get_structure()
            if s and s.get_name() == "level":
                self._handle_level_message(s)

    def _handle_level_message(self, s):
        peaks = s.get_value("peak")
        if not peaks:
            return

        def db_to_linear(db_val):
            clamped = max(-60.0, min(0.0, float(db_val)))
            norm = (clamped + 60.0) / 60.0
            return math.pow(norm, 1.3)

        if len(peaks) >= 2:
            l_val = db_to_linear(peaks[0])
            r_val = db_to_linear(peaks[1])
        else:
            val = db_to_linear(peaks[0])
            l_val, r_val = val, val

        self._decay_l = max(l_val, self._decay_l * 0.82)
        self._decay_r = max(r_val, self._decay_r * 0.82)
        self.audio_level.emit(self._decay_l, self._decay_r)

    def _poll_position(self):
        if self._state == "PLAYING":
            success_pos, pos_ns = self._player.query_position(Gst.Format.TIME)
            pos_sec = (pos_ns / Gst.SECOND) if success_pos else 0.0

            if self._duration <= 0.0:
                success_dur, dur_ns = self._player.query_duration(Gst.Format.TIME)
                if success_dur and dur_ns > 0:
                    self._duration = dur_ns / Gst.SECOND

            self.position_changed.emit(pos_sec, self._duration)

    def load(self, filepath, known_duration=0.0, auto_start=False):
        self._current_path = os.path.abspath(filepath)
        self._duration = float(known_duration) if known_duration > 0 else 0.0

        uri = Gst.filename_to_uri(self._current_path)
        # Fast transition: READY keeps the PulseAudio/PipeWire sink active without reopening device
        self._player.set_state(Gst.State.READY)
        self._player.set_property("uri", uri)
        if auto_start:
            self._player.set_state(Gst.State.PLAYING)
            self._state = "PLAYING"
            self.state_changed.emit(self._state)
        else:
            self._state = "READY"
            self.state_changed.emit(self._state)

        self._decay_l = 0.0
        self._decay_r = 0.0
        self.audio_level.emit(0.0, 0.0)
        self.position_changed.emit(0.0, self._duration)

    def play(self):
        if not self._current_path:
            return
        self._player.set_state(Gst.State.PLAYING)
        self._state = "PLAYING"
        self.state_changed.emit(self._state)

    def pause(self):
        if self._state == "PLAYING":
            self._player.set_state(Gst.State.PAUSED)
            self._state = "PAUSED"
            self.state_changed.emit(self._state)
            self.audio_level.emit(0.0, 0.0)

    def toggle_play_pause(self):
        if self._state == "PLAYING":
            self.pause()
        else:
            self.play()

    def stop(self):
        self._player.set_state(Gst.State.NULL)
        self._state = "STOPPED"
        self._decay_l = 0.0
        self._decay_r = 0.0
        self.state_changed.emit(self._state)
        self.audio_level.emit(0.0, 0.0)
        self.position_changed.emit(0.0, self._duration)

    def seek(self, target_sec):
        if self._duration > 0:
            target_sec = max(0.0, min(float(target_sec), self._duration))
            pos_ns = int(target_sec * Gst.SECOND)
            self._player.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                pos_ns
            )

    def seek_relative(self, delta_sec):
        success_pos, pos_ns = self._player.query_position(Gst.Format.TIME)
        curr = (pos_ns / Gst.SECOND) if success_pos else 0.0
        self.seek(curr + delta_sec)

    def set_volume(self, val_0_to_1):
        self._volume = max(0.0, min(1.0, float(val_0_to_1)))
        self._player.set_property("volume", self._volume)

    def get_volume(self):
        return self._volume

    def is_playing(self):
        return self._state == "PLAYING"

    def is_paused(self):
        return self._state == "PAUSED"

    def get_duration(self):
        return self._duration

    def get_current_path(self):
        return self._current_path
