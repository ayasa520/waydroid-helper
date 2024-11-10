from enum import IntEnum
import os
import re
import gi
import aiofiles
import asyncio

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject, GLib
from waydroid_helper.util import SubprocessManager, logger
from waydroid_helper.compat_widget import FileDialog
from gettext import gettext as _


class SharedFolder(GObject.Object):
    def __init__(self, source, target):
        super().__init__()
        self.source = source
        self.target = target


class SharedFolderRow(Adw.ActionRow):
    __gsignals__ = {"removed": (GObject.SignalFlags.RUN_FIRST, None, (SharedFolder,))}

    def __init__(self, folder: SharedFolder):
        super().__init__()

        self.folder = folder
        self.set_title(folder.source)
        self.set_subtitle(folder.target)

        button = Gtk.Button(icon_name="user-trash-symbolic")
        button.add_css_class("flat")
        button.connect("clicked", self._on_delete_button_clicked)
        self.add_suffix(button)

    def _on_delete_button_clicked(self, button):
        self.emit("removed", self.folder)


class SharedFolderPopover(Gtk.Popover):
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

    def __init__(self):
        super().__init__()
        self.set_autohide(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(12)

        source_label = Gtk.Label(label=_("Source"))
        source_label.set_halign(Gtk.Align.START)
        grid.attach(source_label, 0, 0, 1, 1)

        self.file_chooser_button = Adw.SplitButton()
        self.file_chooser_button.connect("clicked", self._on_file_chooser_clicked)
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

        box.append(grid)

        menu = Gio.Menu()
        section = Gio.Menu()

        special_dirs = [
            GLib.UserDirectory.DIRECTORY_DOCUMENTS,
            GLib.UserDirectory.DIRECTORY_DOWNLOAD,
            GLib.UserDirectory.DIRECTORY_MUSIC,
            GLib.UserDirectory.DIRECTORY_PICTURES,
            GLib.UserDirectory.DIRECTORY_PUBLIC_SHARE,
            GLib.UserDirectory.DIRECTORY_VIDEOS,
            GLib.UserDirectory.DIRECTORY_DESKTOP,
        ]

        self.action_group = Gio.SimpleActionGroup()
        self.file_chooser_button.insert_action_group("folder", self.action_group)

        for i, dir_const in enumerate(special_dirs):
            path = GLib.get_user_special_dir(dir_const)
            if path:
                display_name = os.path.basename(path)
                section.append(display_name, f"folder.choose{i}")
                action = Gio.SimpleAction.new(f"choose{i}", None)
                action.connect("activate", self._on_directory_chosen, path)
                self.action_group.add_action(action)

        menu.append_section(None, section)
        self.file_chooser_button.set_menu_model(menu)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_homogeneous(True)

        cancel_button = Gtk.Button(label=_("Cancel"))
        cancel_button.connect("clicked", self._on_cancel)

        save_button = Gtk.Button(label=_("Save"))
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save_btn_clicked)

        button_box.append(cancel_button)
        button_box.append(save_button)
        box.append(button_box)

        self.set_child(box)
        self.default_map = {
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

    def _on_cancel(self, button):
        self.popdown()

    def _on_save_btn_clicked(self, button):
        source = self.current_path
        target = self.target_entry.get_text()

        if target == "":
            return

        if source:
            self.emit("saved", source, target)
        self.popdown()


class SharedFoldersState(IntEnum):
    UNINITIALIZED = 0
    INITIALIZED = 1


class SharedFoldersWidget(Adw.PreferencesGroup):
    __gtype_name__ = "SharedFoldersWidget"
    __gsignals__ = {"updated": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self):
        super().__init__()
        self.state = SharedFoldersState.UNINITIALIZED
        self.set_title(_("Shared Folders"))
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.add_css_class("boxed-list")
        self.add(self.listbox)

        self.popover = SharedFolderPopover()
        self.popover.connect("saved", self._on_popover_saved)

        self.add_button = Gtk.MenuButton()
        self.add_button.set_icon_name("list-add-symbolic")
        self.add_button.add_css_class("flat")
        self.add_button.set_popover(self.popover)

        self.list_store = Gio.ListStore.new(SharedFolder)
        self.list_store.connect("items-changed", self._on_list_updated)

        self.listbox.bind_model(self.list_store, self._create_shared_folder_row)

        self.listbox.append(self.add_button)
        asyncio.create_task(self.read_drop_file())
        self._subprocess = SubprocessManager()

    async def read_drop_file(self):
        service_name = "waydroid-monitor.service"
        drop_in_dir = os.path.expanduser(f"~/.config/systemd/user/{service_name}.d")
        drop_in_file = os.path.join(drop_in_dir, "override.conf")
        sources = []
        targets = []

        def extract_env_var(env_string, var_name):
            pattern = rf'Environment="{var_name}=(.*?)"'
            match = re.search(pattern, env_string)
            if match:
                return match.group(1)
            return None

        if os.path.exists(drop_in_file):
            async with aiofiles.open(drop_in_file) as f:
                content = await f.read()
                source_str = extract_env_var(content, "SOURCE")
                target_str = extract_env_var(content, "TARGET")
                if source_str and target_str:
                    sources.extend(source_str.split(":"))
                    targets.extend(target_str.split(":"))

        for s, t in zip(sources, targets):
            item = SharedFolder(s, t)
            self.list_store.append(item)
        self._on_list_updated(None, 0, 0, 0)
        self.state = SharedFoldersState.INITIALIZED

    async def write_drop_file(self):
        service_name = "waydroid-monitor.service"
        drop_in_dir = os.path.expanduser(f"~/.config/systemd/user/{service_name}.d")
        os.makedirs(drop_in_dir, exist_ok=True)
        drop_in_file = os.path.join(drop_in_dir, "override.conf")
        contents = ["[Service]"]
        sources = []
        targets = []

        for i in range(self.list_store.get_n_items()):
            item = self.list_store.get_item(i)
            sources.append(os.path.expanduser(item.source))
            targets.append(os.path.expanduser(item.target))
        contents.append(f"Environment=\"SOURCE={':'.join(sources)}\"")
        contents.append(f"Environment=\"TARGET={':'.join(targets)}\"")

        async with aiofiles.open(drop_in_file, "w") as file:
            await file.write("\n".join(contents))

        self.emit("updated")

    def restart_service(self):
        async def _restart_service():
            try:
                await self._subprocess.run("systemctl --user daemon-reload")
                await self._subprocess.run(
                    "systemctl --user restart waydroid-monitor.service"
                )
            except Exception as e:
                logger.error(e)

        asyncio.create_task(_restart_service())

    def _create_shared_folder_row(self, item):
        row = SharedFolderRow(item)
        row.connect("removed", self._on_folder_removed)
        return row

    def _on_popover_saved(self, popover, source, target):
        folder = SharedFolder(source, target)
        self.list_store.append(folder)
        return True

    def _on_folder_removed(self, row, folder):
        for i in range(self.list_store.get_n_items()):
            item = self.list_store.get_item(i)
            if item.source == folder.source and item.target == folder.target:
                self.list_store.remove(i)
                break

    def _on_list_updated(self, model, position=0, removed=0, added=0):
        if self.state == SharedFoldersState.INITIALIZED:
            asyncio.create_task(self.write_drop_file())
        if self.list_store.get_n_items() == 0:
            self.set_description(
                _(
                    "Use the button below to add your first shared folder. "
                    "For file sharing to work, you need to have "
                    "<a href='https://bindfs.org/'>bindfs</a> installed."
                )
            )
        else:
            self.set_description(None)
