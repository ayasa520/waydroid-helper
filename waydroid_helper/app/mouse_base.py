from abc import ABC, abstractmethod


class MouseBase(ABC):
    @abstractmethod
    def click_processor(self, controller, n_press, x, y)->bool:
        pass

    @abstractmethod
    def scroll_processor(self, controller, dx=None, dy=None)->bool:
        pass

    @abstractmethod
    def motion_processor(self, controller, x, y)->bool:
        pass

    @abstractmethod
    def zoom_processor(self, controller, range)->bool:
        pass

    # @abstractmethod
    # def touch_processor(self, controller, keyval, keycode, state):
    #     pass
