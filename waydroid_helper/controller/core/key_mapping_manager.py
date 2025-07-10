#!/usr/bin/env python3
"""
按键映射管理器
负责管理和处理所有的按键映射订阅和触发
"""
import itertools
from typing import Any, Callable, TYPE_CHECKING

from waydroid_helper.controller.core.key_system import Key, KeyCombination
from waydroid_helper.util.log import logger
from waydroid_helper.controller.core.event_bus import Event, EventBus, EventType, event_bus

if TYPE_CHECKING:
    from gi.repository import Gtk


class KeySubscription:
    """按键订阅信息"""

    def __init__(
        self,
        widget: "Gtk.Widget",
        key_combination: KeyCombination,
        condition: Callable[[], bool] | None = None,
        required_states: list[str] | None = None,
    ):
        self.widget: "Gtk.Widget" = widget
        self.key_combination: KeyCombination = key_combination
        self.callback: str = "on_key_triggered"
        self.release_callback: str = "on_key_released"
        self.condition: Callable[[], bool] | None = condition
        self.required_states: list[str] = required_states or []


class KeyMappingManager:
    """按键映射管理器 - 单例"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(KeyMappingManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if hasattr(self, "_initialized"):
            return
        self._initialized: bool = True

        self._key_subscriptions: dict[KeyCombination, list[KeySubscription]] = {}
        self._pressed_keys: set[Key] = set()
        self._triggered_mappings: dict[KeyCombination, set[Key]] = {}

        # 为了检查依赖状态，需要一个对widget状态的引用，暂时留空
        self._widget_states: dict[int, dict[str, Any]] = {}
        logger.info("KeyMappingManager initialized")

        event_bus.subscribe(EventType.MACRO_KEY_PRESSED, self._on_macro_key_pressed)
        event_bus.subscribe(EventType.MACRO_KEY_RELEASED, self._on_macro_key_released)

    def _on_macro_key_pressed(self, event: Event[Key]):
        self.handle_key_press(event.data)

    def _on_macro_key_released(self, event: Event[Key]):
        self.handle_key_release(event.data)

    def subscribe(
        self,
        widget: "Gtk.Widget",
        key_combination: KeyCombination,
        condition: Callable[[], bool] | None = None,
        required_states: list[str] | None = None,
    ) -> bool:
        """订阅按键事件"""
        if not key_combination:
            return False

        subscription = KeySubscription(
            widget=widget,
            key_combination=key_combination,
            condition=condition,
            required_states=required_states or [],
        )

        if key_combination not in self._key_subscriptions:
            self._key_subscriptions[key_combination] = []
        self._key_subscriptions[key_combination].append(subscription)

        logger.debug(
            f"注册按键映射: {key_combination} -> {type(widget).__name__}(id={id(widget)})"
        )
        return True

    def unsubscribe(self, widget: "Gtk.Widget") -> bool:
        """取消widget的所有按键订阅"""
        widget_id = id(widget)
        # 创建一个副本进行迭代，因为我们可能会在循环中修改字典
        for key_combination in list(self._key_subscriptions.keys()):

            # 过滤掉属于该widget的订阅
            self._key_subscriptions[key_combination] = [
                sub
                for sub in self._key_subscriptions[key_combination]
                if id(sub.widget) != widget_id
            ]

            # 如果某个key_combination的订阅列表空了，就从字典中移除它
            if not self._key_subscriptions[key_combination]:
                del self._key_subscriptions[key_combination]

        logger.debug(f"已取消 widget(id={widget_id}) 的所有按键订阅")
        return True

    def unsubscribe_key(
        self, widget: "Gtk.Widget", key_combination: KeyCombination
    ) -> bool:
        """取消widget的特定按键订阅"""
        widget_id = id(widget)

        if key_combination in self._key_subscriptions:
            self._key_subscriptions[key_combination] = [
                sub
                for sub in self._key_subscriptions[key_combination]
                if not (
                    id(sub.widget) == widget_id
                    and sub.key_combination == key_combination
                )
            ]

            if not self._key_subscriptions[key_combination]:
                del self._key_subscriptions[key_combination]

        return True

    def get_subscriptions(self, widget: "Gtk.Widget") -> list[KeyCombination]:
        """获取widget的所有按键订阅"""
        widget_id = id(widget)
        result: list[KeyCombination] = []

        for key_combination, subscriptions in self._key_subscriptions.items():
            if any(id(sub.widget) == widget_id for sub in subscriptions):
                result.append(key_combination)

        return result

    def handle_key_press(self, key: Key) -> bool:
        """处理按键按下事件，返回事件是否被消费"""
        if not key:
            return False

        self._pressed_keys.add(key)

        # 检查是否触发了新的映射
        triggered_new = self._check_and_trigger_mappings()

        # 如果触发了新映射，事件肯定被消费
        if triggered_new:
            return True

        # 如果没有触发新映射，但当前按下的键是某个已激活映射的一部分，
        # 那么也认为事件被消费，防止泄露给下一个处理器。
        # 例如，当 Ctrl+Shift 已激活时，再按 A，A 的事件也应被消费。
        current_pressed_set = set(self._pressed_keys)
        for triggered_keys in self._triggered_mappings.values():
            # 如果已激活的组合是当前按下键的子集 (e.g. 按下A, B, C, 激活了A+B)
            if triggered_keys.issubset(current_pressed_set):
                return True

        return False

    def handle_key_release(self, key: Key) -> bool:
        """处理按键释放事件，返回事件是否被消费"""
        if key not in self._pressed_keys:
            return False

        # 检查释放这个键是否会导致某个映射被释放
        released_a_mapping = self._check_mapping_release(key)

        # 从按下的键中移除
        self._pressed_keys.remove(key)

        # 在释放一个键后，可能会触发一个新的、更短的组合
        triggered_new_on_release = self._check_and_trigger_mappings()

        # 只要释放了旧的映射，或者触发了新的映射，都算事件被消费
        return released_a_mapping or triggered_new_on_release

    def _check_subscription_conditions(self, subscription: KeySubscription) -> bool:
        """检查订阅的触发条件"""
        if subscription.condition and not subscription.condition():
            return False

        if subscription.required_states:
            widget_id = id(subscription.widget)
            widget_states = self._widget_states.get(widget_id, {})
            for state_name in subscription.required_states:
                if not widget_states.get(state_name):
                    return False

        return True

    def _check_and_trigger_mappings(self) -> bool:
        """检查并触发匹配的映射"""
        triggered_any = False
        pressed_keys_list = list(self._pressed_keys)

        # 从最长的组合开始检查，以支持 "Ctrl+Shift+A" 优先于 "Ctrl+A"
        for size in range(len(pressed_keys_list), 0, -1):
            for combo_tuple in itertools.combinations(pressed_keys_list, size):
                key_combination = KeyCombination(list(combo_tuple))

                # 如果这个组合已经触发，就跳过
                if key_combination in self._triggered_mappings:
                    continue

                if key_combination in self._key_subscriptions:
                    # 检查此组合是否是其他已触发组合的子集，如果是，则不触发
                    is_subset_of_triggered = False
                    for triggered_combo in self._triggered_mappings.keys():
                        if key_combination.is_subset_of(triggered_combo):
                            is_subset_of_triggered = True
                            break
                    if is_subset_of_triggered:
                        continue

                    combo_triggered_this_time = False
                    for subscription in self._key_subscriptions[key_combination]:
                        if not self._check_subscription_conditions(subscription):
                            logger.debug("跳过触发: 条件不满足")
                            continue

                        if hasattr(subscription.widget, subscription.callback):
                            callback = getattr(
                                subscription.widget, subscription.callback
                            )
                            # 假设回调返回True表示事件被处理
                            if callback(key_combination):
                                combo_triggered_this_time = True

                    if combo_triggered_this_time:
                        self._triggered_mappings[key_combination] = set(combo_tuple)
                        triggered_any = True
                        logger.debug(f"记录触发的映射: {key_combination}")

        return triggered_any

    def _check_mapping_release(self, released_key: Key) -> bool:
        """处理映射释放，返回是否有映射被释放"""
        released_any = False
        # 使用 list() 来创建副本，因为我们可能在循环中删除元素
        for mapping_key, related_keys in list(self._triggered_mappings.items()):
            if released_key in related_keys:
                if mapping_key in self._key_subscriptions:
                    for subscription in self._key_subscriptions[mapping_key]:
                        if hasattr(subscription.widget, subscription.release_callback):
                            callback = getattr(
                                subscription.widget, subscription.release_callback
                            )
                            # 假设释放回调也返回布尔值
                            if callback(mapping_key):
                                released_any = True

                del self._triggered_mappings[mapping_key]
                logger.debug(f"释放映射: {mapping_key} 因为 {released_key} 被释放")
        return released_any

    def print_mappings(self):
        """打印当前所有的按键映射（调试用）"""
        logger.debug("\n=== KeyMappingManager: 当前按键映射状态 ===")
        logger.debug(f"总计映射: {len(self._key_subscriptions)} 个按键组合")

        if not self._key_subscriptions:
            logger.debug("没有注册的按键映射")
        else:
            for key_combo, subscriptions in self._key_subscriptions.items():
                logger.debug(f"  {key_combo} -> {len(subscriptions)} 个订阅:")
                for sub in subscriptions:
                    widget_name = type(sub.widget).__name__
                    widget_id = id(sub.widget)
                    conditions = []
                    if sub.condition:
                        conditions.append("自定义条件")
                    if sub.required_states:
                        conditions.append(f"依赖状态: {sub.required_states}")
                    conditions_str = f" ({', '.join(conditions)})" if conditions else ""
                    logger.debug(f"    - {widget_name}(id={widget_id}){conditions_str}")
        logger.debug(f"当前按下的键: {[str(k) for k in self._pressed_keys]}")
        logger.debug(
            f"当前触发的映射: {[str(k) for k in self._triggered_mappings.keys()]}"
        )
        logger.debug("=" * 30)

    def clear(self) -> None:
        """清空所有订阅和状态"""
        self._key_subscriptions.clear()
        self._pressed_keys.clear()
        self._triggered_mappings.clear()
        logger.info("KeyMappingManager cleared.")


# 全局实例
key_mapping_manager = KeyMappingManager()
