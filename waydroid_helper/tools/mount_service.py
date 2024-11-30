# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false

import os
import subprocess
from typing import final

import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

import dbus


@final
class MountError(dbus.DBusException):
    _dbus_error_name = "id.waydro.MountError"


class MountService(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName( # pyright:ignore[reportUnknownVariableType]
            "id.waydro.Mount", bus=dbus.SystemBus()
        )  
        dbus.service.Object.__init__(self, bus_name, "/org/waydro/Mount")

    @dbus.service.method("id.waydro.Mount", in_signature="ss", out_signature="a{sv}")
    def BindMount(self, source, target):
        source_str = str(source)
        target_str = str(target)
        try:
            stat_info = os.stat(target_str)
            fuse_version_result = subprocess.run(
                ["bindfs", "--fuse-version"],
                capture_output=True,
                text=True,
            )
            fuse_version = fuse_version_result.stdout.splitlines()[0].split()[4]
            if int(fuse_version.split('.')[0]) < 3:
                nonempty_option = "-o nonempty"
            else:
                nonempty_option = ""

            command = [
                "bindfs",
                "-u",
                str(stat_info.st_uid),
                "-g",
                str(stat_info.st_gid),
                source_str,
                target_str,
            ]
            if nonempty_option:
                command.insert(1, nonempty_option)

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except OSError as e:
            error_msg = f"OS Error: {str(e)}"
            raise MountError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            raise MountError(error_msg)

    @dbus.service.method("id.waydro.Mount", in_signature="s", out_signature="a{sv}")
    def Unmount(self, target):
        target_str = str(target)
        try:
            result = subprocess.run(
                ["fusermount", "-u", "-z", target_str], capture_output=True, text=True
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except OSError as e:
            error_msg = f"OS Error: {str(e)}"
            raise MountError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            raise MountError(error_msg)


def start():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    loop = GLib.MainLoop()
    MountService()
    loop.run()
