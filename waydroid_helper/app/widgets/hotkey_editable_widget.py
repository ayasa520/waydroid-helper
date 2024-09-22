from typing import Any, Callable, List, TypeVar, runtime_checkable, Protocol
import gi

from app.widgets.MappingButtonState import MappingButtonState

from .shortcut import ShortCut
from app.keyboard_mouse_gaming import KeyboardMouseGaming


gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "4.0")

from abc import ABC, abstractmethod
from gi.repository import Gdk, GLib, Gtk


#TODO abc 换成 protocal
@runtime_checkable
class EditableProtocol(Protocol):
    cursor_visible: bool
    cursor_timer: ...
    key_editing_mode: bool
    _pressed_keys: List[int]
    _old_keys: ...

    @property
    def observer(self) -> KeyboardMouseGaming: ...
    @property
    def keys(self) -> List[ShortCut]: ...
    @property
    def max_keys(self) -> int: ...
    def add_controller(self, controller: Gtk.EventController) -> None: ...
    def is_focus(self) -> bool: ...
    def has_focus(self) -> bool: ...
    def add_css_class(self, css_class: str) -> None: ...
    def remove_css_class(self, css_class: str) -> None: ...
    def notify_update(self) -> None: ...
    def start_cursor_blink(self) -> None: ...
    def blink_cursor(self) -> None: ...
    def stop_cursor_blink(self) -> None: ...
    def queue_draw(self) -> None: ...
    def connect(
        self, detailed_signal: str, handler: Callable[..., Any], *args: Any
    ) -> int: ...
    def on_editing_key_pressed(
        self, controller: Gtk.EventController, keyval: int, keycode: int, state
    ): ...
    def on_editing_key_released(
        self, controller: Gtk.EventController, keyval: int, keycode: int, state
    ): ...
    def on_editing_mouse_pressed(
        self, controller: Gtk.GestureClick, n_press: int, x: float, y: float
    ): ...
    def on_editing_mouse_released(
        self, controller: Gtk.GestureClick, n_press: int, x: float, y: float
    ): ...


T = TypeVar("T", bound=EditableProtocol)


class KeyEditableWidget(ABC):
    def __init__(self, *args, **kwargs):
        # 调用 MappingButton 的 __init__
        super().__init__(*args, **kwargs)
        self.cursor_visible = False
        self.cursor_timer = None
        # 快捷键编辑状态
        # edit_mode 开启: 存下当前 old_keys; 关闭: 获取当前 new_keys, 比较并发送更新信号
        self.key_editing_mode = False
        self._pressed_keys = []
        self._old_keys = None
        self.setup_controller()

    # @GObject.Signal(name="key-changed", arg_types=(Gtk.Widget, object, object))
    # def key_changed(self, widget, old_key, new_key):
    #     pass
    # __gsignals__ = {
    #     "key-changed": (
    #         GObject.SignalFlags.RUN_FIRST,
    #         None,
    #         (object, object),
    #     )
    # }

    def notify_update(self: T):
        if self._old_keys is None:
            return
        new_keys = set(self.keys) - set(self._old_keys)
        old_keys = set(self._old_keys) - set(self.keys)
        if not old_keys:
            old_keys = set([ShortCut([])])
        if self.observer:
            for new_key, old_key in zip(new_keys, old_keys):
                if new_key != old_key:
                    self.observer.update(self, old_key, new_key)

    def start_cursor_blink(self: T):
        self.cursor_visible = True
        self.queue_draw()
        self.cursor_timer = GLib.timeout_add(500, self.blink_cursor)

    def blink_cursor(self: T):
        self.cursor_visible = not self.cursor_visible
        self.queue_draw()
        return True  # 返回 True 以保持定时器运行

    def stop_cursor_blink(self: T):
        if self.cursor_timer:
            GLib.source_remove(self.cursor_timer)
            self.cursor_timer = None
        self.cursor_visible = False

    def setup_controller(self: T):
        self.click_controller = Gtk.GestureClick()
        self.click_controller.set_button(button=0)
        self.click_controller.connect("pressed", self.on_editing_mouse_pressed)
        self.click_controller.connect("released", self.on_editing_mouse_released)
        self.add_controller(self.click_controller)

        self.key_controller = Gtk.EventControllerKey()
        self.key_controller.connect("key-pressed", self.on_editing_key_pressed)
        self.key_controller.connect("key-released", self.on_editing_key_released)
        self.add_controller(self.key_controller)

        self.connect("notify::has-focus", self.on_edit_focus)

    def on_editing_mouse_pressed(self, controller:Gtk.GestureClick, n_press, x, y):
        if n_press >= 2:
            self.stop_cursor_blink()
            self.start_cursor_blink()
            self.key_editing_mode = True
            # TODO
            self._old_keys = self.keys.copy()
            return

        if not self.key_editing_mode:
            return
        btn = controller.get_current_button()
        if btn and btn not in self._pressed_keys:
            if len(self._pressed_keys) >= self.max_keys:
                self._pressed_keys.pop(-1)
            self._pressed_keys.append(btn)

        self.update_result_label()

    def on_editing_mouse_released(self, controller, n_press, x, y):
        if not self.key_editing_mode:
            return False
        btn = controller.get_current_button()
        if btn in self._pressed_keys:
            self._pressed_keys.remove(btn)

    def on_edit_focus(self: T, widget, event):
        if self.has_focus():
            # 改为双击编辑快捷键
            self.key_controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
            self.click_controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        else:
            # 失去焦点:1. 停止闪烁; 2. 停止接收键盘事件
            self.stop_cursor_blink()
            self.key_controller.set_propagation_phase(Gtk.PropagationPhase.NONE)
            self.click_controller.set_propagation_phase(Gtk.PropagationPhase.NONE)
            # TODO
            if self.key_editing_mode == True:
                self.notify_update()
                self.key_editing_mode = False
            self._pressed_keys.clear()

            # self.emit("key-changed", self._old_key, self._new_key)

    def on_editing_key_pressed(self, controller: Gtk.EventController, keyval, keycode, state):
        if not self.key_editing_mode:
            return False
        low_level_keyval = Gdk.keyval_to_upper(
            self.get_low_level_keyval(controller.get_widget().get_display(), keycode)
        )
        if low_level_keyval and low_level_keyval not in self._pressed_keys:
            if len(self._pressed_keys) >= self.max_keys:
                self._pressed_keys.pop(-1)
            self._pressed_keys.append(low_level_keyval)

        self.update_result_label()
        return True

    def on_editing_key_released(self, controller: Gtk.EventController, keyval, keycode, state):
        if not self.key_editing_mode:
            return False
        low_level_keyval = Gdk.keyval_to_upper(
            self.get_low_level_keyval(controller.get_widget().get_display(), keycode)
        )

        if low_level_keyval in self._pressed_keys:
            self._pressed_keys.remove(low_level_keyval)
        return True

    def get_low_level_keyval(self: T, display: Gdk.Display, keycode):
        if display.map_keycode(keycode)[0]:
            low_level_keyval = display.translate_key(
                keycode=keycode, state=0, group=0
            ).keyval
            return low_level_keyval
        return 0

    @abstractmethod
    def update_result_label(self):
        raise NotImplementedError("Subclasses should implement this method.")
