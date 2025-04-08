#!/usr/bin/env python3
"""
Winkler Titrator - Main entry point
"""

import sys
from PyQt6.QtWidgets import QApplication
from main import AppWindow

def main():
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 