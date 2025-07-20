#!/usr/bin/env python3
"""
Transparent window module
Provides implementation and window management for transparent windows
"""

from gettext import gettext as _
from typing import TYPE_CHECKING
import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Adw, Gdk, GObject, GLib

from waydroid_helper.controller.app.workspace_manager import WorkspaceManager
from waydroid_helper.controller.core import (
    KeyCombination,
    key_registry,
    Server,
    is_point_in_rect,
    event_bus,
    EventType,
    Event,
)
from waydroid_helper.controller.core.constants import APP_TITLE
from waydroid_helper.controller.core.handler import (
    InputEventHandlerChain,
    InputEvent,
    KeyMappingEventHandler,
    DefaultEventHandler,
    key_mapping_manager,
)
from waydroid_helper.controller.ui.styles import StyleManager
from waydroid_helper.controller.ui.menus import ContextMenuManager
from waydroid_helper.controller.widgets.factory import WidgetFactory
from waydroid_helper.controller.widgets.config import ConfigType

from waydroid_helper.util.log import logger
from waydroid_helper.util.adb_helper import AdbHelper
import asyncio
import weakref

if TYPE_CHECKING:
    from waydroid_helper.controller.widgets.base import BaseWidget


Adw.init()

MAX_RETRY_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 3


class CircleOverlay(Gtk.DrawingArea):
    """Circular overlay for drawing skill release range indicators"""
    
    def __init__(self):
        super().__init__()
        self.circle_data = None
        self.set_draw_func(self._draw_circle, None)
    
    def set_circle_data(self, data):
        """Sets circular data and triggers redraw"""
        self.circle_data = data
        self.queue_draw()
    
    def _draw_circle(self, widget, cr, width, height, user_data):
        """Draws a circle"""
        if not self.circle_data:
            return
            
        # Get circle parameters
        circle_radius = self.circle_data.get('circle_radius', 200)
        
        # Calculate circle parameters
        window_center_x = width / 2
        window_center_y = height / 2
        
        # Draw circle boundary
        cr.set_source_rgba(0.6, 0.6, 0.6, 0.8)  # Semi-transparent gray
        cr.set_line_width(3)
        cr.arc(window_center_x, window_center_y, circle_radius, 0, 2 * math.pi)
        cr.stroke()
        
        # Draw circle center point
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.9)
        cr.arc(window_center_x, window_center_y, 4, 0, 2 * math.pi)
        cr.fill()


class TransparentWindow(Adw.Window):
    """Transparent window"""

    # __gtype_name__ = 'TransparentWindow'

    # Define mode constants
    EDIT_MODE = "edit"
    MAPPING_MODE = "mapping"

    # Define current_mode as a GObject property
    current_mode = GObject.Property(
        type=str,
        default=EDIT_MODE,
        nick="Current Mode",
        blurb="The current operating mode (edit or mapping)",
    )

    def __init__(self, app):
        super().__init__(application=app)

        self.connect("close-request", self._on_close_request)

        self.set_title(APP_TITLE)

        # Create main container (Overlay)
        overlay = Gtk.Overlay.new()
        self.set_content(overlay)

        self.fixed = Gtk.Fixed.new()
        self.fixed.set_name("mapping-widget")
        overlay.set_child(self.fixed)

        # Create mode switching hint
        self.notification_label = Gtk.Label.new("")
        self.notification_label.set_name("mode-notification-label")

        self.notification_box = Gtk.Box()
        self.notification_box.set_name("mode-notification-box")
        self.notification_box.set_halign(Gtk.Align.CENTER)
        self.notification_box.set_valign(Gtk.Align.START)
        self.notification_box.set_margin_top(60)
        self.notification_box.append(self.notification_label)
        self.notification_box.set_opacity(0.0)
        self.notification_box.set_can_target(False)  # Ignore mouse events

        overlay.add_overlay(self.notification_box)

        # Initialize components
        self.widget_factory = WidgetFactory()
        self.style_manager = StyleManager()
        self.menu_manager = ContextMenuManager(self)
        self.workspace_manager = WorkspaceManager(self, self.fixed)

        # Subscribe to events
        event_bus.subscribe(
            EventType.SETTINGS_WIDGET, self._on_widget_settings_requested
        )
        event_bus.subscribe(
            EventType.WIDGET_SELECTION_OVERLAY, self._on_widget_selection_overlay
        )
        
        # Create circular drawing overlay
        self.circle_overlay = CircleOverlay()
        self.circle_overlay.set_can_target(False)  # Ignore mouse events
        overlay.add_overlay(self.circle_overlay)

        # Create global event handler chain
        self.event_handler_chain = InputEventHandlerChain()
        # Import and add default handler
        self.server = Server("0.0.0.0", 10721)
        self.adb_helper = AdbHelper()
        self.scrcpy_setup_task = asyncio.create_task(self.setup_scrcpy())
        self.key_mapping_handler = KeyMappingEventHandler()
        self.default_handler = DefaultEventHandler()

        self.event_handler_chain.add_handler(self.key_mapping_handler)
        self.event_handler_chain.add_handler(self.default_handler)

        # Initialize dual mode system
        self.setup_mode_system()

        # Initialize event handlers
        self.setup_event_handlers()

        # Set fullscreen
        self.setup_window()

        # Set UI (mainly event controllers)
        self.setup_controllers()

        # Initial hint
        GLib.idle_add(self.show_notification, _("Edit Mode (F1: Switch Mode)"))

    def _on_widget_selection_overlay(self, event):
        """Handles component selection overlay events"""
        overlay_data = event.data
        if overlay_data['action'] == 'show':
            self.circle_overlay.set_circle_data(overlay_data)
            logger.debug(f"Displaying circular overlay: {overlay_data}")
        elif overlay_data['action'] == 'hide':
            self.circle_overlay.set_circle_data(None)
            logger.debug(f"Hiding circular overlay: {overlay_data}")

    def _on_widget_settings_requested(self, event: "Event[bool]"):
        """Callback when a widget requests settings, pops up a Popover"""
        widget = event.source
        logger.info(
            f"Widget {type(widget).__name__} (id={id(widget)}) requested settings."
        )

        def workaround_popover_auto_hide(controller, n_press, x, y):
            if popover.get_visible() and popover.get_autohide():
                if (
                    x < 0
                    or y < 0
                    or x > popover.get_width()
                    or y > popover.get_height()
                ):
                    popover.popdown()

        popover = Gtk.Popover()
        popover.set_autohide(event.data)
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", workaround_popover_auto_hide)
        popover.add_controller(click_controller)

        # popover.set_cascade_popdown(event.data)
        # "fix: Tried to map a grabbing popup with a non-top most parent" error
        popover.set_parent(self)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_size_request(250, -1)  # Set a minimum width for the popover
        popover.set_child(main_box)

        # Header Label
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{widget.WIDGET_NAME}{_("Settings")}</b>")
        title_label.set_halign(Gtk.Align.CENTER)
        main_box.append(title_label)

        # Use new configuration system
        config_manager = widget.get_config_manager()

        if not config_manager.configs:
            label = Gtk.Label(label=_("This widget has no settings."))
            main_box.append(label)
        else:
            # Use config manager to generate UI panel
            config_panel = config_manager.create_ui_panel()
            main_box.append(config_panel)

            # # Confirm Button
            # confirm_button = Gtk.Button(label=_("OK"), halign=Gtk.Align.END)
            # confirm_button.add_css_class("suggested-action")

            # def on_confirm_clicked(btn):
            #     # UI value changes are automatically synced to config manager, just close the popover
            #     logger.info("Configuration popover closed by user.")
            #     popover.popdown()

            # confirm_button.connect("clicked", on_confirm_clicked)
            # main_box.append(confirm_button)

        # Pointing and Display
        settings_button_rect = Gdk.Rectangle()
        bounds = widget.get_settings_button_bounds()
        settings_button_rect.x = bounds[0] + widget.x
        settings_button_rect.y = bounds[1] + widget.y
        settings_button_rect.width = bounds[2]
        settings_button_rect.height = bounds[3]

        popover.set_pointing_to(settings_button_rect)
        popover.set_position(Gtk.PositionType.BOTTOM)

        def on_popover_closed(p):
            # Clean up UI references in ConfigManager to prevent memory leaks
            config_manager.clear_ui_references()
            # Unparent the popover from its parent
            p.unparent()

        popover.connect("closed", on_popover_closed)
        popover.popup()

    def _on_close_request(self, window):
        logger.info("Close request received, running cleanup...")
        self.on_clear_widgets(None)
        self.close()
        return False

    def close(self):
        self.server.close()
        if not self.scrcpy_setup_task.done():
            self.scrcpy_setup_task.cancel()

        asyncio.create_task(self.cleanup_scrcpy())
        super().close()

    async def cleanup_scrcpy(self):
        await self.adb_helper.remove_reverse_tunnel()
        logger.info("Scrcpy cleanup finished.")

    async def setup_scrcpy(self):
        """Pushes scrcpy-server and starts it on the device, with retry logic."""
        logger.info("Waiting for internal server to start...")
        await self.server.wait_started()

        if not self.server.server:
            logger.error("Internal server failed to start. Aborting scrcpy setup.")
            return

        logger.info("Internal server started. Starting scrcpy setup...")

        for attempt in range(MAX_RETRY_ATTEMPTS):
            logger.info(f"Scrcpy setup attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}...")
            try:
                # 1. Get screen resolution. Not critical, so no retry on failure.
                await self.adb_helper.get_screen_resolution()

                # 2. Push server to device
                if not await self.adb_helper.push_scrcpy_server():
                    logger.warning(
                        f"Failed to push scrcpy-server. Retrying in {RETRY_DELAY_SECONDS}s..."
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue

                # 3. Generate SCID and setup reverse tunnel
                scid, socket_name = self.adb_helper.generate_scid()
                if not await self.adb_helper.reverse_tunnel(
                    socket_name, self.server.port
                ):
                    logger.warning(
                        f"Failed to set up adb reverse. Retrying in {RETRY_DELAY_SECONDS}s..."
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue

                # 4. Start scrcpy-server on device
                if not await self.adb_helper.start_scrcpy_server(scid):
                    logger.warning(
                        f"Failed to start scrcpy-server. Retrying in {RETRY_DELAY_SECONDS}s..."
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue

                logger.info("Scrcpy setup process completed successfully.")
                return  # Exit on success

            except asyncio.CancelledError:
                logger.info("Scrcpy setup task was cancelled.")
                return  # Use return to exit immediately on cancellation
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during setup attempt {attempt + 1}: {e}"
                )
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        logger.error(
            f"Scrcpy setup failed after {MAX_RETRY_ATTEMPTS} attempts. Aborting."
        )

    def setup_mode_system(self):
        """Initializes the dual mode system"""
        # Listen for current_mode property changes
        self.connect("notify::current-mode", self._on_mode_changed)

        logger.debug(f"Dual mode system initialized, current mode: {self.current_mode}")

    def setup_event_handlers(self):
        """Sets up event handlers"""
        # Example mappings for default handler
        # default_handler.add_key_mapping("T", lambda: print("🎮 Default: T key test"))
        # default_handler.add_key_mapping("G", lambda: print("🎮 Default: G key test"))
        # default_handler.add_mouse_mapping(2, lambda: print("🖱️ Default: middle click"))  # middle click

        logger.debug("Event handler chain initialized")
        logger.debug(
            f"Handler list: {[h['name'] for h in self.event_handler_chain.get_handlers_info()]}"
        )

    def setup_window(self):
        """Sets window properties"""
        self.realize()
        self.set_decorated(False)

        surface = self.get_surface()
        if surface:
            display = self.get_display()
            if display:
                monitor = display.get_monitor_at_surface(surface)
                if monitor:
                    geometry = monitor.get_geometry()
                    self.set_default_size(geometry.width, geometry.height)

        self.set_name("transparent-window")

    def setup_ui(self):
        """Sets up the user interface"""
        # Main container is created and set in __init__
        pass

    def setup_controllers(self):
        """Sets up event controllers"""
        # Global keyboard events
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.on_global_key_press)
        key_controller.connect("key-released", self.on_global_key_release)
        self.add_controller(key_controller)

        # Window-level mouse scroll events
        scroll_controller = Gtk.EventControllerScroll.new(
            flags=Gtk.EventControllerScrollFlags.BOTH_AXES
        )
        scroll_controller.connect("scroll-begin", self.on_window_mouse_scroll)
        scroll_controller.connect("scroll", self.on_window_mouse_scroll)
        scroll_controller.connect("scroll-end", self.on_window_mouse_scroll)
        self.add_controller(scroll_controller)

        # Window-level mouse event controller
        click_controller = Gtk.GestureClick()
        click_controller.set_button(0)  # All buttons
        click_controller.connect("pressed", self.on_window_mouse_pressed)
        click_controller.connect("released", self.on_window_mouse_released)
        self.add_controller(click_controller)

        # Window-level mouse motion events
        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect("motion", self.on_window_mouse_motion)
        self.add_controller(motion_controller)

        # Initialize drag and resize states
        self.dragging_widget = None
        self.resizing_widget = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_direction = None

        # Initialize interaction states
        self.selected_widget = None
        self.interaction_start_x = 0
        self.interaction_start_y = 0
        self.pending_resize_direction = None

    def on_window_mouse_pressed(self, controller, n_press, x, y):
        """Window-level mouse press event"""
        button = controller.get_current_button()
        logger.debug(
            f"Mouse pressed: position({x:.1f}, {y:.1f}), button={button}, mode={self.current_mode}"
        )

        # Use event handler chain in mapping mode
        if self.current_mode == self.MAPPING_MODE:
            logger.debug(
                "In mapping mode, use event handler chain to handle mouse event"
            )

            # Create Key object for mouse button
            mouse_key = key_registry.create_mouse_key(button)

            # Create input event
            event = InputEvent(
                event_type="mouse_press",
                key=mouse_key,
                button=button,
                position=(int(x), int(y)),
                raw_data={"controller": controller, "n_press": n_press, "x": x, "y": y},
            )

            # Process with event handler chain
            handled = self.event_handler_chain.process_event(event)
            if handled:
                logger.debug("Mouse event handled by event handler chain")
                return True
            else:
                logger.debug("Mouse event not handled by any event handler")
            return

        # Mouse event handling in edit mode
        if button == Gdk.BUTTON_SECONDARY:  # Right click
            widget_at_position = self.workspace_manager.get_widget_at_position(x, y)
            if not widget_at_position:
                # Right click on blank area, show create menu
                logger.debug("Right click on blank area, show create menu")
                self.menu_manager.show_widget_creation_menu(x, y, self.widget_factory)
            else:
                # Right click on widget, call widget's right-click callback
                logger.debug(
                    f"Right click on widget: {type(widget_at_position).__name__}"
                )
                local_x, local_y = self.workspace_manager.global_to_local_coords(
                    widget_at_position, x, y
                )
                if hasattr(widget_at_position, "on_widget_right_clicked"):
                    widget_at_position.on_widget_right_clicked(local_x, local_y)

        elif button == Gdk.BUTTON_PRIMARY:  # Left click
            self.workspace_manager.handle_mouse_press(controller, n_press, x, y)

    def on_window_mouse_motion(self, controller, x, y):
        """Window-level mouse motion event"""
        if self.current_mode == self.MAPPING_MODE:
            logger.debug(
                "In mapping mode, use event handler chain to handle mouse motion"
            )
            event = controller.get_current_event()
            state = event.get_modifier_state()
            # FIXME This mouse_key should actually be None, this is just for compatibility.
            # Right-click walking can be triggered when moving in the right-click down state.
            mouse_key = None
            button = None
            if state & Gdk.ModifierType.BUTTON1_MASK:
                mouse_key = key_registry.create_mouse_key(Gdk.BUTTON_PRIMARY)
                button = Gdk.BUTTON_PRIMARY
            elif state & Gdk.ModifierType.BUTTON2_MASK:
                mouse_key = key_registry.create_mouse_key(Gdk.BUTTON_MIDDLE)
                button = Gdk.BUTTON_MIDDLE
            elif state & Gdk.ModifierType.BUTTON3_MASK:
                mouse_key = key_registry.create_mouse_key(Gdk.BUTTON_SECONDARY)
                button = Gdk.BUTTON_SECONDARY

            event = InputEvent(
                event_type="mouse_motion",
                position=(int(x), int(y)),
                key=mouse_key,
                button=button,
                raw_data={"controller": controller, "x": x, "y": y},
            )
            # Skill casting and right-click walking
            event_bus.emit(Event(EventType.MOUSE_MOTION, self, event))
            self.event_handler_chain.process_event(event)
            return

        # In edit mode, delegate to workspace_manager
        self.workspace_manager.handle_mouse_motion(controller, x, y)

    def on_window_mouse_scroll(
        self,
        controller: Gtk.EventControllerScroll,
        dx: float | None = None,
        dy: float | None = None,
    ):
        if self.current_mode == self.MAPPING_MODE:
            event = InputEvent(
                event_type="mouse_scroll",
                raw_data={"controller": controller, "dx": dx, "dy": dy},
            )
            self.event_handler_chain.process_event(event)

    def fixed_put(self, widget, x, y):
        self.fixed.put(widget, x, y)
        widget.x = x
        widget.y = y

    def fixed_move(self, widget, x, y):
        self.fixed.move(widget, x, y)
        widget.x = x
        widget.y = y

    def get_widget_at_position(self, x, y):
        """Gets the component at the specified position"""
        child = self.fixed.get_first_child()
        while child:
            # Get component position and size
            child_x, child_y = self.fixed.get_child_position(child)
            child_width = child.get_allocated_width()
            child_height = child.get_allocated_height()

            # Check if click is within component bounds
            if is_point_in_rect(x, y, child_x, child_y, child_width, child_height):
                return child

            child = child.get_next_sibling()
        return None

    def global_to_local_coords(self, widget, global_x, global_y):
        """Converts global coordinates to widget internal coordinates"""
        widget_x, widget_y = self.fixed.get_child_position(widget)
        return global_x - widget_x, global_y - widget_y

    def handle_widget_interaction(self, widget, x, y, n_press=1):
        """Handles widget interaction - supports double-click detection"""
        logger.debug(
            f"Handle widget interaction: {type(widget).__name__}, position({x:.1f}, {y:.1f}), click count={n_press}"
        )

        # Convert to widget internal coordinates for edit state check
        local_x, local_y = self.global_to_local_coords(widget, x, y)

        # Check if widget has edit decorator and should keep edit state
        should_keep_editing = False
        if hasattr(widget, "should_keep_editing_on_click"):
            should_keep_editing = widget.should_keep_editing_on_click(local_x, local_y)
            logger.debug(f"Widget edit status query result: {should_keep_editing}")

        if should_keep_editing:
            # If it should keep editing state, don't change selection state, and don't trigger bring to front
            logger.debug(
                "Keep editing state, skip selection logic and bring to front operation"
            )
            # Set skip flag to avoid breaking edit state with delayed bring to front
            widget._skip_delayed_bring_to_front = True
            return  # Return directly, do not execute subsequent selection and bring to front logic
        else:
            # Normal selection logic
            # Unselect other widgets
            self.clear_all_selections()

            # Select current widget
            if hasattr(widget, "set_selected"):
                widget.set_selected(True)
                logger.debug("Set widget to selected state")

        # Selection brings to front - using delayed method
        # Clear skip flag (if it exists), ensure normal bring to front works
        if hasattr(widget, "_skip_delayed_bring_to_front"):
            delattr(widget, "_skip_delayed_bring_to_front")
            logger.debug("Clear skip delayed bring to front flag")

        self.schedule_bring_to_front(widget)

        # Convert to widget internal coordinates
        local_x, local_y = self.global_to_local_coords(widget, x, y)
        logger.debug(f"Convert to local coordinates: ({local_x:.1f}, {local_y:.1f})")

        # Handle double-click event
        if n_press == 2:
            logger.debug("Double click detected")
            # When double-clicking, mark widget to avoid delayed bring to front operation
            if not hasattr(widget, "_skip_delayed_bring_to_front"):
                widget._skip_delayed_bring_to_front = True
                logger.debug("Mark widget to skip delayed bring to front operation")

            if hasattr(widget, "on_widget_double_clicked"):
                widget.on_widget_double_clicked(local_x, local_y)
            # Double click does not trigger bring to front when entering edit, to avoid interference with edit state
            logger.debug("Double click completed, skip bring to front operation")
            return

        # Record the operation to be performed, but do not execute immediately
        self.selected_widget = widget
        self.interaction_start_x = x
        self.interaction_start_y = y

        # Check if it's a resize area
        if hasattr(widget, "check_resize_direction"):
            resize_direction = widget.check_resize_direction(local_x, local_y)
            logger.debug(f"Check resize direction: {resize_direction}")
            if resize_direction:
                # When starting to resize, if the widget is in edit state, force exit edit
                if hasattr(widget, "should_keep_editing_on_click"):
                    # This means the widget has an edit decorator, force trigger selection change to exit edit
                    self.clear_all_selections()
                    widget.set_selected(True)
                    logger.debug("When resizing, force exit edit state")

                self.pending_resize_direction = resize_direction
                logger.debug("Prepare resize operation")
                return

        # Otherwise, prepare for drag
        self.pending_resize_direction = None
        logger.debug("Prepare drag operation")

        # Call widget's click callback
        if hasattr(widget, "on_widget_clicked"):
            widget.on_widget_clicked(local_x, local_y)

    def on_window_mouse_released(self, controller, n_press, x, y):
        """Window-level mouse release event"""
        button = controller.get_current_button()
        logger.debug(f"Mouse released: position({x:.1f}, {y:.1f}), button={button}")

        # Use event handler chain in mapping mode
        if self.current_mode == self.MAPPING_MODE:
            logger.debug(
                "In mapping mode, use event handler chain to handle mouse release"
            )

            # Create Key object for mouse button
            mouse_key = key_registry.create_mouse_key(button)

            # Create input event
            event = InputEvent(
                event_type="mouse_release",
                key=mouse_key,
                button=button,
                position=(int(x), int(y)),
                raw_data={"controller": controller, "n_press": n_press, "x": x, "y": y},
            )

            # Process with event handler chain
            handled = self.event_handler_chain.process_event(event)
            if handled:
                logger.debug("Mouse release event handled by event handler chain")
                return True
            else:
                logger.debug("Mouse release event not handled by any event handler")
            return

        # Mouse release handling in edit mode, delegate to workspace_manager
        self.workspace_manager.handle_mouse_release(controller, n_press, x, y)

    def start_widget_drag(self, widget, x, y):
        """Starts dragging widget"""
        self.dragging_widget = widget
        self.drag_start_x = x
        self.drag_start_y = y

        # Bring widget to front when dragging - using safe method
        self.bring_widget_to_front_safe(widget)

    def start_widget_resize(self, widget, x, y, direction):
        """Starts resizing widget"""
        self.resizing_widget = widget
        self.resize_start_x = x
        self.resize_start_y = y
        self.resize_direction = direction

        if hasattr(widget, "start_resize"):
            local_x, local_y = self.global_to_local_coords(widget, x, y)
            widget.start_resize(local_x, local_y, direction)

    def handle_widget_drag(self, x, y):
        """Handles widget dragging"""
        if not self.dragging_widget:
            return

        dx = x - self.drag_start_x
        dy = y - self.drag_start_y

        # Get current position
        current_x, current_y = self.fixed.get_child_position(self.dragging_widget)
        new_x = current_x + dx
        new_y = current_y + dy

        # Limit within window bounds
        widget_bounds = self.dragging_widget.get_widget_bounds()
        window_width = self.get_allocated_width()
        window_height = self.get_allocated_height()

        new_x = max(0, min(new_x, window_width - widget_bounds[2]))
        new_y = max(0, min(new_y, window_height - widget_bounds[3]))

        # Move widget
        self.fixed_move(self.dragging_widget, new_x, new_y)

        # Update drag start point
        self.drag_start_x = x
        self.drag_start_y = y

    def handle_widget_resize(self, x, y):
        """Handles widget resizing"""
        if not self.resizing_widget or not hasattr(
            self.resizing_widget, "handle_resize_motion"
        ):
            return

        self.resizing_widget.handle_resize_motion(x, y)

    def bring_widget_to_front(self, widget):
        """Brings widget to front - using simple safe method"""
        # Simple method: only bring to front when dragging starts, to avoid bringing to front when selecting
        pass

    def bring_widget_to_front_safe(self, widget):
        """Safely brings widget to front - only used when dragging"""
        try:
            # Get current position
            x, y = self.fixed.get_child_position(widget)

            # Remove and re-add (only do this safely when dragging)
            self.fixed.remove(widget)
            self.fixed_put(widget, x, y)

            # Ensure drag state is correct
            self.dragging_widget = widget

        except Exception as e:
            logger.error(f"Error bringing widget to front: {e}")

    def schedule_bring_to_front(self, widget):
        """Delays bringing to front - to avoid state issues with immediate operations"""
        # Use GLib.idle_add to delay the bring to front operation
        GLib.idle_add(self._delayed_bring_to_front, widget)

    def _delayed_bring_to_front(self, widget):
        """Delays the bring to front operation"""
        try:
            # Check if delayed bring to front should be skipped (double-click to enter edit)
            if (
                hasattr(widget, "_skip_delayed_bring_to_front")
                and widget._skip_delayed_bring_to_front
            ):
                logger.debug(
                    "Skip delayed bring to front operation (widget is editing)"
                )
                # Clear flag
                delattr(widget, "_skip_delayed_bring_to_front")
                return False

            # Check if widget still exists
            if widget.get_parent() != self.fixed:
                return False

            # Get current position
            x, y = self.fixed.get_child_position(widget)

            # Save selection state
            selected_state = getattr(widget, "is_selected", False)

            # Remove and re-add
            self.fixed.remove(widget)
            self.fixed_put(widget, x, y)

            # Restore selection state (only call if state actually changed, to avoid triggering unnecessary signals)
            if hasattr(widget, "set_selected"):
                current_state = getattr(widget, "is_selected", False)
                if current_state != selected_state:
                    widget.set_selected(selected_state)
                    logger.debug(f"Bring to front: {current_state} -> {selected_state}")
                else:
                    logger.debug(f"Bring to front: {selected_state}")

        except Exception as e:
            logger.error(f"Error bringing widget to front: {e}")

        return False  # Do not repeat execution

    # def update_cursor_for_position(self, x, y):
    #     """Updates mouse cursor based on position - moved to workspace_manager"""
    #     pass  # This method has been moved to workspace_manager, keep empty method for compatibility

    # def get_cursor_name_for_resize_direction(self, direction):
    #     """Gets mouse cursor name based on resize direction"""
    #     cursor_map = {
    #         "se": "se-resize",
    #         "sw": "sw-resize",
    #         "ne": "ne-resize",
    #         "nw": "nw-resize",
    #         "e": "e-resize",
    #         "w": "w-resize",
    #         "s": "s-resize",
    #         "n": "n-resize",
    #     }
    #     return cursor_map.get(direction, "default")

    def clear_all_selections(self):
        """Clears the selected state of all components"""
        self.workspace_manager.clear_all_selections()

    def set_all_widgets_mapping_mode(self, mapping_mode: bool):
        """Sets the mapping mode for all widgets"""
        widget_count = 0
        child = self.fixed.get_first_child()
        while child:
            if hasattr(child, "set_mapping_mode"):
                child.set_mapping_mode(mapping_mode)
                widget_count += 1
            child = child.get_next_sibling()

        mode_name = "mapping" if mapping_mode else "edit"
        logger.debug(f"Set {widget_count} widgets to {mode_name} mode")

    def create_widget_at_position(self, widget: "BaseWidget", x: int, y: int):
        """Creates a component at the specified position"""
        # Place component directly at the specified position
        self.fixed_put(widget, x, y)

        # Check if it's a multi-key mapping component (e.g., DirectionalPad)
        if hasattr(widget, "get_all_key_mappings"):
            # Register all keys for multi-key mapping components
            key_mappings = widget.get_all_key_mappings()
            success_count = 0
            total_count = len(key_mappings)

            for key_combination, direction in key_mappings.items():
                success = self.register_widget_key_mapping(widget, key_combination)
                if success:
                    success_count += 1
                    logger.debug(
                        f"Register multi-key mapping: {key_combination} -> {type(widget).__name__}({direction})"
                    )
                else:
                    logger.debug(
                        f"Register multi-key mapping failed: {key_combination} -> {direction}"
                    )

            logger.debug(
                f"Multi-key component {type(widget).__name__} registered: {success_count}/{total_count}"
            )

        elif hasattr(widget, "final_keys") and widget.final_keys:
            # Traditional single-key mapping components
            # Register directly using KeyCombination objects
            for key_combination in widget.final_keys:
                success = self.register_widget_key_mapping(widget, key_combination)
                if success:
                    logger.debug(
                        f"Auto register component default key mapping: {key_combination} -> {type(widget).__name__}"
                    )
                    # Update component display text to reflect registered keys
                    if hasattr(widget, "text") and not widget.text:
                        widget.text = str(key_combination)
                else:
                    logger.debug(
                        f"Register component default key mapping failed: {key_combination}"
                    )
        else:
            logger.debug(
                f"Component {type(widget).__name__} has no default key, skip auto registration"
            )

    def on_clear_widgets(self, button: Gtk.Button | None):
        """Clears all components"""
        widgets_to_delete = []
        child = self.fixed.get_first_child()
        while child:
            widgets_to_delete.append(child)
            child = child.get_next_sibling()

        # Clean up key mappings for each widget, then remove from UI
        for widget in widgets_to_delete:
            # Clean up widget's key mappings
            self.unregister_widget_key_mapping(widget)
            # Remove widget from UI
            self.fixed.remove(widget)
            widget.on_delete()
            logger.debug(
                f"Clear widget {type(widget).__name__}(id={id(widget)}) and its key mapping"
            )

        # Clear interaction states
        self.workspace_manager.dragging_widget = None
        self.workspace_manager.resizing_widget = None

        logger.debug(
            f"Clear all components, {len(widgets_to_delete)} widgets and their key mappings"
        )

    def get_physical_keyval(self, keycode):
        """Gets the standard keyval for the physical key (independent of modifier keys)"""
        try:
            display = self.get_display()
            if display:
                success, keyval, _, _, _ = display.translate_key(
                    keycode=keycode, state=Gdk.ModifierType(0), group=0
                )
                if success:
                    return Gdk.keyval_to_upper(keyval)
        except Exception as e:
            logger.debug(f"Failed to get physical keyval: {e}")
        return 0

    def on_global_key_press(self, controller, keyval, keycode, state):
        """Global keyboard event - supports dual mode, uses event handler chain"""
        # Special keys: mode switching and debug functions - these are directly judged by original keyval
        if keyval == Gdk.KEY_F1:
            # F1 switches between two modes
            if self.current_mode == self.EDIT_MODE:
                self.switch_mode(self.MAPPING_MODE)
            else:
                self.switch_mode(self.EDIT_MODE)
            return True
        # elif keyval == Gdk.KEY_F2:
        #     self.switch_mode(self.MAPPING_MODE)
        #     return True
        # elif keyval == Gdk.KEY_F3:
        #     # F3 displays current key mapping status
        #     self.print_key_mappings()
        #     return True
        # elif keyval == Gdk.KEY_F4:
        #     # F4 displays event handler status
        #     self.print_event_handlers_status()
        #     return True

        # Use event handler chain in mapping mode
        if self.current_mode == self.MAPPING_MODE:
            logger.debug("In mapping mode, use event handler chain to handle key event")

            # Get standard keyval for physical key
            physical_keyval = self.get_physical_keyval(keycode)
            if physical_keyval == 0:
                # If failed to get, fallback to original keyval
                physical_keyval = keyval
                logger.debug(f"Fallback to original keyval: {Gdk.keyval_name(keyval)}")

            # Process modifier keys themselves
            if self._is_modifier_key(keyval):
                main_key = key_registry.create_from_keyval(keyval)
            else:
                main_key = key_registry.create_from_keyval(physical_keyval)

            if main_key:
                # Collect modifier keys
                modifiers = []
                if state & Gdk.ModifierType.CONTROL_MASK:
                    ctrl_key = key_registry.get_by_name("Ctrl_L")
                    if ctrl_key:
                        modifiers.append(ctrl_key)
                if state & Gdk.ModifierType.ALT_MASK:
                    alt_key = key_registry.get_by_name("Alt_L")
                    if alt_key:
                        modifiers.append(alt_key)
                if state & Gdk.ModifierType.SHIFT_MASK:
                    shift_key = key_registry.get_by_name("Shift_L")
                    if shift_key:
                        modifiers.append(shift_key)
                if state & Gdk.ModifierType.SUPER_MASK:
                    super_key = key_registry.get_by_name("Super_L")
                    if super_key:
                        modifiers.append(super_key)

                # Create input event
                event = InputEvent(
                    event_type="key_press",
                    key=main_key,
                    modifiers=modifiers,
                    raw_data={
                        "controller": controller,
                        "keyval": keyval,
                        "keycode": keycode,
                        "state": state,
                    },
                )

                # Process with event handler chain
                handled = self.event_handler_chain.process_event(event)
                if handled:
                    logger.debug("Key event handled by event handler chain")
                    return True
                else:
                    logger.debug("Key event not handled by any event handler")

        # General key handling in edit mode or mapping mode
        if keyval == Gdk.KEY_Escape:
            if self.current_mode == self.EDIT_MODE:
                # Edit mode: cancel all selections
                self.clear_all_selections()
            else:
                # Mapping mode: do nothing for now, or switch back to edit mode
                logger.debug("In mapping mode, press ESC key")
            return True

        # Only handle edit-related keys in edit mode
        if self.current_mode == self.EDIT_MODE:
            if keyval == Gdk.KEY_Delete:
                # Delete key deletes selected widget
                self.workspace_manager.delete_selected_widgets()
                return True

        return False

    def delete_selected_widgets(self):
        """Deletes all selected widgets"""
        self.workspace_manager.delete_selected_widgets()

    # ===================Hint Information Methods====================

    def show_notification(self, text: str):
        """Shows a hint message with fade-out effect"""
        self.notification_label.set_label(text)

        # Stop any ongoing animations
        if (
            hasattr(self, "_notification_fade_out_timer")
            and self._notification_fade_out_timer > 0
        ):
            GLib.source_remove(self._notification_fade_out_timer)
        if hasattr(self, "_notification_animation"):
            self._notification_animation.reset()

        # Fade-in animation
        self.notification_box.set_opacity(0)
        animation_target = Adw.PropertyAnimationTarget.new(
            self.notification_box, "opacity"
        )
        self._notification_animation = Adw.TimedAnimation.new(
            self.notification_box, 0.0, 1.0, 300, animation_target
        )
        self._notification_animation.set_easing(Adw.Easing.LINEAR)
        self._notification_animation.play()

        # Plan fade-out
        self._notification_fade_out_timer = GLib.timeout_add(
            1500, self._fade_out_notification
        )

    def _fade_out_notification(self):
        """Executes fade-out animation"""
        animation_target = Adw.PropertyAnimationTarget.new(
            self.notification_box, "opacity"
        )
        self._notification_animation = Adw.TimedAnimation.new(
            self.notification_box, 1.0, 0.0, 500, animation_target
        )
        self._notification_animation.set_easing(Adw.Easing.LINEAR)
        self._notification_animation.play()
        self._notification_fade_out_timer = 0
        return GLib.SOURCE_REMOVE

    # ===================Dual Mode System Methods====================

    def _on_mode_changed(self, widget, pspec):
        """Callback when mode property changes"""
        new_mode = self.current_mode
        logger.debug(f"Mode changed to: {new_mode}")

        # Notify all widgets to switch drawing mode
        mapping_mode = new_mode == self.MAPPING_MODE
        self.set_all_widgets_mapping_mode(mapping_mode)

        # Adjust UI state based on new mode
        if new_mode == self.MAPPING_MODE:
            # Enter mapping mode: cancel all selections, disable edit functions
            self.clear_all_selections()
            logger.debug("Enter mapping mode, edit function disabled")

            self.show_notification(_("Mapping Mode (F1: Switch Mode)"))

            # Add more UI adjustments for mapping mode here
            # e.g., change window title, display status indicator, etc.
            self.set_title(f"{APP_TITLE} - Mapping Mode (F1: Switch Mode)")
            self.set_cursor_from_name("default")

            # Display mapping mode help information
            logger.debug("Enter mapping mode!")
            logger.debug(
                f"- Press configured key combination to trigger corresponding widget action"
            )
            logger.debug("- F1: Switch to edit mode")
            logger.debug("- ESC: Other operations")

        else:
            # Enter edit mode: restore edit functions
            logger.debug("Enter edit mode, edit function enabled")
            self.show_notification(_("Edit Mode (F1: Switch Mode)"))
            self.set_title(f"{APP_TITLE} - Edit Mode (F1: Switch Mode)")

            # Display edit mode help information
            logger.debug("Enter edit mode!")
            logger.debug("- Right click on blank area: create widget")
            logger.debug("- Double click widget: edit key mapping")
            logger.debug("- Left click drag: move widget")
            logger.debug("- Delete: delete selected widget")
            logger.debug("- F1: Switch to mapping mode")

    def switch_mode(self, new_mode):
        """Switches mode"""
        if new_mode not in [self.EDIT_MODE, self.MAPPING_MODE]:
            logger.debug(f"Invalid mode: {new_mode}")
            return False

        if self.current_mode == new_mode:
            logger.debug(f"Already in {new_mode} mode")
            return True

        logger.debug(f"Switch mode: {self.current_mode} -> {new_mode}")

        # Use property system to set mode, which will trigger _on_mode_changed callback
        self.set_property("current-mode", new_mode)

        return True

    def format_key_combination(self, keyval, state) -> KeyCombination:
        """Formats key event into KeyCombination"""
        keys = []

        # Add modifier keys
        if state & Gdk.ModifierType.CONTROL_MASK:
            ctrl_key = key_registry.get_by_name("Ctrl")
            if ctrl_key:
                keys.append(ctrl_key)
        if state & Gdk.ModifierType.ALT_MASK:
            alt_key = key_registry.get_by_name("Alt")
            if alt_key:
                keys.append(alt_key)
        if state & Gdk.ModifierType.SHIFT_MASK:
            shift_key = key_registry.get_by_name("Shift")
            if shift_key:
                keys.append(shift_key)
        if state & Gdk.ModifierType.SUPER_MASK:
            super_key = key_registry.get_by_name("Super")
            if super_key:
                keys.append(super_key)

        # Get main key
        main_key = key_registry.create_from_keyval(keyval, state)
        if main_key:
            keys.append(main_key)

        return KeyCombination(keys)

    def register_widget_key_mapping(
        self, widget, key_combination: KeyCombination
    ) -> bool:
        """Registers widget's key mapping"""
        # Automatically read widget's reentrant attribute
        reentrant = getattr(widget, 'IS_REENTRANT', False)
        return key_mapping_manager.subscribe(widget, key_combination, reentrant=reentrant)

    def unregister_widget_key_mapping(self, widget) -> bool:
        """Unsubscribes all key mappings for a widget"""
        return key_mapping_manager.unsubscribe(widget)

    def unregister_single_widget_key_mapping(
        self, widget, key_combination: KeyCombination
    ) -> bool:
        """Unsubscribes a single key mapping for a widget"""
        return key_mapping_manager.unsubscribe_key(widget, key_combination)

    def get_widget_key_mapping(self, widget) -> list[KeyCombination]:
        """Gets the list of key mappings for a specified widget"""
        return key_mapping_manager.get_subscriptions(widget)

    def print_key_mappings(self):
        """Prints all current key mappings (for debugging)"""
        key_mapping_manager.print_mappings()

    def clear_all_key_mappings(self):
        """Clears all key mappings"""
        return key_mapping_manager.clear()

    def on_global_key_release(self, controller, keyval, keycode, state):
        """Global key release event - uses event handler chain"""
        if self.current_mode == self.MAPPING_MODE:
            logger.debug(
                "In mapping mode, use event handler chain to handle key release"
            )

            # Get standard keyval for physical key
            physical_keyval = self.get_physical_keyval(keycode)
            if physical_keyval == 0:
                # If failed to get, fallback to original keyval
                physical_keyval = keyval
                logger.debug(
                    f"Release fallback to original keyval: {Gdk.keyval_name(keyval)}"
                )

            # Process modifier keys themselves
            if self._is_modifier_key(keyval):
                main_key = key_registry.create_from_keyval(keyval)
            else:
                main_key = key_registry.create_from_keyval(physical_keyval)

            if main_key:
                # Collect modifier keys
                modifiers = []
                if state & Gdk.ModifierType.CONTROL_MASK:
                    ctrl_key = key_registry.get_by_name("Ctrl_L")
                    if ctrl_key:
                        modifiers.append(ctrl_key)
                if state & Gdk.ModifierType.ALT_MASK:
                    alt_key = key_registry.get_by_name("Alt_L")
                    if alt_key:
                        modifiers.append(alt_key)
                if state & Gdk.ModifierType.SHIFT_MASK:
                    shift_key = key_registry.get_by_name("Shift_L")
                    if shift_key:
                        modifiers.append(shift_key)
                if state & Gdk.ModifierType.SUPER_MASK:
                    super_key = key_registry.get_by_name("Super_L")
                    if super_key:
                        modifiers.append(super_key)

                # Create input event
                event = InputEvent(
                    event_type="key_release",
                    key=main_key,
                    modifiers=modifiers,
                    raw_data={
                        "controller": controller,
                        "keyval": keyval,
                        "keycode": keycode,
                        "state": state,
                    },
                )

                # Process with event handler chain
                handled = self.event_handler_chain.process_event(event)
                if handled:
                    logger.debug("Key release event handled by event handler chain")
                    return True
                else:
                    logger.debug("Key release event not handled by any event handler")

        return False

    def _is_modifier_key(self, keyval):
        """Checks if it's a modifier key"""
        modifier_keys = {
            Gdk.KEY_Control_L,
            Gdk.KEY_Control_R,
            Gdk.KEY_Alt_L,
            Gdk.KEY_Alt_R,
            Gdk.KEY_Shift_L,
            Gdk.KEY_Shift_R,
            Gdk.KEY_Super_L,
            Gdk.KEY_Super_R,
            Gdk.KEY_Meta_L,
            Gdk.KEY_Meta_R,
            Gdk.KEY_Hyper_L,
            Gdk.KEY_Hyper_R,
        }
        return keyval in modifier_keys

    # def print_event_handlers_status(self):
    #     """Prints event handler status (for debugging)"""
    #     print(f"\n[DEBUG] ==================Event handler status==================")
    #     print(
    #         f"[DEBUG] Event handler chain status: {'Enabled' if self.event_handler_chain.enabled else 'Disabled'}"
    #     )

    #     handlers_info = self.event_handler_chain.get_handlers_info()
    #     for info in handlers_info:
    #         status = "Enabled" if info["enabled"] else "Disabled"
    #         print(f"[DEBUG] - {info['name']}: Priority={info['priority']}, Status={status}")

    #     # Display default handler's mappings
    #     print(
    #         f"[DEBUG] Default handler key mappings: {list(self.default_handler.key_mappings.keys())}"
    #     )
    #     print(
    #         f"[DEBUG] Default handler mouse mappings: {list(self.default_handler.mouse_mappings.keys())}"
    #     )
    #     print(f"[DEBUG] ================================================\n")
