# Key Mapping Guide for Waydroid Helper

## Overview

The key mapping feature in Waydroid Helper allows you to create custom keyboard and mouse controls for Android applications running in Waydroid. This powerful system enables you to map physical keyboard keys and mouse buttons to touch screen interactions, making mobile games and apps more accessible on desktop systems.

## Getting Started

### Opening the Key Mapping Interface

1. Launch Waydroid Helper
2. Navigate to the **Home** tab
3. In the **Key Mapper** section, click the **Open** button
4. A transparent overlay window will appear over your screen

### Interface Modes

The key mapping interface has two modes:

- **Edit Mode** (Default): Used for placing, configuring, and editing control widgets
- **Mapping Mode**: Used for actual gameplay with active key mappings

**Switch between modes**: Press `F1` to toggle between Edit Mode and Mapping Mode.

## Available Control Widgets

### 1. Single Click
- **Purpose**: Maps a key/mouse button to a single tap at a specific screen location
- **Use Case**: Menu buttons, simple interactions
- **Default Key**: None
- **Configuration**: Position the widget over the target area and assign a key

### 2. Fire Button
- **Purpose**: Designed for shooting games, works in conjunction with the Aim widget
- **Use Case**: Firing weapons in FPS games
- **Default Key**: Left Mouse Button
- **Special Feature**: Automatically activates when Aim widget is triggered

### 3. Directional Pad (D-Pad)
- **Purpose**: Virtual joystick for movement controls
- **Use Case**: Character movement in games
- **Default Keys**: W (up), A (left), S (down), D (right)
- **Configuration**: Resize to match the game's virtual joystick area

### 4. Aim Widget
- **Purpose**: Mouse look/aim control for FPS games
- **Use Case**: Camera control and aiming
- **Default Key**: None
- **Special Features**: 
  - Captures mouse movement for precise aiming
  - Works with Fire button for complete FPS control

### 5. Repeated Click
- **Purpose**: Automated rapid clicking
- **Use Case**: Auto-attack, rapid-fire actions
- **Operating Modes**:
  - **Long-press combo**: Continuous clicking while key is held
  - **Click after button**: Fixed number of clicks after key release
- **Configuration**: Adjustable click rate and count

### 6. Skill Casting
- **Purpose**: Advanced skill targeting with mouse control
- **Use Case**: MOBA games
- **Features**:
  - Mouse-guided skill direction
  - Configurable cast timing
  - Optional cancel button support

### 7. Macro Button
- **Purpose**: Execute complex command sequences
- **Use Case**: Combo moves, complex interactions
- **Supported Commands**:
  - `key_press <key1,key2,...>`: Press specific keys
  - `key_release <key1,key2,...>`: Release specific keys
  - `key_switch <key1,key2,...>`: Toggle key states
  - `click <x,y>`: Click at coordinates
  - `press <x,y>`: Touch down at coordinates
  - `release <x,y>`: Touch up at coordinates
  - `switch <x,y>`: Toggle between press and release at coordinates
  - `sleep <milliseconds>`: Delay execution
  - `release_all`: Release all currently pressed keys
  - `enter_staring`: Enter aiming mode
  - `exit_staring`: Exit aiming mode
  - `swipehold_radius <factor>`: Set dpad radius
  - `swipehold_radius_switch <factor>`: Switch between original and specified radius
  - `mouse`: Use current cursor position for coordinates

### 8. Right Click to Walk
- **Purpose**: Point-and-click movement
- **Use Case**: MOBA games

### 9. Cancel Casting
- **Purpose**: Interrupt ongoing skill casting
- **Use Case**: MOBA games

## Setting Up Key Mappings

### Adding Widgets

1. **Enter Edit Mode** (default when opening key mapper)
2. **Right-click** on an empty area to open the context menu
3. **Select a widget type** from the menu
4. **Position the widget** by dragging it to the desired location
5. **Resize if needed** by dragging the resize handles when selected

### Configuring Key Bindings

1. **Double-click** on any widget to enter key capture mode
2. **Press the desired key(s)** you want to map to this widget
3. The widget will display the assigned key combination

#### Supported Key Types
- **Keyboard keys**: Letters, numbers, function keys, modifiers
- **Mouse buttons**: Left, Right, Middle
- **Key combinations**: Multiple keys pressed together (e.g., Ctrl+A)

### Widget-Specific Configuration

Many widgets have additional settings accessible through their settings panel:

1. **Select a widget** in Edit Mode
2. **Click the settings button** (gear icon) that appears
3. **Adjust parameters** such as:
   - Click rates for Repeated Click
   - Circle radius for Skill Casting
   - Cast timing settings
   - Operating modes

## Using Key Mappings

### Activating Mappings

1. **Switch to Mapping Mode** by pressing `F1`
2. **Position your game window** behind the transparent overlay
3. **Use your configured keys** to control the game
4. The overlay will show minimal visual indicators
