# Minimal, safe add-on entrypoint.
# Registers a "Anki Stats GUI" item in Tools -> menu that opens the GUI.

from aqt import mw
from aqt.qt import QAction
import traceback

def _open_stats_window():
    # Lazy import so optional deps don't block add-on load.
    try:
        from .gui.main import StatsWindow
    except Exception:
        print("anki_stats_gui: failed to import GUI:", flush=True)
        traceback.print_exc()
        return

    # Keep a single instance on mw so it's not GC'd and can be reused.
    if getattr(mw, "_anki_stats_gui_win", None) is None:
        mw._anki_stats_gui_win = StatsWindow(parent=mw)
    win = mw._anki_stats_gui_win
    win.show()
    try:
        win.raise_()
        win.activateWindow()
    except Exception:
        # Some platforms/backends may not support raise_/activateWindow
        pass

# Add Tools menu action
action = QAction("Anki Stats GUI", mw)
action.triggered.connect(_open_stats_window)
mw.form.menuTools.addAction(action)