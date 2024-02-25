#!/usr/bin/env python3

# https://gist.github.com/fthiery/da43365ceeefff8a9e3d0dd83ec24af9

from typing import Any, Callable, Optional
from gi.repository import Gio, GLib
import shlex
import signal

priority = GLib.PRIORITY_DEFAULT


class ProcessLauncher:
    alive = True
    stdout: str = ''
    callback: Callable[[str], Any]
    args: list

    def __init__(self, cmd: str, callback: Callable[[str], Any] = None, timeout: Optional[int] = None) -> None:
        GLib.idle_add(self.run, cmd)
        self.callback = callback
        if timeout:
            GLib.timeout_add_seconds(
                priority=priority,
                interval=timeout,
                function=self.stop
            )

    def run(self, cmd):
        self.cancellable = Gio.Cancellable()
        try:
            flags = Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
            args = shlex.split(cmd)
            self.process = p = Gio.Subprocess.new(args, flags)
            p.wait_check_async(
                cancellable=self.cancellable,
                callback=self._on_finished
            )
            print('Started')
            stream = p.get_stdout_pipe()
            self.data_stream = Gio.DataInputStream.new(stream)
            self.queue_read()
        except GLib.GError as e:
            print(e)

    def queue_read(self):
        self.data_stream.read_line_async(
            io_priority=priority,
            cancellable=self.cancellable,
            callback=self._on_data
        )

    def cancel_read(self):
        print('Cancelling read')
        self.cancellable.cancel()

    def _on_finished(self, proc, results):
        print('Process finished')
        if self.callback:
            # self.callback(self.stout)
            GLib.idle_add(self.callback, self.stdout)
        try:
            proc.wait_check_finish(results)
        except Exception as e:
            print(e)
            self.alive = False
        self.cancel_read()
        self.alive = False

    def _on_data(self, source, result):
        try:
            line, length = source.read_line_finish_utf8(result)
            if line:
                # print(line)
                self.stdout = f'{self.stdout}\n{line}'
        except GLib.GError as e:
            # print(e)
            return
        self.queue_read()

    def stop(self):
        print('Stop')
        self.process.send_signal(signal.SIGTERM)

    def kill(self):
        print('Kill')
        self.cancel_read()
        self.process.send_signal(signal.SIGKILL)


# if __name__ == '__main__':
#     p = ProcessLauncher("waydroid status")
#     m = GLib.MainLoop()
#     m.run()
