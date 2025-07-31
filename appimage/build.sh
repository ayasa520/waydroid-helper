#!/usr/bin/env bash

set -euo pipefail

script_dir="$(dirname "$(readlink -f "$0")")"
project_root="$(readlink -f "$script_dir/..")"
build_dir="$project_root/build"
appdir="$project_root/AppDir"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to handle errors
handle_error() {
    log "Error occurred on line $1"
    exit 1
}

# Set up error handling
trap 'handle_error $LINENO' ERR

# Build the project
log "Building project..."
cd "$project_root"
meson setup -Dbuild_appimage=true --prefix /usr "$build_dir" || { log "Meson setup failed"; exit 1; }
DESTDIR="$appdir" ninja install -C "$build_dir" || { log "Ninja install failed"; exit 1; }

# Build and install adb from nmeum/android-tools
log "Building ADB from nmeum/android-tools..."
cd "$appdir"
mkdir -p usr/bin

# Detect architecture
ARCH=$(uname -m)
log "Detected architecture: $ARCH"

# Create temporary build directory
BUILD_DIR=$(mktemp -d)
cd "$BUILD_DIR"

# Download android-tools source tarball
ANDROID_TOOLS_VERSION="34.0.5"
TARBALL_URL="https://github.com/nmeum/android-tools/releases/download/${ANDROID_TOOLS_VERSION}/android-tools-${ANDROID_TOOLS_VERSION}.tar.xz"

log "Downloading android-tools source tarball..."
if ! wget -O "android-tools-${ANDROID_TOOLS_VERSION}.tar.xz" "$TARBALL_URL"; then
    log "Failed to download android-tools source"
    exit 1
fi

# Extract tarball
log "Extracting android-tools source..."
if ! tar -xf "android-tools-${ANDROID_TOOLS_VERSION}.tar.xz"; then
    log "Failed to extract android-tools source"
    exit 1
fi

cd "android-tools-${ANDROID_TOOLS_VERSION}"

# Create build directory
mkdir -p build
cd build

log "Configuring android-tools build..."
# Configure build with CMake
if ! cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$appdir/usr"; then
    log "Failed to configure android-tools build"
    exit 1
fi

log "Building ADB..."
# Build only adb (not all tools)
if ! make -j$(nproc) adb; then
    log "Failed to build ADB"
    exit 1
fi

# Install adb binary
log "Installing ADB binary..."
# Find adb binary in build directory
ADB_BINARY=$(find . -name "adb" -type f -executable | head -1)
if [ -n "$ADB_BINARY" ]; then
    log "Found ADB binary at: $ADB_BINARY"
    cp "$ADB_BINARY" "$appdir/usr/bin/adb"
    chmod +x "$appdir/usr/bin/adb"
    log "ADB installed successfully"
else
    log "Error: ADB binary not found after build"
    log "Contents of build directory:"
    find . -name "*adb*" -type f
    exit 1
fi

# Clean up
cd "$appdir"
rm -rf "$BUILD_DIR"

log "ADB built and installed successfully"


# Check if AppDir was created
if [ ! -d "$appdir" ]; then
    log "Directory $appdir does not exist."
    exit 1
fi

log "Building fakeroot..."
cd "$appdir"
rm -rf fakeroot
git clone https://salsa.debian.org/clint/fakeroot --depth=1
cd fakeroot
./bootstrap 
./configure --prefix=/usr --libdir=/usr/lib/libfakeroot --disable-static --with-ipc=sysv
make -j$(cat /proc/cpuinfo | awk '/^processor/{print $3}' | wc -l)
make DESTDIR=$appdir install-exec
mv $appdir/usr/bin/fakeroot $appdir/usr/bin/fakeroot-real
echo '#!/bin/bash
$APPDIR/usr/bin/fakeroot-real -l $APPDIR/usr/lib/libfakeroot/libfakeroot.so --faked $APPDIR/usr/bin/faked "$@"' > $appdir/usr/bin/fakeroot
chmod +x $appdir/usr/bin/fakeroot

# Create symbolic links and move files
log "Setting up AppDir..."
cd "$appdir"
ln -sf "$script_dir/.env.sample" .env
ln -sf "$script_dir/build.py" .
ln -sf "$script_dir/build.spec" .
ln -sf "$project_root/requirements.txt" .
ln -sf "$project_root/COPYING" LICENSE
# Copy hooks directory for PyInstaller
cp -r "$script_dir/hooks" . || { log "Failed to copy hooks directory"; exit 1; }
mv usr/bin/waydroid-helper . || { log "Failed to move waydroid-helper"; exit 1; }

# Run the Python build script
log "Running Python build script..."
python3 build.py

log "Build process completed successfully."
