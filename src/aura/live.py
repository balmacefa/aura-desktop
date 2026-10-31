"""Aura Live: fondos interactivos. Una escena web (WebGL/canvas/vídeo) se dibuja en Edge, o una escena 3D en Godot; la ventana se pega al
escritorio (ver win.py) y recibe el cursor, los clics y el estado del equipo por un puente HTTP local (solo 127.0.0.1).

Por qué el puente: el fondo queda DEBAJO de los iconos, así que Windows nunca le entrega el ratón. El servidor lee el cursor con
GetCursorPos y la página lo consulta (como hace Lively). Solo cuentan los clics hechos sobre el escritorio vacío.

Escenas: ``estela``, ``aurora``… (assets/scenes/*.html), ``video:<archivo>`` (un vídeo/GIF de media o del usuario) y ``godot-<proyecto>``.
"""
import ctypes, ctypes.wintypes as wt, json, mimetypes, os, re, shutil, subprocess, sys, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from . import log as _log, paths, win as a
from .procs import hidden_startupinfo, spawn
from .state import handed_over, read_state, write_state

log = _log.get('live')
u, k32 = a.u32, a.k32
u.GetAncestor.restype = wt.HWND
u.WindowFromPoint.restype = wt.HWND

HIDDEN_SCENES = {'video'}                                                   # plantillas internas: no se eligen directamente
VIDEO_EXT = ('.mp4', '.webm', '.gif', '.mkv', '.mov')
BENCH = os.environ.get('AURA_BENCH') == '1'                                 # métricas de rendimiento solo en modo benchmark


# ---------- navegador y Godot ----------
def find_browser():
    """(ruta, es_edge): Edge, que viene con Windows 10/11; Chrome como alternativa."""
    pf = [os.environ.get(k) for k in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA')]
    for base in filter(None, pf):
        p = Path(base) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe'
        if p.exists(): return str(p), True
    for base in filter(None, pf):
        p = Path(base) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe'
        if p.exists(): return str(p), False
    which = shutil.which('msedge')
    return (which, True) if which else (None, True)


def find_godot():
    exe = os.environ.get('AURA_GODOT')
    if exe and os.path.exists(exe): return exe
    for d in os.environ.get('PATH', '').split(os.pathsep):
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.lower().startswith('godot') and f.lower().endswith('win64.exe') and 'console' not in f.lower(): return os.path.join(d, f)
    return None


def scenes():
    """Escenas elegibles: las web incluidas y, solo si Godot está instalado, los proyectos de Godot."""
    web = sorted(p.stem for p in paths.SCENES.glob('*.html') if p.stem not in HIDDEN_SCENES) if paths.SCENES.is_dir() else []
    gd = []
    if find_godot() and paths.GODOT.is_dir():
        gd = sorted('godot-' + d.name for d in paths.GODOT.iterdir() if (d / 'project.godot').exists())
    return web + gd


def media_files():
    """Vídeos/GIF disponibles: (nombre, es_del_usuario)."""
    out = []
    for base, mine in ((paths.MEDIA, False), (paths.USER_MEDIA, True)):
        if base.is_dir(): out += [(p.name, mine) for p in sorted(base.iterdir()) if p.suffix.lower() in VIDEO_EXT]
    return out


def valid_scene(name):
    if name.startswith('video:'): return any(n == name[6:] for n, _ in media_files())
    return name in scenes()


# ---------- lecturas para el puente ----------
class FT(ctypes.Structure): _fields_ = [('lo', wt.DWORD), ('hi', wt.DWORD)]


_cpu = [None, 0.1]


def cpu():
    i, k, us = FT(), FT(), FT(); k32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(us))
    f = lambda x: (x.hi << 32) | x.lo
    cur = (f(i), f(k) + f(us)); prev, _cpu[0] = _cpu[0], cur
    if prev and cur[1] != prev[1]: _cpu[1] = max(0.0, min(1.0, 1 - (cur[0] - prev[0]) / (cur[1] - prev[1])))
    return _cpu[1]


class MEM(ctypes.Structure):
    _fields_ = [('len', wt.DWORD), ('load', wt.DWORD)] + [(n, ctypes.c_ulonglong) for n in ('tp', 'ap', 'tpf', 'apf', 'tv', 'av', 'ae')]


def ram():
    m = MEM(); m.len = ctypes.sizeof(m); k32.GlobalMemoryStatusEx(ctypes.byref(m)); return m.load / 100


clicks = [0]; _was_down = [False]
_slow = [0.0, {}]


def slow():
    """Lo que no cambia a la velocidad del cursor (CPU, RAM, batería, hora) se calcula como mucho 2 veces por segundo."""
    now = time.time()
    if now - _slow[0] > 0.5:
        lt = time.localtime()
        _slow[1] = {'cpu': round(cpu(), 3), 'ram': ram(), 'bat': a.battery_pct(), 'hour': lt.tm_hour + lt.tm_min / 60}
        _slow[0] = now
    return _slow[1]


def bridge_state():
    pt = wt.POINT(); u.GetCursorPos(ctypes.byref(pt))
    w, h = a.screen_size()
    down = bool(u.GetAsyncKeyState(0x01) & 0x8000)
    if down and not _was_down[0]:                                           # flanco de subida; solo si el clic cae en el escritorio
        top = u.GetAncestor(u.WindowFromPoint(pt), 2)                       # GA_ROOT
        if top and a.cls(top) in ('Progman', 'WorkerW'): clicks[0] += 1
    _was_down[0] = down
    return {'x': pt.x / w, 'y': pt.y / h, 'down': down, 'click': clicks[0], **slow()}


# ---------- servidor local ----------
PERF, REQUESTS = [], [0]
ALLOWED_HOSTS = ('127.0.0.1', 'localhost')                                  # anti DNS-rebinding: una web externa no puede leer el cursor
CSP = "default-src 'self' 'unsafe-inline' blob: data:; connect-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:"   # las escenas no hablan con internet


def _inside(base: Path, rel: str):
    """Ruta absoluta de `rel` bajo `base`, o None si se sale (../) o no existe."""
    try:
        p = (base / rel).resolve()
        return p if p.is_file() and (p == base.resolve() or base.resolve() in p.parents) else None
    except (OSError, ValueError):
        return None


class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'                                           # conexiones persistentes: una sola conexión TCP por página

    def log_message(self, *args): pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')                       # las escenas se editan a menudo
        self.send_header('X-Content-Type-Options', 'nosniff'); self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', CSP)
        super().end_headers()

    def _host_ok(self):
        host = (self.headers.get('Host') or '').rsplit(':', 1)[0]
        if host not in ALLOWED_HOSTS:
            self.send_error(403, 'host no permitido'); return False
        return True

    def translate_path(self, path):
        """/scenes/x.html, /lib/x.js, /media/x.mp4 -> archivo real (solo esas tres carpetas; nunca el código del motor)."""
        p = unquote(urlsplit(path).path)
        for prefix, bases in (('/scenes/', (paths.SCENES,)), ('/lib/', (paths.LIB,)), ('/media/', (paths.USER_MEDIA, paths.MEDIA))):
            if p.startswith(prefix):
                for base in bases:
                    hit = _inside(base, p[len(prefix):])
                    if hit: return str(hit)
        return str(paths.DATA / '.no-existe')

    def send_head(self):
        if not urlsplit(self.path).path.startswith(('/scenes/', '/lib/', '/media/')):
            self.send_error(404); return None
        return super().send_head()

    def do_HEAD(self):
        if self._host_ok(): super().do_HEAD()

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if not self._host_ok(): return
        path = urlsplit(self.path)
        if BENCH and path.path == '/perf':                                  # la página informa de sus fotogramas (aura.js con ?bench=1)
            PERF.append({k: float(v[0]) for k, v in parse_qs(path.query).items()}); self.send_response(204); self.end_headers(); return
        if BENCH and path.path == '/perfdump':
            self._json({'perf': PERF[-6:], 'requests': REQUESTS[0]}); return
        if path.path == '/state':
            REQUESTS[0] += 1
            self._json(bridge_state())
        else:
            super().do_GET()


def scene_url(port, scene, palette=''):
    qs = [f'p={palette}'] if palette else []
    if BENCH: qs.append('bench=1')
    if scene.startswith('video:'):
        qs.insert(0, 'src=/media/' + scene[6:].replace(' ', '%20'))
        page = 'video'
    else:
        page = scene
    return f'http://127.0.0.1:{port}/scenes/{page}.html' + ('?' + '&'.join(qs) if qs else '')


def launch(scene, palette, profile: Path):
    srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    w, h = a.screen_size()
    if scene.startswith('godot-'):                                          # escena 3D de Godot: mismo puente /state
        exe = find_godot()
        if not exe: raise RuntimeError('Godot no encontrado (instálalo o define AURA_GODOT)')
        args = [exe, '--path', str(paths.GODOT / scene[6:]), '--rendering-method', 'mobile', '--rendering-driver', os.environ.get('AURA_GODOT_DRIVER', 'd3d12'),
                '--windowed', '--resolution', f'{w}x{h}', '--position', '-32000,0', '--', f'--state=http://127.0.0.1:{port}/state'] + ([f'--pal={palette}'] if palette else [])
        return srv, subprocess.Popen(args, creationflags=0x08000000, startupinfo=hidden_startupinfo())
    browser, is_edge = find_browser()
    if not browser: raise RuntimeError('No se encontró Microsoft Edge (ni Chrome)')
    flags = ['--app=' + scene_url(port, scene, palette), '--user-data-dir=' + str(profile), '--inprivate' if is_edge else '--incognito', '--disable-sync',
             '--disable-extensions', '--no-first-run', '--no-default-browser-check', '--no-service-autorun', '--disable-component-update',
             f'--window-size={w},{h}', '--window-position=0,0', '--disable-features=CalculateNativeWinOcclusion', '--disable-background-timer-throttling',
             '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', '--enable-gpu-rasterization', '--enable-zero-copy',
             '--disable-background-networking', '--disable-breakpad', '--disable-component-extensions-with-background-pages', '--disable-default-apps',
             '--disable-domain-reliability', '--autoplay-policy=no-user-gesture-required', '--start-fullscreen', '--hide-scrollbars', '--disable-infobars']
    return srv, subprocess.Popen([browser] + flags, creationflags=0x08000000, startupinfo=hidden_startupinfo())


def find_app_window(pid, timeout=20):
    """Ventana principal del proceso lanzado, por PID y tamaño (no por título: Edge lo pone tras cargar la página y la ventana ya parpadearía)."""
    end, owner = time.time() + timeout, wt.DWORD()
    while time.time() < end:
        found = []

        def cb(h, _):
            u.GetWindowThreadProcessId(h, ctypes.byref(owner))
            if owner.value == pid and a.cls(h) in ('Chrome_WidgetWin_1', 'Engine', 'Window'):
                r = wt.RECT(); u.GetWindowRect(h, ctypes.byref(r))
                if r.right - r.left >= 400 and r.bottom - r.top >= 300: found.append(h)
            return True
        u.EnumWindows(a.EnumProc(cb), 0)
        if found: return found[0]
        time.sleep(.01)
    return None


def run(scene, palette='', pause_on_battery=True):
    """Demonio de un fondo: arranca, se pega al escritorio, vigila las reglas de pausa y se retira cuando otro demonio toma el relevo."""
    if not valid_scene(scene):
        log.error('escena desconocida: %s', scene); sys.exit(f'escena desconocida: {scene}')
    if palette and not all(re.fullmatch(r'[0-9a-fA-F]{6}', x) for x in palette.split(',')):
        log.error('paleta no válida: %r', palette); sys.exit('paleta no válida')
    paths.ensure_dirs()
    profile = paths.BROWSER_PROFILES / f'p{os.getpid()}'                      # uno por demonio: dos Edge con el mismo perfil se fusionarían
    log.info('arranca la escena %s', scene)
    try:
        srv, proc = launch(scene, palette, profile)
    except RuntimeError as e:
        log.error('%s', e); sys.exit(str(e))
    hwnd = find_app_window(proc.pid)
    if not hwnd:
        proc.kill(); log.error('no apareció la ventana de %s', scene); sys.exit('la escena no abrió ventana')
    godot = scene.startswith('godot-')
    a.embed(hwnd)
    a.reveal(hwnd, 1.6 if godot else 1.0)                                    # deja que la escena dibuje su primer fotograma y la funde
    write_state(daemon=os.getpid(), player=proc.pid, file='live:' + scene, port=srv.server_address[1])   # a partir de aquí el demonio anterior se retira
    log.info('escena %s visible', scene)
    paused, covered_flag = False, False
    try:
        while not handed_over(os.getpid()):
            cov = a.covered_by_fullscreen()
            want = cov or (pause_on_battery and a.on_battery())
            if cov != covered_flag:                                         # los widgets (tapados también) leen este indicador y dejan de actualizarse
                covered_flag = cov; st = read_state(); st['covered'] = cov; write_state(**st)
            if want != paused:
                if want:
                    u.ShowWindow(hwnd, 0)
                    if godot: a.set_suspended(proc.pid, True)               # Godot sigue dibujando aunque esté oculto: se congela el proceso
                else:
                    if godot: a.set_suspended(proc.pid, False)
                    u.ShowWindow(hwnd, 5)
                paused = want
            time.sleep(0.5)
    finally:
        log.info('escena %s: demonio termina', scene)
        if paused and godot: a.set_suspended(proc.pid, False)
        proc.kill(); srv.shutdown(); shutil.rmtree(profile, ignore_errors=True)
        if not handed_over(os.getpid()):
            write_state(); a.refresh_wallpaper()


def start(scene, palette=''):
    """Lanza el demonio del fondo en segundo plano (el anterior se retira solo cuando este termina el fundido)."""
    return spawn('live', scene, palette) if palette else spawn('live', scene)


def stop():
    """Detiene el fondo y limpia cualquier navegador/perfil temporal que haya quedado."""
    st = read_state()
    for key in ('daemon', 'player'):
        if st.get(key) and a.alive(st[key]):
            subprocess.run(['taskkill', '/PID', str(st[key]), '/T', '/F'], capture_output=True, creationflags=0x08000000)
    write_state(); a.refresh_wallpaper()
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*\\Aura\\browser\\*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                   capture_output=True, creationflags=0x08000000)
    shutil.rmtree(paths.BROWSER_PROFILES, ignore_errors=True)


def serve(port=8765):
    """Servidor de desarrollo: abre http://127.0.0.1:<puerto>/scenes/<escena>.html en cualquier navegador para crear escenas."""
    print(f'http://127.0.0.1:{port}/scenes/<escena>.html   (escenas: {", ".join(scenes())})', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()


def main(argv):
    """Rol `live`: argv = [escena, paleta?]."""
    run(argv[0], argv[1] if len(argv) > 1 else '', pause_on_battery='--battery-ok' not in argv and not BENCH)
