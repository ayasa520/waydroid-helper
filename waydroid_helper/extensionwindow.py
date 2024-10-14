import asyncio
from enum import IntEnum
from functools import partial
import math
import gi
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from waydroid_helper.util.ExtentionsManager import PackageManager
from waydroid_helper.util.SubprocessManager import SubprocessError
from waydroid_helper.util.Task import Task
from gi.repository import Gtk, Adw, Gdk
from gettext import gettext as _

adw_version = os.environ.get("adw_version")
gtk_version = os.environ.get("gtk_version")

MESSAGE_DIALOG = "GtkMessageDialog"
BASE_DIALOG = Gtk.MessageDialog
if adw_version >= "10200" and adw_version < "10600":
    MESSAGE_DIALOG = "AdwMessageDialog"
    BASE_DIALOG = Adw.MessageDialog
elif adw_version >= "10600":
    MESSAGE_DIALOG = "AdwAlertDialog"
    BASE_DIALOG = Adw.AlertDialog

if adw_version >= "10400":
    NAVIGATION_PAGE = "AdwNavigationPage"
    BASE_PAGE = Adw.NavigationPage
    RESOURCE_PATH = "/com/jaoushingan/WaydroidHelper/ui/AvailableVersionPage.ui"
else:
    NAVIGATION_PAGE = "AdwLeafletPage"
    BASE_PAGE = Gtk.Box
    RESOURCE_PATH = "/com/jaoushingan/WaydroidHelper/ui/AvailableVersionPage_old.ui"


class AvailableRow(Adw.ActionRow):
    class State(IntEnum):
        UNINSTALLED = 0
        INSTALLING = 1
        INSTALLED = 2

    def __init__(self, name, version, installed):
        super().__init__()
        self.set_title(title=f"{name}-{version}")
        # if version.get("description", "") != "":
        #     adw_action_row.set_subtitle(subtitle=_(version["description"]))
        #     adw_action_row.set_subtitle_selectable(True)
        self.delete_button = Gtk.Button.new()
        self.delete_button.set_valign(align=Gtk.Align.CENTER)
        # self.delete_button.add_css_class("flat")
        self.delete_button.set_icon_name("edit-delete-symbolic")
        self.delete_button.add_css_class("destructive-action")
        self.add_suffix(self.delete_button)
        self.install_button = Gtk.Button.new()
        self.install_button.add_css_class("suggested-action")
        self.install_button.set_valign(align=Gtk.Align.CENTER)
        # self. install_button.add_css_class("flat")
        self.install_button.set_icon_name("software-install-symbolic")
        self.add_suffix(self.install_button)
        self.spinner = Adw.Spinner()
        self.add_suffix(self.spinner)
        # w = self.install_button.get_size(0)
        self.spinner.set_size_request(32,32)

        if installed:
            self.set_installation_state(self.State.INSTALLED)
        else:
            self.set_installation_state(self.State.UNINSTALLED)

    def set_installation_state(self, state):
        if state == self.State.INSTALLED:
            self.install_button.hide()
            self.delete_button.show()
            self.spinner.hide()
        elif state == self.State.UNINSTALLED:
            self.install_button.show()
            self.delete_button.hide()
            self.spinner.hide()
        elif state == self.State.INSTALLING:
            self.install_button.hide()
            self.delete_button.hide()
            self.spinner.show()


class CircularProgressBar(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.fraction = 0.0
        self.set_content_width(40)
        self.set_content_height(40)
        self.set_draw_func(self.draw)
        self.accent_color: Gdk.RGBA = None

    def __init_accent_color(self):
        if adw_version >= "10600":

            def on_accent_color_changed(style_manager):
                accent_color = self.style_manager.get_accent_color()
                self.accent_color = accent_color.to_rgba(accent_color)
                self.queue_draw()

            self.style_manager = self.get_root().get_application().get_style_manager()
            on_accent_color_changed(None, None)
            self.style_manager.connect("notify::accent-color", on_accent_color_changed)
        else:
            style_context = self.get_style_context()
            self.accent_color = style_context.lookup_color("accent_bg_color")[1]

    def set_fraction(self, fraction):
        self.fraction = fraction
        self.queue_draw()

    def draw(self, area, cr, width, height):
        if self.accent_color is None:
            self.__init_accent_color()

        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 5

        cr.set_line_width(4)
        cr.set_source_rgb(0.8, 0.8, 0.8)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.stroke()

        Gdk.cairo_set_source_rgba(cr, self.accent_color)
        cr.arc(
            center_x,
            center_y,
            radius,
            -math.pi / 2,
            (2 * self.fraction - 0.5) * math.pi,
        )
        cr.stroke()


class Dialog(BASE_DIALOG):
    def __init__(self, heading, body, parent, with_cancel=True):
        self.parent_window = parent
        if MESSAGE_DIALOG == "AdwMessageDialog":
            super().__init__(transient_for=parent)
            self.set_heading(heading=heading)
            self.set_body(body=body)
            if with_cancel:
                self.add_response(Gtk.ResponseType.CANCEL.value_nick, _("Cancel"))
                self.set_response_appearance(
                    response=Gtk.ResponseType.CANCEL.value_nick,
                    appearance=Adw.ResponseAppearance.DESTRUCTIVE,
                )
            self.add_response(Gtk.ResponseType.OK.value_nick, _("OK"))
            self.set_response_appearance(
                response=Gtk.ResponseType.OK.value_nick,
                appearance=Adw.ResponseAppearance.SUGGESTED,
            )
        elif MESSAGE_DIALOG == "GtkMessageDialog":
            super().__init__(
                text=heading,
                modal=True,
                secondary_text=body,
                transient_for=parent,
            )
            if with_cancel:
                self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
                cancel_button = self.get_widget_for_response(Gtk.ResponseType.CANCEL)
                cancel_button.add_css_class("destructive-action")
            self.add_button(_("OK"), Gtk.ResponseType.OK)
            ok_button = self.get_widget_for_response(Gtk.ResponseType.OK)
            ok_button.add_css_class("suggested-action")
            self.set_default_response(Gtk.ResponseType.OK)
        else:
            super().__init__()
            self.set_heading(heading)
            self.set_body(body)

            if with_cancel:
                self.add_response(Gtk.ResponseType.CANCEL.value_nick, _("Cancel"))
                self.set_response_appearance(
                    Gtk.ResponseType.CANCEL.value_nick,
                    Adw.ResponseAppearance.DESTRUCTIVE,
                )
            self.add_response(Gtk.ResponseType.OK.value_nick, _("OK"))
            self.set_default_response(Gtk.ResponseType.OK.value_nick)
            self.set_response_appearance(
                Gtk.ResponseType.OK.value_nick, Adw.ResponseAppearance.SUGGESTED
            )

    def close(self):
        if MESSAGE_DIALOG == "GtkMessageDialog":
            super().close()

    def show(self):
        if MESSAGE_DIALOG != "AdwAlertDialog":
            self.present()
        else:
            self.present(self.parent_window)


"""
AdwNavigationView：
若直接 push 而没有 add, 在 pop 之后页面会自动销毁。
但是如果 AdwNavigationPage 的派生类中信号连接了回调函数，则不会自动销毁，必须要手动解除后才会被销毁
"""


@Gtk.Template(resource_path=RESOURCE_PATH)
class AvailableVersionPage(BASE_PAGE):
    __gtype_name__ = "AvailableVersionPage"
    extension_manager: PackageManager = ...
    _task = Task()
    page = Gtk.Template.Child()

    # AdwLeafletView
    if NAVIGATION_PAGE == "AdwLeafletPage":
        back_button = Gtk.Template.Child()

    def __init__(self, ext_versions: dict, extension_manager):
        if NAVIGATION_PAGE == "AdwNavigationPage":
            super().__init__(title=_("Available Versions"))
        else:
            super().__init__()
        self.extension_manager = extension_manager
        ext_versions = sorted(ext_versions, key=lambda x: x["version"], reverse=True)
        adw_preferences_group = Adw.PreferencesGroup.new()
        self.page.add(group=adw_preferences_group)
        self.rows: dict[str, AvailableRow] = {}
        self.lock = asyncio.Lock()

        for version in ext_versions:
            installed = self.extension_manager.is_installed(
                version["name"], version["version"]
            )
            adw_action_row = AvailableRow(
                version["name"], version["version"], installed
            )
            adw_action_row.delete_button.connect(
                "clicked",
                partial(
                    self.on_delete_button_clicked,
                    name=version["name"],
                    version=version["version"],
                ),
            )
            adw_action_row.install_button.connect(
                "clicked",
                partial(
                    self.on_install_button_clicked,
                    name=version["name"],
                    version=version["version"],
                ),
            )
            adw_preferences_group.add(child=adw_action_row)
            self.rows[f"{version['name']}-{version['version']}"] = adw_action_row

        if NAVIGATION_PAGE == "AdwLeafletPage":
            self.back_button.connect("clicked", self.on_back_clicked)

    def on_installation_started(self, obj, name, version):
        pass
        # self.rows[f"{name}-{version}"].set_installation_state(
        #     AvailableRow.State.INSTALLING
        # )

    def on_installation_completed(self, obj, name, version):
        self.rows[f"{name}-{version}"].set_installation_state(
            AvailableRow.State.INSTALLED
        )
        dialog = Dialog(
            _("Installation Complete"),
            _(f"{name}-{version} has been successfully installed."),
            self.get_root(),
            False,
        )
        dialog.show()

    def on_uninstallation_completed(self, obj, name, version):
        self.rows[f"{name}-{version}"].set_installation_state(
            AvailableRow.State.UNINSTALLED
        )
        dialog = Dialog(
            _("Uninstallation Complete"),
            _(f"{name}-{version} has been successfully uninstalled."),
            self.get_root(),
            False,
        )
        dialog.show()

    async def show_dialog(self, title, body):
        dialog = Dialog(
            heading=title,
            body=body,
            parent=self.get_root(),
        )
        # 使用 asyncio.Future 等待用户响应
        future = asyncio.Future()

        def on_response(dialog, response):
            if (
                response == Gtk.ResponseType.OK.value_nick
                or response == Gtk.ResponseType.OK
            ):
                future.set_result(True)
            else:
                future.set_result(False)
            dialog.close()

        dialog.connect("response", on_response)
        dialog.show()

        return await future

    async def __install(self, name, version):
        installation_successful = False
        try:
            # Spinner
            self.rows[f"{name}-{version}"].set_installation_state(
                AvailableRow.State.INSTALLING
            )
            async with self.lock:
                conflicts = self.extension_manager.check_conflicts(
                    name=name, version=version
                )
                if await self.show_dialog(
                    _("Extension Installation"),
                    _("Do you want to install") + " " + name,
                ):
                    if conflicts:
                        if await self.show_dialog(
                            _("Extension Conflict"),
                            _("Do you want to uninstall the conflicting extensions")
                            + " "
                            + ",".join(conflicts),
                        ):
                            await self.extension_manager.remove_packages(conflicts)
                        else:
                            return
                    await self.extension_manager.install_package(
                        name=name, version=version
                    )
                    installation_successful = True
        except SubprocessError as e:
            print(e)
        finally:
            if not installation_successful:
                self.rows[f"{name}-{version}"].set_installation_state(
                    AvailableRow.State.UNINSTALLED
                )

    async def __uninstall(self, name, version):
        try:
            if await self.show_dialog(
                _("Uninstall Confirmation"),
                _("Do you want to uninstall") + " " + name,
            ):
                await self.extension_manager.remove_package(name)
        except SubprocessError as e:
            self.rows[f"{name}-{version}"].set_installation_state(
                AvailableRow.State.INSTALLED
            )
            print(e)

    def on_install_button_clicked(self, button: Gtk.Button, name, version):
        self._task.create_task(self.__install(name, version))

    def on_delete_button_clicked(self, button: Gtk.Button, name, version):
        self._task.create_task(self.__uninstall(name, version))

    def on_back_clicked(self, button):
        """
        AdwLeafletPage
        """
        self.get_root().navigate_back()

    def set_tag(self, tag: str):
        if NAVIGATION_PAGE == "AdwNavigationPage":
            super().set_tag(tag)
