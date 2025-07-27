#!/usr/bin/env python3
"""
类型定义
"""

from enum import Enum
from typing import Any, Callable

# 位置类型
Position = tuple[int, int]
Size = tuple[int, int]
Color = tuple[float, float, float, float]


# 调整大小方向
class ResizeDirection(Enum):
    """调整大小方向枚举"""

    NORTH = "n"
    SOUTH = "s"
    EAST = "e"
    WEST = "w"
    NORTHEAST = "ne"
    NORTHWEST = "nw"
    SOUTHEAST = "se"
    SOUTHWEST = "sw"


# 缩放策略
class ResizeStrategy(Enum):
    """缩放策略枚举"""

    NORMAL = 0
    CENTER = 1
    SYMMETRIC = 2


# 菜单项配置类型
MenuItemConfig = dict[str, Any]
MenuCallback = Callable[[], None]
