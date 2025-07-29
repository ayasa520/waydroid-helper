# pyright: reportUnknownMemberType=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false
# pyright: reportRedeclaration=false
# pyright: reportUnknownVariableType=false
from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gettext import gettext as _

from gi.repository import GLib, GObject, Gtk

from waydroid_helper.util import logger

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()


class FileDialogMeta(type(GObject.Object)):
    def __new__(mcs, name:str, bases:tuple[type, ...], attrs:dict[str, Any]):
        # final class
        for base in bases:
            if isinstance(base, FileDialogMeta):
                raise TypeError(
                    "type '{0}' is not an acceptable base type".format(base.__name__)
                )

        if GTK_VERSION >= (4, 10, 0):

            def __init__(self, parent: Gtk.Window | None = None, title: str | None = None, modal: bool = True):
                # super().__init__()
                self._parent = parent
                self._title = title if title else ""
                self._modal = modal
                self._filedialog = Gtk.FileDialog(title=self._title, modal=self._modal)

            def select_folder(self, callback):
                filter = Gtk.FileFilter()
                filter.add_mime_type("inode/directory")
                self._filedialog.set_default_filter(filter)
                self._filedialog.select_folder(
                    self._parent, None, self._on_folder_selected, callback
                )

            def _on_folder_selected(self, dialog, result, callback):
                try:
                    file = dialog.select_folder_finish(result)
                    if file:
                        path = file.get_path()
                        callback(True, path)
                    else:
                        callback(False, None)
                except GLib.Error as e:
                    logger.error(e)
                    callback(False, None)

            def open_file(self, callback, file_filter=None, initial_folder=None):
                if file_filter:
                    self._filedialog.set_default_filter(file_filter)
                if initial_folder:
                    from gi.repository import Gio
                    folder_file = Gio.File.new_for_path(initial_folder)
                    self._filedialog.set_initial_folder(folder_file)
                self._filedialog.open(
                    self._parent, None, self._on_file_opened, callback
                )

            def _on_file_opened(self, dialog, result, callback):
                try:
                    file = dialog.open_finish(result)
                    if file:
                        path = file.get_path()
                        callback(True, path)
                    else:
                        callback(False, None)
                except GLib.Error as e:
                    logger.error(e)
                    callback(False, None)

            def save_file(self, callback, suggested_name=None, file_filter=None, initial_folder=None):
                if suggested_name:
                    self._filedialog.set_initial_name(suggested_name)
                if file_filter:
                    self._filedialog.set_default_filter(file_filter)
                if initial_folder:
                    from gi.repository import Gio
                    folder_file = Gio.File.new_for_path(initial_folder)
                    self._filedialog.set_initial_folder(folder_file)
                self._filedialog.save(
                    self._parent, None, self._on_file_saved, callback
                )

            def _on_file_saved(self, dialog, result, callback):
                try:
                    file = dialog.save_finish(result)
                    if file:
                        path = file.get_path()
                        callback(True, path)
                    else:
                        callback(False, None)
                except GLib.Error as e:
                    logger.error(e)
                    callback(False, None)

        else:

            def __init__(self, parent: Gtk.Window | None = None, title: str | None = None, modal: bool = True):
                # super().__init__()
                self._parent = parent
                self._title = title
                self._modal = modal
                self._filedialog = Gtk.FileChooserDialog(
                    title=self._title, modal=self._modal, transient_for=self._parent
                )
                self._filedialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
                self._filedialog.add_button(_("Select"), Gtk.ResponseType.ACCEPT)

            def select_folder(self, callback):
                self._filedialog.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
                self._filedialog.connect("response", self._on_folder_selected, callback)
                self._filedialog.present()

            def _on_folder_selected(self, dialog, response, callback):
                try:
                    if response == Gtk.ResponseType.ACCEPT:
                        path:str= dialog.get_file().get_path()
                        callback(True, path)
                    else:
                        callback(False, None)
                except Exception as e:
                    logger.error(e)
                    callback(False, None)
                finally:
                    dialog.destroy()

            def open_file(self, callback, file_filter=None, initial_folder=None):
                self._filedialog.set_action(Gtk.FileChooserAction.OPEN)
                if file_filter:
                    self._filedialog.set_filter(file_filter)
                if initial_folder:
                    from gi.repository import Gio
                    folder_file = Gio.File.new_for_path(initial_folder)
                    try:
                        self._filedialog.set_current_folder(folder_file)
                    except Exception as e:
                        logger.error(f"Failed to set current folder: {e}")
                self._filedialog.connect("response", self._on_file_opened, callback)
                self._filedialog.present()

            def _on_file_opened(self, dialog, response, callback):
                try:
                    if response == Gtk.ResponseType.ACCEPT:
                        path:str = dialog.get_file().get_path()
                        callback(True, path)
                    else:
                        callback(False, None)
                except Exception as e:
                    logger.error(e)
                    callback(False, None)
                finally:
                    dialog.destroy()

            def save_file(self, callback, suggested_name=None, file_filter=None, initial_folder=None):
                self._filedialog.set_action(Gtk.FileChooserAction.SAVE)
                if suggested_name:
                    self._filedialog.set_current_name(suggested_name)
                if file_filter:
                    self._filedialog.set_filter(file_filter)
                if initial_folder:
                    from gi.repository import Gio
                    folder_file = Gio.File.new_for_path(initial_folder)
                    try:
                        self._filedialog.set_current_folder(folder_file)
                    except Exception as e:
                        logger.error(f"Failed to set current folder: {e}")
                self._filedialog.connect("response", self._on_file_saved, callback)
                self._filedialog.present()

            def _on_file_saved(self, dialog, response, callback):
                try:
                    if response == Gtk.ResponseType.ACCEPT:
                        path:str = dialog.get_file().get_path()
                        callback(True, path)
                    else:
                        callback(False, None)
                except Exception as e:
                    logger.error(e)
                    callback(False, None)
                finally:
                    dialog.destroy()

        attrs["__init__"] = __init__
        attrs["select_folder"] = select_folder
        attrs["_on_folder_selected"] = _on_folder_selected
        attrs["open_file"] = open_file
        attrs["_on_file_opened"] = _on_file_opened
        attrs["save_file"] = save_file
        attrs["_on_file_saved"] = _on_file_saved
        return super().__new__(mcs, name, bases, attrs)


class FileDialog(GObject.Object, metaclass=FileDialogMeta):
    __gtype_name__:str = "FileDialog"

    def __init__(self, parent: Gtk.Window | None = None, title: str | None = None, modal: bool = True):
        pass

    def select_folder(self, callback: Callable[[bool, str | None], None]):
        pass

    def open_file(self, callback: Callable[[bool, str | None], None], file_filter=None, initial_folder=None):
        pass

    def save_file(self, callback: Callable[[bool, str | None], None], suggested_name=None, file_filter=None, initial_folder=None):
        pass
