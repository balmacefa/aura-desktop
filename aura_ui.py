"""Ajustes de Aura (tkinter, sin dependencias). Uso: pythonw aura_ui.py   |   python aura.py ui

Diseño según las pautas de Apple (settings.md, color.md, typography.md): ventana de ajustes con barra fija de paneles que
marca el activo, título que refleja el panel, último panel restaurado, claro/oscuro según Windows, selector de color del
sistema, interruptores, foco de teclado visible (Tab/Espacio, Ctrl+1…4, Esc para cerrar).
"""
import ctypes, os, subprocess, threading, tkinter as tk
from tkinter import colorchooser, filedialog

import aura

ctypes.windll.user32.SetProcessDPIAware()
SC = max(1.0, ctypes.windll.user32.GetDpiForSystem() / 96.0)
P = lambda n: int(n * SC)
_run = subprocess.run
subprocess.run = lambda *a, **k: _run(*a, **{'creationflags': 0x08000000, **k})   # sin consolas parpadeantes

STARTUP = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup', 'AuraDesk.lnk')
UI, UI_B = 'Segoe UI', 'Segoe UI Semibold'

# Tokens semánticos con variante clara y oscura. Texto sobre acento: oscuro en oscuro (≈7:1), blanco en claro (≈5:1).
DARK = dict(bg='#12121a', card='#1b1b27', hover='#262636', text='#f2f1f7', text2='#a6a4b8', sep='#2c2c3a',
            accent='#d97757', on_accent='#1a0e09', ok='#5fcf8a', off='#8a8899')
LIGHT = dict(bg='#f3f2f7', card='#ffffff', hover='#e8e7ef', text='#1c1b24', text2='#5d5b70', sep='#dcdae6',
             accent='#b5502f', on_accent='#ffffff', ok='#1f8f55', off='#6b6a7c')


def system_theme():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
        return LIGHT if winreg.QueryValueEx(k, 'AppsUseLightTheme')[0] else DARK
    except OSError:
        return DARK


T = system_theme()

PRESETS = {'Aura': ['0e0e18', 'd97757', '1d1b3a', '3a1b2a'], 'Océano': ['06141a', '1fb5a3', '0b2a3a', '143d2e'],
           'Aurora': ['0b1020', '7c5cff', '12304a', '1fbf8f'], 'Atardecer': ['1a0f1f', 'ff8a5c', '3a1b4a', 'c2416c'],
           'Grafito': ['111114', '6b6f7a', '1c1c22', '2e3038']}
WIDGETS = (('claude', 'Claude Code', 'Botón para abrir el chat'), ('clock', 'Reloj', 'Hora y fecha'),
           ('system', 'Sistema', 'CPU, memoria y disco'), ('calendar', 'Calendario', 'El mes actual con el día resaltado'),
           ('battery', 'Batería', 'Nivel, estado y tiempo restante'), ('pomodoro', 'Pomodoro', 'Foco de 25 min y pausa de 5'),
           ('network', 'Red', 'Velocidad de bajada y subida'))
PANES = ('Resumen', 'Fondo', 'Widgets', 'General')


def hex2rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def mix(a, b, t): return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Switch(tk.Canvas):
    """Interruptor on/off con foco de teclado (Espacio)."""
    def __init__(self, parent, value, command):
        super().__init__(parent, width=P(46), height=P(28), bg=T['card'], highlightthickness=2, highlightbackground=T['card'],
                         highlightcolor=T['accent'], takefocus=1, cursor='hand2')
        self.value, self.command = value, command
        self.bind('<Button-1>', self.toggle); self.bind('<space>', self.toggle); self.draw()

    def draw(self):
        self.delete('all')
        on = self.value
        self.create_oval(P(4), P(4), P(26), P(24), fill=T['accent'] if on else T['off'], outline='')
        self.create_oval(P(22), P(4), P(44), P(24), fill=T['accent'] if on else T['off'], outline='')
        self.create_rectangle(P(15), P(4), P(33), P(24), fill=T['accent'] if on else T['off'], outline='')
        x = P(34) if on else P(14)
        self.create_oval(x - P(8), P(6), x + P(8), P(22), fill=T['on_accent'] if on else T['card'], outline='')

    def toggle(self, _=None):
        self.value = not self.value; self.draw(); self.command(self.value)


class Slider(tk.Canvas):
    """Deslizador propio (el de Tk no permite colorear el control). Ratón o flechas ←/→."""
    def __init__(self, parent, var, lo, hi, length=220):
        super().__init__(parent, width=P(length), height=P(30), bg=T['bg'], highlightthickness=2, highlightbackground=T['bg'],
                         highlightcolor=T['accent'], takefocus=1, cursor='hand2')
        self.var, self.lo, self.hi, self.len = var, lo, hi, P(length)
        for ev in ('<Button-1>', '<B1-Motion>'): self.bind(ev, self.drag)
        self.bind('<Left>', lambda e: self.nudge(-1)); self.bind('<Right>', lambda e: self.nudge(1)); self.draw()

    def draw(self):
        self.delete('all'); a, b, y = P(12), self.len - P(12), P(15)
        x = a + (b - a) * (self.var.get() - self.lo) / (self.hi - self.lo)
        self.create_line(a, y, b, y, width=P(4), fill=T['sep'], capstyle='round')
        self.create_line(a, y, x, y, width=P(4), fill=T['accent'], capstyle='round')
        self.create_oval(x - P(9), y - P(9), x + P(9), y + P(9), fill=T['accent'], outline='')

    def drag(self, e):
        a, b = P(12), self.len - P(12)
        self.var.set(self.lo + (self.hi - self.lo) * min(1, max(0, (e.x - a) / (b - a)))); self.draw(); self.focus_set()

    def nudge(self, d): self.var.set(min(self.hi, max(self.lo, self.var.get() + d * (self.hi - self.lo) / 20))); self.draw()


class Panel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.configure(bg=T['bg']); self.resizable(False, False)
        self.conf = aura.load_conf(); self.msg = tk.StringVar(value='')
        self.panes, self.tabs = {}, {}
        self.bind('<Escape>', lambda e: self.destroy())
        for i, n in enumerate(PANES): self.bind(f'<Control-Key-{i + 1}>', lambda e, n=n: self.show(n))

        bar = tk.Frame(self, bg=T['bg']); bar.pack(fill='x', padx=P(18), pady=(P(14), 0))    # barra fija: siempre visible
        for n in PANES:
            b = self.button(bar, n, lambda n=n: self.show(n), 'tab'); b.pack(side='left', padx=(0, P(4))); self.tabs[n] = b
        tk.Frame(self, bg=T['sep'], height=1).pack(fill='x', pady=(P(6), 0))

        self.body = tk.Frame(self, bg=T['bg'], width=P(520), height=P(640)); self.body.pack(padx=P(18), pady=P(14))
        self.body.pack_propagate(False)
        tk.Label(self, textvariable=self.msg, bg=T['bg'], fg=T['text2'], font=(UI, 10), anchor='w').pack(fill='x', padx=P(18), pady=(0, P(12)))
        for n in PANES: self.panes[n] = getattr(self, 'build_' + n.lower())(tk.Frame(self.body, bg=T['bg']))
        self.show(self.conf.get('pane', 'Resumen')); self.poll()

    # ---------- piezas ----------
    def button(self, parent, text, command, kind='secondary'):
        base = dict(text=text, command=command, relief='flat', bd=0, cursor='hand2', takefocus=1, font=(UI_B if kind != 'plain' else UI, 11),
                    highlightthickness=2, padx=P(14), pady=P(7))
        look = {'primary': dict(bg=T['accent'], fg=T['on_accent'], activebackground=T['accent'], activeforeground=T['on_accent'], highlightbackground=T['accent']),
                'secondary': dict(bg=T['card'], fg=T['text'], activebackground=T['hover'], activeforeground=T['text'], highlightbackground=T['card']),
                'plain': dict(bg=T['bg'], fg=T['accent'], activebackground=T['bg'], activeforeground=T['accent'], highlightbackground=T['bg']),
                'tab': dict(bg=T['bg'], fg=T['text2'], activebackground=T['bg'], activeforeground=T['text'], highlightbackground=T['bg'])}[kind]
        return tk.Button(parent, **base, **look, highlightcolor=T['text'])

    def card(self, parent, **kw):
        return tk.Frame(parent, bg=T['card'], padx=P(14), pady=P(12), **kw)

    def heading(self, parent, text, sub=None):
        tk.Label(parent, text=text, bg=T['bg'], fg=T['text'], font=(UI_B, 15), anchor='w').pack(fill='x')
        if sub: tk.Label(parent, text=sub, bg=T['bg'], fg=T['text2'], font=(UI, 10), anchor='w', wraplength=P(500), justify='left').pack(fill='x', pady=(P(2), P(10)))

    def run(self, fn, ok='Listo'):
        self.msg.set('Trabajando…')
        def job():
            try: fn(); res = ok
            except Exception as e: res = f'No se pudo completar: {e}'
            self.after(0, lambda: (self.msg.set(res), self.update_state()))
        threading.Thread(target=job, daemon=True).start()

    def show(self, name):
        for n, f in self.panes.items(): f.pack_forget()
        for n, b in self.tabs.items():
            b.config(fg=T['text'] if n == name else T['text2'], font=(UI_B if n == name else UI, 11))
        self.panes[name].pack(fill='both', expand=True)
        self.title(f'Aura — {name}')                                        # el título refleja el panel activo
        self.conf['pane'] = name; aura.save_conf(self.conf)                 # y se restaura la próxima vez

    # ---------- Resumen ----------
    def build_resumen(self, f):
        self.heading(f, 'Resumen', 'El fondo animado y los widgets del escritorio.')
        self.status = {}
        for key, title in (('desk', 'Widgets'), ('wall', 'Fondo animado')):
            c = self.card(f); c.pack(fill='x', pady=(0, P(8)))
            dot = tk.Canvas(c, width=P(12), height=P(12), bg=T['card'], highlightthickness=0); dot.pack(side='left', padx=(0, P(10)))
            dot.create_oval(1, 1, P(11), P(11), fill=T['off'], outline='', tags='d')
            col = tk.Frame(c, bg=T['card']); col.pack(side='left')
            tk.Label(col, text=title, bg=T['card'], fg=T['text'], font=(UI_B, 12), anchor='w').pack(fill='x')
            sub = tk.Label(col, text='…', bg=T['card'], fg=T['text2'], font=(UI, 10), anchor='w'); sub.pack(fill='x')
            self.status[key] = (dot, sub)
        self.toggle_all = self.button(f, 'Iniciar todo', self.on_toggle_all, 'primary'); self.toggle_all.pack(anchor='w', pady=(P(10), 0))
        return f

    def on_toggle_all(self):
        running = self._state[0] or self._state[1]
        self.run(lambda: (aura.desk('stop'), aura.wall('stop')) if running else (aura.desk('start'), aura.wall('start')),
                 'Detenido' if running else 'En marcha')

    # ---------- Fondo ----------
    def build_fondo(self, f):
        self.heading(f, 'Fondo', 'Degradado animado propio o un vídeo/GIF tuyo. Se ve detrás de los iconos.')
        self.pal = list(self.conf['palette'])
        self.prev = tk.Canvas(f, width=P(260), height=P(173), bg=T['card'], highlightthickness=0); self.prev.pack(anchor='w')
        self.img = tk.PhotoImage(width=52, height=35)
        tk.Label(f, text='Vista previa aproximada', bg=T['bg'], fg=T['text2'], font=(UI, 10)).pack(anchor='w', pady=(P(2), P(8)))
        row = tk.Frame(f, bg=T['bg']); row.pack(anchor='w')
        for name, p in PRESETS.items():                                   # elegir antes que escribir (entering-data.md)
            b = self.button(row, name, lambda p=p: self.set_palette(p), 'secondary'); b.config(padx=P(9), pady=P(5), font=(UI, 10)); b.pack(side='left', padx=(0, P(5)))
        wells = tk.Frame(f, bg=T['bg']); wells.pack(anchor='w', pady=(P(10), 0))
        self.wells = []
        for i in range(4):
            w = tk.Canvas(wells, width=P(56), height=P(34), highlightthickness=2, highlightbackground=T['sep'], highlightcolor=T['text'],
                          takefocus=1, cursor='hand2'); w.pack(side='left', padx=(0, P(8)))
            w.bind('<Button-1>', lambda e, i=i: self.pick(i)); w.bind('<space>', lambda e, i=i: self.pick(i)); self.wells.append(w)
        sp = tk.Frame(f, bg=T['bg']); sp.pack(anchor='w', pady=(P(10), 0))
        tk.Label(sp, text='Velocidad', bg=T['bg'], fg=T['text'], font=(UI, 11)).pack(side='left')
        self.speed = tk.DoubleVar(value=self.conf['speed'])
        Slider(sp, self.speed, 0.003, 0.05).pack(side='left', padx=P(10))
        tk.Label(sp, text='lenta ← → rápida', bg=T['bg'], fg=T['text2'], font=(UI, 10)).pack(side='left')
        tk.Label(f, text='Fondos interactivos (reaccionan al ratón, a los clics y al uso de CPU)', bg=T['bg'], fg=T['text2'], font=(UI, 10)).pack(anchor='w', pady=(P(14), P(4)))
        live = tk.Frame(f, bg=T['bg']); live.pack(anchor='w')
        for name in aura.scenes():
            b = self.button(live, name.capitalize(), lambda n=name: self.run(lambda: aura.apply_scene(n), f'Escena {n} aplicada'), 'secondary')
            b.config(padx=P(9), pady=P(5), font=(UI, 10)); b.pack(side='left', padx=(0, P(5)), pady=(0, P(5)))
        vids = [v for v in sorted(os.listdir(aura.MEDIA)) if v.endswith(('.mp4', '.webm', '.gif')) and v != 'custom.mp4']
        tk.Label(f, text='Fondos en vídeo (renders de Blender y otros)', bg=T['bg'], fg=T['text2'], font=(UI, 10)).pack(anchor='w', pady=(P(8), P(4)))
        vrow = tk.Frame(f, bg=T['bg']); vrow.pack(anchor='w')
        for v in vids:
            b = self.button(vrow, os.path.splitext(v)[0].replace('_', ' ').capitalize(), lambda v=v: self.run(lambda: aura.apply_video(os.path.join(aura.MEDIA, v)), 'Fondo aplicado'), 'secondary')
            b.config(padx=P(9), pady=P(5), font=(UI, 10)); b.pack(side='left', padx=(0, P(5)))
        act = tk.Frame(f, bg=T['bg']); act.pack(anchor='w', pady=(P(12), 0))
        self.button(act, 'Aplicar fondo', lambda: self.run(self.generate, 'Fondo aplicado'), 'primary').pack(side='left', padx=(0, P(8)))
        self.button(act, 'Elegir vídeo o GIF…', self.choose_file, 'secondary').pack(side='left', padx=(0, P(8)))
        self.button(act, 'Restaurar original', lambda: self.run(lambda: aura.apply_video(os.path.join(aura.MEDIA, 'aura_flow.mp4')), 'Fondo original'), 'plain').pack(side='left')
        self.set_palette(self.pal, save=False)
        return f

    def set_palette(self, p, save=True):
        self.pal = [c.lstrip('#') for c in p]
        for w, c in zip(self.wells, self.pal): w.config(bg='#' + c)
        c = [hex2rgb(x) for x in self.pal]                                # esquinas: la espiral real es animada, esto solo orienta
        for y in range(35):
            row = []
            for x in range(52):
                top, bot = mix(c[0], c[1], x / 51), mix(c[2], c[3], x / 51)
                row.append('#%02x%02x%02x' % mix(top, bot, y / 34))
            self.img.put('{' + ' '.join(row) + '}', to=(0, y))
        self.big = self.img.zoom(P(5)); self.prev.delete('all'); self.prev.create_image(0, 0, image=self.big, anchor='nw')   # guardar la referencia o Tk la libera

    def pick(self, i):
        c = colorchooser.askcolor(color='#' + self.pal[i], title='Color del degradado')[1]   # selector del sistema
        if c: p = list(self.pal); p[i] = c.lstrip('#'); self.set_palette(p)

    def generate(self):
        self.conf['palette'], self.conf['speed'] = self.pal, round(self.speed.get(), 4); aura.save_conf(self.conf)
        dst = os.path.join(aura.MEDIA, 'custom.mp4'); aura.gen(out=dst); aura.apply_video(dst)

    def choose_file(self):
        f = filedialog.askopenfilename(filetypes=[('Vídeo/GIF', '*.mp4 *.mkv *.webm *.gif *.mov'), ('Todos', '*.*')])
        if f:
            def go():
                dst = os.path.join(aura.MEDIA, os.path.basename(f))
                if os.path.abspath(f) != dst: aura.shutil.copy2(f, dst)
                aura.apply_video(dst)
            self.run(go, 'Fondo aplicado')

    # ---------- Widgets ----------
    def build_widgets(self, f):
        self.heading(f, 'Widgets', 'Elige cuáles se muestran. Arrástralos para colocarlos; clic derecho abre su menú.')
        on = self.conf.get('widgets', {})
        box = tk.Frame(f, bg=T['card']); box.pack(fill='x')
        for i, (key, name, desc) in enumerate(WIDGETS):
            if i: tk.Frame(box, bg=T['sep'], height=1).pack(fill='x', padx=P(14))
            r = tk.Frame(box, bg=T['card'], padx=P(14), pady=P(7)); r.pack(fill='x')
            col = tk.Frame(r, bg=T['card']); col.pack(side='left')
            tk.Label(col, text=name, bg=T['card'], fg=T['text'], font=(UI, 11), anchor='w').pack(fill='x')
            tk.Label(col, text=desc, bg=T['card'], fg=T['text2'], font=(UI, 10), anchor='w').pack(fill='x')
            Switch(r, on.get(key, True), lambda v, k=key: self.set_widget(k, v)).pack(side='right')
        return f

    def set_widget(self, key, value):
        self.conf.setdefault('widgets', {})[key] = value; aura.save_conf(self.conf)
        self._restart = getattr(self, '_restart', None)
        if self._restart: self.after_cancel(self._restart)
        self._restart = self.after(700, lambda: self.run(lambda: (aura.desk('stop'), aura.desk('start')), 'Widgets actualizados'))

    # ---------- General ----------
    def build_general(self, f):
        self.heading(f, 'General', 'Arranque y mantenimiento.')
        box = self.card(f); box.pack(fill='x')
        col = tk.Frame(box, bg=T['card']); col.pack(side='left')
        tk.Label(col, text='Iniciar los widgets con Windows', bg=T['card'], fg=T['text'], font=(UI, 11), anchor='w').pack(fill='x')
        tk.Label(col, text='Crea un acceso en la carpeta Inicio; se puede quitar aquí.', bg=T['card'], fg=T['text2'], font=(UI, 10), anchor='w').pack(fill='x')
        Switch(box, os.path.exists(STARTUP), self.set_autostart).pack(side='right')
        acts = tk.Frame(f, bg=T['bg']); acts.pack(anchor='w', pady=(P(14), 0))
        self.button(acts, 'Abrir carpeta de Aura', lambda: os.startfile(aura.ROOT), 'secondary').pack(side='left', padx=(0, P(8)))
        self.button(acts, 'Restablecer posiciones', lambda: self.run(self.reset_positions, 'Posiciones restablecidas'), 'secondary').pack(side='left')
        return f

    def set_autostart(self, on):
        if on:
            ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');$s.TargetPath='%s';$s.Arguments='\"%s\"';"
                  "$s.WorkingDirectory='%s';$s.Save()" % (STARTUP, aura.PYW, aura.DESK, os.path.dirname(aura.DESK)))
            subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True)
        elif os.path.exists(STARTUP):
            os.remove(STARTUP)
        self.msg.set('Arranque con Windows ' + ('activado' if on else 'desactivado'))

    def reset_positions(self):
        cfg = os.path.join(os.environ['LOCALAPPDATA'], 'AuraDesk', 'config.json')
        if os.path.exists(cfg): os.remove(cfg)
        aura.desk('stop'); aura.desk('start')

    # ---------- estado ----------
    _state = (False, False)

    def poll(self): self.update_state(); self.after(5000, self.poll)

    def update_state(self):
        def job():
            d = bool(aura.desk_pids())
            w = bool(aura.json.loads(subprocess.run([aura.PY, aura.WALL, 'status'], capture_output=True, text=True).stdout or '{}').get('activo'))
            self.after(0, lambda: self.apply_state(d, w))
        threading.Thread(target=job, daemon=True).start()

    def apply_state(self, d, w):
        self._state = (d, w)
        n = sum(1 for k, _, _ in WIDGETS if self.conf.get('widgets', {}).get(k, True))
        for key, on, sub in (('desk', d, f'{n} widgets en el escritorio' if d else 'Detenidos'),
                             ('wall', w, os.path.basename(aura.load_conf()['video']) if w else 'Detenido')):
            dot, lab = self.status[key]
            dot.itemconfig('d', fill=T['ok'] if on else T['off'])
            lab.config(text=('Activo · ' if on else '') + sub if on else sub)              # estado en texto, no solo en color
        self.toggle_all.config(text='Detener todo' if d or w else 'Iniciar todo')


if __name__ == '__main__':
    Panel().mainloop()
