import gi

from waydroid_helper.tools import PackageManager
from waydroid_helper.tools.extensions_manager import PackageInfo

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from waydroid_helper.util import template


@template(resource_path="/com/jaoushingan/WaydroidHelper/ui/ExtensionRow.ui")
class ExtensionRow(Adw.ActionRow):
    __gtype_name__: str = "ExtensionRow"
    button: Gtk.Button = Gtk.Template.Child()
    info: list[PackageInfo] = []
    extension_manager: PackageManager

    def __init__(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        info: list[PackageInfo] | None = None,
    ):
        super().__init__()
        if title is not None:
            self.set_title(title)
        if subtitle is not None:
            self.set_subtitle(subtitle)
        if info is not None:
            self.info = info
        # self.button.connect("clicked", self.on_button_clicked)

    def set_info(self, versions: list[PackageInfo]):
        self.info = versions

    def set_manager(self, extension_manager: PackageManager):
        self.extension_manager = extension_manager

    # def on_button_clicked(self, button):
    #     root: Adw.Window = self.get_root()
    #     if root.view_find_page(self.get_title()) is None:
    #         page = AvailableVersionPage(self.info, self.extension_manager)
    #         page.set_tag(self.get_title())
    #         root.view_add(page)
    #     root.view_push_by_tag(self.get_title())
