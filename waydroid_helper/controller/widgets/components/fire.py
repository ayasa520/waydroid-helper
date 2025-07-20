import math
from typing import TYPE_CHECKING, cast
from gettext import pgettext

if TYPE_CHECKING:
    from cairo import Context, Surface
    from gi.repository import Gtk
    from waydroid_helper.controller.widgets.base.base_widget import EditableRegion

from waydroid_helper.controller.core.handler.event_handlers import InputEvent
from waydroid_helper.util.log import logger

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


class Fire(BaseWidget):
    MAPPING_MODE_WIDTH = 30
    MAPPING_MODE_HEIGHT = 30
    WIDGET_NAME = pgettext("Controller Widgets", "Fire")
    WIDGET_DESCRIPTION = pgettext(
        "Controller Widgets",
        "Commonly used in FPS games, add a button to the attack/fire button position, use the left mouse button to click, and must be used with the aim button. Note: Only supports left mouse button, cannot be modified, and won't work alone.",
    )
    WIDGET_VERSION = "1.0"

    def __init__(
        self,
        x: int = 0,
        y: int = 0,
        width: int = 50,
        height: int = 50,
        text: str = "",
        default_keys: set[KeyCombination] = set(
            [KeyCombination([key_registry.get_by_name("Mouse_Left")])]
        ),
    ):
        # 初始化基类，传入默认按键
        super().__init__(
            x,
            y,
            width,
            height,
            pgettext("Controller Widgets", "Fire"),
            text,
            default_keys,
            min_width=25,
            min_height=25,
        )
        self.aim_triggered: bool = False
        event_bus.subscribe(EventType.AIM_TRIGGERED, self._on_aim_triggered)
        event_bus.subscribe(EventType.AIM_RELEASED, self._on_aim_released)

    def _on_aim_triggered(self, event: Event[None]):
        """处理瞄准触发事件"""
        logger.debug("Fire button aim triggered")
        self.aim_triggered = True

    def _on_aim_released(self, event: Event[None]):
        """处理瞄准释放事件"""
        logger.debug("Fire button aim released")
        self.aim_triggered = False

    def draw_widget_content(self, cr: "Context[Surface]", width: int, height: int):
        """绘制开火按钮的具体内容"""
        # 计算圆心和半径
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 5  # 留出边距

        # 绘制圆形背景
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.6)

        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.fill()

        # 绘制圆形边框
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.9)
        cr.set_line_width(2)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.stroke()

    def draw_text_content(self, cr: "Context[Surface]", width: int, height: int):
        """重写文本绘制 - 绘制标准鼠标图标，左键高亮为蓝色，其余为白色，尺寸更小，蓝白互换"""
        center_x = width / 2
        center_y = height / 2

        # 鼠标主体参数（更小尺寸，不能太大）
        mouse_w = min(width, height) * 0.38
        mouse_h = mouse_w * 1.25  # 稍微拉高，接近真实鼠标比例
        mouse_x = center_x - mouse_w / 2
        mouse_y = center_y - mouse_h / 2
        border_width = 1.2

        # 1. 先绘制整个鼠标为蓝色填充
        cr.save()
        cr.translate(center_x, center_y)
        cr.scale(mouse_w / 2, mouse_h / 2)
        cr.set_source_rgba(0.2, 0.6, 1.0, 1.0)  # 蓝色
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

        # 2. 左键（左上区域）用白色覆盖
        cr.save()
        cr.translate(center_x, center_y)
        cr.scale(mouse_w / 2, mouse_h / 2)
        cr.set_source_rgba(1, 1, 1, 1)  # 白色
        cr.move_to(0, 0)
        cr.arc_negative(0, 0, 1, math.pi, math.pi * 1.5)
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

    def draw_selection_border(self, cr: "Context[Surface]", width: int, height: int):
        """重写选择边框绘制 - 绘制圆形边框适配圆形按钮"""
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
        """映射模式下的内容绘制 - 显示按键文本"""
        # 使用和编辑模式相同的文本绘制方式
        self.draw_text_content(cr, width, height)

    def on_key_triggered(
        self,
        key_combination: KeyCombination | None = None,
        event: "InputEvent | None" = None,
    ) -> bool:
        """当映射的按键被触发时的行为 - 模拟点击效果（按键按下）"""
        if not self.aim_triggered:
            return False
        if key_combination:
            used_key = str(key_combination)
        elif self.final_keys:
            used_key = str(next(iter(self.final_keys)))
        else:
            used_key = "未知按键"
        logger.debug(
            f"Fire button triggered by key {used_key} at {self.center_x}, {self.center_y}"
        )
        x, y = self.center_x, self.center_y
        root = self.get_root()
        root = cast("Gtk.Window", root)
        w, h = root.get_width(), root.get_height()
        pointer_id = pointer_id_manager.allocate(self)
        if pointer_id is None:
            logger.warning(f"Fire button cannot allocate pointer_id")
            return False
        msg = InjectTouchEventMsg(
            action=AMotionEventAction.DOWN,
            pointer_id=pointer_id,
            position=(int(x), int(y), w, h),
            pressure=1.0,
            action_button=AMotionEventButtons.PRIMARY,
            buttons=AMotionEventButtons.PRIMARY,
        )
        event_bus.emit(Event(EventType.CONTROL_MSG, self, msg))
        return True

    def on_key_released(
        self,
        key_combination: KeyCombination | None = None,
        event: "InputEvent | None" = None,
    ):
        """当映射的按键被弹起时的行为 - 模拟释放效果（按键弹起）"""
        if not self.aim_triggered:
            return False
        if key_combination:
            used_key = str(key_combination)
        elif self.final_keys:
            used_key = str(next(iter(self.final_keys)))
        else:
            used_key = "未知按键"
        logger.debug(f"Fire button released by key {used_key}")
        x, y = self.center_x, self.center_y
        root = self.get_root()
        root = cast("Gtk.Window", root)
        w, h = root.get_width(), root.get_height()
        pointer_id = pointer_id_manager.get_allocated_id(self)
        if pointer_id is None:
            logger.warning(f"Fire button cannot get pointer_id")
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
        return True

    def get_editable_regions(self) -> list["EditableRegion"]:
        """获取可编辑区域列表 - 支持多区域编辑的widget应重写此方法"""
        return [
            {
                "id": "default",
                "name": "按键映射",
                "bounds": (0, 0, self.width, self.height),
                "get_keys": lambda: self.final_keys.copy(),
                "set_keys": lambda keys: setattr(
                    self, "final_keys", set(keys) if keys else set()
                ),
            }
        ]

    @property
    def mapping_start_x(self):
        return self.x + self.width / 2

    @property
    def mapping_start_y(self):
        return self.y + self.height / 2

    @property
    def center_x(self):
        return self.x + self.width / 2

    @property
    def center_y(self):
        return self.y + self.height / 2
