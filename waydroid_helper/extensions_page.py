# pyright: reportMissingParameterType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownParameterType=false

from typing import TYPE_CHECKING, TypeGuard, cast, final

from waydroid_helper.compat_widget import NavigationView

if TYPE_CHECKING:
    from waydroid_helper.tools.extensions_manager import (
        PackageInfo,
        PackageListItem,
        VariantListItem,
    )

import gi

from waydroid_helper.available_version_page import AvailableVersionPage
from waydroid_helper.tools import ExtensionManagerState, PackageManager

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gettext import gettext as _

from gi.repository import Adw, GObject, Gtk

from waydroid_helper.compat_widget import Spinner
from waydroid_helper.extension_row import ExtensionRow
from waydroid_helper.waydroid import Waydroid


@final
class ExtensionsPage(Gtk.Box):
    __gtype_name__ = "ExtensionsPage"
    waydroid: Waydroid = GObject.Property(
        default=None, type=Waydroid
    )  # pyright:ignore[reportAssignmentType]
    stack: Gtk.Stack
    extensions_page: Adw.PreferencesPage
    extension_manager: PackageManager
    extensions = []

    def __init__(self, waydroid: Waydroid, navigation_view: NavigationView, **kargs):
        super().__init__(**kargs)
        self._navigation_view = navigation_view
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
            "uninstallation-started", self.on_uninstallation_started
        )
        self.extension_manager.connect(
            "uninstallation-completed", self.on_uninstallation_completed
        )
        self.append(self.stack)

    def on_installation_started(self, obj: GObject.Object, name: str, version: str):
        nav_page: AvailableVersionPage = self._navigation_view.find_page(name)
        if isinstance(nav_page, AvailableVersionPage):
            page = cast(AvailableVersionPage, nav_page)
            page.on_installation_started(obj, name, version)

    def on_installation_completed(self, obj: GObject.Object, name: str, version: str):
        nav_page: AvailableVersionPage = self._navigation_view.find_page(name)
        if isinstance(nav_page, AvailableVersionPage):
            page = cast(AvailableVersionPage, nav_page)
            page.on_installation_completed(obj, name, version)

    def on_uninstallation_started(self, obj: GObject.Object, name: str, version: str):
        nav_page: AvailableVersionPage = self._navigation_view.find_page(name)
        if isinstance(nav_page, AvailableVersionPage):
            page = cast(AvailableVersionPage, nav_page)
            page.on_uninstallation_started(obj, name, version)

    def on_uninstallation_completed(self, obj: GObject.Object, name: str, version: str):
        nav_page: AvailableVersionPage = self._navigation_view.find_page(name)
        if isinstance(nav_page, AvailableVersionPage):
            page = cast(AvailableVersionPage, nav_page)
            page.on_uninstallation_completed(obj, name, version)

    def create_row(
        self, title: str, subtitle: str, info: list["PackageInfo"]
    ) -> ExtensionRow:

        def on_button_clicked(button: Gtk.Button):
            if self._navigation_view.find_page(title) is None:
                page = AvailableVersionPage(info, self.extension_manager)
                page.set_tag(title)
                self._navigation_view.add(page)
            self._navigation_view.push_by_tag(title)

        row = ExtensionRow()
        row.set_title(title)
        row.set_subtitle(_(subtitle))
        row.set_info(info)
        row.set_manager(self.extension_manager)

        row.button.connect("clicked", on_button_clicked)
        if self._navigation_view.find_page(title) is not None:
            self._navigation_view.remove(self._navigation_view.find_page(title))
        return row

    # TODO 换成 TreeListModel? 我找不到可用的资料或者样例
    def init_page(self, w: GObject.Object | None, param: GObject.ParamSpec | None):

        def is_package_list_item(
            item: "PackageListItem|VariantListItem",
        ) -> TypeGuard["PackageListItem"]:
            return "name" not in item.keys()

        def is_variant_list_item(
            item: "PackageListItem|VariantListItem",
        ) -> TypeGuard["VariantListItem"]:
            return not is_package_list_item(item)

        if self.extension_manager.get_property("state") != ExtensionManagerState.READY:
            return
        self.extensions = self.extension_manager.get_package_data()
        self.stack.set_visible_child_name("content")
        for each_group in self.extensions:
            title = each_group["name"]
            description = each_group["description"]
            group = Adw.PreferencesGroup.new()
            group.set_title(title)
            group.set_description(_(description))
            # TODO 想想怎么做更好
            for expander_row in sorted(each_group["list"], key=lambda x: x["path"]):
                # if "name" in expander_row.keys():
                if is_variant_list_item(expander_row):
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
                elif is_package_list_item(expander_row):
                    title = expander_row["list"][0]["name"]
                    subtitle = expander_row["list"][0]["description"]
                    row = self.create_row(title, subtitle, expander_row["list"])
                    group.add(child=row)

            self.extensions_page.add(group=group)

    async def refresh(self):
        await self.extension_manager.update_extension_json()
        self.extension_manager.grab_meta()

        self.stack.remove(self.extensions_page)

        self.extensions_page = Adw.PreferencesPage.new()
        self.stack.add_named(self.extensions_page, "content")
        self.init_page(None, None)
