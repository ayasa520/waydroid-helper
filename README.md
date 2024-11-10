# Waydroid Helper

Waydroid Helper is a graphical user interface application written in Python using PyGObject. It provides a user-friendly way to configure Waydroid and install extensions, including Magisk and ARM translation.

## Features

- Configure Waydroid settings
- Install extensions for Waydroid
  - [Magisk](https://github.com/HuskyDG/magisk-files/)
  - [libhoudini](https://github.com/supremegamers/vendor_intel_proprietary_houdini)
  - [libndk](https://github.com/supremegamers/vendor_google_proprietary_ndk_translation-prebuilt)
  - [OpenGapps](https://sourceforge.net/projects/opengapps/)
  - [MindTheGapps](https://github.com/MindTheGapps)
  - [MicroG](https://microg.org/)
  - [SmartDock](https://github.com/axel358/smartdock)

## Installation

### AUR

For Arch users, Waydroid Helper is available in the AUR:
```
yay -S waydroid-helper
```

### Manual Installation

For manual installation, you'll need to install the dependencies and build the project using Meson.

#### Arch-based Distributions
1. Install dependencies:

    ```bash
    sudo pacman -S gtk4 libadwaita meson ninja
    ```


2. Clone the repository:
    ```
    git clone https://github.com/ayasa520/waydroid-helper.git
    cd waydroid-helper
    ```
3. Build and install using Meson:
    ```
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    meson setup --prefix /usr build
    sudo ninja -C build install

    # Uninstall waydroid helper
    # sudo ninja -C build uninstall
    ```

#### Debian-based Distributions
1. Install dependencies:

    ```bash
    sudo apt install libgtk-4-1 libgtk-4-dev libadwaita-1-dev libadwaita-1-0 libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-4.0 gir1.2-adw-1 gettext ninja-build fakeroot attr libcap-dev libdbus-1-dev desktop-file-utils software-properties-common -y
    ```


2. Clone the repository:
    ```
    git clone https://github.com/ayasa520/waydroid-helper.git
    cd waydroid-helper
    ```
3. Build and install using Meson:
    ```
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install meson
    pip install -r requirements.txt
    meson setup --prefix /usr build
    sudo ninja -C build install

    # Uninstall waydroid helper
    # sudo ninja -C build uninstall
    ```

## Screenshots

![](./assets/img/README/1_en.png)
![](./assets/img/README/2_en.png)
![](./assets/img/README/3_en.png)
