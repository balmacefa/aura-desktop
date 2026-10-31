"""Rutas de Aura: recursos incluidos (solo lectura) y datos del usuario (escribibles).

* ``ASSETS``  escenas, librería JS, medios, fuentes, iconos y proyecto de Godot. En desarrollo vive en ``src/aura/assets``; en el ejecutable
  empaquetado (PyInstaller) dentro de la carpeta ``_internal`` junto al .exe.
* ``DATA``    todo lo que el usuario genera: configuración, estado de ejecución, registro, vídeos propios y actualizaciones descargadas.
  Siempre ``%LOCALAPPDATA%\\Aura`` (o ``AURA_DATA_DIR``, útil para pruebas), nunca la carpeta de instalación: así actualizar o
  desinstalar no pisa tus ajustes y la app funciona aunque se instale en una carpeta de solo lectura.
"""
import os, sys
from pathlib import Path

FROZEN = bool(getattr(sys, 'frozen', False))
PKG_DIR = (Path(sys._MEIPASS) / 'aura') if FROZEN else Path(__file__).resolve().parent
ASSETS = PKG_DIR / 'assets'
SCENES = ASSETS / 'scenes'
LIB = ASSETS / 'lib'
MEDIA = ASSETS / 'media'                                                   # vídeos incluidos
FONTS = ASSETS / 'fonts'
ICONS = ASSETS / 'icons'
GODOT = ASSETS / 'godot'
LOCALES = ASSETS / 'locales'
SCRIPTS = ASSETS / 'scripts'

DATA = Path(os.environ.get('AURA_DATA_DIR') or (Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'Aura'))
CONF = DATA / 'aura.json'
STATE = DATA / 'state.json'
LOGS = DATA / 'logs'
LOG_FILE = LOGS / 'aura.log'
USER_MEDIA = DATA / 'media'                                                # vídeos/GIF que añade el usuario
UPDATES = DATA / 'updates'
DESK_CFG = DATA / 'desk.json'                                              # posiciones de los widgets
DESK_PID = DATA / 'desk.pid'
BROWSER_PROFILES = DATA / 'browser'                                        # perfiles temporales de Edge (uno por demonio)


def ensure_dirs():
    for d in (DATA, LOGS, USER_MEDIA):
        d.mkdir(parents=True, exist_ok=True)


def executable_command():
    """Comando base para relanzar Aura como otro proceso: el propio .exe empaquetado, o `pythonw -m aura` en desarrollo."""
    if FROZEN:
        return [sys.executable]
    exe = Path(sys.executable)
    pyw = exe.with_name('pythonw.exe')
    return [str(pyw if pyw.exists() else exe), '-m', 'aura']
