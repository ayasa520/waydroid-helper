from gettext import gettext as _
from waydroid_helper.waydroid import Waydroid
from gi.repository import Gtk, GObject
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')


@Gtk.Template(resource_path='/com/jaoushingan/WaydroidHelper/ui/ExtensionsPage.ui')
class ExtensionsPage(Gtk.Box):
    __gtype_name__ = "ExtensionsPage"
    waydroid: GObject.Property = GObject.Property(default=None, type=Waydroid)

    def __init__(self, waydroid:Waydroid, **kargs):
        super().__init__(**kargs)
        self.set_property("waydroid",waydroid)
