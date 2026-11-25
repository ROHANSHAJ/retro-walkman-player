#!/usr/bin/env python3
import sys
import os

# Ensure package root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.widgets.splash_screen import BootSplashScreen


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RetroWalkman")
    app.setOrganizationName("RetroWalkman")
    # Prevent Qt from quitting when splash screen or loading HUD closes before main window
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    splash = BootSplashScreen()

    def on_boot_complete():
        window.show()
        app.setQuitOnLastWindowClosed(True)
        # If file or folder passed on CLI, open it after window is shown
        if len(sys.argv) > 1:
            paths = sys.argv[1:]
            valid_paths = [p for p in paths if os.path.exists(p)]
            if valid_paths:
                window._add_paths(valid_paths, clear_first=True)

    splash.boot_finished.connect(on_boot_complete)
    splash.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
