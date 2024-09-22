import logging
import gi


gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from .mouse_base import MouseBase
from .control_msg import (
    InjectScrollEventMsg,
    InjectTouchEventMsg,
)
from .controller import Controller
from .input import AMontionEventAction, AMontionEventButtons
from app.pointer_id import PointerId
from gi.repository import Gdk, Gtk

logger = logging.getLogger(__name__)


class MouseSdk(MouseBase):
    def __init__(self, controller: Controller) -> None:
        self.controller = controller
        self.natural_scroll = True
        self.mouse_hover = False

    def convert_click_action(self, event):
        if event.get_event_type() == Gdk.EventType.BUTTON_PRESS:
            action = AMontionEventAction.DOWN
        else:
            action = AMontionEventAction.UP
        return action

    def convert_button(self, event):
        button = event.get_button()
        if button == Gdk.BUTTON_PRIMARY:
            return AMontionEventButtons.PRIMARY
        elif button == Gdk.BUTTON_MIDDLE:
            return AMontionEventButtons.TERTIARY
        elif button == Gdk.BUTTON_SECONDARY:
            return AMontionEventButtons.SECONDARY
        else:
            return 0

    def convert_buttons(self, event, action_button=None):
        state = event.get_modifier_state()
        buttons = 0
        if state & Gdk.ModifierType.BUTTON1_MASK:
            buttons |= AMontionEventButtons.PRIMARY
        if state & Gdk.ModifierType.BUTTON2_MASK:
            buttons |= AMontionEventButtons.TERTIARY
        if state & Gdk.ModifierType.BUTTON3_MASK:
            buttons |= AMontionEventButtons.SECONDARY
        if action_button:
            buttons ^= action_button
        return buttons

    def motion_processor(self, controller: Gtk.EventControllerMotion, x, y):
        # print(controller.get_current_event().get_event_type(), x, y)
        w = controller.get_widget().get_root().get_width()
        h = controller.get_widget().get_root().get_height()
        buttons_state = self.convert_buttons(controller.get_current_event())
        if not self.mouse_hover and buttons_state == 0:
            return False
        action = (
            AMontionEventAction.MOVE
            if buttons_state != 0
            else AMontionEventAction.HOVER_MOVE
        )
        x = max(0, x)
        y = max(0, y)
        position = (int(x), int(y), w, h)
        pressure = 1.0
        msg = InjectTouchEventMsg(
            action=action,
            pointer_id=PointerId.MOUSE,
            position=position,
            pressure=pressure,
            action_button=0,
            buttons=buttons_state,
        )
        self.controller.send_msg(msg)
        return True

    def click_processor(self, controller: Gtk.GestureClick, n_press, x, y):
        w = controller.get_widget().get_root().get_width()
        h = controller.get_widget().get_root().get_height()
        action = self.convert_click_action(controller.get_current_event())
        position = (int(x), int(y), w, h)
        pressure = 1.0 if action == AMontionEventAction.DOWN else 0.0
        action_button = self.convert_button(controller.get_current_event())
        buttons = self.convert_buttons(controller.get_current_event(), action_button)
        msg = InjectTouchEventMsg(
            action=action,
            pointer_id=PointerId.MOUSE,
            position=position,
            pressure=pressure,
            action_button=action_button,
            buttons=buttons,
        )
        self.controller.send_msg(msg)
        return True

    def scroll_processor(self, controller, dx=None, dy=None):
        if controller.get_current_event() is None:
            return False
        begin, x, y = controller.get_current_event().get_position()
        w = controller.get_widget().get_root().get_width()
        h = controller.get_widget().get_root().get_height()
        state = controller.get_current_event().get_modifier_state()
        if begin:
            self.scroll_begin_x = round(x)
            self.scroll_begin_y = round(y)
            # ctrl+scroll begin
            self.ctrl_zoom_range = 1.0

        # ctrl+scroll
        if (state & Gdk.ModifierType.CONTROL_MASK) and dy is not None:
            self.ctrl_zoom_range = self.ctrl_zoom_range + dy * 0.01
            if self.ctrl_zoom_range <= 0.01:
                self.ctrl_zoom_range = 0.01
            return self.zoom_processor(controller, self.ctrl_zoom_range)
        else:

            position = (self.scroll_begin_x, self.scroll_begin_y, w, h)
            hscroll = dx if dx else 0
            vscroll = dy if dy else 0
            if controller.get_unit() == Gdk.ScrollUnit.SURFACE:
                hscroll = float(hscroll)
                vscroll = float(vscroll)
            if hscroll == 0 and vscroll == 0:
                return False
            if self.natural_scroll:
                hscroll = -hscroll
                vscroll = -vscroll
            buttons = self.convert_buttons(controller.get_current_event())
            msg = InjectScrollEventMsg(position, hscroll, vscroll, buttons)
            self.controller.send_msg(msg)
            return True

    def touch_processor(self):
        return True

    def zoom_processor(self, controller, range):
        print(self.scroll_begin_x, self.scroll_begin_y)
        # msg = ControlMsg(
        #     ControlMsgType.INJECT_TOUCH_EVENT,
        #     {
        #         "action": action,
        #         "position": [int(x), int(y), w, h],
        #         "pressure": pressure,
        #         "action_button": action_button,
        #         "buttons": buttons,
        #     },
        # )
        # logging.info(msg.data)
        # self.server.send(msg.pack())
        logging.info(range)
        return True
