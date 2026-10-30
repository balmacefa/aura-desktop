"""Aura Live: fondos interactivos. Una escena web (WebGL/canvas) se dibuja en Edge, se pega al escritorio como AuraWall
y recibe el cursor, los clics y el estado del equipo por un puente HTTP local (solo 127.0.0.1).

Por qué el puente: el fondo queda DEBAJO de los iconos, así que Windows nunca le entrega el ratón. El servidor lee el cursor
con GetCursorPos y la página lo consulta (como hace Lively). Solo cuentan los clics hechos sobre el escritorio vacío.

Uso:  python live.py run <escena> [paleta]   en primer plano      python live.py start <escena> [paleta]   en segundo plano
      python live.py stop | scenes | serve [puerto]   (serve: abre http://127.0.0.1:8765/scenes/<escena>.html en cualquier navegador)
"""
import ctypes, ctypes.wintypes as wt, json, os, shutil, subprocess, sys, tempfile, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import aurawall as a

u, k32 = a.u32, a.k32
EDGE = next((p for p in (r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe') if os.path.exists(p)), None)
PROFILE = os.path.join(tempfile.gettempdir(), 'AuraLive-profile')
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


def state():
    pt = wt.POINT(); u.GetCursorPos(ctypes.byref(pt))
    w, h = a.screen_size()
    down = bool(u.GetAsyncKeyState(0x01) & 0x8000)
    if down and not _was_down[0]:                                           # flanco de subida; solo si el clic cae en el escritorio
        top = u.GetAncestor(u.WindowFromPoint(pt), 2)                       # GA_ROOT
        if top and a._cls(top) in ('Progman', 'WorkerW'): clicks[0] += 1
    _was_down[0] = down
    lt = time.localtime()
    return {'x': pt.x / w, 'y': pt.y / h, 'down': down, 'click': clicks[0], 'cpu': round(cpu(), 3), 'ram': ram(),
            'bat': a.battery_pct(), 'hour': lt.tm_hour + lt.tm_min / 60}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kw): super().__init__(*args, directory=HERE, **kw)

    def log_message(self, *args): pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')                       # las escenas se editan a menudo
        super().end_headers()

    def do_GET(self):
        if self.path.startswith('/state'):
            body = json.dumps(state()).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
        else:
            super().do_GET()


def launch(scene, palette):
    srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    w, h = a.screen_size()
    if scene.startswith('godot-'):                                          # escena 3D de Godot: mismo puente /state
        exe = find_godot() or sys.exit('Godot no encontrado en el PATH')
        state_url = f'http://127.0.0.1:{srv.server_address[1]}/state'
        args = [exe, '--path', os.path.join(GODOT_DIR, scene[6:]), '--rendering-method', 'mobile', '--rendering-driver', os.environ.get('AURA_GODOT_DRIVER', 'd3d12'), '--windowed', '--resolution', f'{w}x{h}', '--position', '0,0',
                '--', f'--state={state_url}'] + ([f'--pal={palette}'] if palette else [])
        return srv, subprocess.Popen(args, creationflags=0x08000000)
    url = f'http://127.0.0.1:{srv.server_address[1]}/scenes/{scene}.html' + (f'?p={palette}' if palette else '')
    flags = ['--app=' + url, '--user-data-dir=' + PROFILE, '--inprivate', '--disable-sync', '--disable-extensions', '--no-first-run',
             '--no-default-browser-check', '--no-service-autorun', '--disable-component-update', f'--window-size={w},{h}', '--window-position=0,0',
             '--disable-features=CalculateNativeWinOcclusion', '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
             '--disable-backgrounding-occluded-windows', '--autoplay-policy=no-user-gesture-required', '--start-fullscreen', '--hide-scrollbars', '--disable-infobars']
    return srv, subprocess.Popen([EDGE] + flags, creationflags=0x08000000)


def run(scene, palette='', pause_on_battery=True):
    if not EDGE and not scene.startswith('godot-'): sys.exit('Microsoft Edge no encontrado')
    if scene not in scenes(): sys.exit(f'escena desconocida: {scene}. Disponibles: {", ".join(scenes())}')
    srv, proc = launch(scene, palette)
    a.write_state(daemon=os.getpid(), player=proc.pid, file='live:' + scene)
    hwnd = None
    end = time.time() + 20
    while time.time() < end and not hwnd:                                   # la ventana de la app se titula como la página
        found = []
        a.u32.EnumWindows(a.EnumProc(lambda h, _: (found.append(h) if a._title(h).startswith('AuraLive') and a._cls(h) in ('Chrome_WidgetWin_1', 'Engine', 'Window') else None) or True), 0)
        hwnd = found[0] if found else None; time.sleep(.3)
    if not hwnd: proc.kill(); sys.exit('Edge no abrió la ventana')
    a.embed(hwnd, a.find_workerw())
    paused = False
    try:
        while True:
            want = a.covered_by_fullscreen() or (pause_on_battery and a.on_battery())
            if want != paused:
                u.ShowWindow(hwnd, 0 if want else 5); paused = want
            time.sleep(2)
    finally:
        proc.kill(); srv.shutdown(); a.write_state(); u.SystemParametersInfoW(0x0014, 0, None, 3)


def stop():
    a.stop()
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    "Get-CimInstance Win32_Process | Where-Object CommandLine -match 'AuraLive-profile' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                   capture_output=True, creationflags=0x08000000)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'run' and len(sys.argv) > 2:
        run(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else '', pause_on_battery='--battery-ok' not in sys.argv)
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
