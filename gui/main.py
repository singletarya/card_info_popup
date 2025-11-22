# Simple main window that hosts your existing TemporalTab widget.
# Replace TemporalTab import with the class you implemented.

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

# Use package-qualified import to avoid top-level resolution issues.
from anki_stats_gui.gui.tabs.temporal_tab import TemporalTab

class StatsWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anki Stats GUI")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # Put your tab or main UI here
        self.temporal_tab = TemporalTab(self)
        layout.addWidget(self.temporal_tab)

        # Optional: set a reasonable default size
        self.resize(900, 600)