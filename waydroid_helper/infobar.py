from gettext import gettext as _
from gi.repository import Gtk
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


@Gtk.Template(resource_path="/com/jaoushingan/WaydroidHelper/ui/InfoBar.ui")
class InfoBar(Gtk.Revealer):
    __gtype_name__ = "InfoBar"
    label: Gtk.Label = Gtk.Template.Child()
    cancel_button: Gtk.Button = Gtk.Template.Child()
    ok_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, label=None, cancel_callback=None, ok_callback=None):
        super().__init__()
        self.label.set_text(label)
        self.cancel_button.connect("clicked", cancel_callback)
        self.ok_button.connect("clicked", ok_callback)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(
            " .info { background-color: mix(@accent_bg_color, @window_bg_color, 0.3); } "
        )

        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
