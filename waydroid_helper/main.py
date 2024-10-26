import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import os
from .window import WaydroidHelperWindow
from gi.repository import Gtk, Gio, Adw
from gi.events import GLibEventLoopPolicy
from waydroid_helper.compat_widget import GLIB_VERSION, Dialog
from waydroid_helper.util import logger
import sys
import asyncio


Adw.init()

if GLIB_VERSION >= (2, 74, 0):
    FLAGS = Gio.ApplicationFlags.DEFAULT_FLAGS
else:
    FLAGS = Gio.ApplicationFlags.FLAGS_NONE

class WaydroidHelperApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id="com.jaoushingan.WaydroidHelper", flags=FLAGS)
        self.create_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self.create_action("about", self.on_about_action)
        self.create_action("preferences", self.on_preferences_action)

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """

        uid = os.getuid()
        if uid == 0:
            win = Adw.ApplicationWindow(application=self)
            def dialog_response(dialog, response):
                sys.exit()
            dialog = Dialog(
                parent=win, heading="Error", body="Cannot run as root user!"
            )
            dialog.add_response(Gtk.ResponseType.OK, "OK")
            dialog.connect("response", dialog_response)
            win.present()
            dialog.present()
            
        else:
            win = self.props.active_window
            if not win:
                win = WaydroidHelperWindow(application=self)
            win.present()

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="waydroid-helper",
            application_icon="com.jaoushingan.WaydroidHelper",
            developer_name="rikka",
            version="0.1.0",
            developers=["rikka"],
            copyright="© 2024 rikka",
        )
        about.present()

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        logger.info("app.preferences action activated")

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    asyncio.set_event_loop_policy(GLibEventLoopPolicy())
    app = WaydroidHelperApplication()
    return app.run(sys.argv)
