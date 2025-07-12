#!/usr/bin/env python3
"""
透明窗口模块
提供透明窗口的实现和窗口管理功能
"""

from gettext import gettext as _
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Adw, Gdk, GObject, GLib

from waydroid_helper.controller.app.workspace_manager import WorkspaceManager
from waydroid_helper.controller.core import (
    KeyCombination,
    key_registry,
    key_mapping_manager,
    Server,
    is_point_in_rect,
    event_bus,
    EventType,
    Event,
)
from waydroid_helper.controller.core.constants import APP_TITLE
from waydroid_helper.controller.core.handler import EventHandlerChain, InputEvent
from waydroid_helper.controller.core.handler.key_mapping_event_handler import (
    KeyMappingEventHandler,
)
from waydroid_helper.controller.core.handler.default import DefaultEventHandler
from waydroid_helper.controller.ui.styles import StyleManager
from waydroid_helper.controller.ui.menus import ContextMenuManager
from waydroid_helper.controller.widgets.factory import WidgetFactory
from waydroid_helper.controller.widgets.config import ConfigType

from waydroid_helper.util.log import logger
from waydroid_helper.util.adb_helper import AdbHelper
import asyncio
import weakref

if TYPE_CHECKING:
    from waydroid_helper.controller.widgets.base import BaseWidget


Adw.init()

MAX_RETRY_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 3


class TransparentWindow(Adw.Window):
    """透明窗口"""

    # __gtype_name__ = 'TransparentWindow'

    # 定义模式常量
    EDIT_MODE = "edit"
    MAPPING_MODE = "mapping"

    # 定义current_mode为GObject属性
    current_mode = GObject.Property(
        type=str,
        default=EDIT_MODE,
        nick="Current Mode",
        blurb="The current operating mode (edit or mapping)",
    )

    def __init__(self, app):
        super().__init__(application=app)

        self.connect("close-request", self._on_close_request)

        self.set_title(APP_TITLE)

        # 创建主容器 (Overlay)
        overlay = Gtk.Overlay.new()
        self.set_content(overlay)

        self.fixed = Gtk.Fixed.new()
        self.fixed.set_name("mapping-widget")
        overlay.set_child(self.fixed)

        # 创建模式切换提示
        self.notification_label = Gtk.Label.new("")
        self.notification_label.set_name("mode-notification-label")

        self.notification_box = Gtk.Box()
        self.notification_box.set_name("mode-notification-box")
        self.notification_box.set_halign(Gtk.Align.CENTER)
        self.notification_box.set_valign(Gtk.Align.START)
        self.notification_box.set_margin_top(60)
        self.notification_box.append(self.notification_label)
        self.notification_box.set_opacity(0.0)
        self.notification_box.set_can_target(False)  # 忽略鼠标事件

        overlay.add_overlay(self.notification_box)

        # 初始化组件
        self.widget_factory = WidgetFactory()
        self.style_manager = StyleManager()
        self.menu_manager = ContextMenuManager(self)
        self.workspace_manager = WorkspaceManager(self, self.fixed)

        # 订阅事件
        event_bus.subscribe(
            EventType.SETTINGS_WIDGET, self._on_widget_settings_requested
        )

        # 创建全局事件处理器链
        self.event_handler_chain = EventHandlerChain()
        # 导入并添加默认处理器
        self.server = Server("0.0.0.0", 10721)
        self.adb_helper = AdbHelper()
        self.scrcpy_setup_task = asyncio.create_task(self.setup_scrcpy())
        self.key_mapping_handler = KeyMappingEventHandler()
        self.default_handler = DefaultEventHandler()

        self.event_handler_chain.add_handler(self.key_mapping_handler)
        self.event_handler_chain.add_handler(self.default_handler)

        # 初始化双模式系统
        self.setup_mode_system()

        # 初始化事件处理器
        self.setup_event_handlers()

        # 设置全屏
        self.setup_window()

        # 设置UI（主要是事件控制器）
        self.setup_controllers()

        # 初始提示
        GLib.idle_add(self.show_notification, _("Edit Mode (F1: Switch Mode)"))

    def _on_widget_settings_requested(self, event: "Event[bool]"):
        """当一个widget请求设置时的回调, 弹出一个Popover"""
        widget = event.source
        logger.info(
            f"Widget {type(widget).__name__} (id={id(widget)}) requested settings."
        )

        def workaround_popover_auto_hide(controller, n_press, x, y):
            if popover.get_visible() and popover.get_autohide():
                if (
                    x < 0
                    or y < 0
                    or x > popover.get_width()
                    or y > popover.get_height()
                ):
                    popover.popdown()

        popover = Gtk.Popover()
        popover.set_autohide(event.data)
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", workaround_popover_auto_hide)
        popover.add_controller(click_controller)

        # popover.set_cascade_popdown(event.data)
        # "fix: Tried to map a grabbing popup with a non-top most parent" 错误
        popover.set_parent(self)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_size_request(250, -1)  # Set a minimum width for the popover
        popover.set_child(main_box)

        # Header Label
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{widget.WIDGET_NAME}{_("Settings")}</b>")
        title_label.set_halign(Gtk.Align.CENTER)
        main_box.append(title_label)

        # 使用新的配置系统
        config_manager = widget.get_config_manager()

        if not config_manager.configs:
            label = Gtk.Label(label=_("This widget has no settings."))
            main_box.append(label)
        else:
            # 使用配置管理器生成UI面板
            config_panel = config_manager.create_ui_panel()
            main_box.append(config_panel)

            # # Confirm Button
            # confirm_button = Gtk.Button(label=_("OK"), halign=Gtk.Align.END)
            # confirm_button.add_css_class("suggested-action")

            # def on_confirm_clicked(btn):
            #     # UI值变化已自动同步到配置管理器，这里只需关闭弹窗
            #     logger.info("Configuration popover closed by user.")
            #     popover.popdown()

            # confirm_button.connect("clicked", on_confirm_clicked)
            # main_box.append(confirm_button)

        # Pointing and Display
        settings_button_rect = Gdk.Rectangle()
        bounds = widget.get_settings_button_bounds()
        settings_button_rect.x = bounds[0] + widget.x
        settings_button_rect.y = bounds[1] + widget.y
        settings_button_rect.width = bounds[2]
        settings_button_rect.height = bounds[3]

        popover.set_pointing_to(settings_button_rect)
        popover.set_position(Gtk.PositionType.BOTTOM)

        def on_popover_closed(p):
            # 清理ConfigManager中对UI控件的引用，防止内存泄漏
            config_manager.clear_ui_references()
            # 从父容器解除对popover的引用
            p.unparent()

        popover.connect("closed", on_popover_closed)
        popover.popup()

    def _on_close_request(self, window):
        logger.info("Close request received, running cleanup...")
        self.on_clear_widgets(None)
        self.close()
        return False

    def close(self):
        self.server.close()
        if not self.scrcpy_setup_task.done():
            self.scrcpy_setup_task.cancel()

        asyncio.create_task(self.cleanup_scrcpy())
        super().close()

    async def cleanup_scrcpy(self):
        await self.adb_helper.remove_reverse_tunnel()
        logger.info("Scrcpy cleanup finished.")

    async def setup_scrcpy(self):
        """Pushes scrcpy-server and starts it on the device, with retry logic."""
        logger.info("Waiting for internal server to start...")
        await self.server.wait_started()

        if not self.server.server:
            logger.error("Internal server failed to start. Aborting scrcpy setup.")
            return

        logger.info("Internal server started. Starting scrcpy setup...")

        for attempt in range(MAX_RETRY_ATTEMPTS):
            logger.info(f"Scrcpy setup attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}...")
            try:
                # 1. Get screen resolution. Not critical, so no retry on failure.
                await self.adb_helper.get_screen_resolution()

                # 2. Push server to device
                if not await self.adb_helper.push_scrcpy_server():
                    logger.warning(
                        f"Failed to push scrcpy-server. Retrying in {RETRY_DELAY_SECONDS}s..."
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue

                # 3. Generate SCID and setup reverse tunnel
                scid, socket_name = self.adb_helper.generate_scid()
                if not await self.adb_helper.reverse_tunnel(
                    socket_name, self.server.port
                ):
                    logger.warning(
                        f"Failed to set up adb reverse. Retrying in {RETRY_DELAY_SECONDS}s..."
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue

                # 4. Start scrcpy-server on device
                if not await self.adb_helper.start_scrcpy_server(scid):
                    logger.warning(
                        f"Failed to start scrcpy-server. Retrying in {RETRY_DELAY_SECONDS}s..."
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue

                logger.info("Scrcpy setup process completed successfully.")
                return  # Exit on success

            except asyncio.CancelledError:
                logger.info("Scrcpy setup task was cancelled.")
                return  # Use return to exit immediately on cancellation
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during setup attempt {attempt + 1}: {e}"
                )
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        logger.error(
            f"Scrcpy setup failed after {MAX_RETRY_ATTEMPTS} attempts. Aborting."
        )

    def setup_mode_system(self):
        """初始化双模式系统"""
        # 监听current_mode属性变化
        self.connect("notify::current-mode", self._on_mode_changed)

        logger.debug(f"Dual mode system initialized, current mode: {self.current_mode}")

    def setup_event_handlers(self):
        """设置事件处理器"""
        # 配置默认处理器的一些示例映射
        # default_handler.add_key_mapping("T", lambda: print("🎮 默认: T键测试"))
        # default_handler.add_key_mapping("G", lambda: print("🎮 默认: G键测试"))
        # default_handler.add_mouse_mapping(2, lambda: print("🖱️ 默认: 中键点击"))  # 中键

        logger.debug("Event handler chain initialized")
        logger.debug(
            f"Handler list: {[h['name'] for h in self.event_handler_chain.get_handlers_info()]}"
        )

    def setup_window(self):
        """设置窗口属性"""
        self.realize()
        self.set_decorated(False)

        surface = self.get_surface()
        if surface:
            display = self.get_display()
            if display:
                monitor = display.get_monitor_at_surface(surface)
                if monitor:
                    geometry = monitor.get_geometry()
                    self.set_default_size(geometry.width, geometry.height)

        self.set_name("transparent-window")

    def setup_ui(self):
        """设置用户界面"""
        # 主容器已在 __init__ 中创建和设置
        pass

    def setup_controllers(self):
        """设置事件控制器"""
        # 全局键盘事件
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.on_global_key_press)
        key_controller.connect("key-released", self.on_global_key_release)
        self.add_controller(key_controller)

        # 窗口级别的鼠标滚动事件
        scroll_controller = Gtk.EventControllerScroll.new(
            flags=Gtk.EventControllerScrollFlags.BOTH_AXES
        )
        scroll_controller.connect("scroll-begin", self.on_window_mouse_scroll)
        scroll_controller.connect("scroll", self.on_window_mouse_scroll)
        scroll_controller.connect("scroll-end", self.on_window_mouse_scroll)
        self.add_controller(scroll_controller)

        # 窗口级别的鼠标事件控制器
        click_controller = Gtk.GestureClick()
        click_controller.set_button(0)  # 所有按钮
        click_controller.connect("pressed", self.on_window_mouse_pressed)
        click_controller.connect("released", self.on_window_mouse_released)
        self.add_controller(click_controller)

        # 窗口级别的鼠标移动事件
        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect("motion", self.on_window_mouse_motion)
        self.add_controller(motion_controller)

        # 初始化拖拽和调整大小状态
        self.dragging_widget = None
        self.resizing_widget = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_direction = None

        # 初始化交互状态
        self.selected_widget = None
        self.interaction_start_x = 0
        self.interaction_start_y = 0
        self.pending_resize_direction = None

    def on_window_mouse_pressed(self, controller, n_press, x, y):
        """窗口级别的鼠标按下事件"""
        button = controller.get_current_button()
        logger.debug(
            f"Mouse pressed: position({x:.1f}, {y:.1f}), button={button}, mode={self.current_mode}"
        )

        # 在映射模式下使用事件处理器链
        if self.current_mode == self.MAPPING_MODE:
            logger.debug(
                "In mapping mode, use event handler chain to handle mouse event"
            )

            # 创建鼠标按键的Key对象
            mouse_key = key_registry.create_mouse_key(button)

            # 创建输入事件
            event = InputEvent(
                event_type="mouse_press",
                key=mouse_key,
                button=button,
                position=(int(x), int(y)),
                raw_data={"controller": controller, "n_press": n_press, "x": x, "y": y},
            )

            # 使用事件处理器链处理
            handled = self.event_handler_chain.process_event(event)
            if handled:
                logger.debug("Mouse event handled by event handler chain")
                return True
            else:
                logger.debug("Mouse event not handled by any event handler")
            return

        # 编辑模式下的鼠标事件处理
        if button == Gdk.BUTTON_SECONDARY:  # 右键
            widget_at_position = self.workspace_manager.get_widget_at_position(x, y)
            if not widget_at_position:
                # 右键空白区域，显示创建菜单
                logger.debug("Right click on blank area, show create menu")
                self.menu_manager.show_widget_creation_menu(x, y, self.widget_factory)
            else:
                # 右键widget，调用widget的右键回调
                logger.debug(
                    f"Right click on widget: {type(widget_at_position).__name__}"
                )
                local_x, local_y = self.workspace_manager.global_to_local_coords(
                    widget_at_position, x, y
                )
                if hasattr(widget_at_position, "on_widget_right_clicked"):
                    widget_at_position.on_widget_right_clicked(local_x, local_y)

        elif button == Gdk.BUTTON_PRIMARY:  # 左键
            self.workspace_manager.handle_mouse_press(controller, n_press, x, y)

    def on_window_mouse_motion(self, controller, x, y):
        """窗口级别的鼠标移动事件"""
        if self.current_mode == self.MAPPING_MODE:
            logger.debug(
                "In mapping mode, use event handler chain to handle mouse motion"
            )
            event = InputEvent(
                event_type="mouse_motion",
                position=(int(x), int(y)),
                raw_data={"controller": controller, "x": x, "y": y},
            )
            self.event_handler_chain.process_event(event)
            return

        # 编辑模式下，委托给 workspace_manager
        self.workspace_manager.handle_mouse_motion(controller, x, y)

    def on_window_mouse_scroll(
        self,
        controller: Gtk.EventControllerScroll,
        dx: float | None = None,
        dy: float | None = None,
    ):
        if self.current_mode == self.MAPPING_MODE:
            event = InputEvent(
                event_type="mouse_scroll",
                raw_data={"controller": controller, "dx": dx, "dy": dy},
            )
            self.event_handler_chain.process_event(event)

    def fixed_put(self, widget, x, y):
        self.fixed.put(widget, x, y)
        widget.x = x
        widget.y = y

    def fixed_move(self, widget, x, y):
        self.fixed.move(widget, x, y)
        widget.x = x
        widget.y = y

    def get_widget_at_position(self, x, y):
        """获取指定位置的组件"""
        child = self.fixed.get_first_child()
        while child:
            # 获取组件的位置和大小
            child_x, child_y = self.fixed.get_child_position(child)
            child_width = child.get_allocated_width()
            child_height = child.get_allocated_height()

            # 检查点击是否在组件范围内
            if is_point_in_rect(x, y, child_x, child_y, child_width, child_height):
                return child

            child = child.get_next_sibling()
        return None

    def global_to_local_coords(self, widget, global_x, global_y):
        """将全局坐标转换为widget内部坐标"""
        widget_x, widget_y = self.fixed.get_child_position(widget)
        return global_x - widget_x, global_y - widget_y

    def handle_widget_interaction(self, widget, x, y, n_press=1):
        """处理widget交互 - 支持双击检测"""
        logger.debug(
            f"Handle widget interaction: {type(widget).__name__}, position({x:.1f}, {y:.1f}), click count={n_press}"
        )

        # 转换为widget内部坐标，用于编辑状态判断
        local_x, local_y = self.global_to_local_coords(widget, x, y)

        # 检查widget是否有编辑装饰器，且是否应该保持编辑状态
        should_keep_editing = False
        if hasattr(widget, "should_keep_editing_on_click"):
            should_keep_editing = widget.should_keep_editing_on_click(local_x, local_y)
            logger.debug(f"Widget edit status query result: {should_keep_editing}")

        if should_keep_editing:
            # 如果应该保持编辑状态，就不改变选择状态，也不要触发置顶
            logger.debug(
                "Keep editing state, skip selection logic and bring to front operation"
            )
            # 设置跳过标志，避免延迟置顶破坏编辑状态
            widget._skip_delayed_bring_to_front = True
            return  # 直接返回，不执行后续的选择和置顶逻辑
        else:
            # 正常的选择逻辑
            # 取消其他widget的选择
            self.clear_all_selections()

            # 选择当前widget
            if hasattr(widget, "set_selected"):
                widget.set_selected(True)
                logger.debug("Set widget to selected state")

        # 选择时置顶 - 使用延迟方式
        # 清除跳过标志（如果存在），确保正常情况下能置顶
        if hasattr(widget, "_skip_delayed_bring_to_front"):
            delattr(widget, "_skip_delayed_bring_to_front")
            logger.debug("Clear skip delayed bring to front flag")

        self.schedule_bring_to_front(widget)

        # 转换为widget内部坐标
        local_x, local_y = self.global_to_local_coords(widget, x, y)
        logger.debug(f"Convert to local coordinates: ({local_x:.1f}, {local_y:.1f})")

        # 处理双击事件
        if n_press == 2:
            logger.debug("Double click detected")
            # 双击时，标记widget避免延迟置顶操作执行
            if not hasattr(widget, "_skip_delayed_bring_to_front"):
                widget._skip_delayed_bring_to_front = True
                logger.debug("Mark widget to skip delayed bring to front operation")

            if hasattr(widget, "on_widget_double_clicked"):
                widget.on_widget_double_clicked(local_x, local_y)
            # 双击进入编辑时不要触发置顶，避免干扰编辑状态
            logger.debug("Double click completed, skip bring to front operation")
            return

        # 记录准备进行的操作，但不立即执行
        self.selected_widget = widget
        self.interaction_start_x = x
        self.interaction_start_y = y

        # 检查是否是调整大小区域
        if hasattr(widget, "check_resize_direction"):
            resize_direction = widget.check_resize_direction(local_x, local_y)
            logger.debug(f"Check resize direction: {resize_direction}")
            if resize_direction:
                # 开始调整大小时，如果widget正在编辑状态，强制退出编辑
                if hasattr(widget, "should_keep_editing_on_click"):
                    # 这表示widget有编辑装饰器，强制触发selection change来退出编辑
                    self.clear_all_selections()
                    widget.set_selected(True)
                    logger.debug("When resizing, force exit edit state")

                self.pending_resize_direction = resize_direction
                logger.debug("Prepare resize operation")
                return

        # 否则准备拖拽
        self.pending_resize_direction = None
        logger.debug("Prepare drag operation")

        # 调用widget的点击回调
        if hasattr(widget, "on_widget_clicked"):
            widget.on_widget_clicked(local_x, local_y)

    def on_window_mouse_released(self, controller, n_press, x, y):
        """窗口级别的鼠标释放事件"""
        button = controller.get_current_button()
        logger.debug(f"Mouse released: position({x:.1f}, {y:.1f}), button={button}")

        # 在映射模式下使用事件处理器链
        if self.current_mode == self.MAPPING_MODE:
            logger.debug(
                "In mapping mode, use event handler chain to handle mouse release"
            )

            # 创建鼠标按键的Key对象
            mouse_key = key_registry.create_mouse_key(button)

            # 创建输入事件
            event = InputEvent(
                event_type="mouse_release",
                key=mouse_key,
                button=button,
                position=(int(x), int(y)),
                raw_data={"controller": controller, "n_press": n_press, "x": x, "y": y},
            )

            # 使用事件处理器链处理
            handled = self.event_handler_chain.process_event(event)
            if handled:
                logger.debug("Mouse release event handled by event handler chain")
                return True
            else:
                logger.debug("Mouse release event not handled by any event handler")
            return

        # 编辑模式下的鼠标释放处理, 委托给 workspace_manager
        self.workspace_manager.handle_mouse_release(controller, n_press, x, y)

    def start_widget_drag(self, widget, x, y):
        """开始拖拽widget"""
        self.dragging_widget = widget
        self.drag_start_x = x
        self.drag_start_y = y

        # 在拖拽时将widget置于顶层 - 使用安全的方法
        self.bring_widget_to_front_safe(widget)

    def start_widget_resize(self, widget, x, y, direction):
        """开始调整widget大小"""
        self.resizing_widget = widget
        self.resize_start_x = x
        self.resize_start_y = y
        self.resize_direction = direction

        if hasattr(widget, "start_resize"):
            local_x, local_y = self.global_to_local_coords(widget, x, y)
            widget.start_resize(local_x, local_y, direction)

    def handle_widget_drag(self, x, y):
        """处理widget拖拽"""
        if not self.dragging_widget:
            return

        dx = x - self.drag_start_x
        dy = y - self.drag_start_y

        # 获取当前位置
        current_x, current_y = self.fixed.get_child_position(self.dragging_widget)
        new_x = current_x + dx
        new_y = current_y + dy

        # 限制在窗口范围内
        widget_bounds = self.dragging_widget.get_widget_bounds()
        window_width = self.get_allocated_width()
        window_height = self.get_allocated_height()

        new_x = max(0, min(new_x, window_width - widget_bounds[2]))
        new_y = max(0, min(new_y, window_height - widget_bounds[3]))

        # 移动widget
        self.fixed_move(self.dragging_widget, new_x, new_y)

        # 更新拖拽起始点
        self.drag_start_x = x
        self.drag_start_y = y

    def handle_widget_resize(self, x, y):
        """处理widget调整大小"""
        if not self.resizing_widget or not hasattr(
            self.resizing_widget, "handle_resize_motion"
        ):
            return

        self.resizing_widget.handle_resize_motion(x, y)

    def bring_widget_to_front(self, widget):
        """将widget置于最前 - 使用简单安全的方法"""
        # 简单的方法：只在开始拖拽时置顶，避免在选择时就置顶
        pass

    def bring_widget_to_front_safe(self, widget):
        """安全地将widget置于最前 - 只在拖拽时使用"""
        try:
            # 获取当前位置
            x, y = self.fixed.get_child_position(widget)

            # 移除并重新添加（只在拖拽时这样做是安全的）
            self.fixed.remove(widget)
            self.fixed_put(widget, x, y)

            # 确保拖拽状态正确
            self.dragging_widget = widget

        except Exception as e:
            logger.error(f"Error bringing widget to front: {e}")

    def schedule_bring_to_front(self, widget):
        """延迟置顶 - 避免立即操作导致的状态问题"""
        # 使用GLib.idle_add来延迟执行置顶操作
        GLib.idle_add(self._delayed_bring_to_front, widget)

    def _delayed_bring_to_front(self, widget):
        """延迟执行的置顶操作"""
        try:
            # 检查是否应该跳过延迟置顶（双击进入编辑时）
            if (
                hasattr(widget, "_skip_delayed_bring_to_front")
                and widget._skip_delayed_bring_to_front
            ):
                logger.debug(
                    "Skip delayed bring to front operation (widget is editing)"
                )
                # 清除标志
                delattr(widget, "_skip_delayed_bring_to_front")
                return False

            # 检查widget是否仍然存在
            if widget.get_parent() != self.fixed:
                return False

            # 获取当前位置
            x, y = self.fixed.get_child_position(widget)

            # 保存选择状态
            selected_state = getattr(widget, "is_selected", False)

            # 移除并重新添加
            self.fixed.remove(widget)
            self.fixed_put(widget, x, y)

            # 恢复选择状态（只在状态真的改变时才调用，避免触发不必要的信号）
            if hasattr(widget, "set_selected"):
                current_state = getattr(widget, "is_selected", False)
                if current_state != selected_state:
                    widget.set_selected(selected_state)
                    logger.debug(f"Bring to front: {current_state} -> {selected_state}")
                else:
                    logger.debug(f"Bring to front: {selected_state}")

        except Exception as e:
            logger.error(f"Error bringing widget to front: {e}")

        return False  # 不重复执行

    # def update_cursor_for_position(self, x, y):
    #     """根据位置更新鼠标指针 - 已移至 workspace_manager"""
    #     pass  # 此方法已移至 workspace_manager，保留空方法以保持兼容性

    # def get_cursor_name_for_resize_direction(self, direction):
    #     """根据调整大小方向获取鼠标指针名称"""
    #     cursor_map = {
    #         "se": "se-resize",
    #         "sw": "sw-resize",
    #         "ne": "ne-resize",
    #         "nw": "nw-resize",
    #         "e": "e-resize",
    #         "w": "w-resize",
    #         "s": "s-resize",
    #         "n": "n-resize",
    #     }
    #     return cursor_map.get(direction, "default")

    def clear_all_selections(self):
        """取消所有组件的选择状态"""
        self.workspace_manager.clear_all_selections()

    def set_all_widgets_mapping_mode(self, mapping_mode: bool):
        """设置所有 widget 的映射模式"""
        widget_count = 0
        child = self.fixed.get_first_child()
        while child:
            if hasattr(child, "set_mapping_mode"):
                child.set_mapping_mode(mapping_mode)
                widget_count += 1
            child = child.get_next_sibling()

        mode_name = "mapping" if mapping_mode else "edit"
        logger.debug(f"Set {widget_count} widgets to {mode_name} mode")

    def create_widget_at_position(self, widget: "BaseWidget", x: int, y: int):
        """在指定位置创建组件"""
        # 直接在指定位置放置组件
        self.fixed_put(widget, x, y)

        # 检查是否是支持多按键映射的组件（如DirectionalPad）
        if hasattr(widget, "get_all_key_mappings"):
            # 为多按键映射组件注册所有按键
            key_mappings = widget.get_all_key_mappings()
            success_count = 0
            total_count = len(key_mappings)

            for key_combination, direction in key_mappings.items():
                success = self.register_widget_key_mapping(widget, key_combination)
                if success:
                    success_count += 1
                    logger.debug(
                        f"Register multi-key mapping: {key_combination} -> {type(widget).__name__}({direction})"
                    )
                else:
                    logger.debug(
                        f"Register multi-key mapping failed: {key_combination} -> {direction}"
                    )

            logger.debug(
                f"Multi-key component {type(widget).__name__} registered: {success_count}/{total_count}"
            )

        elif hasattr(widget, "final_keys") and widget.final_keys:
            # 传统的单按键映射组件
            # 直接使用KeyCombination对象进行注册
            for key_combination in widget.final_keys:
                success = self.register_widget_key_mapping(widget, key_combination)
                if success:
                    logger.debug(
                        f"Auto register component default key mapping: {key_combination} -> {type(widget).__name__}"
                    )
                    # 更新组件显示文本以反映注册的按键
                    if hasattr(widget, "text") and not widget.text:
                        widget.text = str(key_combination)
                else:
                    logger.debug(
                        f"Register component default key mapping failed: {key_combination}"
                    )
        else:
            logger.debug(
                f"Component {type(widget).__name__} has no default key, skip auto registration"
            )

    def on_clear_widgets(self, button: Gtk.Button | None):
        """清空所有组件"""
        widgets_to_delete = []
        child = self.fixed.get_first_child()
        while child:
            widgets_to_delete.append(child)
            child = child.get_next_sibling()

        # 清理每个widget的按键映射，然后从UI中移除
        for widget in widgets_to_delete:
            # 清理widget的按键映射
            self.unregister_widget_key_mapping(widget)
            # 从UI中移除widget
            self.fixed.remove(widget)
            logger.debug(
                f"Clear widget {type(widget).__name__}(id={id(widget)}) and its key mapping"
            )

        # 清除交互状态
        self.workspace_manager.dragging_widget = None
        self.workspace_manager.resizing_widget = None

        logger.debug(
            f"Clear all components, {len(widgets_to_delete)} widgets and their key mappings"
        )

    def get_physical_keyval(self, keycode):
        """获取物理按键对应的标准 keyval（不受修饰键影响）"""
        try:
            display = self.get_display()
            if display:
                success, keyval, _, _, _ = display.translate_key(
                    keycode=keycode, state=Gdk.ModifierType(0), group=0
                )
                if success:
                    return Gdk.keyval_to_upper(keyval)
        except Exception as e:
            logger.debug(f"Failed to get physical keyval: {e}")
        return 0

    def on_global_key_press(self, controller, keyval, keycode, state):
        """全局键盘事件 - 支持双模式，使用事件处理器链"""
        # 特殊按键：模式切换和调试功能 - 这些直接用原始keyval判断
        if keyval == Gdk.KEY_F1:
            # F1在两个模式之间切换
            if self.current_mode == self.EDIT_MODE:
                self.switch_mode(self.MAPPING_MODE)
            else:
                self.switch_mode(self.EDIT_MODE)
            return True
        # elif keyval == Gdk.KEY_F2:
        #     self.switch_mode(self.MAPPING_MODE)
        #     return True
        # elif keyval == Gdk.KEY_F3:
        #     # F3显示当前按键映射状态
        #     self.print_key_mappings()
        #     return True
        # elif keyval == Gdk.KEY_F4:
        #     # F4显示事件处理器状态
        #     self.print_event_handlers_status()
        #     return True

        # 在映射模式下使用事件处理器链
        if self.current_mode == self.MAPPING_MODE:
            logger.debug("In mapping mode, use event handler chain to handle key event")

            # 获取物理按键的标准 keyval
            physical_keyval = self.get_physical_keyval(keycode)
            if physical_keyval == 0:
                # 如果获取失败，回退到原始 keyval
                physical_keyval = keyval
                logger.debug(f"Fallback to original keyval: {Gdk.keyval_name(keyval)}")

            # 处理修饰键本身
            if self._is_modifier_key(keyval):
                main_key = key_registry.create_from_keyval(keyval)
            else:
                main_key = key_registry.create_from_keyval(physical_keyval)

            if main_key:
                # 收集修饰键
                modifiers = []
                if state & Gdk.ModifierType.CONTROL_MASK:
                    ctrl_key = key_registry.get_by_name("Ctrl_L")
                    if ctrl_key:
                        modifiers.append(ctrl_key)
                if state & Gdk.ModifierType.ALT_MASK:
                    alt_key = key_registry.get_by_name("Alt_L")
                    if alt_key:
                        modifiers.append(alt_key)
                if state & Gdk.ModifierType.SHIFT_MASK:
                    shift_key = key_registry.get_by_name("Shift_L")
                    if shift_key:
                        modifiers.append(shift_key)
                if state & Gdk.ModifierType.SUPER_MASK:
                    super_key = key_registry.get_by_name("Super_L")
                    if super_key:
                        modifiers.append(super_key)

                # 创建输入事件
                event = InputEvent(
                    event_type="key_press",
                    key=main_key,
                    modifiers=modifiers,
                    raw_data={
                        "controller": controller,
                        "keyval": keyval,
                        "keycode": keycode,
                        "state": state,
                    },
                )

                # 使用事件处理器链处理
                handled = self.event_handler_chain.process_event(event)
                if handled:
                    logger.debug("Key event handled by event handler chain")
                    return True
                else:
                    logger.debug("Key event not handled by any event handler")

        # 编辑模式或映射模式下的通用按键
        if keyval == Gdk.KEY_Escape:
            if self.current_mode == self.EDIT_MODE:
                # 编辑模式：取消所有选择
                self.clear_all_selections()
            else:
                # 映射模式：暂时什么都不做，或者可以切换回编辑模式
                logger.debug("In mapping mode, press ESC key")
            return True

        # 只在编辑模式下处理编辑相关按键
        if self.current_mode == self.EDIT_MODE:
            if keyval == Gdk.KEY_Delete:
                # Delete键删除选中的widget
                self.workspace_manager.delete_selected_widgets()
                return True

        return False

    def delete_selected_widgets(self):
        """删除所有选中的widget"""
        self.workspace_manager.delete_selected_widgets()

    # ===================提示信息方法===================

    def show_notification(self, text: str):
        """显示带渐隐效果的提示信息"""
        self.notification_label.set_label(text)

        # 停止任何正在进行的动画
        if (
            hasattr(self, "_notification_fade_out_timer")
            and self._notification_fade_out_timer > 0
        ):
            GLib.source_remove(self._notification_fade_out_timer)
        if hasattr(self, "_notification_animation"):
            self._notification_animation.reset()

        # 淡入动画
        self.notification_box.set_opacity(0)
        animation_target = Adw.PropertyAnimationTarget.new(
            self.notification_box, "opacity"
        )
        self._notification_animation = Adw.TimedAnimation.new(
            self.notification_box, 0.0, 1.0, 300, animation_target
        )
        self._notification_animation.set_easing(Adw.Easing.LINEAR)
        self._notification_animation.play()

        # 计划淡出
        self._notification_fade_out_timer = GLib.timeout_add(
            1500, self._fade_out_notification
        )

    def _fade_out_notification(self):
        """执行淡出动画"""
        animation_target = Adw.PropertyAnimationTarget.new(
            self.notification_box, "opacity"
        )
        self._notification_animation = Adw.TimedAnimation.new(
            self.notification_box, 1.0, 0.0, 500, animation_target
        )
        self._notification_animation.set_easing(Adw.Easing.LINEAR)
        self._notification_animation.play()
        self._notification_fade_out_timer = 0
        return GLib.SOURCE_REMOVE

    # ===================双模式系统方法===================

    def _on_mode_changed(self, widget, pspec):
        """模式属性变化时的回调"""
        new_mode = self.current_mode
        logger.debug(f"Mode changed to: {new_mode}")

        # 通知所有widget切换绘制模式
        mapping_mode = new_mode == self.MAPPING_MODE
        self.set_all_widgets_mapping_mode(mapping_mode)

        # 根据新模式调整UI状态
        if new_mode == self.MAPPING_MODE:
            # 进入映射模式：取消所有选择，禁用编辑功能
            self.clear_all_selections()
            logger.debug("Enter mapping mode, edit function disabled")

            self.show_notification(_("Mapping Mode (F1: Switch Mode)"))

            # 可以在这里添加更多映射模式的UI调整
            # 比如改变窗口标题、显示状态指示器等
            self.set_title(f"{APP_TITLE} - Mapping Mode (F1: Switch Mode)")
            self.set_cursor_from_name("default")

            # 显示映射模式帮助信息
            logger.debug("Enter mapping mode!")
            logger.debug(
                f"- Press configured key combination to trigger corresponding widget action"
            )
            logger.debug("- F1: Switch to edit mode")
            logger.debug("- ESC: Other operations")

        else:
            # 进入编辑模式：恢复编辑功能
            logger.debug("Enter edit mode, edit function enabled")
            self.show_notification(_("Edit Mode (F1: Switch Mode)"))
            self.set_title(f"{APP_TITLE} - Edit Mode (F1: Switch Mode)")

            # 显示编辑模式帮助信息
            logger.debug("Enter edit mode!")
            logger.debug("- Right click on blank area: create widget")
            logger.debug("- Double click widget: edit key mapping")
            logger.debug("- Left click drag: move widget")
            logger.debug("- Delete: delete selected widget")
            logger.debug("- F1: Switch to mapping mode")

    def switch_mode(self, new_mode):
        """切换模式"""
        if new_mode not in [self.EDIT_MODE, self.MAPPING_MODE]:
            logger.debug(f"Invalid mode: {new_mode}")
            return False

        if self.current_mode == new_mode:
            logger.debug(f"Already in {new_mode} mode")
            return True

        logger.debug(f"Switch mode: {self.current_mode} -> {new_mode}")

        # 使用属性系统设置模式，会自动触发_on_mode_changed回调
        self.set_property("current-mode", new_mode)

        return True

    def format_key_combination(self, keyval, state) -> KeyCombination:
        """将按键事件格式化为 KeyCombination"""
        keys = []

        # 添加修饰键
        if state & Gdk.ModifierType.CONTROL_MASK:
            ctrl_key = key_registry.get_by_name("Ctrl")
            if ctrl_key:
                keys.append(ctrl_key)
        if state & Gdk.ModifierType.ALT_MASK:
            alt_key = key_registry.get_by_name("Alt")
            if alt_key:
                keys.append(alt_key)
        if state & Gdk.ModifierType.SHIFT_MASK:
            shift_key = key_registry.get_by_name("Shift")
            if shift_key:
                keys.append(shift_key)
        if state & Gdk.ModifierType.SUPER_MASK:
            super_key = key_registry.get_by_name("Super")
            if super_key:
                keys.append(super_key)

        # 获取主要按键
        main_key = key_registry.create_from_keyval(keyval, state)
        if main_key:
            keys.append(main_key)

        return KeyCombination(keys)

    def register_widget_key_mapping(
        self, widget, key_combination: KeyCombination
    ) -> bool:
        """注册widget的按键映射"""
        return key_mapping_manager.subscribe(widget, key_combination)

    def unregister_widget_key_mapping(self, widget) -> bool:
        """取消widget的所有按键映射"""
        return key_mapping_manager.unsubscribe(widget)

    def unregister_single_widget_key_mapping(
        self, widget, key_combination: KeyCombination
    ) -> bool:
        """取消widget的单个按键映射"""
        return key_mapping_manager.unsubscribe_key(widget, key_combination)

    def get_widget_key_mapping(self, widget) -> list[KeyCombination]:
        """获取指定widget的按键映射列表"""
        return key_mapping_manager.get_subscriptions(widget)

    def print_key_mappings(self):
        """打印当前所有的按键映射（调试用）"""
        key_mapping_manager.print_mappings()

    def clear_all_key_mappings(self):
        """清空所有按键映射"""
        return key_mapping_manager.clear()

    def on_global_key_release(self, controller, keyval, keycode, state):
        """全局按键释放事件 - 使用事件处理器链"""
        if self.current_mode == self.MAPPING_MODE:
            logger.debug(
                "In mapping mode, use event handler chain to handle key release"
            )

            # 获取物理按键的标准 keyval
            physical_keyval = self.get_physical_keyval(keycode)
            if physical_keyval == 0:
                # 如果获取失败，回退到原始 keyval
                physical_keyval = keyval
                logger.debug(
                    f"Release fallback to original keyval: {Gdk.keyval_name(keyval)}"
                )

            # 处理修饰键本身
            if self._is_modifier_key(keyval):
                main_key = key_registry.create_from_keyval(keyval)
            else:
                main_key = key_registry.create_from_keyval(physical_keyval)

            if main_key:
                # 收集修饰键
                modifiers = []
                if state & Gdk.ModifierType.CONTROL_MASK:
                    ctrl_key = key_registry.get_by_name("Ctrl_L")
                    if ctrl_key:
                        modifiers.append(ctrl_key)
                if state & Gdk.ModifierType.ALT_MASK:
                    alt_key = key_registry.get_by_name("Alt_L")
                    if alt_key:
                        modifiers.append(alt_key)
                if state & Gdk.ModifierType.SHIFT_MASK:
                    shift_key = key_registry.get_by_name("Shift_L")
                    if shift_key:
                        modifiers.append(shift_key)
                if state & Gdk.ModifierType.SUPER_MASK:
                    super_key = key_registry.get_by_name("Super_L")
                    if super_key:
                        modifiers.append(super_key)

                # 创建输入事件
                event = InputEvent(
                    event_type="key_release",
                    key=main_key,
                    modifiers=modifiers,
                    raw_data={
                        "controller": controller,
                        "keyval": keyval,
                        "keycode": keycode,
                        "state": state,
                    },
                )

                # 使用事件处理器链处理
                handled = self.event_handler_chain.process_event(event)
                if handled:
                    logger.debug("Key release event handled by event handler chain")
                    return True
                else:
                    logger.debug("Key release event not handled by any event handler")

        return False

    def _is_modifier_key(self, keyval):
        """检查是否是修饰键"""
        modifier_keys = {
            Gdk.KEY_Control_L,
            Gdk.KEY_Control_R,
            Gdk.KEY_Alt_L,
            Gdk.KEY_Alt_R,
            Gdk.KEY_Shift_L,
            Gdk.KEY_Shift_R,
            Gdk.KEY_Super_L,
            Gdk.KEY_Super_R,
            Gdk.KEY_Meta_L,
            Gdk.KEY_Meta_R,
            Gdk.KEY_Hyper_L,
            Gdk.KEY_Hyper_R,
        }
        return keyval in modifier_keys

    def print_event_handlers_status(self):
        """打印事件处理器状态（调试用）"""
        print(f"\n[DEBUG] ==================Event handler status==================")
        print(
            f"[DEBUG] Event handler chain status: {'Enabled' if self.event_handler_chain.enabled else 'Disabled'}"
        )

        handlers_info = self.event_handler_chain.get_handlers_info()
        for info in handlers_info:
            status = "启用" if info["enabled"] else "禁用"
            print(f"[DEBUG] - {info['name']}: 优先级={info['priority']}, 状态={status}")

        # 显示默认处理器的映射
        print(
            f"[DEBUG] 默认处理器按键映射: {list(self.default_handler.key_mappings.keys())}"
        )
        print(
            f"[DEBUG] 默认处理器鼠标映射: {list(self.default_handler.mouse_mappings.keys())}"
        )
        print(f"[DEBUG] ================================================\n")
