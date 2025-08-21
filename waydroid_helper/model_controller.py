# pyright: reportAny=false
# pyright: reportAttributeAccessIssue=false,reportUnknownArgumentType=false,reportUnknownMemberType=false

"""
Controller Layer for Waydroid Helper

This module implements the controller that coordinates between the model layer
and SDK layer, providing a clean interface for the view layer.
"""

import asyncio
from typing import Any, Dict, Optional

from gi.repository import GLib, GObject

from waydroid_helper.util import Task, logger
from waydroid_helper.models import PropertyCategory, PropertyModel, SessionModel, ModelState, SessionState
from waydroid_helper.sdk import WaydroidSDK, PropertyManager, ConfigManager


class ModelController(GObject.Object):
    """
    Controller that coordinates between models and SDK.
    
    This controller:
    - Manages the lifecycle of models
    - Coordinates operations between models and SDK
    - Provides a clean interface for the view layer
    - Handles async operations and error handling
    """
    
    def __init__(self):
        super().__init__()

        # Initialize models
        self.property_model = PropertyModel()
        self.session_model = SessionModel()

        # Initialize SDK components
        self.waydroid_sdk = WaydroidSDK()
        self.property_manager = PropertyManager()
        self.config_manager = ConfigManager()

        # Task management
        self._task = Task()
        self._status_update_lock = asyncio.Lock()
        self._monitoring_started = False

        # Defer async initialization until event loop is available
        GLib.idle_add(self._start_status_monitoring)
    
    def _start_status_monitoring(self):
        """Start periodic monitoring of Waydroid status"""
        if self._monitoring_started:
            return False

        self._monitoring_started = True

        # Initial status check
        self._task.create_task(self._initial_status_check())

        # Schedule periodic updates every 2 seconds
        GLib.timeout_add_seconds(2, self._schedule_status_update)

        return False  # Don't repeat this idle callback

    async def _initial_status_check(self):
        """Initial status check with forced property loading"""
        try:
            current_state = await self.waydroid_sdk.get_session_status()

            # Set initial session state
            self.session_model.set_session_state(current_state)

            # Force load privileged and waydroid properties if waydroid is initialized
            if current_state in (SessionState.STOPPED, SessionState.RUNNING):
                await self._load_privileged_properties()
                await self._load_waydroid_properties()

            # Load persist properties if session is running
            if current_state == SessionState.RUNNING:
                await self._load_persist_properties()

            # Load Android version if waydroid is initialized
            if current_state in (SessionState.STOPPED, SessionState.RUNNING):
                await self._load_android_version()

        except Exception as e:
            logger.error(f"Failed initial status check: {e}")

    def _schedule_status_update(self) -> bool:
        """Schedule a status update task"""
        self._task.create_task(self._update_session_status())
        return True  # Continue the timeout
    
    async def _update_session_status(self):
        """Update session status and load properties if needed"""
        async with self._status_update_lock:
            try:
                new_state = await self.waydroid_sdk.get_session_status()
                old_state = self.session_model.get_property("state")

                # Only log significant state changes
                if old_state != new_state:
                    logger.debug(f"Session state transition: {old_state} -> {new_state}")

                # Update session state
                self.session_model.set_session_state(new_state)

                # Handle state transitions
                await self._handle_session_state_transition(old_state, new_state)

            except Exception as e:
                logger.error(f"Failed to update session status: {e}")
    
    async def _handle_session_state_transition(self, old_state: SessionState, new_state: SessionState):
        """Handle session state transitions and load/unload properties accordingly"""

        # When session becomes running, load persist properties
        if new_state == SessionState.RUNNING and old_state != SessionState.RUNNING:
            await self._load_persist_properties()
            # Also load Android version if coming from UNINITIALIZED
            if old_state == SessionState.UNINITIALIZED:
                await self._load_android_version()

        # When session stops, reset persist props state but keep privileged props
        elif new_state == SessionState.STOPPED and old_state == SessionState.RUNNING:
            self.property_model.set_property("state", ModelState.UNINITIALIZED)
            # privileged_state remains READY

        # When Waydroid becomes initialized (stopped), load privileged and waydroid properties
        elif new_state == SessionState.STOPPED and old_state == SessionState.UNINITIALIZED:
            await self._load_privileged_properties()
            await self._load_waydroid_properties()
            await self._load_android_version()

        # When waydroid becomes coproperty_modelmpletely uninitialized, reset all states
        elif new_state == SessionState.UNINITIALIZED:
            self.property_model.set_property("state", ModelState.UNINITIALIZED)
            self.property_model.set_property("privileged-state", ModelState.UNINITIALIZED)
            self.property_model.set_property("waydroid-state", ModelState.UNINITIALIZED)
    

    
    async def _load_persist_properties(self):
        """Load persist properties from Waydroid"""
        self.property_model.set_property("state", ModelState.LOADING)

        try:
            property_definitions = self.property_model._property_definitions
            property_values = await self.property_manager.get_all_persist_properties(
                property_definitions
            )

            for prop_name, raw_value in property_values.items():
                prop_def = self.property_model.get_property_definition(prop_name)
                if prop_def:
                    transformed_value = prop_def.transform_in(raw_value)
                    self.property_model.set_property_value(prop_name, transformed_value)

            self.property_model.set_property("state", ModelState.READY)

        except Exception as e:
            logger.error(f"Failed to load persist properties: {e}")
            self.property_model.set_property("state", ModelState.ERROR)
            raise
    
    async def _load_privileged_properties(self):
        """Load privileged properties from config"""
        self.property_model.set_property("privileged-state", ModelState.LOADING)

        try:
            if not self.config_manager.load_config():
                raise Exception("Failed to load config")

            property_values = self.config_manager.get_all_privileged_properties(
                self.property_model._property_definitions
            )

            for prop_name, raw_value in property_values.items():
                prop_def = self.property_model.get_property_definition(prop_name)
                if prop_def:
                    transformed_value = prop_def.transform_in(raw_value)
                    self.property_model.set_property_value(prop_name, transformed_value)

            self.property_model.set_property("privileged-state", ModelState.READY)

        except Exception as e:
            logger.error(f"Failed to load privileged properties: {e}")
            self.property_model.set_property("privileged-state", ModelState.ERROR)
            raise

    async def _load_waydroid_properties(self):
        """Load waydroid config properties from [waydroid] section"""
        self.property_model.set_property("waydroid-state", ModelState.LOADING)

        try:
            if not self.config_manager.load_config():
                raise Exception("Failed to load config")

            property_values = self.config_manager.get_all_waydroid_properties(
                self.property_model._property_definitions
            )

            for prop_name, raw_value in property_values.items():
                prop_def = self.property_model.get_property_definition(prop_name)
                if prop_def:
                    transformed_value = prop_def.transform_in(raw_value)
                    self.property_model.set_property_value(prop_name, transformed_value)

            self.property_model.set_property("waydroid-state", ModelState.READY)

        except Exception as e:
            logger.error(f"Failed to load waydroid properties: {e}")
            self.property_model.set_property("waydroid-state", ModelState.ERROR)
            raise

    async def _load_android_version(self):
        """Load Android version from config"""
        try:
            android_version = await self.config_manager.get_android_version()
            self.session_model.set_property("android_version", android_version)
        except Exception as e:
            logger.error(f"Failed to load Android version: {e}")
    
    # Public API for view layer
    
    async def save_persist_property(self, property_name: str) -> bool:
        """Save a single persist property"""
        try:
            # Convert property name format (handle both dashes and underscores)
            normalized_name = property_name.replace("-", "_")

            prop_def = self.property_model.get_property_definition(normalized_name)
            if not prop_def or prop_def.category != PropertyCategory.PERSIST:
                logger.error(f"Property {property_name} (normalized: {normalized_name}) is not a persist property")
                return False

            value = self.property_model.get_property_value(normalized_name)
            transformed_value = prop_def.transform_out(value)

            logger.info(f"Saving persist property {normalized_name} = {value} (transformed: {transformed_value})")
            return await self.property_manager.set_persist_property(prop_def.nick, transformed_value)

        except Exception as e:
            logger.error(f"Failed to save persist property {property_name}: {e}")
            return False

    async def refresh_persist_property(self, property_name: str) -> bool:
        """Refresh a single persist property from Waydroid"""
        try:
            # Convert property name format (handle both dashes and underscores)
            normalized_name = property_name.replace("-", "_")

            prop_def = self.property_model.get_property_definition(normalized_name)
            if not prop_def or prop_def.category != PropertyCategory.PERSIST:
                logger.error(f"Property {property_name} (normalized: {normalized_name}) is not a persist property")
                return False

            # Get current value from Waydroid
            raw_value = await self.property_manager.get_persist_property(prop_def.nick)
            transformed_value = prop_def.transform_in(raw_value)

            # Update the model
            self.property_model.set_property_value(normalized_name, transformed_value)

            logger.info(f"Refreshed persist property {normalized_name} = {transformed_value} (raw: {raw_value})")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh persist property {property_name}: {e}")
            return False
    
    async def save_all_privileged_properties(self) -> bool:
        """Save all privileged properties to config file"""
        try:
            # Prepare all privileged properties for saving
            privileged_props = self.property_model.get_privileged_properties()
            properties_to_save = {}

            for prop_name, prop_def in privileged_props.items():
                value = self.property_model.get_property_value(prop_name)
                transformed_value = prop_def.transform_out(value)
                properties_to_save[prop_def.nick] = transformed_value

            # Set all properties in config
            self.config_manager.set_multiple_privileged_properties(properties_to_save)

            # Save config file
            success = await self.config_manager.save_config()

            if success:
                # Trigger upgrade to apply changes
                await self.waydroid_sdk.upgrade(offline=True)

            return success
            
        except Exception as e:
            logger.error(f"Failed to save privileged properties: {e}")
            return False
    
    async def reset_persist_properties(self) -> bool:
        """Reset all persist properties to defaults"""
        try:
            persist_props = self.property_model.get_persist_properties()
            
            # Reset in model
            self.property_model.reset_to_defaults(PropertyCategory.PERSIST)
            
            # Save all persist properties
            tasks = []
            for prop_name in persist_props.keys():
                task = self.save_persist_property(prop_name)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check if all succeeded
            return all(result is True for result in results if not isinstance(result, Exception))
            
        except Exception as e:
            logger.error(f"Failed to reset persist properties: {e}")
            return False
    
    async def reset_privileged_properties(self) -> bool:
        """Reset all privileged properties to defaults"""
        try:
            # Reset in model
            self.property_model.reset_to_defaults(PropertyCategory.PRIVILEGED)
            
            # Reset in config
            self.config_manager.reset_privileged_properties()
            
            # Save config
            return await self.config_manager.save_config()
            
        except Exception as e:
            logger.error(f"Failed to reset privileged properties: {e}")
            return False

    async def save_all_waydroid_properties(self) -> bool:
        """Save all waydroid config properties to [waydroid] section"""
        try:
            # Prepare all waydroid properties for saving
            waydroid_props = self.property_model.get_waydroid_properties()
            properties_to_save = {}

            for prop_name, prop_def in waydroid_props.items():
                value = self.property_model.get_property_value(prop_name)
                transformed_value = prop_def.transform_out(value)
                properties_to_save[prop_def.nick] = transformed_value

            # Set all properties in config
            self.config_manager.set_multiple_waydroid_properties(properties_to_save)

            # Save config file
            success = await self.config_manager.save_config()

            if success:
                # Trigger upgrade to apply changes
                await self.waydroid_sdk.stop_session(wait=True)
                await self.waydroid_sdk.restart_container(wait=True)

            return success

        except Exception as e:
            logger.error(f"Failed to save waydroid properties: {e}")
            return False

    async def reset_waydroid_properties(self) -> bool:
        """Reset all waydroid config properties to defaults"""
        try:
            # Reset in model
            self.property_model.reset_to_defaults(PropertyCategory.WAYDROID)

            # Reset in config
            self.config_manager.reset_waydroid_properties(self.property_model._property_definitions)

            # Save config
            return await self.config_manager.save_config()

        except Exception as e:
            logger.error(f"Failed to reset waydroid properties: {e}")
            return False

    async def restore_privileged_properties(self) -> bool:
        """Restore privileged properties from saved config"""
        try:
            # Reload config from file
            if not self.config_manager.load_config():
                return False
            
            # Reload properties into model
            await self._load_privileged_properties()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore privileged properties: {e}")
            return False
    
    async def restore_waydroid_properties(self) -> bool:
        """Restore waydroid config properties from saved config"""
        try:
            # Reload config from file
            if not self.config_manager.load_config():
                return False
            
            # Reload properties into model
            await self._load_waydroid_properties()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore waydroid properties: {e}")
            return False
    
    async def set_device_info(self, device_properties: Dict[str, Any]) -> bool:
        """Set device information properties"""
        try:
            # Update model
            for prop_name, value in device_properties.items():
                # Convert property names (e.g., "ro.product.brand" -> "ro_product_brand")
                model_prop_name = prop_name.replace(".", "_")
                self.property_model.set_property_value(model_prop_name, value)
            self.config_manager.set_multiple_privileged_properties(device_properties)        
            return True
            
        except Exception as e:
            logger.error(f"Failed to set device info: {e}")
            return False
    
    async def set_extension_properties(self, properties: Dict[str, Any]) -> bool:
        """Set extension properties"""
        try:
            # Set properties in config
            self.config_manager.set_multiple_privileged_properties(properties)
            
            # Save and upgrade
            success = await self.config_manager.save_config()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to set extension properties: {e}")
            return False
    
    async def remove_extension_properties(self, property_keys: list[str]) -> bool:
        """Remove extension properties"""
        try:
            # Remove properties from config
            empty_properties = {key: "" for key in property_keys}
            self.config_manager.set_multiple_privileged_properties(empty_properties)
            
            # Save and upgrade
            success = await self.config_manager.save_config()
            if success:
                await self.waydroid_sdk.upgrade(offline=True)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to remove extension properties: {e}")
            return False
    
    # Session management
    
    async def start_session(self) -> bool:
        """Start Waydroid session"""
        return await self.waydroid_sdk.start_session()
    
    async def stop_session(self) -> bool:
        """Stop Waydroid session"""
        return await self.waydroid_sdk.stop_session()
    
    async def restart_session(self) -> bool:
        """Restart Waydroid session"""
        return await self.waydroid_sdk.restart_session()
    
    async def show_full_ui(self) -> bool:
        """Show Waydroid full UI"""
        return await self.waydroid_sdk.show_full_ui()
    
    async def upgrade(self, offline: bool = False) -> bool:
        """Upgrade Waydroid"""
        return await self.waydroid_sdk.upgrade(offline)
