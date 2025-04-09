#!/usr/bin/env python3
"""
Winkler Titrator - Main entry point
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6 import uic

from .ui.winkler import AppWindow

def main():
    """Launch the Winkler Titrator application."""
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 