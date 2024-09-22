import asyncio
import gi
import logging

from app.widgets.repeated_click import RepeatedClick
from app.controller import Controller
from app.widgets.fire import Fire


gi.require_version("PangoCairo", "1.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from app.widgets.mapping_button import MappingButton
from app.widgets.shortcut import ShortCut
from app.widgets.directional_pad import DirectionalPad
from app.widgets.single_click import SingleClick
from app.widgets.resizable import Resizable, ResizeEdge
from app.factory import EventHandlerFactory
from app.gaming_handler_factory import GamingHandlerFactory
from app.sdk_handler_factory import SdkHandlerFactory
from app.widgets.aim import Aim
from dataclasses import dataclass
from typing import List, Optional

from gi.repository import Gtk, Gdk, Adw, Gio

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)


gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GObject
from gi.events import GLibEventLoopPolicy
from app.server import Server

# Constants
WINDOW_TITLE = "Event Capture Window"
DEFAULT_PORT = 10721
CSS_SELECTED = " .selected { border: 1px solid; } "
CSS_TRANSPARENT = " #mapping-widgwet { background-color: rgba(0, 0, 0, 0); } "


@dataclass
class DragState:
    r_start_x: float = 0
    r_start_y: float = 0
    resize_edge: Optional[ResizeEdge] = None


class InputManager:
    def __init__(
        self, normal_factory: EventHandlerFactory, mapping_factory: EventHandlerFactory
    ) -> None:
        # self.mapping_factory = mapping_factory
        self.normal_mouse_control = normal_factory.create_mouse_handler()
        self.normal_kbd_control = normal_factory.create_keyboard_handler()
        self.mapping_mouse_control = mapping_factory.create_mouse_handler()
        self.mapping_kdb_control = mapping_factory.create_keyboard_handler()

    # def conditional_execution(condition_method, default_return=None):
    #     def decorator(func):
    #         @functools.wraps(func)
    #         def wrapper(self, *args, **kwargs):
    #             if condition_method(self):
    #                 return func(self, *args, **kwargs)
    #             return default_return  # 或者其他默认值

    #         return wrapper

    #     return decorator

    def key_processor(self, controller, keyval, keycode, state) -> bool:
        result = self.mapping_kdb_control.key_processor(
            controller, keyval, keycode, state
        )
        if not result:
            self.normal_kbd_control.key_processor(controller, keyval, keycode, state)
        return result

    def zoom_processor(self, controller, range):
        result = self.mapping_mouse_control.zoom_processor(controller, range)
        if not result:
            self.normal_mouse_control.zoom_processor(controller, range)

    def click_processor(self, controller, n_press, x, y):
        result = self.mapping_mouse_control.click_processor(controller, n_press, x, y)
        if not result:
            self.normal_mouse_control.click_processor(controller, n_press, x, y)

    def motion_processor(self, controller, x, y):
        result = self.mapping_mouse_control.motion_processor(controller, x, y)
        if not result:
            self.normal_mouse_control.motion_processor(controller, x, y)

    def scroll_processor(self, controller, dx=None, dy=None):
        result = self.mapping_mouse_control.scroll_processor(controller, dx, dy)
        if not result:
            self.normal_mouse_control.scroll_processor(controller, dx, dy)

    def drag_processor(self, controller: Gtk.GestureDrag, x, y):
        pass


class DraggableMenuItem(Gtk.Button):

    def __init__(self, label_text, icon_name, target_type):
        super().__init__()
        self.label = label_text
        self.icon_name = icon_name
        self.target_type = target_type
        # 创建一个垂直的 Gtk.Box 用于放置图标和文本
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # 创建并设置图标，调整图标的大小
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(32)  # 设定图标大小为32像素

        # 创建并设置标签
        label = Gtk.Label(label=label_text)

        # 将图标和标签添加到 box
        box.append(icon)
        box.append(label)

        # 将 box 添加到按钮
        self.set_child(box)

        # 确保按钮是正方形，并固定尺寸
        self.set_size_request(100, 100)  # 设定按钮大小为100x100

        # 防止按钮拉伸
        self.set_hexpand(False)  # 禁止水平扩展
        self.set_vexpand(False)  # 禁止垂直扩展

        drag_controller = Gtk.DragSource()
        drag_controller.connect("prepare", self.on_drag_prepare)
        drag_controller.connect("drag-begin", self.on_drag_begin)
        drag_controller.connect("drag-end", self.on_drag_end)
        self.add_controller(drag_controller)

    def on_drag_prepare(self, _ctrl, _x, _y):
        # print(self.is_focus())
        # print(self.has_focus())
        # print("123")
        item = Gdk.ContentProvider.new_for_value(self)
        return item

    def on_drag_begin(self, ctrl, _drag):
        # print(self.is_focus())
        # print(self.has_focus())
        # print("drag begin")
        icon = Gtk.WidgetPaintable.new(self)
        ctrl.set_icon(icon, 0, 0)

    def on_drag_end(self, source, drag, delete_data):
        # print("drag end")
        pass

    def create_button(self, x, y) -> MappingButton:
        if self.target_type == SingleClick or self.target_type == RepeatedClick:
            return self.target_type(ShortCut([]), x, y)
        elif self.target_type == DirectionalPad:
            return self.target_type(
                ShortCut([]),
                ShortCut([]),
                ShortCut([]),
                ShortCut([]),
                x=x,
                y=y,
            )
        elif self.target_type == Aim:
            return self.target_type(ShortCut([]), x, y, 300, 200)
        elif self.target_type == Fire:
            return self.target_type(x, y)


class CustomPopover(Gtk.Popover):
    def __init__(self, parent):
        super().__init__()
        self.set_parent(parent)
        self.set_has_arrow(False)

        self.set_autohide(False)

        # 创建主布局
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_child(self.main_box)

        # 创建顶部布局，包含关闭按钮
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.main_box.append(top_box)

        # 添加占位符推动关闭按钮到右侧
        top_box.append(Gtk.Label(hexpand=True))

        # 创建关闭按钮（使用符号图标）
        close_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
        close_button.set_css_classes(["flat"])
        close_button.connect("clicked", self.on_close)
        top_box.append(close_button)

        # 创建菜单项的容器

        self.menu_box = Gtk.FlowBox()
        self.menu_box.set_max_children_per_line(3)  # 每行最多显示 3 个按钮
        self.menu_box.set_min_children_per_line(3)
        self.menu_box.set_selection_mode(Gtk.SelectionMode.NONE)  # 禁止选择模式

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        # 添加多个按钮，每个按钮图标在上，文字在下，并确保按钮是正方形的
        item_list = [
            ("SingleClick", "face-smile", SingleClick),
            ("RepeatedClick", "face-smile", RepeatedClick),
            ("D-Pad", "face-smile", DirectionalPad),
            ("Aim", "face-smile", Aim),
            ("Fire", "face-smile", Fire),
        ]
        for i in range(len(item_list)):  # 假设有 9 个按钮
            button = DraggableMenuItem(*(item_list[i]))
            self.menu_box.insert(button, -1)
            size_group.add_widget(button)

        self.main_box.append(self.menu_box)

        # 添加CSS样式
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(
            b"""
        button.flat {
            min-height: 24px;
            min-width: 24px;
            padding: 2px;
            margin: 2px;
            background: none;
            border: none;
            box-shadow: none;
            opacity: 0.7;
            transition: opacity 200ms ease;
        }
        button.flat:hover {
            opacity: 1;
        }
        """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def add_menu_item(self, label, icon_name):
        menu_item = DraggableMenuItem(label, icon_name)

        self.menu_box.append(menu_item)

    def on_close(self, button):
        self.popdown()


class Fixed(Gtk.Fixed):
    editing = GObject.Property(type=bool, default=False)

    def __init__(self):
        super().__init__()
        self.drag_state = DragState()
        # self.labels: List[MappingButton] = []
        self.labels = Gio.ListStore.new(MappingButton)

        # self._setup_labels()
        self._setup_css()
        self._setup_controllers()
        self.set_focusable(False)
        self.set_can_focus(False)

    def _setup_controllers(self):
        drop_controller = Gtk.DropTarget.new(
            type=GObject.TYPE_OBJECT, actions=Gdk.DragAction.COPY
        )
        drop_controller.set_gtypes([DraggableMenuItem])
        drop_controller.connect("drop", self.on_drop)
        self.add_controller(drop_controller)

    def on_drop(self, drop_target, value, x, y):
        if isinstance(value, DraggableMenuItem):
            # label = Gtk.Label(label=value.get_label())
            label = value.create_button(x, y)
            self.put(label, label.action_start_x, label.action_start_y)
            self.bind_property(
                "editing",
                label,
                "editing",
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            )
            self.labels.append(label)
            label.set_focusable(True)
            label.set_can_focus(True)
            label.grab_focus()
            return True
        return False

    def _setup_css(self):
        provider = Gtk.CssProvider.new()
        provider.load_from_data(CSS_SELECTED.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    @property
    def selected(self):
        return self.get_focus_child()

    def get_resize_edge(self, x: float, y: float) -> Optional[ResizeEdge]:
        if not self.selected or not isinstance(self.selected, Resizable):
            return None

        w, h = self.selected.get_width(), self.selected.get_height()
        start_x, start_y = self.get_child_position(self.selected)

        edge_zones = {
            ResizeEdge.WEST: (start_x - 10, start_y, 20, h),
            ResizeEdge.EAST: (start_x + w - 10, start_y, 20, h),
            ResizeEdge.NORTH: (start_x, start_y - 10, w, 20),
            ResizeEdge.SOUTH: (start_x, start_y - 10 + h, w, 20),
        }

        for edge, (zone_x, zone_y, zone_width, zone_height) in edge_zones.items():
            if (zone_x <= x <= zone_x + zone_width) and (
                zone_y <= y <= zone_y + zone_height
            ):
                return edge

        return None

    def get_cursor_name(self, edge: Optional[ResizeEdge]) -> str:
        cursor_map = {
            ResizeEdge.NORTH: "size_ver",
            ResizeEdge.SOUTH: "size_ver",
            ResizeEdge.EAST: "size_hor",
            ResizeEdge.WEST: "size_hor",
        }
        return cursor_map.get(edge, "default")

    def on_motion(self, controller: Gtk.EventController, x: float, y: float):
        if not self.selected or not isinstance(self.selected, Resizable):
            # self.set_cursor(Gdk.Cursor.new_from_name("default"))
            self.get_root().get_surface().set_cursor(Gdk.Cursor.new_from_name("default"))
            return

        state = controller.get_current_event().get_modifier_state()

        # 仅用于鼠标指针样式的改变(当成 hover 用)
        if state & Gdk.ModifierType.BUTTON1_MASK:
            pass
        else:
            edge = self.get_resize_edge(x, y)
            self.drag_state.resize_edge = edge
            cursor_name = self.get_cursor_name(edge)
            cursor = Gdk.Cursor.new_from_name(cursor_name)

            # GtkFixed 和 selected 的 cursor 得分别设置
            self.get_root().get_surface().set_cursor(cursor)
            # self.selected.set_cursor(cursor)
            # self.set_cursor(cursor)

    def on_drag_begin(self, gesture: Gtk.GestureDrag, start_x: float, start_y: float):
        logging.info("drag-begin")
        if not self.drag_state.resize_edge:
            # 非调整大小: 即拖动
            new_selected = self.pick(start_x, start_y, Gtk.PickFlags.DEFAULT)
            new_selected.grab_focus()
            if isinstance(new_selected, Gtk.Fixed):
                return
            selected_x, selected_y = self.get_child_position(self.selected)
            self.drag_state.r_start_x = start_x - selected_x
            self.drag_state.r_start_y = start_y - selected_y
        else:
            # 调整大小
            self.selected_original_w = self.selected.get_width()
            self.selected_original_h = self.selected.get_height()
            self.selected_original_x = self.get_child_position(self.selected)[0]
            self.selected_original_y = self.get_child_position(self.selected)[1]

    def on_drag_update(
        self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ):
        if not self.drag_state.resize_edge:
            logging.info("moving")
            if offset_x == 0.0 and offset_y == 0.0:
                return
            start_point = gesture.get_start_point()
            if start_point and self.selected:
                _, start_x, start_y = start_point
                x = max(0, offset_x + start_x - self.drag_state.r_start_x)
                y = max(0, offset_y + start_y - self.drag_state.r_start_y)
                self.selected.move_action(x, y)
        else:
            logging.info("resizing")
            # resize 时一定非预览状态
            self.selected.resize(
                self.drag_state.resize_edge,
                offset_x,
                offset_y,
                self.selected_original_x,
                self.selected_original_y,
                self.selected_original_w,
                self.selected_original_h,
            )

    def on_drag_end(self, gesture, x, y):
        logging.info("drag-end")
        self.drag_state.r_start_x = 0
        self.drag_state.r_start_y = 0

    def enable_edit_mode(self):
        self.set_focusable(True)
        self.set_can_focus(True)
        for btn in self.labels:
            btn.set_focusable(True)
            btn.set_can_focus(True)

    def disable_edit_mode(self):
        for btn in self.labels:
            btn.set_focusable(False)
            btn.set_can_focus(False)

        if self.selected:
            # self.selected.set_cursor(Gdk.Cursor.new_from_name("default"))
            self.get_root().get_surface().set_cursor(Gdk.Cursor.new_from_name("default"))
        self.grab_focus()
        self.drag_state.resize_edge = None
        # self.set_cursor(Gdk.Cursor.new_from_name("default"))
        self.get_root().get_surface().set_cursor(Gdk.Cursor.new_from_name("default"))
        self.set_focusable(False)
        self.set_can_focus(False)


class EditModeHandler:
    def __init__(self, fixed: Fixed, popover: CustomPopover) -> None:
        self.fixed = fixed
        self.popover = popover

    def key_processor(self, controller, keyval, keycode, state) -> bool:
        return False

    def zoom_processor(self, controller, range):
        pass

    def click_processor(self, controller, n_press, x, y):
        action = controller.get_current_event().get_event_type()
        button = controller.get_current_button()
        if action == Gdk.EventType.BUTTON_PRESS and button == Gdk.BUTTON_SECONDARY:
            rect = Gdk.Rectangle()
            rect.x = int(x)
            rect.y = int(y)
            rect.width = 1
            rect.height = 1
            self.popover.set_pointing_to(rect)
            self.popover.popup()

    def motion_processor(self, controller, x, y):
        self.fixed.on_motion(controller, x, y)

    def scroll_processor(self, controller, dx=None, dy=None):
        pass

    def drag_processor(self, controller: Gtk.GestureDrag, x, y):
        event_type = controller.get_current_event().get_event_type()
        if event_type == Gdk.EventType.BUTTON_PRESS:
            self.fixed.on_drag_begin(controller, x, y)
        elif event_type == Gdk.EventType.MOTION_NOTIFY:
            self.fixed.on_drag_update(controller, x, y)
        elif event_type == Gdk.EventType.BUTTON_RELEASE:
            self.fixed.on_drag_end(controller, x, y)


class EventCaptureWindow(Adw.Window):
    editing = GObject.Property(type=bool, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_window()
        self._setup_widgets()
        self._setup_handlers()
        self._setup_controllers()

    def _init_window(self):
        self.realize()
        self.set_decorated(False)
        monitor = self.get_display().get_monitor_at_surface(self.get_surface())
        self.set_default_size(
            monitor.get_geometry().width, monitor.get_geometry().height
        )
        self.set_title(WINDOW_TITLE)

    def _setup_widgets(self):
        self.fixed = Fixed()
        
        #========================================
        self.fixed.window = self
        #========================================

        self.bind_property(
            "editing",
            self.fixed,
            "editing",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )
        self.set_content(self.fixed)
        self.set_name("mapping-widgwet")

        provider = Gtk.CssProvider.new()
        provider.load_from_data(CSS_TRANSPARENT.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        self.popover = CustomPopover(self)

    def _setup_handlers(self):
        self.server = Server("0.0.0.0", DEFAULT_PORT)
        self.controller = Controller(self.server)
        self.custom_handler = InputManager(
            SdkHandlerFactory(self.server, self.controller),
            GamingHandlerFactory(self.server, self.controller, self.fixed.labels),
        )
        self.editmode_handler = EditModeHandler(self.fixed, self.popover)
        self.handler = self.custom_handler

    def _setup_controllers(self):
        self.add_key_controller()
        self.add_mouse_controller()
        self.add_controller(self.create_shortcut_controller())

    def create_shortcut_controller(self):
        key_ctrl_g = Gtk.ShortcutController()
        key_ctrl_g.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        shortcut = Gtk.Shortcut.new(
            trigger=Gtk.ShortcutTrigger.parse_string("<ctrl>g"),
            action=Gtk.CallbackAction.new(self.toggle_capturing),
        )
        key_ctrl_g.add_shortcut(shortcut)
        return key_ctrl_g

    def toggle_capturing(self, *args):
        self.editing = not self.editing
        if self.editing:
            self.handler = self.editmode_handler
            self.fixed.enable_edit_mode()
        else:
            self.handler = self.custom_handler
            self.fixed.disable_edit_mode()
            self.popover.popdown()

        logging.info(f"Event capturing {'stopped' if self.editing else 'started'}.")
        return True

    def add_key_controller(self):
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.key_processor)
        key_controller.connect("key-released", self.key_processor)
        self.add_controller(key_controller)

    def add_mouse_controller(self):
        controller = Gtk.GestureClick().new()
        controller.set_button(button=0)
        controller.connect("pressed", self.click_processor)
        controller.connect("released", self.click_processor)
        self.add_controller(controller)

        motion_controller = Gtk.EventControllerMotion().new()
        motion_controller.connect("motion", self.motion_processor)
        self.add_controller(motion_controller)

        scroll_controller = Gtk.EventControllerScroll().new(
            Gtk.EventControllerScrollFlags.BOTH_AXES
        )
        scroll_controller.connect("scroll-begin", self.scroll_processor)
        scroll_controller.connect("scroll", self.scroll_processor)
        scroll_controller.connect("scroll-end", self.scroll_processor)
        self.add_controller(scroll_controller)

        zoom_controller = Gtk.GestureZoom().new()
        zoom_controller.connect("scale-changed", self.zoom_processor)
        self.add_controller(zoom_controller)

        # TODO 应该看看 DragSource
        gesture = Gtk.GestureDrag.new()
        gesture.connect("drag-begin", self.drag_processor)
        gesture.connect("drag-update", self.drag_processor)
        gesture.connect("drag-end", self.drag_processor)
        self.add_controller(gesture)

    def key_processor(self, controller, keyval, keycode, state) -> bool:
        return self.handler.key_processor(controller, keyval, keycode, state)

    def click_processor(self, controller, n_press, x, y):
        self.handler.click_processor(controller, n_press, x, y)

    def motion_processor(self, controller, x, y):
        self.handler.motion_processor(controller, x, y)

    def scroll_processor(self, controller, dx=None, dy=None):
        self.handler.scroll_processor(controller, dx, dy)

    def zoom_processor(self, controller, range):
        self.handler.zoom_processor(controller, range)

    def drag_processor(self, gesture, x, y):
        self.handler.drag_processor(gesture, x, y)


def main():
    asyncio.set_event_loop_policy(GLibEventLoopPolicy())
    app = Gtk.Application()
    app.connect("activate", lambda app: EventCaptureWindow(application=app).present())
    app.run()


if __name__ == "__main__":
    main()
