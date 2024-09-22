import gi

from .MappingButtonState import MappingButtonState

gi.require_version("Gtk", "4.0")

from enum import Enum
from abc import ABC, abstractmethod
from gi.repository import Gtk
from typing import Protocol, TypeVar, runtime_checkable
from gi.repository import Gtk


@runtime_checkable
class DrawingAreaProtocol(Protocol):
    action_height: int

    def set_action_width(self, width: int) -> None: ...
    def set_action_height(self, height: int) -> None: ...
    def set_content_width(self, width: int) -> None: ...
    def set_content_height(self, height: int) -> None: ...
    def set_size_request(self, width: int, height: int) -> None: ...
    def move_action(x: float, t: float) -> None: ...
    def move(x: float, t: float) -> None: ...


class ResizeEdge(Enum):
    NONE = 0
    NORTH = 1
    SOUTH = 2
    EAST = 3
    WEST = 4


T = TypeVar("T", bound=DrawingAreaProtocol)


class Resizable(ABC):
    def set_action_height(self: T, height: int) -> None:
        """
        不只是映射键可编辑的按钮会用, 切换预览和编辑状态也会用
        """
        if self.state == MappingButtonState.SELECTED:
            self.action_height = height
        self.set_content_height(height)

    def set_action_width(self: T, width: int) -> None:
        """
        不只是映射键可编辑的按钮会用, 切换预览和编辑状态也会用
        """
        if self.state == MappingButtonState.SELECTED:
            self.action_width = width
        self.set_content_width(width)

    @abstractmethod
    def resize(
        self: T,
        resize_edge,
        offset_x,
        offset_y,
        original_x,
        original_y,
        original_w,
        original_h,
    ):
        raise NotImplementedError("Subclasses should implement this method.")


class DefaultResizableWidget(Resizable):
    def resize(
        self: T,
        resize_edge: ResizeEdge,
        offset_x,
        offset_y,
        original_x,
        original_y,
        original_w,
        original_h,
    ):
        if resize_edge == ResizeEdge.EAST:
            self.set_action_width(original_w + offset_x)
        elif resize_edge == ResizeEdge.SOUTH:
            self.set_action_height(original_h + offset_y)
        elif resize_edge == ResizeEdge.NORTH:
            self.set_action_height(original_h - offset_y)
            self.move_action(original_x, original_y + offset_y)
        elif resize_edge == ResizeEdge.WEST:
            self.set_action_width(original_w - offset_x)
            self.move_action(original_x + offset_x, original_y)


class CenterResizableWidget(Resizable):
    def resize(
        self: T,
        resize_edge,
        offset_x,
        offset_y,
        original_x,
        original_y,
        original_w,
        original_h,
    ):
        if resize_edge == ResizeEdge.EAST:
            self.set_action_width(original_w + offset_x * 2)
            # self.set_size_request(original_w + offset_x * 2, original_h)
            self.move(original_x - offset_x, original_y)
        elif resize_edge == ResizeEdge.WEST:
            self.set_action_width(original_w - offset_x * 2)
            # self.set_size_request(original_w - offset_x * 2, original_h)
            self.move(original_x + offset_x, original_y)
        elif resize_edge == ResizeEdge.SOUTH:
            self.set_action_height(original_h + offset_y * 2)
            # self.set_size_request(original_w, original_h + offset_y * 2)
            self.move(original_x, original_y - offset_y)
        elif resize_edge == ResizeEdge.NORTH:
            self.set_action_height(original_h - offset_y * 2)
            # self.set_size_request(original_w, original_h - offset_y * 2)
            self.move(original_x, original_y + offset_y)


class SquareResizableWidget(Resizable):
    def resize(
        self: T,
        resize_edge,
        offset_x,
        offset_y,
        original_x,
        original_y,
        original_w,
        original_h,
    ):
        if resize_edge == ResizeEdge.EAST:
            # self.set_content_width(original_w + offset_x)
            # self.set_content_height(original_h + offset_x)
            self.set_size_request(original_w + offset_x, original_h + offset_x)
        elif resize_edge == ResizeEdge.SOUTH:
            # self.set_content_width(original_w + offset_y)
            # self.set_content_height(original_h + offset_y)
            self.set_size_request(original_w + offset_y, original_h + offset_y)
        elif resize_edge == ResizeEdge.NORTH:
            # self.set_content_height(original_h - offset_y)
            # self.set_content_width(original_w - offset_y)
            self.set_size_request(original_h - offset_y, original_w - offset_y)
            self.move_action(original_x + offset_y, original_y + offset_y)
        elif resize_edge == ResizeEdge.WEST:
            # self.set_content_height(original_h - offset_x)
            # self.set_content_width(original_w - offset_x)
            self.set_size_request(original_h - offset_x, original_w - offset_y)
            self.move_action(original_x + offset_x, original_y + offset_x)


class SquareAndCenterResizableWidget(Resizable):
    def resize(
        self: T,
        resize_edge,
        offset_x,
        offset_y,
        original_x,
        original_y,
        original_w,
        original_h,
    ):
        if resize_edge == ResizeEdge.EAST:
            self.set_action_width(original_w + offset_x * 2)
            self.set_action_height(original_h + offset_x * 2)
            # self.set_size_request(original_w + offset_x * 2, original_h + offset_x * 2)
            self.move(original_x - offset_x, original_y - offset_x)
        elif resize_edge == ResizeEdge.WEST:
            self.set_action_width(original_w - offset_x * 2)
            self.set_action_height(original_h - offset_x * 2)
            # self.set_size_request(original_w - offset_x * 2, original_h - offset_x * 2)
            self.move(original_x + offset_x, original_y + offset_x)
        elif resize_edge == ResizeEdge.SOUTH:
            self.set_action_height(original_h + offset_y * 2)
            self.set_action_width(original_w + offset_y * 2)
            # self.set_size_request(original_h + offset_y * 2, original_w + offset_y * 2)
            self.move(original_x - offset_y, original_y - offset_y)
        elif resize_edge == ResizeEdge.NORTH:
            self.set_action_height(original_h - offset_y * 2)
            self.set_action_width(original_w - offset_y * 2)
            # self.set_size_request(original_h - offset_y * 2, original_w - offset_y * 2)
            self.move(original_x + offset_y, original_y + offset_y)
