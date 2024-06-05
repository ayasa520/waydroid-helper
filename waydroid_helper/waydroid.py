import configparser
import enum
import appdirs
import os
import threading
from gettext import gettext as _
from gi.repository import GObject, GLib
from typing import Optional
from functools import partial
from waydroid_helper.util.ProcessLauncher import ProcessLauncher

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

CONFIG_DIR = os.environ.get("WAYDROID_CONFIG", "/var/lib/waydroid/waydroid.cfg")


class WaydroidState(enum.IntEnum):
    LOADING = 1
    UNINITIALIZED = 2
    STOPPED = 4
    RUNNING = 8


def bool_to_str(b, flag=0) -> str:
    if flag == 0:
        if b:
            return "True"
        else:
            return "False"
    elif flag == 1:
        if b:
            return "true"
        else:
            return "false"
    elif flag == 2:
        if b:
            return "1"
        else:
            return "0"


def str_to_bool(s: str) -> bool:
    s = s.strip()
    if s == "true" or s == "1" or s == "True":
        return True
    else:
        return False


class PropsState(enum.IntEnum):
    UNINITIALIZED = 1
    READY = 2


class Waydroid(GObject.Object):
    state: GObject.Property = GObject.Property(type=object)

    class PersistProps(GObject.Object):
        state: GObject.Property = GObject.Property(type=object)
        transform = {
            "multi-windows": [str_to_bool, partial(bool_to_str, flag=1)],
            "cursor-on-subsurface": [str_to_bool, partial(bool_to_str, flag=1)],
            "invert-colors": [str_to_bool, partial(bool_to_str, flag=1)],
            "suspend": [str_to_bool, partial(bool_to_str, flag=1)],
            "uevent": [str_to_bool, partial(bool_to_str, flag=1)],
            "fake-touch": [lambda x: x, lambda x: x],
            "fake-wifi": [lambda x: x, lambda x: x],
            "height-padding": [lambda x: x, lambda x: x],
            "width-padding": [lambda x: x, lambda x: x],
            "height": [lambda x: x, lambda x: x],
            "width": [lambda x: x, lambda x: x],
        }
        ready_state_list = dict()
        multi_windows: GObject.Property = GObject.Property(
            default=False,
            type=bool,
            nick="persist.waydroid.multi_windows",
            blurb=_("Enable window integration with the desktop"),
        )
        cursor_on_subsurface: GObject.Property = GObject.Property(
            default=False,
            type=bool,
            nick="persist.waydroid.cursor_on_subsurface",
            blurb=_(
                "Workaround for showing the cursor inmulti_windows mode on some compositors"
            ),
        )
        invert_colors: GObject.Property = GObject.Property(
            default=False,
            type=bool,
            nick="persist.waydroid.invert_colors",
            blurb=_(
                "Swaps the color space from RGBA to BGRA (only works with our patched mutter so far)"
            ),
        )
        suspend: GObject.Property = GObject.Property(
            default=False,
            type=bool,
            nick="persist.waydroid.suspend",
            blurb=_(
                "Let the Waydroid container sleep (after the display timeout) when no apps are active"
            ),
        )
        uevent: GObject.Property = GObject.Property(
            default=False,
            type=bool,
            nick="persist.waydroid.uevent",
            blurb=_("Allow android direct access to hotplugged devices"),
        )
        fake_touch: GObject.Property = GObject.Property(
            default="",
            type=str,
            nick="persist.waydroid.fake_touch",
            blurb=_(
                "Interpret mouse inputs as touch inputs. Enter the package names separated by ','. Use the wildcard '*' to match all Apps"
            ),
        )
        fake_wifi: GObject.Property = GObject.Property(
            default="",
            type=str,
            nick="persist.waydroid.fake_wifi",
            blurb=_(
                "Make the Apps appear as if connected to WiFi. Enter the package names separated by ','. Use the wildcard '*' to match all Apps"
            ),
        )
        height_padding: GObject.Property = GObject.Property(
            default="",
            type=str,
            nick="persist.waydroid.height_padding",
            blurb=_("Adjust height padding"),
        )
        width_padding: GObject.Property = GObject.Property(
            default="",
            type=str,
            nick="persist.waydroid.width_padding",
            blurb=_("Adjust width padding"),
        )
        width: GObject.Property = GObject.Property(
            default="",
            type=str,
            nick="persist.waydroid.width",
            blurb=_("Used for user to override desired resolution"),
        )

        height: GObject.Property = GObject.Property(
            default="",
            type=str,
            nick="persist.waydroid.height",
            blurb=_("Used for user to override desired resolution"),
        )

        def _list_properties(self):
            return [prop for prop in self.list_properties() if prop.name != "state"]

        def fetch(self):
            def get_persist_prop(name: str, output: str):
                output = output.split("\n")[-1]
                if "Failed to get service waydroidplatform, trying again..." in output:
                    output = ""

                value = self.transform[name][0](output)

                self.set_property(name, value)
                self.set_ready_state(name, True)
                if self.ready():
                    self.state = PropsState.READY

            self.state = PropsState.UNINITIALIZED
            for prop in self._list_properties():
                p = ProcessLauncher(
                    ["waydroid", "prop", "get", prop.nick],
                    partial(
                        get_persist_prop,
                        prop.name,
                    ),
                )

        def save(self, name):
            key = self.find_property(name).nick
            value = self.transform[name][1](self.get_property(name))
            ProcessLauncher(["waydroid", "prop", "set", key, value])

        def reset_state(self):
            self.state = PropsState.UNINITIALIZED

        def set_ready_state(self, name, state: bool):
            self.ready_state_list[name] = state

        def get_ready_state(self, name):
            return self.ready_state_list.get(name)

        def ready(self):
            for prop in self._list_properties():
                if self.get_ready_state(prop.name) == True:
                    continue
                else:
                    return False
            return True

        def reset_ready_list(self):
            for prop in self._list_properties():
                self.set_ready_state(prop.name, False)

        def __init__(self) -> None:
            super().__init__()
            self.reset_ready_list()
            self.state = PropsState.UNINITIALIZED

    class PrivilegedProps(GObject.Object):
        state: GObject.Property = GObject.Property(type=object)

        transform = {
            "qemu-hw-mainkeys": [
                lambda x: True if x != "" else False,
                lambda x: "1" if x else "0",
            ]
        }
        qemu_hw_mainkeys: GObject.Property = GObject.Property(
            default=0, type=bool, nick="qemu.hw.mainkeys", blurb=_("hide navbar")
        )
        cfg = configparser.ConfigParser()

        def __init__(self) -> None:
            super().__init__()
            self.state = PropsState.UNINITIALIZED
            self.cfg.read(CONFIG_DIR)

        def _list_properties(self):
            return [prop for prop in self.list_properties() if prop.name != "state"]

        def reset_state(self):
            self.state = PropsState.UNINITIALIZED

        def fetch(self):
            self.state = PropsState.UNINITIALIZED
            for each in self._list_properties():
                value = self.cfg.get("properties", each.nick, fallback="")
                self.set_property(each.name, self.transform[each.name][0](value))
            self.state = PropsState.READY

        def restore(self):
            self.fetch()

        def save(self):
            for each in self._list_properties():
                value = self.get_property(each.name)
                self.cfg.set(
                    "properties", each.nick, self.transform[each.name][1](value)
                )

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
                        ],
                        handler=lambda x: self.restore() if int(x) == 126 else None,
                    )

            cache_path = os.path.join(appdirs.user_cache_dir(), "waydroid_helper")
            cache_config_dir = os.path.join(cache_path, "waydroid.cfg")

            thread = threading.Thread(target=save_cache)
            thread.daemon = True
            thread.start()

    persist_props: PersistProps = PersistProps()
    privileged_props: PrivilegedProps = PrivilegedProps()

    # def on_persist_prop_changed(self, w, param):
    #     if isinstance(param.default_value, str):
    #         value = self.persist_props.get_property(param.name) or "''"
    #     elif isinstance(param.default_value, bool):
    #         if self.persist_props.get_property(param.name):
    #             value = "true"
    #         else:
    #             value = "false"
    #     print("触发了!")
    #     ProcessLauncher(["waydroid", "prop", "set", param.nick, value])
    def init_persist_props(self):
        self.persist_props.fetch()

    def init_privileged_props(self):
        self.privileged_props.fetch()

    def reset_persist_props(self):
        self.persist_props.reset_ready_list()
        self.persist_props.reset_state()

    def reset_privileged_props(self):
        self.privileged_props.reset_state()

    def save_privileged_props(self):
        # 感觉保存与 upgrade 分开写更正确, 但是按照目前的写法那样需要输入两次密码
        self.privileged_props.save()

    def restore_privileged_props(self):
        self.privileged_props.restore()

    # 因为双向绑定了, 所以不需要传入值
    def set_persist_prop(self, name):
        self.persist_props.save(name)

    def update_waydroid_status(self):
        def callback(output):
            if self.state == WaydroidState.UNINITIALIZED:
                if "Session:\tRUNNING" in output:
                    self.init_persist_props()
                    self.init_privileged_props()
                    self.set_property("state", WaydroidState.RUNNING)
                elif "Session:\tSTOPPED" in output:
                    self.init_privileged_props()
                    self.set_property("state", WaydroidState.STOPPED)
            elif self.state == WaydroidState.STOPPED:
                if "Session:\tRUNNING" in output:
                    self.init_persist_props()
                    self.set_property("state", WaydroidState.RUNNING)
                elif "WayDroid is not initialized" in output:
                    self.set_property("state", WaydroidState.UNINITIALIZED)
            elif self.state == WaydroidState.RUNNING:
                if "Session:\tSTOPPED" in output:
                    self.reset_persist_props()
                    self.set_property("state", WaydroidState.STOPPED)
                elif "WayDroid is not initialized" in output:
                    self.reset_persist_props()
                    self.reset_privileged_props()
                    self.set_property("state", WaydroidState.UNINITIALIZED)
            elif self.state == WaydroidState.LOADING:
                if "Session:\tSTOPPED" in output:
                    self.init_privileged_props()
                    self.set_property("state", WaydroidState.STOPPED)
                elif "WayDroid is not initialized" in output:
                    self.set_property("state", WaydroidState.UNINITIALIZED)
                if "Session:\tRUNNING" in output:
                    self.init_privileged_props()
                    self.init_persist_props()
                    self.set_property("state", WaydroidState.RUNNING)
            return False

        p = ProcessLauncher(["waydroid", "status"], callback=callback)

        return True

    def __init__(self) -> None:
        super().__init__()
        self.set_property("state", WaydroidState.LOADING)
        # 立即执行一次, 随后再每两秒一次
        self.update_waydroid_status()
        GLib.timeout_add_seconds(2, self.update_waydroid_status)

    def start_session(self):
        ProcessLauncher(["waydroid", "session", "start"], flag=True)

    def stop_session(self):
        ProcessLauncher(["waydroid", "session", "stop"])

    def restart_session(self):
        ProcessLauncher(
            ["sh", "-c", "waydroid session stop && waydroid session start"], flag=True
        )

    def show_full_ui(self):
        ProcessLauncher(["waydroid", "show-full-ui"])

    def upgrade(self, offline: Optional[bool] = None):
        if offline:
            self.save_privileged_props()
        else:
            ProcessLauncher(["pkexec", "waydroid", "upgrade"])
