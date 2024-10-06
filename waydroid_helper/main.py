import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import os
from .window import WaydroidHelperWindow
from gi.repository import Gtk, Gio, Adw
from gi.events import GLibEventLoopPolicy
import sys
import asyncio


Adw.init()


adw_version = os.environ['adw_version']
gtk_version = os.environ['gtk_version']
glib_version = os.environ['glib_version']

MESSAGE_DIALOG = "GtkMessageDialog"
if gtk_version < '41000':
    BaseDialog = Gtk.MessageDialog
elif adw_version >= '10200' and adw_version < '10600':
    MESSAGE_DIALOG = "AdwMessageDialog"
    BaseDialog = Adw.MessageDialog
elif adw_version >= '10600':
    MESSAGE_DIALOG = "AdwAlertDialog"
    BaseDialog = Adw.AlertDialog
if glib_version>='27400':
    FLAGS = Gio.ApplicationFlags.DEFAULT_FLAGS
else:
    FLAGS = Gio.ApplicationFlags.FLAGS_NONE

class Dialog(BaseDialog):
    def __init__(self, parent):
        self.parent_window = parent
        if MESSAGE_DIALOG == "AdwMessageDialog":
            super().__init__(transient_for=parent)
            self.set_modal(True)
            self.set_heading(heading="Error")
            self.set_body(body="Cannot run as root user!")
            self.add_response(Gtk.ResponseType.OK.value_nick, "OK")
            self.set_response_appearance(
                response=Gtk.ResponseType.OK.value_nick,
                appearance=Adw.ResponseAppearance.SUGGESTED,
            )
            self.connect("response", self.dialog_response)
            self.connect("close-request", self.dialog_close)
        elif MESSAGE_DIALOG == "GtkMessageDialog":
            super().__init__(
                text="Error",
                modal=True,
                secondary_text="Cannot run as root user!",
                transient_for=parent
            )
            self.add_button("Ok", Gtk.ResponseType.OK)
            self.set_default_response(Gtk.ResponseType.OK)
            self.connect("response", self.dialog_response)
            self.connect("close-request", self.dialog_close)
        else:
            super().__init__()
            self.set_heading("Error")
            self.set_body("Cannot run as root user!")
            self.add_response(Gtk.ResponseType.OK.value_nick, "OK")
            self.set_close_response(Gtk.ResponseType.OK.value_nick)
            self.connect("response", self.dialog_response)

    def show(self):
        if MESSAGE_DIALOG!='AdwAlertDialog':
            self.present()
        else:
            self.present(self.parent_window)

    def dialog_response(self, dialog, response):
        if MESSAGE_DIALOG == "AdwMessageDialog" or MESSAGE_DIALOG == "AdwAlertDialog":
            if response == Gtk.ResponseType.OK.value_nick:
                sys.exit()
        else:
            if response == Gtk.ResponseType.OK:
                sys.exit()

    def dialog_close(self, dialog):
        sys.exit(0)


class WaydroidHelperApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(
            application_id="com.jaoushingan.WaydroidHelper",
            flags=FLAGS
        )
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
            dialog = Dialog(win)
            win.present()
            dialog.show()
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
        print("app.preferences action activated")

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
