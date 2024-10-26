from typing import Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


from gi.repository import Gtk, Adw, GLib, GObject

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION


BASE_DIALOG = Gtk.MessageDialog
if ADW_VERSION >= (1, 2, 0) and ADW_VERSION < (1, 5, 0):
    BASE_DIALOG = Adw.MessageDialog
elif ADW_VERSION >= (1, 5, 0):
    BASE_DIALOG = Adw.AlertDialog


class DialogMeta(type(GObject.Object)):
    def __new__(mcs, name, bases, attrs):
        # final class
        for base in bases:
            if isinstance(base, DialogMeta):
                raise TypeError("type '{0}' is not an acceptable base type".format(base.__name__))

        if BASE_DIALOG == Gtk.MessageDialog:
            def __init__(self, heading, body, parent, modal=True):
                super(self.__class__, self).__init__(
                    text=heading,
                    secondary_text=body,
                    transient_for=parent,
                    modal=modal,
                )
                self.__parent = parent
                self.connect_after(
                    "response", lambda w, r: super(self.__class__, self).destroy()
                )

            def add_response(self, id: Gtk.ResponseType, label: str):
                super(self.__class__, self).add_button(label, id)

            def set_response_appearance(self, id: Gtk.ResponseType, css_class: str):
                button = super(self.__class__, self).get_widget_for_response(id)
                button.add_css_class(css_class)

            def set_default_response(self, id: Gtk.ResponseType):
                super(self.__class__, self).set_default_response(id)

            def present(self):
                super(self.__class__, self).present()

        elif BASE_DIALOG == Adw.MessageDialog:

            def __init__(self, heading, body, parent, modal=True):
                super(self.__class__, self).__init__(transient_for=parent, modal=modal)
                self.set_heading(heading)
                self.set_body(body)
                self.__parent = parent

            def add_response(self, id: Gtk.ResponseType, label: str):
                super(self.__class__, self).add_response(id.value_nick, label)

            def set_response_appearance(self, id: Gtk.ResponseType, css_class: str):
                appearance_map = {
                    "destructive-action": Adw.ResponseAppearance.DESTRUCTIVE,
                    "suggested-action": Adw.ResponseAppearance.SUGGESTED,
                }
                super(self.__class__, self).set_response_appearance(
                    id.value_nick,
                    appearance_map.get(css_class, Adw.ResponseAppearance.DEFAULT),
                )

            def set_default_response(self, id: Gtk.ResponseType):
                super(self.__class__, self).set_default_response(id.value_nick)

            def present(self):
                super(self.__class__, self).present()

        else:  # Adw.AlertDialog

            def __init__(self, heading, body, parent, modal=True):
                super(self.__class__, self).__init__(heading=heading, body=body)
                self.__parent = parent

            def add_response(self, id: Gtk.ResponseType, label: str):
                super(self.__class__, self).add_response(id.value_nick, label)

            def set_response_appearance(self, id: Gtk.ResponseType, css_class: str):
                appearance_map = {
                    "destructive-action": Adw.ResponseAppearance.DESTRUCTIVE,
                    "suggested-action": Adw.ResponseAppearance.SUGGESTED,
                }
                super(self.__class__, self).set_response_appearance(
                    id.value_nick,
                    appearance_map.get(css_class, Adw.ResponseAppearance.DEFAULT),
                )

            def set_default_response(self, id: Gtk.ResponseType):
                super(self.__class__, self).set_default_response(id.value_nick)

            def present(self):
                super(self.__class__, self).present(self.__parent)

        attrs["__init__"] = __init__
        attrs["add_response"] = add_response
        attrs["set_response_appearance"] = set_response_appearance
        attrs["set_default_response"] = set_default_response
        attrs["present"] = present
        return super().__new__(mcs, name, bases, attrs)


class Dialog(BASE_DIALOG, metaclass=DialogMeta):
    def __init__(
        self, heading: str, body: str, parent: Optional[Gtk.Window], modal: bool = True
    ):
        pass

    def add_response(self, id: Gtk.ResponseType, label: str) -> None:
        pass

    def set_response_appearance(self, id: Gtk.ResponseType, css_class: str) -> None:
        pass

    def set_default_response(self, id: Gtk.ResponseType) -> None:
        pass

    def present(self) -> None:
        pass
