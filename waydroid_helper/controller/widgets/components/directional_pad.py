#!/usr/bin/env python3
"""
方向盘组件
一个圆形的方向盘，支持上下左右四个方向的按键操作
"""

from __future__ import annotations
from enum import Enum
from gettext import pgettext
import math
from typing import TYPE_CHECKING, Callable, cast, TypedDict

from gi.repository import GLib

from waydroid_helper.controller.core.handler.event_handlers import InputEvent

if TYPE_CHECKING:
    from cairo import Context, Surface
    from gi.repository import Gtk
    from waydroid_helper.controller.widgets.base.base_widget import EditableRegion

from waydroid_helper.controller.core import KeyCombination, key_registry
from waydroid_helper.controller.core.control_msg import InjectTouchEventMsg
from waydroid_helper.controller.core.utils import pointer_id_manager
from waydroid_helper.controller.widgets import BaseWidget
from waydroid_helper.controller.widgets.config import create_dropdown_config
from waydroid_helper.controller.widgets.decorators import (
    Resizable,
    ResizableDecorator,
    Editable,
)
from waydroid_helper.controller.android.input import (
    AMotionEventAction,
    AMotionEventButtons,
)
from waydroid_helper.controller.core.event_bus import event_bus, Event, EventType
from waydroid_helper.util.log import logger

class MovementMode(Enum):
    SMOOTH = "smooth"
    INSTANT = "instant"

class DirectionalPadEditableRegion(TypedDict):
    """可编辑区域信息"""

    center: tuple[float, float]
    size: float
    key: KeyCombination | None
    name: str


# 使用带参数的 Resizable 装饰器，设置中心缩放策略
@Resizable(resize_strategy=ResizableDecorator.RESIZE_CENTER)
@Editable(max_keys=1)
class DirectionalPad(BaseWidget):
    """方向键组件"""

    MAPPING_MODE_WIDTH = 80
    MAPPING_MODE_HEIGHT = 80
    WIDGET_NAME = pgettext("Controller Widgets", "Directional Pad")
    WIDGET_DESCRIPTION = pgettext(
        "Controller Widgets",
        "Drag and place it onto the game's movement wheel to control walking direction. After assigning keys, drag the dotted frame to resize the button; make sure the blue frame of the directional pad matches the size of the game wheel.",
    )
    WIDGET_VERSION = "1.0"
    IS_REENTRANT = True  # 支持可重入，实现连续移动功能

    # 方向常量
    DIRECTIONS = ["up", "down", "left", "right"]
    DEFAULT_KEYS = {"up": "W", "down": "S", "left": "A", "right": "D"}

    def __init__(
        self,
        x: int = 0,
        y: int = 0,
        width: int = 150,
        height: int = 150,
        text: str = "",
        direction_keys: dict[str, KeyCombination | None] | None = None,
    ):

        self.direction_keys: dict[str, KeyCombination | None] = {
            "up": None,
            "down": None,
            "left": None,
            "right": None,
        }
        self._set_default_keys()
        if direction_keys is not None:
            self.direction_keys = {
                "up": direction_keys["up"],
                "down": direction_keys["down"],
                "left": direction_keys["left"],
                "right": direction_keys["right"],
            }

        # 收集所有按键到 final_keys 中（用于兼容性和显示）
        all_keys: set[KeyCombination] = set()
        for key_combo in self.direction_keys.values():
            if key_combo:
                all_keys.add(key_combo)

        # 调用基类的初始化
        super().__init__(
            x,
            y,
            width,
            height,
            pgettext("Controller Widgets", "Directional Pad"),
            text,
            set(all_keys),
            min_width=60,
            min_height=60,
        )
        # 当前按下的方向状态
        self.pressed_directions: dict[str, bool] = {
            direction: False for direction in self.DIRECTIONS
        }

        self._joystick_active: bool = False  # 摇杆是否已离开中心

        self._current_position: tuple[float, float] = (x + width / 2, y + height / 2)

        # region 平滑移动系统
        self._timer: int | None = None
        self._timer_interval: int = 20  # ms
        self._move_steps_total: int = 6
        self._move_steps_count: int = 0
        self._target_position: tuple[float, float] = self._current_position

        self._target_points_map: dict[
            tuple[bool, bool, bool, bool], Callable[[], tuple[float, float]]
        ] = {
            (True, False, False, False): lambda: self.top,  # Up
            (False, True, False, False): lambda: self.left,  # Left
            (False, False, True, False): lambda: self.bottom,  # Down
            (False, False, False, True): lambda: self.right,  # Right
            (True, True, False, False): lambda: self.top_left,
            (True, False, False, True): lambda: self.top_right,
            (False, True, True, False): lambda: self.bottom_left,
            (False, False, True, True): lambda: self.bottom_right,
            # 3-key combos resolve to the middle key's axis
            (True, True, True, False): lambda: self.left,
            (True, True, False, True): lambda: self.top,
            (True, False, True, True): lambda: self.right,
            (False, True, True, True): lambda: self.bottom,
            # 4-key combo returns to center
            (True, True, True, True): lambda: self.center,
        }

        # 初始化编辑区域字典
        self.edit_regions: dict[str, DirectionalPadEditableRegion] = {}

        
        # 计算四个方向按钮的区域（用于编辑）
        self._update_edit_regions()

        # 移动模式设置
        # self._movement_mode: MovementMode = MovementMode.SMOOTH
        movement_mode_config = create_dropdown_config(
            key="movement_mode",
            label=pgettext("Controller Widgets", "Operating Method"),
            options=[MovementMode.SMOOTH.value, MovementMode.INSTANT.value],
            option_labels={
                MovementMode.SMOOTH.value: pgettext("Controller Widgets", "Slide control"),
                MovementMode.INSTANT.value: pgettext("Controller Widgets", "Click control"),
            },
            value=MovementMode.SMOOTH.value,
            description=pgettext("Controller Widgets", "Adjusts the control method of the directional pad")
        )
        self.add_config_item(movement_mode_config)
        self.add_config_change_callback("movement_mode", lambda key, value, restoring: self.set_movement_mode(value))

    def set_movement_params(self, interval: int, max_steps: int):
        """设置平滑移动的参数"""
        self._timer_interval = interval
        self._move_steps_total = max_steps
        logger.info(
            f"Directional pad movement parameters updated: interval={interval}ms, steps={max_steps}"
        )

    def set_movement_mode(self, mode: str):
        if mode not in [MovementMode.SMOOTH.value, MovementMode.INSTANT.value]:
            logger.warning(f"Invalid movement mode: {mode}, using 'smooth'")
            # self._movement_mode = MovementMode.SMOOTH
            return
        # self._movement_mode = MovementMode(mode)
        logger.info(f"Directional pad movement mode set to: {mode}")

    def __del__(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None

    def _get_target_position(self) -> tuple[float, float]:
        """根据当前按键状态获取目标位置"""
        key_state = tuple(
            self.pressed_directions[d] for d in ["up", "left", "down", "right"]
        )
        key_state = cast(tuple[bool, bool, bool, bool], key_state)
        return self._target_points_map.get(key_state, lambda: self.center)()

    def _move_to(self, target: tuple[float, float], smooth: bool = False):
        """统一的移动入口点"""
        self._target_position = target
        if self._timer:
            # 如果正在平滑移动，只需更新目标点，让定时器完成
            return

        # 根据移动模式决定是否使用平滑移动
        use_smooth = smooth and self.get_config_value("movement_mode") == MovementMode.SMOOTH.value
        
        if use_smooth:
            self._move_steps_count = 0
            self._timer = GLib.timeout_add(
                self._timer_interval, self._update_smooth_move
            )
            logger.debug(f"Directional pad smooth move started -> {target}")
        else:
            self._current_position = target
            self.queue_draw()
            if self._joystick_active:
                self._emit_touch_event(AMotionEventAction.MOVE)
            logger.debug(f"Directional pad instant move to -> {target}")

    def _update_smooth_move(self) -> bool:
        """平滑移动的定时器回调"""
        if self._move_steps_count < self._move_steps_total:
            dx = self._target_position[0] - self._current_position[0]
            dy = self._target_position[1] - self._current_position[1]
            remaining_steps = self._move_steps_total - self._move_steps_count

            self._current_position = (
                self._current_position[0] + dx / remaining_steps,
                self._current_position[1] + dy / remaining_steps,
            )
            self._move_steps_count += 1
            if self._joystick_active:
                self._emit_touch_event(AMotionEventAction.MOVE)
            self.queue_draw()
            return True  # Continue timer

        # Finish move
        self._current_position = self._target_position
        self._timer = None
        self.queue_draw()
        logger.debug(
            f"Directional pad smooth move finished -> {self._current_position}"
        )
        return False  # Stop timer

    def _set_default_keys(self):
        """为未设置的方向设置默认按键"""
        for direction in self.DIRECTIONS:
            if not self.direction_keys[direction]:
                key_name = self.DEFAULT_KEYS[direction]
                key = key_registry.get_by_name(key_name)
                if key:
                    self.direction_keys[direction] = KeyCombination([key])

    def _update_edit_regions(self):
        """更新四个方向的编辑区域"""
        # 计算方向按钮的位置（与绘制逻辑保持一致）
        center_x = self.width / 2
        center_y = self.height / 2
        radius = min(self.width, self.height) / 2 - 8
        inner_radius = radius * 0.3
        button_radius = (radius + inner_radius) / 2
        button_size = (radius - inner_radius) / 2

        # 方向位置计算
        direction_positions = {
            "up": (center_x, center_y - button_radius),
            "down": (center_x, center_y + button_radius),
            "left": (center_x - button_radius, center_y),
            "right": (center_x + button_radius, center_y),
        }

        # 存储编辑区域信息
        self.edit_regions = {}
        for direction in self.DIRECTIONS:
            self.edit_regions[direction] = {
                "center": direction_positions[direction],
                "size": button_size,
                "key": self.direction_keys[direction],
                "name": f"{direction}方向",
            }

    def get_editable_regions(self) -> list[EditableRegion]:
        """重写：返回四个方向的可编辑区域"""
        regions: list[EditableRegion] = []

        for direction in self.DIRECTIONS:
            region_info = self.edit_regions.get(direction)
            if not region_info:
                continue

            center = region_info.get("center")
            size = region_info.get("size")
            name = region_info.get("name", direction)

            if center and size:
                center_x, center_y = center

                # 计算圆形区域的边界矩形
                bounds = (
                    int(center_x - size),
                    int(center_y - size),
                    int(size * 2),
                    int(size * 2),
                )

                regions.append(
                    {
                        "id": direction,
                        "name": name,
                        "bounds": bounds,
                        "get_keys": self._make_key_getter(direction),
                        "set_keys": self._make_key_setter(direction),
                    }
                )

        return regions

    def _make_key_getter(self, direction: str):
        """为指定方向创建按键获取函数"""

        def get_keys() -> set[KeyCombination]:
            key = self.direction_keys.get(direction)
            return {key} if key else set()

        return get_keys

    def _make_key_setter(self, direction: str) -> Callable[[set[KeyCombination]], None]:
        """为指定方向创建按键设置函数"""

        def set_keys(keys: set[KeyCombination]):
            # 设置对应方向的按键（取第一个，因为现在只支持单个按键）
            if keys:
                self.direction_keys[direction] = next(iter(keys))
            else:
                self.direction_keys[direction] = None

            # 更新编辑区域和总按键列表
            self._update_edit_regions()
            self._update_final_keys()

            # 重绘以更新显示
            self.queue_draw()

        return set_keys

    def _update_final_keys(self):
        """更新总的按键列表（用于兼容性）"""
        all_keys: set[KeyCombination] = set()
        for key_combo in self.direction_keys.values():
            if key_combo:
                all_keys.add(key_combo)
        self.final_keys: set[KeyCombination] = all_keys

    def get_all_key_mappings(self) -> dict[KeyCombination, str]:
        """获取所有按键映射的字典，用于注册到window系统"""
        mappings: dict[KeyCombination, str] = {}
        for direction, key_combo in self.direction_keys.items():
            if key_combo:
                mappings[key_combo] = direction
        return mappings

    def draw_direction_buttons(
        self,
        cr: "Context[Surface]",
        center_x: float,
        center_y: float,
        outer_radius: float,
        inner_radius: float,
    ):
        """绘制四个方向的按钮区域"""
        button_radius = (outer_radius + inner_radius) / 2
        button_size = (outer_radius - inner_radius) / 2

        # 方向位置计算
        direction_positions = {
            "up": (center_x, center_y - button_radius),
            "down": (center_x, center_y + button_radius),
            "left": (center_x - button_radius, center_y),
            "right": (center_x + button_radius, center_y),
        }

        for direction in self.DIRECTIONS:
            x, y = direction_positions[direction]
            key = self.direction_keys[direction]
            is_pressed = self.pressed_directions[direction]

            # 根据按下状态选择颜色
            if is_pressed:
                cr.set_source_rgba(0.2, 0.7, 0.2, 0.9)  # 按下时为绿色
            else:
                cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)  # 默认为灰色

            # 绘制方向按钮圆圈
            cr.arc(x, y, button_size, 0, 2 * math.pi)
            cr.fill()

            # 绘制方向按钮边框
            cr.set_source_rgba(0.3, 0.3, 0.3, 1.0)
            cr.set_line_width(1)
            cr.arc(x, y, button_size, 0, 2 * math.pi)
            cr.stroke()

            # 绘制按键文字
            key_text = str(key) if key else ""

            cr.set_source_rgba(1, 1, 1, 1)  # 白色文字
            cr.select_font_face("Arial", 0, 1)

            # 根据按键长度调整字体大小
            if len(key_text) <= 1:
                cr.set_font_size(14)
            elif len(key_text) <= 3:
                cr.set_font_size(10)
            else:
                cr.set_font_size(8)

            text_extents = cr.text_extents(key_text)
            text_x = x - text_extents.width / 2
            text_y = y + text_extents.height / 2
            cr.move_to(text_x, text_y)
            cr.show_text(key_text)
            cr.new_path()  # 清除路径

    def draw_text_content(self, cr: "Context[Surface]", width: int, height: int):
        """重写文本绘制 - 显示按键映射信息"""
        pass

    def draw_selection_border(self, cr: "Context[Surface]", width: int, height: int):
        """重写选择边框绘制 - 绘制圆形边框适配圆形方向盘"""
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 5

        # 绘制圆形选择边框
        cr.set_source_rgba(0.2, 0.6, 1.0, 0.8)
        cr.set_line_width(3)
        cr.arc(center_x, center_y, radius + 3, 0, 2 * math.pi)
        cr.stroke()

    def draw_mapping_mode_background(
        self, cr: "Context[Surface]", width: int, height: int
    ):
        """映射模式下的背景绘制 - 圆形背景"""
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 2  # 减少边距

        # 绘制单一背景色的圆形
        cr.set_source_rgba(0.6, 0.6, 0.6, 0.5)  # 统一的半透明灰色
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.fill()

    def draw_mapping_mode_content(
        self, cr: "Context[Surface]", width: int, height: int
    ):
        """映射模式下的内容绘制 - 只显示四个方向的按键文字"""
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 2  # 减少边距
        inner_radius = radius * 0.3
        button_radius = (radius + inner_radius) / 2

        # 方向位置计算
        direction_positions = {
            "up": (center_x, center_y - button_radius),
            "down": (center_x, center_y + button_radius),
            "left": (center_x - button_radius, center_y),
            "right": (center_x + button_radius, center_y),
        }

        for direction in self.DIRECTIONS:
            x, y = direction_positions[direction]
            key = self.direction_keys[direction]

            # 只绘制按键文字，不绘制按钮背景和边框
            key_text = str(key) if key else "?"

            cr.set_source_rgba(1, 1, 1, 0.9)  # 白色文字
            cr.select_font_face("Arial", 0, 1)

            # 根据按键长度调整字体大小
            if len(key_text) <= 1:
                cr.set_font_size(10)  # 映射模式下稍小的字体
            elif len(key_text) <= 3:
                cr.set_font_size(8)
            else:
                cr.set_font_size(6)

            text_extents = cr.text_extents(key_text)
            text_x = x - text_extents.width / 2
            text_y = y + text_extents.height / 2
            cr.move_to(text_x, text_y)
            cr.show_text(key_text)
            cr.new_path()  # 清除路径

        if self._joystick_active:
            self._draw_joystick_dot(cr, width, height)

    def get_direction_from_key(self, key_combination: KeyCombination) -> str | None:
        """根据按键组合获取对应的方向"""
        for direction, key in self.direction_keys.items():
            if key == key_combination:
                return direction
        return None

    def _emit_touch_event(
        self, action: AMotionEventAction, position: tuple[float, float] | None = None
    ):
        pos = position if position is not None else self._current_position
        root = self.get_root()
        if not root:
            logger.warning("Failed to get root window")
            return
        root = cast("Gtk.Window", root)
        w, h = root.get_width(), root.get_height()
        pressure = 1.0 if action != AMotionEventAction.UP else 0.0
        buttons = AMotionEventButtons.PRIMARY if action != AMotionEventAction.UP else 0
        pointer_id = pointer_id_manager.get_allocated_id(self)
        if pointer_id is None:
            logger.warning(f"Failed to get pointer ID for {self}")
            return

        msg = InjectTouchEventMsg(
            action=action,
            pointer_id=pointer_id,
            position=(int(pos[0]), int(pos[1]), w, h),
            pressure=pressure,
            action_button=AMotionEventButtons.PRIMARY,
            buttons=buttons,
        )
        event_bus.emit(Event(EventType.CONTROL_MSG, self, msg))

    def on_key_triggered(self, key_combination: KeyCombination | None = None, event: "InputEvent | None" = None) -> bool:
        """当映射的按键被触发时的行为 - 根据按键确定方向"""
        if not key_combination:
            logger.debug(f"Directional pad key triggered (no key specified)")
            return False

        direction = self.get_direction_from_key(key_combination)
        if direction:
            self.pressed_directions[direction] = True
            target = self._get_target_position()
            if not self._joystick_active:
                pointer_id = pointer_id_manager.allocate(self)
                if pointer_id is None:
                    logger.error(f"Failed to allocate pointer ID for {self}")
                    return False
                self._joystick_active = True
                self._current_position = self.center
                self._emit_touch_event(AMotionEventAction.DOWN, position=self.center)
                self._move_to(target, smooth=True)
            else:
                self._move_to(target, smooth=False)

            region_info = self.edit_regions.get(direction)
            if region_info and "center" in region_info:
                center = region_info["center"]
                center_x, center_y = center
                logger.debug(
                    f"Directional pad {direction} direction triggered by key {key_combination} at {self.x+center_x}, {self.y+center_y}"
                )

            # 这里可以调用具体的方向处理方法
            self.on_direction_triggered(direction, key_combination)
            return True
        else:
            logger.debug(f"Directional pad received unknown key: {key_combination}")
            return False

    def on_key_released(self, key_combination: KeyCombination | None = None, event: "InputEvent | None" = None) -> bool:
        """当映射的按键被弹起时的行为 - 根据按键确定方向"""
        if not key_combination:
            logger.debug(f"Directional pad key released (no key specified)")
            return False

        direction = self.get_direction_from_key(key_combination)
        if direction:
            self.pressed_directions[direction] = False
            logger.debug(
                f"Directional pad {direction} direction released by key {key_combination}"
            )

            if not any(self.pressed_directions.values()):
                # 所有键释放: 停用摇杆，瞬移回中心
                self._joystick_active = False
                if self._timer:
                    GLib.source_remove(self._timer)
                    self._timer = None
                self._emit_touch_event(AMotionEventAction.UP)
                pointer_id_manager.release(self)
                self._move_to(self.center, smooth=False)
                logger.debug("All keys released, joystick returned to center")
            else:
                # 还有其他键按下: 更新目标位置并瞬移
                self._move_to(self._get_target_position(), smooth=False)
            # 这里可以调用具体的方向处理方法
            self.on_direction_released(direction, key_combination)
            return True
        else:
            logger.debug(
                f"Directional pad received unknown key release: {key_combination}"
            )
            return False

    def _draw_joystick_dot(
        self, cr: "Context[Surface]", map_width: int, map_height: int
    ):
        """在映射模式下绘制代表摇杆位置的红点"""
        # 1. 计算摇杆相对于其编辑模式中心的归一化偏移
        edit_center_x, edit_center_y = self.center
        offset_x = self._current_position[0] - edit_center_x
        offset_y = self._current_position[1] - edit_center_y

        edit_radius_x = self.width / 2
        edit_radius_y = self.height / 2

        norm_x = offset_x / edit_radius_x if edit_radius_x != 0 else 0
        norm_y = offset_y / edit_radius_y if edit_radius_y != 0 else 0

        # 2. 将归一化偏移应用到映射模式的尺寸上
        map_center_x, map_center_y = map_width / 2, map_height / 2
        draw_x = map_center_x + norm_x * (map_width / 2)
        draw_y = map_center_y + norm_y * (map_height / 2)

        # 3. 绘制红点
        cr.set_source_rgba(1.0, 0.2, 0.2, 0.9)
        cr.arc(draw_x, draw_y, 4, 0, 2 * math.pi)
        cr.fill()

    def on_direction_triggered(self, direction: str, key_combination: KeyCombination):
        """方向被触发时的具体处理 - 子类可以重写此方法"""
        logger.debug(
            f"Directional pad {direction} direction activated: {key_combination}"
        )

    def on_direction_released(self, direction: str, key_combination: KeyCombination):
        """方向被释放时的具体处理 - 子类可以重写此方法"""
        logger.debug(
            f"Directional pad {direction} direction released: {key_combination}"
        )

    def on_resize_release(self):
        """调整大小完成后重新计算编辑区域"""
        self._update_edit_regions()
        self._move_to(self._get_target_position())
        logger.debug(
            f"Directional pad size adjusted, re-calculating edit regions: {self.width}x{self.height}"
        )

    def draw_widget_content(self, cr: "Context[Surface]", width: int, height: int):
        """绘制圆形按钮的具体内容 - 重写以监听尺寸变化"""
        # 检查尺寸是否改变
        if width != self.width or height != self.height:
            self.width = width
            self.height = height
            self._update_edit_regions()
            logger.debug(
                f"Directional pad size changed, re-calculating edit regions: {width}x{height}"
            )

        # 调用原来的绘制逻辑
        self._draw_directional_pad_content(cr, width, height)

    def _draw_directional_pad_content(
        self, cr: "Context[Surface]", width: int, height: int
    ):
        """绘制方向盘的原始内容"""
        # 计算圆心和半径
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 8  # 留出边距

        # 绘制外圆背景
        cr.set_source_rgba(0.4, 0.4, 0.4, 0.7)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.fill()

        # 绘制外圆边框
        cr.set_source_rgba(0.2, 0.2, 0.2, 0.9)
        cr.set_line_width(2)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.stroke()

        # 绘制中心圆
        inner_radius = radius * 0.3
        cr.set_source_rgba(0.6, 0.6, 0.6, 0.8)
        cr.arc(center_x, center_y, inner_radius, 0, 2 * math.pi)
        cr.fill()

        # 绘制四个方向的按钮区域和文字
        self.draw_direction_buttons(cr, center_x, center_y, radius, inner_radius)

    @property
    def mapping_start_x(self):
        return int(self.x + self.width / 2 - self.MAPPING_MODE_WIDTH / 2)

    @property
    def mapping_start_y(self):
        return int(self.y + self.height / 2 - self.MAPPING_MODE_HEIGHT / 2)

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def left(self):
        return (self.x, self.y + self.height / 2)

    @property
    def right(self):
        return (self.x + self.width, self.y + self.height / 2)

    @property
    def top(self):
        return (self.x + self.width / 2, self.y)

    @property
    def bottom(self):
        return (self.x + self.width / 2, self.y + self.height)

    @property
    def top_left(self) -> tuple[float, float]:
        r = min(self.width, self.height) / 2
        return (self.center[0] - 0.7071 * r, self.center[1] - 0.7071 * r)

    @property
    def top_right(self) -> tuple[float, float]:
        r = min(self.width, self.height) / 2
        return (self.center[0] + 0.7071 * r, self.center[1] - 0.7071 * r)

    @property
    def bottom_left(self) -> tuple[float, float]:
        r = min(self.width, self.height) / 2
        return (self.center[0] - 0.7071 * r, self.center[1] + 0.7071 * r)

    @property
    def bottom_right(self) -> tuple[float, float]:
        r = min(self.width, self.height) / 2
        return (self.center[0] + 0.7071 * r, self.center[1] + 0.7071 * r)
