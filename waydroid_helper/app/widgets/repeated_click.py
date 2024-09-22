from enum import IntEnum
import logging
import cairo
import gi
import math


gi.require_version("Gdk", "4.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gdk, Pango, PangoCairo, GLib
from typing import override
from .mapping_button import MappingButton
from .hotkey_editable_widget import KeyEditableWidget
from .shortcut import ShortCut
from app.control_msg import InjectTouchEventMsg
from app.input import AMontionEventAction, AMontionEventButtons
from .MappingButtonState import MappingButtonState

logger = logging.getLogger(__name__)


class RepeatedClickMode(IntEnum):
    LONG_PRESS_COMBO = 0
    CLICK_AFTER_BUTTON = 1


class RepeatedClick(KeyEditableWidget, MappingButton):
    def __init__(
        self,
        key: ShortCut,
        x,
        y,
        size=50,
        mode=RepeatedClickMode.LONG_PRESS_COMBO,
        repeat_times=50,
        interval=20,
    ):
        # ClickButton 只有一组快捷键(一个 ShortCut)
        super().__init__(
            keys=key,
            action_point_x=x,
            action_point_y=y,
            action_width=size,
            action_height=size,
        )
        self.__mode = mode
        self.repeate_times = repeat_times
        self.interval = interval
        self.__cnt = 0
        self.__timer = None

    @override
    def update_result_label(self):
        new_key = ShortCut(self._pressed_keys)
        self._keys = [new_key]
        self.queue_draw()

    def draw_action(self, area, cr: cairo.Context, width, height):
        # 获取 CSS 中定义的颜色
        bg_color = Gdk.RGBA()
        bg_color.parse("rgba(0,0,0,0.5)")
        border_color = Gdk.RGBA()
        if self.state == MappingButtonState.SELECTED:
            border_color.parse("rgba(22, 196, 255, 0.8)")
        elif self.state == MappingButtonState.EXPANDED:
            border_color.parse("rgba(255, 255, 255, 0.8)")
        elif self.state == MappingButtonState.COMPACT:
            border_color.parse("rgba(255, 255, 255, 0)")
        text_color = Gdk.RGBA()
        text_color.parse("rgba(245, 245, 246, 1.0)")

        # 设置背景色
        Gdk.cairo_set_source_rgba(cr, bg_color)
        cr.arc(
            width / 2,
            height / 2,
            min(width, height) / 2,
            0,
            2 * math.pi,
        )
        cr.fill()

        # 绘制圆形边框
        Gdk.cairo_set_source_rgba(cr, border_color)
        cr.set_line_width(2)
        cr.arc(
            width / 2,
            height / 2,
            min(width, height) / 2 - 1,
            0,
            2 * math.pi,
        )
        cr.stroke()

        # 绘制文本
        Gdk.cairo_set_source_rgba(cr, text_color)
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription("Sans 12")
        layout.set_font_description(font)
        text = str(self._keys[0])
        layout.set_text(text)
        ink, logical = layout.get_extents()

        # 计算文本位置使其居中
        x = (width - logical.width / Pango.SCALE) / 2
        y = (height - logical.height / Pango.SCALE) / 2

        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)

        # TODO 看看能不能封装, 因为一些 btn 类似
        text_extents = cr.text_extents(text)
        x = width / 2 - (text_extents.width / 2 + text_extents.x_bearing)
        y = height / 2 - (text_extents.height / 2 + text_extents.y_bearing)
        if self.is_focus() and self.cursor_visible:
            cr.move_to(x - 3, y + 5)
            cr.line_to(x + 3 + text_extents.width, y + 5)
            cr.set_line_width(3)
            cr.stroke()

    def draw_compact(self, area, cr: cairo.Context, width, height):
        self.draw_action(area, cr, width, height)
    
    def draw_expanded(self, area, cr: cairo.Context, width, height):
        self.draw_action(area, cr, width, height)

    def click_center(self):
        if self.__cnt < self.repeate_times:
            x, y = self.action_point_x,self.action_point_y
            w = self.get_root().get_width()
            h = self.get_root().get_height()

            msg = InjectTouchEventMsg(
                action=AMontionEventAction.DOWN,
                pointer_id=self.pointer_id,
                position=(int(x), int(y), w, h),
                pressure=1.0,
                action_button=AMontionEventButtons.PRIMARY,
                buttons=AMontionEventButtons.PRIMARY,
            )
            self.observer.controller.send_msg(msg)
            self.pressed = True

            msg = InjectTouchEventMsg(
                action=AMontionEventAction.UP,
                pointer_id=self.pointer_id,
                position=(int(x), int(y), w, h),
                pressure=0.0,
                action_button=AMontionEventButtons.PRIMARY,
                buttons=0,
            )

            self.observer.controller.send_msg(msg)
            self.pressed = False
            self.__cnt += 1
            logger.info(self.__cnt)
            return True

        self.__cnt = 0
        # GLib.source_remove(self.__timer)
        self.__timer = None
        self.observer.release_id(self.pointer_id)
        self.pointer_id = None
        return False

    @override
    def mapping_start(self, key):
        if self.__timer:
            return
        self.pointer_id = self.observer.occupy_id()
        if not self.pointer_id:
            return
        self.__timer = GLib.timeout_add(self.interval, self.click_center)

    def mapping_end(self, key: ShortCut) -> bool:
        if self.__mode == RepeatedClickMode.LONG_PRESS_COMBO and self.__timer:
            # 计时未结束就 release, 归还 id
            GLib.source_remove(self.__timer)
            self.__cnt = 0
            self.__timer = None
            self.observer.release_id(self.pointer_id)
            self.pointer_id = None

    @property
    def compact_start_x(self):
        return self.action_point_x

    @property
    def compact_start_y(self):
        return self.action_point_y

    @property
    def expanded_start_x(self):
        return self.action_point_x - self.expanded_width / 2

    @property
    def expanded_start_y(self):
        return self.action_point_y - self.expanded_height / 2

    @property
    def action_start_x(self):
        return self.action_point_x - self.action_width / 2

    @property
    def action_start_y(self):
        return self.action_point_y - self.action_height / 2

    @property
    def compact_width(self):
        return 30

    @property
    def compact_height(self):
        return 30

    @property
    def expanded_width(self):
        return self.action_width

    @property
    def expanded_height(self):
        return self.action_height