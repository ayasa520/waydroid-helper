import gi

from waydroid_helper.available_version_page import AvailableVersionPage
from waydroid_helper.util.extensions_manager import PackageManager, ExtensionManagerState

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gettext import gettext as _
from waydroid_helper.extension_row import ExtensionRow
from waydroid_helper.waydroid import Waydroid
from gi.repository import Gtk, GObject, Adw
from waydroid_helper.compat_widget import Spinner


class ExtensionsPage(Gtk.Box):
    __gtype_name__ = "ExtensionsPage"
    waydroid: GObject.Property = GObject.Property(default=None, type=Waydroid)
    stack: Gtk.Stack = ...
    extensions_page: Adw.PreferencesPage = ...
    extension_manager = ...
    extensions = []

    def __init__(self, waydroid: Waydroid, **kargs):
        super().__init__(**kargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_property("waydroid", waydroid)
        self.extensions_page = Adw.PreferencesPage.new()
        self.stack = Gtk.Stack.new()
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # 创建一个居中的容器用于 spinner
        spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        spinner_box.set_halign(Gtk.Align.CENTER)
        spinner_box.set_valign(Gtk.Align.CENTER)
        
        # 创建并设置 spinner
        spinner = Spinner()
        spinner.set_size_request(64, 64)

        # 将 spinner 添加到容器中
        spinner_box.append(spinner)
        self.stack.add_named(name="spinner", child=spinner_box)
        self.stack.add_named(name="content", child=self.extensions_page)

        self.extension_manager = PackageManager()
        self.extension_manager.set_property("waydroid", self.waydroid)
        self.stack.set_visible_child_name("spinner")
        self.extension_manager.connect("notify::state", self.init_page)
        self.extension_manager.connect(
            "installation-started", self.on_installation_started
        )
        self.extension_manager.connect(
            "installation-completed", self.on_installation_completed
        )
        self.extension_manager.connect(
            "uninstallation-completed", self.on_uninstallation_completed
        )
        self.append(self.stack)

    def on_installation_started(self, obj, name, version):
        page: AvailableVersionPage = self.get_root().view_find_page(name)
        page.on_installation_started(obj, name, version)

    def on_installation_completed(self, obj, name, version):
        page: AvailableVersionPage = self.get_root().view_find_page(name)
        page.on_installation_completed(obj, name, version)

    def on_uninstallation_completed(self, obj, name, version):
        page: AvailableVersionPage = self.get_root().view_find_page(name)
        if page is not None:
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
        if self.extension_manager.get_property("state") != ExtensionManagerState.READY:
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
