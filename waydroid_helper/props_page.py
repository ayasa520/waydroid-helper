import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gettext import gettext as _
import json
import os
from waydroid_helper.infobar import InfoBar
from waydroid_helper.util.task import Task
from waydroid_helper.waydroid import PropsState, Waydroid
from gi.repository import Gtk, GObject, Adw, GLib
from functools import partial


@Gtk.Template(resource_path="/com/jaoushingan/WaydroidHelper/ui/PropsPage.ui")
class PropsPage(Gtk.Box):
    __gtype_name__ = "PropsPage"

    items = dict()

    switch_1: Gtk.Switch = Gtk.Template.Child()
    switch_2: Gtk.Switch = Gtk.Template.Child()
    switch_3: Gtk.Switch = Gtk.Template.Child()
    switch_4: Gtk.Switch = Gtk.Template.Child()
    switch_5: Gtk.Switch = Gtk.Template.Child()
    entry_1: Gtk.Switch = Gtk.Template.Child()
    entry_2: Gtk.Switch = Gtk.Template.Child()
    entry_3: Gtk.Switch = Gtk.Template.Child()
    entry_4: Gtk.Switch = Gtk.Template.Child()
    entry_5: Gtk.Switch = Gtk.Template.Child()
    entry_6: Gtk.Switch = Gtk.Template.Child()
    switch_21: Gtk.Switch = Gtk.Template.Child()
    device_combo: Adw.ComboRow = Gtk.Template.Child()
    overlay: Gtk.Overlay = None
    waydroid: Waydroid = GObject.Property(default=None, type=Waydroid)
    reset_persist_prop_btn: Gtk.Button = Gtk.Template.Child()
    reset_privileged_prop_btn: Gtk.Button = Gtk.Template.Child()

    timeout_id = dict()

    _task = Task()
    ids = dict()

    def __init__(self, waydroid: Waydroid, **kargs):
        super().__init__(**kargs)

        data_dir = os.getenv("PKGDATADIR")

        with open(os.path.join(data_dir, "data", "devices.json")) as f:
            self.items = json.load(f)

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

        self.waydroid.persist_props.bind_property(
            self.entry_3.get_name(),
            self.entry_3,
            "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )

        self.waydroid.persist_props.bind_property(
            self.entry_4.get_name(),
            self.entry_4,
            "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )

        self.waydroid.persist_props.bind_property(
            self.entry_5.get_name(),
            self.entry_5,
            "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        self.waydroid.persist_props.bind_property(
            self.entry_6.get_name(),
            self.entry_6,
            "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        self.waydroid.privileged_props.bind_property(
            self.switch_21.get_name(),
            self.switch_21,
            "active",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
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

        model = Gtk.StringList.new(strings=list(self.items["index"].keys()))
        self.device_combo.set_model(model=model)

        # 用 bind 也行？
        # self.waydroid.privileged_props.bind_property(
        #     "ro-product-model",
        #     self.device_combo,
        #     "selected",
        #     GObject.BindingFlags.DEFAULT,
        #     # from the source to target
        #     self.on_device_info_changed,
        #     # partial(self.on_adw_combo_row_selected_item,prop_name="ro-product-brand"),
        # )
        # self.waydroid.privileged_props.bind_property(
        #     "ro-product-brand",
        #     self.device_combo,
        #     "selected",
        #     GObject.BindingFlags.DEFAULT,
        #     self.on_device_info_changed,
        #     # partial(self.on_adw_combo_row_selected_item,prop_name="ro-product-model"),
        # )
        self._model_changed = False
        self._brand_changed = False
        self.waydroid.privileged_props.connect(
            "notify::ro-product-model", self.__on_model_changed
        )
        self.waydroid.privileged_props.connect(
            "notify::ro-product-brand", self.__on_brand_changed
        )

    def check_both_properties_changed(self):
        if self._model_changed and self._brand_changed:
            self._model_changed = False
            self._brand_changed = False
            self.on_device_info_changed()

    def __on_model_changed(self, obj, param_spec):
        self._model_changed = True
        self.check_both_properties_changed()

    def __on_brand_changed(self, obj, param_spec):
        self._brand_changed = True
        self.check_both_properties_changed()

    # waydroid prop to selected
    def on_device_info_changed(self):
        product_brand = self.waydroid.privileged_props.get_property("ro-product-brand")
        product_model = self.waydroid.privileged_props.get_property("ro-product-model")
        device = f"{product_brand} {product_model}"
        current: str = self.device_combo.get_selected_item().get_string()
        if device == current:
            return
        if device in self.items["index"].keys():
            self.device_combo.set_selected(self.items["index"][device])
        else:
            self.device_combo.set_selected(0)

    # # selected to waydroid prop
    def on_adw_combo_row_selected_item(self, comborow, GParamObject):
        self.set_reveal(self.save_privileged_notification, True)
        selected_item = comborow.get_selected_item()
        self.waydroid.privileged_props.set_device_info(
            self.items["devices"][self.items["index"][selected_item.get_string()]][
                "properties"
            ]
        )

    def __connect(self, source: GObject.Object, signal, handler):
        id = source.connect(signal, handler)
        self.ids[f"{hash(source)}_{signal}"] = id

    def __disconnect(self, source: GObject.Object, signal):
        id = self.ids.get(f"{hash(source)}_{signal}", -1)
        if id == -1:
            return
        source.disconnect(id)
        self.ids.pop(f"{hash(source)}_{signal}")

    def on_waydroid_privileged_state_changed(self, w, param):
        if w.get_property("state") == PropsState.READY:
            self.switch_21.set_sensitive(True)
            self.device_combo.set_sensitive(True)
            self.reset_privileged_prop_btn.set_sensitive(True)

            self.__connect(
                self.device_combo,
                "notify::selected-item",
                self.on_adw_combo_row_selected_item,
            )
            self.__connect(
                self.switch_21,
                "notify::active",
                partial(
                    self.on_privileged_switch_clicked, name=self.switch_21.get_name()
                ),
            )

        else:
            self.__disconnect(self.device_combo, "notify::selected-item")
            self.__disconnect(self.switch_21, "notify::active")
            self.switch_21.set_sensitive(False)
            self.device_combo.set_sensitive(False)
            self.reset_privileged_prop_btn.set_sensitive(False)

    def on_waydroid_persist_state_changed(self, w, param):
        if w.get_property("state") == PropsState.READY:
            self.switch_1.set_sensitive(True)
            self.switch_2.set_sensitive(True)
            self.switch_3.set_sensitive(True)
            self.switch_4.set_sensitive(True)
            self.switch_5.set_sensitive(True)
            self.entry_1.set_sensitive(True)
            self.entry_2.set_sensitive(True)
            self.entry_3.set_sensitive(True)
            self.entry_4.set_sensitive(True)
            self.entry_5.set_sensitive(True)
            self.entry_6.set_sensitive(True)
            self.reset_persist_prop_btn.set_sensitive(True)
            self.__connect(
                self.entry_1,
                "notify::text",
                partial(self.on_persist_text_changed, name=self.entry_1.get_name()),
            )

            self.__connect(
                self.entry_2,
                "notify::text",
                partial(self.on_persist_text_changed, name=self.entry_2.get_name()),
            )
            self.__connect(
                self.entry_3,
                "notify::text",
                partial(
                    partial(self.on_persist_text_changed, flag=True),
                    name=self.entry_3.get_name(),
                ),
            )
            self.__connect(
                self.entry_4,
                "notify::text",
                partial(
                    partial(self.on_persist_text_changed, flag=True),
                    name=self.entry_4.get_name(),
                ),
            )
            self.__connect(
                self.entry_5,
                "notify::text",
                partial(
                    partial(self.on_persist_text_changed, flag=True),
                    name=self.entry_5.get_name(),
                ),
            )
            self.__connect(
                self.entry_6,
                "notify::text",
                partial(
                    partial(self.on_persist_text_changed, flag=True),
                    name=self.entry_6.get_name(),
                ),
            )

            self.__connect(
                self.switch_1,
                "notify::active",
                partial(self.on_perisit_switch_clicked, name=self.switch_1.get_name()),
            )

            self.__connect(
                self.switch_2,
                "notify::active",
                partial(self.on_perisit_switch_clicked, name=self.switch_2.get_name()),
            )

            self.__connect(
                self.switch_3,
                "notify::active",
                partial(self.on_perisit_switch_clicked, name=self.switch_3.get_name()),
            )

            self.__connect(
                self.switch_4,
                "notify::active",
                partial(self.on_perisit_switch_clicked, name=self.switch_4.get_name()),
            )

            self.__connect(
                self.switch_5,
                "notify::active",
                partial(self.on_perisit_switch_clicked, name=self.switch_5.get_name()),
            )
        else:
            self.__disconnect(self.switch_1, "notify::active")
            self.__disconnect(self.switch_2, "notify::active")
            self.__disconnect(self.switch_3, "notify::active")
            self.__disconnect(self.switch_4, "notify::active")
            self.__disconnect(self.switch_5, "notify::active")
            self.__disconnect(self.entry_1, "notify::text")
            self.__disconnect(self.entry_2, "notify::text")
            self.__disconnect(self.entry_3, "notify::text")
            self.__disconnect(self.entry_3, "notify::text")
            self.__disconnect(self.entry_4, "notify::text")
            self.__disconnect(self.entry_5, "notify::text")
            self.__disconnect(self.entry_6, "notify::text")
            self.switch_1.set_sensitive(False)
            self.switch_2.set_sensitive(False)
            self.switch_3.set_sensitive(False)
            self.switch_4.set_sensitive(False)
            self.switch_5.set_sensitive(False)
            self.entry_1.set_sensitive(False)
            self.entry_2.set_sensitive(False)
            self.entry_3.set_sensitive(False)
            self.entry_4.set_sensitive(False)
            self.entry_5.set_sensitive(False)
            self.entry_6.set_sensitive(False)
            self.reset_persist_prop_btn.set_sensitive(False)

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
        # 这种判断state==ready时再connect, state==uninitialized时候disconnect是不是更好?
        # if self.waydroid.privileged_props.get_property("state") != PropsState.READY:
        #     return
        self.set_reveal(self.save_privileged_notification, True)
        # self.save_privileged_notification.set_reveal_child(True)

    def __on_persist_text_changed(self, name):
        self._task.create_task(self.waydroid.save_persist_prop(name))
        self.timeout_id[name] = None

    def on_persist_text_changed(self, a, b, name, flag=False):
        # if self.waydroid.persist_props.get_property("state") != PropsState.READY:
        #     return
        if self.timeout_id.get(name) is not None:
            GLib.source_remove(self.timeout_id[name])

        self.timeout_id[name] = GLib.timeout_add(
            1000, partial(self.__on_persist_text_changed, name)
        )
        if flag:
            self.set_reveal(self.save_notification, True)

    def on_perisit_switch_clicked(self, a: Gtk.Switch, b, name):
        # print(a.get_widget().get_name())
        # if self.waydroid.persist_props.get_property("state") != PropsState.READY:
        #     return
        # print("回调")
        self.set_reveal(self.save_notification, True)
        # self.save_notification.set_reveal_child(True)
        # print("来咯", name, self.waydroid.persist_props.get_property(name))
        self._task.create_task(self.waydroid.save_persist_prop(name))

    def on_cancel_button_clicked(self, button):
        self.set_reveal(self.save_notification, False)
        # self.save_notification.set_reveal_child(False)

    def on_restart_button_clicked(self, button):
        self.set_reveal(self.save_notification, False)
        # self.save_notification.set_reveal_child(False)
        self._task.create_task(self.waydroid.restart_session())

    def on_restore_button_clicked(self, button):
        self.set_reveal(self.save_privileged_notification, False)
        # self.save_privileged_notification.set_reveal_child(False)
        self.waydroid.restore_privileged_props()

    def on_apply_button_clicked(self, button):
        self.set_reveal(self.save_privileged_notification, False)
        # self.save_privileged_notification.set_reveal_child(False)
        self._task.create_task(self.waydroid.save_privileged_props())

    @Gtk.Template.Callback()
    def on_reset_persist_clicked(self, button):
        self._task.create_task(self.waydroid.reset_persist_props())

    @Gtk.Template.Callback()
    def on_reset_privileged_clicked(self, button):
        self._task.create_task(self.waydroid.reset_privileged_props())

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
