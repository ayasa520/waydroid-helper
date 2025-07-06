#!/usr/bin/env python3
"""
基础组件模块
提供可拖动和调整大小的基础组件类
"""

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, GObject

from waydroid_helper.controller.core.key_system import KeyCombination
from waydroid_helper.util.log import logger
from typing import TYPE_CHECKING, Any, Callable, TypedDict, cast

if TYPE_CHECKING:
    from cairo import Context, Surface


class EditableRegion(TypedDict):
    """可编辑区域信息"""

    id: str
    name: str
    bounds: tuple[int|float, int|float, int|float, int|float]
    get_keys: Callable[[], set[KeyCombination]]
    set_keys: Callable[[set[KeyCombination]], None]


class BaseWidget(Gtk.DrawingArea):
    """基础可拖动调整大小组件"""

    # 组件元数据 - 子类可以覆盖这些属性
    WIDGET_NAME = "Base Widget"
    WIDGET_DESCRIPTION = "Base widget, providing basic drag and select functionality"
    WIDGET_VERSION = "1.0"

    # 映射模式固定尺寸 - 子类可以覆盖这些值
    MAPPING_MODE_WIDTH = 50  # 默认映射模式宽度
    MAPPING_MODE_HEIGHT = 50  # 默认映射模式高度

    # 定义GObject属性
    __gtype_name__ = "BaseWidget"

    # 将is_selected设为可观察的属性
    is_selected = GObject.Property(type=bool, default=False)

    # 添加mapping_mode属性，用于控制绘制样式
    mapping_mode = GObject.Property(type=bool, default=False)

    def __init__(
        self,
        x:int=0,
        y:int=0,
        width:int=150,
        height:int=100,
        title:str="Component",
        text:str="",
        default_keys:set[KeyCombination]|None=None,
        min_width:int=100,
        min_height:int=100,
    ):
        super().__init__()

        # 基础属性
        self.original_width:int = width  # 保存原始尺寸
        self.original_height:int = height
        self.title:str = title
        self.text:str = text  # 显示文本，独立于按键映射

        # 编辑模式下的坐标也是业务实际使用的坐标
        self.x:int = x  # 编辑模式下x坐标
        self.y:int = y  # 编辑模式下y坐标
        self.width:int = width  # 编辑模式下宽度
        self.height:int = height  # 编辑模式下高度

        self.min_width:int = min_width
        self.min_height:int = min_height

        # 按键映射属性
        self.final_keys: set[KeyCombination] = (
            set(default_keys) if default_keys else set()
        )  # 最终保存的按键组合集合

        # 交互状态
        self.is_dragging:bool = False
        self.drag_start_x:int = 0
        self.drag_start_y:int = 0

        # 设置大小
        self.set_size_request(width, height)

        # 设置绘制函数
        self.set_draw_func(self.draw_func, None)

        # 添加事件控制器
        self.setup_event_controllers()

    @property
    def mapping_start_x(self)->float:
        return self.x

    @property
    def mapping_start_y(self)->float:
        return self.y

    def setup_event_controllers(self):
        """设置基础事件控制器 - 只处理widget特定的事件"""
        # 使组件可获得焦点（用于键盘事件）
        self.set_focusable(True)

    def draw_func(self, widget:Gtk.DrawingArea, cr:'Context[Surface]', width:int, height:int, user_data:Any):
        """基础绘制函数 - 调用子类的具体绘制方法"""
        if self.mapping_mode:
            # 映射模式下的精简绘制
            self.draw_mapping_mode(cr, width, height)
        else:
            # 编辑模式下的正常绘制
            self.draw_widget_content(cr, width, height)
            self.draw_text_content(cr, width, height)
            self.draw_selection_indicators(cr, width, height)

    def draw_widget_content(self, cr:'Context[Surface]', width:int, height:int)->None:
        """绘制widget的具体内容 - 子类应重写此方法"""
        # 默认绘制一个简单的矩形背景
        raise NotImplementedError("子类必须实现draw_widget_content方法")

    def draw_text_content(self, cr:'Context[Surface]', width:int, height:int)->None:
        """绘制文本内容 - 公共逻辑"""
        if self.text:
            raise NotImplementedError("子类必须实现draw_text_content方法")
        elif hasattr(self, "title") and self.title and self.title != "组件":
            # 如果没有text但有标题，绘制标题
            cr.set_source_rgba(0, 0, 0, 1)
            cr.select_font_face("Arial", 0, 1)
            cr.set_font_size(12)
            text_extents = cr.text_extents(self.title)
            x = (width - text_extents.width) / 2
            y = (height + text_extents.height) / 2
            cr.move_to(x, y)
            cr.show_text(self.title)

    def draw_selection_indicators(self, cr:'Context[Surface]', width:int, height:int):
        """绘制选择状态指示器"""
        if self.is_selected:
            # 绘制默认的矩形选择边框
            self.draw_selection_border(cr, width, height)

    def draw_selection_border(self, cr:'Context[Surface]', width:int, height:int)->None:
        """绘制选择边框 - 子类可以重写此方法来自定义边框样式"""
        raise NotImplementedError("子类必须实现draw_selection_border方法")

    def draw_mapping_mode(self, cr:'Context[Surface]', width:int, height:int)->None:
        """映射模式下的精简绘制"""
        # 绘制统一的背景
        self.draw_mapping_mode_background(cr, width, height)

        # 调用子类的映射模式内容绘制
        self.draw_mapping_mode_content(cr, width, height)

    def draw_mapping_mode_background(self, cr:'Context[Surface]', width:int, height:int)->None:
        """映射模式下的背景绘制 - 统一样式"""
        # 默认绘制单一背景色矩形
        cr.set_source_rgba(0.6, 0.6, 0.6, 0.5)  # 半透明灰色
        cr.rectangle(0, 0, width, height)
        cr.fill()

    def draw_mapping_mode_content(self, cr:'Context[Surface]', width:int, height:int)->None:
        """映射模式下的内容绘制 - 子类必须重写此方法"""
        # 默认什么都不绘制，子类应该重写此方法
        pass

    def set_selected(self, selected: bool)->None:
        """设置选择状态"""
        self.is_selected = selected
        self.queue_draw()

    def set_mapping_mode(self, mapping_mode: bool)->None:
        """设置映射模式"""
        if self.mapping_mode != mapping_mode:
            self.mapping_mode = mapping_mode

            if mapping_mode:
                parent = self.get_parent()
                parent = cast('Gtk.Fixed', parent)
                parent.move(self, self.mapping_start_x, self.mapping_start_y)

                self.set_size_request(self.MAPPING_MODE_WIDTH, self.MAPPING_MODE_HEIGHT)

                if hasattr(self, "set_content_width"):
                    self.set_content_width(self.MAPPING_MODE_WIDTH)
                if hasattr(self, "set_content_height"):
                    self.set_content_height(self.MAPPING_MODE_HEIGHT)

                logger.debug(
                    f"{type(self).__name__} switched to mapping mode, size: {self.width}x{self.height} -> {self.MAPPING_MODE_WIDTH}x{self.MAPPING_MODE_HEIGHT}"
                )
            else:
                parent = self.get_parent()
                parent = cast('Gtk.Fixed', parent)
                parent.move(self, self.x, self.y)

                self.set_size_request(self.width, self.height)

                if hasattr(self, "set_content_width"):
                    self.set_content_width(self.width)
                if hasattr(self, "set_content_height"):
                    self.set_content_height(self.height)

                logger.debug(
                    f"{type(self).__name__} switched to edit mode, size restored: {self.width}x{self.height}"
                )

            self.queue_draw()

    def get_widget_bounds(self):
        """获取widget的边界信息"""
        parent = self.get_parent()
        parent = cast('Gtk.Fixed', parent)
        if parent:
            x, y = parent.get_child_position(self)
            width = self.get_allocated_width()
            height = self.get_allocated_height()
            return x, y, width, height
        return 0, 0, self.width, self.height

    def on_widget_clicked(self, x, y):
        """widget被点击时的回调 - 子类可以重写"""
        pass

    def on_widget_double_clicked(self, x, y):
        """widget被双击时的回调 - 子类可以重写"""
        pass

    def on_widget_right_clicked(self, x, y):
        """widget被右键点击时的回调 - 子类可以重写"""
        pass
        return False

    def on_key_triggered(
        self, key_combination: KeyCombination|None = None
    ) -> bool:
        """按键触发时调用的方法（按键按下）

        Args:
            key_combination: 触发的按键组合
        """
        raise NotImplementedError("子类必须实现on_key_triggered方法")

    def on_key_released(self, key_combination: KeyCombination|None = None) -> bool:
        """按键弹起时调用的方法（按键弹起）

        Args:
            key_combination: 弹起的按键组合
        """
        raise NotImplementedError("子类必须实现on_key_released方法")

    def get_editable_regions(self) -> list[EditableRegion]:
        """获取可编辑区域列表 - 支持多区域编辑的widget应重写此方法

        返回格式: [
            {
                'id': 'region_id',           # 区域唯一标识
                'name': 'Region Name',       # 区域显示名称
                'bounds': (x, y, w, h),      # 区域边界 (相对于widget坐标)
                'get_keys': lambda: [...],   # 获取当前按键的函数
                'set_keys': lambda keys: ... # 设置按键的函数
            },
            ...
        ]
        """
        # 默认返回单个编辑区域（整个widget）
        return []

    def get_region_at_position(self, x:int|float, y:int|float) -> EditableRegion|None:
        """获取指定位置的区域ID - 支持多区域编辑的widget应重写此方法"""
        regions = self.get_editable_regions()
        if not regions:
            return None
        for region in regions:
            bounds = region.get("bounds")
            if bounds and len(bounds) == 4:
                rx, ry, rw, rh = bounds
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    return region
        return None
