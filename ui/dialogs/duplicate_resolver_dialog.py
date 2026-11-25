import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QFrame, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from backend.duplicate_detector import DuplicateDetector


class DuplicateResolverDialog(QDialog):
    """
    Cybernetic dialog displaying grouped duplicate songs with bitrates,
    file paths, and quality indicators, allowing one-click purging of lower-quality copies.
    """
    duplicates_purged = pyqtSignal(list)  # list of indexes to remove

    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self.dup_groups = DuplicateDetector.find_duplicates(playlist)

        self.setWindowTitle("DUPLICATE TRACKS DETECTOR & RESOLVER")
        self.resize(750, 480)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #15181f, stop:0.5 #0d1014, stop:1 #06080a);
                border: 2px solid #ffaa00;
                border-radius: 10px;
            }
            QLabel {
                color: #b0c0d0;
                font-family: Monospace;
            }
            QTreeWidget {
                background: #080a0d;
                border: 1px solid #28303c;
                border-radius: 6px;
                color: #e2e8f0;
                font-family: Monospace;
                font-size: 11px;
            }
            QHeaderView::section {
                background: #141a22;
                color: #ffaa00;
                padding: 4px;
                font-family: Monospace;
                font-weight: bold;
                font-size: 10px;
                border: 1px solid #242c38;
            }
            QScrollBar:horizontal {
                background: #080a0d;
                height: 8px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #253346;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover { background: #ffaa00; }
            QScrollBar:vertical {
                background: #080a0d;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #253346;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover { background: #ffaa00; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        hdr_row = QHBoxLayout()
        hdr_info = QVBoxLayout()
        t_lbl = QLabel("DUPLICATE TRACKS AUDIT CONSOLE")
        t_lbl.setStyleSheet("color: #ffaa00; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        
        total_dups = sum(len(g["items"]) - 1 for g in self.dup_groups)
        self.lbl_sub = QLabel(f"Found {len(self.dup_groups)} duplicate group(s) ({total_dups} redundant files).")
        self.lbl_sub.setStyleSheet("color: #94a3b8; font-size: 11px;")

        hdr_info.addWidget(t_lbl)
        hdr_info.addWidget(self.lbl_sub)
        hdr_row.addLayout(hdr_info, 1)
        layout.addLayout(hdr_row)

        # Tree Widget displaying clusters
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Action / Track", "Bitrate / Quality", "Duration", "File Path"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.Stretch)

        self._populate_tree()
        layout.addWidget(self.tree, 1)

        # Bottom Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_auto_best = QPushButton("AUTO-KEEP HIGHEST QUALITY")
        self.btn_auto_best.setFixedHeight(34)
        self.btn_auto_best.setStyleSheet("""
            QPushButton {
                background: #b45309;
                border: 1px solid #f59e0b;
                border-radius: 5px;
                color: #ffffff;
                font-family: Monospace;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background: #d97706; }
        """)
        self.btn_auto_best.clicked.connect(self._auto_resolve_best)

        self.btn_keep_first = QPushButton("KEEP FIRST IN PLAYLIST")
        self.btn_keep_first.setFixedHeight(34)
        self.btn_keep_first.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                border: 1px solid #475569;
                border-radius: 5px;
                color: #cbd5e1;
                font-family: Monospace;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background: #334155; }
        """)
        self.btn_keep_first.clicked.connect(self._auto_resolve_first)

        self.btn_close = QPushButton("CANCEL")
        self.btn_close.setFixedHeight(34)
        self.btn_close.setStyleSheet("background: #0f172a; border: 1px solid #334155; border-radius: 5px; color: #94a3b8; font-family: Monospace; font-weight: bold;")
        self.btn_close.clicked.connect(self.reject)

        btn_row.addWidget(self.btn_auto_best, 2)
        btn_row.addWidget(self.btn_keep_first, 1)
        btn_row.addWidget(self.btn_close, 1)
        layout.addLayout(btn_row)

    def _populate_tree(self):
        self.tree.clear()
        if not self.dup_groups:
            item = QTreeWidgetItem(["No duplicate songs detected in current library!", "", "", ""])
            item.setForeground(0, QColor("#22c55e"))
            self.tree.addTopLevelItem(item)
            return

        for g in self.dup_groups:
            parent_item = QTreeWidgetItem([f"{g['name']}", f"{len(g['items'])} copies", "", ""])
            parent_item.setForeground(0, QColor("#ffaa00"))
            parent_item.setFont(0, QFont("Monospace", 10, QFont.Bold))

            best_idx = g["best_index"]
            for m in g["items"]:
                idx = m["index"]
                meta = m["meta"]
                is_best = (idx == best_idx)

                dur_s = int(meta.get("duration", 0))
                dur_str = f"{dur_s // 60:02d}:{dur_s % 60:02d}"
                ext = os.path.splitext(meta.get("path", ""))[1].upper()
                quality_str = f"{ext} {meta.get('bitrate', 128)}k"
                if is_best:
                    quality_str += " [BEST]"

                action_str = f"[{'KEEP' if is_best else 'PURGE'}] #{idx + 1}: {meta.get('title', 'Unknown')}"
                child = QTreeWidgetItem([action_str, quality_str, dur_str, meta.get("path", "")])
                child.setData(0, Qt.UserRole, idx)

                if is_best:
                    child.setForeground(0, QColor("#39ff14"))
                    child.setForeground(1, QColor("#39ff14"))
                else:
                    child.setForeground(0, QColor("#ef4444"))
                    child.setForeground(1, QColor("#94a3b8"))

                parent_item.addChild(child)

            self.tree.addTopLevelItem(parent_item)
            parent_item.setExpanded(True)

    def _auto_resolve_best(self):
        to_remove = []
        for g in self.dup_groups:
            best_idx = g["best_index"]
            for m in g["items"]:
                if m["index"] != best_idx:
                    to_remove.append(m["index"])

        if not to_remove:
            QMessageBox.information(self, "No Duplicates", "No redundant copies to remove.")
            return

        reply = QMessageBox.question(
            self, "Confirm Duplicate Removal",
            f"Remove {len(to_remove)} redundant duplicate copies from playlist, keeping the highest quality version?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.duplicates_purged.emit(sorted(to_remove, reverse=True))
            self.accept()

    def _auto_resolve_first(self):
        to_remove = []
        for g in self.dup_groups:
            first_idx = g["items"][0]["index"]
            for m in g["items"][1:]:
                to_remove.append(m["index"])

        if not to_remove:
            return

        reply = QMessageBox.question(
            self, "Confirm Duplicate Removal",
            f"Remove {len(to_remove)} duplicate copies from playlist, keeping the first occurrence?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.duplicates_purged.emit(sorted(to_remove, reverse=True))
            self.accept()
