#!/usr/bin/env python3
"""
Widget Configuration Module
Defines the data structures and types for widget settings.
"""

from enum import Enum, auto
from typing import TypedDict, Any, Literal

class ConfigType(Enum):
    """Defines the type of UI control for a setting."""
    SLIDER = auto()
    DROPDOWN = auto()
    TEXT = auto()
    NUMBER = auto()

class BaseConfigOption(TypedDict):
    """Base structure for a configuration option."""
    label: str
    type: ConfigType
    value: Any

class SliderConfigOption(BaseConfigOption):
    """Configuration for a slider."""
    type: Literal[ConfigType.SLIDER]
    min: float
    max: float
    step: float

class DropdownConfigOption(BaseConfigOption):
    """Configuration for a dropdown."""
    type: Literal[ConfigType.DROPDOWN]
    options: list[str]

class TextConfigOption(BaseConfigOption):
    """Configuration for a text input."""
    type: Literal[ConfigType.TEXT]

class NumberConfigOption(BaseConfigOption):
    """Configuration for a number input."""
    type: Literal[ConfigType.NUMBER]

# A union of all possible config option types
ConfigOption = SliderConfigOption | DropdownConfigOption | TextConfigOption | NumberConfigOption 