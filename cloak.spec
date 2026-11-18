# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for Cloak standalone executable."""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all pyfiglet font assets so ASCII banners work in frozen binaries
datas = collect_data_files('pyfiglet')

hiddenimports = [
    'stego',
    'stego.exceptions',
    'stego.crypto',
    'stego.envelope',
    'stego.carriers',
    'stego.carriers.detector',
    'stego.carriers.image',
    'stego.carriers.audio',
    'stego.tui',
] + collect_submodules('rich') + collect_submodules('questionary')

block_cipher = None

a = Analysis(
    ['stego/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='cloak',
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
