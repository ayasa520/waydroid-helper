import configparser
import enum
import appdirs
import os
import threading
from gi.repository import GObject, GLib
from typing import Optional
from functools import partial
from waydroid_helper.util.ProcessLauncher import ProcessLauncher

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

CONFIG_DIR = os.environ.get("WAYDROID_CONFIG", "/var/lib/waydroid/waydroid.cfg")


class WaydroidState(enum.IntEnum):
    UNINITIALIZED = 0
    STOPPED = 1
    RUNNING = 2
    LOADING = 3


class Waydroid(GObject.Object):
    state: GObject.Property = GObject.Property(type=object)

    class PersistProps(GObject.Object):
        multi_windows: GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.multi_windows"
        )
        cursor_on_subsurface: GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.cursor_on_subsurface"
        )
        invert_colors: GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.invert_colors"
        )
        suspend: GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.suspend"
        )
        uevent: GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.uevent"
        )
        fake_touch: GObject.Property = GObject.Property(
            default="", type=str, nick="persist.waydroid.fake_touch"
        )
        fake_wifi: GObject.Property = GObject.Property(
            default="", type=str, nick="persist.waydroid.fake_wifi"
        )

    class PrivilegedProps(GObject.Object):
        qemu_hw_mainkeys: GObject.Property = GObject.Property(
            default=0, type=int, nick="qemu.hw.mainkeys"
        )

    persist_props: PersistProps = PersistProps()
    privileged_props: PrivilegedProps = PrivilegedProps()

    signals = dict()

    def on_persist_prop_changed(self, w, param):
        if isinstance(param.default_value, str):
            value = self.persist_props.get_property(param.name) or "''"
        elif isinstance(param.default_value, bool):
            if self.persist_props.get_property(param.name):
                value = "true"
            else:
                value = "false"
        ProcessLauncher(["waydroid", "prop", "set", param.nick, value])

    def init_privileged_props(self):
        for each in self.privileged_props.list_properties():
            value = self.cfg.get("properties", each.nick, fallback="")
            if isinstance(each.default_value, bool):
                if "1" in value or "True" in value or "true" in value:
                    value = True
                else:
                    value = False
            elif isinstance(each.default_value, int):
                value = 0 if not value else int(value)
            self.privileged_props.set_property(each.name, value)

    def save_privileged_props(self):
        for each in self.privileged_props.list_properties():
            value = self.privileged_props.get_property(each.name)
            if isinstance(value, bool):
                value = "true" if value else "false"
            self.cfg.set("properties", each.nick, str(value))

        def save_cache():
            os.makedirs(cache_path, exist_ok=True)
            with open(cache_config_dir, "w") as f:
                self.cfg.write(f)
                ProcessLauncher(
                    [
                        "pkexec",
                        "sh",
                        "-c",
                        f"cp -r {cache_config_dir} {CONFIG_DIR} && waydroid upgrade -o",
                    ]
                )

        cache_path = os.path.join(appdirs.user_cache_dir(), "waydroid_helper")
        cache_config_dir = os.path.join(cache_path, "waydroid.cfg")

        thread = threading.Thread(target=save_cache)
        thread.daemon = True
        thread.start()

    def update_waydroid_status(self):
        def callback(output):
            if self.state == WaydroidState.UNINITIALIZED:
                if "Session:\tRUNNING" in output:
                    self.init_persist_props()
                    self.set_property("state", WaydroidState.RUNNING)
                elif "Session:\tSTOPPED" in output:
                    self.set_property("state", WaydroidState.STOPPED)
            elif self.state == WaydroidState.STOPPED:
                if "Session:\tRUNNING" in output:
                    self.init_persist_props()
                    self.set_property("state", WaydroidState.RUNNING)
                elif "WayDroid is not initialized" in output:
                    self.set_property("state", WaydroidState.UNINITIALIZED)
            elif self.state == WaydroidState.RUNNING:
                if "Session:\tSTOPPED" in output:
                    self.disconnect_persist_props()
                    self.set_property("state", WaydroidState.STOPPED)
                elif "WayDroid is not initialized" in output:
                    self.disconnect_persist_props()
                    self.set_property("state", WaydroidState.UNINITIALIZED)
            elif self.state == WaydroidState.LOADING:
                if "Session:\tSTOPPED" in output:
                    self.disconnect_persist_props()
                    self.set_property("state", WaydroidState.STOPPED)
                elif "WayDroid is not initialized" in output:
                    self.disconnect_persist_props()
                    self.set_property("state", WaydroidState.UNINITIALIZED)
                elif "Session:\tRUNNING" in output:
                    self.init_persist_props()
                    self.set_property("state", WaydroidState.RUNNING)

        p = ProcessLauncher(["waydroid", "status"], callback=callback)

        return True

    def disconnect_persist_props(self):
        for each in self.persist_props.list_properties():
            if each.name in self.signals.keys():
                self.persist_props.disconnect(self.signals[each.name])
                self.signals.pop(each.name)

    def init_persist_props(self):
        def get_persist_prop(name: str, output: str):
            output = output.split("\n")[-1]
            if "Failed to get service waydroidplatform, trying again..." in output:
                output = ""
            if isinstance(self.persist_props.get_property(name), str):
                value = output
            elif isinstance(self.persist_props.get_property(name), bool):
                if "1" in output or "True" in output or "true" in output:
                    value = True
                else:
                    value = False
            # print(name, output, type(self.persist_props.get_property(name)))
            self.persist_props.set_property(name, value)
            id = self.persist_props.connect(
                f"notify::{name}", self.on_persist_prop_changed
            )
            self.signals[name] = id

        for prop in self.persist_props.list_properties():
            p = ProcessLauncher(
                ["waydroid", "prop", "get", prop.nick],
                partial(get_persist_prop, prop.name),
            )

    def __init__(self) -> None:
        super().__init__()
        self.set_property("state", WaydroidState.LOADING)
        GLib.timeout_add_seconds(2, self.update_waydroid_status)
        self.cfg = configparser.ConfigParser()
        self.cfg.read(CONFIG_DIR)
        self.init_privileged_props()

    def start_session(self):
        ProcessLauncher(["waydroid", "session", "start"])

    def stop_session(self):
        ProcessLauncher(["waydroid", "session", "stop"])

    def show_full_ui(self):
        ProcessLauncher(["waydroid", "show-full-ui"])

    def upgrade(self, offline: Optional[bool] = None):
        if offline:
            self.save_privileged_props()
        else:
            ProcessLauncher(["pkexec", "waydroid", "upgrade"])
