from functools import partial
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from waydroid_helper.util.ExtentionsManager import PackageManager
from waydroid_helper.util.SubprocessManager import SubprocessError
from waydroid_helper.util.Task import Task
from gi.repository import Gtk, Adw
from gettext import gettext as _


class Dialog(Adw.MessageDialog):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_heading(heading=kwargs["heading"])
        self.set_body(body=kwargs["body"])
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


@Gtk.Template(
    resource_path="/com/jaoushingan/WaydroidHelper/ui/AvailableVersionPage.ui"
)
class AvailableVersionPage(Adw.NavigationPage):
    __gtype_name__ = "AvailableVersionPage"
    extension_manager: PackageManager = ...
    _task = Task()
    page = Gtk.Template.Child()

    def __init__(self, ext_versions: dict, extension_manager):
        super().__init__(title=_("Available Versions"))
        self.extension_manager = extension_manager
        ext_versions = sorted(ext_versions, key=lambda x: x["version"], reverse=True)
        adw_preferences_group = Adw.PreferencesGroup.new()
        self.page.add(group=adw_preferences_group)

        for version in ext_versions:
            adw_action_row = Adw.ActionRow.new()
            adw_action_row.set_title(title=f'{version["name"]}-{version["version"]}')
            if version.get("description", "") != "":
                adw_action_row.set_subtitle(subtitle=_(version["description"]))
                adw_action_row.set_subtitle_selectable(True)
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

            if self.extension_manager.is_installed(version["name"]):
                delete_button = Gtk.Button.new()
                delete_button.set_valign(align=Gtk.Align.CENTER)
                delete_button.add_css_class("flat")
                delete_button.set_icon_name("edit-delete-symbolic")
                delete_button.connect(
                    "clicked",
                    partial(self.on_delete_button_clicked, name=version["name"]),
                )
                adw_action_row.add_suffix(delete_button)

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
                transient_for=self.get_root(),
            )

        else:
            dialog = Dialog(
                heading=_("Extension Installation"),
                body=_("Do you want to install") + " " + name,
                transient_for=self.get_root(),
            )

        def dialog_response(dialog, response):
            if response == Gtk.ResponseType.OK.value_nick:
                self._task.create_task(self.__install(name, version))

        dialog.connect("response", dialog_response)
        dialog.present()

    def on_delete_button_clicked(self, button: Gtk.Button, name):
        dialog = Dialog(
            heading=_("Uninstall Confirmation"),
            body=_("Do you want to uninstall") + " " + name,
            transient_for=self.get_root(),
        )

        def dialog_response(dialog, response):
            if response == Gtk.ResponseType.OK.value_nick:
                self._task.create_task(self.__uninstall(name))

        dialog.connect("response", dialog_response)
        dialog.present()
