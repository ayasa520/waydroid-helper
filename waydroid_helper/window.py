import subprocess
from gi.repository import Gtk, GLib, GObject, Adw
from waydroid_helper.waydroid import Waydroid
from gettext import gettext as _


@Gtk.Template(resource_path='/com/jaoushingan/WaydroidHelper/window.ui')
class WaydroidHelperWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'WaydroidHelperWindow'
    status = Gtk.Template.Child()
    status_image = Gtk.Template.Child("status-image")
    informer: Gtk.Button = Gtk.Template.Child("stop-button")
    switch_1 = Gtk.Template.Child()
    switch_2 = Gtk.Template.Child()
    switch_3 = Gtk.Template.Child()
    switch_4 = Gtk.Template.Child()
    switch_5 = Gtk.Template.Child()
    switch_6 = Gtk.Template.Child()
    switch_7 = Gtk.Template.Child()
    switch_21 = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.waydroid = Waydroid()
        self.waydroid.bind_property(
            "state", self.informer, "sensitive",  GObject.BindingFlags.SYNC_CREATE)
        self.waydroid.persist_props.connect(
            "notify::state", self.on_waydroid_state_changed)
        self.waydroid.bind_property(
            "state", self.switch_1, "sensitive", GObject.BindingFlags.SYNC_CREATE)
        self.waydroid.persist_props.bind_property(
            "multi-windows", self.switch_1, "active", GObject.BindingFlags.BIDIRECTIONAL)
        self.waydroid.persist_props.bind_property(
            "cursor-on_subsurface", self.switch_2, "active", GObject.BindingFlags.BIDIRECTIONAL)
        self.waydroid.persist_props.bind_property(
            "invert-colors", self.switch_3, "active", GObject.BindingFlags.BIDIRECTIONAL)
        self.waydroid.persist_props.bind_property(
            "suspend", self.switch_4, "active", GObject.BindingFlags.BIDIRECTIONAL)
        self.waydroid.persist_props.bind_property(
            "uevent", self.switch_5, "active", GObject.BindingFlags.BIDIRECTIONAL)
        self.waydroid.persist_props.bind_property(
            "fake-touch", self.switch_6, "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self.waydroid.persist_props.bind_property(
            "fake-wifi", self.switch_7, "text", GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)

        self.waydroid.privileged_props.bind_property(
            "qemu-hw-mainkeys", self.switch_21, "active",
            GObject.BindingFlags.BIDIRECTIONAL |
            GObject.BindingFlags.SYNC_CREATE
        )

    def on_waydroid_state_changed(self, w: Waydroid, param):
        if w.get_property("state"):
            self.status.set_title(_("Connected"))
            self.status.set_subtitle(_("Waydroid session is running"))
            self.status_image.set_from_icon_name('vcs-normal')
        else:
            self.status.set_title(_("Stopped"))
            self.status.set_subtitle(_("Waydroid session is stopped"))
            self.status_image.set_from_icon_name('vcs-conflicting')

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
    
    @Gtk.Template.Callback()
    def on_save_privileged_props(self, button):
        print("save")
        self.waydroid.save_privileged_props()
