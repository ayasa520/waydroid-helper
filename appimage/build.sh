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
$APPDIR/_internal/usr/bin/fakeroot-real -l $APPDIR/_internal/usr/lib/libfakeroot/libfakeroot.so --faked $APPDIR/_internal/usr/bin/faked "$@"' > $appdir/usr/bin/fakeroot
chmod +x $appdir/usr/bin/fakeroot

# Create symbolic links and move files
log "Setting up AppDir..."
cd "$appdir"
ln -sf "$script_dir/.env.sample" .env
ln -sf "$script_dir/build.py" .
ln -sf "$script_dir/build.spec" .
ln -sf "$project_root/requirements.txt" .
ln -sf "$project_root/COPYING" LICENSE
mv usr/bin/waydroid-helper . || { log "Failed to move waydroid-helper"; exit 1; }

# Run the Python build script
log "Running Python build script..."
python3 build.py

log "Build process completed successfully."
