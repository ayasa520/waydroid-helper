from gettext import gettext as _
from waydroid_helper.extensionspage import ExtensionsPage
from waydroid_helper.generalpage import GeneralPage
from waydroid_helper.waydroid import Waydroid
from waydroid_helper.propspage import PropsPage
from gi.repository import Gtk, Adw, Gio
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# from waydroid_helper.controller import ControllerWindow


@Gtk.Template(resource_path="/com/jaoushingan/WaydroidHelper/ui/window.ui")
class WaydroidHelperWindow(Adw.ApplicationWindow):
    __gtype_name__ = "WaydroidHelperWindow"
    stack: Adw.ViewStack = Gtk.Template.Child()

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

        self.stack.add_titled_with_icon(
            child=general_page,
            name="page01",
            title=_("Home"),
            icon_name="user-home-symbolic",
        )
        self.stack.add_titled_with_icon(
            child=props_page,
            name="page02",
            title=_("Settings"),
            icon_name="emblem-system-symbolic",
        )
        self.stack.add_titled_with_icon(
            child=extensions_page,
            name="page03",
            title=_("Extensions"),
            icon_name="application-x-addon-symbolic",
        )
