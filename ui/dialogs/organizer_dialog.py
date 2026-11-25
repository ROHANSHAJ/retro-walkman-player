import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QCheckBox, QProgressBar, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from backend.library_organizer import OrganizerWorker


class OrganizerDialog(QDialog):
    library_organized = pyqtSignal(str)  # emits target virtual library dir path

    def __init__(self, default_source_dir=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Organize Library with Pointers (Symlinks)")
        self.setFixedSize(580, 440)
        self.setStyleSheet("""
            QDialog {
                background: #1e2024;
                color: #e0e4e8;
            }
            QLabel {
                color: #b0b6bc;
                font-size: 11px;
                font-weight: bold;
            }
            QLineEdit {
                background: #141618;
                border: 1px solid #383c44;
                border-radius: 4px;
                padding: 6px 8px;
                color: #ffffff;
                font-size: 11px;
            }
            QCheckBox {
                color: #e0e4e8;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton {
                background: #2e3238;
                border: 1px solid #454a54;
                border-radius: 4px;
                padding: 6px 14px;
                color: #e0e4e8;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3e444c;
            }
            QProgressBar {
                background: #141618;
                border: 1px solid #383c44;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: #ffb000;
                border-radius: 3px;
            }
        """)

        home_music = os.path.expanduser("~/Music")
        self.source_dir = default_source_dir or (home_music if os.path.exists(home_music) else os.path.expanduser("~"))
        self.target_dir = os.path.join(self.source_dir, "Virtual_Library")
        self.worker = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        hdr = QLabel("AUTO-FOLDER MUSIC USING POINTERS (SYMLINKS)")
        hdr.setStyleSheet("color: #ffb000; font-size: 13px; font-weight: bold;")
        layout.addWidget(hdr)

        # Informational banner
        info = QLabel(
            "Uses filesystem pointers (symlinks) — NO files are copied or duplicated.\n"
            "0 extra disk space is consumed, and your original music files remain safe."
        )
        info.setStyleSheet("color: #40c4ff; background: #0c2030; border: 1px solid #005580; padding: 8px; border-radius: 6px; font-size: 11px;")
        layout.addWidget(info)

        # Source folder
        layout.addWidget(QLabel("Source Music Folder:"))
        src_row = QHBoxLayout()
        self.txt_source = QLineEdit(self.source_dir)
        btn_src = QPushButton("Browse...")
        btn_src.clicked.connect(self._browse_source)
        src_row.addWidget(self.txt_source, 1)
        src_row.addWidget(btn_src)
        layout.addLayout(src_row)

        # Target folder
        layout.addWidget(QLabel("Target Virtual Library (Symlink Roots):"))
        tgt_row = QHBoxLayout()
        self.txt_target = QLineEdit(self.target_dir)
        btn_tgt = QPushButton("Browse...")
        btn_tgt.clicked.connect(self._browse_target)
        tgt_row.addWidget(self.txt_target, 1)
        tgt_row.addWidget(btn_tgt)
        layout.addLayout(tgt_row)

        # Organization options
        opts_box = QFrame()
        opts_box.setStyleSheet("background: #141618; border: 1px solid #282c32; border-radius: 6px; padding: 8px;")
        opts_layout = QVBoxLayout(opts_box)
        opts_layout.setSpacing(6)

        self.chk_artist = QCheckBox("Auto-Folder by Artist  (/By_Artist/<Artist>/<Album>/<Track>)")
        self.chk_artist.setChecked(True)
        self.chk_year = QCheckBox("Auto-Folder by Release Year  (/By_Year/<Year>/<Track>)")
        self.chk_year.setChecked(True)
        self.chk_genre = QCheckBox("Auto-Folder by Genre  (/By_Genre/<Genre>/<Track>)")
        self.chk_genre.setChecked(True)

        opts_layout.addWidget(self.chk_artist)
        opts_layout.addWidget(self.chk_year)
        opts_layout.addWidget(self.chk_genre)
        layout.addWidget(opts_box)

        # Progress bar & status
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_status = QLabel("Ready to organize.")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.lbl_status)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_cancel = QPushButton("Close")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_start = QPushButton("Create Pointers")
        self.btn_start.setStyleSheet("background: #ffb000; color: #1a1c1e; font-size: 12px;")
        self.btn_start.clicked.connect(self._start_organizing)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_start)
        layout.addLayout(btn_row)

    def _browse_source(self):
        d = QFileDialog.getExistingDirectory(self, "Select Source Music Folder", self.txt_source.text())
        if d:
            self.txt_source.setText(d)
            self.txt_target.setText(os.path.join(d, "Virtual_Library"))

    def _browse_target(self):
        d = QFileDialog.getExistingDirectory(self, "Select Target Virtual Library", self.txt_target.text())
        if d:
            self.txt_target.setText(d)

    def _start_organizing(self):
        src = self.txt_source.text().strip()
        tgt = self.txt_target.text().strip()
        if not os.path.exists(src):
            QMessageBox.critical(self, "Error", f"Source directory does not exist:\n{src}")
            return

        self.btn_start.setEnabled(False)
        self.btn_start.setText("Organizing...")
        self.progress_bar.setValue(0)

        self.worker = OrganizerWorker(
            source_dir=src,
            target_dir=tgt,
            group_by_artist=self.chk_artist.isChecked(),
            group_by_year=self.chk_year.isChecked(),
            group_by_genre=self.chk_genre.isChecked()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_summary.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current, total, msg):
        pct = int((current / float(total)) * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"[{current}/{total}] {msg}")

    def _on_finished(self, stats):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Create Pointers")
        self.progress_bar.setValue(100)
        self.lbl_status.setText(f"Done! Created {stats['symlinks_created']} pointers.")

        summary_msg = (
            f"Organization Complete!\n\n"
            f"• Scanned Audio Files: {stats['scanned_files']}\n"
            f"• Pointers Created: {stats['symlinks_created']}\n"
            f"• Pointers Skipped (Already existed): {stats['symlinks_skipped']}\n\n"
            f"Virtual library located at:\n{stats['target_dir']}\n\n"
            f"Would you like to open this virtual library in the player now?"
        )
        reply = QMessageBox.question(self, "Success", summary_msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.library_organized.emit(stats["target_dir"])
            self.accept()

    def _on_error(self, err_msg):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Create Pointers")
        QMessageBox.warning(self, "Organization Notice", err_msg)
