# pyright: reportUnknownVariableType=false,reportMissingImports=false

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import asyncio
import os
import sys

from gi.events import GLibEventLoopPolicy
from gi.repository import Adw, Gio, GObject, Gtk

from waydroid_helper.compat_widget import GLIB_VERSION, MessageDialog
from waydroid_helper.util import logger

from .window import WaydroidHelperWindow

Adw.init()

if GLIB_VERSION >= (2, 74, 0):
    flags = Gio.ApplicationFlags.DEFAULT_FLAGS
else:
    flags = Gio.ApplicationFlags.FLAGS_NONE


class WaydroidHelperApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self, version: str):
        super().__init__(application_id="com.jaoushingan.WaydroidHelper", flags=flags)
        self.version = version
        self.create_action(
            "quit",
            lambda *_: self.quit(),  # pyright: ignore[reportUnknownArgumentType]
            ["<primary>q"],
        )
        self.create_action("about", self.on_about_action)
        self.create_action("preferences", self.on_preferences_action)

    # @override
    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """

        uid = os.getuid()
        if uid == 0:
            win = Adw.ApplicationWindow(application=self)

            def dialog_response(
                dialog: MessageDialog, response: Gtk.ResponseType | str
            ):
                sys.exit()

            dialog = MessageDialog(
                parent=win, heading="Error", body="Cannot run as root user!"
            )
            dialog.add_response(Gtk.ResponseType.OK, "OK")
            dialog.connect(  # pyright: ignore[reportUnknownMemberType]
                "response", dialog_response
            )
            win.present()
            dialog.present()

        else:
            win = self.props.active_window
            if not win:
                win = WaydroidHelperWindow(application=self)
            win.present()

    def on_about_action(self, widget: Gtk.Widget, _: GObject.Object):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="waydroid-helper",
            application_icon="com.jaoushingan.WaydroidHelper",
            developer_name="rikka",
            version=self.version,
            developers=["rikka"],
            copyright="© 2024 rikka",
        )
        about.present()

    def on_preferences_action(self, widget: Gtk.Widget, _: GObject.Object):
        """Callback for the app.preferences action."""
        logger.info("app.preferences action activated")

    def create_action(
        self,
        name: str,
        callback: Callable[[Gtk.Widget, GObject.Object], None],
        shortcuts: list[str] | None = None,
    ):
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


def main(version: str):
    """The application's entry point."""
    asyncio.set_event_loop_policy(
        GLibEventLoopPolicy()  # pyright:ignore[reportUnknownArgumentType]
    )
    app = WaydroidHelperApplication(version)
    return app.run(sys.argv)
