"""Ayudantes de Windows para pegar una ventana al escritorio (solo ctypes).

Receta medida con Lively en Windows 11 build 26200 (ver docs/ARQUITECTURA-fondo.md):
  1. Progman recibe el mensaje 0x052C: se crea la capa WorkerW detrás de los iconos.
  2. La ventana del fondo recibe el estilo LAYERED|TOOLWINDOW|NOACTIVATE (ANTES de reparentar: después Windows lo ignora), se reparenta a
     **Progman** y se coloca justo detrás de SHELLDLL_DefView.
  3. Progman es NOREDIRECTIONBITMAP: solo se compone contenido por GPU (Chrome/Edge, Godot con D3D12), no GDI ni render por software.
"""
import ctypes, ctypes.wintypes as wt, time

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
dwm = ctypes.windll.dwmapi
ntdll = ctypes.windll.ntdll
u32.SetProcessDPIAware()

WINDOW_PREFIX = 'AuraLive'                                                 # las ventanas de fondo de Aura se titulan así (y no cuentan como «tapar»)
WS_CHILD, WS_VISIBLE = 0x40000000, 0x10000000
SHELL_CLASSES = {'Progman', 'WorkerW', 'Shell_TrayWnd', 'SHELLDLL_DefView'}

EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
u32.FindWindowW.restype = wt.HWND
u32.FindWindowExW.restype = wt.HWND
u32.GetForegroundWindow.restype = wt.HWND
u32.SetParent.argtypes = [wt.HWND, wt.HWND]
u32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
u32.SetLayeredWindowAttributes.argtypes = [wt.HWND, wt.DWORD, ctypes.c_ubyte, wt.DWORD]


def cls(h):
    b = ctypes.create_unicode_buffer(256); u32.GetClassNameW(h, b, 256); return b.value


def title(h):
    b = ctypes.create_unicode_buffer(256); u32.GetWindowTextW(h, b, 256); return b.value


def screen_size():
    return u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)


def alive(pid):
    h = k32.OpenProcess(0x1000, False, int(pid or 0))                      # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = wt.DWORD(); k32.GetExitCodeProcess(h, ctypes.byref(code)); k32.CloseHandle(h)
    return code.value == 259                                               # STILL_ACTIVE


def create_time(pid):
    """Instante de creación del proceso: identifica el proceso aunque Windows reutilice el PID."""
    h = k32.OpenProcess(0x1000, False, int(pid or 0))
    if not h:
        return None
    c, e, k, u = (wt.FILETIME() for _ in range(4))
    ok = k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)); k32.CloseHandle(h)
    return ((c.dwHighDateTime << 32) | c.dwLowDateTime) if ok else None


def set_suspended(pid, suspend):
    """Congela/reanuda un proceso (para fondos que siguen dibujando aunque estén ocultos)."""
    h = k32.OpenProcess(0x0800, False, pid)                                # PROCESS_SUSPEND_RESUME
    if h:
        (ntdll.NtSuspendProcess if suspend else ntdll.NtResumeProcess)(h)
        k32.CloseHandle(h)


# ---------- escritorio ----------
def find_workerw():
    """HWND de la capa WorkerW que queda detrás de los iconos (la crea con el mensaje 0x052C)."""
    progman = u32.FindWindowW('Progman', None)
    res = wt.DWORD()
    u32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(res))
    child = u32.FindWindowExW(progman, None, 'WorkerW', None)             # Windows 11 24H2+: WorkerW es hijo de Progman
    if child:
        return child
    found = []                                                             # Windows 10 / 11 anterior: WorkerW hermano del que contiene DefView

    def cb(h, _):
        if u32.FindWindowExW(h, None, 'SHELLDLL_DefView', None):
            w = u32.FindWindowExW(None, h, 'WorkerW', None)
            if w:
                found.append(w)
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return found[0] if found else progman


def embed(hwnd, workerw=None):
    """Pega la ventana al escritorio, transparente (alpha 0) hasta que `reveal` la funda."""
    w, h = screen_size()
    progman = u32.FindWindowW('Progman', None)
    defview = u32.FindWindowExW(progman, None, 'SHELLDLL_DefView', None)
    u32.SetWindowLongW(hwnd, -20, 0x00080000 | 0x80 | 0x08000000)          # LAYERED | TOOLWINDOW | NOACTIVATE (ANTES de SetParent)
    u32.SetLayeredWindowAttributes(hwnd, 0, 0, 2)
    u32.SetParent(hwnd, progman)
    u32.SetWindowLongW(hwnd, -16, WS_CHILD | WS_VISIBLE | 0x04000000 | 0x02000000)   # + CLIPSIBLINGS | CLIPCHILDREN
    u32.SetWindowPos(hwnd, defview, 0, 0, w, h, 0x0010 | 0x0040)           # justo detrás de DefView; NOACTIVATE | SHOWWINDOW


def fade_in(hwnd, secs=0.9):
    """Aparece con un fundido (curva suave) sobre lo que haya detrás. Respeta «Mostrar animaciones» de Windows."""
    anim = ctypes.c_int(1)
    if u32.SystemParametersInfoW(0x1042, 0, ctypes.byref(anim), 0) and not anim.value:   # SPI_GETCLIENTAREAANIMATION
        secs = 0
    n = max(1, int(secs * 60))
    for i in range(1, n + 1):
        t = i / n
        u32.SetLayeredWindowAttributes(hwnd, 0, int(255 * t * t * (3 - 2 * t)), 2)
        time.sleep(secs / n)
    u32.SetLayeredWindowAttributes(hwnd, 0, 255, 2)


def reveal(hwnd, settle=1.0, secs=0.9):
    """Funde la ventana ya cargada. Mientras se asienta reafirma alpha 0 cada 15 ms: Chrome y Godot reinician el estilo al arrancar y,
    sin esto, se verían un instante a opacidad total."""
    end = time.time() + settle
    while time.time() < end:
        if not u32.SetLayeredWindowAttributes(hwnd, 0, 0, 2):             # perdió LAYERED: se suma de nuevo (sin pisar los bits de Chrome)
            u32.SetWindowLongW(hwnd, -20, (u32.GetWindowLongW(hwnd, -20) & 0xFFFFFFFF) | 0x00080000 | 0x80 | 0x08000000)
        time.sleep(0.015)
    fade_in(hwnd, secs)


def covered_by_fullscreen():
    """True si alguna ventana normal y visible cubre todo el área de trabajo (maximizada o a pantalla completa): el escritorio no se ve y
    dibujar el fondo es CPU tirada. Se ignoran las minimizadas, las «cloaked» (UWP ocultas), las de herramientas/transparentes, las sin
    título (marcos UWP vacíos), las superposiciones del sistema (CoreWindow) y las propias."""
    wa = wt.RECT(); u32.SystemParametersInfoW(0x30, 0, ctypes.byref(wa), 0)            # SPI_GETWORKAREA: pantalla sin la barra de tareas
    hit = []
    cloaked, r = ctypes.c_int(0), wt.RECT()

    def cb(h, _):
        if not u32.IsWindowVisible(h) or u32.IsIconic(h):
            return True
        if u32.GetWindowLongW(h, -20) & (0x80 | 0x08000000 | 0x20):                     # TOOLWINDOW | NOACTIVATE | TRANSPARENT
            return True
        t = title(h)
        if not t or cls(h) in SHELL_CLASSES | {'Windows.UI.Core.CoreWindow'} or t.startswith(WINDOW_PREFIX):
            return True
        cloaked.value = 0
        if dwm.DwmGetWindowAttribute(h, 13, ctypes.byref(cloaked), 4) == 0 and cloaked.value:   # DWMWA_CLOAKED
            return True
        u32.GetWindowRect(h, ctypes.byref(r))
        if r.left <= wa.left + 8 and r.top <= wa.top + 8 and r.right >= wa.right - 8 and r.bottom >= wa.bottom - 8:   # una maximizada sobresale ~8 px
            hit.append(h); return False
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return bool(hit)


class _SPS(ctypes.Structure):
    _fields_ = [('ac', ctypes.c_ubyte), ('flag', ctypes.c_ubyte), ('pct', ctypes.c_ubyte), ('sv', ctypes.c_ubyte), ('life', wt.DWORD), ('full', wt.DWORD)]


def power():
    s = _SPS(); k32.GetSystemPowerStatus(ctypes.byref(s)); return s


def battery_pct():
    s = power()
    return 100 if s.pct == 255 else s.pct


def on_battery():
    """Con batería baja (<30 %) y sin cargador: el fondo se pausa para ahorrar."""
    s = power()
    return s.ac == 0 and s.pct < 30


def refresh_wallpaper():
    """Fuerza a Windows a repintar su fondo normal (al detener el fondo animado)."""
    u32.SystemParametersInfoW(0x0014, 0, None, 3)
