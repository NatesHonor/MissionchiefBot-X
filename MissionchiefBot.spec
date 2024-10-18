# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=['C:\\Users\\natha\\PycharmProjects\\MissionchiefBot'],
    binaries=[],
    datas=[
        ('C:\\Users\\natha\\PycharmProjects\\MissionchiefBot\\config\\*', 'config'),
        ('C:\\Users\\natha\\PycharmProjects\\MissionchiefBot\\data\\*', 'data'),
        ('C:\\Users\\natha\\PycharmProjects\\MissionchiefBot\\scripts\\*', 'scripts'),
        ('C:\\Users\\natha\\PycharmProjects\\MissionchiefBot\\utils\\*', 'utils'),
        ('C:\\Users\\natha\\PycharmProjects\\MissionchiefBot\\clean.py', '.'),
        ('C:\\Users\\natha\\PycharmProjects\\MissionchiefBot\\functions.py', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['C:\\Users\\natha\\PycharmProjects\\MissionchiefBot\\build', 'C:\\Users\\natha\\PycharmProjects\\MissionchiefBot\\dist'],
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
    name='MissionchiefBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
