import configparser
import appdirs
import os
import threading
from gi.repository import GObject, GLib, Gtk
from typing import Optional
from functools import partial
from waydroid_helper.util.ProcessLauncher import ProcessLauncher

CONFIG_DIR = os.environ.get(
    "WAYDROID_CONFIG", "/var/lib/waydroid/waydroid.cfg")


class Waydroid(GObject.Object):

    subprocesses: list[ProcessLauncher] = []
    state: GObject.Property = GObject.Property(default=False, type=bool)

    class PersistProps(GObject.Object):
        multi_windows:  GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.multi_windows")
        cursor_on_subsurface: GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.cursor_on_subsurface")
        invert_colors: GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.invert_colors")
        suspend: GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.suspend")
        uevent: GObject.Property = GObject.Property(
            default=False, type=bool, nick="persist.waydroid.uevent")
        fake_touch: GObject.Property = GObject.Property(
            default="", type=str, nick="persist.waydroid.fake_touch")
        fake_wifi: GObject.Property = GObject.Property(
            default="", type=str, nick="persist.waydroid.fake_wifi")

    class PrivilegedProps(GObject.Object):
        qemu_hw_mainkeys: GObject.Property = GObject.Property(
            default=0, type=int, nick="qemu.hw.mainkeys")

    persist_props: PersistProps = PersistProps()
    privileged_props: PrivilegedProps = PrivilegedProps()

    signals = dict()

    def on_persist_prop_changed(self, w, param):
        if isinstance(param.default_value, str):
            value = self.persist_props.get_property(param.name) or "\'\'"
        elif isinstance(param.default_value, bool):
            if self.persist_props.get_property(param.name):
                value = "true"
            else:
                value = "false"
        self.subprocesses.append(ProcessLauncher(
            f"waydroid prop set {param.nick} {value}"))

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
            self.subprocesses.append(
                ProcessLauncher(
                    f"pkexec sh -c 'cp -r {cache_config_dir} {CONFIG_DIR} && waydroid upgrade -o'"
                )
            )

        cache_path = os.path.join(appdirs.user_cache_dir(), "waydroid_helper")
        cache_config_dir = os.path.join(cache_path, "waydroid.cfg")

        thread = threading.Thread(target=save_cache)
        thread.daemon = True
        thread.start()


    def update_waydroid_status(self):
        def callback(output):
            running = "Session:\tRUNNING" in output
            if running != self.get_property("state"):
                if running:
                    self.init_persist_props()
                else:
                    self.disconnect_persist_props()
                self.set_property("state", running)

        p = ProcessLauncher("waydroid status", callback=callback)
        self.subprocesses.append(p)

        self.subprocesses = [each for each in self.subprocesses if each.alive]

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
            # 重复
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
                f"notify::{name}",
                self.on_persist_prop_changed
            )
            self.signals[name] = id

        
        for prop in self.persist_props.list_properties():
            p = ProcessLauncher(
                f"waydroid prop get {prop.nick}",
                partial(get_persist_prop, prop.name)
            )
            self.subprocesses.append(p)

    def __init__(self) -> None:
        super().__init__()
        GLib.timeout_add_seconds(2, self.update_waydroid_status)
        self.cfg = configparser.ConfigParser()
        self.cfg.read(CONFIG_DIR)
        self.init_privileged_props()

    def start_session(self):
        self.subprocesses.append(ProcessLauncher("waydroid session start"))

    def stop_session(self):
        self.subprocesses.append(ProcessLauncher("waydroid session stop"))

    def show_full_ui(self):
        self.subprocesses.append(ProcessLauncher(f"waydroid show-full-ui"))

    def upgrade(self, offline: Optional[bool] = None):
        flag = '-o' if offline else ''
        self.subprocesses.append(ProcessLauncher(
            f"pkexec waydroid upgrade {flag}"))
