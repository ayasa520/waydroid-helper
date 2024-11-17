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

from gi.repository import Gtk, Adw, GLib, GObject

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION

if ADW_VERSION >= (1, 4, 0):
    base_page = Adw.NavigationPage
else:
    base_page = Gtk.Box


# 其实应该做成 final 类了, 但是
class NavigationPageMeta(type(GObject.Object)):
    def __new__(mcs, name, bases, attrs):
        if ADW_VERSION < (1, 4, 0) and (Gtk.Box in bases):
            attrs["title"] = GObject.Property(type=str, default="")

            def __init__(self, child=None, title: str = "", tag: str | None = None):
                super(NavigationPage, self).__init__(name=tag)
                if child:
                    self.append(child)
                    child.set_vexpand(True)
                    child.set_hexpand(True)
                self._child = child
                if title:
                    self.set_property("title", title)

            def set_child(self, child: Gtk.Widget | None = None) -> None:
                if self._child:
                    self.remove(self._child)
                self._child = child
                if child:
                    self.append(child)
                    child.set_vexpand(True)
                    child.set_hexpand(True)

            def set_tag(self, tag: str):
                super(NavigationPage, self).set_name(tag)

            def get_tag(self):
                return super(NavigationPage, self).get_name()

            def get_title(self):
                return self.get_property("title")

            attrs["__init__"] = __init__
            attrs["set_tag"] = set_tag
            attrs["get_tag"] = get_tag
            attrs["set_child"] = set_child
            attrs["get_title"] = get_title

        elif ADW_VERSION >= (1, 4, 0) and (Adw.NavigationPage in bases):

            def __init__(
                self,
                child: Gtk.Widget | None = None,
                title: str = "",
                tag: str | None = None,
            ):
                super(NavigationPage, self).__init__(child=child, title=title, tag=tag)

            def set_tag(self, tag: str):
                super(NavigationPage, self).set_tag(tag)

            def get_tag(self):
                return super(NavigationPage, self).get_tag()

            def set_child(self, child: Gtk.Widget | None = None) -> None:
                super(NavigationPage, self).set_child(child)

            def get_title(self):
                return super(NavigationPage, self).get_title()

            attrs["__init__"] = __init__
            attrs["set_tag"] = set_tag
            attrs["get_tag"] = get_tag
            attrs["set_child"] = set_child
            attrs["get_title"] = get_title
        return super().__new__(mcs, name, bases, attrs)


class NavigationPage(base_page, metaclass=NavigationPageMeta):
    __gtype_name__: str = "NavigationPage"

    def __init__(
        self, child: Gtk.Widget | None = None, title: str = "", tag: str | None = None
    ):
        pass

    @classmethod
    def new(cls, child: Gtk.Widget, title: str):
        return NavigationPage(child=child, title=title)

    @classmethod
    def new_with_tag(cls, child: Gtk.Widget, title: str, tag: str):
        return NavigationPage(child=child, title=title, tag=tag)

    def set_tag(self, tag: str):
        pass

    def get_tag(self):
        pass

    def set_child(self, child: Gtk.Widget | None = None) -> None:
        pass

    def get_title(self):
        pass

    def get_root(self)->Gtk.Window:
        return super(NavigationPage, self).get_root()
