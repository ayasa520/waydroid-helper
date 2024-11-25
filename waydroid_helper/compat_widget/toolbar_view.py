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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, GObject, Gtk

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION


class ToolbarViewMeta(type(GObject.Object)):
    def __new__(mcs, name, bases, attrs):
        replace = False
        if ADW_VERSION < (1, 4, 0) and (Gtk.Widget in bases):
            replace = True

            def __init__(self):
                super(ToolbarView, self).__init__()
                self._toolbar_view = Gtk.Box.new(
                    orientation=Gtk.Orientation.VERTICAL, spacing=0
                )
                self._top_bar = None
                self._content = None
                self._bottom_bar = None
                self.set_layout_manager(Gtk.BinLayout())
                self._toolbar_view.set_parent(self)
                self.connect("destroy", self.on_destroy)

            def set_content(self, content: Gtk.Widget|None = None) -> None:
                if self._content:
                    self._toolbar_view.remove(self._content)
                self._content = content
                if content:
                    self._toolbar_view.insert_child_after(content, self._top_bar)
                    content.set_vexpand(True)

            def add_top_bar(self, widget: Gtk.Widget):
                if self._top_bar:
                    self._toolbar_view.remove(self._top_bar)
                self._top_bar = widget
                if widget:
                    self._toolbar_view.prepend(widget)

            def add_bottom_bar(self, widget: Gtk.Widget):
                if self._bottom_bar:
                    self._toolbar_view.remove(self._bottom_bar)
                self._bottom_bar = widget
                if widget:
                    self._toolbar_view.append(widget)

            def on_destroy(self, widget):
                self._toolbar_view.unparent()
                self._toolbar_view = None

            attrs["__init__"] = __init__
            attrs["set_content"] = set_content
            attrs["add_top_bar"] = add_top_bar
            attrs["add_bottom_bar"] = add_bottom_bar
            attrs["on_destroy"] = on_destroy

        if not replace:

            def __init__(self):
                super(ToolbarView, self).__init__()
                self._toolbar_view = Adw.ToolbarView.new()
                self.set_layout_manager(Gtk.BinLayout())
                self._toolbar_view.set_parent(self)
                self.connect("destroy", self.on_destroy)

            def set_content(self, content:Gtk.Widget|None = None) -> None:
                self._toolbar_view.set_content(content)

            def add_top_bar(self, widget: Gtk.Widget):
                self._toolbar_view.add_top_bar(widget)

            def add_bottom_bar(self, widget: Gtk.Widget):
                self._toolbar_view.add_bottom_bar(widget)

            def on_destroy(self, widget):
                self._toolbar_view.unparent()
                self._toolbar_view = None

            attrs["__init__"] = __init__
            attrs["set_content"] = set_content
            attrs["add_top_bar"] = add_top_bar
            attrs["add_bottom_bar"] = add_bottom_bar
            attrs["on_destroy"] = on_destroy

        return super().__new__(mcs, name, bases, attrs)


class ToolbarView(Gtk.Widget, metaclass=ToolbarViewMeta):
    __gtype_name__: str = "ToolbarView"

    @classmethod
    def new(cls):
        return ToolbarView()

    def __init__(self):
        pass

    def set_content(self, content: Gtk.Widget|None = None) -> None:
        pass

    def add_top_bar(self, widget: Gtk.Widget):
        pass

    def add_bottom_bar(self, widget: Gtk.Widget):
        pass


ToolbarView.set_css_name("compat-toolbarview")
