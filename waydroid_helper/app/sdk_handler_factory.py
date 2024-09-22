from .keyboard_sdk import KeyboardSdk
from .keyboard_base import KeyboardBase
from .mouse_base import MouseBase
from .mouse_sdk import MouseSdk
from .factory import EventHandlerFactory


class SdkHandlerFactory(EventHandlerFactory):
    def __init__(self, server, controller):
        super().__init__(server, controller)
    def create_mouse_handler(self) -> MouseBase:
        return MouseSdk(self.controller)

    def create_keyboard_handler(self) -> KeyboardBase:
        return KeyboardSdk(self.controller)
