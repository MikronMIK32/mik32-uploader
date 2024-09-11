# -*- mode: python ; coding: utf-8 -*-

import os
import shutil
import zipfile
import tarfile

program_name = 'mik32_upload'

with open('_version.py', 'r') as f:
    applicaton_version_line = f.read().strip()
    applicaton_version_line = applicaton_version_line[len(
        'applicaton_version = '):].strip('\'')

a = Analysis(
    ['mik32_upload.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=program_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mik32_upload',
)


def zip_directory(directory_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                zipf.write(os.path.join(root, file),
                           os.path.relpath(os.path.join(root, file),
                                           os.path.join(directory_path, '..')))


def tar_gz_directory(directory_path, tar_gz_path):
    with tarfile.open(tar_gz_path, "w:gz") as tar:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                tar.add(os.path.join(root, file),
                        os.path.relpath(os.path.join(root, file),
                                        os.path.join(directory_path, '..')))


shutil.copytree('./openocd-scripts/',
                f'./dist/{program_name}/openocd-scripts/')
if os.name == 'nt':
    zip_directory(f'./dist/{program_name}/',
                  f'./dist/mik32-uploader-{applicaton_version_line}.zip')
else:
    tar_gz_directory(f'./dist/{program_name}/',
                     f'./dist/mik32-uploader-{applicaton_version_line}.tar.gz')
