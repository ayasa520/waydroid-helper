#!/usr/bin/env python3
"""
项目常量定义
"""

# 应用程序信息
APP_ID = "com.example.advanced-transparent-widgets"
APP_TITLE = "透明窗口 - 可拖动调整大小组件"

# 组件默认尺寸
DEFAULT_WIDGET_WIDTH = 150
DEFAULT_WIDGET_HEIGHT = 100
MIN_WIDGET_WIDTH = 50
MIN_WIDGET_HEIGHT = 30

# 调整大小相关
RESIZE_BORDER_WIDTH = 8

# 组件类型
WIDGET_TYPES = {
    "TEXT": "text_widget",
    "BUTTON": "button_widget",
    "CHART": "chart_widget",
    "CLOCK": "clock_widget",
}

# 缩放策略
RESIZE_STRATEGIES = {"NORMAL": 0, "CENTER": 1, "SYMMETRIC": 2}
