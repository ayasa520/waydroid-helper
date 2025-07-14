#!/usr/bin/env python3
import math
from typing import TYPE_CHECKING, cast
from gettext import pgettext

if TYPE_CHECKING:
    from cairo import Context, Surface
    from gi.repository import Gtk
    from waydroid_helper.controller.widgets.base.base_widget import EditableRegion

from waydroid_helper.controller.core.handler.event_handlers import InputEvent
from waydroid_helper.util.log import logger

from waydroid_helper.controller.widgets.decorators import (
    Resizable,
    ResizableDecorator,
)
from waydroid_helper.controller.android.input import (
    AMotionEventAction,
    AMotionEventButtons,
)
from waydroid_helper.controller.core import (
    Event,
    EventType,
    event_bus,
    KeyCombination,
    key_registry,
    pointer_id_manager,
)
from waydroid_helper.controller.core.control_msg import InjectTouchEventMsg
from waydroid_helper.controller.widgets.base.base_widget import BaseWidget
from gi.repository import GLib


@Resizable(resize_strategy=ResizableDecorator.RESIZE_CENTER)
class RightClickToWalk(BaseWidget):
    """Right click widget for work or context menu actions"""

    MAPPING_MODE_WIDTH = 30
    MAPPING_MODE_HEIGHT = 30
    WIDGET_NAME = pgettext("Controller Widgets", "Right Click to Walk")
    WIDGET_DESCRIPTION = pgettext(
        "Controller Widgets",
        "Right click widget for work or context menu actions. Map to any key to trigger right mouse button click at the widget position.",
    )
    WIDGET_VERSION = "1.0"
    IS_REENTRANT = True

    def __init__(
        self,
        x: int = 0,
        y: int = 0,
        width: int = 100,
        height: int = 100,
        text: str = "",
        default_keys: set[KeyCombination] = set(
            [KeyCombination([key_registry.get_by_name("Mouse_Right")])]
        ),
    ):
        # Initialize base class with default right-click key
        super().__init__(
            x,
            y,
            width,
            height,
            pgettext("Controller Widgets", "Right Click"),
            text,
            default_keys,
            min_width=25,
            min_height=25,
        )

        self._joystick_active: bool = False  # 摇杆是否已离开中心

        self._current_position: tuple[float, float] = (x + width / 2, y + height / 2)
        self.is_reentrant:bool = True

        # region 平滑移动系统
        self._timer_interval: int = 20  # ms
        self._move_steps_total: int = 6
        self._move_steps_count: int = 0
        self._timer: int | None = None

    def draw_widget_content(self, cr: "Context[Surface]", width: int, height: int):
        """绘制组件的具体内容 - 圆形背景，上下左右箭头，中心鼠标图标"""
        # 计算圆心和半径
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 8  # 留出边距，与 dpad 一致

        # 绘制外圆背景
        cr.set_source_rgba(0.4, 0.4, 0.4, 0.7)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.fill()

        # 绘制外圆边框
        cr.set_source_rgba(0.2, 0.2, 0.2, 0.9)
        cr.set_line_width(2)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.stroke()

        # 绘制上下左右箭头
        self._draw_direction_arrows(cr, center_x, center_y, radius)

        # 绘制中心圆 - 与 dpad 相同的样式
        inner_radius = radius * 0.3
        cr.set_source_rgba(0.6, 0.6, 0.6, 0.8)
        cr.arc(center_x, center_y, inner_radius, 0, 2 * math.pi)
        cr.fill()

        # 在中心圆里绘制鼠标图标
        self._draw_mouse_in_center(cr, center_x, center_y, inner_radius)

    def _draw_direction_arrows(
        self, cr: "Context[Surface]", center_x: float, center_y: float, radius: float
    ):
        """绘制上下左右四个方向的好看箭头 - 实心三角形样式"""
        arrow_distance = radius * 0.65  # 箭头距离中心的距离
        arrow_size = radius * 0.12  # 箭头大小

        # 箭头位置
        positions = {
            "up": (center_x, center_y - arrow_distance),
            "down": (center_x, center_y + arrow_distance),
            "left": (center_x - arrow_distance, center_y),
            "right": (center_x + arrow_distance, center_y),
        }

        # 设置箭头颜色 - 白色带轻微透明度
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.9)

        # 上箭头 ↑ - 实心三角形
        x, y = positions["up"]
        cr.move_to(x, y - arrow_size)  # 顶点
        cr.line_to(x - arrow_size * 0.6, y + arrow_size * 0.5)  # 左下
        cr.line_to(x + arrow_size * 0.6, y + arrow_size * 0.5)  # 右下
        cr.close_path()
        cr.fill()

        # 下箭头 ↓ - 实心三角形
        x, y = positions["down"]
        cr.move_to(x, y + arrow_size)  # 底点
        cr.line_to(x - arrow_size * 0.6, y - arrow_size * 0.5)  # 左上
        cr.line_to(x + arrow_size * 0.6, y - arrow_size * 0.5)  # 右上
        cr.close_path()
        cr.fill()

        # 左箭头 ← - 实心三角形
        x, y = positions["left"]
        cr.move_to(x - arrow_size, y)  # 左点
        cr.line_to(x + arrow_size * 0.5, y - arrow_size * 0.6)  # 右上
        cr.line_to(x + arrow_size * 0.5, y + arrow_size * 0.6)  # 右下
        cr.close_path()
        cr.fill()

        # 右箭头 → - 实心三角形
        x, y = positions["right"]
        cr.move_to(x + arrow_size, y)  # 右点
        cr.line_to(x - arrow_size * 0.5, y - arrow_size * 0.6)  # 左上
        cr.line_to(x - arrow_size * 0.5, y + arrow_size * 0.6)  # 左下
        cr.close_path()
        cr.fill()

        # 可选：添加轻微的边框让箭头更突出
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.3)  # 半透明黑色边框
        cr.set_line_width(0.5)

        # 重新绘制上箭头的边框
        x, y = positions["up"]
        cr.move_to(x, y - arrow_size)
        cr.line_to(x - arrow_size * 0.6, y + arrow_size * 0.5)
        cr.line_to(x + arrow_size * 0.6, y + arrow_size * 0.5)
        cr.close_path()
        cr.stroke()

        # 重新绘制下箭头的边框
        x, y = positions["down"]
        cr.move_to(x, y + arrow_size)
        cr.line_to(x - arrow_size * 0.6, y - arrow_size * 0.5)
        cr.line_to(x + arrow_size * 0.6, y - arrow_size * 0.5)
        cr.close_path()
        cr.stroke()

        # 重新绘制左箭头的边框
        x, y = positions["left"]
        cr.move_to(x - arrow_size, y)
        cr.line_to(x + arrow_size * 0.5, y - arrow_size * 0.6)
        cr.line_to(x + arrow_size * 0.5, y + arrow_size * 0.6)
        cr.close_path()
        cr.stroke()

        # 重新绘制右箭头的边框
        x, y = positions["right"]
        cr.move_to(x + arrow_size, y)
        cr.line_to(x - arrow_size * 0.5, y - arrow_size * 0.6)
        cr.line_to(x - arrow_size * 0.5, y + arrow_size * 0.6)
        cr.close_path()
        cr.stroke()

    def _draw_mouse_in_center(
        self,
        cr: "Context[Surface]",
        center_x: float,
        center_y: float,
        circle_radius: float,
    ):
        """在中心圆内绘制鼠标图标 - 右键蓝色高亮"""
        # 鼠标尺寸适应中心圆
        mouse_w = circle_radius * 1.2  # 适当大小，不超出中心圆
        mouse_h = mouse_w * 1.25  # 稍微拉高，接近真实鼠标比例
        border_width = 1.0

        # 1. 先绘制整个鼠标为白色填充
        cr.save()
        cr.translate(center_x, center_y)
        cr.scale(mouse_w / 2, mouse_h / 2)
        cr.set_source_rgba(1, 1, 1, 1)  # 白色背景
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

        # 2. 右键（右上区域）用蓝色覆盖 - 修正为右键蓝色
        cr.save()
        cr.translate(center_x, center_y)
        cr.scale(mouse_w / 2, mouse_h / 2)
        cr.set_source_rgba(0.2, 0.6, 1.0, 1.0)  # 蓝色
        cr.move_to(0, 0)
        cr.arc(0, 0, 1, math.pi * 1.5, math.pi * 2)  # 右上区域 (0° 到 90°)
        cr.line_to(0, 0)
        cr.close_path()
        cr.fill()
        cr.restore()

        # 3. 鼠标外轮廓（黑色椭圆描边）
        cr.set_line_width(border_width)
        cr.set_source_rgba(0, 0, 0, 1)
        cr.save()
        cr.translate(center_x, center_y)
        cr.scale(mouse_w / 2, mouse_h / 2)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()
        cr.stroke()

        # 4. 绘制横线分割（上半/下半）
        mouse_x = center_x - mouse_w / 2
        mouse_y = center_y - mouse_h / 2
        cr.set_line_width(border_width)
        cr.set_source_rgba(0, 0, 0, 1)
        split_y = center_y
        cr.move_to(mouse_x, split_y)
        cr.line_to(mouse_x + mouse_w, split_y)
        cr.stroke()

        # 5. 绘制竖线分割（上半左右键）
        cr.set_line_width(border_width)
        cr.set_source_rgba(0, 0, 0, 1)
        split_x = center_x
        cr.move_to(split_x, mouse_y)
        cr.line_to(split_x, split_y)
        cr.stroke()

        # 清除路径，避免影响后续绘制
        cr.new_path()

    def draw_text_content(self, cr: "Context[Surface]", width: int, height: int):
        """重写文本绘制 - 鼠标图标已在 draw_widget_content 中绘制，这里为空"""
        pass

    def draw_selection_border(self, cr: "Context[Surface]", width: int, height: int):
        """Override selection border drawing - circular border for circular button"""
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 5

        # Draw circular selection border
        cr.set_source_rgba(0.2, 0.6, 1.0, 0.8)
        cr.set_line_width(3)
        cr.arc(center_x, center_y, radius + 3, 0, 2 * math.pi)
        cr.stroke()

    def draw_mapping_mode_background(
        self, cr: "Context[Surface]", width: int, height: int
    ):
        """Mapping mode background drawing - circular background"""
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 2  # Reduce margin

        # Draw single background color circle
        cr.set_source_rgba(0.6, 0.6, 0.6, 0.5)  # Unified semi-transparent gray
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.fill()

    def draw_mapping_mode_content(
        self, cr: "Context[Surface]", width: int, height: int
    ):
        """映射模式下的内容绘制 - 只显示鼠标图标，与 fire 组件类似，右键蓝色高亮"""
        # 在映射模式下只绘制鼠标图标，尺寸与 fire 组件一致
        center_x = width / 2
        center_y = height / 2

        # 鼠标主体参数（与 fire.py 相同的尺寸）
        mouse_w = min(width, height) * 0.38
        mouse_h = mouse_w * 1.25  # 稍微拉高，接近真实鼠标比例
        mouse_x = center_x - mouse_w / 2
        mouse_y = center_y - mouse_h / 2
        border_width = 1.2

        # 1. 先绘制整个鼠标为白色填充
        cr.save()
        cr.translate(center_x, center_y)
        cr.scale(mouse_w / 2, mouse_h / 2)
        cr.set_source_rgba(1, 1, 1, 1)  # 白色背景
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

        # 2. 右键（右上区域）用蓝色覆盖 - 修正为右键蓝色
        cr.save()
        cr.translate(center_x, center_y)
        cr.scale(mouse_w / 2, mouse_h / 2)
        cr.set_source_rgba(0.2, 0.6, 1.0, 1.0)  # 蓝色
        cr.move_to(0, 0)
        cr.arc(0, 0, 1, math.pi * 1.5, math.pi * 2)  # 右上区域 (270° 到 360°)
        cr.line_to(0, 0)
        cr.close_path()
        cr.fill()
        cr.restore()

        # 3. 鼠标外轮廓（黑色椭圆描边）
        cr.set_line_width(border_width)
        cr.set_source_rgba(0, 0, 0, 1)
        cr.save()
        cr.translate(center_x, center_y)
        cr.scale(mouse_w / 2, mouse_h / 2)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()
        cr.stroke()

        # 4. 绘制横线分割（上半/下半）
        cr.set_line_width(border_width)
        cr.set_source_rgba(0, 0, 0, 1)
        split_y = center_y
        cr.move_to(mouse_x, split_y)
        cr.line_to(mouse_x + mouse_w, split_y)
        cr.stroke()

        # 5. 绘制竖线分割（上半左右键）
        cr.set_line_width(border_width)
        cr.set_source_rgba(0, 0, 0, 1)
        split_x = center_x
        cr.move_to(split_x, mouse_y)
        cr.line_to(split_x, split_y)
        cr.stroke()

        # 清除路径，避免影响后续绘制
        cr.new_path()

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
            return True  # Continue timer

        # Finish move
        # reset
        self._current_position = self._target_position
        self._timer = None
        self._joystick_active = False
        self._current_position = (self.center_x, self.center_y)
        self._emit_touch_event(AMotionEventAction.UP)
        logger.debug(
            f"Directional pad smooth move finished -> {self._current_position}"
        )
        return False  # Stop timer

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

    def _move_to(self, target: tuple[float, float], smooth: bool = False):
        """统一的移动入口点"""
        self._target_position = target
        if self._timer:
            return

        use_smooth = smooth

        if use_smooth:
            self._move_steps_count = 0
            self._timer = GLib.timeout_add(
                self._timer_interval, self._update_smooth_move
            )
            logger.debug(f"Directional pad smooth move started -> {target}")
        else:
            self._current_position = target
            if self._joystick_active:
                self._emit_touch_event(AMotionEventAction.MOVE)
            logger.debug(f"Directional pad instant move to -> {target}")

    def _get_target(
        self,
        cx: float,
        cy: float,
        r: float,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ):
        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        if length == 0:
            raise ValueError("射线方向长度为0，无法定义方向")

        # 单位方向向量
        dx /= length
        dy /= length

        # 从圆心出发沿着方向 (dx, dy)，走 r 的距离
        px = cx + dx * r
        py = cy + dy * r

        return (px, py)

    def on_key_triggered(
        self,
        key_combination: KeyCombination | None = None,
        event: "InputEvent | None" = None,
    ):
        if not event or event.position is None:
            return False
        # 获取屏幕中心坐标
        root = self.get_root()
        root = cast("Gtk.Window", root)
        w, h = root.get_width(), root.get_height()
        cur_x, cur_y = event.position
        window_center_x, window_center_y = w / 2, h / 2
        target_x, target_y = self._get_target(
            self.center_x,
            self.center_y,
            self.width / 2,
            window_center_x,
            window_center_y,
            cur_x,
            cur_y,
        )
        self._move_to((target_x, target_y), smooth=True)
        if not self._joystick_active:
            self._joystick_active = True
            logger.debug("Right click widget joystick activated")
            pointer_id = pointer_id_manager.allocate(self)
            if pointer_id is None:
                logger.error(f"Failed to allocate pointer ID for {self}")
                return False
            self._current_position = self.center_x, self.center_y
            self._emit_touch_event(AMotionEventAction.DOWN, position=(self.center_x, self.center_y))

        return True

    def on_key_released(
        self,
        key_combination: KeyCombination | None = None,
        event: "InputEvent | None" = None,
    ):
        """When mapped key is released - release right click"""
        return True

    def get_editable_regions(self) -> list["EditableRegion"]:
        """Get editable regions list - widgets supporting multi-region editing should override this method"""
        return [
            {
                "id": "default",
                "name": "Key Mapping",
                "bounds": (0, 0, self.width, self.height),
                "get_keys": lambda: self.final_keys.copy(),
                "set_keys": lambda keys: setattr(
                    self, "final_keys", set(keys) if keys else set()
                ),
            }
        ]

    @property
    def mapping_start_x(self):
        return self.x + self.width / 2 - self.MAPPING_MODE_WIDTH / 2

    @property
    def mapping_start_y(self):
        return self.y + self.height / 2 - self.MAPPING_MODE_HEIGHT / 2

    @property
    def center_x(self):
        return self.x + self.width / 2

    @property
    def center_y(self):
        return self.y + self.height / 2
