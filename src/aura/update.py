"""Actualizaciones desde GitHub Releases (solo stdlib).

Seguridad: se consulta SIEMPRE https://api.github.com/repos/<REPO>/releases/latest (REPO fijo en __init__.py); el instalador debe llamarse
``Aura-Setup-X.Y.Z.exe``, descargarse de https://github.com/<REPO>/releases/download/ (o de los hosts de activos de GitHub tras la redirección),
no superar 250 MB y coincidir con el SHA-256 publicado en ``SHA256SUMS.txt`` de la MISMA versión. Si algo no cuadra, no se ejecuta nada.
No se envía información del usuario: es una petición GET anónima con el nombre y la versión de Aura como agente. Se puede desactivar
(Ajustes › General › Comprobar actualizaciones, o ``autoupdate: false`` en aura.json).
"""
import hashlib, json, re, subprocess, sys, time, urllib.error, urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit

from . import REPO, __version__, config, log as _log, paths

log = _log.get('update')
API = f'https://api.github.com/repos/{REPO}/releases/latest'
ASSET_RE = re.compile(r'^Aura-Setup-(\d+\.\d+\.\d+)\.exe$')
DOWNLOAD_PREFIX = f'https://github.com/{REPO}/releases/download/'
ALLOWED_HOSTS = ('github.com', 'objects.githubusercontent.com', 'release-assets.githubusercontent.com', 'api.github.com')
MAX_BYTES = 250 * 1024 * 1024
CHECK_EVERY = 24 * 3600


@dataclass
class Release:
    version: str
    tag: str
    url: str
    sums_url: str
    size: int
    page: str
    notes: str


def parse_version(v):
    m = re.match(r'^v?(\d+)\.(\d+)\.(\d+)', str(v or ''))
    return tuple(int(x) for x in m.groups()) if m else None


def is_newer(candidate, current=__version__):
    a, b = parse_version(candidate), parse_version(current)
    return bool(a and b and a > b)


def _get(url, timeout=10):
    if urlsplit(url).scheme != 'https' or urlsplit(url).hostname not in ALLOWED_HOSTS:
        raise ValueError(f'untrusted url: {url}')
    req = urllib.request.Request(url, headers={'User-Agent': f'Aura/{__version__}', 'Accept': 'application/vnd.github+json'})
    return urllib.request.urlopen(req, timeout=timeout)


def latest():
    """Última versión publicada como Release, o None (sin red, sin releases o sin el instalador esperado)."""
    try:
        with _get(API) as r:
            data = json.load(r)
    except (urllib.error.URLError, OSError, ValueError) as e:
        log.info('no se pudo consultar GitHub: %s', e); return None
    if data.get('draft') or data.get('prerelease'): return None
    exe = next((a for a in data.get('assets', []) if ASSET_RE.match(a.get('name', ''))), None)
    sums = next((a for a in data.get('assets', []) if a.get('name') == 'SHA256SUMS.txt'), None)
    if not exe or not sums or not parse_version(data.get('tag_name')): return None
    if not exe['browser_download_url'].startswith(DOWNLOAD_PREFIX) or not sums['browser_download_url'].startswith(DOWNLOAD_PREFIX): return None
    return Release(version=ASSET_RE.match(exe['name']).group(1), tag=data['tag_name'], url=exe['browser_download_url'], sums_url=sums['browser_download_url'],
                   size=int(exe.get('size') or 0), page=data.get('html_url', ''), notes=(data.get('body') or '')[:4000])


def check(force=False):
    """Release más nueva que la instalada, o None. Respeta `autoupdate`, el intervalo de 24 h y la versión omitida (salvo `force`)."""
    c = config.load()
    if not force and (not c['autoupdate'] or time.time() - c['last_update_check'] < CHECK_EVERY):
        return None
    rel = latest()
    config.update(last_update_check=int(time.time()))
    if rel and is_newer(rel.version) and (force or rel.version != c['skipped_version']):
        return rel
    return None


def _expected_sha(rel):
    with _get(rel.sums_url) as r:
        text = r.read(1_000_000).decode('utf-8', 'replace')
    name = f'Aura-Setup-{rel.version}.exe'
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip('*') == name and re.fullmatch(r'[0-9a-fA-F]{64}', parts[0]): return parts[0].lower()
    raise ValueError('SHA256SUMS.txt does not list the installer')


def download(rel, progress=None):
    """Descarga el instalador y verifica su SHA-256. Devuelve la ruta o lanza ValueError."""
    paths.UPDATES.mkdir(parents=True, exist_ok=True)
    dest = paths.UPDATES / f'Aura-Setup-{rel.version}.exe'
    expected = _expected_sha(rel)
    h, got = hashlib.sha256(), 0
    with _get(rel.url, timeout=30) as r, open(dest, 'wb') as f:
        total = int(r.headers.get('Content-Length') or rel.size or 0)
        if total > MAX_BYTES: raise ValueError('installer is too large')
        while chunk := r.read(256 * 1024):
            got += len(chunk)
            if got > MAX_BYTES: raise ValueError('installer is too large')
            h.update(chunk); f.write(chunk)
            if progress: progress(got, total)
    if h.hexdigest() != expected:
        dest.unlink(missing_ok=True); raise ValueError('checksum mismatch: the download was discarded')
    log.info('actualización %s descargada y verificada', rel.version)
    return dest


def install(path):
    """Lanza el instalador en silencio (cierra Aura y la vuelve a abrir). El proceso que llama debe terminar enseguida."""
    log.info('instalando %s', path)
    subprocess.Popen([str(path), '/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CLOSEAPPLICATIONS'], creationflags=0x00000008, close_fds=True)


def cli():
    """`aura update`: comprueba (forzado) y, si hay versión nueva, la instala."""
    rel = check(force=True)
    if not rel:
        print(f'Aura {__version__} is up to date.'); return 0
    print(f'Aura {rel.version} is available (you have {__version__}). Downloading…')
    install(download(rel, lambda a, b: print(f'\r{a * 100 // max(b, 1)}%', end='', flush=True)))
    print('\nInstalling; Aura will restart.'); return 0
