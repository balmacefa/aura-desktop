"""AuraWall: fondo de escritorio animado para Windows 11 (vídeo/GIF), sin dependencias de Python.

Arquitectura (derivada del análisis estático de Lively con REA, ver docs/ARQUITECTURA.md):
  1. Progman recibe el mensaje 0x052C para crear la capa WorkerW detrás de los iconos.
  2. Un reproductor externo (ffplay, render D3D11) se reparenta a Progman, detrás de SHELLDLL_DefView, con exstyle LAYERED (receta medida en Lively).
  3. Un bucle de reglas de pausa suspende el reproductor cuando no se ve o gasta batería.

Uso:  python aurawall.py run <archivo>      en primer plano (Ctrl+C para salir)
      python aurawall.py start <archivo>    en segundo plano
      python aurawall.py stop | status
"""
import ctypes, ctypes.wintypes as wt, json, os, shutil, subprocess, sys, time

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
ntdll = ctypes.windll.ntdll
u32.SetProcessDPIAware()

STATE_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'AuraWall')
STATE = os.path.join(STATE_DIR, 'state.json')
TITLE = 'AuraWallPlayer'
GWL_STYLE, WS_CHILD, WS_VISIBLE = -16, 0x40000000, 0x10000000
SWP_FLAGS = 0x0004 | 0x0010 | 0x0040           # NOZORDER | NOACTIVATE | SHOWWINDOW
PROCESS_SUSPEND_RESUME = 0x0800
SHELL_CLASSES = {'Progman', 'WorkerW', 'Shell_TrayWnd', 'SHELLDLL_DefView'}

EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
u32.FindWindowW.restype = wt.HWND
u32.FindWindowExW.restype = wt.HWND
u32.GetForegroundWindow.restype = wt.HWND


def _cls(h):
    b = ctypes.create_unicode_buffer(256); u32.GetClassNameW(h, b, 256); return b.value


def _title(h):
    b = ctypes.create_unicode_buffer(256); u32.GetWindowTextW(h, b, 256); return b.value


def find_workerw():
    """Devuelve el HWND de la capa WorkerW que queda detrás de los iconos."""
    progman = u32.FindWindowW('Progman', None)
    res = wt.DWORD()
    u32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(res))   # crea WorkerW
    # Windows 11 24H2+: WorkerW es hijo de Progman
    child = u32.FindWindowExW(progman, None, 'WorkerW', None)
    if child:
        return child
    # Windows 10 / 11 anterior: WorkerW hermano, tras el que contiene SHELLDLL_DefView
    found = []

    def cb(h, _):
        if u32.FindWindowExW(h, None, 'SHELLDLL_DefView', None):
            w = u32.FindWindowExW(None, h, 'WorkerW', None)
            if w:
                found.append(w)
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return found[0] if found else progman


def find_by_title(title, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        hit = []
        u32.EnumWindows(EnumProc(lambda h, _: (hit.append(h) if _title(h) == title else None) or True), 0)
        if hit:
            return hit[0]
        time.sleep(0.015)
    return None


def screen_size():
    return u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)


def embed(player, workerw):
    w, h = screen_size()
    u32.SetParent.argtypes = [wt.HWND, wt.HWND]
    u32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
    # Receta de Lively (WinDesktopCore, vía REA): TryAttachToDesktop = SetParent(player, WorkerW) + estilo sin borde
    # + SetWindowPos; EnsureWorkerWZOrder = dejar WorkerW al fondo de los hijos de Progman (bajo los iconos).
    # Medido con Lively en funcionamiento (build 26200): el reproductor es hijo de PROGMAN (no de WorkerW), entre DefView y
    # WorkerW, con exstyle LAYERED|TOOLWINDOW|NOACTIVATE.
    progman = u32.FindWindowW('Progman', None)
    defview = u32.FindWindowExW(progman, None, 'SHELLDLL_DefView', None)
    u32.SetLayeredWindowAttributes.argtypes = [wt.HWND, wt.DWORD, ctypes.c_ubyte, wt.DWORD]
    u32.SetWindowLongW(player, -20, 0x00080000 | 0x80 | 0x08000000)    # LAYERED | TOOLWINDOW | NOACTIVATE (debe ir ANTES de SetParent: después Windows lo ignora)
    u32.SetLayeredWindowAttributes(player, 0, 0, 2)                    # transparente hasta que fade_in() la muestre
    u32.SetParent(player, progman)
    u32.SetWindowLongW(player, GWL_STYLE, WS_CHILD | WS_VISIBLE | 0x04000000 | 0x02000000)   # + CLIPSIBLINGS | CLIPCHILDREN
    u32.SetWindowPos(player, defview, 0, 0, w, h, 0x0010 | 0x0040)                          # justo detrás de DefView


def fade_in(hwnd, secs=0.9):
    """Aparece con un fundido (curva suave) sobre lo que haya detrás: el fondo anterior o el de Windows."""
    anim = ctypes.c_int(1)
    if u32.SystemParametersInfoW(0x1042, 0, ctypes.byref(anim), 0) and not anim.value:   # SPI_GETCLIENTAREAANIMATION: animaciones desactivadas en Windows
        secs = 0
    n = max(1, int(secs * 60))
    for i in range(1, n + 1):
        t = i / n
        u32.SetLayeredWindowAttributes(hwnd, 0, int(255 * t * t * (3 - 2 * t)), 2)
        time.sleep(secs / n)
    u32.SetLayeredWindowAttributes(hwnd, 0, 255, 2)


def reveal(hwnd, settle=1.0, secs=0.9):
    """Muestra la ventana ya cargada con un fundido. Mientras se asienta, reafirma la transparencia 0 cada 15 ms: Chrome y Godot reinician
    el estilo de su ventana al arrancar y, sin esto, se verían un instante a opacidad total."""
    end = time.time() + settle
    while time.time() < end:
        if not u32.SetLayeredWindowAttributes(hwnd, 0, 0, 2):           # perdió LAYERED: se vuelve a poner (sumando bits, no pisando los de Chrome)
            u32.SetWindowLongW(hwnd, -20, (u32.GetWindowLongW(hwnd, -20) & 0xFFFFFFFF) | 0x00080000 | 0x80 | 0x08000000)
        time.sleep(0.015)
    fade_in(hwnd, secs)


def handed_over(me):
    """True si otro demonio (un fondo nuevo) ya tomó el relevo: este debe retirarse sin tocar el escritorio."""
    d = read_state().get('daemon')
    return bool(d) and d != me


def covered_by_fullscreen():
    """True si la ventana en primer plano cubre toda la pantalla (juego, vídeo, app a pantalla completa)."""
    fg = u32.GetForegroundWindow()
    if not fg or _cls(fg) in SHELL_CLASSES or _title(fg).startswith((TITLE, 'AuraLive')) or not u32.IsWindowVisible(fg):
        return False                                    # el propio reproductor no cuenta como "ventana que tapa"
    r = wt.RECT(); u32.GetWindowRect(fg, ctypes.byref(r))
    w, h = screen_size()
    return r.left <= 0 and r.top <= 0 and r.right >= w and r.bottom >= h


def battery_pct():
    class SPS(ctypes.Structure):
        _fields_ = [('ac', ctypes.c_ubyte), ('flag', ctypes.c_ubyte), ('pct', ctypes.c_ubyte), ('sv', ctypes.c_ubyte),
                    ('life', wt.DWORD), ('full', wt.DWORD)]
    s = SPS(); k32.GetSystemPowerStatus(ctypes.byref(s))
    return 100 if s.pct == 255 else s.pct


def on_battery():
    class SPS(ctypes.Structure):
        _fields_ = [('ac', ctypes.c_ubyte), ('flag', ctypes.c_ubyte), ('pct', ctypes.c_ubyte),
                    ('sv', ctypes.c_ubyte), ('life', wt.DWORD), ('full', wt.DWORD)]
    s = SPS(); k32.GetSystemPowerStatus(ctypes.byref(s))
    return s.ac == 0 and s.pct < 30                    # solo ahorra con batería baja (<30 %)


def set_suspended(pid, suspend):
    h = k32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
    if h:
        (ntdll.NtSuspendProcess if suspend else ntdll.NtResumeProcess)(h)
        k32.CloseHandle(h)


def write_state(**kw):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE, 'w') as f:
        json.dump(kw, f)


def read_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def alive(pid):
    h = k32.OpenProcess(0x1000, False, pid or 0)     # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = wt.DWORD(); k32.GetExitCodeProcess(h, ctypes.byref(code)); k32.CloseHandle(h)
    return code.value == 259                          # STILL_ACTIVE


def run(path, pause_on_battery=True):
    ffplay = shutil.which('ffplay')
    if not ffplay:
        sys.exit('ffplay no encontrado (winget install Gyan.FFmpeg)')
    w, h = screen_size()
    proc = subprocess.Popen([ffplay, '-noborder', '-loop', '0', '-an', '-loglevel', 'quiet',
                             '-x', str(w), '-y', str(h), '-left', '-32000', '-top', '0',   # nace fuera de pantalla; embed() la coloca en 0,0
                             '-window_title', TITLE, path], creationflags=0x08000000,       # sin consola
                            env={**os.environ, 'SDL_RENDER_DRIVER': 'direct3d11'})          # Progman es NOREDIRECTIONBITMAP: solo se compone contenido GPU, no GDI/software
    hwnd = find_by_title(TITLE)
    if not hwnd:
        proc.kill(); sys.exit('el reproductor no abrió ventana')
    embed(hwnd, find_workerw())
    reveal(hwnd, 0.4)
    write_state(daemon=os.getpid(), player=proc.pid, file=os.path.abspath(path))   # a partir de aquí el demonio anterior se retira
    paused = False

    def pause(on):
        # Una ventana suspendida no atiende mensajes y, siendo hija del escritorio, congelaría al shell:
        # se oculta ANTES de suspender y se muestra DESPUÉS de reanudar.
        if on:
            u32.ShowWindow(hwnd, 0); set_suspended(proc.pid, True)
        else:
            set_suspended(proc.pid, False); u32.ShowWindow(hwnd, 5)
    try:
        while proc.poll() is None and not handed_over(os.getpid()):
            want = covered_by_fullscreen() or (pause_on_battery and on_battery())
            if want != paused:
                pause(want); paused = want
            time.sleep(0.5)
    finally:
        if paused:
            set_suspended(proc.pid, False)
        proc.kill()
        if not handed_over(os.getpid()):                                     # relevo: el nuevo ya está delante, no tocar nada
            write_state()
            u32.SystemParametersInfoW(0x0014, 0, None, 3)                    # fuerza a Windows a repintar el fondo normal


def start(path, battery_ok=False):
    pyw = shutil.which('pythonw') or sys.executable
    extra = ['--battery-ok'] if battery_ok else []
    subprocess.Popen([pyw, os.path.abspath(__file__), 'run', os.path.abspath(path)] + extra, creationflags=0x00000008)  # DETACHED


def stop():
    st = read_state()
    for key in ('daemon', 'player'):
        if st.get(key) and alive(st[key]):
            subprocess.run(['taskkill', '/PID', str(st[key]), '/T', '/F'], capture_output=True)
    write_state()
    u32.SystemParametersInfoW(0x0014, 0, None, 3)


def status():
    st = read_state()
    print(json.dumps({**st, 'activo': bool(st.get('daemon')) and alive(st.get('daemon'))}, ensure_ascii=False))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd in ('run', 'start') and len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        ok = '--battery-ok' in sys.argv        # no pausar al ir con batería
        run(sys.argv[2], pause_on_battery=not ok) if cmd == 'run' else start(sys.argv[2], battery_ok=ok)
    elif cmd == 'stop':
        stop()
    elif cmd == 'status':
        status()
    else:
        print(__doc__)
