import os
from gi.repository import GLib
import subprocess
import threading
from typing import Any, Callable, Optional
import gi

gi.require_version("Gtk", "4.0")


class ProcessLauncher:

    def __init__(
        self,
        cmd: list,
        callback: Callable[[str], Any] = None,
        timeout: Optional[int] = None,
        handler: Callable[[str], Any] = None,
        flag=False,
    ):
        self.cmd = cmd
        self.callback = callback
        self.outputs = []
        self.flag = flag
        self.handler = handler

        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()

    def run(self):
        try:
            process = subprocess.Popen(
                self.cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                preexec_fn=os.setsid if self.flag else None,
            )
        except FileNotFoundError:
            print(f"{self.cmd[0]} not found")

        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                print(f"Output: {output.strip()}")
                self.outputs.append(output.strip())

        return_code = process.poll()
        if return_code != 0:
            print(f"failed with return code {return_code}")
            if self.handler:
                GLib.idle_add(self.handler, return_code)
        
        else:
            if self.callback:
                GLib.idle_add(self.callback, "\n".join(self.outputs))
            print(f"Return code:{return_code}")
