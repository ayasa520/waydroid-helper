import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION


class Spinner(Gtk.Widget):
    __gtype_name__ = "Spinner"

    def __init__(self):
        super().__init__()
        if ADW_VERSION >= (1, 6, 0):
            self._spinner = Adw.Spinner.new()
        else:
            self._spinner = Gtk.Spinner.new()
            self._spinner.start()

        self.set_layout_manager(Gtk.BinLayout())
        self._spinner.set_parent(self)
        self.connect("destroy", self.on_destroy)

    def set_halign(self, align: Gtk.Align) -> None:
        self._spinner.set_halign(align)

    def set_valign(self, align: Gtk.Align) -> None:
        self._spinner.set_valign(align)

    def set_size_request(self, width: int, height: int):
        self._spinner.set_size_request(width, height)

    def set_spinning(self, spinning: bool):
        if isinstance(self, Gtk.Spinner):
            self._spinner.set_spinning(spinning)

    def on_destroy(self, widget):
        self._spinner.unparent()
        self._spinner = None

Spinner.set_css_name("compat-spinner")