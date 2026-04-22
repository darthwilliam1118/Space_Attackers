# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Space Attackers — self-contained Windows .exe"""

import os

ROOT = os.path.dirname(os.path.abspath(SPEC))  # noqa: F821  (SPEC injected by PyInstaller)

a = Analysis(
    [os.path.join(ROOT, "src", "__main__.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "assets"), "assets"),
    ],
    hiddenimports=[
        "arcade",
        "arcade.gl",
        "arcade.gl.enums",
        "pyglet",
        "pyglet.gl",
        "pyglet.image.codecs",
        "pyglet.image.codecs.png",
        "pyglet.media",
        "pyglet.media.codecs",
        "pyglet.media.codecs.wave",
        "pyglet.libs.win32",
        "pyglet.libs.win32.com",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Space_Attackers",
    icon=os.path.join(ROOT, "assets", "images", "sa-icon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # windowed — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
