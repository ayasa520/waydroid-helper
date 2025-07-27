#
# Copyright (C) 2010 The A Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from enum import IntEnum


class AKeyState(IntEnum):
    UNKNOWN = -1
    UP = 0
    DOWN = 1
    VIRTUAL = 2


class AMetaState(IntEnum):
    NONE = 0
    ALT_ON = 0x02
    ALT_LEFT_ON = 0x10
    ALT_RIGHT_ON = 0x20
    SHIFT_ON = 0x01
    SHIFT_LEFT_ON = 0x40
    SHIFT_RIGHT_ON = 0x80
    SYM_ON = 0x04
    FUNCTION_ON = 0x08
    CTRL_ON = 0x1000
    CTRL_LEFT_ON = 0x2000
    CTRL_RIGHT_ON = 0x4000
    META_ON = 0x10000
    META_LEFT_ON = 0x20000
    META_RIGHT_ON = 0x40000
    CAPS_LOCK_ON = 0x100000
    NUM_LOCK_ON = 0x200000
    SCROLL_LOCK_ON = 0x400000


class AInputEventType(IntEnum):
    KEY = 1
    MOTION = 2
    FOCUS = 3
    CAPTURE = 4
    DRAG = 5
    TOUCH_MODE = 6


class AKeyEventAction(IntEnum):
    DOWN = 0
    UP = 1
    MULTIPLE = 2


class AKeyEventFlags(IntEnum):
    WOKE_HERE = 0x1
    SOFT_KEYBOARD = 0x2
    KEEP_TOUCH_MODE = 0x4
    FROM_SYSTEM = 0x8
    EDITOR_ACTION = 0x10
    CANCELED = 0x20
    VIRTUAL_HARD_KEY = 0x40
    LONG_PRESS = 0x80
    CANCELED_LONG_PRESS = 0x100
    TRACKING = 0x200
    FALLBACK = 0x400


# define AMOTION_EVENT_ACTION_POINTER_INDEX_SHIFT 8
class AMotionEventAction(IntEnum):
    MASK = 0xFF
    POINTER_INDEX_MASK = 0xFF00
    DOWN = 0
    UP = 1
    MOVE = 2
    CANCEL = 3
    OUTSIDE = 4
    POINTER_DOWN = 5
    POINTER_UP = 6
    HOVER_MOVE = 7
    SCROLL = 8
    HOVER_ENTER = 9
    HOVER_EXIT = 10
    BUTTON_PRESS = 11
    BUTTON_RELEASE = 12


class AMotionEventFlags(IntEnum):
    WINDOW_IS_OBSCURED = 0x1


class AMotionEventEdgeTouchFlags(IntEnum):
    NONE = 0
    TOP = 0x01
    BOTTOM = 0x02
    LEFT = 0x04
    RIGHT = 0x08


class AMotionEventAxis(IntEnum):
    X = 0
    Y = 1
    PRESSURE = 2
    SIZE = 3
    TOUCH_MAJOR = 4
    TOUCH_MINOR = 5
    TOOL_MAJOR = 6
    TOOL_MINOR = 7
    ORIENTATION = 8
    VSCROLL = 9
    HSCROLL = 10
    Z = 11
    RX = 12
    RY = 13
    RZ = 14
    HAT_X = 15
    HAT_Y = 16
    LTRIGGER = 17
    RTRIGGER = 18
    THROTTLE = 19
    RUDDER = 20
    WHEEL = 21
    GAS = 22
    BRAKE = 23
    DISTANCE = 24
    TILT = 25
    SCROLL = 26
    RELATIVE_X = 27
    RELATIVE_Y = 28
    GENERIC_1 = 32
    GENERIC_2 = 33
    GENERIC_3 = 34
    GENERIC_4 = 35
    GENERIC_5 = 36
    GENERIC_6 = 37
    GENERIC_7 = 38
    GENERIC_8 = 39
    GENERIC_9 = 40
    GENERIC_10 = 41
    GENERIC_11 = 42
    GENERIC_12 = 43
    GENERIC_13 = 44
    GENERIC_14 = 45
    GENERIC_15 = 46
    GENERIC_16 = 47
    GESTURE_X_OFFSET = 48
    GESTURE_Y_OFFSET = 49
    GESTURE_SCROLL_X_DISTANCE = 50
    GESTURE_SCROLL_Y_DISTANCE = 51
    GESTURE_PINCH_SCALE_FACTOR = 52
    GESTURE_SWIPE_FINGER_COUNT = 53
    AMOTION_EVENT_MAXIMUM_VALID_AXIS_VALUE = GESTURE_SWIPE_FINGER_COUNT


class AMotionEventButtons(IntEnum):
    PRIMARY = 1 << 0
    SECONDARY = 1 << 1
    TERTIARY = 1 << 2
    BACK = 1 << 3
    FORWARD = 1 << 4
    STYLUS_PRIMARY = 1 << 5
    STYLUS_SECONDARY = 1 << 6


class AMotionEventToolType(IntEnum):
    UNKNOWN = 0
    FINGER = 1
    STYLUS = 2
    MOUSE = 3
    ERASER = 4
    PALM = 5


class AMotionClassification(IntEnum):
    NONE = 0
    AMBIGUOUS_GESTURE = 1
    DEEP_PRESS = 2
    TWO_FINGER_SWIPE = 3
    MULTI_FINGER_SWIPE = 4
    PINCH = 5


class AInputSourceClass(IntEnum):
    MASK = 0x000000FF
    NONE = 0x00000000
    BUTTON = 0x00000001
    POINTER = 0x00000002
    NAVIGATION = 0x00000004
    POSITION = 0x00000008
    JOYSTICK = 0x00000010


class AInputSource(IntEnum):
    UNKNOWN = 0x00000000
    KEYBOARD = 0x00000100 | AInputSourceClass.BUTTON
    DPAD = 0x00000200 | AInputSourceClass.BUTTON
    GAMEPAD = 0x00000400 | AInputSourceClass.BUTTON
    TOUCHSCREEN = 0x00001000 | AInputSourceClass.POINTER
    MOUSE = 0x00002000 | AInputSourceClass.POINTER
    STYLUS = 0x00004000 | AInputSourceClass.POINTER
    BLUETOOTH_STYLUS = 0x00008000 | STYLUS
    TRACKBALL = 0x00010000 | AInputSourceClass.NAVIGATION
    MOUSE_RELATIVE = 0x00020000 | AInputSourceClass.NAVIGATION
    TOUCHPAD = 0x00100000 | AInputSourceClass.POSITION
    TOUCH_NAVIGATION = 0x00200000 | AInputSourceClass.NONE
    JOYSTICK = 0x01000000 | AInputSourceClass.JOYSTICK
    HDMI = 0x02000000 | AInputSourceClass.BUTTON
    SENSOR = 0x04000000 | AInputSourceClass.NONE
    ROTARY_ENCODER = 0x00400000 | AInputSourceClass.NONE
    ANY = 0xFFFFFF00


class AKeyboardType(IntEnum):
    NONE = 0
    NON_ALPHABETIC = 1
    ALPHABETIC = 2


class AInputMotionRange(IntEnum):
    X = AMotionEventAxis.X
    Y = AMotionEventAxis.Y
    PRESSURE = AMotionEventAxis.PRESSURE
    SIZE = AMotionEventAxis.SIZE
    TOUCH_MAJOR = AMotionEventAxis.TOUCH_MAJOR
    TOUCH_MINOR = AMotionEventAxis.TOUCH_MINOR
    TOOL_MAJOR = AMotionEventAxis.TOOL_MAJOR
    TOOL_MINOR = AMotionEventAxis.TOOL_MINOR
    ORIENTATION = AMotionEventAxis.ORIENTATION
