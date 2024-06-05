from gettext import gettext as _
from gi.repository import Gtk, GObject, Adw, GLib, Gdk
from functools import partial
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

        # style_context = self.get_style_context()
        # c1, c2 = style_context.lookup_color("accent_bg_color"),style_context.lookup_color("window_bg_color")

        # window_bg_color =c2[1] if c2[0] else Gdk.RGBA()
        # if color[0]:
        #     theme_color = color[1].to_string()
        # else:
        #     print("没找到")
        #     theme_color = "rgba(255, 255, 255, 1)"

        # print(theme_color)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(
            " .info { background-color: mix(@accent_bg_color, @window_bg_color, 0.3); } "
        )

        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
