import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib
from .navigation_view import NavigationView
from .navigation_page import NavigationPage
from .toolbar_view import ToolbarView
from .spinner import Spinner
from .message_dialog import MessageDialog
from .header_bar import HeaderBar
from .file_dialog import FileDialog
from .shared_folder_dialog import SharedFolderDialog

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION

__all__ = [
    "NavigationView",
    "NavigationPage",
    "ToolbarView",
    "Spinner",
    "MessageDialog",
    "HeaderBar",
    "FileDialog",
    "SharedFolderDialog",
    "GTK_VERSION",
    "ADW_VERSION",
    "GLIB_VERSION"
]
