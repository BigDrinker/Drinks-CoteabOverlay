# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

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

hiddenimports = [
    'native_overlay_process',
    'qtpy',
    'qtpy.QtCore',
    'qtpy.QtGui',
    'qtpy.QtWidgets',
    'qtpy.QtWebChannel',
    'qtpy.QtWebEngineCore',
    'qtpy.QtWebEngineWidgets',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtWebChannel',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets',
]

# Collect packages that contain runtime data, DLLs, plugins, or dynamically
# imported modules. Including PySide6 here bundles QtWebEngineProcess,
# platform plugins, translations, and other files required on another PC.
for package in ('webview', 'winocr', 'autoit', 'qtpy', 'PySide6'):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += collect_submodules('biome_tracker')

a = Analysis(
    ['main.py'],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # The app is being built for pywebview's Qt backend. Excluding these
        # prevents pywebview from falling back to the broken pythonnet backend.
        'pythonnet',
        'clr',
        'clr_loader',
    ],
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
    console=False,  # Keep True until the packaged build is confirmed working.
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
