from typing import List
from gi.repository import Gdk


class ShortCut:
    def __init__(self, keyvals: List[int]) -> None:
        self._keyvals = frozenset(keyvals)

    def __eq__(self, other):
        if isinstance(other, ShortCut):
            return self._keyvals == other._keyvals
        return False

    def __hash__(self):
        return hash(self._keyvals)

    def __repr__(self):
        return "+".join([self.keyval_name(key) for key in self._keyvals])
    
    def keyval_name(self, key):
        button_names = {
            1: "Left",
            2: "Middle",
            3: "Right",
            4: "Back",
            5: "Forward"
        }
        if key<=5:
            return button_names[key]
        else:
            return Gdk.keyval_name(key)

    @property
    def length(self):
        return len(self._keyvals)

    @property
    def key(self):
        return self._keyvals
