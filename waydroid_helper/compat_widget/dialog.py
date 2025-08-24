# pyright: reportUnknownMemberType=false
# pyright: reportUnknownParameterType=false
# pyright: reportMissingParameterType=false
# pyright: reportRedeclaration=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportAny=false
# pyright: reportCallIssue=false
# pyright: reportMissingSuperCall=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportUntypedBaseClass=false


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


from gi.repository import Adw, GLib, GObject, Gtk

GTK_VERSION = Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
ADW_VERSION = Adw.get_major_version(), Adw.get_minor_version(), Adw.get_micro_version()
GLIB_VERSION = GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION


# 根据版本选择基类并创建兼容层
if ADW_VERSION >= (1, 5, 0):
    _BaseDialog = Adw.Dialog
else:
    _BaseDialog = Adw.Window


class Dialog(_BaseDialog):
    def __init__(
        self,
        title: str = "",
        content_widget: Gtk.Widget | None = None,
        parent: Gtk.Window | None = None,
        modal: bool = True,
    ):

        if ADW_VERSION >= (1, 5, 0):
            # AdwDialog 版本
            super().__init__(content_height=200, content_width=400)
            self._parent = parent
            self._content_widget = None
            self._title = title
            
            if title:
                self.set_title(title)
        else:
            # AdwWindow 版本
            super().__init__(
                title=title,
                transient_for=parent,
                modal=modal,
            )
            self._parent = parent
            self._content_widget = None
            
            # 设置默认大小和样式
            self.set_default_size(400, 300)
            self.add_css_class("dialog")
        
        # 如果提供了内容组件，设置它
        if content_widget:
            self.set_content(content_widget)

    def set_content(self, widget: Gtk.Widget) -> None:
        if self._content_widget and ADW_VERSION < (1, 5, 0):
            super().set_content(None)
        elif self._content_widget and ADW_VERSION >= (1, 5, 0):
            super().set_child(None)
        
        self._content_widget = widget
        
        if ADW_VERSION >= (1, 5, 0):
            super().set_child(widget)
        else:
            super().set_content(widget)

    def get_content(self) -> Gtk.Widget | None:
        return self._content_widget

    def present(self) -> None:
        if ADW_VERSION >= (1, 5, 0):
            if self._parent:
                super().present(self._parent)
            else:
                # 尝试获取活动窗口
                app = Gtk.Application.get_default()
                if app:
                    try:
                        active_window = getattr(app, 'get_active_window', lambda: None)()
                        if active_window:
                            super().present(active_window)
                    except (AttributeError, TypeError):
                        pass
        else:
            super().present()

    def close(self) -> None:
        super().close()
