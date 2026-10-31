"""Estado compartido entre los procesos de Aura (archivo JSON atómico en %LOCALAPPDATA%\\Aura\\state.json).

Lo escribe el demonio del fondo (``daemon``, ``player``, ``file``, ``port``, ``covered``) y lo leen el panel, la CLI y los widgets.
"""
import json, os

from . import paths
from .win import alive


def atomic_write(path, text):
    """Escribe a un temporal y lo renombra: un corte a medias no deja el archivo corrupto."""
    path = os.fspath(path)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


def read_state():
    try:
        with open(paths.STATE, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_state(**kw):
    atomic_write(paths.STATE, json.dumps(kw))


def handed_over(me):
    """True si otro demonio (un fondo nuevo) ya tomó el relevo: este debe retirarse sin tocar el escritorio."""
    d = read_state().get('daemon')
    return bool(d) and d != me


def wall_running():
    st = read_state()
    return bool(st.get('daemon') and alive(st['daemon']))
