from app.mouse_base import MouseBase
from app.keyboard_base import KeyboardBase
from app.keyboard_mouse_gaming import KeyboardMouseGaming
from app.factory import EventHandlerFactory
from app.widgets.mapping_button import MappingButton


class GamingHandlerFactory(EventHandlerFactory):
    def __init__(self, server, controller,  mapping_buttons: list[MappingButton]):
        super().__init__(server, controller)
        self.mapping_buttons = mapping_buttons
        self.handler = KeyboardMouseGaming(self.controller, self.mapping_buttons)

    def create_mouse_handler(self) -> MouseBase:
        return self.handler

    def create_keyboard_handler(self) -> KeyboardBase:
        return self.handler
