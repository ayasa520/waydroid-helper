#!/usr/bin/env python3
"""
技能释放按钮组件
一个圆形的半透明灰色按钮，支持技能释放操作
"""

import math
import time
from gettext import pgettext
from typing import TYPE_CHECKING, cast
from enum import Enum

if TYPE_CHECKING:
    from cairo import Context, Surface, FontSlant, FontWeight
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
    pointer_id_manager,
)
from waydroid_helper.controller.core.control_msg import InjectTouchEventMsg
from waydroid_helper.controller.widgets.base.base_widget import BaseWidget
from waydroid_helper.controller.widgets.config import (
    create_slider_config,
    create_dropdown_config,
)
from waydroid_helper.controller.widgets.decorators import (
    Resizable,
    ResizableDecorator,
    Editable,
)
from gi.repository import GLib
import cairo


class SkillState(Enum):
    """技能释放状态枚举"""
    INACTIVE = "inactive"      # 未激活
    MOVING = "moving"          # 移动中（向目标位置移动）
    ACTIVE = "active"          # 激活状态（可以瞬移）
    LOCKED = "locked"          # 锁定状态（手动释放模式）


class CastTiming(Enum):
    """施法时机枚举"""
    ON_RELEASE = "on_release"    # 松开释放
    IMMEDIATE = "immediate"      # 立即释放
    MANUAL = "manual"           # 手动释放


@Editable
@Resizable(resize_strategy=ResizableDecorator.RESIZE_CENTER)
class SkillCasting(BaseWidget):
    """技能释放按钮组件 - 圆形半透明按钮"""

    # 组件元数据
    WIDGET_NAME = pgettext("Controller Widgets", "Skill Casting")
    WIDGET_DESCRIPTION = pgettext(
        "Controller Widgets",
        "Skill casting widget that detects real-time mouse position for directional casting.",
    )
    WIDGET_VERSION = "1.0"

    # 映射模式固定尺寸
    MAPPING_MODE_HEIGHT = 30

    @property
    def MAPPING_MODE_WIDTH(self):
        """根据文字长度计算映射模式宽度，与draw_mapping_mode_background的逻辑保持一致"""
        if self.text:
            # 估算文字宽度：对于12px的Arial字体
            # 英文数字字符平均约7-8px，为保险起见用8px
            # 中文字符约12px，这里简化统一按8px估算（略保守）
            estimated_text_width = len(self.text) * 8

            # 加上左右内边距 (padding_x = 8 * 2 = 16)
            padding_x = 8
            rect_width = estimated_text_width + 2 * padding_x

            # 确保最小宽度 24，与draw_mapping_mode_background一致
            rect_width = max(rect_width, 24)

            # 为了保险起见，再加4px缓冲，确保不会被截断
            return rect_width + 4
        else:
            # 无文字时的默认宽度，与draw_mapping_mode_background的default保持一致
            return 24 + 4  # 24是最小宽度，+4是缓冲

    def __init__(
        self,
        x: int = 0,
        y: int = 0,
        width: int = 50,
        height: int = 50,
        text: str = "",
        default_keys: set[KeyCombination] | None = None,
    ):
        # 初始化基类，传入默认按键
        super().__init__(
            x,
            y,
            width,
            height,
            pgettext("Controller Widgets", "Skill Casting"),
            text,
            default_keys,
            min_width=25,
            min_height=25,
        )
        
        # 技能状态管理
        self._skill_state: SkillState = SkillState.INACTIVE
        self._current_position: tuple[float, float] = (x + width / 2, y + height / 2)
        self._target_position: tuple[float, float] = (x + width / 2, y + height / 2)
        self.is_reentrant: bool = True
        
        # 平滑移动系统
        self._timer_interval: int = 20  # ms
        self._move_steps_total: int = 6
        self._move_steps_count: int = 0
        self._move_timer: int | None = None
        
        # 圆形映射参数（像素值）
        self.circle_radius: int = 200  # 圆半径，单位像素
        self._mouse_x: float = 0
        self._mouse_y: float = 0
        
        # 施法时机配置
        self.cast_timing: str = CastTiming.ON_RELEASE.value  # 默认为松开释放
        
        # 设置配置项
        self.setup_config()
        
        # 监听选中状态变化，用于圆形绘制通知
        self.connect('notify::is-selected', self._on_selection_changed)

        event_bus.subscribe(EventType.MOUSE_MOTION, lambda event: (self.on_key_triggered(None, event.data), None)[1])

    def setup_config(self) -> None:
        """设置配置项"""
        
        # 添加圆半径配置
        circle_radius_config = create_slider_config(
            key="circle_radius",
            label=pgettext("Controller Widgets", "Circle Radius (px)"),
            value=self.circle_radius,
            min_value=50,
            max_value=500,
            step=10,
            description=pgettext(
                "Controller Widgets", "Adjusts the radius of the skill casting circle range in pixels"
            ),
        )
        
        # 添加施法时机配置
        cast_timing_config = create_dropdown_config(
            key="cast_timing",
            label=pgettext("Controller Widgets", "Cast Timing"),
            options=[CastTiming.ON_RELEASE.value, CastTiming.IMMEDIATE.value, CastTiming.MANUAL.value],
            option_labels={
                CastTiming.ON_RELEASE.value: pgettext("Controller Widgets", "On Release"),
                CastTiming.IMMEDIATE.value: pgettext("Controller Widgets", "Immediate"),
                CastTiming.MANUAL.value: pgettext("Controller Widgets", "Manual"),
            },
            value=self.cast_timing,
            description=pgettext(
                "Controller Widgets", "Determines when the skill casting ends: On Release (default), Immediate (auto-release after moving), or Manual (sticky mode)"
            ),
        )
        
        self.add_config_item(circle_radius_config)
        self.add_config_item(cast_timing_config)
        
        # 添加配置变更回调
        self.add_config_change_callback("circle_radius", self._on_circle_radius_changed)
        self.add_config_change_callback("cast_timing", self._on_cast_timing_changed)

    def _on_circle_radius_changed(self, key: str, value: int) -> None:
        """处理圆半径配置变更"""
        try:
            self.circle_radius = int(value)
            # 如果当前选中状态，重新发送圆形绘制事件
            self._update_circle_if_selected()
        except (ValueError, TypeError):
            logger.error(f"Invalid circle radius value: {value}")

    def _on_cast_timing_changed(self, key: str, value: str) -> None:
        """处理施法时机配置变更"""
        try:
            self.cast_timing = str(value)
        except (ValueError, TypeError):
            logger.error(f"Invalid cast timing value: {value}")

    def _update_circle_if_selected(self):
        """如果当前组件被选中，更新圆形绘制"""
        if self.is_selected:
            circle_data = {
                'widget_id': id(self),
                'widget_type': 'skill_casting',
                'circle_radius': self.circle_radius,
                'action': 'show'
            }
            event_bus.emit(Event(EventType.WIDGET_SELECTION_OVERLAY, self, circle_data))

    def _on_selection_changed(self, widget, pspec):
        """当选中状态变化时的回调"""
        if self.is_selected:
            # 发送显示圆形的事件
            circle_data = {
                'widget_id': id(self),
                'widget_type': 'skill_casting',
                'circle_radius': self.circle_radius,
                'action': 'show'
            }
            event_bus.emit(Event(EventType.WIDGET_SELECTION_OVERLAY, self, circle_data))
        else:
            # 发送隐藏圆形的事件
            circle_data = {
                'widget_id': id(self),
                'widget_type': 'skill_casting',
                'action': 'hide'
            }
            event_bus.emit(Event(EventType.WIDGET_SELECTION_OVERLAY, self, circle_data))

    def draw_widget_content(self, cr: "Context[Surface]", width: int, height: int):
        """绘制圆形按钮的具体内容"""
        # 计算圆心和半径
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 5  # 留出边距

        # 绘制圆形背景
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.6)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.fill()

        # 绘制雷达扫描效果
        # 绘制同心圆（类似雷达的圆圈）- 从内向外颜色加深
        # 内圆 - 最浅灰色 (133/400 = 0.33)
        inner_radius = radius * 0.33
        cr.set_source_rgba(0.8, 0.8, 0.8, 0.8)  # 最浅灰色
        cr.arc(center_x, center_y, inner_radius, 0, 2 * math.pi)
        cr.fill()
        
        # 中圆 - 中等灰色 (266/400 = 0.66)
        middle_radius = radius * 0.66
        cr.set_source_rgba(0.6, 0.6, 0.6, 0.8)  # 中等灰色
        cr.arc(center_x, center_y, middle_radius, 0, 2 * math.pi)
        cr.fill()
        
        # 外圆已经是原本的圆形背景(0.5, 0.5, 0.5, 0.6)，是最深的，保持不变
        
        # 绘制135度扇形朝上 - 透明度高
        cr.set_source_rgba(64/255, 224/255, 208/255, 0.25)  # 青绿色，透明度0.25
        cr.move_to(center_x, center_y)
        # 135度扇形，以向上(-π/2)为中心，向两边扩展67.5度
        start_angle_135 = -math.pi / 2 - 135 * math.pi / 360  # 向上中心-67.5度
        end_angle_135 = -math.pi / 2 + 135 * math.pi / 360   # 向上中心+67.5度
        cr.arc(center_x, center_y, radius, start_angle_135, end_angle_135)
        cr.close_path()
        cr.fill()
        
        # 绘制45度扇形朝上 - 透明度低
        cr.set_source_rgba(64/255, 224/255, 208/255, 0.15)  # 青绿色，透明度0.15
        cr.move_to(center_x, center_y)
        # 45度扇形，以向上(-π/2)为中心，向两边扩展22.5度
        start_angle_45 = -math.pi / 2 - 45 * math.pi / 360   # 向上中心-22.5度
        end_angle_45 = -math.pi / 2 + 45 * math.pi / 360     # 向上中心+22.5度
        cr.arc(center_x, center_y, radius, start_angle_45, end_angle_45)
        cr.close_path()
        cr.fill()

        # 绘制圆形边框
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.9)
        cr.set_line_width(2)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.stroke()

    def draw_text_content(self, cr: "Context[Surface]", width: int, height: int):
        """重写文本绘制 - 使用白色文字适配圆形按钮"""
        if self.text:
            center_x = width / 2
            center_y = height / 2

            cr.set_source_rgba(1, 1, 1, 1)  # 白色文字
            cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(12)
            text_extents = cr.text_extents(self.text)
            x = center_x - text_extents.width / 2
            y = center_y + text_extents.height / 2
            cr.move_to(x, y)
            cr.show_text(self.text)

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
        """映射模式下的背景绘制 - 根据文字长度的圆角矩形"""
        center_x = width / 2
        center_y = height / 2

        # 计算文字尺寸
        if self.text:
            cr.set_font_size(12)
            text_extents = cr.text_extents(self.text)
            text_width = text_extents.width
            text_height = text_extents.height
        else:
            text_width = 20  # 默认宽度
            text_height = 12  # 默认高度

        # 圆角矩形参数
        padding_x = 8  # 左右内边距
        padding_y = 4  # 上下内边距
        corner_radius = 6  # 圆角半径

        rect_width = text_width + 2 * padding_x
        rect_height = text_height + 2 * padding_y

        # 确保矩形不会太小
        rect_width = max(rect_width, 24)
        rect_height = max(rect_height, 16)

        # 计算矩形位置（居中）
        rect_x = center_x - rect_width / 2
        rect_y = center_y - rect_height / 2

        # 绘制圆角矩形背景
        cr.set_source_rgba(0.6, 0.6, 0.6, 0.7)  # 稍微加深一点透明度

        # 使用路径绘制圆角矩形
        # 左上角
        cr.move_to(rect_x + corner_radius, rect_y)
        # 上边
        cr.line_to(rect_x + rect_width - corner_radius, rect_y)
        # 右上角
        cr.arc(
            rect_x + rect_width - corner_radius,
            rect_y + corner_radius,
            corner_radius,
            -math.pi / 2,
            0,
        )
        # 右边
        cr.line_to(rect_x + rect_width, rect_y + rect_height - corner_radius)
        # 右下角
        cr.arc(
            rect_x + rect_width - corner_radius,
            rect_y + rect_height - corner_radius,
            corner_radius,
            0,
            math.pi / 2,
        )
        # 下边
        cr.line_to(rect_x + corner_radius, rect_y + rect_height)
        # 左下角
        cr.arc(
            rect_x + corner_radius,
            rect_y + rect_height - corner_radius,
            corner_radius,
            math.pi / 2,
            math.pi,
        )
        # 左边
        cr.line_to(rect_x, rect_y + corner_radius)
        # 左上角
        cr.arc(
            rect_x + corner_radius,
            rect_y + corner_radius,
            corner_radius,
            math.pi,
            3 * math.pi / 2,
        )
        cr.close_path()
        cr.fill()

        # 绘制圆角矩形边框
        cr.set_source_rgba(0.4, 0.4, 0.4, 0.9)
        cr.set_line_width(1)
        # 重复上面的路径
        cr.move_to(rect_x + corner_radius, rect_y)
        cr.line_to(rect_x + rect_width - corner_radius, rect_y)
        cr.arc(
            rect_x + rect_width - corner_radius,
            rect_y + corner_radius,
            corner_radius,
            -math.pi / 2,
            0,
        )
        cr.line_to(rect_x + rect_width, rect_y + rect_height - corner_radius)
        cr.arc(
            rect_x + rect_width - corner_radius,
            rect_y + rect_height - corner_radius,
            corner_radius,
            0,
            math.pi / 2,
        )
        cr.line_to(rect_x + corner_radius, rect_y + rect_height)
        cr.arc(
            rect_x + corner_radius,
            rect_y + rect_height - corner_radius,
            corner_radius,
            math.pi / 2,
            math.pi,
        )
        cr.line_to(rect_x, rect_y + corner_radius)
        cr.arc(
            rect_x + corner_radius,
            rect_y + corner_radius,
            corner_radius,
            math.pi,
            3 * math.pi / 2,
        )
        cr.close_path()
        cr.stroke()

    def draw_mapping_mode_content(
        self, cr: "Context[Surface]", width: int, height: int
    ):
        if self.text:
            center_x = width / 2
            center_y = height / 2

            # 使用白色文字以在灰色背景上清晰显示
            cr.set_source_rgba(1, 1, 1, 1)  # 白色文字
            cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(12)
            text_extents = cr.text_extents(self.text)
            x = center_x - text_extents.width / 2
            y = center_y + text_extents.height / 2
            cr.move_to(x, y)
            cr.show_text(self.text)

            # 清除路径，避免影响后续绘制
            cr.new_path()

    def _get_window_center(self) -> tuple[float, float]:
        """获取窗口中心坐标"""
        root = self.get_root()
        if not root:
            return (0, 0)
        root = cast("Gtk.Window", root)
        w, h = root.get_width(), root.get_height()
        return (w / 2, h / 2)

    def _get_window_size(self) -> tuple[int, int]:
        """获取窗口大小"""
        root = self.get_root()
        if not root:
            return (800, 600)
        root = cast("Gtk.Window", root)
        return root.get_width(), root.get_height()

    def _map_circle_to_circle(self, mouse_x: float, mouse_y: float) -> tuple[float, float]:
        """
        将鼠标在圆形范围内的坐标映射到虚拟摇杆圆形范围内的坐标
        
        外圆：窗口中心为圆心，半径按百分比缩放
        内圆：widget中心为圆心，宽度/2为半径
        """
        # 获取窗口信息
        window_center_x, window_center_y = self._get_window_center()
        window_width, window_height = self._get_window_size()
        
        # 外圆参数（使用像素值）
        outer_radius = self.circle_radius
        
        # 虚拟摇杆圆形参数
        widget_center_x = self.center_x
        widget_center_y = self.center_y
        widget_radius = self.width / 2
        
        # 计算鼠标相对于外圆中心的位置
        rel_x = mouse_x - window_center_x
        rel_y = mouse_y - window_center_y
        
        # 计算距离
        distance = math.sqrt(rel_x * rel_x + rel_y * rel_y)
        
        if distance <= outer_radius:
            # 鼠标在外圆内，直接按比例映射
            if distance == 0:
                # 避免除零，直接返回widget中心
                target_x = widget_center_x
                target_y = widget_center_y
            else:
                # 按距离比例映射
                ratio = distance / outer_radius
                target_x = widget_center_x + (rel_x / distance) * ratio * widget_radius
                target_y = widget_center_y + (rel_y / distance) * ratio * widget_radius
        else:
            # 鼠标在外圆外，投影到圆形边界，再映射到widget圆形边界
            if distance == 0:
                target_x = widget_center_x
                target_y = widget_center_y
            else:
                # 投影到外圆边界，然后映射到widget圆形边界
                target_x = widget_center_x + (rel_x / distance) * widget_radius
                target_y = widget_center_y + (rel_y / distance) * widget_radius
        
        return (target_x, target_y)

    def _start_smooth_move_to_target(self):
        """开始平滑移动到目标位置"""
        if self._move_timer:
            GLib.source_remove(self._move_timer)
        
        self._skill_state = SkillState.MOVING
        self._move_steps_count = 0
        self._move_timer = GLib.timeout_add(
            self._timer_interval, self._update_smooth_move
        )

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
            
            if self._skill_state == SkillState.MOVING:
                self._emit_touch_event(AMotionEventAction.MOVE)
            
            return True  # Continue timer

        # 移动完成，到达目标位置
        self._current_position = self._target_position
        self._move_timer = None
        
        if self._skill_state == SkillState.MOVING:
            # 根据施法时机决定下一步动作
            if self.cast_timing == CastTiming.IMMEDIATE.value:
                # 立即释放模式：移动完成后立即发送UP事件并重置
                self._emit_touch_event(AMotionEventAction.UP)
                self._reset_skill()
            elif self.cast_timing == CastTiming.MANUAL.value:
                # 手动释放模式：进入锁定状态，等待第二次按键
                self._skill_state = SkillState.LOCKED
            else:
                # 默认松开释放模式：进入激活状态，等待按键松开
                self._skill_state = SkillState.ACTIVE
        
        return False  # Stop timer

    def _instant_move_to_target(self):
        """瞬间移动到目标位置"""
        self._current_position = self._target_position
        self._emit_touch_event(AMotionEventAction.MOVE)

    def _emit_touch_event(
        self, action: AMotionEventAction, position: tuple[float, float] | None = None
    ):
        """发送触摸事件"""
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

    def _reset_skill(self):
        """重置技能状态"""
        self._skill_state = SkillState.INACTIVE
        self._current_position = (self.center_x, self.center_y)
        
        # 清理定时器
        if self._move_timer:
            GLib.source_remove(self._move_timer)
            self._move_timer = None
        
        # 释放指针ID
        pointer_id_manager.release(self)
        

    def on_key_triggered(
        self,
        key_combination: KeyCombination | None = None,
        event: "InputEvent | None" = None,
    ):
        if not event or not event.event_type:
            return False
            
        # 判断事件类型
        is_key_press = event.event_type == "key_press"
        is_mouse_motion = event.event_type == "mouse_motion"
        
        if not (is_key_press or is_mouse_motion):
            return False

        if is_mouse_motion:
            if not event.position:
                return False
            self._mouse_x, self._mouse_y = event.position
         
        # 将鼠标位置映射到虚拟摇杆位置
        self._target_position = self._map_circle_to_circle(self._mouse_x, self._mouse_y)
        
        if self._skill_state == SkillState.INACTIVE:
            # 首次激活 - 只有按键事件才能激活
            if is_key_press:
                self._skill_state = SkillState.MOVING
                
                # 分配指针ID并发送DOWN事件
                pointer_id = pointer_id_manager.allocate(self)
                if pointer_id is None:
                    logger.error(f"Failed to allocate pointer ID for {self}")
                    return False
                
                self._current_position = (self.center_x, self.center_y)
                self._emit_touch_event(AMotionEventAction.DOWN, position=self._current_position)
                
                # 开始平滑移动到目标位置
                self._start_smooth_move_to_target()
                
            else:
                # 鼠标移动事件在未激活状态下不处理
                return False
                
        elif self._skill_state == SkillState.MOVING:
            # 移动中，更新目标位置但不重新开始移动
            pass
            
        elif self._skill_state == SkillState.ACTIVE:
            # 激活状态，瞬移到新目标位置
            self._instant_move_to_target()
            
        elif self._skill_state == SkillState.LOCKED:
            # 锁定状态（手动释放模式）
            if is_key_press:
                # 第二次按键，释放技能
                self._emit_touch_event(AMotionEventAction.UP)
                self._reset_skill()
            else:
                # 鼠标移动，瞬移到新目标位置
                self._instant_move_to_target()

        return True

    def on_key_released(
        self,
        key_combination: KeyCombination | None = None,
        event: "InputEvent | None" = None,
    ):
        """当映射的键释放时，根据施法时机决定是否发送UP事件"""
        if self._skill_state == SkillState.INACTIVE:
            return True

        # 根据施法时机决定处理方式
        if self.cast_timing == CastTiming.ON_RELEASE.value:
            # 松开释放模式：按键松开时发送UP事件
            if self._skill_state in [SkillState.MOVING, SkillState.ACTIVE]:
                self._emit_touch_event(AMotionEventAction.UP)
                self._reset_skill()
        elif self.cast_timing == CastTiming.IMMEDIATE.value:
            # 立即释放模式：按键松开时什么都不做（已经在移动完成时自动释放了）
            pass
        elif self.cast_timing == CastTiming.MANUAL.value:
            # 手动释放模式：按键松开时什么都不做（等待第二次按键）
            pass
        
        return True

    def get_editable_regions(self) -> list["EditableRegion"]:
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
