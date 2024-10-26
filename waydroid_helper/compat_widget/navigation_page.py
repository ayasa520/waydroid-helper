from typing import Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from waydroid_helper.util import logger
from gi.repository import Gtk, Adw, GLib, GObject

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION

if ADW_VERSION >= (1, 4, 0):
    BASE_PAGE = Adw.NavigationPage
else:
    BASE_PAGE = Gtk.Box

# 其实应该做成 final 类了, 但是
class NavigationPageMeta(type(GObject.Object)):
    def __new__(mcs, name, bases, attrs):
        replace = False
        if ADW_VERSION < (1, 4, 0) and (Gtk.Box in bases):
            replace = True
            attrs["title"] = GObject.Property(type=str, default="")

            def __init__(self, child=None, title: str = "", tag: str = None):
                super(NavigationPage, self).__init__(name=tag)
                if child:
                    self.append(child)
                    child.set_vexpand(True)
                    child.set_hexpand(True)
                self._child = child
                if title:
                    self.set_property("title", title)

            def set_child(self, child: Optional[Gtk.Widget] = None) -> None:
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

        elif ADW_VERSION >= (1, 4, 0) and (Adw.NavigationPage in bases):
            replace = True

            def __init__(
                self, child: Gtk.Widget = None, title: str = "", tag: str = None
            ):
                super(NavigationPage, self).__init__(child=child, title=title, tag=tag)

            def set_tag(self, tag: str):
                super(NavigationPage, self).set_tag(tag)

            def get_tag(self):
                super(NavigationPage, self).get_tag()

            def set_child(self, child: Optional[Gtk.Widget] = None) -> None:
                super(NavigationPage, self).set_child(child)

            def get_title(self):
                super(NavigationPage, self).get_title()
        if replace:
            attrs["__init__"] = __init__
            attrs["set_tag"] = set_tag
            attrs["get_tag"] = get_tag
            attrs["set_child"] = set_child
            attrs["get_title"] = get_title
        return super().__new__(mcs, name, bases, attrs)

class NavigationPage(BASE_PAGE, metaclass=NavigationPageMeta):
    __gtype_name__ = "NavigationPage"
    def __init__(self, child: Gtk.Widget = None, title: str = "", tag: str = None):
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

    def set_child(self, child: Optional[Gtk.Widget] = None) -> None:
        pass

    def get_title(self):
        pass

