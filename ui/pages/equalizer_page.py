from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QFrame, QComboBox, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from ui.widgets.rotary_knob import RotaryKnob
from ui.widgets.vu_meter import StereoVUMeter
from backend.audio_engine import EQ_PRESETS


BAND_LABELS = ["31Hz", "62Hz", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz", "8kHz", "16kHz"]


class EqualizerPage(QWidget):
    band_changed = pyqtSignal(int, float)      # band_idx, gain_db
    preset_selected = pyqtSignal(str)          # preset_name
    volume_changed = pyqtSignal(float)         # 0.0 to 1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sliders = []
        self._labels = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(14)

        # Header: Preset selector & Reset button
        hdr_box = QHBoxLayout()
        hdr_lbl = QLabel("10-BAND STUDIO GRAPHIC EQUALIZER & DSP")
        hdr_lbl.setStyleSheet("color: #00f0ff; font-size: 13px; font-weight: bold; letter-spacing: 1px;")

        self.preset_combo = QComboBox()
        for p in EQ_PRESETS.keys():
            self.preset_combo.addItem(p)
        self.preset_combo.setStyleSheet("""
            QComboBox {
                background: #14171a;
                border: 1px solid #323842;
                border-radius: 4px;
                padding: 4px 10px;
                color: #e0e4e8;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)

        btn_reset = QPushButton("Reset Flat")
        btn_reset.setStyleSheet("""
            QPushButton {
                background: #20242a;
                border: 1px solid #3a424e;
                border-radius: 4px;
                padding: 4px 12px;
                color: #b0b8c2;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #303640; color: #ffffff; }
        """)
        btn_reset.clicked.connect(lambda: self.preset_combo.setCurrentText("Flat"))

        hdr_box.addWidget(hdr_lbl)
        hdr_box.addStretch()
        hdr_box.addWidget(QLabel("PRESET:"))
        hdr_box.addWidget(self.preset_combo)
        hdr_box.addWidget(btn_reset)
        layout.addLayout(hdr_box)

        # Equalizer Deck Box
        eq_box = QFrame()
        eq_box.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #181b1f, stop:0.04 #141619, stop:0.96 #111315, stop:1 #0b0c0e);
                border: 2px solid #2b3038;
                border-radius: 8px;
            }
        """)
        eq_layout = QVBoxLayout(eq_box)
        eq_layout.setContentsMargins(16, 16, 16, 16)

        # Faders row
        fader_row = QHBoxLayout()
        fader_row.setSpacing(12)

        # dB markings on left
        db_scale = QVBoxLayout()
        for label in ["+12dB", "+6dB", " 0dB", "-6dB", "-12dB", "-24dB"]:
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #606872; font-family: Monospace; font-size: 9px; font-weight: bold;")
            db_scale.addWidget(lbl)
        fader_row.addLayout(db_scale)

        # 10 vertical sliders
        for i, band_name in enumerate(BAND_LABELS):
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignCenter)
            col.setSpacing(4)

            val_lbl = QLabel("0.0")
            val_lbl.setStyleSheet("color: #00f0ff; font-family: Monospace; font-size: 10px; font-weight: bold;")
            val_lbl.setAlignment(Qt.AlignCenter)
            self._labels.append(val_lbl)

            slider = QSlider(Qt.Vertical)
            slider.setRange(-24, 12)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBothSides)
            slider.setTickInterval(6)
            slider.setStyleSheet("""
                QSlider::groove:vertical {
                    width: 6px;
                    background: #0d0f11;
                    border: 1px solid #282d34;
                    border-radius: 3px;
                }
                QSlider::sub-page:vertical {
                    background: #00f0ff;
                    border-radius: 3px;
                }
                QSlider::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #d0d6de, stop:0.5 #9096a0, stop:1 #606670);
                    border: 1px solid #16181b;
                    height: 16px;
                    margin-left: -6px;
                    margin-right: -6px;
                    border-radius: 4px;
                }
            """)
            slider.valueChanged.connect(lambda val, idx=i: self._on_slider_changed(idx, val))
            self._sliders.append(slider)

            name_lbl = QLabel(band_name)
            name_lbl.setStyleSheet("color: #a0a8b2; font-size: 10px; font-weight: bold;")
            name_lbl.setAlignment(Qt.AlignCenter)

            col.addWidget(val_lbl)
            col.addWidget(slider, 1)
            col.addWidget(name_lbl)
            fader_row.addLayout(col)

        eq_layout.addLayout(fader_row)
        layout.addWidget(eq_box, 1)

        # Bottom row: Master Volume rotary knob + Stereo VU meter
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(20)

        # Left: Rotary knob
        knob_box = QHBoxLayout()
        self.vol_knob = RotaryKnob(style_mode="black")
        self.vol_knob.valueChanged.connect(self.volume_changed.emit)
        knob_lbl = QLabel("MASTER LEVEL\nROTARY DIAL")
        knob_lbl.setStyleSheet("color: #a0a8b2; font-size: 10px; font-weight: bold;")
        knob_box.addWidget(self.vol_knob)
        knob_box.addWidget(knob_lbl)

        # Right: Stereo VU meter
        self.vu_meter = StereoVUMeter()

        bottom_row.addLayout(knob_box)
        bottom_row.addStretch()
        bottom_row.addWidget(self.vu_meter)
        layout.addLayout(bottom_row)

    def _on_slider_changed(self, idx, val):
        sign = "+" if val > 0 else ""
        self._labels[idx].setText(f"{sign}{val:.1f}")
        self.band_changed.emit(idx, float(val))

    def _on_preset_changed(self, preset_name):
        self.preset_selected.emit(preset_name)
        if preset_name in EQ_PRESETS:
            gains = EQ_PRESETS[preset_name]
            for idx, g in enumerate(gains):
                self._sliders[idx].blockSignals(True)
                self._sliders[idx].setValue(int(g))
                sign = "+" if g > 0 else ""
                self._labels[idx].setText(f"{sign}{g:.1f}")
                self._sliders[idx].blockSignals(False)

    def update_levels(self, l_val, r_val):
        self.vu_meter.set_levels(l_val, r_val)

    def set_theme(self, theme_key, pal):
        accent = pal.get("accent", "#00f0ff")
        knob_mode = "cyan" if theme_key == "glass" else ("silver" if theme_key == "ipod" else "black")
        self.vol_knob.set_style_mode(knob_mode)

        # Update slider styles
        slider_qss = f"""
            QSlider::groove:vertical {{
                width: 6px;
                background: #0d0f11;
                border: 1px solid #282d34;
                border-radius: 3px;
            }}
            QSlider::sub-page:vertical {{
                background: {accent};
                border-radius: 3px;
            }}
            QSlider::handle:vertical {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #d0d6de, stop:0.5 #9096a0, stop:1 #606670);
                border: 1px solid #16181b;
                height: 16px;
                margin-left: -6px;
                margin-right: -6px;
                border-radius: 4px;
            }}
        """
        for s in self._sliders:
            s.setStyleSheet(slider_qss)

        for lbl in self._labels:
            lbl.setStyleSheet(f"color: {accent}; font-family: Monospace; font-size: 10px; font-weight: bold;")
