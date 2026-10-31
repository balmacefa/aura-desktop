"""Registro de Aura: un solo archivo rotativo en %LOCALAPPDATA%\\Aura\\logs\\aura.log.

Los procesos de fondo corren sin consola: sin esto un fallo no deja ninguna pista. `get(nombre)` devuelve un logger y, la primera vez que
se llama en el proceso, instala también el gancho de excepciones no capturadas (hilo principal y secundarios). Solo stdlib.
"""
import logging, logging.handlers, sys, threading

from . import paths

LOG_DIR, LOG_FILE = str(paths.LOGS), str(paths.LOG_FILE)
_ready = False


def get(name='aura'):
    global _ready
    root = logging.getLogger('aura')
    if not _ready:
        _ready = True
        root.setLevel(logging.INFO)
        try:
            paths.LOGS.mkdir(parents=True, exist_ok=True)
            h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=512 * 1024, backupCount=3, encoding='utf-8')
            h.setFormatter(logging.Formatter('%(asctime)s %(levelname)-7s [%(process)d %(name)s] %(message)s'))
            root.addHandler(h)
        except OSError:
            root.addHandler(logging.NullHandler())                          # sin disco no hay registro, pero nunca se rompe la app

        def hook(t, v, tb): root.critical('Excepción no capturada', exc_info=(t, v, tb))
        sys.excepthook = hook
        threading.excepthook = lambda a: root.critical('Excepción en hilo %s', getattr(a.thread, 'name', '?'), exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
    return root.getChild(name) if name != 'aura' else root
