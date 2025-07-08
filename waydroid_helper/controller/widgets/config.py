#!/usr/bin/env python3
"""
Widget Configuration System
统一的配置系统，提供配置项定义、UI生成、验证和序列化功能
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
import json

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from waydroid_helper.util.log import logger


class ConfigType(Enum):
    """配置项类型枚举"""
    SLIDER = auto()
    DROPDOWN = auto()
    TEXT = auto()
    NUMBER = auto()
    SWITCH = auto()
    COLOR = auto()


@dataclass
class ConfigItem(ABC):
    """配置项基类"""
    key: str
    label: str
    description: str = ""
    value: Any = None
    
    @abstractmethod
    def create_ui_widget(self) -> Gtk.Widget:
        """创建对应的UI控件"""
        pass
    
    @abstractmethod
    def get_value_from_ui(self, widget: Gtk.Widget) -> Any:
        """从UI控件获取值"""
        pass
    
    @abstractmethod
    def set_value_to_ui(self, widget: Gtk.Widget, value: Any) -> None:
        """设置值到UI控件"""
        pass
    
    @abstractmethod
    def validate(self, value: Any) -> bool:
        """验证值是否合法"""
        pass
    
    def serialize(self) -> Dict[str, Any]:
        """序列化配置项"""
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "value": self.value,
            "type": self.__class__.__name__,
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'ConfigItem':
        """反序列化配置项"""
        raise NotImplementedError("Subclasses must implement deserialize")


@dataclass
class SliderConfig(ConfigItem):
    """滑动条配置项"""
    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 1.0
    show_value: bool = True
    
    def create_ui_widget(self) -> Gtk.Widget:
        """创建滑动条UI控件"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # 标签
        label = Gtk.Label(label=self.label, xalign=0)
        label.set_tooltip_text(self.description)
        box.append(label)
        
        # 滑动条
        adjustment = Gtk.Adjustment(
            value=self.value if self.value is not None else self.min_value,
            lower=self.min_value,
            upper=self.max_value,
            step_increment=self.step,
        )
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
        scale.set_draw_value(self.show_value)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_digits(0 if self.step >= 1 else 1)
        scale.set_hexpand(True)
        
        box.append(scale)
        return box
    
    def get_value_from_ui(self, widget: Gtk.Widget) -> float:
        """从滑动条获取值"""
        if isinstance(widget, Gtk.Box):
            scale = widget.get_last_child()
            if isinstance(scale, Gtk.Scale):
                return scale.get_value()
        return self.value
    
    def set_value_to_ui(self, widget: Gtk.Widget, value: Any) -> None:
        """设置值到滑动条"""
        if isinstance(widget, Gtk.Box):
            scale = widget.get_last_child()
            if isinstance(scale, Gtk.Scale):
                scale.set_value(float(value))
    
    def validate(self, value: Any) -> bool:
        """验证值是否在有效范围内"""
        try:
            val = float(value)
            return self.min_value <= val <= self.max_value
        except (ValueError, TypeError):
            return False
    
    def serialize(self) -> Dict[str, Any]:
        """序列化滑动条配置"""
        data = super().serialize()
        data.update({
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step": self.step,
            "show_value": self.show_value,
        })
        return data


@dataclass
class DropdownConfig(ConfigItem):
    """下拉选择配置项"""
    options: List[str] = field(default_factory=list)
    option_labels: Optional[Dict[str, str]] = None
    
    def create_ui_widget(self) -> Gtk.Widget:
        """创建下拉选择UI控件"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # 标签
        label = Gtk.Label(label=self.label, xalign=0)
        label.set_tooltip_text(self.description)
        box.append(label)
        
        # 下拉框
        dropdown = Gtk.DropDown()
        
        # 创建选项列表
        string_list = Gtk.StringList()
        for option in self.options:
            display_label = (self.option_labels or {}).get(option, option)
            string_list.append(display_label)
        
        dropdown.set_model(string_list)
        
        # 设置当前选择
        if self.value in self.options:
            dropdown.set_selected(self.options.index(self.value))
        
        dropdown.set_hexpand(True)
        box.append(dropdown)
        return box
    
    def get_value_from_ui(self, widget: Gtk.Widget) -> str:
        """从下拉框获取值"""
        if isinstance(widget, Gtk.Box):
            dropdown = widget.get_last_child()
            if isinstance(dropdown, Gtk.DropDown):
                selected = dropdown.get_selected()
                if selected < len(self.options):
                    return self.options[selected]
        return self.value
    
    def set_value_to_ui(self, widget: Gtk.Widget, value: Any) -> None:
        """设置值到下拉框"""
        if isinstance(widget, Gtk.Box):
            dropdown = widget.get_last_child()
            if isinstance(dropdown, Gtk.DropDown) and value in self.options:
                dropdown.set_selected(self.options.index(value))
    
    def validate(self, value: Any) -> bool:
        """验证值是否在选项列表中"""
        return value in self.options
    
    def serialize(self) -> Dict[str, Any]:
        """序列化下拉选择配置"""
        data = super().serialize()
        data.update({
            "options": self.options,
            "option_labels": self.option_labels,
        })
        return data


@dataclass
class TextConfig(ConfigItem):
    """文本输入配置项"""
    placeholder: str = ""
    max_length: int = 0
    
    def create_ui_widget(self) -> Gtk.Widget:
        """创建文本输入UI控件"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # 标签
        label = Gtk.Label(label=self.label, xalign=0)
        label.set_tooltip_text(self.description)
        box.append(label)
        
        # 文本输入框
        entry = Gtk.Entry()
        entry.set_placeholder_text(self.placeholder)
        if self.max_length > 0:
            entry.set_max_length(self.max_length)
        if self.value:
            entry.set_text(str(self.value))
        
        entry.set_hexpand(True)
        box.append(entry)
        return box
    
    def get_value_from_ui(self, widget: Gtk.Widget) -> str:
        """从文本框获取值"""
        if isinstance(widget, Gtk.Box):
            entry = widget.get_last_child()
            if isinstance(entry, Gtk.Entry):
                return entry.get_text()
        return self.value or ""
    
    def set_value_to_ui(self, widget: Gtk.Widget, value: Any) -> None:
        """设置值到文本框"""
        if isinstance(widget, Gtk.Box):
            entry = widget.get_last_child()
            if isinstance(entry, Gtk.Entry):
                entry.set_text(str(value) if value is not None else "")
    
    def validate(self, value: Any) -> bool:
        """验证文本长度"""
        try:
            text = str(value)
            return len(text) <= self.max_length if self.max_length > 0 else True
        except:
            return False
    
    def serialize(self) -> Dict[str, Any]:
        """序列化文本配置"""
        data = super().serialize()
        data.update({
            "placeholder": self.placeholder,
            "max_length": self.max_length,
        })
        return data


@dataclass
class SwitchConfig(ConfigItem):
    """开关配置项"""
    default_value: bool = False
    
    def create_ui_widget(self) -> Gtk.Widget:
        """创建开关UI控件"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # 标签
        label = Gtk.Label(label=self.label, xalign=0)
        label.set_tooltip_text(self.description)
        box.append(label)
        
        # 开关
        switch = Gtk.Switch()
        switch.set_active(self.value if self.value is not None else self.default_value)
        switch.set_halign(Gtk.Align.END)
        
        box.append(switch)
        return box
    
    def get_value_from_ui(self, widget: Gtk.Widget) -> bool:
        """从开关获取值"""
        if isinstance(widget, Gtk.Box):
            switch = widget.get_last_child()
            if isinstance(switch, Gtk.Switch):
                return switch.get_active()
        return self.value if self.value is not None else self.default_value
    
    def set_value_to_ui(self, widget: Gtk.Widget, value: Any) -> None:
        """设置值到开关"""
        if isinstance(widget, Gtk.Box):
            switch = widget.get_last_child()
            if isinstance(switch, Gtk.Switch):
                switch.set_active(bool(value))
    
    def validate(self, value: Any) -> bool:
        """验证是否为布尔值"""
        return isinstance(value, bool)
    
    def serialize(self) -> Dict[str, Any]:
        """序列化开关配置"""
        data = super().serialize()
        data.update({
            "default_value": self.default_value,
        })
        return data


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.configs: Dict[str, ConfigItem] = {}
        self.ui_widgets: Dict[str, Gtk.Widget] = {}
        self.change_callbacks: Dict[str, List[Callable[[str, Any], None]]] = {}
    
    def add_config(self, config: ConfigItem) -> None:
        """添加配置项"""
        self.configs[config.key] = config
        self.change_callbacks[config.key] = []
    
    def get_config(self, key: str) -> Optional[ConfigItem]:
        """获取配置项"""
        return self.configs.get(key)
    
    def set_value(self, key: str, value: Any) -> bool:
        """设置配置值"""
        if key not in self.configs:
            logger.warning(f"Config key not found: {key}")
            return False
        
        config = self.configs[key]
        if not config.validate(value):
            logger.warning(f"Invalid value for config {key}: {value}")
            return False
        
        old_value = config.value
        config.value = value
        
        # 更新UI
        if key in self.ui_widgets:
            config.set_value_to_ui(self.ui_widgets[key], value)
        
        # 触发回调
        for callback in self.change_callbacks.get(key, []):
            try:
                callback(key, value)
            except Exception as e:
                logger.error(f"Error calling config change callback: {e}")
        
        logger.debug(f"Config {key} changed: {old_value} -> {value}")
        return True
    
    def get_value(self, key: str) -> Any:
        """获取配置值"""
        if key in self.configs:
            return self.configs[key].value
        return None
    
    def add_change_callback(self, key: str, callback: Callable[[str, Any], None]) -> None:
        """添加配置变更回调"""
        if key not in self.change_callbacks:
            self.change_callbacks[key] = []
        self.change_callbacks[key].append(callback)
    
    def create_ui_panel(self, parent: Optional[Gtk.Widget] = None) -> Gtk.Widget:
        """创建配置面板UI"""
        if not self.configs:
            label = Gtk.Label(label="No configuration available")
            return label
        
        # 主容器
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)
        
        # 为每个配置项创建UI
        for key, config in self.configs.items():
            try:
                widget = config.create_ui_widget()
                self.ui_widgets[key] = widget
                main_box.append(widget)
            except Exception as e:
                logger.error(f"Failed to create UI for config {key}: {e}")
        
        return main_box
    
    def collect_values_from_ui(self) -> Dict[str, Any]:
        """从UI收集所有配置值"""
        values = {}
        for key, config in self.configs.items():
            if key in self.ui_widgets:
                try:
                    value = config.get_value_from_ui(self.ui_widgets[key])
                    values[key] = value
                except Exception as e:
                    logger.error(f"Failed to get value from UI for config {key}: {e}")
        return values
    
    def apply_values_from_ui(self) -> bool:
        """从UI应用所有配置值"""
        values = self.collect_values_from_ui()
        success = True
        
        for key, value in values.items():
            if not self.set_value(key, value):
                success = False
        
        return success
    
    def serialize(self) -> Dict[str, Any]:
        """序列化所有配置"""
        return {
            key: config.serialize() for key, config in self.configs.items()
        }
    
    def deserialize(self, data: Dict[str, Any]) -> None:
        """反序列化配置"""
        for key, config_data in data.items():
            if key in self.configs:
                self.configs[key].value = config_data.get("value")
                self.set_value(key, config_data.get("value"))
    
    def clear(self) -> None:
        """清空所有配置"""
        self.configs.clear()
        self.ui_widgets.clear()
        self.change_callbacks.clear()


# 配置项工厂函数，方便创建常用配置项
def create_slider_config(key: str, label: str, value: float = 0.0, 
                        min_value: float = 0.0, max_value: float = 100.0, 
                        step: float = 1.0, description: str = "") -> SliderConfig:
    """创建滑动条配置项"""
    return SliderConfig(
        key=key, label=label, value=value, description=description,
        min_value=min_value, max_value=max_value, step=step
    )


def create_dropdown_config(key: str, label: str, options: List[str], 
                          value: Optional[str] = None, option_labels: Optional[Dict[str, str]] = None,
                          description: str = "") -> DropdownConfig:
    """创建下拉选择配置项"""
    return DropdownConfig(
        key=key, label=label, value=value or (options[0] if options else ""),
        description=description, options=options, option_labels=option_labels
    )


def create_text_config(key: str, label: str, value: str = "", 
                      placeholder: str = "", max_length: int = 0,
                      description: str = "") -> TextConfig:
    """创建文本输入配置项"""
    return TextConfig(
        key=key, label=label, value=value, description=description,
        placeholder=placeholder, max_length=max_length
    )


def create_switch_config(key: str, label: str, value: bool = False,
                        description: str = "") -> SwitchConfig:
    """创建开关配置项"""
    return SwitchConfig(
        key=key, label=label, value=value, description=description
    ) 