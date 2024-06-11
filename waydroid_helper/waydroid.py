import configparser
import copy
import enum
import appdirs
import os
from gettext import gettext as _
from gi.repository import GObject, GLib
import asyncio
from typing import Optional
from functools import partial
from waydroid_helper.util.SubprocessManager import SubprocessManager

import gi

from waydroid_helper.util.Task import Task

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

    _subprocess = SubprocessManager()
    _task = Task()

    class PersistProps(GObject.Object):
        state: GObject.Property = GObject.Property(type=object)

        _subprocess = SubprocessManager()
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

        async def fetch(self):
            def get_persist_prop(name: str, result: str):
                output = result.strip().split("\n")[-1]
                if "Failed to get service waydroidplatform, trying again..." in output:
                    output = ""

                value = self.transform[name][0](output)

                self.set_property(name, value)

            self.state = PropsState.UNINITIALIZED
            tasks = set()
            for prop in self._list_properties():
                coro = self._subprocess._run_subprocess(
                    f"waydroid prop get {prop.nick}", key=prop.name
                )
                tasks.add(coro)

            results = await asyncio.gather(*tasks)
            for each in results:
                get_persist_prop(each["key"], each["stdout"])
            self.state = PropsState.READY

        async def save(self, name):
            key = self.find_property(name).nick
            value = self.transform[name][1](self.get_property(name))
            await self._subprocess._run_subprocess(f'waydroid prop set {key} "{value}"')

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

        # def reset_ready_list(self):
        #     for prop in self._list_properties():
        #         self.set_ready_state(prop.name, False)

        def __init__(self) -> None:
            super().__init__()
            # self.reset_ready_list()
            self.state = PropsState.UNINITIALIZED

    class PrivilegedProps(GObject.Object):
        state: GObject.Property = GObject.Property(type=object)
        _subprocess = SubprocessManager()

        transform = {
            "qemu-hw-mainkeys": [
                lambda x: True if x != "" else False,
                lambda x: "1" if x else "0",
            ],
            "ro-build-id": [lambda x: x, lambda x: x],
            "ro-build-display-id": [lambda x: x, lambda x: x],
            "ro-product-name": [lambda x: x, lambda x: x],
            "ro-product-device": [lambda x: x, lambda x: x],
            "ro-product-board": [lambda x: x, lambda x: x],
            "ro-system-build-product": [lambda x: x, lambda x: x],
            "ro-system-build-flavor": [lambda x: x, lambda x: x],
            "ro-product-manufacturer": [lambda x: x, lambda x: x],
            "ro-product-brand": [lambda x: x, lambda x: x],
            "ro-product-model": [lambda x: x, lambda x: x],
            "ro-boot-bootloader": [lambda x: x, lambda x: x],
            "ro-bootloader": [lambda x: x, lambda x: x],
            "ro-build-description": [lambda x: x, lambda x: x],
            "ro-bootimage-build-fingerprint": [lambda x: x, lambda x: x],
            "ro-build-tags": [lambda x: x, lambda x: x],
            "ro-build-type": [lambda x: x, lambda x: x],
            "ro-build-fingerprint": [lambda x: x, lambda x: x],
            "ro-vendor-build-fingerprint": [lambda x: x, lambda x: x],
        }
        qemu_hw_mainkeys: GObject.Property = GObject.Property(
            default=0, type=bool, nick="qemu.hw.mainkeys", blurb=_("hide navbar")
        )

        ro_build_id = GObject.Property(type=str, default="", nick="ro.build.id")
        ro_build_display_id = GObject.Property(
            type=str, default="", nick="ro.build.display.id"
        )
        ro_product_name = GObject.Property(type=str, default="", nick="ro.product.name")
        ro_product_device = GObject.Property(
            type=str, default="", nick="ro.product.device"
        )
        ro_product_board = GObject.Property(
            type=str, default="", nick="ro.product.board"
        )
        ro_system_build_product = GObject.Property(
            type=str, default="", nick="ro.system.build.product"
        )
        ro_system_build_flavor = GObject.Property(
            type=str, default="", nick="ro.system.build.flavor"
        )
        ro_product_manufacturer = GObject.Property(
            type=str, default="", nick="ro.product.manufacturer"
        )
        ro_product_brand = GObject.Property(
            type=str, default="", nick="ro.product,brand"
        )
        ro_product_model = GObject.Property(
            type=str, default="", nick="ro.product.model"
        )
        ro_boot_bootloader = GObject.Property(
            type=str, default="", nick="ro.boot.bootloader"
        )
        ro_bootloader = GObject.Property(type=str, default="", nick="ro.bootloader")
        ro_build_description = GObject.Property(
            type=str, default="", nick="ro.build.description"
        )
        ro_bootimage_build_fingerprint = GObject.Property(
            type=str, default="", nick="ro.bootimage.build.fingerprint"
        )
        ro_build_tags = GObject.Property(type=str, default="", nick="ro.build.tags")
        ro_build_type = GObject.Property(type=str, default="", nick="ro.build.type")
        ro_build_fingerprint = GObject.Property(
            type=str, default="", nick="ro.build.fingerprint"
        )
        ro_vendor_build_fingerprint = GObject.Property(
            type=str, default="", nick="ro.vendor.build.fingerprint"
        )

        cfg: configparser.ConfigParser = configparser.ConfigParser()
        old: configparser.ConfigParser = None

        def __init__(self) -> None:
            super().__init__()
            self.state = PropsState.UNINITIALIZED
            self.cfg.read(CONFIG_DIR)
            self.old = copy.deepcopy(self.cfg)

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
            self.cfg = self.old
            self.fetch()

        async def save(self):
            self.old = copy.deepcopy(self.cfg)
            for each in self._list_properties():
                value = self.get_property(each.name)
                if not value:
                    self.cfg.remove_option("properties", each.nick)
                else:
                    self.cfg.set(
                        "properties", each.nick, self.transform[each.name][1](value)
                    )

            # def save_cache():
            cache_path = os.path.join(appdirs.user_cache_dir(), "waydroid_helper")
            cache_config_dir = os.path.join(cache_path, "waydroid.cfg")

            os.makedirs(cache_path, exist_ok=True)
            with open(cache_config_dir, "w") as f:
                self.cfg.write(f)
            cmd = f"pkexec sh -c \"cp -r '{cache_config_dir}' '{CONFIG_DIR}' && waydroid upgrade -o\""
            result = await self._subprocess._run_subprocess(
                cmd,
                flag=True,
            )
            return result

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

    async def init_persist_props(self):
        await self.persist_props.fetch()

    def init_privileged_props(self):
        self.privileged_props.fetch()

    def reset_persist_props(self):
        # self.persist_props.reset_ready_list()
        self.persist_props.reset_state()

    def reset_privileged_props(self):
        self.privileged_props.reset_state()

    async def save_privileged_props(self):
        # 感觉保存与 upgrade 分开写更正确, 但是按照目前的写法那样需要输入两次密码
        await self.stop_session()
        print("已经关闭session")
        # await self.update_waydroid_status()
        result = await self.privileged_props.save()
        print("已经得到保存并 upgrade 结果")
        if int(result["returncode"]) == 126:
            self.privileged_props.restore()
            print("已经恢复")
        await self.start_session()
        print("已经启动session")

    def restore_privileged_props(self):
        self.privileged_props.restore()

    # 因为双向绑定了, 所以不需要传入值
    async def save_persist_prop(self, name):
        await self.persist_props.save(name)

    async def update_waydroid_status(self):
        result = await self._subprocess._run_subprocess("waydroid status")
        output = result["stdout"]
        if self.state == WaydroidState.UNINITIALIZED:
            if "Session:\tRUNNING" in output:
                await self.init_persist_props()
                self.init_privileged_props()
                self.set_property("state", WaydroidState.RUNNING)
            elif "Session:\tSTOPPED" in output:
                self.init_privileged_props()
                self.set_property("state", WaydroidState.STOPPED)
        elif self.state == WaydroidState.STOPPED:
            if "Session:\tRUNNING" in output:
                await self.init_persist_props()
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
                await self.init_persist_props()
                self.set_property("state", WaydroidState.RUNNING)

    def __update_waydroid_status(self):
        self._task.create_task(self.update_waydroid_status())
        return True

    def __init__(self) -> None:
        super().__init__()
        self.set_property("state", WaydroidState.LOADING)
        # 立即执行一次, 随后再每两秒一次
        self._task.create_task(self.update_waydroid_status())
        GLib.timeout_add_seconds(2, self.__update_waydroid_status)

    async def start_session(self):
        result = await self._subprocess._run_subprocess(
            command="waydroid session start", flag=True
        )
        await self.update_waydroid_status()
        return result

    async def stop_session(self):
        result = await self._subprocess._run_subprocess(
            command="waydroid session stop", flag=True
        )
        await self.update_waydroid_status()
        return result

    async def restart_session(self):
        await self.stop_session()
        await self.start_session()

    async def show_full_ui(self):
        result = await self._subprocess._run_subprocess(
            command="waydroid show-full-ui", flag=True
        )
        await self.update_waydroid_status()
        return result

    async def upgrade(self, offline: Optional[bool] = None):
        if offline:
            await self.save_privileged_props()
        else:
            await self._subprocess._run_subprocess(
                command="pkexec waydroid upgrade", flag=True
            )
            await self.update_waydroid_status()
