# pyright: reportAny=false
# pyright: reportAttributeAccessIssue=false,reportUnknownArgumentType=false,reportUnknownMemberType=false

"""
Clean SDK Layer for Waydroid Helper

This module implements a clean SDK that handles Waydroid operations without
managing state or emitting events. It's a pure interface to Waydroid functionality.
"""

import asyncio
import configparser
import copy
import os
from typing import Any, Dict, List, Optional, Tuple

from gi.repository import GLib

from waydroid_helper.util import SubprocessError, SubprocessManager, logger
from waydroid_helper.models import SessionState, PropertyDefinition


CONFIG_PATH = os.environ.get("WAYDROID_CONFIG", "/var/lib/waydroid/waydroid.cfg")


class WaydroidSDK:
    """
    Pure Waydroid SDK that handles session management.
    
    This SDK:
    - Provides clean interfaces to Waydroid operations
    - Returns results without managing state
    - Has no knowledge of models or UI
    """
    
    def __init__(self):
        self._subprocess = SubprocessManager()
    
    async def get_session_status(self) -> SessionState:
        """Get current Waydroid session status"""
        try:
            result = await self._subprocess.run("waydroid status")
            output = result["stdout"]
            
            if "WayDroid is not initialized" in output:
                return SessionState.UNINITIALIZED
            elif "Session:\tRUNNING" in output:
                return SessionState.RUNNING
            elif "Session:\tSTOPPED" in output:
                return SessionState.STOPPED
            else:
                return SessionState.LOADING
                
        except SubprocessError as e:
            logger.error(f"Failed to get Waydroid status: {e}")
            return SessionState.UNINITIALIZED
    
    async def start_session(self) -> bool:
        """Start Waydroid session"""
        try:
            await self._subprocess.run("waydroid session start", flag=True)
            return True
        except SubprocessError as e:
            logger.error(f"Failed to start Waydroid session: {e}")
            return False
    
    async def stop_session(self) -> bool:
        """Stop Waydroid session"""
        try:
            await self._subprocess.run("waydroid session stop", flag=True)
            return True
        except SubprocessError as e:
            logger.error(f"Failed to stop Waydroid session: {e}")
            return False
    
    async def restart_session(self) -> bool:
        """Restart Waydroid session"""
        stop_success = await self.stop_session()
        if not stop_success:
            return False
        
        # Wait a moment for the session to fully stop
        await asyncio.sleep(1)
        
        return await self.start_session()
    
    async def show_full_ui(self) -> bool:
        """Show Waydroid full UI"""
        try:
            await self._subprocess.run("waydroid show-full-ui", flag=True)
            return True
        except SubprocessError as e:
            logger.error(f"Failed to show Waydroid full UI: {e}")
            return False
    
    async def upgrade(self, offline: bool = False) -> bool:
        """Upgrade Waydroid"""
        try:
            if offline:
                cmd = f"pkexec {os.environ['WAYDROID_CLI_PATH']} upgrade -o"
            else:
                cmd = f"pkexec {os.environ['WAYDROID_CLI_PATH']} upgrade"
            
            await self._subprocess.run(cmd, flag=True)
            return True
        except SubprocessError as e:
            logger.error(f"Failed to upgrade Waydroid: {e}")
            return False


class PropertyManager:
    """
    Manager for Waydroid properties.
    
    This manager:
    - Handles both persist properties (via waydroid prop) and privileged properties (via config)
    - Provides clean interfaces for property operations
    - Returns results without managing state
    """
    
    def __init__(self):
        self._subprocess = SubprocessManager()
    
    async def get_persist_property(self, property_nick: str) -> str:
        """Get a persist property value using waydroid prop get"""
        try:
            result = await self._subprocess.run(f"waydroid prop get {property_nick}")
            output = result["stdout"].replace(
                "[gbinder] Service manager /dev/binder has appeared", ""
            ).strip().split("\n")[-1]
            return output
        except SubprocessError as e:
            logger.error(f"Failed to get persist property {property_nick}: {e}")
            return ""
    
    async def set_persist_property(self, property_nick: str, value: str) -> bool:
        """Set a persist property value using waydroid prop set"""
        try:
            await self._subprocess.run(f'waydroid prop set {property_nick} "{value}"')
            return True
        except SubprocessError as e:
            logger.error(f"Failed to set persist property {property_nick}: {e}")
            return False
    
    async def get_all_persist_properties(self, property_definitions: Dict[str, PropertyDefinition]) -> Dict[str, str]:
        """Get all persist properties in parallel"""
        persist_props = {name: prop_def for name, prop_def in property_definitions.items()
                        if not prop_def.is_privileged}

        if not persist_props:
            return {}

        # Load properties sequentially with error handling
        property_values = {}
        for name, prop_def in persist_props.items():
            try:
                result = await self._subprocess.run(f"waydroid prop get {prop_def.nick}")
                output = result["stdout"].replace(
                    "[gbinder] Service manager /dev/binder has appeared", ""
                ).strip().split("\n")[-1]
                property_values[name] = output
            except Exception as e:
                logger.warning(f"Failed to get property {name}: {e}")
                property_values[name] = ""
        return property_values


class ConfigManager:
    """
    Manager for Waydroid configuration files.
    
    This manager:
    - Handles privileged properties that require config file modification
    - Provides clean interfaces for config operations
    - Returns results without managing state
    """
    
    def __init__(self):
        self._subprocess = SubprocessManager()
        self._config_cache: Optional[configparser.ConfigParser] = None
    
    def load_config(self) -> bool:
        """Load Waydroid configuration file"""
        try:
            self._config_cache = configparser.ConfigParser()
            self._config_cache.read(CONFIG_PATH)
            return True
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return False
    
    def get_privileged_property(self, property_nick: str) -> str:
        """Get a privileged property from config"""
        if not self._config_cache:
            if not self.load_config():
                return ""
        
        try:
            return self._config_cache.get("properties", property_nick, fallback="")
        except Exception as e:
            logger.error(f"Failed to get privileged property {property_nick}: {e}")
            return ""
    
    def get_all_privileged_properties(self, property_definitions: Dict[str, PropertyDefinition]) -> Dict[str, str]:
        """Get all privileged properties from config"""
        if not self._config_cache:
            if not self.load_config():
                return {}
        
        privileged_props = {name: prop_def for name, prop_def in property_definitions.items() 
                           if prop_def.is_privileged}
        
        property_values = {}
        for name, prop_def in privileged_props.items():
            try:
                value = self._config_cache.get("properties", prop_def.nick, fallback="")
                property_values[name] = value
            except Exception as e:
                logger.error(f"Failed to get privileged property {name}: {e}")
                property_values[name] = ""
        
        return property_values
    
    def set_privileged_property(self, property_nick: str, value: str):
        """Set a privileged property in config (in memory only)"""
        if not self._config_cache:
            if not self.load_config():
                return
        
        if value == "":
            # Remove empty properties
            self._config_cache.remove_option("properties", property_nick)
        else:
            self._config_cache.set("properties", property_nick, value)
    
    def set_multiple_privileged_properties(self, properties: Dict[str, str]):
        """Set multiple privileged properties in config (in memory only)"""
        if not self._config_cache:
            if not self.load_config():
                logger.error("Failed to load config for setting privileged properties")
                return

        for property_nick, value in properties.items():
            if value == "":
                if self._config_cache.has_option("properties", property_nick):
                    self._config_cache.remove_option("properties", property_nick)
            else:
                self._config_cache.set("properties", property_nick, value)
    
    async def save_config(self) -> bool:
        """Save config to file using privileged access"""
        if not self._config_cache:
            logger.error("No config loaded to save")
            return False
        
        try:
            # Save to cache directory first
            cache_dir = os.path.join(GLib.get_user_cache_dir(), "waydroid-helper")
            cache_config_path = os.path.join(cache_dir, "waydroid.cfg")
            
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_config_path, "w") as f:
                self._config_cache.write(f)
            
            # Copy to system location with pkexec
            cmd = f"pkexec {os.environ['WAYDROID_CLI_PATH']} copy_to_var {cache_config_path} waydroid.cfg"
            await self._subprocess.run(cmd, flag=True)
            
            return True
        except SubprocessError as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    async def get_android_version(self) -> str:
        """Get Android version from system image"""
        if not self._config_cache:
            if not self.load_config():
                return ""
        
        try:
            system_image_path = os.path.join(
                self._config_cache.get("waydroid", "images_path"), "system.img"
            )
            result = await self._subprocess.run(
                f"debugfs -R 'cat /system/build.prop' {system_image_path} | grep '^ro.build.version.release=' | cut -d'=' -f2"
            )
            return result["stdout"].strip()
        except Exception as e:
            logger.error(f"Failed to get Android version: {e}")
            return ""
    
    def reset_privileged_properties(self, property_definitions: Dict[str, PropertyDefinition]):
        """Reset all privileged properties to defaults (in memory only)"""
        if not self._config_cache:
            if not self.load_config():
                return
        
        privileged_props = {name: prop_def for name, prop_def in property_definitions.items() 
                           if prop_def.is_privileged}
        
        for name, prop_def in privileged_props.items():
            self._config_cache.remove_option("properties", prop_def.nick)
