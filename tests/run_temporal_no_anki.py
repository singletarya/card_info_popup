# Standalone test harness to run TemporalLearningPatterns without Anki
# Usage: python tests/run_temporal_no_anki.py

import sys
import types
import os
import time
import datetime
from collections import defaultdict

# Create a fake 'aqt' module with a minimal 'mw' object
aqt = types.ModuleType("aqt")
mw = types.SimpleNamespace()
# mw.col will hold decks and a fake db object
class FakeDB:
    def __init__(self, rows, card_map):
        self._rows = rows
        self._card_map = card_map
    def all(self, query, **params):
        # ignore query string and just return rows; honor :did parameter if present
        did = params.get('did', None)
        if did is None:
            return list(self._rows)
        # filter rows by card -> deck mapping
        return [r for r in self._rows if self._card_map.get(r[1]) == did]

class FakeDecks:
    def __init__(self, decks_map):
        self._decks = decks_map
    def decks(self):
        return self._decks
    def all_names(self):
        return [v.get('name') for v in self._decks.values()]
    def id(self, name):
        for did, info in self._decks.items():
            if info.get('name') == name:
                return did
        return None

# Prepare some fake data: revlog rows are (time_ms, cid, id, ease, ivl, lastIvl, type)
now_ms = int(time.time() * 1000)
rows = [
    # recent review (1 minute ago) for card 1001
    (now_ms - 60 * 1000, 1001, 2001, 2.5, 1, 0, 0),
    # older review (2 days ago) for card 1002
    (now_ms - 2 * 24 * 60 * 60 * 1000, 1002, 2002, 2.5, 1, 0, 0),
    # a very old review (400 days ago) for card 1001
    (now_ms - 400 * 24 * 60 * 60 * 1000, 1001, 2003, 2.5, 1, 0, 0),
]
# Map card id -> deck id
card_map = {
    1001: 1,
    1002: 2,
}
# Deck definitions
decks_map = {
    1: {'name': 'Default'},
    2: {'name': 'Spanish'},
}

# Attach fake structures to mw
mw.col = types.SimpleNamespace()
mw.col.db = FakeDB(rows, card_map)
mw.col.decks = FakeDecks(decks_map)
# Put mw into the fake aqt module and inject into sys.modules before importing the addon
aqt.mw = mw
sys.modules['aqt'] = aqt
# Make sure the parent directory of the package is on sys.path so
# `import anki_stats_gui` works when running this script directly.
pkg_parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if pkg_parent not in sys.path:
    sys.path.insert(0, os.path.dirname(pkg_parent))

# Provide a lightweight placeholder package module for `anki_stats_gui` so we can
# import submodules without executing the addon's `__init__.py` (which imports
# real Anki UI objects). We set a __path__ so Python can find `analytics`.
import types as _types
pkg_dir = pkg_parent
pkg_mod = _types.ModuleType('anki_stats_gui')
pkg_mod.__path__ = [pkg_dir]
sys.modules['anki_stats_gui'] = pkg_mod

# Now import the analytics module from the add-on
from anki_stats_gui.analytics.temporal_patterns import TemporalLearningPatterns

p = TemporalLearningPatterns()
print("--- fetch_revlog(None) (all decks) ---")
all_rows = p.fetch_revlog(None)
print("rows returned:", len(all_rows))
for r in all_rows:
    ts = datetime.datetime.fromtimestamp(r[0]/1000)
    print(ts.isoformat(), "cid=", r[1])

print('\n--- fetch_revlog(deck_id=1) (Default deck) ---')
rows_d1 = p.fetch_revlog(1)
print('rows returned:', len(rows_d1))
for r in rows_d1:
    ts = datetime.datetime.fromtimestamp(r[0]/1000)
    print(ts.isoformat(), "cid=", r[1])

print('\n--- compute() results (uses fetch_revlog()) ---')
results = p.compute()
for k, v in results.items():
    print(f"{k}: {v}")

print('\nTest harness finished.')
