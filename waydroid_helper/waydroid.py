from gi.repository import GObject, GLib
from typing import Any, Callable, Optional
from functools import partial
from waydroid_helper.util.ProcessLauncher import ProcessLauncher

# TODO: 移除结束的 subprocess
subprocesses: list[ProcessLauncher] = []


class Waydroid(GObject.Object):
    state: GObject.Property = GObject.Property(default=False, type=bool)
    multi_windows:  GObject.Property = GObject.Property(
        default=False, type=bool)
    cursor_on_subsurface: GObject.Property = GObject.Property(
        default=False, type=bool)
    invert_colors: GObject.Property = GObject.Property(
        default=False, type=bool)
    suspend: GObject.Property = GObject.Property(default=False, type=bool)
    uevent: GObject.Property = GObject.Property(default=False, type=bool)

    def update_waydroid_status(self):
        def callback(output):
            running = "Session:\tRUNNING" in output
            if running != self.get_property("state"):
                if running:
                    self.init_props()
                self.set_property("state", running)

        p = ProcessLauncher("waydroid status", callback=callback)
        subprocesses.append(p)
        return True

    def init_props(self):
        def get_prop(key: str, output: str):
            print("在这里", key, output)
            output=output.split("\n")[-1]
            value = False
            if "1" in output or "True" in output or "true" in output:
                value = True
            self.set_property(key, value)
            print(f"set {key} 了",self.get_property(key))

        subprocesses.append(ProcessLauncher(
            "waydroid prop get persist.waydroid.multi_windows", partial(get_prop, "multi_windows")))
        subprocesses.append(ProcessLauncher(
            "waydroid prop get persist.waydroid.cursor_on_subsurface", partial(get_prop, "cursor_on_subsurface")))
        subprocesses.append(ProcessLauncher(
            "waydroid prop get persist.waydroid.invert_colors", partial(get_prop, "invert_colors")))
        subprocesses.append(ProcessLauncher(
            "waydroid prop get persist.waydroid.suspend", partial(get_prop, "suspend")))
        subprocesses.append(ProcessLauncher(
            "waydroid prop get persist.waydroid.uevent", partial(get_prop, "uevent")))

    def __init__(self) -> None:
        super().__init__()
        GLib.timeout_add_seconds(2, self.update_waydroid_status)

    def start_session(self):
        subprocesses.append(ProcessLauncher("waydroid session start"))
        # subprocess.run("waydroid session start &", shell=True)

    def stop_session(self):
        subprocesses.append(ProcessLauncher("waydroid session stop"))
        # subprocess.run("waydroid session stop &", shell=True)

    def set_prop(self, key:str, value:bool):
        if value:
            value="true"
        else:
            value="false"
        subprocesses.append(ProcessLauncher(
            f"waydroid prop set {key} {value}"))

    def get_prop(self, key):
        subprocesses.append(ProcessLauncher(f"waydroid prop set {key}"))

    def show_full_ui(self):
        subprocesses.append(ProcessLauncher(f"waydroid show-full-ui"))

    def upgrade(self, offline: Optional[bool] = None):
        flag = '-o' if offline else ''
        subprocesses.append(ProcessLauncher(f"pkexec waydroid upgrade {flag}"))
