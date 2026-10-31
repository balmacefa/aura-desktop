"""Lanzar procesos de Aura en segundo plano: el propio .exe empaquetado, o `pythonw -m aura` en desarrollo."""
import os, subprocess

from . import paths

DETACHED = 0x00000008


def spawn(role, *args, env=None):
    """Arranca `aura --role <role> args…` desvinculado de quien lo lanza (sobrevive al padre, sin consola)."""
    cmd = paths.executable_command() + ['--role', role, *map(str, args)]
    cwd = None if paths.FROZEN else str(paths.PKG_DIR.parent)               # en desarrollo `-m aura` necesita `src` en la ruta
    return subprocess.Popen(cmd, cwd=cwd, creationflags=DETACHED, env={**os.environ, **(env or {})}, close_fds=True)


def hidden_startupinfo():
    """STARTUPINFO con SW_HIDE: la ventana nace oculta y no parpadea antes de pegarse al escritorio."""
    si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = 0
    return si
