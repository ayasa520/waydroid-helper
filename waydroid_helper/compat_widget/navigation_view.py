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
            self.maybe_removed = None
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
        if ADW_VERSION >= (1, 4, 0):
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

            if not self._navigation_view.get_page(page):
                self._navigation_view.append(page)
            self._navigation_stack.append(page)
            self._navigation_view.get_page(page).set_navigatable(True)
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
                self.maybe_removed = self._navigation_stack.pop()
                self._navigation_view.get_page(self.maybe_removed).set_navigatable(
                    False
                )
                self._navigation_view.set_visible_child(self._navigation_stack[-1])

                # print(self._navigation_stack)
                # print([self._navigation_view.get_page(n).get_navigatable() for n in self._navigation_stack if self._navigation_view.get_page(n)])
                return True
            return False

    def __on_visible_child_changed(self, leaflet, pspec):
        """
        AdwLeaflet
        """
        if not self._navigation_view.get_child_transition_running():
            current_page = self._navigation_view.get_visible_child()

            if current_page == self._navigation_stack[-1]:
                return

            # 手势或者键盘触发 NavigationBack, pop 没有被调用
            self.maybe_removed = self._navigation_stack.pop()
            self._navigation_view.get_page(self.maybe_removed).set_navigatable(False)

            # if self.maybe_removed is None:
            #     return

            # pop
            if self.maybe_removed not in self._pages:
                self._navigation_view.remove(self.maybe_removed)
            self.maybe_removed = None

    def push_by_tag(self, tag):
        if ADW_VERSION >= (1, 4, 0):
            self._navigation_view.push_by_tag(tag)
        else:
            # page = self._navigation_view.get_child_by_name(tag)
            # # 肯定不行, 因为这个检查的是 AdwLeafletPage 的 name
            # if page:
            #     self._navigation_stack.append(page)
            #     self._navigation_view.set_visible_child_name(tag)
            # else:

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

    def on_destroy(self, widget):
        self._navigation_view.unparent()
        self._navigation_view = None
