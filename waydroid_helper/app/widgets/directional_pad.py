import logging
import cairo
import gi
import math

from app.input import AMontionEventAction, AMontionEventButtons
from app.control_msg import InjectTouchEventMsg


gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gdk, Pango, PangoCairo, Gtk, GLib
from typing import override
from bidict import ON_DUP_DROP_OLD, bidict
from .mapping_button import MappingButton
from .shortcut import ShortCut
from .hotkey_editable_widget import KeyEditableWidget
from .resizable import SquareAndCenterResizableWidget
from .MappingButtonState import MappingButtonState

logger = logging.getLogger(__name__)


class DirectionalPad(KeyEditableWidget, SquareAndCenterResizableWidget, MappingButton):
    def __init__(
        self,
        up_key: ShortCut,
        left_key: ShortCut,
        down_key: ShortCut,
        right_key: ShortCut,
        x: int,
        y: int,
        size=200,
    ):
        # DirectionalPad 有 4 组快捷键
        super().__init__(
            keys=[up_key, left_key, down_key, right_key],
            action_point_x=x,
            action_point_y=y,
            action_width=size,
            action_height=size,
            max_keys=1,
        )
        self.__max_icon_size = 300
        self.__buttons = []
        # self.mouse_pressed_directions = {"up": False, "down": False, "left": False, "right": False}
        self.__direction_keys = bidict()
        self.__direction_keys.putall(
            {
                "up": up_key,
                "left": left_key,
                "down": down_key,
                "right": right_key,
            },
            on_dup=ON_DUP_DROP_OLD,
        )
        self.__editing_direction = None
        self.__active_keys = {"up": False, "left": False, "down": False, "right": False}
        # dpad 正在虚拟摇杆移动中标志
        # self.__mapping_moving = False
        self.__current_position = None
        self.__timer = None
        self.__interval = 20
        self.__max_cnt = 6
        self.__cnt = 0
        # up left down right
        self.__dest_point = None
        self.__dest_points = {
            (True, False, False, False): lambda: self.top,
            (False, True, False, False): lambda: self.left,
            (False, False, True, False): lambda: self.bottom,
            (False, False, False, True): lambda: self.right,
            (True, True, False, False): lambda: self.top_left,
            (True, False, False, True): lambda: self.top_right,
            (False, True, True, False): lambda: self.bottom_left,
            (False, False, True, True): lambda: self.bottom_right,
            (True, True, True, False): lambda: self.left,
            (True, True, False, True): lambda: self.top,
            (True, False, True, True): lambda: self.right,
            (False, True, True, True): lambda: self.bottom,
            (True, True, True, True): lambda: (
                self.action_point_x,
                self.action_point_y,
            ),
        }

    @property
    def left(self):
        return (self.action_point_x - self.action_width / 2, self.action_point_y)

    @property
    def right(self):
        return (self.action_point_x + self.action_width / 2, self.action_point_y)

    @property
    def top(self):
        return (self.action_point_x, self.action_point_y - self.action_height / 2)

    @property
    def bottom(self):
        return (self.action_point_x, self.action_point_y + self.action_height / 2)

    @property
    def top_left(self):
        r = self.action_width / 2
        return (self.action_point_x - 0.7071 * r, self.action_point_y - 0.7071 * r)

    @property
    def bottom_left(self):
        r = self.action_width / 2
        return (self.action_point_x - 0.7071 * r, self.action_point_y + 0.7071 * r)

    @property
    def bottom_right(self):
        r = self.action_width / 2
        return (self.action_point_x + 0.7071 * r, self.action_point_y + 0.7071 * r)

    @property
    def top_right(self):
        r = self.action_width / 2
        return (self.action_point_x + 0.7071 * r, self.action_point_y - 0.7071 * r)

    @override
    def update_result_label(self):
        if self.__editing_direction:
            # self.text[self._selected_direction] = " + ".join(
            #     [Gdk.keyval_name(key) for key in self.pressed_keys]
            # )
            old_key = self.__direction_keys.get(self.__editing_direction, ShortCut([]))
            new_key = ShortCut(self._pressed_keys)
            self.__direction_keys[self.__editing_direction] = new_key
            if old_key:
                self._keys.remove(old_key)
            self._keys.append(new_key)
            # print(self.text[self._selected_direction])
            self.queue_draw()

    @override
    def on_editing_mouse_pressed(self, gesture: Gtk.GestureClick, n_press, x, y):
        direction = self.get_button_at(x, y)
        if direction and direction != self.__editing_direction and n_press == 2:
            # self.mouse_pressed_directions[direction] = True
            self.__editing_direction = direction
            if self.key_editing_mode == False:
                self.key_editing_mode = True
                # TODO
                self._old_keys = self.keys.copy()
            # self.key_controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
            self.stop_cursor_blink()
            self.start_cursor_blink()
            print(f"{direction} button pressed")
        elif direction != self.__editing_direction:
            self.stop_cursor_blink()
            if self.key_editing_mode == True:
                self.key_editing_mode = False
                # TODO
                self.notify_update()
            self.__editing_direction = None
            self.queue_draw()
        elif direction and n_press == 1 and self.key_editing_mode:
            super().on_editing_mouse_pressed(gesture, n_press, x, y)

    def is_in_circle(self, cx, cy, radius, px, py):
        start_x = cx - radius
        start_y = cy - radius
        return (
            px >= start_x
            and px <= start_x + 2 * radius
            and py >= start_y
            and py <= start_y + 2 * radius
        )

    def get_button_at(self, px, py):
        for direction, cx, cy, r in self.__buttons:
            if self.is_in_circle(cx, cy, r, px, py):
                return direction
        return None

    def draw_action(self, area, cr: cairo.Context, width, height):
        # 清除背景
        # cr.set_source_rgb(0.9, 0.9, 0.9)
        # cr.paint()

        border_color = Gdk.RGBA()
        if self.state == MappingButtonState.SELECTED:
            border_color.parse("rgba(22, 196, 255, 0.8)")
        elif self.state == MappingButtonState.EXPANDED:
            border_color.parse("rgba(255, 255, 255, 0.8)")
        elif self.state == MappingButtonState.COMPACT:
            border_color.parse("rgba(255, 255, 255, 0)")

        bg_color = Gdk.RGBA()
        bg_color.parse("rgba(0,0,0,0.5)")
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

        # 设置按钮颜色
        button_color = Gdk.RGBA()
        button_color.parse("rgba(0,0,0,0.5)")

        # 绘制四个圆形按钮
        radius = min(width, self.__max_icon_size) / 8
        buttons = [
            (
                "up",
                width / 2,
                max(height / 4, height / 2 - self.__max_icon_size / 4),
                radius,
            ),
            (
                "right",
                min(3 * width / 4, width / 2 + self.__max_icon_size / 4),
                height / 2,
                radius,
            ),
            (
                "down",
                width / 2,
                min(3 * height / 4, height / 2 + self.__max_icon_size / 4),
                radius,
            ),
            (
                "left",
                max(width / 4, width / 2 - self.__max_icon_size / 4),
                height / 2,
                radius,
            ),
        ]
        self.__buttons = buttons
        text = {
            "up": str(self.__direction_keys.get("up", ShortCut([]))),
            "down": str(self.__direction_keys.get("down", ShortCut([]))),
            "left": str(self.__direction_keys.get("left", ShortCut([]))),
            "right": str(self.__direction_keys.get("right", ShortCut([]))),
        }
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
        for name, x, y, r in buttons:
            cr.arc(x, y, r, 0, 2 * math.pi)
            # if self.pressed_button == name:
            # cr.set_source_rgb(*pressed_color)
            # else:
            Gdk.cairo_set_source_rgba(cr, button_color)
            cr.fill()

            # 边框
            Gdk.cairo_set_source_rgba(cr, border_color)
            cr.set_line_width(2)
            cr.arc(
                x,
                y,
                r - 1,
                0,
                2 * math.pi,
            )
            cr.stroke()

            # 文字
            Gdk.cairo_set_source_rgba(cr, text_color)
            layout = PangoCairo.create_layout(cr)
            font = Pango.FontDescription("Sans 12")
            layout.set_font_description(font)
            layout.set_text(text[name])
            ink, logical = layout.get_extents()

            # 计算文本位置使其居中
            text_extents = cr.text_extents(text[name])

            text_x = x - (logical.width / Pango.SCALE) / 2
            text_y = y - (logical.height / Pango.SCALE) / 2

            cr.move_to(text_x, text_y)
            PangoCairo.show_layout(cr, layout)

            # TODO 看看能不能封装, 因为一些 btn 类似
            text_extents = cr.text_extents(text[name])
            under_x = x - (text_extents.width / 2 + text_extents.x_bearing)
            under_y = y - (text_extents.height / 2 + text_extents.y_bearing)
            if (
                self.is_focus()
                and self.cursor_visible
                and self.__editing_direction == name
            ):
                cr.move_to(under_x - 3, under_y + 5)
                cr.line_to(under_x + 3 + text_extents.width, under_y + 5)
                cr.set_line_width(3)
                cr.stroke()

    def draw_compact(self, area, cr: cairo.Context, width, height):
        self.draw_action(area, cr, width, height)

    def draw_expanded(self, area, cr: cairo.Context, width, height):
        self.draw_action(area, cr, width, height)

    def get_point_to_move(self, new_direction):
        point = self.__dest_points.get(
            (
                self.__active_keys["up"],
                self.__active_keys["left"],
                self.__active_keys["down"],
                self.__active_keys["right"],
            )
        )
        if point:
            return point()
        elif new_direction == "up":
            return self.top
        elif new_direction == "left":
            return self.left
        elif new_direction == "down":
            return self.bottom
        else:
            return self.right

    def move_to(self, x, y, w, h, pointer_id):
        msg = InjectTouchEventMsg(
            action=AMontionEventAction.MOVE,
            pointer_id=pointer_id,
            position=(int(x), int(y), w, h),
            pressure=1.0,
            action_button=0,
            buttons=AMontionEventButtons.PRIMARY,
        )
        self.observer.controller.send_msg(msg)
        self.__current_position = (x, y)

    def update_position(self, w, h, pointer_id):
        if self.__max_cnt > self.__cnt:
            dx = self.__dest_point[0] - self.__current_position[0]
            dy = self.__dest_point[1] - self.__current_position[1]

            dx = dx / (6 - self.__cnt)
            dy = dy / (6 - self.__cnt)
            self.move_to(
                self.__current_position[0] + dx,
                self.__current_position[1] + dy,
                w,
                h,
                pointer_id,
            )

            self.__cnt += 1
            return True
        self.__cnt = 0
        # GLib.source_remove(self.__timer)
        self.__timer = None
        if self.__current_position != self.__dest_point:
            self.move_to(self.__dest_point[0], self.__dest_point[1], w, h, pointer_id)
        return False

    @override
    def mapping_start(self, key):
        # 因为 directional pad 有四组快捷键, 所以需要将快捷键传入
        if not self.pointer_id:
            pointer_id = self.observer.occupy_id()
            if not pointer_id:
                return
            self.pointer_id = pointer_id
        if key is None:
            return None
        flag = not any(self.__active_keys.values())

        w = self.get_root().get_width()
        h = self.get_root().get_height()

        direction = self.__direction_keys.inverse[key]
        self.__active_keys[direction] = True
        self.__dest_point = self.get_point_to_move(direction)

        # 没有按下其他方向键
        if flag:
            x, y = (self.action_point_x, self.action_point_y)
            self.__current_position = (x, y)
            msg = InjectTouchEventMsg(
                action=AMontionEventAction.DOWN,
                pointer_id=self.pointer_id,
                position=(int(x), int(y), w, h),
                pressure=1.0,
                action_button=AMontionEventButtons.PRIMARY,
                buttons=AMontionEventButtons.PRIMARY,
            )
            self.observer.controller.send_msg(msg)

            self.__timer = GLib.timeout_add(
                self.__interval,
                self.update_position,
                w,
                h,
                self.pointer_id,
            )

        if self.__timer is None:
            self.move_to(
                self.__dest_point[0], self.__dest_point[1], w, h, self.pointer_id
            )

    def mapping_end(self, key: ShortCut) -> bool:
        if not self.pointer_id:
            return

        direction = self.__direction_keys.inverse[key]
        self.__active_keys[direction] = False
        w = self.get_root().get_width()
        h = self.get_root().get_height()

        # 所有的方向键均释放
        if not any(self.__active_keys.values()):
            if self.__timer:
                GLib.source_remove(self.__timer)
                self.__timer = None
            x, y = self.__current_position
            msg = InjectTouchEventMsg(
                action=AMontionEventAction.UP,
                pointer_id=self.pointer_id,
                position=(int(x), int(y), w, h),
                pressure=0.0,
                action_button=AMontionEventButtons.PRIMARY,
                buttons=0,
            )
            self.observer.controller.send_msg(msg)
            self.__current_position = (self.action_point_x, self.action_point_y)
            self.observer.release_id(self.pointer_id)
            self.pointer_id = None
            return True

        self.__dest_point = self.get_point_to_move(direction)
        if self.__timer is None:
            self.move_to(
                self.__dest_point[0], self.__dest_point[1], w, h, self.pointer_id
            )
        return False

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
        return 100

    @property
    def compact_height(self):
        return 100

    @property
    def expanded_width(self):
        return self.action_width

    @property
    def expanded_height(self):
        return self.action_height
