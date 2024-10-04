# -*- mode: python ; coding: utf-8 -*-

from argparse import ArgumentParser
from platform import system

parser = ArgumentParser()
parser.add_argument("--binary", action="store_true")
options = parser.parse_args()

a = Analysis(
    ["waydroid-helper"],
    binaries=[
        ('usr/bin/fakeroot-real', 'usr/bin'),
        ('usr/bin/fakeroot', 'usr/bin'),
        ('usr/bin/faked', 'usr/bin'),
        ('usr/lib/libfakeroot', 'usr/lib/libfakeroot'),
        ('usr/bin/waydroid-cli', 'usr/bin')
    ],
    pathex=["usr/share/waydroid-helper"],
    datas=[
        ("LICENSE", "."), 
        ("usr/share/applications", "usr/share/applications"),
        ("usr/share/glib-2.0", "usr/share/glib-2.0"),
        ("usr/share/icons", "usr/share/icons"),
        ("usr/share/locale", "usr/share/locale"),
        ("usr/share/metainfo", "usr/share/metainfo"),
        ("usr/share/polkit-1", "usr/share/polkit-1"),
        ("usr/share/waydroid-helper/data", "usr/share/waydroid-helper/data"),
        ("usr/share/waydroid-helper/waydroid-helper.gresource", "usr/share/waydroid-helper/"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={
        "gi": {
            "icons": ["Adwaita"],
            "themes": ["Adwaita"],
            "module-versions": {"Gtk": "4.0"},
        }
    },
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

if system() == "Linux":
    if not options.binary:
        exe = EXE(
            pyz,
            a.scripts,
            [],
            exclude_binaries=True,
            name="waydroid-helper",
            debug=False,
            bootloader_ignore_signals=False,
            strip=False,
            upx=True,
            console=False,
            disable_windowed_traceback=False,
            argv_emulation=False,
            target_arch=None,
            codesign_identity=None,
            entitlements_file=None,
        )
        coll = COLLECT(
            exe,
            a.binaries,
            a.datas,
            strip=False,
            upx=True,
            upx_exclude=[],
            name="waydroid-helper",
        )
    else:
        exe = EXE(
            pyz,
            a.scripts,
            a.binaries,
            a.datas,
            [],
            name="waydroid-helper",
            debug=False,
            bootloader_ignore_signals=False,
            strip=False,
            upx=True,
            upx_exclude=[],
            runtime_tmpdir=None,
            console=False,
            disable_windowed_traceback=False,
            argv_emulation=False,
            target_arch=None,
            codesign_identity=None,
            entitlements_file=None,
        )
