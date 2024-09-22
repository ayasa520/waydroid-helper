import logging
import gi


gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk, Gio
from collections import deque
from .keyboard_base import KeyboardBase
from .controller import Controller
from app.mouse_base import MouseBase
from app.widgets.shortcut import ShortCut
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.widgets.mapping_button import MappingButton


logger = logging.getLogger(__name__)


class KeyboardMouseGaming(KeyboardBase, MouseBase):
    def __init__(self, controller: Controller, mapping_buttons: Gio.ListStore) -> None:
        self.controller = controller
        self.mapping_buttons = mapping_buttons
        self.pressed = set()
        self.activated: set[ShortCut] = set()
        self.mapping_dict = {
            key: btn for btn in self.mapping_buttons for key in btn.keys
        }
        self.available_pointer_ids = deque(range(1, 11))
        # self.occupied_ids = bidict()
        self.mapping_buttons.connect("items-changed", self.on_mapping_button_changed)
        self.ignore_dict = {"Fire": True}

        for btn in self.mapping_buttons:
            # if isinstance(btn, HotkeyEditableWidget):
            btn.observer = self

    def on_mapping_button_changed(self, l, position, removed, added):
        if added > 0:
            for i in range(position, added + position):
                btn: MappingButton = self.mapping_buttons.get_item(i)
                btn.observer = self
                for key in btn.keys:
                    if key != ShortCut([]):
                        self.mapping_dict.update({key: btn})
        elif removed > 0:
            for i in range(position, position + removed):
                btn: MappingButton = self.mapping_buttons.get_item(i)
                for key in btn.keys:
                    self.mapping_dict.pop(key, None)

    def occupy_id(self):
        if self.available_pointer_ids:
            return self.available_pointer_ids.popleft()
        return None

    def release_id(self, id: int):
        self.available_pointer_ids.append(id)

    # def occupy_id(self, mapping_button):
    # id = self.occupied_ids.inverse.get(mapping_button)
    # if id:
    #     return id
    # if not self.available_pointer_ids:
    #     return None
    # id = self.available_pointer_ids.popleft()
    # self.occupied_ids[id] = mapping_button
    # return id

    # def release_id(self, mapping_button):
    #     id = self.occupied_ids.inverse.get(mapping_button)
    #     if id is None:
    #         return None
    #     self.available_pointer_ids.append(id)
    #     self.occupied_ids.pop(id)
    #     return id
    def get_upper_low_level_keyval(self, display, keycode):
        if display.map_keycode(keycode)[0]:
            low_level_keyval = display.translate_key(
                keycode=keycode, state=0, group=0
            ).keyval
            return Gdk.keyval_to_upper(low_level_keyval)
        return 0

    def key_mouse_processor(self, keyval) -> bool:
        new_events: set[ShortCut] = set()
        for keys, key in self.mapping_dict.items():
            if keys.key.issubset(self.pressed):
                is_superset = False
                for other_keys in self.mapping_dict.keys():
                    if (
                        keys != other_keys
                        and keys.key.issubset(other_keys.key)
                        and other_keys.key.issubset(self.pressed)
                    ):
                        is_superset = True
                        break
                if not is_superset:
                    new_events.add(keys)

        flag = False
        # Check for stopped eventkeys
        for key in self.activated - new_events:
            # pointer_id = self.release_id(self.mapping_dict[key])
            # if pointer_id:
            #     self.mapping_dict[key].mapping_end(
            #         key, self.server, pointer_id
            #     )
            # pointer_id = self.occupied_ids.inverse.get(self.mapping_dict[key])
            # if pointer_id and self.mapping_dict[key].mapping_end(
            #     key, self.server, pointer_id
            # ):
            #     self.release_id(self.mapping_dict[key])
            if self.ignore_dict.get(self.mapping_dict[key].__class__.__name__, False):
                continue
            self.mapping_dict[key].mapping_end(key)
            if keyval in key.key:
                flag = True

        # Check for started events
        for key in new_events - self.activated:
            # pointer_id = self.occupy_id(self.mapping_dict[key])
            # if pointer_id:
            #     self.mapping_dict[key].mapping_start(key, self.server, pointer_id)
            if self.ignore_dict.get(self.mapping_dict[key].__class__.__name__, False):
                continue
            self.mapping_dict[key].mapping_start(key)
            if keyval in key.key:
                flag = True

        self.activated = new_events
        return flag

    def key_processor(
        self, controller: Gtk.EventControllerKey, keyval, keycode, state
    ) -> bool:
        # 确实效率有点儿低了, 如果放弃支持组合键的话, 可以极大提高效率
        keyval = self.get_upper_low_level_keyval(
            controller.get_widget().get_display(), keycode
        )
        if controller.get_current_event().get_event_type() == Gdk.EventType.KEY_PRESS:
            self.pressed.add(keyval)
        else:
            self.pressed.discard(keyval)

        return self.key_mouse_processor(keyval)

    def update(self, mapping_buton, old_key, new_key):
        logger.info(
            f"{mapping_buton} {[Gdk.keyval_name(k) for k in old_key.key]} {[Gdk.keyval_name(k) for k in new_key.key]}"
        )
        self.mapping_dict.pop(old_key, None)
        self.mapping_dict[new_key] = mapping_buton
        if old_key in self.activated:
            self.mapping_dict[new_key].mapping_end(new_key)
            self.activated.remove(old_key)

    def set_ignore(self, type: str, flag: bool):
        self.ignore_dict[type] = flag

    def set_ignore_fire(self, flag):
        self.set_ignore("Fire", flag)

    def click_processor(self, controller: Gtk.GestureClick, n_press, x, y) -> bool:
        btn = controller.get_current_button()
        if (
            controller.get_current_event().get_event_type()
            == Gdk.EventType.BUTTON_PRESS
        ):
            self.pressed.add(btn)
        else:
            self.pressed.discard(btn)
        return self.key_mouse_processor(btn)

    def scroll_processor(self, controller, dx=None, dy=None) -> bool:
        return False

    def motion_processor(self, controller, x, y) -> bool:
        return False

    def zoom_processor(self, controller, range) -> bool:
        return False
