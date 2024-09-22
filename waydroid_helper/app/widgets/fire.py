import logging
import cairo
import gi
import math



gi.require_version("Gdk", "4.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gdk, Pango, PangoCairo
from typing import override
from .mapping_button import MappingButton
from .shortcut import ShortCut
from app.control_msg import InjectTouchEventMsg
from .MappingButtonState import MappingButtonState
from app.input import AMontionEventAction, AMontionEventButtons

logger = logging.getLogger(__name__)


class Fire(MappingButton):
    def __init__(self, x, y):
        # ClickButton 只有一组快捷键(一个 ShortCut)
        super().__init__(
            keys=ShortCut([1]),
            action_point_x=x,
            action_point_y=y,
            action_width=50,
            action_height=50,
        )

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

    def draw_compact(self, area, cr: cairo.Context, width, height):
        self.draw_action(area, cr, width, height)
    
    def draw_expanded(self, area, cr: cairo.Context, width, height):
        self.draw_action(area, cr, width, height)

    @override
    def mapping_start(self, key):
        pointer_id = self.observer.occupy_id()
        if not pointer_id:
            return

        self.pointer_id = pointer_id
        x, y = self.action_point_x, self.action_point_y
        action = AMontionEventAction.DOWN
        w = self.get_root().get_width()
        h = self.get_root().get_height()

        msg = InjectTouchEventMsg(
            action=action,
            pointer_id=pointer_id,
            position=(int(x), int(y), w, h),
            pressure=1.0,
            action_button=AMontionEventButtons.PRIMARY,
            buttons=AMontionEventButtons.PRIMARY,
        )
        self.observer.controller.send_msg(msg)

    def mapping_end(self, key: ShortCut):
        if not self.pointer_id:
            return

        x, y = self.action_point_x, self.action_point_y
        action = AMontionEventAction.UP
        w = self.get_root().get_width()
        h = self.get_root().get_height()

        msg = InjectTouchEventMsg(
            action=action,
            pointer_id=self.pointer_id,
            position=(int(x), int(y), w, h),
            pressure=0.0,
            action_button=AMontionEventButtons.PRIMARY,
            buttons=0,
        )
        self.observer.controller.send_msg(msg)
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
