#!/usr/bin/env python3
"""
CSS样式管理
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Gdk

# 透明窗口样式
CSS_TRANSPARENT = """
#transparent-window {
    background-color: rgba(0, 0, 0, 0.05);
}
#mapping-widget {
    background-color: rgba(0, 0, 0, 0);
}
"""


class StyleManager:
    """样式管理器"""

    def __init__(self):
        self.provider: Gtk.CssProvider | None = None
        self.setup_styles()

    def setup_styles(self):
        """设置全局样式"""
        self.provider = Gtk.CssProvider.new()
        self.provider.load_from_data(CSS_TRANSPARENT.encode())

        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, self.provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
            )

    def add_custom_style(self, css_content: str):
        """添加自定义样式"""
        if self.provider:
            current_css = CSS_TRANSPARENT + "\n" + css_content
            self.provider.load_from_data(current_css.encode())
