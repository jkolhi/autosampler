# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

# Get PortAudio path from brew
portaudio_path = os.popen('brew --prefix portaudio').read().strip()

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        (f'{portaudio_path}/lib/libportaudio.2.dylib', '.'),
    ],
    datas=[],
    hiddenimports=[
        'sounddevice',
        '_sounddevice_data',
        'numpy',
        'matplotlib',
        'tkinter'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AudioSampler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AudioSampler'
)

app = BUNDLE(
    coll,
    name='AudioAutoSampler.app',
    icon=None,
    bundle_identifier='se.originalminds.AudioAutoSampler',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSMicrophoneUsageDescription': 'Audio recording and monitoring',
        'NSAppleMusicUsageDescription': 'Audio device access required'
    },
    entitlements_file='entitlements.plist'
)