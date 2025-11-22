# anki_stats_gui/__init__.py
import sys
print(sys.path)
from aqt import mw
from aqt.qt import QAction

# Import your GUI tab
from .gui.tabs.temporal_tab import TemporalTab


# Function to launch the GUI in a separate window
def launch_gui():
    from PyQt6.QtWidgets import QMainWindow

    # Create a new main window to host the tab
    window = QMainWindow()
    window.setWindowTitle("Anki Temporal Learning Stats")

    # Instantiate the TemporalTab and set it as central widget
    tab = TemporalTab()
    window.setCentralWidget(tab)
    window.resize(900, 600)  # optional: set initial window size
    window.show()
    return window

# Add a menu item in Anki's Tools menu
action = QAction("Open Temporal Stats", mw)
action.triggered.connect(launch_gui)
mw.form.menuTools.addAction(action)
