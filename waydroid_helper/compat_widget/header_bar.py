# pyright: reportUnknownMemberType=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false
# pyright: reportRedeclaration=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportAny=false
# pyright: reportMissingSuperCall=false
# pyright: reportCallIssue=false

# from typing import override
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, GObject
from .navigation_page import NavigationPage
from .navigation_view import NavigationView

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION


class HeaderBarMeta(type(GObject.Object)):
    def __new__(mcs, name, bases, attrs):
        # final class
        for base in bases:
            if isinstance(base, HeaderBarMeta):
                raise TypeError(
                    "type '{0}' is not an acceptable base type".format(base.__name__)
                )

        def __init__(self):
            super(self.__class__, self).__init__()
            self._header = Adw.HeaderBar.new()
            self._header.bind_property(
                "title-widget",
                self,
                "title-widget",
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            )

            self._header.bind_property(
                "centering-policy",
                self,
                "centering-policy",
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            )
            self.set_layout_manager(Gtk.BinLayout())
            self._header.set_parent(self)
            if ADW_VERSION < (1, 4, 0):
                self._navigation_page = None
                self._navigation_view = None

            self.connect("destroy", self.on_destroy)

        def __getattr__(self, name):
            return getattr(self._header, name)

        def on_destroy(self, widget):
            self._header.unparent()

        def do_unroot(self):
            Gtk.Widget.do_unroot(self)

        if ADW_VERSION >= (1, 4, 0):

            def do_root(self):
                Gtk.Widget.do_root(self)

        else:

            def do_root(self):
                Gtk.Widget.do_root(self)
                if not (self._navigation_page and self._navigation_view):
                    self._navigation_page = self.get_ancestor(NavigationPage)
                    self._navigation_view = self.get_ancestor(NavigationView)
                    if (
                        self._navigation_page
                        and self._navigation_view
                        and not self._header.get_title_widget()
                    ):

                        def on_back_clicked(button):
                            self._navigation_view.pop()

                        title = self._navigation_page.get_title()
                        navigation_stack = self._navigation_view.get_navigation_stack()
                        if (
                            len(navigation_stack) > 0
                            and navigation_stack[0] != self._navigation_page
                        ):
                            back_button = Gtk.Button()
                            back_button.set_icon_name("go-previous-symbolic")
                            back_button.add_css_class("flat")
                            back_button.connect("clicked", on_back_clicked)
                            self._header.pack_start(back_button)
                        title_label = Gtk.Label()
                        title_label.set_markup(f"<b>{title}</b>")
                        self._header.set_title_widget(title_label)

        @classmethod
        def new(cls):
            return HeaderBar()

        attrs["__init__"] = __init__
        attrs["__getattr__"] = __getattr__
        attrs["on_destroy"] = on_destroy
        attrs["do_unroot"] = do_unroot
        attrs["do_root"] = do_root
        attrs["new"] = new

        return super().__new__(mcs, name, bases, attrs)


class HeaderBar(Gtk.Widget, metaclass=HeaderBarMeta):
    __gtype_name__: str = "HeaderBar"
    title_widget: GObject.Property = GObject.Property(type=Gtk.Widget, default=None)
    centering_policy: GObject.Property = GObject.Property(
        type=Adw.CenteringPolicy, default=Adw.CenteringPolicy.LOOSE
    )

    def __init__(self):
        pass

    def __getattr__(self, name):
        pass

    def on_destroy(self, widget):
        pass

    # @override
    def do_unroot(self):
        pass

    # @override
    def do_root(self):
        pass



HeaderBar.set_css_name("compat-headerbar")
