import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gettext import gettext as _
from waydroid_helper import ExtensionsPage,GeneralPage,Waydroid,PropsPage
from waydroid_helper.compat_widget import ADW_VERSION, NavigationView, NavigationPage, ToolbarView,HeaderBar
from gi.repository import Gtk, Adw, Gio, GObject


@Gtk.Template(resource_path="/com/jaoushingan/WaydroidHelper/ui/window.ui")
class WaydroidHelperWindow(Adw.ApplicationWindow):
    __gtype_name__ = "WaydroidHelperWindow"
    navigation_view: NavigationView = Gtk.Template.Child()

    def view_push(self, widget):
        self.navigation_view.push(widget)

    def view_add(self, widget):
        self.navigation_view.add(widget)

    def view_find_page(self, tag: str):
        return self.navigation_view.find_page(tag)

    def view_push_by_tag(self, tag: str):
        self.navigation_view.push_by_tag(tag)


    def stack_add_titled_with_icon(
        self, child: Gtk.Widget, name: str | None, title: str, icon_name: str
    ):
        view_page = self.adw_view_stack.add_titled(child, name, title)
        view_page.set_icon_name(icon_name)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # theme = Gtk.IconTheme.get_for_display(self.get_display())
        # theme.add_resource_path("/com/jaoushingan/WaydroidHelper/icons")
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

        adw_toolbar_view = ToolbarView.new()

        self.adw_view_stack = Adw.ViewStack.new()
        adw_toolbar_view.set_content(content=self.adw_view_stack)

        self.adw_header_bar = HeaderBar.new()
        if ADW_VERSION>=(1,4,0):
            adw_view_switcher = Adw.ViewSwitcher.new()
            adw_view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
            adw_view_switcher.set_stack(self.adw_view_stack)
            self.adw_header_bar.set_title_widget(adw_view_switcher)
        else:
            self.adw_header_bar.set_property("centering-policy", Adw.CenteringPolicy.STRICT)
            adw_view_switcher_title = Adw.ViewSwitcherTitle.new()
            adw_view_switcher_title.set_stack(self.adw_view_stack)
            adw_view_switcher_title.set_title("Waydroid Helper")
            self.adw_header_bar.set_title_widget(adw_view_switcher_title)

        adw_toolbar_view.add_top_bar(widget=self.adw_header_bar)

        menu_button_model = Gio.Menu()
        menu_button_model.append(
            label=_("_Preferences"),
            detailed_action="app.preferences",
        )
        menu_button_model.append(
            label=_("_About waydroid-helper"),
            detailed_action="app.about",
        )
        menu_button = Gtk.MenuButton.new()
        menu_button.set_icon_name(icon_name="open-menu-symbolic")
        menu_button.set_menu_model(menu_model=menu_button_model)
        self.adw_header_bar.pack_end(child=menu_button)

        adw_view_switcher_bar = Adw.ViewSwitcherBar.new()
        adw_view_switcher_bar.set_stack(self.adw_view_stack)
        if ADW_VERSION<(1,4,0):
            adw_view_switcher_title.bind_property("title-visible",adw_view_switcher_bar,"reveal",GObject.BindingFlags.SYNC_CREATE)
        adw_toolbar_view.add_bottom_bar(adw_view_switcher_bar)

        if ADW_VERSION>=(1,4,0):
            breakpoint_condition = Adw.BreakpointCondition.new_length(
                type=Adw.BreakpointConditionLengthType.MAX_WIDTH,
                value=550,
                unit=Adw.LengthUnit.PX,
            )
            break_point = Adw.Breakpoint.new(condition=breakpoint_condition)
            none_value = GObject.Value()
            none_value.init(GObject.TYPE_OBJECT)
            none_value.set_object(None)

            break_point.add_setters(
                objects=[adw_view_switcher_bar, self.adw_header_bar],
                names=["reveal", "title-widget"],
                values=[True, none_value],
            )
            self.add_breakpoint(breakpoint=break_point)

        adw_navigation_page = NavigationPage.new(
            child=adw_toolbar_view, title="Waydroid Helper"
        )
        self.navigation_view.push(adw_navigation_page)


        self.waydroid = Waydroid()
        general_page = GeneralPage(self.waydroid)
        props_page = PropsPage(self.waydroid)
        extensions_page = ExtensionsPage(self.waydroid)

        self.stack_add_titled_with_icon(
            child=general_page,
            name="page01",
            title=_("Home"),
            icon_name="home-symbolic",
        )
        self.stack_add_titled_with_icon(
            child=props_page,
            name="page02",
            title=_("Settings"),
            icon_name="system-symbolic",
        )
        self.stack_add_titled_with_icon(
            child=extensions_page,
            name="page03",
            title=_("Extensions"),
            icon_name="addon-symbolic",
        )
