from enum import IntEnum
import os
import re
import gi
import aiofiles
import asyncio


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject
from waydroid_helper.util import SubprocessManager, logger, SubprocessError
from waydroid_helper.compat_widget import SharedFolderDialog
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

        self.add_button = Gtk.Button()
        self.add_button.set_icon_name("list-add-symbolic")
        self.add_button.add_css_class("flat")
        self.add_button.connect("clicked", self._on_add_button_clicked)

        self.list_store = Gio.ListStore.new(SharedFolder)
        self.list_store.connect("items-changed", self._on_list_updated)

        self.listbox.bind_model(self.list_store, self._create_shared_folder_row)

        self.listbox.append(self.add_button)
        asyncio.create_task(self.read_drop_file())
        self._subprocess = SubprocessManager()

    def _on_add_button_clicked(self, button):
        self.dialog = SharedFolderDialog(parent=self.get_root())
        self.dialog.connect("saved", self._on_dialog_saved)
        self.dialog.present()

    def _on_dialog_saved(self, dialog, source, target):
        folder = SharedFolder(source, target)
        self.list_store.append(folder)
        return True

    async def read_drop_file(self):
        monitor_service_name = "waydroid-monitor.service"
        mount_service_name = "waydroid-mount.service"
        try:
            await self._subprocess.run(f"systemctl --user list-unit-files {monitor_service_name}")
            await self._subprocess.run(f"systemctl list-unit-files {mount_service_name}")
        except Exception:
            logger.error(f"{monitor_service_name} or {monitor_service_name} not exists!")
            self.hide()
            return

        drop_in_dir = os.path.expanduser(f"~/.config/systemd/user/{monitor_service_name}.d")
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
