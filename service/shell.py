#!/usr/bin/env python3

import socket
import threading

from service.pty import PTY


class ShellService:
    pty: PTY = None

    def __init__(self) -> None:
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.threads = []
        self.ptys = []
        try:
            self.s.bind(("127.0.0.1", 25000))
            self.s.listen(0)
            print("[+]Start Server.")
        except Exception as e:
            print("[-]Error Happened: %s" % e.message)
            return

    def start(self, secret):
        def service_thread():
            c = self.s.accept()
            received = c[0].recv(1024).decode().strip()
            if received == secret:
                pty = PTY(c[0].fileno(), c[0].fileno(), c[0].fileno())
                self.ptys.append(pty)
                pty.spawn(["waydroid", "shell", "--", "sh", "-c",
                           'export BOOTCLASSPATH=/apex/com.android.art/javalib/core-oj.jar:/apex/com.android.art/javalib/core-libart.jar:/apex/com.android.art/javalib/core-icu4j.jar:/apex/com.android.art/javalib/okhttp.jar:/apex/com.android.art/javalib/bouncycastle.jar:/apex/com.android.art/javalib/apache-xml.jar:/system/framework/framework.jar:/system/framework/ext.jar:/system/framework/telephony-common.jar:/system/framework/voip-common.jar:/system/framework/ims-common.jar:/system/framework/framework-atb-backward-compatibility.jar:/apex/com.android.conscrypt/javalib/conscrypt.jar:/apex/com.android.media/javalib/updatable-media.jar:/apex/com.android.mediaprovider/javalib/framework-mediaprovider.jar:/apex/com.android.os.statsd/javalib/framework-statsd.jar:/apex/com.android.permission/javalib/framework-permission.jar:/apex/com.android.sdkext/javalib/framework-sdkextensions.jar:/apex/com.android.wifi/javalib/framework-wifi.jar:/apex/com.android.tethering/javalib/framework-tethering.jar;export PATH=/data/adb/overlay_modules/bin:$PATH;[ ! -e /dev/tty ] && mknod -m 666 /dev/tty c 5 0;sh'])
            else:
                c[0].sendall(b'Invalid secret.\n')
            c[0].close()

        thread = threading.Thread(target=service_thread)
        self.threads.append(thread)
        thread.start()

    def stop(self):
        self.stopping = True
        for pty in self.ptys:
            if pty:
                pty.stop()

        self.ptys.clear()

        for thread in self.threads:
            thread.join()
        self.threads.clear()
        print("stop")

    def __del__(self):
        self.s.close()
