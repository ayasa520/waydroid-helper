#!/usr/bin/env python3

import configparser
import subprocess
import threading
import tools.helper
import dbus
import secrets
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from service.shell import ShellService


# class NotPrivilegedException(dbus.DBusException):
#     _dbus_error_name = "org.waydroid.Helper.dbus.service.PolKit.NotPrivilegedException"

#     def __init__(self, action_id, *p, **k):
#         self._dbus_error_name = self.__class__._dbus_error_name + "." + action_id
#         super(NotPrivilegedException, self).__init__(*p, **k)


class Waydroid(dbus.service.Object):

    def __init__(self, conn=None, object_path=None, bus_name=None):
        self.dbus_info = None
        self.polkit = None
        self.shell_service = ShellService()
        dbus.service.Object.__init__(self, conn, object_path, bus_name)

    @dbus.service.method(dbus_interface="com.waydroid.HelperInterface", in_signature="s", out_signature="s",
                         sender_keyword="sender", connection_keyword="conn")
    def Shell(self, command, sender=None, conn=None):
        self._check_polkit_privilege(sender, conn, "com.waydroid.Helper.auth")
        return tools.helper.shell(str(command)).stdout.decode("utf-8")

    @dbus.service.method(dbus_interface="com.waydroid.HelperInterface", out_signature="s", sender_keyword="sender",
                         connection_keyword="conn")
    def StartShell(self, sender=None, conn=None):
        self._check_polkit_privilege(sender, conn, "com.waydroid.Helper.auth")
        secret = secrets.token_hex(8)
        self.shell_service.start(secret)
        return secret

    @dbus.service.method(dbus_interface="com.waydroid.HelperInterface", in_signature="s", out_signature="s",
                         sender_keyword="sender", connection_keyword="conn")
    def InstallApk(self, apk, sender=None, conn=None):
        self._check_polkit_privilege(sender, conn, "com.waydroid.Helper.auth")
        output = tools.helper.shell("pm install /data/waydroid_tmp/{}".format(apk))
        tools.helper.shell("rm -f /data/waydroid_tmp/{}".format(apk))
        return output.stdout.decode("utf-8").strip()

    @dbus.service.method(dbus_interface="com.waydroid.HelperInterface")
    def StopShell(self):
        if self.shell_service:
            self.shell_service.stop()

    @dbus.service.method(dbus_interface="com.waydroid.HelperInterface", sender_keyword="sender",
                         connection_keyword="conn")
    def Unfreeze(self, sender=None, conn=None):
        self._check_polkit_privilege(sender, conn, "com.waydroid.Helper.auth")
        tools.helper.run(["waydroid", "container", "unfreeze"])

    @dbus.service.method(dbus_interface="com.waydroid.HelperInterface", in_signature="ss", out_signature="b",
                         sender_keyword="sender", connection_keyword="conn")
    def SetBaseProp(self, key, value, sender, conn):
        self._check_polkit_privilege(sender, conn, "com.waydroid.Helper.auth")
        try:
            cfg = configparser.ConfigParser()
            with open("/var/lib/waydroid/waydroid_base.prop") as f:
                first_line = f.readline()
                if not first_line.startswith("["):
                    f.seek(0)
                    content = "[DEFAULT]\n" + f.read()
                else:
                    content = first_line + f.read()
            print(content)
            cfg.read_string(content)
            cfg.set(section="DEFAULT", option=key, value=value)
            with open("/var/lib/waydroid/waydroid_base.prop", "w") as f:
                f.writelines(["{} = {}\n".format(k, v)
                              for k, v in cfg.items("DEFAULT")])
        except:
            raise
        return dbus.Boolean(True)

    def _check_polkit_privilege(self, sender, conn, action_id):
        # Get Peer PID
        if self.dbus_info is None:
            # Get DBus Interface and get info thru that
            self.dbus_info = dbus.Interface(conn.get_object("org.freedesktop.DBus",
                                                            "/org/freedesktop/DBus/Bus", False),
                                            "org.freedesktop.DBus")
        pid = self.dbus_info.GetConnectionUnixProcessID(sender)

        # Query polkit
        if self.polkit is None:
            self.polkit = dbus.Interface(dbus.SystemBus().get_object(
                "org.freedesktop.PolicyKit1",
                "/org/freedesktop/PolicyKit1/Authority", False),
                "org.freedesktop.PolicyKit1.Authority")

        # Check auth against polkit; if it times out, try again
        try:
            auth_response = self.polkit.CheckAuthorization(
                ("unix-process", {"pid": dbus.UInt32(pid, variant_level=1),
                                  "start-time": dbus.UInt64(0, variant_level=1)}),
                action_id, {"AllowUserInteraction": "true"}, dbus.UInt32(1), "", timeout=600)
            print(auth_response)
            (is_auth, _, details) = auth_response
        except dbus.DBusException as e:
            if e._dbus_error_name == "org.freedesktop.DBus.Error.ServiceUnknown":
                # polkitd timeout, retry
                self.polkit = None
                return self._check_polkit_privilege(sender, conn, action_id)
            else:
                # it's another error, propagate it
                raise

        if not is_auth:
            # Aww, not authorized :(
            print(":(")
            raise ValueError("not authorized")

        print("Successful authorization!")
        return True

    @dbus.service.signal("com.waydroid.HelperInterface", signature="ay")
    def logcat_signal(self, output):
        print(output)
        pass

    @dbus.service.method(dbus_interface="com.waydroid.HelperInterface")
    def StopLogcat(self):

        if self.p:
            print("kill了")
            self.p.kill()
        self.p = None

    @dbus.service.method(dbus_interface="com.waydroid.HelperInterface", sender_keyword="sender",
                         connection_keyword="conn")
    def Logcat(self, sender=None, conn=None):
        self._check_polkit_privilege(sender, conn, "com.waydroid.Helper.auth")
        cmd = ["waydroid", "logcat"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE)

        def run():
            while True:
                try:
                    line = self.p.stdout.readline()
                    print(self.p)
                    if line:
                        self.logcat_signal(line)
                except:
                    break
            print("logcat over")

        trd = threading.Thread(target=run)
        trd.start()


if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    name = dbus.service.BusName("com.waydroid.Helper", bus)
    waydroid = Waydroid(bus, "/Waydroid")
    mainloop = GLib.MainLoop()
    mainloop.run()
