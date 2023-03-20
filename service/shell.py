#!/usr/bin/env python3

import os
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
                print("对象是", self.pty)
                pty = PTY(c[0].fileno(), c[0].fileno(), c[0].fileno())
                self.ptys.append(pty)
                pty.spawn(["waydroid", "shell", "--", "sh", "-c",
                           'export PATH=/data/adb/overlay_modules/bin:$PATH;[ ! -e /dev/tty ] && mknod -m 666 /dev/tty c 5 0;sh'])
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
            print("join了")
            thread.join()
        self.threads.clear()
        print("stop")

    def __del__(self):
        self.s.close()
