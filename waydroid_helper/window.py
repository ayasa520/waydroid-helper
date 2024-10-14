import os
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gettext import gettext as _
from waydroid_helper.extensionspage import ExtensionsPage
from waydroid_helper.generalpage import GeneralPage
from waydroid_helper.waydroid import Waydroid
from waydroid_helper.propspage import PropsPage
from gi.repository import Gtk, Adw, Gio

# from waydroid_helper.controller import ControllerWindow

adw_version = os.environ["adw_version"]

if adw_version >= "10400":
    NAVIGATION = "navigation_view"
    RESOURCE_PATH = "/com/jaoushingan/WaydroidHelper/ui/window.ui"
else:
    NAVIGATION = "leaflet"
    RESOURCE_PATH = "/com/jaoushingan/WaydroidHelper/ui/window_old.ui"

@Gtk.Template(resource_path=RESOURCE_PATH)
class WaydroidHelperWindow(Adw.ApplicationWindow):
    __gtype_name__ = "WaydroidHelperWindow"
    stack: Adw.ViewStack = Gtk.Template.Child()
    navigation_view = Gtk.Template.Child(NAVIGATION)

    def on_visible_child_changed(self, leaflet, pspec):
        """
        AdwLeaflet
        """
        if not self.navigation_view.get_child_transition_running():
            current_page = self.navigation_view.get_visible_child()
            if current_page in self.leafletpages:
                index = self.leafletpages.index(current_page)
                if index < len(self.leafletpages) - 1:
                    # This is a back navigation
                    pages_to_remove = self.leafletpages[index + 1 :]
                    for page in pages_to_remove:
                        self.navigation_view.remove(page)
                    self.leafletpages = self.leafletpages[: index + 1]

    def view_push(self, widget):
        if NAVIGATION == "navigation_view":
            self.navigation_view.push(widget)
        else:
            # AdwLeaflet
            self.navigation_view.append(widget)
            self.navigation_view.set_visible_child(widget)
            self.leafletpages.append(widget)

    def view_add(self, widget):
        if NAVIGATION == "navigation_view":
            self.navigation_view.add(widget)

    def view_find_page(self, tag: str):
        if NAVIGATION == "navigation_view":
            return self.navigation_view.find_page(tag)

    def view_push_by_tag(self, tag: str):
        if NAVIGATION == "navigation_view":
            self.navigation_view.push_by_tag(tag)

    def navigate_back(self):
        """
        AdwLeafletPage
        """
        self.navigation_view.navigate(Adw.NavigationDirection.BACK)

    def stack_add_titled_with_icon(
        self, child: Gtk.Widget, name: str | None, title: str, icon_name: str
    ):
        if adw_version >= "10200":
            self.stack.add_titled_with_icon(child, name, title, icon_name)
        else:
            view_page = self.stack.add_titled(child, name, title)
            view_page.set_icon_name(icon_name)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.settings = Gio.Settings(schema_id="com.jaoushingan.WaydroidHelper")

        self.settings.bind(
            "width", self, "default-width", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "height", self, "default-height", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "is-maximized", self, "maximized", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "is-fullscreen", self, "fullscreened", Gio.SettingsBindFlags.DEFAULT
        )

        self.waydroid = Waydroid()
        general_page = GeneralPage(self.waydroid)
        props_page = PropsPage(self.waydroid)
        extensions_page = ExtensionsPage(self.waydroid)

        self.stack_add_titled_with_icon(
            child=general_page,
            name="page01",
            title=_("Home"),
            icon_name="com.jaoushingan.WaydroidHelper-home-symbolic",
        )
        self.stack_add_titled_with_icon(
            child=props_page,
            name="page02",
            title=_("Settings"),
            icon_name="com.jaoushingan.WaydroidHelper-system-symbolic",
        )
        self.stack_add_titled_with_icon(
            child=extensions_page,
            name="page03",
            title=_("Extensions"),
            icon_name="com.jaoushingan.WaydroidHelper-addon-symbolic",
        )
        if NAVIGATION == "leaflet":
            self.navigation_view.connect(
                "notify::child-transition-running", self.on_visible_child_changed
            )
            self.leafletpages = [self.navigation_view.get_child_by_name("page-1")]
