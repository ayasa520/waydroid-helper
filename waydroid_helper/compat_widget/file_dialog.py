import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, GLib, GObject
from waydroid_helper.util import logger
from gettext import gettext as _


GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()


class FileDialogMeta(type(GObject.Object)):
    def __new__(mcs, name, bases, attrs):
        # final class
        for base in bases:
            if isinstance(base, FileDialogMeta):
                raise TypeError(
                    "type '{0}' is not an acceptable base type".format(base.__name__)
                )

        if GTK_VERSION >= (4, 10, 0):

            def __init__(self, parent=None, title=None, modal=True):
                # super().__init__()
                self._parent = parent
                self._title = title
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

        else:

            def __init__(self, parent=None, title=None, modal=True):
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
                        path = dialog.get_file().get_path()
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
        return super().__new__(mcs, name, bases, attrs)


class FileDialog(GObject.Object, metaclass=FileDialogMeta):
    __gtype_name__ = "FileDialog"

    def __init__(self, parent=None, title=None, modal=True):
        pass

    def select_folder(self, callback):
        pass
