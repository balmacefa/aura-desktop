"""Configuración del usuario (%LOCALAPPDATA%\\Aura\\aura.json): validada, con escritura atómica y migración del formato antiguo."""
import json, os, re

from . import log as _log, paths
from .state import atomic_write

log = _log.get('config')
HEX6 = re.compile(r'^[0-9a-fA-F]{6}$')
DEFAULT_PALETTE = ['0e0e18', 'd97757', '1d1b3a', '3a1b2a']
DEFAULT = {
    'scene': 'estela',                # estela | constelacion | orbes | aurora | malla | degradado | video:<archivo> | godot-<proyecto>
    'palette': DEFAULT_PALETTE,
    'widgets': {},                    # nombre -> bool; lo que falte se muestra
    'lang': 'auto',                   # auto | en | es
    'autoupdate': True,               # comprobar versiones nuevas en GitHub (una vez al día)
    'autostart': True,                # iniciar con Windows
    'first_run_done': False,
    'pane': 'Resumen',
    'last_update_check': 0,
    'skipped_version': '',
}
KEYS = set(DEFAULT)


def check_palette(p):
    p = [str(x).lstrip('#') for x in p]
    if len(p) != 4 or not all(HEX6.match(x) for x in p):
        raise ValueError('palette needs 4 hexadecimal colors of 6 digits (e.g. 0e0e18)')
    return [x.lower() for x in p]


def _migrate(raw):
    """aura.json de la 1.x: mode/scene/video/speed -> una sola clave `scene`."""
    if 'mode' in raw:
        if raw.get('mode') == 'video':
            name = os.path.basename(str(raw.get('video', '')))
            raw['scene'] = ('video:' + name) if name else DEFAULT['scene']
        raw.pop('mode', None); raw.pop('video', None); raw.pop('speed', None); raw.pop('seconds', None)
    return raw


def load():
    conf = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT.items()}
    try:
        with open(paths.CONF, encoding='utf-8') as f:
            raw = json.load(f)
    except FileNotFoundError:
        return conf
    except (OSError, ValueError) as e:
        log.warning('aura.json ilegible (%s): se usan los valores por defecto', e)
        try: os.replace(paths.CONF, str(paths.CONF) + '.bad')                    # se conserva para diagnóstico
        except OSError: pass
        return conf
    if isinstance(raw, dict):
        conf.update({k: v for k, v in _migrate(raw).items() if k in KEYS})
    try: conf['palette'] = check_palette(conf['palette'])
    except (ValueError, TypeError): conf['palette'] = list(DEFAULT_PALETTE)
    if not isinstance(conf['widgets'], dict): conf['widgets'] = {}
    if conf['lang'] not in ('auto', 'en', 'es'): conf['lang'] = 'auto'
    for k in ('autoupdate', 'autostart', 'first_run_done'): conf[k] = bool(conf[k])
    if not isinstance(conf['scene'], str) or not conf['scene']: conf['scene'] = DEFAULT['scene']
    return conf


def save(conf):
    atomic_write(paths.CONF, json.dumps({k: v for k, v in conf.items() if k in KEYS}, indent=2, ensure_ascii=False))


def update(**changes):
    """Carga, cambia y guarda en un paso; devuelve la configuración nueva."""
    c = load(); c.update(changes); save(c); return c
