from gi.repository import Gtk, GObject

from gettext import gettext as _
from waydroid_helper.waydroid import Waydroid


@Gtk.Template(resource_path='/com/jaoushingan/WaydroidHelper/ui/GeneralPage.ui')
class GeneralPage(Gtk.Box):
    __gtype_name__ = "GeneralPage"
    waydroid: GObject.Property = GObject.Property(default=None, type=Waydroid)
    status = Gtk.Template.Child()
    status_image = Gtk.Template.Child("status-image")
    informer: Gtk.Button = Gtk.Template.Child("stop-button")

    def on_waydroid_state_changed(self, w, param):
        if w.get_property("state"):
            self.status.set_title(_("Connected"))
            self.status.set_subtitle(_("Waydroid session is running"))
            self.status_image.set_from_icon_name('vcs-normal')
        else:
            self.status.set_title(_("Stopped"))
            self.status.set_subtitle(_("Waydroid session is stopped"))
            self.status_image.set_from_icon_name('vcs-conflicting')

    def __init__(self, **kargs):
        super().__init__(**kargs)

        def init_later(w, p):
            if not self.waydroid:
                return
            self.waydroid.bind_property(
                "state",
                self.informer,
                "sensitive",
                GObject.BindingFlags.SYNC_CREATE
            )
            self.waydroid.connect(
                "notify::state", self.on_waydroid_state_changed)
        self.connect("notify::waydroid", init_later)

    @Gtk.Template.Callback()
    def on_start_button_clicked(self, button: Gtk.Button):
        print("waydroid session start")
        self.waydroid.start_session()

    @Gtk.Template.Callback()
    def on_stop_button_clicked(self, button):
        print("waydroid session stop")
        self.waydroid.stop_session()

    @Gtk.Template.Callback()
    def on_start_upgrade_offline_clicked(self, button):
        print("sudo waydroid upgrade -o")
        self.waydroid.upgrade(True)
