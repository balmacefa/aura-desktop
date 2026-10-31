"""Icono de Aura junto al reloj (zona de notificación) y proceso «anfitrión» de la aplicación (solo ctypes).

Es lo que arranca al abrir Aura o al iniciar sesión (`--background`): una sola instancia (mutex). Abre/cierra el fondo y los widgets según la
configuración, comprueba actualizaciones y ofrece el menú: Abrir Aura, Pausar/Reanudar, cambiar de fondo, iniciar con Windows, buscar
actualizaciones y Salir. Si Aura ya está abierta, abrirla de nuevo solo abre la ventana de ajustes.
"""
import ctypes, ctypes.wintypes as wt, threading, time

from . import __version__, autostart, cli, config, i18n, log as _log, paths, update
from .i18n import t
from .procs import spawn
from .state import wall_running

log = _log.get('tray')
u32, k32, sh32 = ctypes.windll.user32, ctypes.windll.kernel32, ctypes.windll.shell32
LRESULT = ctypes.c_ssize_t
WM_APP_TRAY, WM_CLOSE, WM_DESTROY, WM_NULL = 0x8001, 0x0010, 0x0002, 0x0000
WM_LBUTTONDBLCLK, WM_RBUTTONUP, WM_LBUTTONUP = 0x0203, 0x0205, 0x0202
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 1, 2, 4, 0x10
MF_STRING, MF_SEPARATOR, MF_CHECKED, MF_POPUP, MF_DEFAULT = 0, 0x800, 8, 0x10, 0x1000
TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x0002, 0x0100

ID_OPEN, ID_PAUSE, ID_AUTOSTART, ID_UPDATES, ID_QUIT, ID_SCENE0 = 1, 2, 3, 4, 9, 100


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [('cbSize', wt.DWORD), ('hWnd', wt.HWND), ('uID', wt.UINT), ('uFlags', wt.UINT), ('uCallbackMessage', wt.UINT), ('hIcon', wt.HICON),
                ('szTip', wt.WCHAR * 128), ('dwState', wt.DWORD), ('dwStateMask', wt.DWORD), ('szInfo', wt.WCHAR * 256), ('uVersion', wt.UINT),
                ('szInfoTitle', wt.WCHAR * 64), ('dwInfoFlags', wt.DWORD), ('guid', ctypes.c_ubyte * 16), ('hBalloonIcon', wt.HICON)]


WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [('style', wt.UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int), ('hInstance', wt.HINSTANCE),
                ('hIcon', wt.HICON), ('hCursor', wt.HANDLE), ('hbrBackground', wt.HBRUSH), ('lpszMenuName', wt.LPCWSTR), ('lpszClassName', wt.LPCWSTR)]


u32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]; u32.DefWindowProcW.restype = LRESULT
u32.CreateWindowExW.restype = wt.HWND
u32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
u32.CreatePopupMenu.restype = wt.HMENU
u32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
u32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, ctypes.c_void_p]
u32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
u32.LoadImageW.restype = wt.HANDLE
u32.LoadImageW.argtypes = [wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ctypes.c_int, ctypes.c_int, wt.UINT]
k32.GetModuleHandleW.restype = wt.HINSTANCE


class Tray:
    def __init__(self):
        self.hwnd = None; self.notified = ''; self.nid = None; self.created_msg = u32.RegisterWindowMessageW('TaskbarCreated')
        self._proc = WNDPROC(self._wndproc)                                  # referencia viva: si se recoge, Windows llama a memoria liberada

    # ---------- ventana oculta + icono ----------
    def create(self):
        hinst = k32.GetModuleHandleW(None)
        wc = WNDCLASSW(); wc.lpfnWndProc = self._proc; wc.hInstance = hinst; wc.lpszClassName = 'AuraTrayWindow'
        u32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = u32.CreateWindowExW(0, 'AuraTrayWindow', 'AuraTray', 0, 0, 0, 0, 0, None, None, hinst, None)   # ventana normal, nunca mostrada (recibe TaskbarCreated)
        self.add_icon()

    def _icon(self):
        size = u32.GetSystemMetrics(49)                                      # SM_CXSMICON: tamaño de icono pequeño según DPI
        return u32.LoadImageW(None, str(paths.ICONS / 'aura.ico'), 1, size, size, 0x10)

    def add_icon(self):
        n = NOTIFYICONDATAW(); n.cbSize = ctypes.sizeof(n); n.hWnd = self.hwnd; n.uID = 1
        n.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP; n.uCallbackMessage = WM_APP_TRAY; n.hIcon = self._icon(); n.szTip = t('tray.tip') + f' {__version__}'
        self.nid = n
        sh32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(n))

    def balloon(self, title, text):
        n = NOTIFYICONDATAW(); n.cbSize = ctypes.sizeof(n); n.hWnd = self.hwnd; n.uID = 1; n.uFlags = NIF_INFO
        n.szInfoTitle = title[:63]; n.szInfo = text[:255]; n.dwInfoFlags = 1
        sh32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(n))

    def remove_icon(self):
        if self.nid: sh32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))

    # ---------- menú ----------
    def menu(self):
        c = config.load(); scenes = cli.scenes()
        m = u32.CreatePopupMenu()
        u32.AppendMenuW(m, MF_STRING | MF_DEFAULT, ID_OPEN, t('tray.open'))
        u32.AppendMenuW(m, MF_SEPARATOR, 0, None)
        u32.AppendMenuW(m, MF_STRING, ID_PAUSE, t('tray.resume') if not wall_running() else t('tray.pause'))
        sub = u32.CreatePopupMenu()
        for i, name in enumerate(scenes):
            label = t(f'scene.{name}.name') if t(f'scene.{name}.name') != f'scene.{name}.name' else name
            u32.AppendMenuW(sub, MF_STRING | (MF_CHECKED if name == c['scene'] else 0), ID_SCENE0 + i, label)
        u32.AppendMenuW(m, MF_POPUP, sub, t('tray.scenes'))
        u32.AppendMenuW(m, MF_SEPARATOR, 0, None)
        u32.AppendMenuW(m, MF_STRING | (MF_CHECKED if autostart.is_enabled() else 0), ID_AUTOSTART, t('tray.autostart'))
        u32.AppendMenuW(m, MF_STRING, ID_UPDATES, t('tray.updates'))
        u32.AppendMenuW(m, MF_SEPARATOR, 0, None)
        u32.AppendMenuW(m, MF_STRING, ID_QUIT, t('tray.quit'))
        return m, scenes

    def show_menu(self):
        m, scenes = self.menu()
        pt = wt.POINT(); u32.GetCursorPos(ctypes.byref(pt))
        u32.SetForegroundWindow(self.hwnd)                                   # sin esto el menú no se cierra al pulsar fuera
        cmd = u32.TrackPopupMenu(m, TPM_RIGHTBUTTON | TPM_RETURNCMD, pt.x, pt.y, 0, self.hwnd, None)
        u32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        u32.DestroyMenu(m)
        if cmd: self.command(cmd, scenes)

    def command(self, cmd, scenes):
        if cmd == ID_OPEN: spawn('ui')
        elif cmd == ID_PAUSE: self.bg(lambda: cli.wall('stop') if wall_running() else cli.wall('start'))
        elif cmd == ID_AUTOSTART:
            on = not autostart.is_enabled(); autostart.set_enabled(on); config.update(autostart=on)
        elif cmd == ID_UPDATES: self.bg(lambda: self.check_updates(force=True))
        elif cmd == ID_QUIT: u32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        elif ID_SCENE0 <= cmd < ID_SCENE0 + len(scenes): self.bg(lambda: cli.apply_scene(scenes[cmd - ID_SCENE0]))

    def bg(self, fn):
        def job():
            try: fn()
            except Exception: log.exception('acción de la bandeja fallida')
        threading.Thread(target=job, daemon=True).start()

    # ---------- actualizaciones ----------
    def check_updates(self, force=False):
        rel = update.check(force=force)
        if rel and rel.version != self.notified:
            self.notified = rel.version
            self.balloon(t('tray.update_title'), t('tray.update_text', version=rel.version))
        elif force and not rel:
            self.balloon(t('tray.tip'), t('up.uptodate'))

    def update_loop(self):
        time.sleep(20)                                                       # no competir con el arranque
        while True:
            try: self.check_updates()
            except Exception: log.exception('comprobación de actualizaciones fallida')
            time.sleep(3600)                                                 # check() solo consulta GitHub cada 24 h

    # ---------- bucle ----------
    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_APP_TRAY:
            if lparam == WM_LBUTTONDBLCLK or lparam == WM_LBUTTONUP: spawn('ui')
            elif lparam == WM_RBUTTONUP: self.show_menu()
            return 0
        if msg == self.created_msg: self.add_icon(); return 0               # el Explorador se reinició: se vuelve a poner el icono
        if msg == WM_CLOSE: u32.DestroyWindow(hwnd); return 0
        if msg == WM_DESTROY: u32.PostQuitMessage(0); return 0
        return u32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def run(self):
        msg = wt.MSG()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u32.TranslateMessage(ctypes.byref(msg)); u32.DispatchMessageW(ctypes.byref(msg))


def _single_instance():
    k32.CreateMutexW(None, False, 'Local\\AuraTrayHost')
    return k32.GetLastError() != 183                                         # ERROR_ALREADY_EXISTS


def main(background=False):
    paths.ensure_dirs()
    c = config.load(); i18n.setup(c['lang'])
    if not _single_instance():
        if not background: spawn('ui')                                       # abrir Aura de nuevo = abrir los ajustes de la instancia que ya corre
        return
    log.info('Aura %s arranca (background=%s)', __version__, background)
    if c['first_run_done']:
        cli.desk('start')
        try: cli.wall('start')
        except Exception: log.exception('no se pudo arrancar el fondo')
    else:
        spawn('ui')                                                          # primera vez: bienvenida
    tray = Tray(); tray.create()
    if c['autoupdate']: threading.Thread(target=tray.update_loop, daemon=True).start()
    tray.run()
    tray.remove_icon()
    cli.desk('stop'); cli.wall('stop')
    log.info('Aura se cierra')
