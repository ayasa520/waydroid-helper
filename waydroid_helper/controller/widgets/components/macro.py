#!/usr/bin/env python3
"""
宏组件
一个圆形的半透明灰色按钮，支持单击操作，可以配置宏命令
"""

import asyncio
import math
from gettext import pgettext
from typing import TYPE_CHECKING, cast, NamedTuple

if TYPE_CHECKING:
    from cairo import Context, Surface, FontSlant, FontWeight
    from gi.repository import Gtk
    from waydroid_helper.controller.widgets.base.base_widget import EditableRegion


class MacroCommand(NamedTuple):
    """宏命令数据结构"""
    command_type: str  # "key_press", "key_release", "sleep", "release_all"
    args: list[str]    # 命令参数

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
        "Execute macro commands when triggered.",
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
        
        # 提供一个包含 sleep 和 release_all 命令的示例
        self.press_command_list:list[str] = [ ]
        self.release_command_list:list[str] = [ ]
        
        # 设置宏命令配置
        self.setup_config()
        self.triggered:bool = False
        
        # 任务管理
        self.current_press_task: asyncio.Task[None] | None = None
        self.current_release_task: asyncio.Task[None] | None = None
        
        # 按键状态跟踪 - 记录已按下但未释放的按键
        self.pressed_keys: set[str] = set()

    def setup_config(self) -> None:
        """设置配置项"""
        # 添加宏命令配置
        macro_config = create_textarea_config(
            key="macro_command",
            label=pgettext("Controller Widgets", "Macro Command"),
            value="\n".join(self.press_command_list)+"\nrelease_actions\n"+ "\n".join(self.release_command_list),
            description=pgettext("Controller Widgets", "The macro commands to execute when triggered. Supported commands:\n"
                                                      "- key_press <key1,key2,...>: Press keys\n"
                                                      "- key_release <key1,key2,...>: Release keys\n"
                                                      "- sleep <seconds>: Delay execution (supports decimals)\n"
                                                      "- release_all: Release all currently pressed keys\n"
                                                      "- Use 'release_actions' to separate press and release commands\n"
                                                      "- Lines starting with # are comments")
        )
        self.add_config_item(macro_config)
        self.add_config_change_callback("macro_command", self.on_macro_command_changed)
    
    def on_macro_command_changed(self, key:str, value:str):
        """当宏命令文本框内容改变时，解析并存储命令列表"""
        parts = value.split("release_actions", 1)
        self.press_command_list = parts[0].strip().splitlines()
        
        if len(parts) > 1:
            self.release_command_list = parts[1].strip().splitlines()
        else:
            self.release_command_list = []
        

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
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 5

        # 绘制圆形选择边框
        cr.set_source_rgba(0.2, 0.6, 1.0, 0.8)
        cr.set_line_width(3)
        cr.arc(center_x, center_y, radius + 3, 0, 2 * math.pi)
        cr.stroke()

    def draw_mapping_mode_background(self, cr: 'Context[Surface]', width: int, height: int):
        pass

    def draw_mapping_mode_content(self, cr: 'Context[Surface]', width: int, height: int):
        pass

    def on_key_triggered(self, key_combination: KeyCombination | None = None) -> bool:
        """当映射的按键被触发时的行为 - 执行预先解析好的按下宏命令"""
        if self.current_release_task and not self.current_release_task.done():
            return True
        
        if self.current_press_task and not self.current_press_task.done():
            return True
            
        if self.press_command_list:
            self.current_press_task = asyncio.create_task(
                self._parse_and_execute_commands_async(self.press_command_list, "press")
            )
        return True

    def on_key_released(self, key_combination: KeyCombination | None = None) -> bool:
        """当映射的按键被弹起时的行为 - 执行预先解析好的弹起宏命令"""
        # 如果当前有 release task 在执行，直接返回 True
        # if self.current_release_task and not self.current_release_task.done():
        #     logger.debug("宏按键有 release task 在执行，跳过新的 release 触发")
        #     return True
        
        # 如果没有 release_command 配置，直接返回 True
        if not self.release_command_list:
            return True
            
        # 如果有 release_command 配置，终止当前的 press task（如果有）
        if self.current_press_task and not self.current_press_task.done():
            self.current_press_task.cancel()

        if self.current_release_task and not self.current_release_task.done():
            self.current_release_task.cancel()
        
        # 创建新的 release task
        self.current_release_task = asyncio.create_task(
            self._parse_and_execute_commands_async(self.release_command_list, "release")
        )
        return True

    async def _parse_and_execute_commands_async(self, commands: list[str], task_type: str = "unknown"):
        """异步解析并执行一系列宏命令"""
        try:
            for command_line in commands:
                line = command_line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split(" ", 1)
                command = parts[0].lower()
                args_str = parts[1] if len(parts) > 1 else ""

                if command in ["key_press", "key_release"]:
                    if not args_str:
                        logger.warning("Macro command: key_press missing parameters.")
                        continue

                    key_names = [k.strip() for k in args_str.split(",")]
                    for name in key_names:
                        try:
                            key = key_system.deserialize_key(name)
                            
                            # 记录按键状态
                            if command == "key_press":
                                self.pressed_keys.add(name)
                            elif command == "key_release":
                                self.pressed_keys.discard(name)
                            
                            event_bus.emit(
                                Event(
                                    type=EventType.MACRO_KEY_PRESSED if command == "key_press" else EventType.MACRO_KEY_RELEASED,
                                    source=self,
                                    data=key,
                                )
                            )
                        except ValueError:
                            logger.warning(f"Macro command: cannot recognize key '{name}'")

                elif command == "sleep":
                    # 支持 sleep 命令，非阻塞延迟
                    if not args_str:
                        logger.warning("Macro command: sleep missing parameters.")
                        continue
                    
                    try:
                        sleep_time = float(args_str)
                        if sleep_time > 0:
                            await asyncio.sleep(sleep_time)
                        else:
                            logger.warning(f"Macro command: sleep time must be greater than 0, current value: {sleep_time}")
                    except ValueError:
                        logger.warning(f"Macro command: sleep parameter is invalid '{args_str}'")

                elif command == "release_all":
                    for key_name in list(self.pressed_keys):
                        try:
                            key = key_system.deserialize_key(key_name)
                            event_bus.emit(
                                Event(
                                    type=EventType.MACRO_KEY_RELEASED,
                                    source=self,
                                    data=key,
                                )
                            )
                        except ValueError:
                            logger.warning(f"Macro command: cannot recognize key '{key_name}'")
                    
                    self.pressed_keys.clear()

                elif command == "other_command":
                    pass
                else:
                    logger.warning(f"Macro command: unknown command '{command}'")
        except asyncio.CancelledError:
            logger.debug(f"Macro command task cancelled: {task_type}")
            raise
        except Exception as e:
            logger.error(f"Macro command execution exception: {e}")
        finally:
            logger.debug(f"Macro command task completed: {task_type}")

    def trigger_release_all(self):
        """手动触发 release_all 命令"""
        for key_name in list(self.pressed_keys):
            try:
                key = key_system.deserialize_key(key_name)
                event_bus.emit(
                    Event(
                        type=EventType.MACRO_KEY_RELEASED,
                        source=self,
                        data=key,
                    )
                )
            except ValueError:
                logger.warning(f"Macro command: cannot recognize key '{key_name}'")
        self.pressed_keys.clear()


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
