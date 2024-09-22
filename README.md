# Waydroid Helper

Waydroid Helper is a graphical user interface application written in Python using PyGObject. It provides a user-friendly way to configure Waydroid and install extensions, including Magisk and ARM translation.

## Features

- Configure Waydroid settings
- Install extensions for Waydroid
  - Magisk
  - ARM translation
  - And more...

## Installation

### AUR

For Arch users, Waydroid Helper is available in the AUR:
```
yay -S waydroid-helper
```

### Manual Installation

For manual installation, you'll need to install the dependencies and build the project using Meson.

#### Dependencies

On Arch Linux, install the following packages:

- python
- python-bidict
- python-httpx
- python-gobject (>=3.50.0)
- python-yaml
- pywayland
- python-cairo
- gtk4
- libadwaita
- python-aiofiles

Note: Package names may differ on other distributions. Please refer to your distribution's package manager to find the equivalent packages.

#### Building and Installing

1. Clone the repository:
```
git clone https://github.com/ayasa520/waydroid-helper.git
cd waydroid-helper
```
2. Build and install using Meson:
```
meson setup --prefix /usr build
ninja -C build install
```

## Screenshots

![](./assets/img/README/1_en.png)
![](./assets/img/README/2_en.png)
![](./assets/img/README/3_en.png)