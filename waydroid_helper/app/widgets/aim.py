import logging
import cairo
import gi
import math


gi.require_version("Gdk", "4.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gdk, Pango, PangoCairo, GObject, Adw
from typing import Tuple, override
from .mapping_button import MappingButton
from .hotkey_editable_widget import KeyEditableWidget
from .shortcut import ShortCut
from .MappingButtonState import MappingButtonState
from app.wayland_pointer_lock import PointerConstraint
from app.control_msg import InjectTouchEventMsg
from app.input import AMontionEventAction, AMontionEventButtons
from app.widgets.resizable import CenterResizableWidget

logger = logging.getLogger(__name__)


class Aim(KeyEditableWidget, CenterResizableWidget, MappingButton):
    def __init__(self, key: ShortCut, x, y, width, height):
        super().__init__(
            keys=key,
            action_point_x=x,
            action_point_y=y,
            action_width=width,
            action_height=height,
            max_keys=1,
        )
        self.__pointer_constraint: PointerConstraint = None
        self.__aiming = False
        self.__current_pos: Tuple[int, int] = None
        self.sensitivity = 20
        self.connect("notify::aiming", self.on_aiming_changed)

    def relative_motion_processor(self, obj, dx, dy, dx_unaccel, dy_unaccel):
        if not self.pointer_id:
            self.pointer_id = self.observer.occupy_id()
        if not self.pointer_id:
            return

        _dx = dx_unaccel * 20 / self.sensitivity
        _dy = dy_unaccel * 20 / self.sensitivity

        w = self.get_root().get_width()
        h = self.get_root().get_height()

        if self.__current_pos:
            x, y = (
                self.__current_pos[0] + _dx,
                self.__current_pos[1] + _dy,
            )

            if (
                x >= self.action_start_x + self.action_width
                or x <= self.action_start_x
                or y >= self.action_start_y + self.action_height
                or y <= self.action_start_y
            ):

                msg = InjectTouchEventMsg(
                    action=AMontionEventAction.UP,
                    pointer_id=self.pointer_id,
                    position=(int(x), int(y), w, h),
                    pressure=0.0,
                    action_button=AMontionEventButtons.PRIMARY,
                    buttons=0,
                )
                self.observer.controller.send_msg(msg)
                self.__current_pos = None

        if not self.__current_pos:
            self.__current_pos = (self.action_point_x, self.action_point_y)
            msg = InjectTouchEventMsg(
                action=AMontionEventAction.DOWN,
                pointer_id=self.pointer_id,
                position=(int(self.action_point_x), int(self.action_point_y), w, h),
                pressure=1.0,
                action_button=AMontionEventButtons.PRIMARY,
                buttons=AMontionEventButtons.PRIMARY,
            )
            self.observer.controller.send_msg(msg)

        self.__current_pos = (
            self.__current_pos[0] + _dx,
            self.__current_pos[1] + _dy,
        )

        msg = InjectTouchEventMsg(
            action=AMontionEventAction.MOVE,
            pointer_id=self.pointer_id,
            position=(int(self.__current_pos[0]), int(self.__current_pos[1]), w, h),
            pressure=1.0,
            action_button=0,
            buttons=AMontionEventButtons.PRIMARY,
        )
        self.observer.controller.send_msg(msg)

    @GObject.Property(type=bool, default=False)
    def aiming(self):
        return self.__aiming

    @aiming.setter
    def aiming(self, value):
        if self.__aiming != value:
            self.__aiming = value
            self.notify("aiming")

    @property
    def pointer_constraint(self):
        if not self.__pointer_constraint:
            self.__pointer_constraint = PointerConstraint(self.get_root())
            self.__pointer_constraint.setup()
            self.__pointer_constraint.connect(
                "relative-motion", self.relative_motion_processor
            )
        return self.__pointer_constraint

    @override
    def update_result_label(self):
        new_key = ShortCut(self._pressed_keys)
        self._keys = [new_key]
        self.queue_draw()

    @override
    def draw_action(self, area, cr: cairo.Context, width, height):
        # 获取 CSS 中定义的颜色
        bg_color = Gdk.RGBA()
        bg_color.parse("rgba(0,0,0,0.5)")
        border_color = Gdk.RGBA()
        if self.state == MappingButtonState.SELECTED:
            border_color.parse("rgba(22, 196, 255, 0.8)")
        elif self.state == MappingButtonState.EXPANDED:
            border_color.parse("rgba(255, 255, 255, 0.8)")
        text_color = Gdk.RGBA()
        text_color.parse("rgba(245, 245, 246, 1.0)")

        # 设置背景色
        Gdk.cairo_set_source_rgba(cr, bg_color)
        cr.arc(
            width / 2,
            height / 2,
            min(width, height, 50) / 2,
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
            min(width, height, 50) / 2 - 1,
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
            # 设置准心颜色
        cr.set_source_rgba(1, 1, 1, 0.8)  # 白色，80%不透明度

        # 设置线宽
        cr.set_line_width(2)

        # 计算圆的半径和中心
        radius = min(width, height, 50) / 2
        center_x = width / 2
        center_y = height / 2

        # 定义准心标记的长度
        marker_length = radius / 3  # 可以调整这个值来改变标记的长度

        # 绘制上标记
        cr.move_to(center_x, center_y - radius)
        cr.line_to(center_x, center_y - radius + marker_length)

        # 绘制下标记
        cr.move_to(center_x, center_y + radius)
        cr.line_to(center_x, center_y + radius - marker_length)

        # 绘制左标记
        cr.move_to(center_x - radius, center_y)
        cr.line_to(center_x - radius + marker_length, center_y)

        # 绘制右标记
        cr.move_to(center_x + radius, center_y)
        cr.line_to(center_x + radius - marker_length, center_y)

        # 执行绘制
        cr.stroke()

    def draw_compact(self, area, cr: cairo.Context, width, height):
        return

    def draw_expanded(self, area, cr: cairo.Context, width, height):
        self.draw_action(area, cr, width, height)

    def aiming_start(self):
        self.aiming = True

    def aiming_stop(self):
        self.aiming = False

    def aiming_toggle(self):
        self.aiming = not self.aiming

    def on_aiming_changed(self, widget, event):
        if self.aiming:
            self.get_root().get_surface().set_cursor(Gdk.Cursor.new_from_name("none"))
            self.pointer_constraint.lock_pointer()
            self.observer.set_ignore_fire(False)
        else:
            self.get_root().get_surface().set_cursor(
                Gdk.Cursor.new_from_name("default")
            )
            self.pointer_constraint.unlock_pointer()
            if self.__current_pos:
                x, y = self.__current_pos
                w = self.get_root().get_width()
                h = self.get_root().get_height()
                msg = InjectTouchEventMsg(
                    action=AMontionEventAction.UP,
                    pointer_id=self.pointer_id,
                    position=(int(x), int(y), w, h),
                    pressure=0.0,
                    action_button=AMontionEventButtons.PRIMARY,
                    buttons=0,
                )
                self.observer.controller.send_msg(msg)
                self.__current_pos = None
            if self.pointer_id:
                self.observer.release_id(self.pointer_id)
                self.pointer_id = None
            self.observer.set_ignore_fire(True)

    @override
    def mapping_start(self, key):
        self.aiming_toggle()

    def mapping_end(self, key: ShortCut):
        return

    @property
    def compact_start_x(self):
        return self.action_point_x - self.compact_width / 2

    @property
    def compact_start_y(self):
        return self.action_point_y - self.compact_height / 2

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
        return 50

    @property
    def expanded_height(self):
        return 50
