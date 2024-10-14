import os
import gi

from waydroid_helper.extensionwindow import AvailableVersionPage
from waydroid_helper.util.ExtentionsManager import PackageManager, ExtentionManagerState

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gettext import gettext as _
from waydroid_helper.extensionrow import ExtensionRow
from waydroid_helper.waydroid import Waydroid
from gi.repository import Gtk, GObject, Adw

adw_version = os.environ["adw_version"]
if adw_version >= "10600":
    RESOURCE_PATH = "/com/jaoushingan/WaydroidHelper/ui/ExtensionsPage.ui"
else:
    RESOURCE_PATH = "/com/jaoushingan/WaydroidHelper/ui/ExtensionsPage_old.ui"


@Gtk.Template(resource_path=RESOURCE_PATH)
class ExtensionsPage(Gtk.Box):
    __gtype_name__ = "ExtensionsPage"
    waydroid: GObject.Property = GObject.Property(default=None, type=Waydroid)
    extensions_page: Adw.PreferencesPage = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    extension_manager = ...
    extensions = []

    # houdini_expanderrow: Adw.ExpanderRow = Gtk.Template.Child()
    # ndk_expanderrow: Adw.ExpanderRow = Gtk.Template.Child()

    def __init__(self, waydroid: Waydroid, **kargs):
        super().__init__(**kargs)
        self.set_property("waydroid", waydroid)
        self.extension_manager = PackageManager()
        self.extension_manager.set_property("waydroid", self.waydroid)
        self.extension_manager.connect("notify::state", self.init_page)
        self.stack.set_visible_child_name("spinner")

        self.extension_manager.connect(
            "installation-started", self.on_installation_started
        )
        self.extension_manager.connect(
            "installation-completed", self.on_installation_completed
        )
        self.extension_manager.connect(
            "uninstallation-completed", self.on_uninstallation_completed
        )

    def on_installation_started(self, obj, name, version):
        page:AvailableVersionPage = self.get_root().view_find_page(name)
        page.on_installation_started(obj, name, version)

    def on_installation_completed(self, obj, name, version):
        page:AvailableVersionPage = self.get_root().view_find_page(name)
        page.on_installation_completed(obj, name, version)

    def on_uninstallation_completed(self, obj, name, version):
        page:AvailableVersionPage = self.get_root().view_find_page(name)
        page.on_uninstallation_completed(obj, name, version)

    def create_row(self, title, subtitle, info):

        def on_button_clicked(button):
            root: Adw.Window = self.get_root()
            if root.view_find_page(title) is None:
                page = AvailableVersionPage(info, self.extension_manager)
                page.set_tag(title)
                root.view_add(page)
            root.view_push_by_tag(title)

        row = ExtensionRow.new()
        row.set_title(title)
        row.set_subtitle(_(subtitle))
        row.set_info(info)
        row.set_manager(self.extension_manager)

        row.button.connect("clicked", on_button_clicked)
        return row

    def init_page(self, w, param):
        if self.extension_manager.get_property("state") != ExtentionManagerState.READY:
            return
        self.extensions = self.extension_manager.get_data()
        self.stack.set_visible_child_name("content")
        for each_group in self.extensions:
            title = each_group["name"]
            description = each_group["description"]
            group = Adw.PreferencesGroup.new()
            group.set_title(title)
            group.set_description(_(description))
            # TODO 想想怎么做更好
            for expander_row in sorted(each_group["list"], key=lambda x: x["path"]):
                if "name" in expander_row.keys():
                    title = expander_row["name"]
                    subtitle = expander_row["description"]
                    expanderrow = Adw.ExpanderRow.new()
                    expanderrow.set_title(title)
                    expanderrow.set_subtitle(_(subtitle))

                    for each_row in sorted(
                        expander_row["list"], key=lambda x: x["path"]
                    ):
                        # 直接读了一个具体版本的名字和描述, 不太好
                        title = each_row["list"][0]["name"]
                        subtitle = each_row["list"][0]["description"]
                        row = self.create_row(title, subtitle, each_row["list"])
                        expanderrow.add_row(row)
                    group.add(child=expanderrow)
                else:
                    title = expander_row["list"][0]["name"]
                    subtitle = expander_row["list"][0]["description"]
                    row = self.create_row(title, subtitle, expander_row["list"])
                    group.add(child=row)

            self.extensions_page.add(group=group)
