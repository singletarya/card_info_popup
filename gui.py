# gui.py

from aqt import mw
from aqt.qt import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QLabel, QPushButton
)

def launch_gui():
    dlg = QDialog(mw)
    dlg.setWindowTitle("Anki Study Analytics")
    dlg.resize(600, 400)

    # Create tab container
    tabs = QTabWidget()

    # ---------------------
    # TAB 1 — Descriptive Stats
    # ---------------------
    tab1 = QWidget()
    t1_layout = QVBoxLayout()

    t1_label = QLabel("Descriptive Statistics (Mean, Median, Mode, etc.)")
    t1_layout.addWidget(t1_label)

    t1_refresh = QPushButton("Refresh Descriptive Stats")
    t1_layout.addWidget(t1_refresh)

    tab1.setLayout(t1_layout)
    tabs.addTab(tab1, "Descriptive Stats")

    # ---------------------
    # TAB 2 — Analytical Stats
    # ---------------------
    tab2 = QWidget()
    t2_layout = QVBoxLayout()

    t2_label = QLabel("Analytical Statistics (Trends, correlations, etc.)")
    t2_layout.addWidget(t2_label)

    t2_button = QPushButton("Compute Analytical Stats")
    t2_layout.addWidget(t2_button)

    tab2.setLayout(t2_layout)
    tabs.addTab(tab2, "Analytical Stats")

    # ---------------------
    # TAB 3 — Session Overview
    # ---------------------
    tab3 = QWidget()
    t3_layout = QVBoxLayout()

    t3_label = QLabel("Today's Study Session Overview")
    t3_layout.addWidget(t3_label)

    t3_button = QPushButton("Load Session Summary")
    t3_layout.addWidget(t3_button)

    tab3.setLayout(t3_layout)
    tabs.addTab(tab3, "Session Overview")

    # Layout for dialog
    main_layout = QVBoxLayout()
    main_layout.addWidget(tabs)

    dlg.setLayout(main_layout)
    dlg.exec()
