# pyright: reportAny=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownParameterType=false

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import json
import os
from functools import partial
from gettext import gettext as _

from gi.repository import Adw, GLib, GObject, Gtk

from waydroid_helper.infobar import InfoBar
from waydroid_helper.util import Task, logger, template
from waydroid_helper.waydroid import PropsState, Waydroid


@template(resource_path="/com/jaoushingan/WaydroidHelper/ui/PropsPage.ui")
class PropsPage(Gtk.Box):
    __gtype_name__: str = "PropsPage"

    items: dict[Any, Any] = dict()

    switch_1: Gtk.Switch = Gtk.Template.Child()
    switch_2: Gtk.Switch = Gtk.Template.Child()
    switch_3: Gtk.Switch = Gtk.Template.Child()
    switch_4: Gtk.Switch = Gtk.Template.Child()
    switch_5: Gtk.Switch = Gtk.Template.Child()
    entry_1: Gtk.Entry = Gtk.Template.Child()
    entry_2: Gtk.Entry = Gtk.Template.Child()
    entry_3: Gtk.Entry = Gtk.Template.Child()
    entry_4: Gtk.Entry = Gtk.Template.Child()
    entry_5: Gtk.Entry = Gtk.Template.Child()
    entry_6: Gtk.Entry = Gtk.Template.Child()
    switch_21: Gtk.Switch = Gtk.Template.Child()
    device_combo: Adw.ComboRow = Gtk.Template.Child()
    waydroid_switch_1: Gtk.Switch = Gtk.Template.Child()
    waydroid_switch_2: Gtk.Switch = Gtk.Template.Child()
    waydroid_entry_1: Gtk.Entry = Gtk.Template.Child()
    overlay: Gtk.Overlay | None = None
    waydroid: Waydroid = GObject.Property(
        default=None, type=Waydroid
    )  # pyright:ignore[reportAssignmentType]
    reset_persist_prop_btn: Gtk.Button = Gtk.Template.Child()
    reset_privileged_prop_btn: Gtk.Button = Gtk.Template.Child()
    reset_waydroid_prop_btn: Gtk.Button = Gtk.Template.Child()

    timeout_id: dict[Any, Any] = dict()
    _task: Task = Task()

    # Removed complex signal management - no longer needed with new architecture!

    def __init__(self, waydroid: Waydroid, **kargs):
        super().__init__(**kargs)

        default_dir = os.path.join(
            "/usr/share", os.environ.get("PROJECT_NAME", "waydroid-helper")
        )
        data_dir = os.getenv("PKGDATADIR", default_dir)

        with open(os.path.join(data_dir, "data", "devices.json")) as f:
            self.items = json.load(f)

        self.set_property("waydroid", waydroid)
        self.waydroid.persist_props.connect(
            "notify::state", self.on_waydroid_persist_state_changed
        )
        self.waydroid.privileged_props.connect(
            "notify::state", self.on_waydroid_privileged_state_changed
        )
        self.waydroid.waydroid_props.connect(
            "notify::state", self.on_waydroid_waydroid_state_changed
        )
        self._sync_props = True
        # # self.waydroid.bind_property(
        # #     "state", self.switch_1, "sensitive", GObject.BindingFlags.SYNC_CREATE)

        # REMOVED: bind_property calls - new architecture handles this automatically
        # self.waydroid.persist_props.bind_property(
        #     self.switch_1.get_name(),
        #     self.switch_1,
        #     "active",
        #     GObject.BindingFlags.BIDIRECTIONAL,
        # )

        # self.waydroid.persist_props.bind_property(
        #     self.switch_2.get_name(),
        #     self.switch_2,
        #     "active",
        #     GObject.BindingFlags.BIDIRECTIONAL,
        # )
        # self.waydroid.persist_props.bind_property(
        #     self.switch_3.get_name(),
        #     self.switch_3,
        #     "active",
        #     GObject.BindingFlags.BIDIRECTIONAL,
        # )
        # self.waydroid.persist_props.bind_property(
        #     self.switch_4.get_name(),
        #     self.switch_4,
        #     "active",
        #     GObject.BindingFlags.BIDIRECTIONAL,
        # )
        # self.waydroid.persist_props.bind_property(
        #     self.switch_5.get_name(),
        #     self.switch_5,
        #     "active",
        #     GObject.BindingFlags.BIDIRECTIONAL,
        # )
        # self.waydroid.persist_props.bind_property(
        #     self.entry_1.get_name(),
        #     self.entry_1,
        #     "text",
        #     GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        # )
        # self.waydroid.persist_props.bind_property(
        #     self.entry_2.get_name(),
        #     self.entry_2,
        #     "text",
        #     GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        # )

        # self.waydroid.persist_props.bind_property(
        #     self.entry_3.get_name(),
        #     self.entry_3,
        #     "text",
        #     GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        # )

        # self.waydroid.persist_props.bind_property(
        #     self.entry_4.get_name(),
        #     self.entry_4,
        #     "text",
        #     GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        # )

        # self.waydroid.persist_props.bind_property(
        #     self.entry_5.get_name(),
        #     self.entry_5,
        #     "text",
        #     GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        # )
        # self.waydroid.persist_props.bind_property(
        #     self.entry_6.get_name(),
        #     self.entry_6,
        #     "text",
        #     GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        # )
        # self.waydroid.privileged_props.bind_property(
        #     self.switch_21.get_name(),
        #     self.switch_21,
        #     "active",
        #     GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        # )

        self.save_notification: InfoBar = InfoBar(
            label=_("Restart the session to apply the changes"),
            # cancel_callback=self.on_cancel_button_clicked,
            ok_callback=self.on_restart_button_clicked,
        )
        self.save_privileged_notification: InfoBar = InfoBar(
            label=_("Save and restart the container"),
            cancel_callback=self.on_restore_button_clicked,
            ok_callback=self.on_apply_button_clicked,
        )
        self.save_waydroid_notification: InfoBar = InfoBar(
            label=_("Save and restart Waydroid"),
            cancel_callback=self.on_restore_waydroid_button_clicked,
            ok_callback=self.on_apply_waydroid_button_clicked,
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
        self._model_changed: bool = False
        self._brand_changed: bool = False
        self.waydroid.privileged_props.connect(
            "notify::ro-product-model", self.__on_model_changed
        )
        self.waydroid.privileged_props.connect(
            "notify::ro-product-brand", self.__on_brand_changed
        )

        # Set up simple, permanent signal connections (no more dynamic connect/disconnect!)
        self._setup_permanent_signal_connections()

        # Set up manual property synchronization (replaces bind_property)
        self._setup_property_synchronization()

    def _setup_permanent_signal_connections(self):
        """Set up permanent signal connections - no more complex connect/disconnect logic!"""

        # Connect persist property controls - these stay connected permanently
        # The handlers will check if the state is ready before acting
        self.entry_1.connect("notify::text",
                           partial(self.on_persist_text_changed, name=self.entry_1.get_name()))
        self.entry_2.connect("notify::text",
                           partial(self.on_persist_text_changed, name=self.entry_2.get_name()))
        self.entry_3.connect("notify::text",
                           partial(self.on_persist_text_changed, name=self.entry_3.get_name(), flag=True))
        self.entry_4.connect("notify::text",
                           partial(self.on_persist_text_changed, name=self.entry_4.get_name(), flag=True))
        self.entry_5.connect("notify::text",
                           partial(self.on_persist_text_changed, name=self.entry_5.get_name(), flag=True))
        self.entry_6.connect("notify::text",
                           partial(self.on_persist_text_changed, name=self.entry_6.get_name(), flag=True))

        self.switch_1.connect("notify::active",
                            partial(self.on_perisit_switch_clicked, name=self.switch_1.get_name()))
        self.switch_2.connect("notify::active",
                            partial(self.on_perisit_switch_clicked, name=self.switch_2.get_name()))
        self.switch_3.connect("notify::active",
                            partial(self.on_perisit_switch_clicked, name=self.switch_3.get_name()))
        self.switch_4.connect("notify::active",
                            partial(self.on_perisit_switch_clicked, name=self.switch_4.get_name()))
        self.switch_5.connect("notify::active",
                            partial(self.on_perisit_switch_clicked, name=self.switch_5.get_name()))

        # Connect privileged property controls
        self.device_combo.connect("notify::selected-item", self.on_adw_combo_row_selected_item)
        self.switch_21.connect("notify::active",
                             partial(self.on_privileged_switch_clicked, name=self.switch_21.get_name()))

        # Connect waydroid config property controls
        self.waydroid_switch_1.connect("notify::active",
                                     partial(self.on_waydroid_switch_clicked, name=self.waydroid_switch_1.get_name()))
        self.waydroid_switch_2.connect("notify::active",
                                     partial(self.on_waydroid_switch_clicked, name=self.waydroid_switch_2.get_name()))
        self.waydroid_entry_1.connect("notify::text",
                                    partial(self.on_waydroid_text_changed, name=self.waydroid_entry_1.get_name()))

    def _setup_property_synchronization(self):
        """Set up manual property synchronization to replace bind_property"""
        # Listen for model changes and update UI accordingly
        self.waydroid._controller.property_model.add_change_listener(self._on_model_property_changed)

        # Set up initial UI state when properties are loaded
        # self.waydroid.persist_props.connect("notify::state", self._sync_persist_props_to_ui)
        # self.waydroid.privileged_props.connect("notify::state", self._sync_privileged_props_to_ui)
        # self.waydroid.waydroid_props.connect("notify::state", self._sync_waydroid_props_to_ui)

    def _on_model_property_changed(self, property_name: str, value: Any):
        """Handle property changes from the model and update UI"""
        # Map property names to UI widgets
        self._sync_props = True
        widget_map = {
            "multi_windows": self.switch_1,
            "cursor_on_subsurface": self.switch_2,
            "invert_colors": self.switch_3,
            "suspend": self.switch_4,
            "uevent": self.switch_5,
            "fake_touch": self.entry_1,
            "fake_wifi": self.entry_2,
            "height_padding": self.entry_3,
            "width_padding": self.entry_4,
            "width": self.entry_5,
            "height": self.entry_6,
            "qemu_hw_mainkeys": self.switch_21,
            # Waydroid config widgets
            "mount_overlays": self.waydroid_switch_1,
            "auto_adb": self.waydroid_switch_2,
            "images_path": self.waydroid_entry_1,
        }

        widget = widget_map.get(property_name)
        if widget:
            # Temporarily block signals to avoid circular updates
            if hasattr(widget, 'set_active'):  # Switch
                widget.set_active(bool(value))
            elif hasattr(widget, 'set_text'):  # Entry
                widget.set_text(str(value) if value else "")
        self._sync_props = False

# TODO 此处应该是model同步过来, 现在只会在状态切换到 ready时读取一次
    # def _sync_persist_props_to_ui(self, props_obj: GObject.Object, param: GObject.ParamSpec):
    #     """Sync persist properties to UI when they become ready"""
    #     if props_obj.get_property("state") == PropsState.READY:
    #         # Update all persist property UI elements
    #         self.switch_1.set_active(self.waydroid._controller.property_model.get_property_value("multi_windows") or False)
    #         self.switch_2.set_active(self.waydroid._controller.property_model.get_property_value("cursor_on_subsurface") or False)
    #         self.switch_3.set_active(self.waydroid._controller.property_model.get_property_value("invert_colors") or False)
    #         self.switch_4.set_active(self.waydroid._controller.property_model.get_property_value("suspend") or False)
    #         self.switch_5.set_active(self.waydroid._controller.property_model.get_property_value("uevent") or False)

    #         self.entry_1.set_text(str(self.waydroid._controller.property_model.get_property_value("fake_touch") or ""))
    #         self.entry_2.set_text(str(self.waydroid._controller.property_model.get_property_value("fake_wifi") or ""))
    #         self.entry_3.set_text(str(self.waydroid._controller.property_model.get_property_value("height_padding") or ""))
    #         self.entry_4.set_text(str(self.waydroid._controller.property_model.get_property_value("width_padding") or ""))
    #         self.entry_5.set_text(str(self.waydroid._controller.property_model.get_property_value("width") or ""))
    #         self.entry_6.set_text(str(self.waydroid._controller.property_model.get_property_value("height") or ""))

    # def _sync_privileged_props_to_ui(self, props_obj: GObject.Object, param: GObject.ParamSpec):
    #     """Sync privileged properties to UI when they become ready"""
    #     if props_obj.get_property("state") == PropsState.READY:
    #         # Update privileged property UI elements
    #         self.switch_21.set_active(self.waydroid._controller.property_model.get_property_value("qemu_hw_mainkeys") or False)

    # def _sync_waydroid_props_to_ui(self, props_obj: GObject.Object, param: GObject.ParamSpec):
    #     """Sync waydroid config properties to UI when they become ready"""
    #     if props_obj.get_property("state") == PropsState.READY:
    #         # Update waydroid config UI elements
    #         self.waydroid_switch_1.set_active(self.waydroid._controller.property_model.get_property_value("mount_overlays") or False)
    #         self.waydroid_switch_2.set_active(self.waydroid._controller.property_model.get_property_value("auto_adb") or False)
    #         self.waydroid_entry_1.set_text(str(self.waydroid._controller.property_model.get_property_value("images_path") or ""))

    def check_both_properties_changed(self):
        if self._model_changed and self._brand_changed:
            self._model_changed = False
            self._brand_changed = False
            self.on_device_info_changed()

    def __on_model_changed(self, obj: GObject.Object, param_spec: GObject.ParamSpec):
        self._model_changed = True
        self.check_both_properties_changed()

    def __on_brand_changed(self, obj: GObject.Object, param_spec: GObject.ParamSpec):
        self._brand_changed = True
        self.check_both_properties_changed()

    # waydroid prop to selected
    def on_device_info_changed(self):
        product_brand = self.waydroid.privileged_props.get_property("ro-product-brand")
        product_model = self.waydroid.privileged_props.get_property("ro-product-model")
        device = f"{product_brand} {product_model}"

        current = ""
        match self.device_combo.get_selected_item():
            case None:
                current = ""
            case Gtk.StringObject() as item:
                current = item.get_string()
            case _:
                current = ""

        if device == current:
            return
        if device in self.items["index"].keys():
            self.device_combo.set_selected(self.items["index"][device])
        else:
            self.device_combo.set_selected(0)

    def on_adw_combo_row_selected_item(
        self, comborow: Adw.ComboRow, GParamObject: GObject.ParamSpec
    ):
        """Handle combo box selection - now with simple state checking"""
        # Simple state check - no more complex connect/disconnect needed!
        if self.waydroid.privileged_props.get_property("state") != PropsState.READY and self._sync_props:
            return

        self.set_reveal(self.save_privileged_notification, True)
        match comborow.get_selected_item():
            case None:
                logger.info("No device selected")
                return
            case Gtk.StringObject() as selected_item:
                self.waydroid.privileged_props.set_device_info(
                    self.items["devices"][
                        self.items["index"][selected_item.get_string()]
                    ]["properties"]
                )
            case _:
                return

    # REMOVED: Complex __connect/__disconnect mechanism
    # The new architecture eliminates the need for manual signal management!

    def on_waydroid_privileged_state_changed(
        self, w: GObject.Object, param: GObject.ParamSpec
    ):
        """Simplified state handling - just enable/disable UI elements"""
        state = w.get_property("state")
        is_ready = state == PropsState.READY

        # Enable/disable all privileged property controls
        self.switch_21.set_sensitive(is_ready)
        self.device_combo.set_sensitive(is_ready)
        self.reset_privileged_prop_btn.set_sensitive(is_ready)

    def on_waydroid_waydroid_state_changed(
        self, w: GObject.Object, param: GObject.ParamSpec
    ):
        """Simplified state handling for waydroid config properties"""
        state = w.get_property("state")
        is_ready = state == PropsState.READY

        # Enable/disable waydroid config controls
        self.waydroid_switch_1.set_sensitive(is_ready)
        self.waydroid_switch_2.set_sensitive(is_ready)
        self.waydroid_entry_1.set_sensitive(is_ready)
        self.reset_waydroid_prop_btn.set_sensitive(is_ready)

    def on_waydroid_persist_state_changed(
        self, w: GObject.Object, param: GObject.ParamSpec
    ):
        """Simplified state handling - just enable/disable UI elements"""
        state = w.get_property("state")
        is_ready = state == PropsState.READY



        # Enable/disable all persist property controls
        controls = [
            self.switch_1, self.switch_2, self.switch_3, self.switch_4, self.switch_5,
            self.entry_1, self.entry_2, self.entry_3, self.entry_4, self.entry_5, self.entry_6,
            self.reset_persist_prop_btn
        ]

        for control in controls:
            control.set_sensitive(is_ready)

    def set_reveal(self, widget: InfoBar, reveal_child: bool):
        if (
            reveal_child == True
            and not self.save_notification.get_reveal_child()
            and not self.save_privileged_notification.get_reveal_child()
            and not self.save_waydroid_notification.get_reveal_child()
        ):
            if self.overlay:
                self.remove(self.overlay)
            self.overlay = Gtk.Overlay.new()
            self.append(self.overlay)
            if widget == self.save_notification:
                self.overlay.set_child(self.save_notification)
                self.overlay.add_overlay(self.save_privileged_notification)
                self.overlay.add_overlay(self.save_waydroid_notification)
            elif widget == self.save_privileged_notification:
                self.overlay.set_child(self.save_privileged_notification)
                self.overlay.add_overlay(self.save_notification)
                self.overlay.add_overlay(self.save_waydroid_notification)
            else:  # waydroid notification
                self.overlay.set_child(self.save_waydroid_notification)
                self.overlay.add_overlay(self.save_notification)
                self.overlay.add_overlay(self.save_privileged_notification)
        widget.set_reveal_child(reveal_child)

    def on_privileged_switch_clicked(
        self, a: Gtk.Widget, b: GObject.ParamSpec, name: str
    ):
        """Handle privileged switch clicks - now with simple state checking"""
        # Simple state check - no more complex connect/disconnect needed!
        if self.waydroid.privileged_props.get_property("state") != PropsState.READY and self._sync_props:
            return

        # Update the model with the new value
        normalized_name = name.replace("-", "_")
        new_value = a.get_active() if hasattr(a, 'get_active') else False

        # Update the model
        self.waydroid._controller.property_model.set_property_value(normalized_name, new_value)

        self.set_reveal(self.save_privileged_notification, True)

    def on_waydroid_switch_clicked(self, a: Gtk.Switch, b: GObject.ParamSpec, name: str):
        """Handle waydroid switch clicks - now with simple state checking"""
        # Simple state check - no more complex connect/disconnect needed!
        if self.waydroid.waydroid_props.get_property("state") != PropsState.READY and self._sync_props:
            return

        # Update the model with the new value
        normalized_name = name.replace("-", "_")
        new_value = a.get_active()

        # Update the model
        self.waydroid._controller.property_model.set_property_value(normalized_name, new_value)

        # Show notification for waydroid config changes
        self.set_reveal(self.save_waydroid_notification, True)

    def on_waydroid_text_changed(self, a: Gtk.Entry, b: GObject.ParamSpec, name: str):
        """Handle waydroid text changes - now with simple state checking"""
        # Simple state check - no more complex connect/disconnect needed!
        if self.waydroid.waydroid_props.get_property("state") != PropsState.READY and self._sync_props:
            return

        # Update the model with the new value
        normalized_name = name.replace("-", "_")
        new_value = a.get_text()

        # Update the model
        self.waydroid._controller.property_model.set_property_value(normalized_name, new_value)

        # Show notification for waydroid config changes
        self.set_reveal(self.save_waydroid_notification, True)

    def __on_persist_text_changed(self, name: str):
        # Update the model with the new value before saving
        normalized_name = name.replace("-", "_")

        # Find the corresponding entry widget to get the current value
        widget_map = {
            "fake-touch": self.entry_1,
            "fake-wifi": self.entry_2,
            "height-padding": self.entry_3,
            "width-padding": self.entry_4,
            "width": self.entry_5,
            "height": self.entry_6,
        }

        widget = widget_map.get(name)
        if widget:
            new_value = widget.get_text()

            # Update the model
            self.waydroid._controller.property_model.set_property_value(normalized_name, new_value)

        self._task.create_task(self.waydroid.save_persist_prop(name))
        self.timeout_id[name] = None

    def on_persist_text_changed(
        self, a: Gtk.Widget, b: GObject.ParamSpec, name: str, flag: bool = False
    ):
        """Handle persist text changes - now with simple state checking"""
        # Simple state check - no more complex connect/disconnect needed!
        if self.waydroid.persist_props.get_property("state") != PropsState.READY and self._sync_props:
            return

        if self.timeout_id.get(name) is not None:
            GLib.source_remove(self.timeout_id[name])

        self.timeout_id[name] = GLib.timeout_add(
            1000, partial(self.__on_persist_text_changed, name)
        )
        if flag:
            self.set_reveal(self.save_notification, True)

    def on_perisit_switch_clicked(self, a: Gtk.Switch, b: GObject.ParamSpec, name: str):
        """Handle persist switch clicks - now with simple state checking"""
        # Simple state check - no more complex connect/disconnect needed!
        if self.waydroid.persist_props.get_property("state") != PropsState.READY and self._sync_props:
            return

        # Update the model with the new value
        normalized_name = name.replace("-", "_")
        new_value = a.get_active()

        # Update the model
        self.waydroid._controller.property_model.set_property_value(normalized_name, new_value)

        self.set_reveal(self.save_notification, True)
        self._task.create_task(self.waydroid.save_persist_prop(name))

    # def on_cancel_button_clicked(self, button):
    #     self.set_reveal(self.save_notification, False)
    # self.save_notification.set_reveal_child(False)

    def on_restart_button_clicked(self, button: Gtk.Button):
        # self.set_reveal(self.save_notification, False)
        # self.save_notification.set_reveal_child(False)
        self._task.create_task(self.waydroid.restart_session())

    def on_restore_button_clicked(self, button: Gtk.Button):
        # self.set_reveal(self.save_privileged_notification, False)
        # self.save_privileged_notification.set_reveal_child(False)
        self._task.create_task(self.waydroid.restore_privileged_props())

    def on_apply_button_clicked(self, button: Gtk.Button):
        # self.set_reveal(self.save_privileged_notification, False)
        # self.save_privileged_notification.set_reveal_child(False)
        self._task.create_task(self.waydroid.save_privileged_props())

    def on_restore_waydroid_button_clicked(self, button: Gtk.Button):
        # Restore waydroid config properties from file
        self._task.create_task(self.waydroid._controller.reset_waydroid_properties())

    def on_apply_waydroid_button_clicked(self, button: Gtk.Button):
        # Save waydroid config properties
        self._task.create_task(self.waydroid.save_waydroid_props())

    @Gtk.Template.Callback()
    def on_reset_persist_clicked(self, button: Gtk.Button):
        self._task.create_task(self.waydroid.reset_persist_props())

    @Gtk.Template.Callback()
    def on_reset_privileged_clicked(self, button: Gtk.Button):
        self._task.create_task(self.waydroid.reset_privileged_props())

    @Gtk.Template.Callback()
    def on_reset_waydroid_clicked(self, button: Gtk.Button):
        self._task.create_task(self.waydroid.reset_waydroid_props())

    # @Gtk.Template.Callback()
    # def on_switch_clicked(self, a:Gtk.Switch, b=None, c=None, d=None):
    #     # print(a.get_widget().get_name())
    #     print("callback")
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
