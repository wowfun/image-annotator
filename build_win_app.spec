# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['image_annotator.py'],
             pathex=['E:\\Projects\\image-annotator'],
             binaries=[],
             datas=[('ui', 'ui'), ('user-config.yml', '.'), ('application-config.yml', '.'), ('resources','resources')],
             hiddenimports=['PySide2.QtXml'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='image_annotator',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False , icon='resources/images/win-app-16.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=['vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll', 'msvcp140_1.dll', 'python36.dll', 'qminimal.dll', 'qoffscreen.dll', 'qwebgl.dll', 'qwindows.dll'],
               name='image-annotator')
