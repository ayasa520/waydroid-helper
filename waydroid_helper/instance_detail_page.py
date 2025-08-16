# pyright: reportCallIssue=false
# pyright: reportUnknownVariableType=false
# pyright: reportAny=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

from gettext import gettext as _
from typing import cast

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, GObject, Gtk

from waydroid_helper.controller import TransparentWindow
from waydroid_helper.infobar import InfoBar
from waydroid_helper.shared_folder import SharedFoldersWidget
from waydroid_helper.util import Task, logger, template
from waydroid_helper.waydroid import Waydroid, WaydroidState
from waydroid_helper.compat_widget import NavigationPage, HeaderBar, ToolbarView


class InstanceDetailPage(NavigationPage):
    __gtype_name__: str = "InstanceDetailPage"

    def __init__(self, waydroid: Waydroid, navigation_view, props_page, extensions_page, **kwargs):
        super().__init__(title="Instance Details", **kwargs)

        self.waydroid = waydroid
        self._navigation_view = navigation_view
        self._props_page = props_page
        self._extensions_page = extensions_page
        self._task: Task = Task()
        self._key_mapping_window: TransparentWindow | None = None
        self._app: Gtk.Application | None = None

        # Create main content
        self._create_content()

        # Connect to waydroid state changes to update key mapping buttons
        self.waydroid.connect("notify::state", self._on_waydroid_state_changed)
        
    def _create_content(self):
        # Create toolbar view
        toolbar_view = ToolbarView.new()
        
        # Create header bar
        header_bar = HeaderBar()
        toolbar_view.add_top_bar(header_bar)
        
        # Create view stack for tabs
        self.view_stack = Adw.ViewStack.new()
        
        # Create details tab (共享文件夹和按键映射)
        details_tab = self._create_details_tab()
        details_page = self.view_stack.add_titled(details_tab, "details", _("Details"))
        details_page.set_icon_name("info-symbolic")

        # Use existing settings tab
        settings_page = self.view_stack.add_titled(self._props_page, "settings", _("Settings"))
        settings_page.set_icon_name("system-symbolic")

        # Use existing extensions tab
        extensions_page = self.view_stack.add_titled(self._extensions_page, "extensions", _("Extensions"))
        extensions_page.set_icon_name("addon-symbolic")
        
        # Create view switcher
        view_switcher = Adw.ViewSwitcher.new()
        view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        view_switcher.set_stack(self.view_stack)
        header_bar.set_title_widget(view_switcher)
        
        # Create view switcher bar for narrow screens
        view_switcher_bar = Adw.ViewSwitcherBar.new()
        view_switcher_bar.set_stack(self.view_stack)
        toolbar_view.add_bottom_bar(view_switcher_bar)
        
        toolbar_view.set_content(self.view_stack)
        self.set_child(toolbar_view)
        
    def _create_details_tab(self):
        """创建详情标签页，包含共享文件夹和按键映射"""
        box = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Create preferences page
        prefs_page = Adw.PreferencesPage.new()
        
        # 共享文件夹组
        shared_folders_widget = SharedFoldersWidget()
        prefs_page.add(shared_folders_widget)
        
        # 按键映射组
        key_mapping_group = self._create_key_mapping_group()
        prefs_page.add(key_mapping_group)
        
        self.infobar: InfoBar = InfoBar(
            label=_("Restart the systemd user service immediately"),
            ok_callback=lambda *_: shared_folders_widget.restart_service(),
        )
        shared_folders_widget.connect(
            "updated", lambda _: self.infobar.set_reveal_child(True)
        )

        box.append(prefs_page)
        box.append(self.infobar)
        
        return box
        
    def _create_key_mapping_group(self):
        """创建按键映射组"""
        group = Adw.PreferencesGroup.new()
        group.set_title(_("Key Mapper"))
        
        # 按键映射行
        key_mapping_row = Adw.ActionRow.new()
        key_mapping_row.set_title(_("Key Mapping Window"))
        key_mapping_row.set_subtitle(_("Manage key mapping overlay window for game control"))
        
        # 按钮容器
        button_box = Gtk.Box.new(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # 打开按钮
        self.open_key_mapping_button = Gtk.Button.new_with_label(_("Open"))
        self.open_key_mapping_button.set_sensitive(False)
        self.open_key_mapping_button.add_css_class("suggested-action")
        self.open_key_mapping_button.connect("clicked", self.on_open_key_mapping_clicked)
        button_box.append(self.open_key_mapping_button)
        
        # 关闭按钮
        self.close_key_mapping_button = Gtk.Button.new_with_label(_("Close"))
        self.close_key_mapping_button.set_sensitive(False)
        self.close_key_mapping_button.add_css_class("destructive-action")
        self.close_key_mapping_button.connect("clicked", self.on_close_key_mapping_clicked)
        button_box.append(self.close_key_mapping_button)
        
        key_mapping_row.add_suffix(button_box)
        group.add(key_mapping_row)
        
        return group
        
    def set_app(self, app: Gtk.Application):
        """设置应用实例"""
        self._app = app
        # 初始化按键映射按钮状态
        self._update_key_mapping_buttons()

    def _on_waydroid_state_changed(self, w, param):
        """Waydroid状态变化时更新按键映射按钮"""
        self._update_key_mapping_buttons()
        
    def _update_key_mapping_buttons(self):
        """Update key mapping buttons status"""
        try:
            if self._key_mapping_window and self._key_mapping_window.is_visible():
                self.open_key_mapping_button.set_sensitive(False)
                self.close_key_mapping_button.set_sensitive(True)
            else:
                self.open_key_mapping_button.set_sensitive(True)
                self.close_key_mapping_button.set_sensitive(False)
        except Exception as e:
            logger.error(f"Update key mapping buttons status failed: {e}")
            # Set to default state when error occurs
            self.open_key_mapping_button.set_sensitive(True)
            self.close_key_mapping_button.set_sensitive(False)

    def on_open_key_mapping_clicked(self, button: Gtk.Button):
        """Open key mapping window"""
        logger.info("Open key mapping window")
        try:
            if self._app:
                # Create key mapping window
                self._key_mapping_window = TransparentWindow(self._app)
                # Listen for window close event
                self._key_mapping_window.connect("close-request", self._on_key_mapping_window_closed)
                self._key_mapping_window.present()
                # Update button status
                self._update_key_mapping_buttons()
                logger.info("Key mapping window opened")
                
                # Minimize the main window
                root = self.get_root()
                root = cast(Gtk.ApplicationWindow, root)
                if root and hasattr(root, 'minimize'):
                    root.minimize()
                    logger.info("Main window minimized")
            else:
                logger.error("Cannot get application instance")
        except Exception as e:
            logger.error(f"Open key mapping window failed: {e}")

    def _on_key_mapping_window_closed(self, window):
        """Callback when key mapping window is closed"""
        logger.info("Key mapping window closed")
        self._key_mapping_window = None
        self._update_key_mapping_buttons()
        return False  # Allow window to close

    def on_close_key_mapping_clicked(self, button: Gtk.Button):
        """Close key mapping window"""
        logger.info("Close key mapping window")
        try:
            if self._key_mapping_window:
                self._key_mapping_window.close()
                # No need to set to None here, close-request will trigger callback
                logger.info("Key mapping window close request sent")
            else:
                logger.warning("No open key mapping window")
        except Exception as e:
            logger.error(f"Close key mapping window failed: {e}")
            # Manually clean up on error
            self._key_mapping_window = None
            self._update_key_mapping_buttons()
