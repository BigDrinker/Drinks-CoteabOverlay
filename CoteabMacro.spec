# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules
from pathlib import Path

project = Path(SPECPATH)

datas = [
    (str(project / 'frontend' / 'dist'), 'lib/dist'),
    (str(project / 'lib'), 'lib'),
    (str(project / 'images'), 'images'),
    (str(project / 'paths'), 'paths'),
    (str(project / 'crafting_files_do_not_open'), 'crafting_files_do_not_open'),
    (str(project / 'config.json'), '.'),
    (str(project / 'overlay_settings.json'), '.'),
    (str(project / 'LICENSE.txt'), '.'),
    (str(project / 'CHANGELOG.md'), '.'),
    (str(project / 'INSTALL.txt'), '.'),
]

binaries = []
hiddenimports = ['native_overlay_process']

for package in ('webview', 'winocr', 'autoit'):
    try:
        package_datas, package_binaries, package_hidden = collect_all(package)
        datas += package_datas
        binaries += package_binaries
        hiddenimports += package_hidden
    except Exception:
        pass

for package in ('biome_tracker',):
    hiddenimports += collect_submodules(package)

a = Analysis(
    ['main.py'],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='Coteab Macro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project / 'lib' / 'official_release.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Coteab Macro',
)
