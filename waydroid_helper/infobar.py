# pyright: reportUnknownArgumentType=false
from typing import Callable
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk
from waydroid_helper.util import template


@template(resource_path="/com/jaoushingan/WaydroidHelper/ui/InfoBar.ui")
class InfoBar(Gtk.Revealer):
    __gtype_name__: str = "InfoBar"
    label: Gtk.Label = Gtk.Template.Child()
    cancel_button: Gtk.Button = Gtk.Template.Child()
    ok_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, label: str, cancel_callback:Callable[[Gtk.Button],None]|None=None, ok_callback:Callable[[Gtk.Button],None]|None=None):
        super().__init__()
        self.label.set_text(label)
        if cancel_callback:
            self.cancel_button.connect("clicked", cancel_callback)
        if ok_callback:
            self.ok_button.connect("clicked", ok_callback)

        self.cancel_button.connect_after(
            "clicked", lambda _: self.default_callback(self, False)
        )
        self.ok_button.connect_after(
            "clicked", lambda _: self.default_callback(self, False)
        )

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(  # pyright:ignore[reportUnknownMemberType]
            " .info { background-color: mix(@accent_bg_color, @window_bg_color, 0.3); } "
        )

        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def default_callback(self, widget: Gtk.Revealer, reveal: bool):
        widget.set_reveal_child(reveal)