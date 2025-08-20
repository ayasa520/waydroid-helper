# pyright: reportAny=false
# pyright: reportAttributeAccessIssue=false,reportUnknownArgumentType=false,reportUnknownMemberType=false

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import asyncio
import configparser
import copy
import enum
import os
from collections.abc import Awaitable
from functools import partial
from gettext import gettext as _
from typing import Any, Callable, Dict, Optional, List

from gi.repository import GLib, GObject

from waydroid_helper.util import (SubprocessError, SubprocessManager, Task,
                                  logger)

CONFIG_PATH = os.environ.get("WAYDROID_CONFIG", "/var/lib/waydroid/waydroid.cfg")

# Import new architecture components
from waydroid_helper.model_controller import ModelController
from waydroid_helper.models import SessionState, ModelState

# Compatibility aliases for existing code
WaydroidState = SessionState
PropsState = ModelState


def bool_to_str(b: bool, flag: int = 0):
    if flag == 0:
        if b:
            return "True"
        else:
            return "False"
    elif flag == 1:
        if b:
            return "true"
        else:
            return "false"
    elif flag == 2:
        if b:
            return "1"
        else:
            return "0"


def str_to_bool(s: str) -> bool:
    s = s.strip()
    if s == "true" or s == "1" or s == "True":
        return True
    else:
        return False


# 有一说一, 将来直接通过 app_process 跑一个 java 服务器比 subprocess 更好


class PersistPropsCompat(GObject.Object):
    """Compatibility wrapper for persist properties"""

    state = GObject.Property(type=object)

    def __init__(self, controller: ModelController):
        super().__init__()
        self._controller = controller
        self.set_property("state", PropsState.UNINITIALIZED)

        # Bind to model state - use GLib.idle_add to ensure proper initialization
        GLib.idle_add(self._setup_state_binding)

        # Set up property bindings for all persist properties
        self._setup_property_bindings()

    def _setup_state_binding(self):
        """Set up state binding after initialization"""
        self._controller.property_model.connect("notify::state", self._on_model_state_changed)
        # Sync initial state
        initial_state = self._controller.property_model.get_property("state")
        self.set_property("state", initial_state)
        return False  # Don't repeat

    def _on_model_state_changed(self, model: GObject.Object, param: GObject.ParamSpec):
        """Update compatibility state when model state changes"""
        model_state = model.get_property("state")
        self.set_property("state", model_state)

    def _setup_property_bindings(self):
        """Set up property bindings - simplified approach"""
        # Instead of dynamic GObject properties, we'll handle property access
        # through get_property/set_property overrides
        pass

    def get_property(self, property_name: str) -> Any:
        """Get property value from model"""
        if property_name == "state":
            return super().get_property(property_name)

        # Convert property name format (handle both dashes and underscores)
        model_prop_name = property_name.replace("-", "_")
        return self._controller.property_model.get_property_value(model_prop_name)

    def set_property(self, property_name: str, value: Any):
        """Set property value in model"""
        if property_name == "state":
            super().set_property(property_name, value)
            return

        # Convert property name format (handle both dashes and underscores)
        model_prop_name = property_name.replace("-", "_")
        self._controller.property_model.set_property_value(model_prop_name, value)

    async def fetch(self):
        """Fetch properties (compatibility method)"""
        # This is handled automatically by the controller
        pass

    async def reset(self):
        """Reset properties (compatibility method)"""
        await self._controller.reset_persist_properties()

    async def save(self, name: str):
        """Save a property (compatibility method)"""
        await self._controller.save_persist_property(name)

    async def refresh(self, name: str):
        """Refresh a property from Waydroid (compatibility method)"""
        return await self._controller.refresh_persist_property(name)


class PrivilegedPropsCompat(GObject.Object):
    """Compatibility wrapper for privileged properties"""

    state = GObject.Property(type=object)
    android_version = GObject.Property(type=str, default="")

    def __init__(self, controller: ModelController):
        super().__init__()
        self._controller = controller
        self.set_property("state", PropsState.UNINITIALIZED)

        # Bind to model states - use GLib.idle_add to ensure proper initialization
        GLib.idle_add(self._setup_state_binding)

        # Set up property bindings for all privileged properties
        self._setup_property_bindings()

    def _setup_state_binding(self):
        """Set up state binding after initialization"""
        # Privileged props bind to privileged_state, not the main state
        self._controller.property_model.connect("notify::privileged-state", self._on_privileged_state_changed)
        self._controller.session_model.connect("notify::android-version", self._on_android_version_changed)
        # Sync initial state
        initial_state = self._controller.property_model.get_property("privileged-state")
        self.set_property("state", initial_state)
        return False  # Don't repeat

    def _on_privileged_state_changed(self, model: GObject.Object, param: GObject.ParamSpec):
        """Update compatibility state when privileged state changes"""
        privileged_state = model.get_property("privileged-state")
        self.set_property("state", privileged_state)

    def _on_android_version_changed(self, model: GObject.Object, param: GObject.ParamSpec):
        """Update Android version when session model changes"""
        android_version = model.get_property("android_version")
        self.set_property("android_version", android_version)

    def _setup_property_bindings(self):
        """Set up property bindings - simplified approach"""
        # Instead of dynamic GObject properties, we'll handle property access
        # through get_property/set_property overrides
        pass

    def get_property(self, property_name: str) -> Any:
        """Get property value from model"""
        if property_name in ("state", "android_version"):
            return super().get_property(property_name)

        # Convert property name format (handle both dashes and underscores)
        model_prop_name = property_name.replace("-", "_")
        return self._controller.property_model.get_property_value(model_prop_name)

    def set_property(self, property_name: str, value: Any):
        """Set property value in model"""
        if property_name in ("state", "android_version"):
            super().set_property(property_name, value)
            return

        # Convert property name format (handle both dashes and underscores)
        model_prop_name = property_name.replace("-", "_")
        self._controller.property_model.set_property_value(model_prop_name, value)

    def set_device_info(self, data: Dict[str, Any]):
        """Set device info (compatibility method)"""
        self._controller._task.create_task(self._controller.set_device_info(data))

    async def fetch(self):
        """Fetch properties (compatibility method)"""
        # This is handled automatically by the controller
        pass

    async def reset(self):
        """Reset properties (compatibility method)"""
        await self._controller.reset_privileged_properties()

    async def save(self):
        """Save properties (compatibility method)"""
        await self._controller.save_all_privileged_properties()

    async def restore(self):
        """Restore properties (compatibility method)"""
        await self._controller.restore_privileged_properties()


class WaydroidPropsCompat(GObject.Object):
    """Compatibility wrapper for waydroid config properties"""

    state = GObject.Property(type=object)

    def __init__(self, controller: ModelController):
        super().__init__()
        self._controller = controller

        # Connect to model changes
        self._controller.property_model.connect("notify::waydroid-state", self._on_waydroid_state_changed)

        # Set initial state with a delay to ensure proper initialization
        GLib.idle_add(self._set_initial_state)

    def _set_initial_state(self):
        # Sync initial state
        initial_state = self._controller.property_model.get_property("waydroid-state")
        self.set_property("state", initial_state)
        return False  # Don't repeat

    def _on_waydroid_state_changed(self, model: GObject.Object, param: GObject.ParamSpec):
        """Update compatibility state when waydroid state changes"""
        waydroid_state = model.get_property("waydroid-state")
        self.set_property("state", waydroid_state)

    def set_property(self, property_name: str, value: Any):
        """Set property value in model"""
        if property_name == "state":
            super().set_property(property_name, value)
            return

        # Convert property name format (handle both dashes and underscores)
        model_prop_name = property_name.replace("-", "_")
        self._controller.property_model.set_property_value(model_prop_name, value)
    # Compatibility methods for accessing properties
    def get_property(self, property_name: str):
        if property_name in ("state"):
            return super().get_property(property_name)

        """Get a waydroid property value (compatibility method)"""
        normalized_name = property_name.replace("-", "_")
        return self._controller.property_model.get_property_value(normalized_name)

    def set_property_value(self, name: str, value):
        """Set a waydroid property value (compatibility method)"""
        normalized_name = name.replace("-", "_")
        return self._controller.property_model.set_property_value(normalized_name, value)


class WaydroidCompat(GObject.Object):
    """
    Compatibility wrapper for the old Waydroid class.

    This class provides the same interface as the original Waydroid class
    but uses the new clean architecture internally. This allows for
    incremental migration of the codebase.
    """
    state: WaydroidState = GObject.Property( # pyright: ignore[reportAssignmentType]
        type=object
    )

    def __init__(self) -> None:
        super().__init__()

        # Initialize the new architecture
        self._controller = ModelController()

        # Set up property bindings for compatibility
        self._setup_compatibility_bindings()

        # Initialize state
        self.set_property("state", WaydroidState.LOADING)

    def _setup_compatibility_bindings(self):
        """Set up bindings between new models and old interface"""
        # Bind session state
        self._controller.session_model.connect(
            "notify::state", self._on_session_state_changed
        )

        # Set up property change listeners
        self._controller.property_model.add_change_listener(self._on_property_changed)

    def _on_session_state_changed(self, model: GObject.Object, param: GObject.ParamSpec):
        """Handle session state changes from the new model"""
        new_state = model.get_property("state")
        self.set_property("state", new_state)

    def _on_property_changed(self, property_name: str, value: Any):
        """Handle property changes from the new model"""
        # This can be used to emit compatibility signals if needed
        pass

    # Compatibility properties
    @property
    def persist_props(self):
        """Compatibility property for persist props"""
        if not hasattr(self, '_persist_props_compat'):
            self._persist_props_compat = PersistPropsCompat(self._controller)
        return self._persist_props_compat

    @property
    def privileged_props(self):
        """Compatibility property for privileged props"""
        if not hasattr(self, '_privileged_props_compat'):
            self._privileged_props_compat = PrivilegedPropsCompat(self._controller)
        return self._privileged_props_compat

    @property
    def waydroid_props(self):
        """Compatibility property for waydroid config props"""
        if not hasattr(self, '_waydroid_props_compat'):
            self._waydroid_props_compat = WaydroidPropsCompat(self._controller)
        return self._waydroid_props_compat

    # Session management methods (delegate to controller)
    async def start_session(self):
        """Start Waydroid session"""
        return await self._controller.start_session()

    async def stop_session(self):
        """Stop Waydroid session"""
        return await self._controller.stop_session()

    async def restart_session(self):
        """Restart Waydroid session"""
        return await self._controller.restart_session()

    async def show_full_ui(self):
        """Show Waydroid full UI"""
        return await self._controller.show_full_ui()

    async def upgrade(self, offline: bool = False) -> bool:
        """Upgrade Waydroid"""
        return await self._controller.upgrade(offline)

    # Property management methods (delegate to controller)
    async def reset_persist_props(self):
        """Reset persist properties"""
        return await self._controller.reset_persist_properties()

    async def reset_privileged_props(self):
        """Reset privileged properties"""
        return await self._controller.reset_privileged_properties()

    async def save_persist_prop(self, name: str):
        """Save a persist property"""
        return await self._controller.save_persist_property(name)

    async def refresh_persist_prop(self, name: str):
        """Refresh a persist property from Waydroid"""
        return await self._controller.refresh_persist_property(name)

    async def save_privileged_props(self):
        """Save privileged properties"""
        return await self._controller.save_all_privileged_properties()

    async def restore_privileged_props(self):
        """Restore privileged properties"""
        return await self._controller.restore_privileged_properties()

    async def save_waydroid_props(self):
        """Save waydroid config properties"""
        return await self._controller.save_all_waydroid_properties()

    async def reset_waydroid_props(self):
        """Reset waydroid config properties"""
        return await self._controller.reset_waydroid_properties()

    async def set_extension_props(self, pairs: Dict[str, Any]):
        """Set extension properties"""
        return await self._controller.set_extension_properties(pairs)

    async def remove_extension_props(self, keys: List[str]):
        """Remove extension properties"""
        return await self._controller.remove_extension_properties(keys)

    def get_android_version(self):
        """Get Android version"""
        return self._controller.session_model.get_property("android_version")

    # State management methods
    def reset_persist_props_state(self):
        """Reset persist props state (compatibility)"""
        # This is handled automatically by the new architecture
        pass

    def reset_privileged_props_state(self):
        """Reset privileged props state (compatibility)"""
        # This is handled automatically by the new architecture
        pass

    def reset_waydroid_props_state(self):
        """Reset waydroid props state (compatibility)"""
        # This is handled automatically by the new architecture
        pass


# Create alias for backward compatibility
Waydroid = WaydroidCompat