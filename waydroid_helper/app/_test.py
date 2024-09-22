import ctypes
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk

# 加载libgtk-4.so
libgtk = ctypes.CDLL("libgtk-4.so")

# 定义函数原型
libgtk.gdk_wayland_surface_get_wl_surface.restype = ctypes.c_void_p
libgtk.gdk_wayland_surface_get_wl_surface.argtypes = [ctypes.c_void_p]
libgtk.gdk_wayland_display_get_wl_display.restype = ctypes.c_void_p
libgtk.gdk_wayland_display_get_wl_display.argtypes = [ctypes.c_void_p]
# 加载 libwayland-client.so
libpointer = ctypes.CDLL(
    "/home/rikka/工程/waydroid-helper/waydroid_helper/app/libpointer-lock.so"
)
libpointer.wayland_pointer_lock_init.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
libpointer.wayland_pointer_lock_init.restype = ctypes.c_bool
libpointer.lock_pointer.restype = ctypes.c_bool
libpointer.lock_pointer.argtypes = [ctypes.c_void_p]
libpointer.unlock_pointer.argtypes = [ctypes.c_void_p]
libpointer.unlock_pointer.restype = ctypes.c_bool
CALLBACK_TYPE = ctypes.CFUNCTYPE(
    None, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double
)
libpointer.set_relative_motion_callback.argtypes = [CALLBACK_TYPE]


class WaylandData(ctypes.Structure):
    _fields_ = [
        ("pointer_constraints", ctypes.c_void_p),
        ("locked_pointer", ctypes.c_void_p),
        ("seat", ctypes.c_void_p),
        ("pointer", ctypes.c_void_p),
        ("compositor", ctypes.c_void_p),
        ("wl_registry", ctypes.c_void_p),
        ("relative_pointer_manager", ctypes.c_void_p),
        ("relative_pointer", ctypes.c_void_p),
        ("wl_display", ctypes.c_void_p),
        ("wl_surface", ctypes.c_void_p),
        # ("queue", ctypes.c_void_p)
    ]


class PointerConstraint:
    def __init__(self, widget):
        self.widget = widget
        self.locked_pointer = False
        self.wd = WaylandData()

    def python_callback(self, x, y, z, w):
        print(f"Callback called with: {x}, {y}, {z}, {w}")

    def setup(self):
        # 获取Wayland显示和表面
        self.wl_display_ptr = get_wayland_display(self.widget)
        self.wl_surface_ptr = get_wayland_surface(self.widget)
        if not (
            libpointer.wayland_pointer_lock_init(
                self.wl_display_ptr, self.wl_surface_ptr, ctypes.byref(self.wd)
            )
        ):
            print("error")
        self.c_callback = CALLBACK_TYPE(self.python_callback)
        libpointer.set_relative_motion_callback(self.c_callback)

    def lock_pointer(self):
        self.locked_pointer = True
        libpointer.lock_pointer(ctypes.byref(self.wd))
        self.widget.set_cursor_from_name("none")

    def unlock_pointer(self):
        self.locked_pointer = False
        libpointer.unlock_pointer(ctypes.byref(self.wd))
        self.widget.set_cursor_from_name("default")


def get_wayland_surface(widget: Gtk.Window):
    gdk_surface = widget.get_surface()
    return libgtk.gdk_wayland_surface_get_wl_surface(hash(gdk_surface))


def get_wayland_display(widget):
    gdk_display = widget.get_display()
    return libgtk.gdk_wayland_display_get_wl_display(hash(gdk_display))


class MyWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(300, 300)
        self.set_title("Pointer Constraint Demo")

        self.pointer_constraint = PointerConstraint(self)

        button = Gtk.Button(label="Lock/Unlock Pointer")
        button.connect("clicked", self.on_button_clicked)
        self.set_child(button)
        self.realize()
        self.pointer_constraint.setup()

    def on_button_clicked(self, button):
        if not self.pointer_constraint.locked_pointer:
            self.pointer_constraint.lock_pointer()
            button.set_label("Unlock Pointer")
        else:
            self.pointer_constraint.unlock_pointer()
            button.set_label("Lock Pointer")


class MyApp(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def do_activate(self):
        win = MyWindow(application=self)
        win.present()


app = MyApp(application_id="com.example.MyApp")
app.run(None)
