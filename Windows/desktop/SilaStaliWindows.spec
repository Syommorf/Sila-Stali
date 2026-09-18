# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.'), ('window_icon.png', '.'), ('module_laser.png', '.'), ('module_bender.png', '.'), ('module_mech.png', '.'), ('module_weld.png', '.'), ('module_store.png', '.'), ('module_laser_hub.png', '.'), ('module_bender_hub.png', '.'), ('module_mech_hub.png', '.'), ('module_weld_hub.png', '.'), ('module_store_hub.png', '.'), ('module_laser_square.png', '.'), ('module_bender_square.png', '.'), ('module_mech_square.png', '.'), ('module_weld_square.png', '.'), ('module_store_square.png', '.'), ('module_chief.png', '.'), ('module_chief_hub.png', '.'), ('module_chief_square.png', '.'), ('module_laser_grid.png', '.'), ('module_bender_grid.png', '.'), ('module_mech_grid.png', '.'), ('module_weld_grid.png', '.'), ('module_store_grid.png', '.'), ('module_chief_grid.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SilaStaliWindows',
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
    icon=['icon.ico'],
)
