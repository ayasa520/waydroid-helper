from gettext import gettext as _

from waydroid_helper.infobar import InfoBar
from waydroid_helper.waydroid import PropsState, Waydroid, WaydroidState
from gi.repository import Gtk, GObject, Adw, GLib
from functools import partial
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


@Gtk.Template(resource_path="/com/jaoushingan/WaydroidHelper/ui/PropsPage.ui")
class PropsPage(Gtk.Box):
    __gtype_name__ = "PropsPage"
    switch_1: Gtk.Switch = Gtk.Template.Child()
    switch_2: Gtk.Switch = Gtk.Template.Child()
    switch_3: Gtk.Switch = Gtk.Template.Child()
    switch_4: Gtk.Switch = Gtk.Template.Child()
    switch_5: Gtk.Switch = Gtk.Template.Child()
    entry_1: Gtk.Switch = Gtk.Template.Child()
    entry_2: Gtk.Switch = Gtk.Template.Child()
    switch_21: Gtk.Switch = Gtk.Template.Child()
    overlay: Gtk.Overlay = None
    waydroid: Waydroid = GObject.Property(default=None, type=Waydroid)

    timeout_id = dict()

    def __init__(self, waydroid: Waydroid, **kargs):
        super().__init__(**kargs)

        self.set_property("waydroid", waydroid)
        self.waydroid.persist_props.connect(
            "notify::state", self.on_waydroid_persist_state_changed
        )
        self.waydroid.privileged_props.connect(
            "notify::state", self.on_waydroid_privileged_state_changed
        )
        # # self.waydroid.bind_property(
        # #     "state", self.switch_1, "sensitive", GObject.BindingFlags.SYNC_CREATE)

        self.waydroid.persist_props.bind_property(
            self.switch_1.get_name(),
            self.switch_1,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL,
        )

        self.waydroid.persist_props.bind_property(
            self.switch_2.get_name(),
            self.switch_2,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL,
        )
        self.waydroid.persist_props.bind_property(
            self.switch_3.get_name(),
            self.switch_3,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL,
        )
        self.waydroid.persist_props.bind_property(
            self.switch_4.get_name(),
            self.switch_4,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL,
        )
        self.waydroid.persist_props.bind_property(
            self.switch_5.get_name(),
            self.switch_5,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL,
        )
        self.waydroid.persist_props.bind_property(
            self.entry_1.get_name(),
            self.entry_1,
            "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        self.waydroid.persist_props.bind_property(
            self.entry_2.get_name(),
            self.entry_2,
            "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )

        self.waydroid.privileged_props.bind_property(
            self.switch_21.get_name(),
            self.switch_21,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )

        self.switch_1.connect(
            "notify::active",
            partial(self.on_perisit_switch_clicked, name=self.switch_1.get_name()),
        )

        self.switch_2.connect(
            "notify::active",
            partial(self.on_perisit_switch_clicked, name=self.switch_2.get_name()),
        )

        self.switch_3.connect(
            "notify::active",
            partial(self.on_perisit_switch_clicked, name=self.switch_3.get_name()),
        )

        self.switch_4.connect(
            "notify::active",
            partial(self.on_perisit_switch_clicked, name=self.switch_4.get_name()),
        )

        self.switch_5.connect(
            "notify::active",
            partial(self.on_perisit_switch_clicked, name=self.switch_5.get_name()),
        )

        self.entry_1.connect(
            "notify::text",
            partial(self.on_persist_text_changed, name=self.entry_1.get_name()),
        )

        self.entry_2.connect(
            "notify::text",
            partial(self.on_persist_text_changed, name=self.entry_2.get_name()),
        )

        self.switch_21.connect(
            "notify::active",
            partial(self.on_privileged_switch_clicked, name=self.switch_21.get_name()),
        )

        self.save_notification: InfoBar = InfoBar(
            label=_("Restart the session to apply the changes"),
            cancel_callback=self.on_cancel_button_clicked,
            ok_callback=self.on_restart_button_clicked,
        )
        self.save_privileged_notification: InfoBar = InfoBar(
            label=_("Save and restart the container"),
            cancel_callback=self.on_restore_button_clicked,
            ok_callback=self.on_apply_button_clicked,
        )

    def on_waydroid_privileged_state_changed(self, w, param):
        if w.get_property("state") == PropsState.READY:
            self.switch_21.set_sensitive(True)
        else:
            self.switch_21.set_sensitive(False)

    def on_waydroid_persist_state_changed(self, w, param):
        if w.get_property("state") == PropsState.READY:
            self.switch_1.set_sensitive(True)
            self.switch_2.set_sensitive(True)
            self.switch_3.set_sensitive(True)
            self.switch_4.set_sensitive(True)
            self.switch_5.set_sensitive(True)
            self.entry_1.set_sensitive(True)
            self.entry_2.set_sensitive(True)
        else:
            self.switch_1.set_sensitive(False)
            self.switch_2.set_sensitive(False)
            self.switch_3.set_sensitive(False)
            self.switch_4.set_sensitive(False)
            self.switch_5.set_sensitive(False)
            self.entry_1.set_sensitive(False)
            self.entry_2.set_sensitive(False)

    def set_reveal(self, widget: InfoBar, reveal_child: bool):
        if (
            reveal_child == True
            and not self.save_notification.get_reveal_child()
            and not self.save_privileged_notification.get_reveal_child()
        ):
            if self.overlay:
                self.remove(self.overlay)
            self.overlay = Gtk.Overlay.new()
            self.append(self.overlay)
            if widget == self.save_notification:
                self.overlay.set_child(self.save_notification)
                self.overlay.add_overlay(self.save_privileged_notification)
            else:
                self.overlay.set_child(self.save_privileged_notification)
                self.overlay.add_overlay(self.save_notification)
        widget.set_reveal_child(reveal_child)

    def on_privileged_switch_clicked(self, a, b, name):
        if self.waydroid.privileged_props.get_property("state") != PropsState.READY:
            return
        self.set_reveal(self.save_privileged_notification, True)
        # self.save_privileged_notification.set_reveal_child(True)

    def __on_persist_text_changed(self, name):
        self.waydroid.set_persist_prop(name)
        self.timeout_id[name] = None

    def on_persist_text_changed(self, a, b, name):
        if self.waydroid.persist_props.get_property("state") != PropsState.READY:
            return
        if self.timeout_id.get(name) is not None:
            GLib.source_remove(self.timeout_id[name])

        self.timeout_id[name] = GLib.timeout_add(
            1000, partial(self.__on_persist_text_changed, name)
        )

    def on_perisit_switch_clicked(self, a: Gtk.Switch, b, name):
        # print(a.get_widget().get_name())
        if self.waydroid.persist_props.get_property("state") != PropsState.READY:
            return
        # print("回调")
        self.set_reveal(self.save_notification, True)
        # self.save_notification.set_reveal_child(True)
        # print("来咯", name, self.waydroid.persist_props.get_property(name))
        self.waydroid.set_persist_prop(name)

    def on_cancel_button_clicked(self, button):
        self.set_reveal(self.save_notification, False)
        # self.save_notification.set_reveal_child(False)

    def on_restart_button_clicked(self, button):
        self.set_reveal(self.save_notification, False)
        # self.save_notification.set_reveal_child(False)
        self.waydroid.restart_session()

    def on_restore_button_clicked(self, button):
        self.set_reveal(self.save_privileged_notification, False)
        # self.save_privileged_notification.set_reveal_child(False)
        self.waydroid.restore_privileged_props()

    def on_apply_button_clicked(self, button):
        self.set_reveal(self.save_privileged_notification, False)
        # self.save_privileged_notification.set_reveal_child(False)
        self.waydroid.save_privileged_props()

    # @Gtk.Template.Callback()
    # def on_switch_clicked(self, a:Gtk.Switch, b=None, c=None, d=None):
    #     # print(a.get_widget().get_name())
    #     print("回调")
    #     if self.waydroid.persist_props.get_state()!=2:
    #         return

    #     print("switch")

    #     print(a.get_active(),b,c,d)
    #     self.save_notification.set_reveal_child(not         self.save_notification.get_reveal_child())

    # @Gtk.Template.Callback()
    # def on_actionrow_clicked(self, a:Gtk.GestureClick, b, c, d):
    #     print(a.get_widget().get_name())
    #     if b > 1:
    #         return
    #     else:
    #         self.save_notification.set_reveal_child(True)
