# -*- mode: python ; coding: utf-8 -*-

import os
import subprocess

# Determine the path to ffmpeg
ffmpeg_path = subprocess.check_output(['which', 'ffmpeg']).decode().strip()

a = Analysis(
    ['src/FreeScribe.client/client.py'],
    pathex=[],
    binaries=[(ffmpeg_path, 'ffmpeg')],
    datas=[('./src/FreeScribe.client/whisper-assets', 'whisper/assets'), ('./src/FreeScribe.client/markdown', 'markdown'), ('./src/FreeScribe.client/assets', 'assets')],
    hiddenimports=[],
    hookspath=['./scripts/hooks'],
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
    name='freescribe-client',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    icon=['src/FreeScribe.client/assets/logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FreeScribe',
)
app = BUNDLE(
    coll,
    name='freescribe-client.app',
    icon='src/FreeScribe.client/assets/logo.ico',
    bundle_identifier='com.clinicianfocus.freescribe',
    info_plist={'NSMicrophoneUsageDescription':'This app requires access to the microphone to capture audio.'},
)
