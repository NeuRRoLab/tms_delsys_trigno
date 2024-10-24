# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['tms_trigno.py'],
    pathex=['.'],
    binaries=[],
    datas=[('trignoSetup.py', '.'), ('AeroPy','AeroPy'), ('QT','QT'), ('lib','lib')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TMS Trigno',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon = 'Logo.ico'
)
