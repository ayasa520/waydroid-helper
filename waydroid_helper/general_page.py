# pyright: reportCallIssue=false
# pyright: reportUnknownVariableType=false
# pyright: reportAny=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

from gettext import gettext as _
from typing import cast

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, GObject, Gtk

from waydroid_helper.controller import TransparentWindow
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
    open_key_mapping_button: Gtk.Button = Gtk.Template.Child("open-key-mapping-button")
    close_key_mapping_button: Gtk.Button = Gtk.Template.Child("close-key-mapping-button")
    shared_folders_widget: SharedFoldersWidget = Gtk.Template.Child()
    # mount_list:Gtk.ListBox = Gtk.Template.Child()

    _task: Task = Task()
    _key_mapping_window: TransparentWindow | None = None
    _app: Gtk.Application | None = None

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
            
        # Always update key mapping buttons status
        self._update_key_mapping_buttons()

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
        
        # Initialize application instance
        self._app = None
        
        # Get application instance with delay to ensure UI is fully initialized
        GLib.idle_add(self._get_app_instance)
        
        # Initialize key mapping buttons status after delay
        GLib.idle_add(self._update_key_mapping_buttons)

    def _get_app_instance(self):
        """Get application instance with delay"""
        try:
            root = self.get_root()
            if root and hasattr(root, 'get_application'):
                self._app = root.get_application()  # pyright: ignore[reportAttributeAccessIssue]
                logger.debug("Successfully get application instance")
        except Exception as e:
            logger.error(f"Get application instance failed: {e}")
        return False  # Do not repeat execution

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

    def _update_key_mapping_buttons(self):
        """Update key mapping buttons status"""
        try:
            if self._key_mapping_window and self._key_mapping_window.is_visible():
                self.open_key_mapping_button.set_sensitive(False)
                self.close_key_mapping_button.set_sensitive(True)
            else:
                self.open_key_mapping_button.set_sensitive(True)
                self.close_key_mapping_button.set_sensitive(False)
        except Exception as e:
            logger.error(f"Update key mapping buttons status failed: {e}")
            # Set to default state when error occurs
            self.open_key_mapping_button.set_sensitive(True)
            self.close_key_mapping_button.set_sensitive(False)

    @Gtk.Template.Callback()
    def on_open_key_mapping_clicked(self, button: Gtk.Button):
        """Open key mapping window"""
        logger.info("Open key mapping window")
        try:
            if self._app:
                # Create key mapping window
                self._key_mapping_window = TransparentWindow(self._app)
                # Listen for window close event
                self._key_mapping_window.connect("close-request", self._on_key_mapping_window_closed)
                self._key_mapping_window.present()
                # Update button status
                self._update_key_mapping_buttons()
                logger.info("Key mapping window opened")
                
                # Minimize the main window
                root = self.get_root()
                root = cast(Gtk.ApplicationWindow, root)
                if root and hasattr(root, 'minimize'):
                    root.minimize()
                    logger.info("Main window minimized")
            else:
                logger.error("Cannot get application instance")
        except Exception as e:
            logger.error(f"Open key mapping window failed: {e}")

    def _on_key_mapping_window_closed(self, window):
        """Callback when key mapping window is closed"""
        logger.info("Key mapping window closed")
        self._key_mapping_window = None
        self._update_key_mapping_buttons()
        return False  # Allow window to close

    @Gtk.Template.Callback()
    def on_close_key_mapping_clicked(self, button: Gtk.Button):
        """Close key mapping window"""
        logger.info("Close key mapping window")
        try:
            if self._key_mapping_window:
                self._key_mapping_window.close()
                # No need to set to None here, close-request will trigger callback
                logger.info("Key mapping window close request sent")
            else:
                logger.warning("No open key mapping window")
        except Exception as e:
            logger.error(f"Close key mapping window failed: {e}")
            # Manually clean up on error
            self._key_mapping_window = None
            self._update_key_mapping_buttons()
