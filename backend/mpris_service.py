import os
import urllib.parse
from PyQt5.QtCore import QObject, pyqtSignal

try:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False


class MPRIS2Service(QObject):
    """
    Standard MPRIS2 D-Bus Interface (org.mpris.MediaPlayer2.retro_walkman)
    Allows Retro Walkman Pro to appear in:
    - GNOME Shell Top Bar / Notification Shade
    - GNOME Lock Screen with Play/Pause, Next/Prev, Cover Art
    - Respond to hardware media keys on keyboard
    """
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    play_pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    next_requested = pyqtSignal()
    prev_requested = pyqtSignal()
    seek_requested = pyqtSignal(float)
    raise_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bus_name = None
        self._root_obj = None
        self._is_registered = False

        self._playback_status = "Stopped"
        self._volume = 0.85
        self._position_us = 0
        self._metadata = {}

        if HAS_DBUS:
            self._setup_dbus()

    def _setup_dbus(self):
        try:
            DBusGMainLoop(set_as_default=True)
            self._session_bus = dbus.SessionBus()
            self._bus_name = dbus.service.BusName("org.mpris.MediaPlayer2.retro_walkman", self._session_bus)
            self._root_obj = _MPRISDbusObject(self, self._session_bus)
            self._is_registered = True
            print("MPRIS2: Successfully registered on session bus (org.mpris.MediaPlayer2.retro_walkman)")
        except Exception as e:
            print(f"MPRIS2: Registration skipped or failed: {e}")

    def update_track(self, title, artist, album, art_path, duration_sec):
        if not self._is_registered:
            return

        art_url = ""
        if art_path and os.path.exists(art_path):
            art_url = "file://" + urllib.parse.quote(os.path.abspath(art_path))

        length_us = int(float(duration_sec or 0) * 1000000)
        meta_dict = {
            "mpris:trackid": dbus.ObjectPath("/org/mpris/MediaPlayer2/Track/1", variant_level=1),
            "mpris:length": dbus.Int64(length_us, variant_level=1),
            "mpris:artUrl": dbus.String(art_url, variant_level=1),
            "xesam:title": dbus.String(title or "Unknown Title", variant_level=1),
            "xesam:artist": dbus.Array([dbus.String(artist or "Unknown Artist")], signature="s", variant_level=1),
            "xesam:album": dbus.String(album or "Unknown Album", variant_level=1)
        }
        self._metadata = meta_dict

        if self._root_obj:
            d = dbus.Dictionary({"Metadata": dbus.Dictionary(self._metadata, signature="sv", variant_level=1)}, signature="sv")
            self._root_obj.emit_property_changed("org.mpris.MediaPlayer2.Player", d)

    def update_playback_status(self, state_str):
        if not self._is_registered:
            return

        mapping = {
            "PLAYING": "Playing",
            "PAUSED": "Paused",
            "STOPPED": "Stopped"
        }
        self._playback_status = mapping.get(state_str, "Stopped")
        if self._root_obj:
            d = dbus.Dictionary({"PlaybackStatus": dbus.String(self._playback_status, variant_level=1)}, signature="sv")
            self._root_obj.emit_property_changed("org.mpris.MediaPlayer2.Player", d)

    def update_position(self, pos_sec):
        self._position_us = int(pos_sec * 1000000)

    def update_volume(self, vol_0_to_1):
        self._volume = max(0.0, min(1.0, float(vol_0_to_1)))
        if self._root_obj:
            d = dbus.Dictionary({"Volume": dbus.Double(self._volume, variant_level=1)}, signature="sv")
            self._root_obj.emit_property_changed("org.mpris.MediaPlayer2.Player", d)


if HAS_DBUS:
    class _MPRISDbusObject(dbus.service.Object):
        def __init__(self, service_wrapper, bus):
            super().__init__(bus, "/org/mpris/MediaPlayer2")
            self._srv = service_wrapper

        def emit_property_changed(self, interface, changed_props_dict):
            try:
                self.PropertiesChanged(
                    dbus.String(interface),
                    changed_props_dict,
                    dbus.Array([], signature="s")
                )
            except Exception as e:
                pass

        # ---------------------------------------------------------
        # org.freedesktop.DBus.Properties
        # ---------------------------------------------------------
        @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="ss", out_signature="v")
        def Get(self, interface_name, property_name):
            all_props = self.GetAll(interface_name)
            return all_props.get(property_name, "")

        @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}")
        def GetAll(self, interface_name):
            if interface_name == "org.mpris.MediaPlayer2":
                return dbus.Dictionary({
                    "CanQuit": dbus.Boolean(True, variant_level=1),
                    "CanRaise": dbus.Boolean(True, variant_level=1),
                    "HasTrackList": dbus.Boolean(False, variant_level=1),
                    "Identity": dbus.String("Retro Walkman Pro", variant_level=1),
                    "SupportedUriSchemes": dbus.Array([dbus.String("file"), dbus.String("http")], signature="s", variant_level=1),
                    "SupportedMimeTypes": dbus.Array([dbus.String("audio/mpeg"), dbus.String("audio/flac")], signature="s", variant_level=1)
                }, signature="sv")
            elif interface_name == "org.mpris.MediaPlayer2.Player":
                meta_val = dbus.Dictionary(self._srv._metadata, signature="sv", variant_level=1) if self._srv._metadata else dbus.Dictionary({}, signature="sv", variant_level=1)
                return dbus.Dictionary({
                    "PlaybackStatus": dbus.String(self._srv._playback_status, variant_level=1),
                    "LoopStatus": dbus.String("Playlist", variant_level=1),
                    "Rate": dbus.Double(1.0, variant_level=1),
                    "Shuffle": dbus.Boolean(False, variant_level=1),
                    "Metadata": meta_val,
                    "Volume": dbus.Double(self._srv._volume, variant_level=1),
                    "Position": dbus.Int64(self._srv._position_us, variant_level=1),
                    "MinimumRate": dbus.Double(1.0, variant_level=1),
                    "MaximumRate": dbus.Double(1.0, variant_level=1),
                    "CanControl": dbus.Boolean(True, variant_level=1),
                    "CanPlay": dbus.Boolean(True, variant_level=1),
                    "CanPause": dbus.Boolean(True, variant_level=1),
                    "CanSeek": dbus.Boolean(True, variant_level=1),
                    "CanGoNext": dbus.Boolean(True, variant_level=1),
                    "CanGoPrevious": dbus.Boolean(True, variant_level=1)
                }, signature="sv")
            return dbus.Dictionary({}, signature="sv")

        @dbus.service.signal("org.freedesktop.DBus.Properties", signature="sa{sv}as")
        def PropertiesChanged(self, interface_name, changed_properties, invalidated_properties):
            pass

        # ---------------------------------------------------------
        # org.mpris.MediaPlayer2
        # ---------------------------------------------------------
        @dbus.service.method("org.mpris.MediaPlayer2")
        def Raise(self):
            self._srv.raise_requested.emit()

        @dbus.service.method("org.mpris.MediaPlayer2")
        def Quit(self):
            self._srv.quit_requested.emit()

        # ---------------------------------------------------------
        # org.mpris.MediaPlayer2.Player
        # ---------------------------------------------------------
        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def Next(self):
            self._srv.next_requested.emit()

        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def Previous(self):
            self._srv.prev_requested.emit()

        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def Pause(self):
            self._srv.pause_requested.emit()

        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def PlayPause(self):
            self._srv.play_pause_requested.emit()

        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def Stop(self):
            self._srv.stop_requested.emit()

        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def Play(self):
            self._srv.play_requested.emit()

        @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature="x")
        def Seek(self, offset_us):
            offset_sec = float(offset_us) / 1000000.0
            self._srv.seek_requested.emit(offset_sec)
else:
    class _MPRISDbusObject:
        pass
