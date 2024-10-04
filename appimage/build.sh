#!/bin/bash

script_dir="$( dirname "$( readlink -f "$0" )" )"
cd $script_dir/..
meson setup -Dbuild_appimage=true  --prefix /usr build && DESTDIR=../AppDir ninja install -C build

if [ ! -d "$script_dir/../AppDir" ]; then
    echo "Directory $script_dir/../AppDir does not exist."
    exit 1
fi

cd $script_dir/../AppDir
ln -sf $script_dir/.env.sample .env
ln -sf $script_dir/build.py .
ln -sf $script_dir/build.spec .
ln -sf $script_dir/../requirements.txt .
ln -sf $script_dir/../COPYING LICENSE
mv usr/bin/waydroid-helper .
python3 build.py