# __init__.py

from aqt import mw
from aqt.qt import QAction
from .gui import launch_gui

def on_menu_click():
    launch_gui()

action = QAction("Open Stats GUI", mw)
action.triggered.connect(on_menu_click)

mw.form.menuTools.addAction(action)
