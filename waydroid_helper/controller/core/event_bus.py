#!/usr/bin/env python3
"""
事件总线模块
提供事件驱动的组件通信和状态管理
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Generic, TypeVar

from waydroid_helper.util.log import logger

# 事件数据类型
T = TypeVar("T")


class EventType(Enum):
    """事件类型"""

    # 系统事件
    MODE_CHANGED = auto()  # 模式改变

    # aim 事件
    AIM_TRIGGERED = auto()  # 瞄准触发
    AIM_RELEASED = auto()  # 瞄准释放

    # ControlMsg
    CONTROL_MSG = auto()  # 控制消息

    # 宏命令事件
    MACRO_KEY_PRESSED = auto()  # 宏命令按键按下
    MACRO_KEY_RELEASED = auto()  # 宏命令按键释放

    # 自定义事件（组件可以定义自己的事件）
    CUSTOM = auto()  # 自定义事件基类
    CREATE_WIDGET = auto()  # 创建组件
    DELETE_WIDGET = auto()  # 删除组件
    SETTINGS_WIDGET = auto() # 设置组件
    WIDGET_SELECTION_OVERLAY = auto()  # 组件选中覆盖层显示

    MOUSE_MOTION = auto()  # 鼠标移动事件
    CANCEL_CASTING = auto()  # 取消施法事件
    MASK_CLICKED = auto()  # 遮罩层点击事件，传递点击坐标


@dataclass
class Event(Generic[T]):
    """事件基类"""

    type: EventType  # 事件类型
    source: Any  # 事件源
    data: T  # 事件数据
    timestamp: float = field(default_factory=lambda: __import__("time").time())


@dataclass
class BusEventHandler:
    """事件总线处理器"""

    callback: Callable[[Event[Any]], None]  # 回调函数
    filter: Callable[[Event[Any]], bool] | None = None  # 事件过滤器
    priority: int = 0  # 优先级（越大越先执行）


class EventBus:
    """事件总线 - 提供事件驱动的组件通信"""

    def __init__(self):
        # 事件处理器: {事件类型: [处理器列表]}
        self._handlers: dict[EventType, list[BusEventHandler]] = {}

        # 初始化事件类型
        for event_type in EventType:
            self._handlers[event_type] = []

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event[Any]], None],
        filter: Callable[[Event[Any]], bool] | None = None,
        priority: int = 0,
    ) -> None:
        """
        订阅事件
        :param event_type: 事件类型
        :param handler: 处理函数
        :param filter: 可选的事件过滤器
        :param priority: 处理优先级
        """
        event_handler = BusEventHandler(handler, filter, priority)
        self._handlers[event_type].append(event_handler)
        # 按优先级排序
        self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)

        logger.debug(f"订阅事件: {event_type.name}, 优先级={priority}")

    def unsubscribe(
        self, event_type: EventType, handler: Callable[[Event[Any]], None]
    ) -> bool:
        """取消事件订阅"""
        if event_type not in self._handlers:
            return False

        original_len = len(self._handlers[event_type])
        self._handlers[event_type] = [
            h for h in self._handlers[event_type] if h.callback != handler
        ]

        return len(self._handlers[event_type]) < original_len

    def emit(self, event: Event[Any]) -> None:
        """
        发送事件
        事件会按优先级顺序传递给所有订阅者
        """
        if event.type not in self._handlers:
            return

        logger.debug(f"发送事件: {event.type.name}")
        for handler in self._handlers[event.type]:
            try:
                # 检查过滤器
                if handler.filter and not handler.filter(event):
                    continue

                # 调用处理函数
                handler.callback(event)

            except Exception as e:
                logger.error(f"处理事件 {event.type.name} 出错: {e}")

    def clear(self) -> None:
        """清空所有订阅"""
        for event_type in self._handlers:
            self._handlers[event_type].clear()
        logger.info("EventBus cleared.")


# 全局事件总线实例
event_bus = EventBus()
