import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib
from .navigation_page import NavigationPage
from waydroid_helper.util import logger

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION


class NavigationView(Gtk.Widget):
    __gtype_name__ = "NavigationView"

    def __init__(self):
        super().__init__()
        if ADW_VERSION >= (1, 4, 0):
            self._navigation_view = Adw.NavigationView()
        else:
            self._pages: list[NavigationPage] = []
            self._navigation_stack: list[NavigationPage] = []
            self._navigation_view = Adw.Leaflet()
            self._navigation_view.set_can_unfold(False)
            self._navigation_view.set_can_navigate_back(True)
            self._navigation_view.connect(
                "notify::child-transition-running", self.__on_visible_child_changed
            )

        self.set_layout_manager(Gtk.BinLayout())
        self._navigation_view.set_parent(self)
        self.connect("destroy", self.on_destroy)
    
    def get_navigation_stack(self):
        if ADW_VERSION>=(1,4,0):
            return list(self._navigation_view.get_navigation_stack())
        else:
            return self._navigation_stack
        

    def find_page(self, tag):
        if ADW_VERSION >= (1, 4, 0):
            return self._navigation_view.find_page(tag)
        else:
            for page in set(self._pages + self._navigation_stack):
                if page.get_tag() == tag:
                    return page
            return None

    def push(self, page: NavigationPage):
        if ADW_VERSION >= (1, 4, 0):
            self._navigation_view.push(page)
        else:
            for p in self._pages:
                if p.get_tag() == page.get_tag() and p is not page:
                    logger.warning(
                        f"Duplicate page tag in NavigationView: {page.get_tag()}"
                    )
                    return
            if page in self._navigation_stack:
                logger.warning("Page is already in navigation stack")
                return

            self._navigation_stack.append(page)
            self._navigation_view.append(page)
            self._navigation_view.set_visible_child(page)

    def add(self, page):
        if ADW_VERSION >= (1, 4, 0):
            self._navigation_view.add(page)
        else:
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
        if ADW_VERSION >= (1, 4, 0):
            self._navigation_view.remove(page)
        else:
            if page in self._pages:
                self._pages.remove(page)

    def pop(self) -> bool:
        if ADW_VERSION >= (1, 4, 0):
            return self._navigation_view.pop()
        else:
            if len(self._navigation_stack) > 1:
                # self._navigation_stack.pop()
                self._navigation_view.navigate(Adw.NavigationDirection.BACK)
                return True
            return False

    def __on_visible_child_changed(self, leaflet, pspec):
        """
        AdwLeaflet
        """
        if not self._navigation_view.get_child_transition_running():
            current_page = self._navigation_view.get_visible_child()
            # push 新页面
            if current_page == self._navigation_stack[-1]:
                return
            # pop
            page = self._navigation_stack.pop()
            self._navigation_view.remove(page)

    def push_by_tag(self, tag):
        if ADW_VERSION >= (1, 4, 0):
            self._navigation_view.push_by_tag(tag)
        else:
            for page in self._pages:
                if page.get_tag() == tag:
                    self.push(page)
                    return

    def on_destroy(self, widget):
        self._navigation_view.unparent()
        self._navigation_view = None


