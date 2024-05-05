from gi.repository import Gtk, Gdk, Adw, GObject


class ControllerWindow(Adw.Window):
    def __init__(self, **kargs):
        grab: GObject.Property = GObject.Property(default=True, type=bool)
        super().__init__(**kargs)
        # instance.set_name, class.set_css_name
        self.set_name("controller_window")

        self.set_size_request(800, 600)
        vbox = Gtk.Box.new(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_content(vbox)
        vbox.set_name("vbox")
        vbox.set_hexpand(True)
        vbox.set_vexpand(True)

        provider = Gtk.CssProvider.new()
        provider.load_from_data(
            " #controller_window { background-color: rgba(0, 0, 0, 0); } ;"
        )

        provider1 = Gtk.CssProvider.new()
        provider1.load_from_data(
            " #vbox {  border: 4px solid rgba(255, 0, 255, 1);  border-radius: 12px;};"
        )

        self.switch = True

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider1, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        def switch(w, data):
            if self.switch:
                Gtk.StyleContext.add_provider_for_display(
                    Gdk.Display.get_default(),
                    provider1,
                    Gtk.STYLE_PROVIDER_PRIORITY_USER,
                )
                self.switch = False
            else:
                Gtk.StyleContext.remove_provider_for_display(
                    Gdk.Display.get_default(), provider1
                )
                self.switch = True
                self.force_floating()

        s = Gtk.Shortcut.new(
            trigger=Gtk.ShortcutTrigger.parse_string("<Ctrl>g"),
            action=Gtk.CallbackAction.new(switch),
        )
        self.add_shortcut(shortcut=s)
        self.set_decorated(False)
        # self.set_resizable(False)
        # self.
        # window.present()
