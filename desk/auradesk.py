"""AuraDesk: widgets de escritorio para Windows 11. Solo stdlib.

Widgets: Claude Code, reloj, sistema, calendario, batería, Pomodoro y red. Cuáles se muestran lo decide `aura.json`
(clave "widgets", editable desde el panel de Aura). Modelo tomado del análisis de Rainmeter (docs/ARQUITECTURA.md):
ventanas sin borde mandadas al fondo del orden Z, arrastrables, con posición persistente.

Uso:  pythonw auradesk.py            arranca los widgets (clic derecho sobre uno -> menú)
      python  auradesk.py --check    prueba las lecturas de sistema sin abrir ventanas
"""
import calendar, ctypes, ctypes.wintypes as wt, json, os, shutil, struct, subprocess, sys, time
import tkinter as tk
from collections import deque

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
u32.SetProcessDPIAware()
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'AuraDesk')
CFG = os.path.join(CFG_DIR, 'config.json')
try:                                                                        # registro compartido (aura_log.py en la raíz del proyecto)
    sys.path.insert(0, ROOT)
    import aura_log
    log = aura_log.get('desk')
except Exception:                                                           # sin el módulo (copia suelta) la app sigue funcionando
    import logging
    log = logging.getLogger('aura.desk')
S = max(1.0, u32.GetDpiForSystem() / 96.0)                      # escala de pantalla (200% aquí)

# Colores con un solo significado cada uno (color.md): ACCENT = dato/acción principal; WARN y BAD = estado, siempre con texto
BG, EDGE, TRACK = '#14141d', '#2c2c3a', '#2a2a38'
FG, DIM = '#f2f1f7', '#a6a4b8'                                  # contraste sobre BG: ~15:1 y ~7:1
ACCENT, ON_ACCENT, WARN, BAD, KEY = '#d97757', '#1a0e09', '#f2c14e', '#ff6b6b', '#010101'
UI, UI_B = 'Segoe UI', 'Segoe UI Semibold'                     # una sola familia: la del sistema (typography.md)

DIAS = ('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo')
MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre')


# ---------- lecturas de sistema (ctypes, sin psutil) ----------
class FT(ctypes.Structure):
    _fields_ = [('lo', wt.DWORD), ('hi', wt.DWORD)]


def _ft(x): return (x.hi << 32) | x.lo


_last = [None]


def cpu_percent():
    i, k, u = FT(), FT(), FT()
    k32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u))
    cur = (_ft(i), _ft(k) + _ft(u))                            # kernel incluye el tiempo idle
    prev, _last[0] = _last[0], cur
    if not prev or cur[1] == prev[1]:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (1 - (cur[0] - prev[0]) / (cur[1] - prev[1]))))


class MEM(ctypes.Structure):
    _fields_ = [('len', wt.DWORD), ('load', wt.DWORD), ('tp', ctypes.c_ulonglong), ('ap', ctypes.c_ulonglong),
                ('tpf', ctypes.c_ulonglong), ('apf', ctypes.c_ulonglong), ('tv', ctypes.c_ulonglong),
                ('av', ctypes.c_ulonglong), ('ae', ctypes.c_ulonglong)]


def ram():
    m = MEM(); m.len = ctypes.sizeof(m); k32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.load, (m.tp - m.ap) / 2**30, m.tp / 2**30


def disk(path='C:\\'):
    d = shutil.disk_usage(path)
    return 100 * d.used / d.total, d.used / 2**30, d.total / 2**30


class SPS(ctypes.Structure):
    _fields_ = [('ac', ctypes.c_ubyte), ('flag', ctypes.c_ubyte), ('pct', ctypes.c_ubyte), ('sv', ctypes.c_ubyte),
                ('life', wt.DWORD), ('full', wt.DWORD)]


def battery():
    """(porcentaje|None, con_corriente, cargando, segundos_restantes|None)"""
    s = SPS(); k32.GetSystemPowerStatus(ctypes.byref(s))
    if s.flag == 128 or s.pct == 255:                          # sin batería / desconocido
        return None, True, False, None
    return s.pct, s.ac == 1, bool(s.flag & 8), (None if s.life == 0xFFFFFFFF else s.life)


_net_prev = {}


def net_rates():
    """(bajada, subida) en bytes/s entre dos llamadas separadas ~1 s. GetIfTable: contadores de 32 bits por interfaz."""
    iph = ctypes.windll.iphlpapi
    size = wt.ULONG(0); iph.GetIfTable(None, ctypes.byref(size), False)
    buf = ctypes.create_string_buffer(size.value or 1)
    if iph.GetIfTable(buf, ctypes.byref(size), False) != 0:
        return 0, 0
    down = up = 0
    for i in range(struct.unpack_from('<I', buf, 0)[0]):
        o = 4 + i * 860                                         # sizeof(MIB_IFROW)
        idx, typ = struct.unpack_from('<II', buf, o + 512)
        oper, = struct.unpack_from('<I', buf, o + 544)
        if typ == 24 or oper not in (4, 5):                     # sin loopback ni interfaces caídas
            continue
        rin, rout = struct.unpack_from('<I', buf, o + 552)[0], struct.unpack_from('<I', buf, o + 576)[0]
        p = _net_prev.get(idx)
        if p:
            down += (rin - p[0]) & 0xFFFFFFFF; up += (rout - p[1]) & 0xFFFFFFFF
        _net_prev[idx] = (rin, rout)
    return down, up


def fmt_rate(b):
    for unit, d in (('MB/s', 2**20), ('KB/s', 2**10)):
        if b >= d: return f'{b / d:.1f} {unit}'
    return f'{b:.0f} B/s'


def level_color(pct): return BAD if pct >= 95 else WARN if pct >= 85 else ACCENT


# ---------- configuración ----------
def load_cfg():
    try:
        with open(CFG) as f: return json.load(f)
    except (OSError, ValueError): return {}


def save_cfg(cfg):
    os.makedirs(CFG_DIR, exist_ok=True)
    tmp = CFG + '.tmp'                                                      # atómico: un corte no deja posiciones corruptas
    with open(tmp, 'w') as f: json.dump(cfg, f)
    os.replace(tmp, CFG)


def enabled_widgets():
    try:
        with open(os.path.join(ROOT, 'aura.json'), encoding='utf-8') as f: return json.load(f).get('widgets', {})
    except (OSError, ValueError): return {}


# ---------- ventana base de widget ----------
class Widget(tk.Toplevel):
    def __init__(self, root, name, w, h, default_xy, cfg):
        super().__init__(root)
        self.name, self.cfg, self.root_, self.W, self.H = name, cfg, root, int(w * S), int(h * S)
        x, y = cfg.get(name) or (int(default_xy[0] * S), int(default_xy[1] * S))   # defaults en unidades lógicas
        self.overrideredirect(True)
        self.config(bg=KEY); self.attributes('-transparentcolor', KEY, '-alpha', 0.96)
        self.geometry(f'{self.W}x{self.H}+{x}+{y}')
        self.cv = tk.Canvas(self, width=self.W, height=self.H, bg=KEY, highlightthickness=0)
        self.cv.pack()
        r, p = 16 * S, 2
        pts = [p + r, p, self.W - p - r, p, self.W - p, p, self.W - p, p + r, self.W - p, self.H - p - r,
               self.W - p, self.H - p, self.W - p - r, self.H - p, p + r, self.H - p, p, self.H - p,
               p, self.H - p - r, p, p + r, p, p]
        self.panel = self.cv.create_polygon(pts, smooth=True, fill=BG, outline=EDGE, width=1)   # filo neutro: el acento no decora
        self.cv.bind('<ButtonPress-1>', self._press); self.cv.bind('<B1-Motion>', self._drag)
        self.cv.bind('<ButtonRelease-1>', self._release); self.cv.bind('<Button-3>', self._menu)
        self.update_idletasks(); self.hwnd = u32.GetParent(self.winfo_id()) or self.winfo_id()
        ex = u32.GetWindowLongW(self.hwnd, -20)
        u32.SetWindowLongW(self.hwnd, -20, ex | 0x80)              # TOOLWINDOW: sin icono en la barra
        self.to_bottom()

    def to_bottom(self):
        u32.SetWindowPos(self.hwnd, 1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)   # HWND_BOTTOM, NOSIZE|NOMOVE|NOACTIVATE

    def font(self, size, bold=False): return (UI_B if bold else UI, size)   # tk ya escala los puntos por DPI
    def px(self, n): return int(n * S)

    def label(self, x, y, text='', size=10, bold=False, color=DIM, anchor='w'):
        return self.cv.create_text(self.px(x) if anchor != 'e' else self.W - self.px(x), self.px(y), anchor=anchor,
                                   fill=color, font=self.font(size, bold), text=text)

    def bar(self, y, pct, color=ACCENT, x0=16):
        """Barra fina de progreso con pista; devuelve (pista, barra) para actualizar con set_bar."""
        a, b = self.px(x0), self.W - self.px(x0)
        t = self.cv.create_rectangle(a, self.px(y), b, self.px(y + 5), fill=TRACK, width=0)
        r = self.cv.create_rectangle(a, self.px(y), a, self.px(y + 5), fill=color, width=0)
        return t, r

    def set_bar(self, bar, y, pct, color=ACCENT, x0=16):
        a, b = self.px(x0), self.W - self.px(x0)
        self.cv.coords(bar[1], a, self.px(y), a + (b - a) * max(0, min(100, pct)) / 100, self.px(y + 5))
        self.cv.itemconfig(bar[1], fill=color)

    def _press(self, e): self._ox, self._oy, self._moved = e.x_root - self.winfo_x(), e.y_root - self.winfo_y(), False

    def _drag(self, e):
        self._moved = True
        self.geometry(f'+{e.x_root - self._ox}+{e.y_root - self._oy}')

    def _release(self, e):
        if self._moved:
            self.cfg[self.name] = [self.winfo_x(), self.winfo_y()]; save_cfg(self.cfg)
        else:
            self.on_click()
        self.to_bottom()

    def _menu(self, e):
        m = tk.Menu(self, tearoff=0)
        for text, fn in self.menu_items() + [('Abrir ajustes de Aura', open_settings), ('Salir de AuraDesk', self.root_.quit)]:
            m.add_command(label=text, command=fn)
        m.tk_popup(e.x_root, e.y_root)

    def menu_items(self): return []
    def on_click(self): pass
    def tick(self): pass


def open_settings():
    subprocess.Popen([shutil.which('pythonw') or sys.executable, os.path.join(ROOT, 'aura_ui.py')], cwd=ROOT, creationflags=0x00000008)


class Clock(Widget):
    def __init__(self, root, cfg):
        super().__init__(root, 'clock', 230, 90, (30, 124), cfg)
        self.t = self.label(115, 34, size=24, bold=True, color=FG, anchor='center')
        self.d = self.label(115, 66, size=10, anchor='center')

    def tick(self):
        t = time.localtime()
        self.cv.itemconfig(self.t, text=time.strftime('%H:%M:%S', t))
        self.cv.itemconfig(self.d, text=f'{DIAS[t.tm_wday].capitalize()} {t.tm_mday} de {MESES[t.tm_mon - 1]}')


class SystemW(Widget):
    ROWS = ('CPU', 'Memoria', 'Disco C:')

    def __init__(self, root, cfg):
        super().__init__(root, 'system', 230, 130, (30, 230), cfg)
        self.rows = []
        for i, name in enumerate(self.ROWS):
            y = 24 + i * 36
            self.label(16, y, name)
            self.rows.append((self.label(16, y, size=10, color=FG, anchor='e'), self.bar(y + 13, 0), y + 13))

    def tick(self):
        c = cpu_percent(); rl, ru, rt = ram(); dp, du, dt = disk()
        for (val, bar, by), pct, txt in zip(self.rows, (c, rl, dp), (f'{c:.0f} %', f'{ru:.1f} de {rt:.1f} GB', f'{du:.0f} de {dt:.0f} GB')):
            self.cv.itemconfig(val, text=txt); self.set_bar(bar, by, pct, level_color(pct))


class ClaudeButton(Widget):
    def __init__(self, root, cfg):
        super().__init__(root, 'claude', 230, 70, (30, 40), cfg)
        self.cv.create_oval(self.px(16), self.px(28), self.px(30), self.px(42), fill=ACCENT, width=0)
        self.label(46, 24, 'Claude Code', size=13, bold=True, color=FG)
        self.label(46, 46, 'Clic para abrir el chat')

    def on_click(self):
        script = os.path.join(HERE, 'claude-widget.ps1')
        subprocess.Popen(['pwsh', '-NoProfile', '-WindowStyle', 'Hidden', '-File', script], creationflags=0x08000000)


class CalendarW(Widget):
    def __init__(self, root, cfg):
        super().__init__(root, 'calendar', 230, 190, (1250, 440), cfg)
        self.title = self.label(16, 22, size=12, bold=True, color=FG)
        for i, d in enumerate('LMXJVSD'):                       # cabecera de días (lunes primero)
            self.label(16 + 14 + i * 33, 50, d, size=10, color=DIM, anchor='center')
        self.cells = [[self.cv.create_text(self.px(16 + 14 + c * 33), self.px(76 + r * 22), font=self.font(10), fill=FG) for c in range(7)]
                      for r in range(6)]
        self.mark = self.cv.create_oval(0, 0, 0, 0, fill=ACCENT, width=0, state='hidden')
        self.cv.tag_lower(self.mark, self.cells[0][0]); self.shown = None

    def tick(self):
        t = time.localtime()
        if self.shown == (t.tm_year, t.tm_mon, t.tm_mday): return
        self.shown = (t.tm_year, t.tm_mon, t.tm_mday)
        self.cv.itemconfig(self.title, text=f'{MESES[t.tm_mon - 1].capitalize()} {t.tm_year}')
        weeks = calendar.monthcalendar(t.tm_year, t.tm_mon)
        self.cv.itemconfig(self.mark, state='hidden')
        for r in range(6):
            for c in range(7):
                d = weeks[r][c] if r < len(weeks) else 0
                today = d == t.tm_mday
                self.cv.itemconfig(self.cells[r][c], text=str(d) if d else '', fill=ON_ACCENT if today else (DIM if c >= 5 else FG),
                                   font=self.font(10, today))
                if today:
                    x, y, rad = self.px(30 + c * 33), self.px(76 + r * 22), self.px(11)
                    self.cv.coords(self.mark, x - rad, y - rad, x + rad, y + rad); self.cv.itemconfig(self.mark, state='normal')


class BatteryW(Widget):
    def __init__(self, root, cfg):
        super().__init__(root, 'battery', 230, 80, (1250, 655), cfg)
        a = self.px(14)
        self.box = (a, a, a + self.px(52), a + self.px(52))
        self.cv.create_oval(*self.box, outline=TRACK, width=self.px(6))
        self.arc = self.cv.create_arc(*self.box, start=90, extent=0, style='arc', outline=ACCENT, width=self.px(6))
        self.pct = self.cv.create_text(a + self.px(26), a + self.px(26), fill=FG, font=self.font(10, True))
        self.l1 = self.label(84, 28, size=12, bold=True, color=FG)
        self.l2 = self.label(84, 50)

    def tick(self):
        pct, ac, charging, left = battery()
        if pct is None:
            self.cv.itemconfig(self.pct, text='—'); self.cv.itemconfig(self.l1, text='Sin batería'); self.cv.itemconfig(self.l2, text='Equipo de escritorio'); return
        color = ACCENT if pct > 20 or ac else BAD
        self.cv.itemconfig(self.arc, extent=-3.599 * pct, outline=color)
        self.cv.itemconfig(self.pct, text=f'{pct}')
        self.cv.itemconfig(self.l1, text='Cargando' if charging else 'Conectada' if ac else 'Con batería')
        rest = f'{left // 3600} h {left % 3600 // 60:02d} min restantes' if left and not ac else f'{pct} %'
        self.cv.itemconfig(self.l2, text=rest + ('  ·  nivel bajo' if pct <= 20 and not ac else ''))


class PomodoroW(Widget):
    FOCO, PAUSA = 25 * 60, 5 * 60

    def __init__(self, root, cfg):
        super().__init__(root, 'pomodoro', 230, 84, (1250, 740), cfg)
        self.mode, self.total, self.left, self.running = 'Foco', self.FOCO, self.FOCO, False
        self.stamp = time.time()
        self.t = self.label(16, 30, size=24, bold=True, color=FG)
        self.state = self.label(16, 30, size=10, anchor='e')
        self.hint = self.label(16, 62, size=10)
        self.pb = self.bar(70, 0, x0=16)

    def on_click(self):
        if self.left <= 0: self.switch()
        self.running = not self.running; self.stamp = time.time()

    def switch(self):
        self.mode, self.total = ('Pausa', self.PAUSA) if self.mode == 'Foco' else ('Foco', self.FOCO)
        self.left = self.total

    def menu_items(self):
        return [('Reiniciar Pomodoro', lambda: (setattr(self, 'running', False), setattr(self, 'mode', 'Pausa'), self.switch()))]

    def tick(self):
        now = time.time()
        if self.running:
            self.left = max(0, self.left - (now - self.stamp))
            if self.left <= 0:
                self.running = False
                try:
                    import winsound; winsound.MessageBeep()
                except ImportError: pass
        self.stamp = now
        m, s = divmod(int(self.left + 0.999), 60)
        self.cv.itemconfig(self.t, text=f'{m:02d}:{s:02d}')
        self.cv.itemconfig(self.state, text=self.mode, fill=ACCENT if self.mode == 'Foco' else FG)
        self.cv.itemconfig(self.hint, text='Terminado · clic para continuar' if self.left <= 0 else 'Clic para pausar' if self.running else 'Clic para empezar')
        self.set_bar(self.pb, 70, 100 * (1 - self.left / self.total))


class NetworkW(Widget):
    N = 40

    def __init__(self, root, cfg):
        super().__init__(root, 'network', 230, 96, (1250, 835), cfg)
        self.hist = deque([0] * self.N, maxlen=self.N)
        self.label(16, 20, 'Red')
        self.dn = self.label(16, 20, size=10, color=FG, anchor='e')
        self.label(16, 40, 'Subida')
        self.upl = self.label(16, 40, size=10, color=FG, anchor='e')
        self.line = self.cv.create_line(0, 0, 0, 0, fill=ACCENT, width=self.px(2), smooth=True)

    def tick(self):
        d, u = net_rates(); self.hist.append(d)
        self.cv.itemconfig(self.dn, text=f'↓ {fmt_rate(d)}'); self.cv.itemconfig(self.upl, text=f'↑ {fmt_rate(u)}')
        top = max(max(self.hist), 100 * 1024)
        x0, x1, y0, y1 = self.px(16), self.W - self.px(16), self.px(52), self.px(86)
        pts = []
        for i, v in enumerate(self.hist):
            pts += [x0 + (x1 - x0) * i / (self.N - 1), y1 - (y1 - y0) * v / top]
        self.cv.coords(self.line, *pts)


REGISTRY = (('claude', ClaudeButton), ('clock', Clock), ('system', SystemW), ('calendar', CalendarW),
            ('battery', BatteryW), ('pomodoro', PomodoroW), ('network', NetworkW))


def main():
    cfg, on = load_cfg(), enabled_widgets()
    log.info('widgets: arrancan %s', [n for n, _ in REGISTRY if on.get(n, True)])
    root = tk.Tk(); root.withdraw()
    widgets = [cls(root, cfg) for name, cls in REGISTRY if on.get(name, True)]

    def loop():
        for w in widgets: w.tick()
        root.after(1000, loop)
    loop(); root.mainloop()


if __name__ == '__main__':
    if '--check' in sys.argv:
        cpu_percent(); net_rates(); time.sleep(1)
        print({'cpu%': round(cpu_percent(), 1), 'ram': [round(x, 1) for x in ram()], 'disk': [round(x, 1) for x in disk()],
               'bateria': battery(), 'red B/s': net_rates(), 'escala': S, 'activos': enabled_widgets() or 'todos'})
    else:
        main()
