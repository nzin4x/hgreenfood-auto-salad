# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 메인 프로그램 (초기 설정 통합)
main_a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.default.yaml', '.'),
    ],
    hiddenimports=['cryptography', 'tinydb', 'yaml', 'requests', 'app'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

main_pyz = PYZ(main_a.pure, main_a.zipped_data, cipher=block_cipher)

main_exe = EXE(
    main_pyz,
    main_a.scripts,
    main_a.binaries,
    main_a.zipfiles,
    main_a.datas,
    [],
    name='HGreenfoodAutoReservation',
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
    icon=None,
)
