# pyright: reportCallIssue=false
# pyright: reportUnknownVariableType=false
# pyright: reportAny=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GObject, Gtk

from waydroid_helper.infobar import InfoBar
from waydroid_helper.shared_folder import SharedFoldersWidget
from waydroid_helper.util import Task, logger, template
from waydroid_helper.waydroid import Waydroid, WaydroidState


@template(resource_path="/com/jaoushingan/WaydroidHelper/ui/GeneralPage.ui")
class GeneralPage(Gtk.Box):
    __gtype_name__: str = "GeneralPage"
    waydroid: Waydroid = GObject.Property(
        default=None, type=Waydroid
    )  # pyright: ignore[reportAssignmentType]
    status: Adw.ActionRow = Gtk.Template.Child()
    status_image: Gtk.Image = Gtk.Template.Child("status-image")
    stop_button: Gtk.Button = Gtk.Template.Child("stop-button")
    start_button: Gtk.Button = Gtk.Template.Child("start-button")
    general_button_stack: Gtk.Stack = Gtk.Template.Child()
    init_button: Gtk.Button = Gtk.Template.Child("init-button")
    updrade_button: Gtk.Button = Gtk.Template.Child()
    show_full_ui_button: Gtk.Button = Gtk.Template.Child("show-full-ui-button")
    shared_folders_widget: SharedFoldersWidget = Gtk.Template.Child()
    # mount_list:Gtk.ListBox = Gtk.Template.Child()

    _task: Task = Task()

    def update_menu(self, state: WaydroidState):
        if state == WaydroidState.RUNNING:
            self.status.set_title(_("Connected"))
            self.status.set_subtitle(_("Waydroid session is running"))
            self.status_image.set_from_icon_name("normal")
            self.start_button.set_sensitive(False)
            self.stop_button.set_sensitive(True)
            self.general_button_stack.set_visible_child_name("initialized_menu")
            self.updrade_button.set_sensitive(True)
            self.show_full_ui_button.set_sensitive(True)
        elif state == WaydroidState.STOPPED:
            self.status.set_title(_("Stopped"))
            self.status.set_subtitle(_("Waydroid session is stopped"))
            self.status_image.set_from_icon_name("conflicting")
            self.start_button.set_sensitive(True)
            self.stop_button.set_sensitive(False)
            self.general_button_stack.set_visible_child_name("initialized_menu")
            self.updrade_button.set_sensitive(True)
            self.show_full_ui_button.set_sensitive(True)

        elif state == WaydroidState.UNINITIALIZED:
            self.status.set_title(_("Uninitialized"))
            self.status.set_subtitle(_("Waydroid is not initialized"))
            self.status_image.set_from_icon_name("conflicting")
            self.general_button_stack.set_visible_child_name("uninitialized_menu")
            self.init_button.set_sensitive(True)
            self.updrade_button.set_sensitive(False)
            self.show_full_ui_button.set_sensitive(False)
        elif state == WaydroidState.LOADING:
            self.status.set_title(_("Loading"))
            self.status.set_subtitle("")
            self.status_image.set_from_icon_name("")
            self._disable_buttons()

    def on_waydroid_state_changed(self, w: GObject.Object, param: GObject.ParamSpec):
        self.update_menu(w.get_property(param.name))

    def __init__(
        self,
        waydroid: Waydroid,
        **kargs  # pyright: ignore[reportMissingParameterType,reportUnknownParameterType]
    ):
        super().__init__(**kargs)
        self.set_property("waydroid", waydroid)
        self.waydroid.connect("notify::state", self.on_waydroid_state_changed)
        self.infobar: InfoBar = InfoBar(
            label=_("Restart the systemd user service immediately"),
            ok_callback=lambda *_: self.shared_folders_widget.restart_service(),
        )
        self.shared_folders_widget.connect(
            "updated", lambda _: self.infobar.set_reveal_child(True)
        )
        self.append(self.infobar)

    def _disable_buttons(self):
        self.start_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)
        self.init_button.set_sensitive(False)
        self.updrade_button.set_sensitive(False)
        self.show_full_ui_button.set_sensitive(False)

    @Gtk.Template.Callback()
    def on_init_button_clicked(self, button: Gtk.Button):
        self._disable_buttons()
        logger.info("waydroid init")
        # TODO

    async def __on_start_button_clicked(self):
        old = self.waydroid.state
        self._disable_buttons()
        await self.waydroid.start_session()
        if old == self.waydroid.state:
            self.update_menu(self.waydroid.state)

    @Gtk.Template.Callback()
    def on_start_button_clicked(self, button: Gtk.Button):
        logger.info("waydroid session start")
        self._task.create_task(self.__on_start_button_clicked())

    async def __on_stop_button_clicked(self):
        old = self.waydroid.state
        self._disable_buttons()
        await self.waydroid.stop_session()
        if old == self.waydroid.state:
            self.update_menu(self.waydroid.state)

    @Gtk.Template.Callback()
    def on_stop_button_clicked(self, button: Gtk.Button):
        logger.info("waydroid session stop")
        self._task.create_task(self.__on_stop_button_clicked())

    @Gtk.Template.Callback()
    def on_show_full_ui_button_clicked(self, button: Gtk.Button):
        logger.info("waydroid show-full-ui")
        self._task.create_task(self.waydroid.show_full_ui())

    async def __on_start_upgrade_offline_clicked(self):
        old = self.waydroid.state
        self._disable_buttons()
        await self.waydroid.upgrade(True)
        if old == self.waydroid.state:
            self.update_menu(self.waydroid.state)

    @Gtk.Template.Callback()
    def on_start_upgrade_offline_clicked(self, button: Gtk.Button):
        logger.info("sudo waydroid upgrade -o")
        self._task.create_task(self.__on_start_upgrade_offline_clicked())

    #
    # @Gtk.Template.Callback()
    # def on_mount_point_add_button_clicked(self, button):
    #     pass
