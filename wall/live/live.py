"""Aura Live: fondos interactivos. Una escena web (WebGL/canvas) se dibuja en Edge, se pega al escritorio como AuraWall
y recibe el cursor, los clics y el estado del equipo por un puente HTTP local (solo 127.0.0.1).

Por qué el puente: el fondo queda DEBAJO de los iconos, así que Windows nunca le entrega el ratón. El servidor lee el cursor
con GetCursorPos y la página lo consulta (como hace Lively). Solo cuentan los clics hechos sobre el escritorio vacío.

Uso:  python live.py run <escena> [paleta]   en primer plano      python live.py start <escena> [paleta]   en segundo plano
      python live.py stop | scenes | serve [puerto]   (serve: abre http://127.0.0.1:8765/scenes/<escena>.html en cualquier navegador)
"""
import ctypes, ctypes.wintypes as wt, json, os, re, shutil, subprocess, sys, tempfile, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import aurawall as a
try:                                                                        # registro compartido (aura_log.py en la raíz del proyecto)
    sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
    import aura_log
    log = aura_log.get('live')
except Exception:                                                           # sin el módulo (copia suelta) la app sigue funcionando
    import logging
    log = logging.getLogger('aura.live')


u, k32 = a.u32, a.k32
EDGE = next((p for p in (r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe') if os.path.exists(p)), None)
PROFILE = os.path.join(tempfile.gettempdir(), f'AuraLive-profile-{os.getpid()}')   # uno por demonio: dos Edge con el mismo perfil se fusionarían
SCENES = os.path.join(HERE, 'scenes')
u.GetAncestor.restype = wt.HWND
u.WindowFromPoint.restype = wt.HWND


GODOT_DIR = os.path.join(os.path.dirname(HERE), 'godot')


def find_godot():
    for d in os.environ['PATH'].split(os.pathsep):
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.lower().startswith('godot') and f.lower().endswith('win64.exe'): return os.path.join(d, f)


def scenes():
    web = sorted(f[:-5] for f in os.listdir(SCENES) if f.endswith('.html'))
    gd = sorted('godot-' + d for d in os.listdir(GODOT_DIR) if os.path.exists(os.path.join(GODOT_DIR, d, 'project.godot'))) if os.path.isdir(GODOT_DIR) else []
    return web + gd


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


def state():
    pt = wt.POINT(); u.GetCursorPos(ctypes.byref(pt))
    w, h = a.screen_size()
    down = bool(u.GetAsyncKeyState(0x01) & 0x8000)
    if down and not _was_down[0]:                                           # flanco de subida; solo si el clic cae en el escritorio
        top = u.GetAncestor(u.WindowFromPoint(pt), 2)                       # GA_ROOT
        if top and a._cls(top) in ('Progman', 'WorkerW'): clicks[0] += 1
    _was_down[0] = down
    return {'x': pt.x / w, 'y': pt.y / h, 'down': down, 'click': clicks[0], **slow()}


BENCH = os.environ.get('AURA_BENCH') == '1'                                # métricas de rendimiento solo en modo benchmark
PERF, REQUESTS = [], [0]
ALLOWED_HOSTS = ('127.0.0.1', 'localhost')                                 # anti DNS-rebinding: una web externa no puede leer el cursor
CSP = "default-src 'self' 'unsafe-inline' blob: data:; connect-src 'self'; img-src 'self' data: blob:"   # las escenas no pueden hablar con internet


class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'                                           # conexiones persistentes: una sola conexión TCP por página

    def __init__(self, *args, **kw): super().__init__(*args, directory=HERE, **kw)

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

    def send_head(self):                                                    # solo se sirven /scenes y /lib: nunca el código del motor
        path = urlsplit(self.path).path
        if not path.startswith(('/scenes/', '/lib/')) or '..' in path:
            self.send_error(404); return None
        return super().send_head()

    def do_HEAD(self):
        if self._host_ok(): super().do_HEAD()

    def do_GET(self):
        if not self._host_ok(): return
        path = urlsplit(self.path)
        if BENCH and path.path == '/perf':                                  # la página informa de sus fotogramas (aura.js con ?bench=1)
            from urllib.parse import parse_qs
            PERF.append({k: float(v[0]) for k, v in parse_qs(path.query).items()}); self.send_response(204); self.end_headers(); return
        if BENCH and path.path == '/perfdump':
            body = json.dumps({'perf': PERF[-6:], 'requests': REQUESTS[0]}).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body); return
        if path.path == '/state':
            REQUESTS[0] += 1
            body = json.dumps(state()).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
        else:
            super().do_GET()


def hidden():
    """STARTUPINFO con SW_HIDE: la ventana nace oculta y no parpadea antes de pegarse al escritorio."""
    si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = 0
    return si


def launch(scene, palette):
    srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    w, h = a.screen_size()
    if scene.startswith('godot-'):                                          # escena 3D de Godot: mismo puente /state
        exe = find_godot()
        if not exe: log.error('Godot no encontrado en el PATH'); sys.exit('Godot no encontrado en el PATH')
        state_url = f'http://127.0.0.1:{srv.server_address[1]}/state'
        args = [exe, '--path', os.path.join(GODOT_DIR, scene[6:]), '--rendering-method', 'mobile', '--rendering-driver', os.environ.get('AURA_GODOT_DRIVER', 'd3d12'), '--windowed', '--resolution', f'{w}x{h}', '--position', '-32000,0',
                '--', f'--state={state_url}'] + ([f'--pal={palette}'] if palette else [])
        return srv, subprocess.Popen(args, creationflags=0x08000000, startupinfo=hidden())
    qs = [f'p={palette}'] if palette else []
    if BENCH: qs.append('bench=1')
    url = f'http://127.0.0.1:{srv.server_address[1]}/scenes/{scene}.html' + ('?' + '&'.join(qs) if qs else '')
    flags = ['--app=' + url, '--user-data-dir=' + PROFILE, '--inprivate', '--disable-sync', '--disable-extensions', '--no-first-run',
             '--no-default-browser-check', '--no-service-autorun', '--disable-component-update', f'--window-size={w},{h}', '--window-position=0,0',
             '--disable-features=CalculateNativeWinOcclusion', '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
             '--disable-backgrounding-occluded-windows', '--enable-gpu-rasterization', '--enable-zero-copy', '--disable-background-networking',
             '--disable-breakpad', '--disable-component-extensions-with-background-pages', '--disable-default-apps', '--disable-domain-reliability', '--autoplay-policy=no-user-gesture-required', '--start-fullscreen', '--hide-scrollbars', '--disable-infobars']
    return srv, subprocess.Popen([EDGE] + flags, creationflags=0x08000000, startupinfo=hidden())


def find_app_window(pid, timeout=20):
    """Ventana principal del proceso lanzado, por PID y tamaño (no por título: Edge lo pone tras cargar la página y la ventana ya parpadearía)."""
    end, owner = time.time() + timeout, wt.DWORD()
    while time.time() < end:
        found = []

        def cb(h, _):
            u.GetWindowThreadProcessId(h, ctypes.byref(owner))
            if owner.value == pid and a._cls(h) in ('Chrome_WidgetWin_1', 'Engine', 'Window'):
                r = wt.RECT(); u.GetWindowRect(h, ctypes.byref(r))
                if r.right - r.left >= 400 and r.bottom - r.top >= 300: found.append(h)
            return True
        a.u32.EnumWindows(a.EnumProc(cb), 0)
        if found: return found[0]
        time.sleep(.01)
    return None


def run(scene, palette='', pause_on_battery=True):
    if not EDGE and not scene.startswith('godot-'): log.error('Microsoft Edge no encontrado'); sys.exit('Microsoft Edge no encontrado')
    if scene not in scenes(): log.error('escena desconocida: %s', scene); sys.exit(f'escena desconocida: {scene}. Disponibles: {", ".join(scenes())}')
    if palette and not all(re.fullmatch(r'[0-9a-fA-F]{6}', x) for x in palette.split(',')): log.error('paleta no válida: %r', palette); sys.exit('paleta no válida')
    log.info('arranca la escena %s', scene)
    srv, proc = launch(scene, palette)
    hwnd = find_app_window(proc.pid)
    if not hwnd: proc.kill(); log.error('no apareció la ventana de %s', scene); sys.exit('la escena no abrió ventana')
    a.embed(hwnd, a.find_workerw())
    a.reveal(hwnd, 1.6 if scene.startswith('godot-') else 1.0)              # deja que la escena dibuje su primer fotograma y la funde
    a.write_state(daemon=os.getpid(), player=proc.pid, file='live:' + scene, port=srv.server_address[1])  # a partir de aquí el demonio anterior se retira
    log.info('escena %s visible', scene)
    paused = False
    try:
        while not a.handed_over(os.getpid()):
            want = a.covered_by_fullscreen() or (pause_on_battery and a.on_battery())
            if want != paused:
                u.ShowWindow(hwnd, 0 if want else 5); paused = want
            time.sleep(0.5)
    finally:
        log.info('escena %s: demonio termina', scene)
        proc.kill(); srv.shutdown(); shutil.rmtree(PROFILE, ignore_errors=True)
        if not a.handed_over(os.getpid()):
            a.write_state(); u.SystemParametersInfoW(0x0014, 0, None, 3)


def stop():
    a.stop()
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    "Get-CimInstance Win32_Process | Where-Object CommandLine -match 'AuraLive-profile' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                   capture_output=True, creationflags=0x08000000)
    for d in os.listdir(tempfile.gettempdir()):                                # perfiles temporales de Edge que hayan quedado
        if d.startswith('AuraLive-profile'): shutil.rmtree(os.path.join(tempfile.gettempdir(), d), ignore_errors=True)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'run' and len(sys.argv) > 2:
        run(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else '', pause_on_battery='--battery-ok' not in sys.argv and not BENCH)
    elif cmd == 'start' and len(sys.argv) > 2:
        pyw = shutil.which('pythonw') or sys.executable
        subprocess.Popen([pyw, os.path.abspath(__file__), 'run'] + sys.argv[2:], creationflags=0x00000008)
    elif cmd == 'serve':                                                   # para desarrollar escenas en un navegador normal
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
        print(f'http://127.0.0.1:{port}/scenes/<escena>.html   (escenas: {", ".join(scenes())})', flush=True)
        ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
    elif cmd == 'stop': stop()
    elif cmd == 'scenes': print('\n'.join(scenes()))
    else: print(__doc__)
