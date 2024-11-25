# pyright: reportUnknownMemberType=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false
# pyright: reportRedeclaration=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportAny=false
# pyright: reportCallIssue=false
# pyright: reportMissingSuperCall=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportUntypedBaseClass=false

from typing import final

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION

class SpinnerMeta(type(Gtk.Widget)):
    def __new__(mcs, name, bases, attrs):
        # final class
        for base in bases:
            if isinstance(base, SpinnerMeta):
                raise TypeError("type '{0}' is not an acceptable base type".format(base.__name__))

        if ADW_VERSION >= (1, 6, 0):
            def __init__(self):
                super(self.__class__, self).__init__()
                self._spinner = Adw.Spinner.new()
                self.set_layout_manager(Gtk.BinLayout())
                self._spinner.set_parent(self)
                self.connect("destroy", self.on_destroy)

            def set_spinning(self, spinning: bool):
                pass
        else:
            def __init__(self):
                super(self.__class__, self).__init__()
                self._spinner = Gtk.Spinner.new()
                self._spinner.start()
                self.set_layout_manager(Gtk.BinLayout())
                self._spinner.set_parent(self)
                self.connect("destroy", self.on_destroy)

            def set_spinning(self, spinning: bool):
                self._spinner.set_spinning(spinning)

        attrs["__init__"] = __init__
        attrs["set_spinning"] = set_spinning
        return super().__new__(mcs, name, bases, attrs)


@final
class Spinner(Gtk.Widget, metaclass=SpinnerMeta):
    __gtype_name__ = "Spinner"

    def set_halign(self, align: Gtk.Align) -> None:
        self._spinner.set_halign(align)

    def set_valign(self, align: Gtk.Align) -> None:
        self._spinner.set_valign(align)

    def set_size_request(self, width: int, height: int):
        self._spinner.set_size_request(width, height)

    def on_destroy(self, widget):
        self._spinner.unparent()
        self._spinner = None
    
    def __init__(self):
        pass    


Spinner.set_css_name("compat-spinner")