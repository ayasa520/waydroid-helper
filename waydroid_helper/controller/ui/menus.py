#!/usr/bin/env python3
"""
动态菜单管理
根据发现的组件自动生成菜单项
"""

from __future__ import annotations
from gettext import gettext as _
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

import gi
from gi.repository import Gdk, Gtk

from waydroid_helper.controller.core import key_system
from waydroid_helper.controller.core.key_system import (
    Key,
    KeyCombination,
    KeyType,
    key_registry,
)
from waydroid_helper.util.log import logger


gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

if TYPE_CHECKING:
    from waydroid_helper.controller.widgets.factory import WidgetFactory
    from waydroid_helper.controller.app.window import TransparentWindow
    from waydroid_helper.controller.widgets.base import BaseWidget


class ContextMenuManager:
    """动态上下文菜单管理器"""

    def __init__(self, parent_window: "TransparentWindow"):
        self.parent_window: "TransparentWindow" = parent_window

    def show_widget_creation_menu(
        self, x: int, y: int, widget_factory: "WidgetFactory"
    ):
        """显示动态生成的组件创建菜单"""
        popover = Gtk.Popover()
        popover.set_parent(self.parent_window)
        popover.set_has_arrow(False)
        popover.set_autohide(True)

        # 创建菜单内容
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        popover.set_child(menu_box)

        # 动态生成组件菜单项
        available_types = widget_factory.get_available_types()

        if not available_types:
            # 如果没有发现任何组件，显示提示
            label = Gtk.Label(label=_("No widgets found"))
            menu_box.append(label)
        else:
            # 为每个发现的组件类型创建菜单项
            for widget_type in sorted(available_types):
                metadata = widget_factory.get_widget_metadata(widget_type)

                # 使用metadata中的名称，如果没有则使用类型名
                display_name = metadata.get("name", widget_type.title())

                button = Gtk.Button(label=str(display_name))
                button.connect(
                    "clicked",
                    lambda btn, wtype=widget_type: [
                        self._create_widget_callback(wtype, x, y, widget_factory),
                        popover.popdown(),
                    ],
                )
                menu_box.append(button)

        # 添加分隔线
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        menu_box.append(separator)

        # 添加工具菜单项
        tool_items = [
            (_("Refresh widgets"), lambda: self._refresh_widgets(widget_factory)),
            (_("Show widget info"), lambda: self._show_widget_info(widget_factory)),
            (_("Clear all"), lambda: self._clear_all_widgets()),
            (_("Save layout"), lambda: self._save_layout()),
            (_("Load layout"), lambda: self._load_layout(widget_factory)),
        ]

        for label, callback in tool_items:
            button = Gtk.Button(label=label)
            button.connect(
                "clicked", lambda btn, cb=callback: [cb(), popover.popdown()]
            )
            menu_box.append(button)

        # 设置菜单位置
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)
        popover.popup()

    def _create_widget_callback(
        self, widget_type: str, x: int, y: int, widget_factory: "WidgetFactory"
    ):
        """创建组件的回调函数"""
        try:
            widget = widget_factory.create_widget(widget_type, x=x, y=y)
            if widget:
                self.parent_window.create_widget_at_position(widget, x, y)
                logger.debug(f"Created {widget_type} widget at position ({x}, {y})")
            else:
                logger.debug(f"Failed to create {widget_type} widget")
        except Exception as e:
            logger.debug(f"Error creating {widget_type} widget: {e}")

    def _refresh_widgets(self, widget_factory: "WidgetFactory"):
        """刷新组件列表"""
        logger.debug("Refreshing widget list...")
        widget_factory.reload_widgets()
        widget_factory.print_discovered_widgets()

    def _show_widget_info(self, widget_factory: "WidgetFactory"):
        """显示组件信息"""
        widget_factory.print_discovered_widgets()

    def _clear_all_widgets(self):
        """清空所有组件"""
        self.parent_window.on_clear_widgets(None)

    def _get_screen_size(self):
        """获取当前屏幕尺寸"""
        try:
            # 尝试从显示获取屏幕尺寸
            display = Gdk.Display.get_default()
            if display:
                monitors = display.get_monitors()
                if monitors and monitors.get_n_items() > 0:
                    monitor = monitors.get_item(0)
                    if monitor and isinstance(monitor, Gdk.Monitor):
                        geometry = monitor.get_geometry()
                        return geometry.width, geometry.height
                    else:
                        raise Exception("Failed to get monitor geometry")
                else:
                    raise Exception("No monitors found")
            else:
                raise Exception("Failed to get display information")
        except Exception as e:
            # 备用方案：使用窗口大小或默认值
            if hasattr(self.parent_window, "get_width") and hasattr(
                self.parent_window, "get_height"
            ):
                screen_width = self.parent_window.get_width() or 1920
                screen_height = self.parent_window.get_height() or 1080
                logger.warning(
                    f"Failed to get screen size({e}), using window size: {screen_width}x{screen_height}"
                )
                return screen_width, screen_height
            else:
                screen_width = 1920
                screen_height = 1080
                logger.warning(
                    f"Failed to get screen size({e}), using default value: {screen_width}x{screen_height}"
                )
                return screen_width, screen_height

    def _serialize_key_combination(self, key_combination: KeyCombination) -> list[str]:
        """序列化按键组合为字符串列表"""
        if not key_combination:
            return []
        return [str(key) for key in key_combination.keys]

    def _deserialize_key_combination(
        self, key_names: list[str]
    ) -> KeyCombination | None:
        """从字符串列表反序列化按键组合"""
        keys: list[Key] = []
        for key_name in key_names:
            key =  key_system.deserialize_key(key_name)
            if key:
                keys.append(key)
        return KeyCombination(keys) if keys else None

    def _save_layout(self):
        """保存当前布局到文件，包括屏幕尺寸信息"""
        try:
            # 获取用户主目录下的保存路径
            save_dir = Path.home() / ".controller_layouts"
            save_dir.mkdir(exist_ok=True)
            save_file = save_dir / "layout.json"

            # 获取当前屏幕尺寸
            screen_width, screen_height = self._get_screen_size()

            # 收集所有widget的信息
            widgets_data = []
            if hasattr(self.parent_window, "fixed"):
                child: "BaseWidget" | None = self.parent_window.fixed.get_first_child()
                while child:
                    # 获取widget的位置
                    x, y = child.x, child.y

                    # 获取widget的尺寸
                    width = child.width
                    height = child.height

                    # 获取widget类型
                    widget_type = type(child).__name__.lower()

                    # 创建widget数据
                    widget_data: dict[str, Any] = {
                        "type": widget_type,
                        "x": float(x),
                        "y": float(y),
                        "width": float(width),
                        "height": float(height),
                    }

                    # 如果widget有text属性，也保存
                    if hasattr(child, "text") and child.text:
                        widget_data["text"] = str(child.text)

                    # 保存按键映射 - 根据组件类型处理
                    if widget_type == "directionalpad":
                        # DirectionalPad 有四个方向的按键
                        if hasattr(child, "direction_keys") and child.direction_keys:
                            widget_data["direction_keys"] = {
                                "up": self._serialize_key_combination(
                                    child.direction_keys["up"]
                                ),
                                "down": self._serialize_key_combination(
                                    child.direction_keys["down"]
                                ),
                                "left": self._serialize_key_combination(
                                    child.direction_keys["left"]
                                ),
                                "right": self._serialize_key_combination(
                                    child.direction_keys["right"]
                                ),
                            }
                    else:
                        # 其他组件的通用按键映射
                        if hasattr(child, "final_keys") and child.final_keys:
                            widget_data["default_keys"] = [
                                self._serialize_key_combination(kc)
                                for kc in child.final_keys
                            ]
                    
                    # 保存组件配置
                    if hasattr(child, "get_config_manager"):
                        config_manager = child.get_config_manager()
                        if config_manager.configs:
                            widget_data["config"] = config_manager.serialize()

                    widgets_data.append(widget_data)
                    child = child.get_next_sibling()

            # 创建完整的布局数据，包括屏幕尺寸信息
            layout_data = {
                "version": "1.2",  # 增加版本号
                "screen_resolution": {"width": screen_width, "height": screen_height},
                "widgets": widgets_data,
                "created_at": str(Path().absolute()),  # 保存创建时间戳
            }

            # 保存到文件
            with open(save_file, "w", encoding="utf-8") as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Layout saved to: {save_file}")
            logger.info(f"Saved {len(widgets_data)} widgets")
            logger.info(f"Screen resolution: {screen_width}x{screen_height}")

        except Exception as e:
            logger.error(f"Failed to save layout: {e}")

    def _load_layout(self, widget_factory: "WidgetFactory"):
        """从文件加载布局，支持屏幕尺寸缩放适配"""
        try:
            # 获取保存文件路径
            save_dir = Path.home() / ".controller_layouts"
            save_file = save_dir / "layout.json"

            if not save_file.exists():
                logger.info(f"Layout file does not exist: {save_file}")
                return

            # 读取布局文件
            with open(save_file, "r", encoding="utf-8") as f:
                layout_data = json.load(f)

            # 验证布局数据
            if "widgets" not in layout_data:
                logger.error("Invalid layout file format")
                return

            # 获取当前屏幕尺寸
            current_screen_width, current_screen_height = self._get_screen_size()

            # 计算缩放比例
            scale_x = 1.0
            scale_y = 1.0
            saved_resolution = layout_data.get("screen_resolution")

            if saved_resolution:
                saved_width = saved_resolution.get("width", current_screen_width)
                saved_height = saved_resolution.get("height", current_screen_height)
                scale_x = current_screen_width / saved_width
                scale_y = current_screen_height / saved_height
                logger.info(
                    f"Original screen: {saved_width}x{saved_height}, current screen: {current_screen_width}x{current_screen_height}"
                )
                logger.info(f"Scale: X={scale_x:.3f}, Y={scale_y:.3f}")
            else:
                logger.info("Layout file does not have screen resolution information, not scaling")

            # 清空现有组件
            if hasattr(self.parent_window, "on_clear_widgets"):
                self.parent_window.on_clear_widgets(None)

            # 重新创建组件
            widgets_created = 0
            for widget_data in layout_data["widgets"]:
                try:
                    # 获取基本信息
                    widget_type = widget_data.get("type", "")
                    original_x = widget_data.get("x", 0)
                    original_y = widget_data.get("y", 0)
                    original_width = widget_data.get("width", 100)
                    original_height = widget_data.get("height", 100)
                    text = widget_data.get("text", "")

                    # 应用缩放比例
                    x = int(original_x * scale_x)
                    y = int(original_y * scale_y)
                    width = int(original_width * scale_x)
                    height = int(original_height * scale_y)

                    # 根据组件类型准备参数
                    create_kwargs = {"width": width, "height": height, "text": text}

                    # 添加按键映射参数
                    if widget_type == "directionalpad":
                        if "direction_keys" in widget_data:
                            create_kwargs["direction_keys"] = {
                                "up": self._deserialize_key_combination(
                                    widget_data["direction_keys"]["up"]
                                ),
                                "down": self._deserialize_key_combination(
                                    widget_data["direction_keys"]["down"]
                                ),
                                "left": self._deserialize_key_combination(
                                    widget_data["direction_keys"]["left"]
                                ),
                                "right": self._deserialize_key_combination(
                                    widget_data["direction_keys"]["right"]
                                ),
                            }
                    else:
                        # 其他组件的通用按键
                        default_keys = []
                        if "default_keys" in widget_data:
                            for key_names in widget_data["default_keys"]:
                                key_combo = self._deserialize_key_combination(key_names)
                                if key_combo:
                                    default_keys.append(key_combo)
                        create_kwargs["default_keys"] = default_keys

                    # 创建widget
                    widget = widget_factory.create_widget(widget_type, **create_kwargs)

                    if widget:
                        # 在缩放后的位置创建widget
                        if hasattr(self.parent_window, "create_widget_at_position"):
                            self.parent_window.create_widget_at_position(widget, x, y)
                            
                            # 恢复配置
                            if "config" in widget_data and hasattr(widget, "get_config_manager"):
                                config_manager = widget.get_config_manager()
                                config_manager.deserialize(widget_data["config"])
                                logger.debug(f"Restored configuration for {widget_type} widget")
                            
                            widgets_created += 1
                            logger.debug(
                                f"Restored {widget_type} widget: original position ({original_x}, {original_y}) -> new position ({x}, {y}), original size ({original_width}x{original_height}) -> new size ({width}x{height})"
                            )
                        else:
                            logger.error(
                                "Failed to create widget, missing create_widget_at_position method"
                            )
                    else:
                        logger.error(f"Failed to create {widget_type} widget")

                except Exception as e:
                    logger.error(f"Failed to create widget: {e}")
                    continue

                    # 创建widget
                    widget = widget_factory.create_widget(widget_type, **create_kwargs)

                    if widget:
                        # 在缩放后的位置创建widget
                        if hasattr(self.parent_window, "create_widget_at_position"):
                            self.parent_window.create_widget_at_position(widget, x, y)
                            widgets_created += 1
                            logger.debug(
                                f"Restored {widget_type} widget: original position ({original_x}, {original_y}) -> new position ({x}, {y}), original size ({original_width}x{original_height}) -> new size ({width}x{height})"
                            )
                        else:
                            logger.error(
                                "Failed to create widget, missing create_widget_at_position method"
                            )
                    else:
                        logger.error(f"Failed to create {widget_type} widget")

                except Exception as e:
                    logger.error(f"Failed to create widget: {e}")
                    continue

            logger.info(f"Layout loaded, restored {widgets_created} widgets")

        except Exception as e:
            logger.error(f"Failed to load layout: {e}")
