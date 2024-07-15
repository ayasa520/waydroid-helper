import gi

from waydroid_helper.util.ExtentionsManager import PackageManager, ExtentionManagerState

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gettext import gettext as _
from waydroid_helper.extensionrow import ExtensionRow
from waydroid_helper.waydroid import Waydroid
from gi.repository import Gtk, GObject, Adw


@Gtk.Template(resource_path="/com/jaoushingan/WaydroidHelper/ui/ExtensionsPage.ui")
class ExtensionsPage(Gtk.Box):
    __gtype_name__ = "ExtensionsPage"
    waydroid: GObject.Property = GObject.Property(default=None, type=Waydroid)
    extensions_page: Adw.PreferencesPage = Gtk.Template.Child()
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

    def init_page(self, w, param):
        if self.extension_manager.get_property("state") != ExtentionManagerState.READY:
            return
        self.extensions = self.extension_manager.get_data()

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

                    for each_row in sorted(expander_row["list"], key=lambda x: x["path"]):
                        # 直接读了一个具体版本的名字和描述, 不太好
                        title = each_row["list"][0]["name"]
                        subtitle = each_row["list"][0]["description"]
                        row = ExtensionRow.new()
                        row.set_title(title)
                        row.set_subtitle(_(subtitle))
                        row.set_info(each_row["list"])
                        row.set_manager(self.extension_manager)
                        expanderrow.add_row(row)
                    group.add(child=expanderrow)
                else:
                    title = expander_row["list"][0]["name"]
                    subtitle = expander_row["list"][0]["description"]
                    row = ExtensionRow.new()
                    row.set_title(title)
                    row.set_subtitle(_(subtitle))
                    row.set_info(expander_row["list"])
                    row.set_manager(self.extension_manager)
                    group.add(child=row)

            self.extensions_page.add(group=group)
