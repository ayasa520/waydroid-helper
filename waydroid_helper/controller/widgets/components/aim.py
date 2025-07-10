from __future__ import annotations
import math
from typing import TYPE_CHECKING, cast
from gettext import pgettext

from waydroid_helper.controller.android.input import (
    AMotionEventAction,
    AMotionEventButtons,
)
from waydroid_helper.controller.core import (
    Event,
    EventType,
    KeyCombination,
    event_bus,
    is_point_in_rect,
    pointer_id_manager,
)
from waydroid_helper.controller.core.control_msg import InjectTouchEventMsg
from waydroid_helper.controller.platform import get_platform
from waydroid_helper.controller.widgets import BaseWidget
from waydroid_helper.controller.widgets.config import create_slider_config, create_text_config
from waydroid_helper.controller.widgets.decorators import (
    Editable,
    Resizable,
    ResizableDecorator,
)
from waydroid_helper.util.log import logger

if TYPE_CHECKING:
    from cairo import Context, Surface
    from waydroid_helper.controller.platform import PlatformBase
    from gi.repository import Gtk
    from waydroid_helper.controller.widgets.base.base_widget import EditableRegion


@Editable
@Resizable(resize_strategy=ResizableDecorator.RESIZE_SYMMETRIC)
class Aim(BaseWidget):
    MAPPING_MODE_WIDTH = 0
    MAPPING_MODE_HEIGHT = 0
    WIDGET_NAME = pgettext("Controller Widgets", "Aim")
    WIDGET_DESCRIPTION = pgettext(
        "Controller Widgets",
        "Commonly used in shooting games. Add to the draggable view position in the game. Combined with the fire button to achieve mouse movement view and aiming. After adding, please first drag the rectangle to adjust the effective range of view rotation, which needs to correspond to the effective range that can trigger view rotation operation in the game.",
    )
    WIDGET_VERSION = "1.0"

    # 固定圆形区域大小
    CIRCLE_SIZE = 50
    CIRCLE_RADIUS = 25

    def __init__(
        self,
        x: int = 0,
        y: int = 0,
        width: int = 200,
        height: int = 150,
        text: str = "",
        default_keys: set[KeyCombination] | None = None,
    ):
        super().__init__(
            x,
            y,
            width,
            height,
            pgettext("Controller Widgets", "Aim"),
            text,
            default_keys,
            min_width=200,
            min_height=150,
        )
        self.is_triggered: bool = False
        self.platform: "PlatformBase" | None = None
        self._current_pos: tuple[int | float | None, int | float | None] = (None, None)
        self.sensitivity: int = 20
        self.setup_config()

    def setup_config(self) -> None:
        """设置配置项"""
        
        # 添加灵敏度配置
        sensitivity_config = create_slider_config(
            key="sensitivity",
            label=pgettext("Controller Widgets", "Sensitivity"),
            value=self.sensitivity,
            min_value=1,
            max_value=100,
            step=1,
            description=pgettext("Controller Widgets", "Adjusts the sensitivity of aim movement")
        )
        
        self.add_config_item(sensitivity_config)
        # 添加配置变更回调
        self.add_config_change_callback("sensitivity", self._on_sensitivity_changed)

    def _on_sensitivity_changed(self, key: str, value: int) -> None:
        """处理灵敏度配置变更"""
        try:
            self.sensitivity = int(value)
            logger.debug(f"Aim sensitivity changed to: {self.sensitivity}")
        except (ValueError, TypeError):
            logger.error(f"Invalid sensitivity value: {value}")

    def on_relative_pointer_motion(
        self, dx: float, dy: float, dx_unaccel: float, dy_unaccel: float
    ) -> None:
        """处理相对鼠标移动事件"""

        if self.is_triggered:
            logger.debug(
                f"[RELATIVE_MOTION] Aim button triggered by relative mouse motion {dx}, {dy} at {self.center_x}, {self.center_y}"
            )

            _dx = dx_unaccel * self.sensitivity / 50
            _dy = dy_unaccel * self.sensitivity / 50

            root = self.get_root()
            root = cast("Gtk.Window", root)
            w, h = root.get_width(), root.get_height()

            if self._current_pos != (None, None):
                x, y = self._current_pos
                if x is None or y is None:
                    logger.error(f"Invalid current position for Aim button")
                    return
                if not is_point_in_rect(
                    x + _dx, y + _dy, self.x, self.y, self.width, self.height
                ):
                    pointer_id = pointer_id_manager.allocate(self)
                    if pointer_id is None:
                        logger.error(f"Failed to get pointer_id for Aim button")
                        return
                    msg = InjectTouchEventMsg(
                        action=AMotionEventAction.UP,
                        pointer_id=pointer_id,
                        position=(int(x + _dx), int(y + _dy), w, h),
                        pressure=0.0,
                        action_button=AMotionEventButtons.PRIMARY,
                        buttons=0,
                    )
                    event_bus.emit(Event(EventType.CONTROL_MSG, self, msg))
                    self._current_pos = (None, None)

            if self._current_pos == (None, None):
                self._current_pos = (self.center_x, self.center_y)
                pointer_id = pointer_id_manager.allocate(self)
                if pointer_id is None:
                    logger.warning(f"Failed to allocate pointer_id for Aim button")
                    return
                msg = InjectTouchEventMsg(
                    action=AMotionEventAction.DOWN,
                    pointer_id=pointer_id,
                    position=(int(self.center_x), int(self.center_y), w, h),
                    pressure=1.0,
                    action_button=AMotionEventButtons.PRIMARY,
                    buttons=0,
                )
                event_bus.emit(Event(EventType.CONTROL_MSG, self, msg))

            if self._current_pos[0] is None or self._current_pos[1] is None:
                logger.error(f"Invalid current position for Aim button")
                return

            pointer_id = pointer_id_manager.get_allocated_id(self)
            if pointer_id is None:
                logger.error(f"Invalid pointer_id for Aim button")
                return

            self._current_pos = (self._current_pos[0] + _dx, self._current_pos[1] + _dy)
            msg = InjectTouchEventMsg(
                action=AMotionEventAction.MOVE,
                pointer_id=pointer_id,
                position=(int(self._current_pos[0]), int(self._current_pos[1]), w, h),
                pressure=1.0,
                action_button=0,
                buttons=AMotionEventButtons.PRIMARY,
            )
            event_bus.emit(Event(EventType.CONTROL_MSG, self, msg))

    def draw_widget_content(self, cr: "Context[Surface]", width: int, height: int):
        """绘制瞄准按钮的具体内容 - 中心50*50圆形区域"""
        # 计算中心位置
        center_x = width / 2
        center_y = height / 2

        # 绘制固定大小的圆形区域
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.6)  # 半透明灰色背景
        cr.arc(center_x, center_y, self.CIRCLE_RADIUS, 0, 2 * math.pi)
        cr.fill()

        # 绘制圆形边框
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.9)
        cr.set_line_width(2)
        cr.arc(center_x, center_y, self.CIRCLE_RADIUS, 0, 2 * math.pi)
        cr.stroke()

        # 绘制准心 - 四条短线
        cr.set_source_rgba(1, 1, 1, 0.9)  # 白色准心线
        cr.set_line_width(2)

        # 准心线长度
        crosshair_length = 8

        # 上方短线 (从圆的顶部向圆心延伸)
        cr.move_to(center_x, center_y - self.CIRCLE_RADIUS)
        cr.line_to(center_x, center_y - self.CIRCLE_RADIUS + crosshair_length)
        cr.stroke()

        # 下方短线 (从圆的底部向圆心延伸)
        cr.move_to(center_x, center_y + self.CIRCLE_RADIUS)
        cr.line_to(center_x, center_y + self.CIRCLE_RADIUS - crosshair_length)
        cr.stroke()

        # 左侧短线 (从圆的左侧向圆心延伸)
        cr.move_to(center_x - self.CIRCLE_RADIUS, center_y)
        cr.line_to(center_x - self.CIRCLE_RADIUS + crosshair_length, center_y)
        cr.stroke()

        # 右侧短线 (从圆的右侧向圆心延伸)
        cr.move_to(center_x + self.CIRCLE_RADIUS, center_y)
        cr.line_to(center_x + self.CIRCLE_RADIUS - crosshair_length, center_y)
        cr.stroke()

    def draw_text_content(self, cr: "Context[Surface]", width: int, height: int):
        """绘制文本内容 - 在中心圆形区域显示"""
        if self.text:
            center_x = width / 2
            center_y = height / 2

            cr.set_source_rgba(1, 1, 1, 1)  # 白色文字
            cr.select_font_face("Arial")
            cr.set_font_size(12)
            text_extents = cr.text_extents(self.text)
            x = center_x - text_extents.width / 2
            y = center_y + text_extents.height / 2
            cr.move_to(x, y)
            cr.show_text(self.text)

            # 清除路径，避免影响后续绘制
            cr.new_path()

    def draw_selection_border(self, cr: "Context[Surface]", width: int, height: int):
        """绘制选择边框 - 整个矩形区域背景色，重新绘制内容"""
        # 绘制整个矩形的半透明背景色
        cr.set_source_rgba(0.2, 0.6, 1.0, 0.3)  # 半透明蓝色背景
        cr.rectangle(0, 0, width, height)
        cr.fill()

        # 重新绘制组件内容（避免被背景色覆盖）
        self.draw_widget_content(cr, width, height)
        self.draw_text_content(cr, width, height)

        # 绘制矩形边框
        cr.set_source_rgba(0.2, 0.6, 1.0, 0.8)  # 更深的蓝色边框
        cr.set_line_width(3)
        cr.rectangle(0, 0, width, height)
        cr.stroke()

    def draw_mapping_mode_background(
        self, cr: "Context[Surface]", width: int, height: int
    ):
        """映射模式下的背景绘制 - 完全透明，什么都不绘制"""
        pass

    def draw_mapping_mode_content(
        self, cr: "Context[Surface]", width: int, height: int
    ):
        """映射模式下的内容绘制 - 完全透明，什么都不绘制"""
        pass

    def on_key_triggered(self, key_combination: KeyCombination | None = None) -> bool:
        """当映射的按键被触发时的行为 - 瞄准触发"""

        if not self.platform:
            self.platform = get_platform(self.get_root())
        if self.platform:
            self.platform.set_relative_pointer_callback(self.on_relative_pointer_motion)
        else:
            logger.error("Failed to get platform")
            return False

        if key_combination:
            used_key = str(key_combination)
        elif self.final_keys:
            used_key = str(next(iter(self.final_keys)))
        else:
            used_key = "未知按键"
        if not self.is_triggered:
            self.is_triggered = True
            self.platform.lock_pointer()
            root = self.get_root()
            root = cast("Gtk.Window", root)
            root.set_cursor_from_name("none")
            event_bus.emit(Event(type=EventType.AIM_TRIGGERED, source=self, data=None))
            logger.debug(
                f"Aim button triggered by key {used_key} at {self.center_x}, {self.center_y}"
            )
        else:
            self.is_triggered = False
            self.platform.unlock_pointer()
            root = self.get_root()
            root = cast("Gtk.Window", root)
            root.set_cursor_from_name("default")
            event_bus.emit(Event(type=EventType.AIM_RELEASED, source=self, data=None))
            if self._current_pos != (None, None):
                x, y = self._current_pos
                if x is None or y is None:
                    logger.error(f"Invalid current position for Aim button")
                    return False
                w, h = root.get_width(), root.get_height()
                pointer_id = pointer_id_manager.allocate(self)
                if pointer_id is None:
                    logger.warning(f"Failed to allocate pointer_id for Aim button")
                    return False
                msg = InjectTouchEventMsg(
                    action=AMotionEventAction.UP,
                    pointer_id=pointer_id,
                    position=(int(x), int(y), w, h),
                    pressure=0.0,
                    action_button=AMotionEventButtons.PRIMARY,
                    buttons=0,
                )
                event_bus.emit(Event(EventType.CONTROL_MSG, self, msg))
                pointer_id_manager.release(self)
                self._current_pos = (None, None)
            logger.debug(
                f"Aim button released by key {used_key} at {self.center_x}, {self.center_y}"
            )
        return True

    def on_key_released(self, key_combination: KeyCombination | None = None) -> bool:
        return True
        # """当映射的按键被弹起时的行为 - 瞄准释放"""
        # if key_combination:
        #     used_key = str(key_combination)
        # elif self.final_keys:
        #     used_key = str(next(iter(self.final_keys)))
        # else:
        #     used_key = "未知按键"
        # logging.debug(f"[RELEASE]🎯 瞄准按钮通过按键 {used_key} 被释放!")

    def get_delete_button_bounds(self) -> tuple[int, int, int, int]:
        """获取删除按钮的边界 (x, y, w, h) - 将按钮定位在中心圆的右上角边缘"""
        # 删除按钮应该在中心圆右上角, 恰好在圆边上
        size = 16
        center_x = self.width / 2
        center_y = self.height / 2

        # 45度角 (-pi/4)
        angle = -math.pi / 4

        # 删除按钮的中心点
        button_center_x = center_x + self.CIRCLE_RADIUS * math.cos(angle)
        button_center_y = center_y + self.CIRCLE_RADIUS * math.sin(angle)

        # 计算左上角坐标
        x = button_center_x - size / 2
        y = button_center_y - size / 2

        return (int(x), int(y), size, size)
    
    def get_settings_button_bounds(self) -> tuple[int, int, int, int]:
        size = 16
        center_x = self.width / 2
        center_y = self.height / 2

        angle = math.pi / 4

        button_center_x = center_x + self.CIRCLE_RADIUS * math.cos(angle)
        button_center_y = center_y + self.CIRCLE_RADIUS * math.sin(angle)

        x = button_center_x - size / 2
        y = button_center_y - size / 2

        return (int(x), int(y), size, size)

    def get_editable_regions(self) -> list["EditableRegion"]:
        """获取可编辑区域列表 - 中心50*50圆形区域为可编辑区域"""
        # 计算中心圆形区域的边界框
        center_x = self.width / 2
        center_y = self.height / 2
        circle_left = center_x - self.CIRCLE_RADIUS
        circle_top = center_y - self.CIRCLE_RADIUS

        return [
            {
                "id": "aim_center",
                "name": "瞄准区域",
                "bounds": (int(circle_left), int(circle_top), self.CIRCLE_SIZE, self.CIRCLE_SIZE),
                "get_keys": lambda: self.final_keys.copy(),
                "set_keys": lambda keys: setattr(
                    self, "final_keys", set(keys) if keys else set()
                ),
            }
        ]

    @property
    def mapping_start_x(self):
        """映射起始X坐标 - 中心位置"""
        return self.x + self.width / 2

    @property
    def mapping_start_y(self):
        """映射起始Y坐标 - 中心位置"""
        return self.y + self.height / 2

    @property
    def center_x(self):
        """中心X坐标"""
        return self.x + self.width / 2

    @property
    def center_y(self):
        """中心Y坐标"""
        return self.y + self.height / 2
