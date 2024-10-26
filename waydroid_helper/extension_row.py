import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gettext import gettext as _
from waydroid_helper.available_version_page import AvailableVersionPage
from gi.repository import Gtk, Adw


@Gtk.Template(resource_path="/com/jaoushingan/WaydroidHelper/ui/ExtensionRow.ui")
class ExtensionRow(Adw.ActionRow):
    __gtype_name__ = "ExtensionRow"
    button: Gtk.Button = Gtk.Template.Child()
    info: list = []
    extension_manager = ...

    def __init__(self, title=..., subtitle=..., info=...):
        super().__init__()
        if title is not ...:
            self.set_title(title)
        if subtitle is not ...:
            self.set_subtitle(subtitle)
        if info is not ...:
            self.info = info
        # self.button.connect("clicked", self.on_button_clicked)

    def set_info(self, versions):
        self.info = versions

    def set_manager(self, extension_manager):
        self.extension_manager = extension_manager

    @classmethod
    def new(cls):
        return ExtensionRow()

    # def on_button_clicked(self, button):
    #     root: Adw.Window = self.get_root()
    #     if root.view_find_page(self.get_title()) is None:
    #         page = AvailableVersionPage(self.info, self.extension_manager)
    #         page.set_tag(self.get_title())
    #         root.view_add(page)
    #     root.view_push_by_tag(self.get_title())
