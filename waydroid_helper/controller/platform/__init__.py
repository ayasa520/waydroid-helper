"""
平台相关功能模块
提供不同平台的特定功能支持
"""

import os
from waydroid_helper.util.log import logger
from .base import PlatformBase


def get_platform(widget):
    """获取当前平台的实现"""
    if os.environ.get("WAYLAND_DISPLAY"):
        try:
            from .wayland import WaylandPlatform

            return WaylandPlatform(widget)
        except ImportError as e:
            logger.error(f"Failed to load Wayland platform support: {e}")

    # 可以在这里添加其他平台支持
    # elif os.environ.get('DISPLAY'):
    #     from .x11 import X11Platform
    #     return X11Platform(widget)

    logger.warning("No suitable platform implementation found")
    return None


__all__ = ["PlatformBase", "get_platform"]
