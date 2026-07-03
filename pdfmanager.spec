# -*- mode: python ; coding: utf-8 -*-

import platform
import sys
from typing import Optional


def _mac_target_arch_from_host() -> Optional[str]:
    """Map host CPU architecture to a PyInstaller macOS target_arch value."""
    host = platform.machine().lower()
    if host in ("arm64", "aarch64"):
        return "arm64"
    if host in ("x86_64", "amd64", "x64", "i386"):
        return "x86_64"
    return None


a = Analysis(
    ['pdfmanager.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe_kwargs = {
    'exclude_binaries': True,
    'name': 'pdfmanager',
    'debug': False,
    'bootloader_ignore_signals': False,
    'strip': False,
    'upx': True,
    'console': False,
    'disable_windowed_traceback': False,
    'argv_emulation': False,
}

if sys.platform == 'darwin':
    exe_kwargs['target_arch'] = _mac_target_arch_from_host()
    exe_kwargs['codesign_identity'] = None
    exe_kwargs['entitlements_file'] = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    **exe_kwargs,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pdfmanager',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='pdfmanager.app',
        icon=None,
        bundle_identifier=None,
    )
