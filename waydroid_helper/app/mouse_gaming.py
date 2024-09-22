import logging
from typing import List
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from .mouse_base import MouseBase
from .control_msg import ControlMsg, ControlMsgType
from .server import Server
from .input import AMontionEventAction, AMontionEventButtons
from .wayland_pointer_lock import PointerConstraint
from app.widgets.mapping_button import MappingButton
from gi.repository import Gdk, Gtk

logger = logging.getLogger(__name__)


class MouseGaming(MouseBase):

    def __init__(self, server, mapping_keys:List[MappingButton]) -> None:
        self.server: Server = server
        self.pointer_constraint: PointerConstraint = None

    def zoom_processor(self, controller, range) -> bool:
        # print("zoom")
        return False

    def relative_motion_processor(self, obj, dx, dy, dx_unaccel, dy_unaccel):
        logging.info(f"{dx}, {dy}, {dx_unaccel}, {dy_unaccel}")

    def click_processor(self, controller: Gtk.GestureClick, n_press, x, y) -> bool:
        if not self.pointer_constraint:
            self.pointer_constraint = PointerConstraint(
                controller.get_widget().get_root()
            )
            self.pointer_constraint.setup()
            self.pointer_constraint.connect(
                "relative-motion", self.relative_motion_processor
            )

        action = controller.get_current_event().get_event_type()
        button = controller.get_current_button()
        if action == Gdk.EventType.BUTTON_PRESS and button == Gdk.BUTTON_SECONDARY:
            if not self.pointer_constraint.locked_pointer:
                self.pointer_constraint.lock_pointer()
                print("锁定")
            else:
                print("解锁")
                self.pointer_constraint.unlock_pointer()
        return False

    def motion_processor(self, controller, x, y) -> bool:
        # print("motion")
        return False

    def scroll_processor(self, controller, dx=None, dy=None) -> bool:
        # print("scroll")
        return False
