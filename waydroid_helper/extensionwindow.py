from functools import partial
import gi
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from waydroid_helper.util.ExtentionsManager import PackageManager
from waydroid_helper.util.SubprocessManager import SubprocessError
from waydroid_helper.util.Task import Task
from gi.repository import Gtk, Adw
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


class Dialog(BASE_DIALOG):
    def __init__(self, heading, body, parent):
        self.parent_window = parent
        if MESSAGE_DIALOG == "AdwMessageDialog":
            super().__init__(transient_for=parent)
            self.set_heading(heading=heading)
            self.set_body(body=body)
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

            self.add_response(Gtk.ResponseType.CANCEL.value_nick, _("Cancel"))
            self.set_response_appearance(
                Gtk.ResponseType.CANCEL.value_nick, Adw.ResponseAppearance.DESTRUCTIVE
            )
            self.add_response(Gtk.ResponseType.OK.value_nick, _("OK"))
            self.set_default_response(Gtk.ResponseType.OK.value_nick)
            self.set_response_appearance(
                Gtk.ResponseType.OK.value_nick, Adw.ResponseAppearance.SUGGESTED
            )

    def show(self):
        if MESSAGE_DIALOG != "AdwAlertDialog":
            self.present()
        else:
            self.present(self.parent_window)


@Gtk.Template(resource_path=RESOURCE_PATH)
class AvailableVersionPage(BASE_PAGE):
    __gtype_name__ = "AvailableVersionPage"
    extension_manager: PackageManager = ...
    _task = Task()
    page = Gtk.Template.Child()

    # AdwLeafletView
    if NAVIGATION_PAGE=='AdwLeafletPage':
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

        for version in ext_versions:
            adw_action_row = Adw.ActionRow.new()
            adw_action_row.set_title(title=f'{version["name"]}-{version["version"]}')
            # if version.get("description", "") != "":
            #     adw_action_row.set_subtitle(subtitle=_(version["description"]))
            #     adw_action_row.set_subtitle_selectable(True)
            adw_preferences_group.add(child=adw_action_row)

            install_button = Gtk.Button.new()
            install_button.set_valign(align=Gtk.Align.CENTER)
            install_button.add_css_class("flat")
            install_button.set_icon_name("document-save-symbolic")
            install_button.connect(
                "clicked",
                partial(
                    self.on_install_button_clicked,
                    name=version["name"],
                    version=version["version"],
                ),
            )
            adw_action_row.add_suffix(install_button)

            if self.extension_manager.is_installed(version["name"], version["version"]):
                delete_button = Gtk.Button.new()
                delete_button.set_valign(align=Gtk.Align.CENTER)
                delete_button.add_css_class("flat")
                delete_button.set_icon_name("edit-delete-symbolic")
                delete_button.connect(
                    "clicked",
                    partial(self.on_delete_button_clicked, name=version["name"]),
                )
                adw_action_row.add_suffix(delete_button)
            if NAVIGATION_PAGE == "AdwLeafletPage":
                self.back_button.connect("clicked", self.on_back_clicked)

    async def __install(self, name, version):
        try:
            await self.extension_manager.install_package(
                name=name, version=version, remove_conflicts=True
            )
        except SubprocessError as e:
            print(e)

    async def __uninstall(self, name):
        try:
            await self.extension_manager.remove_package(name)
        except SubprocessError as e:
            print(e)

    def on_install_button_clicked(self, button: Gtk.Button, name, version):
        conflicts = self.extension_manager.check_conflicts(name=name, version=version)
        if len(conflicts) != 0:
            dialog = Dialog(
                heading=_("Extension Conflict"),
                body=_("Do you want to uninstall the conflicting extensions")
                + " "
                + ", ".join(conflicts),
                parent=self.get_root(),
            )

        else:
            dialog = Dialog(
                heading=_("Extension Installation"),
                body=_("Do you want to install") + " " + name,
                parent=self.get_root(),
            )

        def dialog_response(dialog, response):
            if (
                response == Gtk.ResponseType.OK.value_nick
                or response == Gtk.ResponseType.OK
            ):
                self._task.create_task(self.__install(name, version))
            if MESSAGE_DIALOG == "GtkMessageDialog":
                dialog.close()

        dialog.connect("response", dialog_response)
        dialog.show()

    def on_delete_button_clicked(self, button: Gtk.Button, name):
        dialog = Dialog(
            heading=_("Uninstall Confirmation"),
            body=_("Do you want to uninstall") + " " + name,
            parent=self.get_root(),
        )

        def dialog_response(dialog, response):
            if (
                response == Gtk.ResponseType.OK.value_nick
                or response == Gtk.ResponseType.OK
            ):
                self._task.create_task(self.__uninstall(name))
            if MESSAGE_DIALOG == "GtkMessageDialog":
                dialog.close()

        dialog.connect("response", dialog_response)
        dialog.show()

    def on_back_clicked(self, button):
        """
        AdwLeafletPage
        """
        self.get_root().navigate_back()
