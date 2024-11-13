import weakref
import gi
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, GObject, Gio
from waydroid_helper.util import connect_weakly
from .file_dialog import FileDialog
from gettext import gettext as _

ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()

if ADW_VERSION >= (1, 5, 0):
    BASE_DIALOG = Adw.Dialog
else:
    BASE_DIALOG = Adw.Window


class DialogMeta(type(GObject.Object)):
    def __new__(mcs, name, bases, attrs):
        # final class
        for base in bases:
            if isinstance(base, DialogMeta):
                raise TypeError(
                    "type '{0}' is not an acceptable base type".format(base.__name__)
                )

        if BASE_DIALOG == Adw.Window:

            def __init__(self, parent):
                super(self.__class__, self).__init__(transient_for=parent, modal=True)
                self.set_size_request(400, 100)
                self.set_default_size(400, 100)
                self.set_resizable(False)
                content = self._init_content()
                self.set_content(content)

                instance = weakref.ref(self)
                method = weakref.ref(Adw.Window.destroy)
                shortcut = Gtk.Shortcut.new(
                    Gtk.ShortcutTrigger.parse_string("Escape"),
                    Gtk.CallbackAction.new(lambda *_: method()(instance())),
                )
                shortcut_controller = Gtk.ShortcutController()
                shortcut_controller.add_shortcut(shortcut)
                self.add_controller(shortcut_controller)

            def present(self):
                super(self.__class__, self).present()

            def _on_cancel(self, button):
                self.destroy()

            def _on_save_btn_clicked(self, button):
                source = self.current_path
                target = self.target_entry.get_text()

                if target == "":
                    return

                if source:
                    self.emit("saved", source, target)
                self.destroy()

        else:  # Adw.Dialog

            def __init__(self, parent):
                super(self.__class__, self).__init__(
                    content_height=100, content_width=400
                )
                self.__parent = parent
                content = self._init_content()
                self.set_child(content)

            def present(self):
                super(self.__class__, self).present(self.__parent)

            def _on_cancel(self, button):
                self.close()

            def _on_save_btn_clicked(self, button):
                source = self.current_path
                target = self.target_entry.get_text()

                if target == "":
                    return

                if source:
                    self.emit("saved", source, target)
                self.close()

        attrs["__init__"] = __init__
        attrs["_on_cancel"] = _on_cancel
        attrs["_on_save_btn_clicked"] = _on_save_btn_clicked
        attrs["present"] = present
        return super().__new__(mcs, name, bases, attrs)


class SharedFolderDialog(BASE_DIALOG, metaclass=DialogMeta):
    __gtype_name__ = "SharedFolderDialog"
    __gsignals__ = {
        "saved": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (
                str,
                str,
            ),
        ),
    }

    special_dirs = [
        GLib.UserDirectory.DIRECTORY_DOCUMENTS,
        GLib.UserDirectory.DIRECTORY_DOWNLOAD,
        GLib.UserDirectory.DIRECTORY_MUSIC,
        GLib.UserDirectory.DIRECTORY_PICTURES,
        GLib.UserDirectory.DIRECTORY_PUBLIC_SHARE,
        GLib.UserDirectory.DIRECTORY_VIDEOS,
        GLib.UserDirectory.DIRECTORY_DESKTOP,
    ]

    default_map = {
        GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_DOCUMENTS
        ): os.path.expanduser("~/.local/share/waydroid/data/media/0/Documents"),
        GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_DOWNLOAD
        ): os.path.expanduser("~/.local/share/waydroid/data/media/0/Download"),
        GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_MUSIC
        ): os.path.expanduser("~/.local/share/waydroid/data/media/0/Music"),
        GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_PICTURES
        ): os.path.expanduser("~/.local/share/waydroid/data/media/0/Pictures"),
        GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_VIDEOS
        ): os.path.expanduser("~/.local/share/waydroid/data/media/0/Movies"),
    }

    def __init__(self, parent):
        pass

    def _init_content(self):
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(12)

        source_label = Gtk.Label(label=_("Source"))
        source_label.set_halign(Gtk.Align.START)
        grid.attach(source_label, 0, 0, 1, 1)

        self.file_chooser_button = Adw.SplitButton()
        # FIXME
        connect_weakly(
            self.file_chooser_button, "clicked", self._on_file_chooser_clicked
        )
        # self.file_chooser_button.connect("clicked", self._on_file_chooser_clicked)

        self.current_path = GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_PUBLIC_SHARE
        )
        self.file_chooser_button.set_label(self.current_path)
        self.file_chooser_button.set_hexpand(True)
        grid.attach(self.file_chooser_button, 1, 0, 1, 1)

        target_label = Gtk.Label(label=_("Target"))
        target_label.set_halign(Gtk.Align.START)
        grid.attach(target_label, 0, 1, 1, 1)

        self.target_entry = Gtk.Entry()
        self.target_entry.set_placeholder_text(_("Target Directory"))
        self.target_entry.set_hexpand(True)
        grid.attach(self.target_entry, 1, 1, 1, 1)

        content.append(grid)

        menu = Gio.Menu()
        section = Gio.Menu()

        self.action_group = Gio.SimpleActionGroup()
        self.file_chooser_button.insert_action_group("folder", self.action_group)

        for i, dir_const in enumerate(self.special_dirs):
            path = GLib.get_user_special_dir(dir_const)
            if path:
                display_name = os.path.basename(path)
                section.append(display_name, f"folder.choose{i}")
                action = Gio.SimpleAction.new(f"choose{i}", None)
                # FIXME
                connect_weakly(action, "activate", self._on_directory_chosen, path)
                # action.connect("activate", self._on_directory_chosen, path)
                self.action_group.add_action(action)

        menu.append_section(None, section)
        self.file_chooser_button.set_menu_model(menu)

        # 按钮盒子保持原来的布局
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_homogeneous(True)
        button_box.set_margin_top(12)

        cancel_button = Gtk.Button(label=_("Cancel"))
        # FIXME
        connect_weakly(cancel_button, "clicked", self._on_cancel)
        # cancel_button.connect("clicked", self._on_cancel)

        save_button = Gtk.Button(label=_("Save"))
        save_button.add_css_class("suggested-action")
        # FIXME
        connect_weakly(save_button, "clicked", self._on_save_btn_clicked)
        # save_button.connect("clicked", self._on_save_btn_clicked)

        button_box.append(cancel_button)
        button_box.append(save_button)
        content.append(button_box)

        return content

    def present(self):
        pass

    def _on_cancel(self, button):
        pass

    def _on_save_btn_clicked(self, button):
        pass

    def _on_directory_chosen(self, action, parameter, path):
        self.current_path = path
        self.file_chooser_button.set_label(path)
        self._set_default_target(self.current_path)

    def _on_file_chooser_clicked(self, button):
        dialog = FileDialog(
            title=_("Select Folder"), modal=True, parent=self.get_root()
        )
        dialog.select_folder(self._on_folder_selected)

    def _on_folder_selected(self, success, path):
        if success and path:
            self.current_path = path
            self.file_chooser_button.set_label(path)
            self._set_default_target(self.current_path)

    def _set_default_target(self, source):
        if source in self.default_map:
            self.target_entry.set_text(self.default_map[source])
        else:
            self.target_entry.set_text("")
