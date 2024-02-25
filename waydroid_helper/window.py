import subprocess
from gi.repository import Gtk, GLib, GObject, Adw
from waydroid_helper.proppage import PropPage
from waydroid_helper.waydroid import Waydroid
from waydroid_helper.generalpage import GeneralPage
from gettext import gettext as _


@Gtk.Template(resource_path='/com/jaoushingan/WaydroidHelper/ui/window.ui')
class WaydroidHelperWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'WaydroidHelperWindow'
    general_page: GeneralPage = Gtk.Template.Child()
    prop_page: PropPage = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        GObject.type_ensure(GeneralPage)
        GObject.type_ensure(PropPage)
        self.waydroid = Waydroid()
        self.general_page.set_property("waydroid", self.waydroid)
        self.prop_page.set_property("waydroid", self.waydroid)


