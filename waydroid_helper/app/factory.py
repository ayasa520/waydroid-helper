from abc import ABC, abstractmethod

from .controller import Controller
from .server import Server
from .mouse_base import MouseBase
from .keyboard_base import KeyboardBase


class EventHandlerFactory(ABC):
    def __init__(self, server: Server, controller: Controller):
        self.server = server
        self.controller = controller

    @abstractmethod
    def create_keyboard_handler(self) -> KeyboardBase:
        pass

    @abstractmethod
    def create_mouse_handler(self) -> MouseBase:
        pass
