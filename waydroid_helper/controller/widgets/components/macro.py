#!/usr/bin/env python3
"""
宏组件
一个圆形的半透明灰色按钮，支持单击操作，可以配置宏命令
"""

import math
from gettext import pgettext
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cairo import Context, Surface, FontSlant, FontWeight
    from gi.repository import Gtk
    from waydroid_helper.controller.widgets.base.base_widget import EditableRegion

from waydroid_helper.util.log import logger

from waydroid_helper.controller.android.input import (
    AMotionEventAction,
    AMotionEventButtons,
)
from waydroid_helper.controller.core import (
    Event,
    EventType,
    event_bus,
    Key,
    KeyCombination,
    key_system,
    pointer_id_manager,
)
from waydroid_helper.controller.core.control_msg import InjectTouchEventMsg
from waydroid_helper.controller.widgets.base.base_widget import BaseWidget
from waydroid_helper.controller.widgets.decorators import (
    Editable,
)
from waydroid_helper.controller.widgets.config import create_textarea_config

import cairo


@Editable
class Macro(BaseWidget):
    """宏按钮组件 - 圆形半透明按钮"""

    # 组件元数据
    WIDGET_NAME = pgettext("Controller Widgets", "Macro")
    WIDGET_DESCRIPTION = pgettext(
        "Controller Widgets",
        "Execute a macro command when triggered.",
    )
    WIDGET_VERSION = "1.0"

    # 映射模式固定尺寸
    MAPPING_MODE_HEIGHT = 30
    MAPPING_MODE_WIDTH = 30


    def __init__(self, x:int=0, y:int=0, width:int=50, height:int=50, text:str="", default_keys:set[KeyCombination]|None=None):
        # 初始化基类，传入默认按键
        super().__init__(
            x,
            y,
            width,
            height,
            pgettext("Controller Widgets", "Macro"),
            text,
            default_keys,
            min_width=50,  # 固定大小
            min_height=50,  # 固定大小
        )
        
        self.press_command_list:list[str] = []
        self.release_command_list:list[str] = []
        
        # 设置宏命令配置
        self.setup_config()

    def setup_config(self) -> None:
        """设置配置项"""
        # 添加宏命令配置
        macro_config = create_textarea_config(
            key="macro_command",
            label=pgettext("Controller Widgets", "Macro Command"),
            value="\n".join(self.press_command_list)+"\nrelease_actions\n"+ "\n".join(self.release_command_list),
            description=pgettext("Controller Widgets", "The macro commands to execute when triggered")
        )
        self.add_config_item(macro_config)
        self.add_config_change_callback("macro_command", self.on_macro_command_changed)
    
    def on_macro_command_changed(self, key:str, value:str):
        """当宏命令文本框内容改变时，解析并存储命令列表"""
        # 使用 split(..., 1) 来确保只分割一次，更健壮
        parts = value.split("release_actions", 1)
        self.press_command_list = parts[0].strip().splitlines()
        
        if len(parts) > 1:
            self.release_command_list = parts[1].strip().splitlines()
        else:
            self.release_command_list = []
        
        logger.debug(f"宏命令已更新。按下: {len(self.press_command_list)}条, 弹起: {len(self.release_command_list)}条")

    def draw_widget_content(self, cr: 'Context[Surface]', width: int, height: int):
        """绘制圆形按钮的具体内容"""
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

    def draw_text_content(self, cr: 'Context[Surface]', width: int, height: int):
        """重写文本绘制 - 使用白色文字适配圆形按钮"""
        if self.text:
            center_x = width / 2
            center_y = height / 2

            cr.set_source_rgba(1, 1, 1, 1)  # 白色文字
            cr.select_font_face("Arial", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
            cr.set_font_size(12)
            text_extents = cr.text_extents(self.text)
            x = center_x - text_extents.width / 2
            y = center_y + text_extents.height / 2
            cr.move_to(x, y)
            cr.show_text(self.text)

            # 清除路径，避免影响后续绘制
            cr.new_path()

    def draw_selection_border(self, cr: 'Context[Surface]', width: int, height: int):
        """重写选择边框绘制 - 绘制圆形边框适配圆形按钮"""
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 5

        # 绘制圆形选择边框
        cr.set_source_rgba(0.2, 0.6, 1.0, 0.8)
        cr.set_line_width(3)
        cr.arc(center_x, center_y, radius + 3, 0, 2 * math.pi)
        cr.stroke()

    def draw_mapping_mode_background(self, cr: 'Context[Surface]', width: int, height: int):
        """映射模式下的背景绘制 - 根据文字长度的圆角矩形"""
        # 映射模式下完全透明
        pass

    def draw_mapping_mode_content(self, cr: 'Context[Surface]', width: int, height: int):
        """映射模式下的内容绘制 - 根据文字长度的圆角矩形"""
        # 映射模式下完全透明
        pass

    def on_key_triggered(self, key_combination: KeyCombination | None = None) -> bool:
        """当映射的按键被触发时的行为 - 执行预先解析好的按下宏命令"""
        if self.press_command_list:
            self._parse_and_execute_commands(self.press_command_list)
        return True

    def on_key_released(self, key_combination: KeyCombination | None = None) -> bool:
        """当映射的按键被弹起时的行为 - 执行预先解析好的弹起宏命令"""
        if self.release_command_list:
            self._parse_and_execute_commands(self.release_command_list)
        return True

    def _parse_and_execute_commands(self, commands: list[str]):
        """解析并执行一系列宏命令"""
        for command_line in commands:
            line = command_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(" ", 1)
            command = parts[0].lower()
            args_str = parts[1] if len(parts) > 1 else ""

            if command in ["key_press", "key_release"]:
                if not args_str:
                    logger.warning("宏命令: key_press 缺少参数。")
                    continue

                key_names = [k.strip() for k in args_str.split(",")]
                for name in key_names:
                    try:
                        key = key_system.deserialize_key(name)
                        event_bus.emit(
                            Event(
                                type=EventType.MACRO_KEY_PRESSED if command == "key_press" else EventType.MACRO_KEY_RELEASED,
                                source=self,
                                data=key,
                            )
                        )
                    except ValueError:
                        logger.warning(f"宏命令: 无法识别按键 '{name}'")

            elif command == "other_command":
                # 在这里可以扩展其他命令
                pass
            else:
                logger.warning(f"宏命令: 未知指令 '{command}'")

    def get_editable_regions(self)->list['EditableRegion']:
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
        return int(self.x + self.width / 2)

    @property
    def mapping_start_y(self):
        return int(self.y + self.height / 2)

    @property
    def center_x(self):
        return self.x + self.width / 2

    @property
    def center_y(self):
        return self.y + self.height / 2
