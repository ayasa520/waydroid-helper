from gettext import gettext as _
from waydroid_helper.util.Task import Task
from waydroid_helper.waydroid import Waydroid
from waydroid_helper.waydroid import WaydroidState
from gi.repository import Gtk, GObject, Gdk
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


@Gtk.Template(resource_path="/com/jaoushingan/WaydroidHelper/ui/GeneralPage.ui")
class GeneralPage(Gtk.Box):
    __gtype_name__ = "GeneralPage"
    waydroid: Waydroid = GObject.Property(default=None, type=Waydroid)
    status = Gtk.Template.Child()
    status_image = Gtk.Template.Child("status-image")
    stop_button: Gtk.Button = Gtk.Template.Child("stop-button")
    start_button: Gtk.Button = Gtk.Template.Child("start-button")
    general_button_stack: Gtk.Stack = Gtk.Template.Child()
    init_button: Gtk.Button = Gtk.Template.Child("init-button")
    updrade_button: Gtk.Button = Gtk.Template.Child()

    _task = Task()

    def on_waydroid_state_changed(self, w, param):
        if w.get_property("state") == WaydroidState.RUNNING:
            self.status.set_title(_("Connected"))
            self.status.set_subtitle(_("Waydroid session is running"))
            self.status_image.set_from_icon_name("vcs-normal")
            self.start_button.set_sensitive(False)
            self.stop_button.set_sensitive(True)
            self.general_button_stack.set_visible_child_name("initialized_menu")
            self.updrade_button.set_sensitive(True)
        elif w.get_property("state") == WaydroidState.STOPPED:
            self.status.set_title(_("Stopped"))
            self.status.set_subtitle(_("Waydroid session is stopped"))
            self.status_image.set_from_icon_name("vcs-conflicting")
            self.start_button.set_sensitive(True)
            self.stop_button.set_sensitive(False)
            self.general_button_stack.set_visible_child_name("initialized_menu")
            self.updrade_button.set_sensitive(True)
        elif w.get_property("state") == WaydroidState.UNINITIALIZED:
            self.status.set_title(_("Uninitialized"))
            self.status.set_subtitle(_("Waydroid is not initialized"))
            self.status_image.set_from_icon_name("vcs-conflicting")
            self.general_button_stack.set_visible_child_name("uninitialized_menu")
            self.init_button.set_sensitive(True)
            self.updrade_button.set_sensitive(False)
        elif w.get_property("state") == WaydroidState.LOADING:
            self.status.set_title(_("Loading"))
            self.status.set_subtitle("")
            self.status_image.set_from_icon_name("")
            self._disable_buttons()

    def __init__(self, waydroid: Waydroid, **kargs):
        super().__init__(**kargs)
        self.set_property("waydroid", waydroid)
        self.waydroid.connect("notify::state", self.on_waydroid_state_changed)

    def _disable_buttons(self):
        self.start_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)
        self.init_button.set_sensitive(False)
        self.updrade_button.set_sensitive(False)

    @Gtk.Template.Callback()
    def on_init_button_clicked(self, button: Gtk.Button):
        self._disable_buttons()
        print("waydroid init")
        # TODO

    @Gtk.Template.Callback()
    def on_start_button_clicked(self, button: Gtk.Button):
        print("waydroid session start")
        self._disable_buttons()
        self._task.create_task(self.waydroid.start_session())

    @Gtk.Template.Callback()
    def on_stop_button_clicked(self, button):
        print("waydroid session stop")
        self._disable_buttons()
        self._task.create_task(self.waydroid.stop_session())

    @Gtk.Template.Callback()
    def on_start_upgrade_offline_clicked(self, button):
        print("sudo waydroid upgrade -o")
        self._disable_buttons()
        self._task.create_task(self.waydroid.upgrade(True))
