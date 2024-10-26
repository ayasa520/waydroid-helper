from typing import Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, GObject

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION


class ToolbarView(Gtk.Widget):
    __gtype_name__ = "ToolbarView"

    def __init__(self):
        super().__init__()
        if ADW_VERSION >= (1, 4, 0):
            self._toolbar_view = Adw.ToolbarView.new()
        else:
            self._toolbar_view = Gtk.Box.new(
                orientation=Gtk.Orientation.VERTICAL, spacing=10
            )
            self._top_bar = None
            self._content = None
            self._bottom_bar = None

        self.set_layout_manager(Gtk.BinLayout())
        self._toolbar_view.set_parent(self)
        self.connect("destroy", self.on_destroy)

    @classmethod
    def new(cls):
        return ToolbarView()

    def set_content(self, content: Optional[Gtk.Widget] = None) -> None:
        if ADW_VERSION >= (1, 4, 0):
            self._toolbar_view.set_content(content)
        else:
            if self._content:
                self._toolbar_view.remove(self._content)
            self._content = content
            if content:
                self._toolbar_view.insert_child_after(content, self._top_bar)
                content.set_vexpand(True)

    def add_top_bar(self, widget: Gtk.Widget):
        if ADW_VERSION >= (1, 4, 0):
            self._toolbar_view.add_top_bar(widget)
        else:
            if self._top_bar:
                self._toolbar_view.remove(self._top_bar)
            self._top_bar = widget
            if widget:
                self._toolbar_view.prepend(widget)
                # widget.set_hexpand(True)

    def add_bottom_bar(self, widget: Gtk.Widget):
        if ADW_VERSION >= (1, 4, 0):
            self._toolbar_view.add_bottom_bar(widget)
        else:
            if self._bottom_bar:
                self._toolbar_view.remove(self._bottom_bar)
            self._bottom_bar = widget
            if widget:
                self._toolbar_view.append(widget)

    def on_destroy(self, widget):
        self._toolbar_view.unparent()
        self._toolbar_view = None
