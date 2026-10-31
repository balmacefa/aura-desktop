"""Textos de la interfaz en inglés y español (assets/locales/*.json). `t('clave', nombre=valor)`; si falta una clave se usa la inglesa.

El idioma es el de configuración (`lang`: auto | en | es); «auto» sigue el idioma de pantalla de Windows. Para añadir un idioma, copia
``en.json`` a ``<código>.json``, traduce y añade el código en config.py (``lang``) y en ui.py (selector).
"""
import ctypes, json

from . import paths

LANGS = ('en', 'es')
_en, _cur, lang = {}, {}, 'en'


def _read(code):
    try:
        with open(paths.LOCALES / f'{code}.json', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def system_language():
    """Idioma de pantalla de Windows (GetUserDefaultUILanguage); inglés si no está entre los disponibles."""
    code = {0x0a: 'es'}.get(ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3ff, 'en')
    return code if code in LANGS else 'en'


def setup(choice='auto'):
    global _en, _cur, lang
    lang = system_language() if choice not in LANGS else choice
    _en = _read('en'); _cur = _read(lang) if lang != 'en' else _en
    return lang


def t(key, **kw):
    s = _cur.get(key) or _en.get(key) or key
    try:
        return s.format(**kw) if kw else s
    except (KeyError, IndexError, ValueError):
        return s
