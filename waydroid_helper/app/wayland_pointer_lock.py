import ctypes

from gi.repository import GObject
from pywayland import ffi
from pywayland.client import Display
from pywayland.protocol.wayland import WlSurface, WlCompositor, WlSeat
from pywayland.protocol.pointer_constraints_unstable_v1 import ZwpPointerConstraintsV1
from pywayland.protocol.relative_pointer_unstable_v1 import ZwpRelativePointerManagerV1

# 加载libgtk-4.so
libgtk = ctypes.CDLL("libgtk-4.so")

# 定义函数原型
libgtk.gdk_wayland_surface_get_wl_surface.restype = ctypes.c_void_p
libgtk.gdk_wayland_surface_get_wl_surface.argtypes = [ctypes.c_void_p]
libgtk.gdk_wayland_display_get_wl_display.restype = ctypes.c_void_p
libgtk.gdk_wayland_display_get_wl_display.argtypes = [ctypes.c_void_p]


def get_wayland_surface(widget):
    gdk_surface = widget.get_surface()
    return libgtk.gdk_wayland_surface_get_wl_surface(hash(gdk_surface))


def get_wayland_display(widget):
    gdk_display = widget.get_display()
    return libgtk.gdk_wayland_display_get_wl_display(hash(gdk_display))


class PointerConstraint(GObject.Object):
    __gsignals__ = {
        "relative-motion": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (float, float, float, float),
        )
    }

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.wl_display_ptr = None
        self.wl_surface_ptr = None
        self.pointer_constraints = None
        self.relative_pointer_manager = None
        self.locked_pointer = None
        self.relative_pointer = None
        self.compositor = None
        self.seat = None
        self.pointer = None

    def seat_handle_capabilities(self, seat, caps):
        if (caps & WlSeat.capability.pointer) and not self.pointer:
            self.pointer = seat.get_pointer()

    def registry_global(self, registry, id, interface, version):
        if interface == ZwpPointerConstraintsV1.name:
            self.pointer_constraints = registry.bind(
                id, ZwpPointerConstraintsV1, version
            )
        elif interface == WlCompositor.name:
            self.compositor = registry.bind(id, WlCompositor, version)
        elif interface == WlSeat.name:
            self.seat = registry.bind(id, WlSeat, version)
            self.seat.dispatcher["capabilities"] = self.seat_handle_capabilities
        elif interface == ZwpRelativePointerManagerV1.name:
            self.relative_pointer_manager = registry.bind(
                id, ZwpRelativePointerManagerV1, version
            )

    def setup(self):
        # 获取Wayland显示和表面
        self.wl_display_ptr = get_wayland_display(self.widget)
        self.wl_surface_ptr = get_wayland_surface(self.widget)

        # 创建PyWayland显示对象
        self.wl_display = Display()
        self.wl_display._ptr = ffi.cast("struct wl_display *", self.wl_display_ptr)
        self.wl_surface = WlSurface()
        self.wl_surface._ptr = ffi.cast("struct wl_proxy *", self.wl_surface_ptr)

        # 获取全局对象
        registry = self.wl_display.get_registry()
        registry.dispatcher["global"] = self.registry_global

        self.wl_display.roundtrip()
        self.wl_display.roundtrip()
        if not (self.pointer_constraints and self.pointer and self.seat):
            print("Failed to get required interfaces")
            exit(1)

    def relative_pointer_handle_relative_motion(
        self,
        zwp_relative_pointer_v1,
        utime_hi,
        utime_lo,
        dx,
        dy,
        dx_unaccel,
        dy_unaccel,
    ):
        self.emit("relative-motion", dx, dy, dx_unaccel, dy_unaccel)

    def lock_pointer(self):
        if self.pointer_constraints and self.pointer:
            self.locked_pointer = self.pointer_constraints.lock_pointer(
                self.wl_surface,
                self.pointer,
                None,
                ZwpPointerConstraintsV1.lifetime.persistent,
            )

        if self.relative_pointer_manager and self.pointer:
            self.relative_pointer = self.relative_pointer_manager.get_relative_pointer(
                self.pointer
            )
            if self.relative_pointer:
                self.relative_pointer.dispatcher["relative_motion"] = (
                    self.relative_pointer_handle_relative_motion
                )

    def unlock_pointer(self):
        if self.locked_pointer:
            self.locked_pointer.destroy()
            self.locked_pointer = None
        if self.relative_pointer:
            self.relative_pointer.destroy()
            self.relative_pointer = None


# class MyWindow(Gtk.ApplicationWindow):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.set_default_size(300, 300)
#         self.set_title("Pointer Constraint Demo")

#         self.pointer_constraint = PointerConstraint(self)

#         button = Gtk.Button(label="Lock/Unlock Pointer")
#         button.connect("clicked", self.on_button_clicked)
#         self.set_child(button)

#     def on_button_clicked(self, button):
#         if not self.pointer_constraint.locked_pointer:
#             self.pointer_constraint.lock_pointer()
#             button.set_label("Unlock Pointer")
#         else:
#             self.pointer_constraint.unlock_pointer()
#             button.set_label("Lock Pointer")


# class MyApp(Gtk.Application):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)

#     def do_activate(self):
#         win = MyWindow(application=self)
#         win.present()
#         win.pointer_constraint.setup()


# app = MyApp(application_id="com.example.MyApp")
# app.run(None)
