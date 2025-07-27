"""
装饰器模块
提供各种组件装饰器，用于为组件添加额外功能
"""

from .base_decorator import WidgetDecorator, widget_decorator
from .editable import Editable, EditableDecorator
from .resizable import Resizable, ResizableDecorator

__all__ = [
    'WidgetDecorator',
    'widget_decorator', 
    'ResizableDecorator',
    'Resizable',
    'EditableDecorator',
    'Editable'
] 