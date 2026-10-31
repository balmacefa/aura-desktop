# -*- mode: python ; coding: utf-8 -*-
# Receta de PyInstaller: carpeta autocontenida `dist/Aura/` con Aura.exe (sin consola) + Python + Tk + recursos. Uso: python scripts/build.py
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))
SRC = os.path.join(ROOT, 'src')

a = Analysis(
    [os.path.join(SRC, 'aura', '__main__.py')],
    pathex=[SRC],
    datas=[(os.path.join(SRC, 'aura', 'assets'), os.path.join('aura', 'assets'))],
    hiddenimports=['aura.cli', 'aura.ui', 'aura.desk', 'aura.live', 'aura.tray', 'aura.update', 'aura.i18n', 'aura.fonts', 'aura.autostart', 'winreg'],
    excludes=['unittest', 'pydoc', 'test', 'tkinter.test', 'lib2to3', 'idlelib', 'turtledemo', 'distutils'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='Aura',
    console=False,                                   # aplicación de ventana: sin consola negra
    icon=os.path.join(SRC, 'aura', 'assets', 'icons', 'aura.ico'),
    version=os.path.join(SPECPATH, 'version_info.txt'),
    upx=False,                                       # UPX provoca falsos positivos en antivirus
    disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Aura')
