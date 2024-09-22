# https://github.com/Genymobile/scrcpy/blob/master/app/src/control_msg.h

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum


import logging
import struct
from typing import Tuple

from .input import (
    AKeyEventAction,
    AMetaState,
    AMontionEventAction,
    AMontionEventButtons,
)

from .keycodes import AKeyCode

logger = logging.getLogger(__name__)


class ControlMsgType(IntEnum):
    INJECT_KEYCODE = 0
    INJECT_TEXT = 1
    INJECT_TOUCH_EVENT = 2
    INJECT_SCROLL_EVENT = 3
    BACK_OR_SCREEN_ON = 4
    EXPAND_NOTIFICATION_PANEL = 5
    EXPAND_SETTINGS_PANEL = 6
    COLLAPSE_PANELS = 7
    GET_CLIPBOARD = 8
    SET_CLIPBOARD = 9
    SET_SCREEN_POWER_MODE = 10
    ROTATE_DEVICE = 11
    UHID_CREATE = 12
    UHID_INPUT = 13
    OPEN_HARD_KEYBOARD_SETTINGS = 14


class ControlMsg(ABC):
    @property
    @abstractmethod
    def msg_type(self) -> ControlMsgType:
        raise NotImplementedError

    @abstractmethod
    def pack(self):
        raise NotImplementedError


@dataclass
class InjectKeycodeMsg(ControlMsg):
    action: AKeyEventAction
    keycode: AKeyCode
    repeat: int
    metastate: AMetaState

    @property
    def msg_type(self) -> ControlMsgType:
        return ControlMsgType.INJECT_KEYCODE

    def pack(self):
        packed_data = None
        try:
            packed_data = struct.pack(
                ">BBIII",
                self.msg_type,
                # AndroidKeyEventAction
                self.action,
                # AndroidKeyCode
                self.keycode,
                self.repeat,
                # AndroidMetaState
                self.metastate,
            )
        except Exception as e:
            logger.error(e)
        return packed_data


@dataclass
class InjectTextMsg(ControlMsg):
    text: str

    @property
    def msg_type(self) -> ControlMsgType:
        return ControlMsgType.INJECT_TEXT

    def pack(self):
        packed_data = None
        try:
            text = self.text.encode()
            packed_data = struct.pack(">BI", self.msg_type, len(text))
            packed_data += text
        except Exception as e:
            logger.error(e)

        return packed_data


@dataclass
class InjectTouchEventMsg(ControlMsg):
    action: AMontionEventAction
    action_button: AMontionEventButtons
    buttons: AMontionEventButtons
    pointer_id: int
    position: Tuple[int, int, int, int]
    pressure: float

    def pack(self):
        packed_data = None
        try:
            packed_data = struct.pack(
                ">BBqIIHHfII",
                self.msg_type,
                self.action,
                self.pointer_id,
                *self.position,
                self.pressure,
                self.action_button,
                self.buttons
            )
        except Exception as e:
            logger.error(e)
        return packed_data

    @property
    def msg_type(self) -> ControlMsgType:
        return ControlMsgType.INJECT_TOUCH_EVENT


@dataclass
class InjectScrollEventMsg(ControlMsg):
    position: Tuple[int, int, int, int]
    hscroll: float
    vscroll: float
    buttons: AMontionEventButtons

    def pack(self):
        packed_data = None
        try:
            packed_data = struct.pack(
                ">BIIHHffI",
                self.msg_type,
                *self.position,
                self.hscroll,
                self.vscroll,
                self.buttons
            )
        except Exception as e:
            logging.error(e)

        return packed_data

    @property
    def msg_type(self) -> ControlMsgType:
        return ControlMsgType.INJECT_SCROLL_EVENT
