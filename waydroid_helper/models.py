# pyright: reportAny=false
# pyright: reportAttributeAccessIssue=false,reportUnknownArgumentType=false,reportUnknownMemberType=false

"""
Clean Model Layer for Waydroid Helper

This module implements a clean separation between data models and business logic,
eliminating the complex signal management issues in the original implementation.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import asyncio
import enum
from typing import Any, Callable, Dict, Optional, Set
from dataclasses import dataclass, field
from functools import partial
from gettext import gettext as _

from gi.repository import GObject

from waydroid_helper.util import logger


class ModelState(enum.IntEnum):
    """State of a model component"""
    UNINITIALIZED = 1
    LOADING = 2
    READY = 3
    ERROR = 4


class SessionState(enum.IntEnum):
    """Waydroid session state"""
    LOADING = 0x01
    UNINITIALIZED = 0x02
    STOPPED = 0x04
    RUNNING = 0x08
    CONNECTED = 0x10


@dataclass
class PropertyDefinition:
    """Definition of a Waydroid property"""
    name: str
    nick: str  # The actual waydroid property name (e.g., persist.waydroid.multi_windows)
    property_type: type
    default_value: Any
    description: str = ""
    transform_in: Callable[[str], Any] = lambda x: x
    transform_out: Callable[[Any], str] = lambda x: str(x)
    is_privileged: bool = False  # True for properties that require root/config file changes


class PropertyModel(GObject.Object):
    """
    Clean property model that holds property state without circular dependencies.
    
    This model:
    - Holds the current state of all properties
    - Emits signals when properties change
    - Validates property changes
    - Has no knowledge of UI or SDK layers
    """
    
    state = GObject.Property(type=object)  # For persist props
    privileged_state = GObject.Property(type=object)  # For privileged props

    def __init__(self):
        super().__init__()
        self._properties: Dict[str, Any] = {}
        self._property_definitions: Dict[str, PropertyDefinition] = {}
        self._change_listeners: Set[Callable[[str, Any], None]] = set()
        self.set_property("state", ModelState.UNINITIALIZED)
        self.set_property("privileged-state", ModelState.UNINITIALIZED)
        self._setup_property_definitions()
    
    def _setup_property_definitions(self):
        """Setup all property definitions"""
        # Persist properties (can be changed via waydroid prop commands)
        persist_props = [
            PropertyDefinition(
                name="multi_windows",
                nick="persist.waydroid.multi_windows",
                property_type=bool,
                default_value=False,
                description=_("Enable window integration with the desktop"),
                transform_in=self._str_to_bool,
                transform_out=partial(self._bool_to_str, flag=1),
                is_privileged=False
            ),
            PropertyDefinition(
                name="cursor_on_subsurface",
                nick="persist.waydroid.cursor_on_subsurface",
                property_type=bool,
                default_value=False,
                description=_("Workaround for showing the cursor in multi_windows mode on some compositors"),
                transform_in=self._str_to_bool,
                transform_out=partial(self._bool_to_str, flag=1),
                is_privileged=False
            ),
            PropertyDefinition(
                name="invert_colors",
                nick="persist.waydroid.invert_colors",
                property_type=bool,
                default_value=False,
                description=_("Swaps the color space from RGBA to BGRA"),
                transform_in=self._str_to_bool,
                transform_out=partial(self._bool_to_str, flag=1),
                is_privileged=False
            ),
            PropertyDefinition(
                name="suspend",
                nick="persist.waydroid.suspend",
                property_type=bool,
                default_value=False,
                description=_("Let the Waydroid container sleep when no apps are active"),
                transform_in=self._str_to_bool,
                transform_out=partial(self._bool_to_str, flag=1),
                is_privileged=False
            ),
            PropertyDefinition(
                name="uevent",
                nick="persist.waydroid.uevent",
                property_type=bool,
                default_value=False,
                description=_("Allow android direct access to hotplugged devices"),
                transform_in=self._str_to_bool,
                transform_out=partial(self._bool_to_str, flag=1),
                is_privileged=False
            ),
            PropertyDefinition(
                name="fake_touch",
                nick="persist.waydroid.fake_touch",
                property_type=str,
                default_value="",
                description=_("Interpret mouse inputs as touch inputs"),
                is_privileged=False
            ),
            PropertyDefinition(
                name="fake_wifi",
                nick="persist.waydroid.fake_wifi",
                property_type=str,
                default_value="",
                description=_("Make the Apps appear as if connected to WiFi"),
                is_privileged=False
            ),
            PropertyDefinition(
                name="height_padding",
                nick="persist.waydroid.height_padding",
                property_type=str,
                default_value="",
                description=_("Adjust height padding"),
                is_privileged=False
            ),
            PropertyDefinition(
                name="width_padding",
                nick="persist.waydroid.width_padding",
                property_type=str,
                default_value="",
                description=_("Adjust width padding"),
                is_privileged=False
            ),
            PropertyDefinition(
                name="height",
                nick="persist.waydroid.height",
                property_type=str,
                default_value="",
                description=_("Used for user to override desired resolution"),
                is_privileged=False
            ),
            PropertyDefinition(
                name="width",
                nick="persist.waydroid.width",
                property_type=str,
                default_value="",
                description=_("Used for user to override desired resolution"),
                is_privileged=False
            ),
            # 其实不是 persist, 但是先放这里
            PropertyDefinition(
                name="boot_completed",
                nick="sys.boot_completed",
                property_type=bool,
                default_value=False,
                description=_("Enable window integration with the desktop"),
                transform_in=self._str_to_bool,
                transform_out=partial(self._bool_to_str, flag=2),
                is_privileged=False
            ),
        ]
        
        # Privileged properties (require root access to modify config files)
        privileged_props = [
            PropertyDefinition(
                name="qemu_hw_mainkeys",
                nick="qemu.hw.mainkeys",
                property_type=bool,
                default_value=False,
                description=_("Hide navbar"),
                transform_in=self._str_to_bool,
                transform_out=lambda x: "1" if x else "0",
                is_privileged=True
            ),
            # Device info properties
            PropertyDefinition(
                name="ro_product_brand",
                nick="ro.product.brand",
                property_type=str,
                default_value="",
                is_privileged=True
            ),
            PropertyDefinition(
                name="ro_product_manufacturer",
                nick="ro.product.manufacturer",
                property_type=str,
                default_value="",
                is_privileged=True
            ),
            PropertyDefinition(
                name="ro_product_model",
                nick="ro.product.model",
                property_type=str,
                default_value="",
                is_privileged=True
            ),
            PropertyDefinition(
                name="ro_product_device",
                nick="ro.product.device",
                property_type=str,
                default_value="",
                is_privileged=True
            ),
        ]
        
        # Register all properties
        for prop_def in persist_props + privileged_props:
            self._property_definitions[prop_def.name] = prop_def
            self._properties[prop_def.name] = prop_def.default_value
    
    @staticmethod
    def _str_to_bool(s: str) -> bool:
        """Convert string to boolean"""
        s = s.strip().lower()
        return s in ("true", "1", "yes", "on")
    
    @staticmethod
    def _bool_to_str(b: bool, flag: int = 0) -> str:
        """Convert boolean to string with different formats"""
        if flag == 0:
            return "True" if b else "False"
        elif flag == 1:
            return "true" if b else "false"
        elif flag == 2:
            return "1" if b else "0"
        return str(b)
    
    def get_property_definition(self, name: str) -> Optional[PropertyDefinition]:
        """Get property definition by name"""
        return self._property_definitions.get(name)
    
    def get_property_value(self, name: str) -> Any:
        """Get current property value"""
        return self._properties.get(name)
    
    def set_property_value(self, name: str, value: Any) -> bool:
        """
        Set property value and emit change signal.
        Returns True if value was changed, False if it was the same.
        """
        if name not in self._property_definitions:
            logger.warning(f"Unknown property: {name}")
            return False
        
        prop_def = self._property_definitions[name]
        
        # Type validation
        if not isinstance(value, prop_def.property_type):
            try:
                value = prop_def.property_type(value)
            except (ValueError, TypeError):
                logger.error(f"Invalid value type for property {name}: {value}")
                return False
        
        old_value = self._properties.get(name)
        if old_value == value:
            return False
        
        self._properties[name] = value
        self._emit_property_changed(name, value)
        return True
    
    def _emit_property_changed(self, name: str, value: Any):
        """Emit property changed signal to all listeners"""
        for listener in self._change_listeners:
            try:
                listener(name, value)
            except Exception as e:
                logger.error(f"Error in property change listener: {e}")
    
    def add_change_listener(self, listener: Callable[[str, Any], None]):
        """Add a listener for property changes"""
        self._change_listeners.add(listener)
    
    def remove_change_listener(self, listener: Callable[[str, Any], None]):
        """Remove a property change listener"""
        self._change_listeners.discard(listener)
    
    def get_persist_properties(self) -> Dict[str, PropertyDefinition]:
        """Get all persist properties (non-privileged)"""
        return {name: prop_def for name, prop_def in self._property_definitions.items() 
                if not prop_def.is_privileged}
    
    def get_privileged_properties(self) -> Dict[str, PropertyDefinition]:
        """Get all privileged properties"""
        return {name: prop_def for name, prop_def in self._property_definitions.items() 
                if prop_def.is_privileged}
    
    def reset_to_defaults(self, privileged_only: bool = False):
        """Reset properties to their default values"""
        for name, prop_def in self._property_definitions.items():
            if privileged_only and not prop_def.is_privileged:
                continue
            self.set_property_value(name, prop_def.default_value)


class SessionModel(GObject.Object):
    """
    Model for Waydroid session state.
    
    This model:
    - Tracks session state (running, stopped, etc.)
    - Emits signals when session state changes
    - Has no knowledge of UI or SDK layers
    """
    
    state = GObject.Property(type=object)
    android_version = GObject.Property(type=str, default="")
    
    def __init__(self):
        super().__init__()
        self._change_listeners: Set[Callable[[SessionState], None]] = set()
        self.set_property("state", SessionState.LOADING)
    
    def set_session_state(self, new_state: SessionState):
        """Set session state and emit change signal if different"""
        old_state = self.get_property("state")
        if old_state != new_state:
            self.set_property("state", new_state)
            self._emit_state_changed(new_state)
    
    def _emit_state_changed(self, new_state: SessionState):
        """Emit state changed signal to all listeners"""
        for listener in self._change_listeners:
            try:
                listener(new_state)
            except Exception as e:
                logger.error(f"Error in session state change listener: {e}")
    
    def add_change_listener(self, listener: Callable[[SessionState], None]):
        """Add a listener for session state changes"""
        self._change_listeners.add(listener)
    
    def remove_change_listener(self, listener: Callable[[SessionState], None]):
        """Remove a session state change listener"""
        self._change_listeners.discard(listener)
