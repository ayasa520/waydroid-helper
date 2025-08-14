#!/usr/bin/env python3
"""
控制消息模块
"""
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum

from waydroid_helper.util.log import logger
from waydroid_helper.controller.android import (AKeyCode, AKeyEventAction,
                                                AMetaState, AMotionEventAction,
                                                AMotionEventButtons)


class ScreenInfo:
    _instance = None
    width: int = 0
    height: int = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def set_resolution(self, width: int, height: int):
        self.width = width
        self.height = height

    def get_resolution(self) -> tuple[int, int]:
        return self.width, self.height


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

def to_fixed_point_u16(f_val: float) -> int:
    """将一个浮点数转换为 Q16 格式的定点数 (作为16位无符号整数)"""
    # 假设浮点数在 0.0 到 1.0 之间
    if f_val < 0.0:
        f_val = 0.0
    if f_val > 1.0:
        f_val = 1.0
    # 乘以 2^16 - 1 (即 65535) 并取整
    return int(f_val * 0xFFFF)

def to_fixed_point_i16(f: float) -> int:
    assert -1.0 <= f <= 1.0, "Input out of range"
    i = int(f * (2 ** 15))  # 0x1p15 == 32768
    assert i >= -0x8000, "Underflow detected"
    if i >= 0x7fff:
        # Handle the edge case for f == 1.0
        assert i == 0x8000, "Overflow detected"
        i = 0x7fff
    return i 

@dataclass
class ControlMsg(ABC):
    @property
    @abstractmethod
    def msg_type(self) -> ControlMsgType:
        raise NotImplementedError

    @abstractmethod
    def pack(self) -> bytes | None:
        raise NotImplementedError


@dataclass
class InjectKeycodeMsg(ControlMsg):
    action: AKeyEventAction
    keycode: AKeyCode
    repeat: int
    metastate: AMetaState|int

    @property
    def msg_type(self) -> ControlMsgType:
        return ControlMsgType.INJECT_KEYCODE

    def pack(self) -> bytes | None:
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
    action: AMotionEventAction
    pointer_id: int
    position: tuple[int, int, int, int] # x, y, screen_width, screen_height
    pressure: float
    action_button: AMotionEventButtons | int
    buttons: AMotionEventButtons | int

    @property
    def msg_type(self) -> ControlMsgType:
        return ControlMsgType.INJECT_TOUCH_EVENT
        
    def pack(self):
        screen_info = ScreenInfo()
        device_w, device_h = screen_info.get_resolution()
        
        client_x, client_y, client_w, client_h = self.position

        if device_w == 0 or device_h == 0:
            logger.warning("Device resolution not set, using client resolution. Coordinates may be incorrect.")
            device_w, device_h = client_w, client_h
        
        # Scale coordinates
        scaled_x = int(client_x * device_w / client_w) if client_w != 0 else 0
        scaled_y = int(client_y * device_h / client_h) if client_h != 0 else 0
        
        # 修正:
        # 1. pointer_id 使用 'Q' (无符号64位)
        # 2. pressure 使用 to_fixed_point_u16 转换并使用 'H' (无符号16位)
        pressure_fixed = to_fixed_point_u16(self.pressure)
        return struct.pack(
            ">BBQIIHHHII", # 注意这里的 Q 和 H
            self.msg_type,
            self.action,
            self.pointer_id,
            scaled_x,
            scaled_y,
            device_w,
            device_h,
            pressure_fixed,
            self.action_button,
            self.buttons,
        )


@dataclass
class InjectScrollEventMsg(ControlMsg):
    position: tuple[int, int, int, int] # x, y, screen_width, screen_height
    hscroll: float
    vscroll: float
    buttons: AMotionEventButtons | int

    @property
    def msg_type(self) -> ControlMsgType:
        return ControlMsgType.INJECT_SCROLL_EVENT

    def pack(self):
        screen_info = ScreenInfo()
        device_w, device_h = screen_info.get_resolution()
        
        client_x, client_y, client_w, client_h = self.position

        if device_w == 0 or device_h == 0:
            logger.warning("Device resolution not set, using client resolution. Coordinates may be incorrect.")
            device_w, device_h = client_w, client_h

        # Scale coordinates
        scaled_x = int(client_x * device_w / client_w) if client_w != 0 else 0
        scaled_y = int(client_y * device_h / client_h) if client_h != 0 else 0
        
        hscroll_fixed = to_fixed_point_i16(max(-1.0, min(1.0, self.hscroll/16)))
        vscroll_fixed = to_fixed_point_i16(max(-1.0, min(1.0, self.vscroll/16)))
        return struct.pack(
            ">BIIHHhhI",
            self.msg_type,
            scaled_x,
            scaled_y,
            device_w,
            device_h,
            hscroll_fixed,
            vscroll_fixed,
            self.buttons,
        )