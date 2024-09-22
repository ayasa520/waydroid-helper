from abc import ABC, abstractmethod


class KeyboardBase(ABC):
    @abstractmethod
    def key_processor(self, controller, keyval, keycode, state)->bool:
        pass
