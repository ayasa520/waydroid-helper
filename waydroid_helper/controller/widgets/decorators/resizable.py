#!/usr/bin/env python3
"""
可调整大小装饰器
为组件添加调整大小的功能
"""

import gi

gi.require_version('Gdk', '4.0')
from waydroid_helper.util.log import logger

from .base_decorator import WidgetDecorator, parameterized_widget_decorator


class ResizableDecorator(WidgetDecorator):
    """可调整大小装饰器"""
    
    # 缩放策略常量
    RESIZE_NORMAL = 0      # 普通缩放
    RESIZE_CENTER = 1      # 中心缩放
    RESIZE_SYMMETRIC = 2   # 对称缩放
    
    def __init__(self, widget, **kwargs):
        """初始化装饰器"""
        # 从参数中获取缩放策略，默认为普通缩放
        self.resize_strategy = kwargs.get('resize_strategy', self.RESIZE_NORMAL)
        
        # 初始化调整大小状态变量
        self.is_resizing_flag = False
        self.resize_direction = None
        self.original_width = 0
        self.original_height = 0
        self.original_x = 0
        self.original_y = 0
        self.global_start_x = 0
        self.global_start_y = 0
        self.current_resize_strategy = self.resize_strategy
        
        super().__init__(widget, **kwargs)
    
    def _setup_decorator(self):
        """设置可调整大小的功能"""
        # 立即Hook绘制函数
        self._hook_draw_function()
        
        logger.debug(f"ResizableDecorator applied to {type(self._wrapped_widget).__name__}")
        logger.debug(f"Resizable Hook draw function: {self._wrapped_widget.draw_func}")
        logger.debug(f"Resize strategy: {self.current_resize_strategy}")
    
    def can_resize_at_position(self, x, y, width, height):
        """检查指定位置是否可以调整大小，返回调整方向"""
        border = 8  # 边缘调整区域宽度
        
        # 检查边缘区域
        left_edge = x <= border
        right_edge = x >= width - border
        top_edge = y <= border
        bottom_edge = y >= height - border
        
        if bottom_edge and right_edge:
            return 'se'
        elif bottom_edge and left_edge:
            return 'sw'
        elif top_edge and right_edge:
            return 'ne'
        elif top_edge and left_edge:
            return 'nw'
        elif right_edge:
            return 'e'
        elif left_edge:
            return 'w'
        elif bottom_edge:
            return 's'
        elif top_edge:
            return 'n'
        
        return None
    
    def get_cursor_for_resize_area(self, resize_direction):
        """根据调整方向返回鼠标指针样式"""
        cursor_map = {
            'se': 'se-resize',
            'sw': 'sw-resize', 
            'ne': 'ne-resize',
            'nw': 'nw-resize',
            'e': 'e-resize',
            'w': 'w-resize',
            's': 's-resize',
            'n': 'n-resize'
        }
        return cursor_map.get(resize_direction)
    
    def handle_resize_with_strategy(self, resize_direction, global_dx, global_dy, 
                                  original_width, original_height, original_x, original_y, 
                                  resize_strategy):
        """根据缩放策略处理调整大小"""
        new_width = original_width
        new_height = original_height
        new_x = original_x
        new_y = original_y
        
        if resize_strategy == self.RESIZE_NORMAL:
            # 普通缩放
            if 'e' in resize_direction:
                new_width = max(50, original_width + global_dx)
            elif 'w' in resize_direction:
                new_width = max(50, original_width - global_dx)
                new_x = original_x + global_dx
                if new_width == 50:
                    new_x = original_x + original_width - 50
                    
            if 's' in resize_direction:
                new_height = max(30, original_height + global_dy)
            elif 'n' in resize_direction:
                new_height = max(30, original_height - global_dy)
                new_y = original_y + global_dy
                if new_height == 30:
                    new_y = original_y + original_height - 30
                    
        elif resize_strategy == self.RESIZE_CENTER:
            # 中心缩放 - 从中心向四个方向同时扩展
            center_x = original_x + original_width / 2
            center_y = original_y + original_height / 2
            
            # 根据拖拽方向计算实际的缩放因子
            scale_factor = 1.0
            
            if 'e' in resize_direction:
                # 向右拖拽：根据右边移动距离计算缩放因子
                scale_factor = (original_width + global_dx) / original_width if original_width > 0 else 1.0
            elif 'w' in resize_direction:
                # 向左拖拽：根据左边移动距离计算缩放因子
                scale_factor = (original_width - global_dx) / original_width if original_width > 0 else 1.0
            elif 's' in resize_direction:
                # 向下拖拽：根据下边移动距离计算缩放因子
                scale_factor = (original_height + global_dy) / original_height if original_height > 0 else 1.0
            elif 'n' in resize_direction:
                # 向上拖拽：根据上边移动距离计算缩放因子
                scale_factor = (original_height - global_dy) / original_height if original_height > 0 else 1.0
            
            # 对于角落拖拽，取较大的变化量作为缩放因子
            if len(resize_direction) == 2:  # 角落拖拽 (如 'se', 'nw' 等)
                scale_factor_x = 1.0
                scale_factor_y = 1.0
                
                if 'e' in resize_direction:
                    scale_factor_x = (original_width + global_dx) / original_width if original_width > 0 else 1.0
                elif 'w' in resize_direction:
                    scale_factor_x = (original_width - global_dx) / original_width if original_width > 0 else 1.0
                    
                if 's' in resize_direction:
                    scale_factor_y = (original_height + global_dy) / original_height if original_height > 0 else 1.0
                elif 'n' in resize_direction:
                    scale_factor_y = (original_height - global_dy) / original_height if original_height > 0 else 1.0
                
                # 对角拖拽时，选择变化更大的缩放因子
                scale_factor = scale_factor_x if abs(scale_factor_x - 1.0) > abs(scale_factor_y - 1.0) else scale_factor_y
            
            # 确保最小尺寸
            scale_factor = max(scale_factor, self._wrapped_widget.min_width / original_width, self._wrapped_widget.min_height / original_height)
            
            # 计算新的尺寸（宽高同时缩放）
            new_width = max(50, original_width * scale_factor)
            new_height = max(30, original_height * scale_factor)
            
            # 保持中心位置不变
            new_x = center_x - new_width / 2
            new_y = center_y - new_height / 2
                
        elif resize_strategy == self.RESIZE_SYMMETRIC:
            # 对称缩放
            if 'e' in resize_direction or 'w' in resize_direction:
                width_change = global_dx if 'e' in resize_direction else -global_dx
                new_width = max(50, original_width + width_change * 2)
                width_diff = new_width - original_width
                new_x = original_x - width_diff / 2
                
            if 's' in resize_direction or 'n' in resize_direction:
                height_change = global_dy if 's' in resize_direction else -global_dy
                new_height = max(30, original_height + height_change * 2)
                height_diff = new_height - original_height
                new_y = original_y - height_diff / 2
                
        return new_width, new_height, new_x, new_y
    
    def check_resize_direction(self, x, y):
        """检查鼠标位置对应的调整方向"""
        width = self._wrapped_widget.get_allocated_width()
        height = self._wrapped_widget.get_allocated_height()
        return self.can_resize_at_position(x, y, width, height)
    
    # def update_cursor_for_position(self, x, y):
    #     """根据鼠标位置更新指针样式"""
    #     resize_direction = self.check_resize_direction(x, y)
    #     if resize_direction:
    #         cursor_name = self.get_cursor_for_resize_area(resize_direction)
    #         if cursor_name:
    #             cursor = Gdk.Cursor.new_from_name(cursor_name)
    #             self._wrapped_widget.set_cursor(cursor)
    #     else:
    #         self._wrapped_widget.set_cursor(None)
    
    def start_resize(self, x, y, resize_direction):
        """开始调整大小"""
        self.is_resizing_flag = True
        self.resize_direction = resize_direction
        self.original_width = self._wrapped_widget.width
        self.original_height = self._wrapped_widget.height
        
        # 获取全局坐标
        parent = self._wrapped_widget.get_parent()
        if parent and hasattr(parent, 'get_child_position'):
            widget_x, widget_y = parent.get_child_position(self._wrapped_widget)
            self.global_start_x = widget_x + x
            self.global_start_y = widget_y + y
            self.original_x = widget_x
            self.original_y = widget_y
    
    def is_resizing(self):
        """检查是否正在调整大小"""
        return self.is_resizing_flag
    
    def on_resize_release(self):
        """调整大小释放事件"""
        self.is_resizing_flag = False
        self.resize_direction = None
    
    def handle_resize_motion(self, global_x, global_y):
        """处理调整大小的鼠标移动"""
        if not self.is_resizing_flag or not self.resize_direction:
            return
            
        # 计算全局坐标的变化量
        global_dx = global_x - self.global_start_x
        global_dy = global_y - self.global_start_y
        
        # 使用缩放策略处理调整大小
        new_width, new_height, new_x, new_y = self.handle_resize_with_strategy(
            self.resize_direction, global_dx, global_dy,
            self.original_width, self.original_height, 
            self.original_x, self.original_y,
            self.current_resize_strategy
        )
        
        # 应用变化
        self._wrapped_widget.width = new_width
        self._wrapped_widget.height = new_height
        self._wrapped_widget.x = new_x
        self._wrapped_widget.y = new_y
        self._wrapped_widget.set_size_request(new_width, new_height)
        self._wrapped_widget.set_content_height(new_height)
        self._wrapped_widget.set_content_width(new_width)

        parent = self._wrapped_widget.get_parent()
        if parent and hasattr(parent, 'move'):
            parent.move(self._wrapped_widget, new_x, new_y)
        
        self._wrapped_widget.queue_draw()
    
    def _hook_draw_function(self):
        """Hook绘制函数，在原绘制完成后添加调整大小装饰"""
        # 初始化装饰器绘制列表（如果不存在）
        if not hasattr(self._wrapped_widget, '_decorator_draws'):
            self._wrapped_widget._decorator_draws = []
            # 保存原始绘制函数
            original_draw = self._wrapped_widget.draw_func
            
            def master_draw_func(widget, cr, width, height, user_data):
                # 调用原始绘制
                original_draw(widget, cr, width, height, user_data)
                # 调用所有装饰器的绘制
                for draw_func in widget._decorator_draws:
                    draw_func(cr, width, height)
            
            # 设置主绘制函数
            self._wrapped_widget.set_draw_func(master_draw_func, None)
        
        # 添加此装饰器的绘制函数到列表
        def resize_draw(cr, width, height):
            if hasattr(self._wrapped_widget, 'is_selected') and self._wrapped_widget.is_selected:
                self.draw_resize_decorations(cr, width, height)
        
        self._wrapped_widget._decorator_draws.append(resize_draw)
    
    def draw_resize_decorations(self, cr, width, height):
        """绘制调整大小的装饰元素（手柄等）"""
        self.draw_resize_handles(cr, width, height)
    
    def draw_resize_handles(self, cr, width, height):
        """绘制调整大小的手柄"""
        handle_size = 8
        handle_color = (0.2, 0.6, 1.0, 1.0)  # 蓝色
        
        # 设置手柄样式
        cr.set_source_rgba(*handle_color)
        cr.set_line_width(1)
        
        # 四个角的位置
        positions = [
            (0, 0),                           # 左上角
            (width - handle_size, 0),         # 右上角
            (0, height - handle_size),        # 左下角
            (width - handle_size, height - handle_size)  # 右下角
        ]
        
        # 绘制四个角的小正方形
        for x, y in positions:
            cr.rectangle(x, y, handle_size, handle_size)
            cr.fill()
            
            # 绘制边框
            cr.set_source_rgba(1, 1, 1, 1)  # 白色边框
            cr.rectangle(x, y, handle_size, handle_size)
            cr.stroke()
            cr.set_source_rgba(*handle_color)  # 恢复蓝色
        
        # 中间边缘的手柄（上下左右）
        edge_positions = [
            (width/2 - handle_size/2, 0),                    # 上边
            (width/2 - handle_size/2, height - handle_size), # 下边
            (0, height/2 - handle_size/2),                   # 左边
            (width - handle_size, height/2 - handle_size/2)  # 右边
        ]
        
        for x, y in edge_positions:
            cr.rectangle(x, y, handle_size, handle_size)
            cr.fill()
            
            # 绘制边框
            cr.set_source_rgba(1, 1, 1, 1)  # 白色边框
            cr.rectangle(x, y, handle_size, handle_size)
            cr.stroke()
            cr.set_source_rgba(*handle_color)  # 恢复蓝色


# 创建参数化装饰器函数
Resizable = parameterized_widget_decorator(ResizableDecorator) 