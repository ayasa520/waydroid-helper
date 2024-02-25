from gi.repository import Gtk, GObject

from gettext import gettext as _
from waydroid_helper.waydroid import Waydroid


@Gtk.Template(resource_path='/com/jaoushingan/WaydroidHelper/ui/PropPage.ui')
class PropPage(Gtk.Box):
    __gtype_name__ = "PropPage"
    switch_1 = Gtk.Template.Child()
    switch_2 = Gtk.Template.Child()
    switch_3 = Gtk.Template.Child()
    switch_4 = Gtk.Template.Child()
    switch_5 = Gtk.Template.Child()
    switch_6 = Gtk.Template.Child()
    switch_7 = Gtk.Template.Child()
    switch_21 = Gtk.Template.Child()

    waydroid: GObject.Property = GObject.Property(default=None, type=Waydroid)

    def __init__(self, **kargs):
        super().__init__(kargs)
        def init_later(w,p):
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
        self.connect("notify::waydroid", init_later)
    @Gtk.Template.Callback()
    def on_save_privileged_props(self, button):
        print("save")
        self.waydroid.save_privileged_props()
