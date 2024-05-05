from gettext import gettext as _
from waydroid_helper.waydroid import Waydroid, WaydroidState
from gi.repository import Gtk, GObject
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')


@Gtk.Template(resource_path='/com/jaoushingan/WaydroidHelper/ui/PropsPage.ui')
class PropsPage(Gtk.Box):
    __gtype_name__ = "PropsPage"
    switch_1 = Gtk.Template.Child()
    switch_2 = Gtk.Template.Child()
    switch_3 = Gtk.Template.Child()
    switch_4 = Gtk.Template.Child()
    switch_5 = Gtk.Template.Child()
    switch_6 = Gtk.Template.Child()
    switch_7 = Gtk.Template.Child()
    switch_21 = Gtk.Template.Child()

    waydroid: GObject.Property = GObject.Property(default=None, type=Waydroid)

    def __init__(self, waydroid: Waydroid, **kargs):
        super().__init__(**kargs)

        self.set_property("waydroid", waydroid)
        self.waydroid.connect(
            "notify::state", self.on_waydroid_state_changed)
        # self.waydroid.bind_property(
        #     "state", self.switch_1, "sensitive", GObject.BindingFlags.SYNC_CREATE)
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

    def on_waydroid_state_changed(self, w, param):
        print("状态改变, 在 props", w.get_property("state"))
        if w.get_property("state") == WaydroidState.RUNNING:
            self.switch_1.set_sensitive(True)
            self.switch_2.set_sensitive(True)
            self.switch_3.set_sensitive(True)
            self.switch_4.set_sensitive(True)
            self.switch_5.set_sensitive(True)
            self.switch_6.set_sensitive(True)
            self.switch_7.set_sensitive(True)
            self.switch_21.set_sensitive(True)
        elif w.get_property("state") == WaydroidState.STOPPED:
            self.switch_1.set_sensitive(False)
            self.switch_2.set_sensitive(False)
            self.switch_3.set_sensitive(False)
            self.switch_4.set_sensitive(False)
            self.switch_5.set_sensitive(False)
            self.switch_6.set_sensitive(False)
            self.switch_7.set_sensitive(False)
            self.switch_21.set_sensitive(True)
        elif w.get_property("state") == WaydroidState.UNINITIALIZED:
            self.switch_1.set_sensitive(False)
            self.switch_2.set_sensitive(False)
            self.switch_3.set_sensitive(False)
            self.switch_4.set_sensitive(False)
            self.switch_5.set_sensitive(False)
            self.switch_6.set_sensitive(False)
            self.switch_7.set_sensitive(False)
            self.switch_21.set_sensitive(False)
        elif w.get_property("state") == WaydroidState.LOADING:
            self.switch_1.set_sensitive(False)
            self.switch_2.set_sensitive(False)
            self.switch_3.set_sensitive(False)
            self.switch_4.set_sensitive(False)
            self.switch_5.set_sensitive(False)
            self.switch_6.set_sensitive(False)
            self.switch_7.set_sensitive(False)
            self.switch_21.set_sensitive(False)

    @Gtk.Template.Callback()
    def on_save_privileged_props(self, button):
        print("save")
        self.waydroid.save_privileged_props()
