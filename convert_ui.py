from PyQt6 import uic

# Input and output file paths
ui_file = "src/main/python/winkler.ui"
py_file = "src/main/python/winkler.py"

# Convert .ui file to .py
with open(py_file, 'w', encoding='utf-8') as f:
    uic.compileUi(ui_file, f) 