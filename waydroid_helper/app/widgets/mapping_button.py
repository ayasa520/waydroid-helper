import cairo
import gi

from app.keyboard_mouse_gaming import KeyboardMouseGaming
from .MappingButtonState import MappingButtonState
from .combined_meta import CombinedMeta


gi.require_version("Gtk", "4.0")

from abc import abstractmethod, ABC
from gi.repository import Gtk, GObject
from typing import Union, List, override
from .shortcut import ShortCut


class MappingButton(Gtk.DrawingArea, ABC, metaclass=CombinedMeta):

    # __gsignals__ = {
    #     "key-changed": (
    #         GObject.SignalFlags.RUN_FIRST,
    #         None,
    #         (object, object),
    #     )
    # }

    state = GObject.Property(type=object)
    editing = GObject.Property(type=bool, default=False)

    def __init__(
        self,
        keys: Union[ShortCut, List[ShortCut]],
        action_point_x,
        action_point_y,
        action_width,
        action_height,
        max_keys=2,
    ):
        super().__init__()

        # preview->editing->expanded
        self.action_point_x = action_point_x
        self.action_point_y = action_point_y
        self.action_height = action_height
        self.action_width = action_width

        # max_keys 每组快捷键包含的最大键数
        self.__max_keys = max_keys
        if isinstance(keys, ShortCut):
            keys = [keys]
        self._keys = keys
        self.__observer: KeyboardMouseGaming = None
        self.pointer_id = None
        self.pressed = False
        # # for key input
        # self.set_focusable(True)
        # self.set_can_focus(True)
        self.set_content_width(action_width)
        self.set_content_height(action_height)
        self.set_draw_func(self.draw)

        self.connect("notify::state", self.on_state_changed)
        self.connect("notify::has-focus", self.on_focus)
        self.connect("notify::editing", self.on_editing_changed)

    def on_state_changed(self, widget, _):
        print("状态转换", self.state)
        if self.state == MappingButtonState.SELECTED:
            self.add_css_class("selected")
            self.set_content_height(self.action_height)
            self.set_content_width(self.action_width)
            self.move(self.action_start_x, self.action_start_y)
        elif self.state == MappingButtonState.EXPANDED:
            self.remove_css_class("selected")
            self.set_content_height(self.expanded_height)
            self.set_content_width(self.expanded_width)
            self.move(self.expanded_start_x, self.expanded_start_y)
        elif self.state == MappingButtonState.COMPACT:
            self.remove_css_class("selected")
            self.set_content_height(self.compact_height)
            self.set_content_width(self.compact_width)
            self.move(self.compact_start_x, self.compact_start_y)

    def move_action(self, x, y):
        fixed: Gtk.Fixed = self.get_parent()
        self.action_point_x = self.action_point_x - self.action_start_x + x
        self.action_point_y = self.action_point_y - self.action_start_y + y
        fixed.move(self, x, y)

    def move(self, x, y):
        fixed: Gtk.Fixed = self.get_parent()
        fixed.move(self, x, y)

    @property
    def compact_width(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def compact_height(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def expanded_width(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def expanded_height(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def compact_start_x(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def compact_start_y(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def expanded_start_x(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def expanded_start_y(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def action_start_x(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @property
    def action_start_y(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def on_editing_changed(self, widget, event):
        if not self.editing:
            self.state = MappingButtonState.COMPACT
        else:
            if not self.has_focus():
                self.state = MappingButtonState.EXPANDED

    def on_focus(self, widget, event):
        if self.has_focus():
            print("获得焦点")
            self.state = MappingButtonState.SELECTED
        else:
            print("失去焦点")
            if self.editing:
                self.state = MappingButtonState.EXPANDED
            else:
                self.state = MappingButtonState.COMPACT
        # else:
        #     self.editing_mode = False

    @property
    def observer(self):
        return self.__observer

    @observer.setter
    def observer(self, observer):
        self.__observer = observer

    # @property
    # def center(self) -> tuple:
    #     x = self.get_width() / 2 + self.expanded_center_x
    #     y = self.get_height() / 2 + self.expanded_center_y
    #     return (x, y)

    @property
    def keys(self):
        return self._keys

    @property
    def max_keys(self):
        """
        ShortCut 最多包含按键数
        """
        return self.__max_keys

    def draw(self, area, cr: cairo.Context, width, height):
        if self.state == MappingButtonState.COMPACT:
            self.draw_compact(area, cr, width, height)
        elif self.state == MappingButtonState.EXPANDED:
            self.draw_expanded(area, cr, width, height)
        else:
            self.draw_action(area, cr, width, height)

    @abstractmethod
    def draw_compact(self, area, cr: cairo.Context, width, height):
        raise NotImplementedError("Subclasses should implement this method.")

    @abstractmethod
    def draw_expanded(self, area, cr: cairo.Context, width, height):
        raise NotImplementedError("Subclasses should implement this method.")

    @abstractmethod
    def draw_action(self, area, cr: cairo.Context, width, height):
        raise NotImplementedError("Subclasses should implement this method.")

    @abstractmethod
    def mapping_start(self, key: ShortCut):
        raise NotImplementedError("Subclasses should implement this method.")

    @abstractmethod
    def mapping_end(self, key: ShortCut):
        """
        如果映射结束, 返回 True, 才能释放 pointer_id
        """
        raise NotImplementedError("Subclasses should implement this method.")
