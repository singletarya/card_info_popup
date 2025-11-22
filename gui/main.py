# anki_stats_gui/main.py
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow

# Import your TemporalTab from the package
from gui.tabs import temporal_tab

def main():
    app = QApplication(sys.argv)

    # Create a main window and set the TemporalTab as central widget
    window = QMainWindow()
    window.setWindowTitle("Temporal Learning Stats (Standalone Test)")
    tab = temporal_tab()
    window.setCentralWidget(tab)
    window.resize(900, 600)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
