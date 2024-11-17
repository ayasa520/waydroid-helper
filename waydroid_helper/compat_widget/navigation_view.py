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
# pyright: reportReturnType=false

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, GObject
from .navigation_page import NavigationPage
from waydroid_helper.util import logger

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION


class NavigationViewMeta(type(GObject.Object)):
    def __new__(mcs, name, bases, attrs):
        # final class
        for base in bases:
            if isinstance(base, NavigationViewMeta):
                raise TypeError(
                    "type '{0}' is not an acceptable base type".format(base.__name__)
                )

        if ADW_VERSION >= (1, 4, 0):

            def __init__(self):
                super(self.__class__, self).__init__()
                self._navigation_view = Adw.NavigationView()
                self.set_layout_manager(Gtk.BinLayout())
                self._navigation_view.set_parent(self)
                self.connect("destroy", self.on_destroy)

            def get_navigation_stack(self):
                return list(self._navigation_view.get_navigation_stack())

            def find_page(self, tag):
                return self._navigation_view.find_page(tag)

            def push(self, page: NavigationPage):
                self._navigation_view.push(page)

            def add(self, page):
                self._navigation_view.add(page)

            def remove(self, page):
                self._navigation_view.remove(page)

            def pop(self) -> bool:
                return self._navigation_view.pop()

            def push_by_tag(self, tag):
                self._navigation_view.push_by_tag(tag)

        else:

            def __init__(self):
                super(self.__class__, self).__init__()
                self.maybe_removed = None
                self._pages = []
                self._navigation_stack  = []
                self._navigation_view = Adw.Leaflet()
                self._navigation_view.set_can_unfold(False)
                self._navigation_view.set_can_navigate_back(True)
                self._navigation_view.connect(
                    "notify::child-transition-running", self._on_visible_child_changed
                )
                self.set_layout_manager(Gtk.BinLayout())
                self._navigation_view.set_parent(self)
                self.connect("destroy", self.on_destroy)

            def get_navigation_stack(self):
                return self._navigation_stack

            def find_page(self, tag):
                for page in set(self._pages + self._navigation_stack):
                    if page.get_tag() == tag:
                        return page
                return None

            def push(self, page: NavigationPage):
                for p in self._pages:
                    if p.get_tag() == page.get_tag() and p is not page:
                        logger.warning(
                            f"Duplicate page tag in NavigationView: {page.get_tag()}"
                        )
                        return
                if page in self._navigation_stack:
                    logger.warning("Page is already in navigation stack")
                    return

                if not self._navigation_view.get_page(page):
                    self._navigation_view.append(page)
                self._navigation_stack.append(page)
                self._navigation_view.get_page(page).set_navigatable(True)
                self._navigation_view.set_visible_child(page)

            def add(self, page):
                for p in set(self._navigation_stack + self._pages):
                    if p.get_tag() == page.get_tag():
                        logger.warning(
                            f"Duplicate page tag in NavigationView: {page.get_tag()}"
                        )
                        return
                self._pages.append(page)
                if len(self._navigation_stack) == 0:
                    self.push(page)

            def remove(self, page):
                if page in self._pages:
                    self._pages.remove(page)

            def pop(self) -> bool:
                if len(self._navigation_stack) > 1:
                    self.maybe_removed = self._navigation_stack.pop()
                    self._navigation_view.get_page(self.maybe_removed).set_navigatable(
                        False
                    )
                    self._navigation_view.set_visible_child(self._navigation_stack[-1])
                    return True
                return False

            def _on_visible_child_changed(self, leaflet, pspec):
                """
                AdwLeaflet
                """
                if not self._navigation_view.get_child_transition_running():
                    current_page = self._navigation_view.get_visible_child()

                    if current_page == self._navigation_stack[-1]:
                        return

                    # 手势或者键盘触发 NavigationBack, pop 没有被调用
                    self.maybe_removed = self._navigation_stack.pop()
                    self._navigation_view.get_page(self.maybe_removed).set_navigatable(
                        False
                    )

                    # pop
                    if self.maybe_removed not in self._pages:
                        self._navigation_view.remove(self.maybe_removed)
                    self.maybe_removed = None

            def push_by_tag(self, tag):
                for page in self._pages:
                    if page.get_tag() == tag:

                        if page in self._navigation_stack:
                            logger.warning("Page is already in navigation stack")
                            return

                        if not self._navigation_view.get_page(page):
                            self._navigation_view.append(page)

                        self._navigation_stack.append(page)
                        self._navigation_view.get_page(page).set_navigatable(True)
                        self._navigation_view.set_visible_child(page)

            attrs["_on_visible_child_changed"] = _on_visible_child_changed

        def on_destroy(self, widget):
            self._navigation_view.unparent()
            self._navigation_view = None

        attrs["__init__"] = __init__
        attrs["get_navigation_stack"] = get_navigation_stack
        attrs["find_page"] = find_page
        attrs["push"] = push
        attrs["add"] = add
        attrs["remove"] = remove
        attrs["pop"] = pop
        attrs["push_by_tag"] = push_by_tag
        attrs["on_destroy"] = on_destroy

        return super().__new__(mcs, name, bases, attrs)


class NavigationView(Gtk.Widget, metaclass=NavigationViewMeta):
    __gtype_name__:str = "NavigationView"

    def __init__(self):
        pass

    def get_navigation_stack(self):
        pass

    def find_page(self, tag: str)->NavigationPage:
        pass

    def push(self, page: NavigationPage):
        pass

    def add(self, page: NavigationPage):
        pass

    def remove(self, page: NavigationPage):
        pass

    def pop(self) -> bool:
        pass

    def push_by_tag(self, tag: str):
        pass

    def on_destroy(self, widget):
        pass


NavigationView.set_css_name("compat-navigation-view")
