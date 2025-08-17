# pyright: reportUnknownArgumentType=false
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import GLib, Gtk

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
        # 1. 重置尺寸请求以触发 GTK 重新计算尺寸
        if hasattr(self, 'label'):
            self.label.set_size_request(-1, -1)
        
        # 2. 设置 reveal 状态，触发动画
        widget.set_reveal_child(reveal)
        
        # 3. 确保在状态改变后重新计算布局
        def ensure_resize():
            if hasattr(self, 'label'):
                # 重置尺寸后再次调用 queue_resize
                self.label.queue_resize()
            widget.queue_resize()
            return False  # 停止 timeout
        
        # 使用 timeout 确保在动画完成后重新计算尺寸
        GLib.timeout_add(250, ensure_resize)
