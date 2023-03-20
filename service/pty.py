"""Pseudo terminal utilities."""

# Bugs: No signal handling.  Doesn't set slave termios and window size.
#       Only tested on Linux, FreeBSD, and macOS.
# See:  W. Richard Stevens. 1992.  Advanced Programming in the
#       UNIX Environment.  Chapter 19.
# Author: Steen Lumholt -- with additions by Guido.

from select import select
import os
import sys
import time
import tty
import signal
import psutil


# names imported directly for test mocking purposes
from os import close, waitpid, kill
from tty import setraw, tcgetattr, tcsetattr


class PTY:
    STDIN_FILENO = 0
    STDOUT_FILENO = 1
    STDERR_FILENO = 2

    CHILD = 0
    def __init__(self, stdin_filno, stdout_fileno, stderr_fileno):
        self.STDOUT_FILENO = stdout_fileno
        self.STDIN_FILENO = stdin_filno
        self.STDERR_FILENO = stderr_fileno
        self.pids=[]

    def openpty(self):
        """openpty() -> (master_fd, slave_fd)
        Open a pty master/slave pair, using os.openpty() if possible."""

        try:
            return os.openpty()
        except (AttributeError, OSError):
            pass
        master_fd, slave_name = self._open_terminal()
        slave_fd = self.slave_open(slave_name)
        return master_fd, slave_fd

    def master_open(self):
        """master_open() -> (master_fd, slave_name)
        Open a pty master and return the fd, and the filename of the slave end.
        Deprecated, use openpty() instead."""

        try:
            master_fd, slave_fd = os.openpty()
        except (AttributeError, OSError):
            pass
        else:
            slave_name = os.ttyname(slave_fd)
            os.close(slave_fd)
            return master_fd, slave_name

        return self._open_terminal()

    def _open_terminal(self):
        """Open pty master and return (master_fd, tty_name)."""
        for x in 'pqrstuvwxyzPQRST':
            for y in '0123456789abcdef':
                pty_name = '/dev/pty' + x + y
                try:
                    fd = os.open(pty_name, os.O_RDWR)
                except OSError:
                    continue
                return (fd, '/dev/tty' + x + y)
        raise OSError('out of pty devices')

    def slave_open(self, tty_name):
        """slave_open(tty_name) -> slave_fd
        Open the pty slave and acquire the controlling terminal, returning
        opened filedescriptor.
        Deprecated, use openpty() instead."""

        result = os.open(tty_name, os.O_RDWR)
        try:
            from fcntl import ioctl, I_PUSH
        except ImportError:
            return result
        try:
            ioctl(result, I_PUSH, "ptem")
            ioctl(result, I_PUSH, "ldterm")
        except OSError:
            pass
        return result

    def fork(self):
        """fork() -> (pid, master_fd)
        Fork and make the child a session leader with a controlling terminal."""

        try:
            pid, fd = os.forkpty()
        except (AttributeError, OSError):
            pass
        else:
            if pid == self.CHILD:
                try:
                    os.setsid()
                except OSError:
                    # os.forkpty() already set us session leader
                    pass
            return pid, fd

        master_fd, slave_fd = self.openpty()
        pid = os.fork()
        if pid == self.CHILD:
            # Establish a new session.
            os.setsid()
            os.close(master_fd)

            # Slave becomes stdin/stdout/stderr of child.
            os.dup2(slave_fd, self.STDIN_FILENO)
            os.dup2(slave_fd, self.STDOUT_FILENO)
            os.dup2(slave_fd, self.STDERR_FILENO)
            if slave_fd > self.STDERR_FILENO:
                os.close(slave_fd)

            # Explicitly open the tty to make it become a controlling tty.
            tmp_fd = os.open(os.ttyname(self.STDOUT_FILENO), os.O_RDWR)
            os.close(tmp_fd)
        else:
            os.close(slave_fd)

        # Parent and child process.
        return pid, master_fd

    def _writen(self, fd, data):
        """Write all the data to a descriptor."""
        while data:
            n = os.write(fd, data)
            data = data[n:]

    def _read(fd):
        """Default read function."""
        return os.read(fd, 1024)

    def _copy(self, master_fd, master_read=_read, stdin_read=_read):
        """Parent copy loop.
        Copies
                pty master -> standard output   (master_read)
                standard input -> pty master    (stdin_read)"""
        fds = [master_fd, self.STDIN_FILENO]
        while fds:
            rfds, _wfds, _xfds = select(fds, [], [])

            if master_fd in rfds:
                # Some OSes signal EOF by returning an empty byte string,
                # some throw OSErrors.
                try:
                    data = master_read(master_fd)
                except OSError:
                    data = b""
                if not data:  # Reached EOF.
                    return    # Assume the child process has exited and is
                            # unreachable, so we clean up.
                else:
                    os.write(self.STDOUT_FILENO, data)

            if self.STDIN_FILENO in rfds:
                data = stdin_read(self.STDIN_FILENO)
                if not data:
                    fds.remove(self.STDIN_FILENO)
                else:
                    self._writen(master_fd, data)

    def spawn(self, argv, master_read=_read, stdin_read=_read):
        """Create a spawned process."""
        if type(argv) == type(''):
            argv = (argv,)
        sys.audit('pty.spawn', argv)

        pid, master_fd = self.fork()
        if pid != self.CHILD:
            print("pid: ", pid)
            self.pids.append(pid)
        if pid == self.CHILD:
            os.execlp(argv[0], *argv)

        try:
            mode = tcgetattr(self.STDIN_FILENO)
            setraw(self.STDIN_FILENO)
            restore = True
        except tty.error:    # This is the same as termios.error
            restore = False

        try:
            self._copy(master_fd, master_read, stdin_read)
        finally:
            if restore:
                tcsetattr(self.STDIN_FILENO, tty.TCSAFLUSH, mode)

        close(master_fd)
        return waitpid(pid, 0)[1]

    def stop(self):
        print("PID 有:", self.pids)
        for pid in self.pids[::-1]:
            if psutil.pid_exists(pid):
                print("kill",pid)
                os.kill(pid, signal.SIGTERM)
                self.pids.remove(pid)

    
