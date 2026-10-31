"""Ajustes de Aura (tkinter, sin dependencias).

Diseño según las pautas de Apple (settings.md, color.md, typography.md): barra fija de paneles que marca el activo, título que refleja el panel,
último panel restaurado, claro/oscuro según Windows, selector de color del sistema, interruptores, foco de teclado visible (Tab/Espacio,
Ctrl+1…5, Esc para cerrar). Primera vez: bienvenida con elección de fondo. Textos en assets/locales/*.json.
"""
import ctypes, os, shutil, threading, tkinter as tk, webbrowser
from tkinter import colorchooser, filedialog

from . import REPO, __version__, autostart, cli, config, fonts, i18n, log as _log, paths, update, win          # noqa: F401  (win: DPI)
from .i18n import t
from .procs import spawn

log = _log.get('ui')
SC = max(1.0, ctypes.windll.user32.GetDpiForSystem() / 96.0)
P = lambda n: int(n * SC)
UI, UI_B, UI_M = fonts.UI, fonts.UI_B, fonts.UI_M
SPONSORS = 'https://github.com/sponsors/' + REPO.split('/')[0]

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
PRESETS = {'aura': ['0e0e18', 'd97757', '1d1b3a', '3a1b2a'], 'ocean': ['06141a', '1fb5a3', '0b2a3a', '143d2e'], 'boreal': ['0b1020', '7c5cff', '12304a', '1fbf8f'],
           'sunset': ['1a0f1f', 'ff8a5c', '3a1b4a', 'c2416c'], 'graphite': ['111114', '6b6f7a', '1c1c22', '2e3038']}
WIDGETS = ('claude', 'clock', 'system', 'calendar', 'battery', 'pomodoro', 'network')
PANES = ('overview', 'background', 'colors', 'widgets', 'general')
WELCOME_SCENES = ('estela', 'aurora', 'orbes', 'constelacion', 'malla', 'degradado')


def hex2rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def mix(a, b, f): return tuple(round(a[i] + (b[i] - a[i]) * f) for i in range(3))


def scene_label(name):
    key = f'scene.{name}.name'
    return t(key) if t(key) != key else name.replace('godot-', '').capitalize()


def scene_desc(name):
    key = f'scene.{name}.desc'
    return t(key) if t(key) != key else ''


def media_label(name):
    stem = os.path.splitext(name)[0]
    key = f'video.{stem}.name'
    return t(key) if t(key) != key else stem.replace('_', ' ').capitalize()


class Switch(tk.Canvas):
    """Interruptor on/off con foco de teclado (Espacio)."""
    def __init__(self, parent, value, command, bg=None):
        bg = bg or T['card']
        super().__init__(parent, width=P(46), height=P(28), bg=bg, highlightthickness=2, highlightbackground=bg, highlightcolor=T['accent'], takefocus=1, cursor='hand2')
        self.value, self.command = value, command
        self.bind('<Button-1>', self.toggle); self.bind('<space>', self.toggle); self.draw()

    def draw(self):
        self.delete('all'); on = self.value; c = T['accent'] if on else T['off']
        self.create_oval(P(4), P(4), P(26), P(24), fill=c, outline=''); self.create_oval(P(22), P(4), P(44), P(24), fill=c, outline='')
        self.create_rectangle(P(15), P(4), P(33), P(24), fill=c, outline='')
        x = P(34) if on else P(14)
        self.create_oval(x - P(8), P(6), x + P(8), P(22), fill=T['on_accent'] if on else self['bg'], outline='')

    def toggle(self, _=None):
        self.value = not self.value; self.draw(); self.command(self.value)


class Card(tk.Frame):
    """Opción seleccionable con título y descripción. Estado «En uso» en texto (no solo color), foco de teclado y hover."""
    def __init__(self, parent, title, desc, command, wrap=215):
        super().__init__(parent, bg=T['card'], highlightthickness=2, highlightbackground=T['card'], highlightcolor=T['text'], takefocus=1, cursor='hand2')
        self.command, self.active, self.title = command, False, title
        self.t = tk.Label(self, text=title, bg=T['card'], fg=T['text'], font=(UI_B, 11), anchor='w')
        self.d = tk.Label(self, text=desc, bg=T['card'], fg=T['text2'], font=(UI, 10), anchor='w', wraplength=P(wrap), justify='left')
        self.t.pack(fill='x', padx=P(10), pady=(P(8), 0)); self.d.pack(fill='x', padx=P(10), pady=(0, P(8)))
        for w in (self, self.t, self.d):
            w.bind('<Button-1>', lambda e: self.command()); w.bind('<Enter>', lambda e: self.tint(T['hover'])); w.bind('<Leave>', lambda e: self.tint(T['card']))
        self.bind('<Return>', lambda e: self.command()); self.bind('<space>', lambda e: self.command())

    def tint(self, c):
        for w in (self, self.t, self.d): w.config(bg=c)

    def set_active(self, on):
        self.active = on
        self.config(highlightbackground=T['accent'] if on else T['card'])
        self.t.config(text=('✓ ' if on else '') + self.title, fg=T['accent'] if on else T['text'])


class Panel(tk.Tk):
    busy = False

    def __init__(self):
        super().__init__()
        self.conf = config.load(); i18n.setup(self.conf['lang'])
        self.configure(bg=T['bg']); self.resizable(False, False)
        try: self.iconbitmap(str(paths.ICONS / 'aura.ico'))
        except tk.TclError: pass
        self.msg = tk.StringVar(value='')
        self.bind('<Escape>', lambda e: self.destroy())
        self.build()
        self.after(30, self.style_titlebar)
        self.poll()
        if self.conf['autoupdate']: threading.Thread(target=self.bg_check, daemon=True).start()

    def style_titlebar(self):
        """Barra de título del color del tema (oscura en modo oscuro) en Windows 10 20H1+ / 11; en versiones antiguas se ignora."""
        try:
            self.update_idletasks(); hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            dwm = ctypes.windll.dwmapi; c = ctypes.c_int
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(c(1 if T is DARK else 0)), 4)                   # DWMWA_USE_IMMERSIVE_DARK_MODE
            r, g, b = hex2rgb(T['bg'])
            dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c(r | g << 8 | b << 16)), 4)                    # DWMWA_CAPTION_COLOR (Windows 11)
            tr, tg, tb = hex2rgb(T['text'])
            dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(c(tr | tg << 8 | tb << 16)), 4)                   # DWMWA_TEXT_COLOR
        except (OSError, AttributeError, ValueError):
            pass

    # ---------- estructura ----------
    def build(self):
        for w in self.winfo_children(): w.destroy()
        self.panes, self.tabs, self.cards, self.pending_restart = {}, {}, {}, None
        if not self.conf['first_run_done']:
            self.title(t('wel.title')); self.build_welcome(); return
        bar = tk.Frame(self, bg=T['bg']); bar.pack(fill='x', padx=P(18), pady=(P(14), 0))                 # barra fija: siempre visible
        for i, n in enumerate(PANES):
            b = self.button(bar, t(f'tab.{n}'), lambda n=n: self.show(n), 'tab'); b.pack(side='left', padx=(0, P(4))); self.tabs[n] = b
            self.bind(f'<Control-Key-{i + 1}>', lambda e, n=n: self.show(n))
        tk.Frame(self, bg=T['sep'], height=1).pack(fill='x', pady=(P(6), 0))
        self.banner = tk.Frame(self, bg=T['bg']); self.banner.pack(fill='x', padx=P(18))
        self.body = tk.Frame(self, bg=T['bg'], width=P(520), height=P(560)); self.body.pack(padx=P(18), pady=P(14)); self.body.pack_propagate(False)
        tk.Label(self, textvariable=self.msg, bg=T['bg'], fg=T['text2'], font=(UI, 10), anchor='w').pack(fill='x', padx=P(18), pady=(0, P(12)))
        for n in PANES: self.panes[n] = getattr(self, 'build_' + n)(tk.Frame(self.body, bg=T['bg']))
        pane = self.conf.get('pane', 'overview'); self.show(pane if pane in PANES else 'overview')

    # ---------- piezas ----------
    def button(self, parent, text, command, kind='secondary'):
        base = dict(text=text, command=command, relief='flat', bd=0, cursor='hand2', takefocus=1, font=(UI_B if kind != 'plain' else UI, 11), highlightthickness=2, padx=P(14), pady=P(7))
        look = {'primary': dict(bg=T['accent'], fg=T['on_accent'], activebackground=T['accent'], activeforeground=T['on_accent'], highlightbackground=T['accent']),
                'secondary': dict(bg=T['card'], fg=T['text'], activebackground=T['hover'], activeforeground=T['text'], highlightbackground=T['card']),
                'plain': dict(bg=T['bg'], fg=T['accent'], activebackground=T['bg'], activeforeground=T['accent'], highlightbackground=T['bg']),
                'tab': dict(bg=T['bg'], fg=T['text2'], activebackground=T['bg'], activeforeground=T['text'], highlightbackground=T['bg'])}[kind]
        b = tk.Button(parent, **base, **look, highlightcolor=T['text'])
        if kind in ('secondary', 'tab'):                                     # estado al pasar el cursor
            rest = look['bg']; b.bind('<Enter>', lambda e: b.config(bg=T['hover'])); b.bind('<Leave>', lambda e: b.config(bg=rest))
        return b

    def card(self, parent): return tk.Frame(parent, bg=T['card'], padx=P(14), pady=P(12))

    def heading(self, parent, text, sub=None):
        tk.Label(parent, text=text, bg=T['bg'], fg=T['text'], font=(UI_B, 15), anchor='w').pack(fill='x')
        if sub: tk.Label(parent, text=sub, bg=T['bg'], fg=T['text2'], font=(UI, 10), anchor='w', wraplength=P(500), justify='left').pack(fill='x', pady=(P(2), P(10)))

    def row(self, parent, title, desc, widget_factory):
        """Fila de ajustes: título + descripción a la izquierda, control a la derecha."""
        r = tk.Frame(parent, bg=T['card'], padx=P(14), pady=P(8)); r.pack(fill='x')
        col = tk.Frame(r, bg=T['card']); col.pack(side='left')
        tk.Label(col, text=title, bg=T['card'], fg=T['text'], font=(UI, 11), anchor='w').pack(fill='x')
        if desc: tk.Label(col, text=desc, bg=T['card'], fg=T['text2'], font=(UI, 10), anchor='w', wraplength=P(360), justify='left').pack(fill='x')
        widget_factory(r).pack(side='right')
        return r

    def run(self, fn, ok=''):
        if self.busy: self.msg.set(t('msg.busy')); return                    # evita transiciones superpuestas
        self.busy = True; self.msg.set(t('msg.applying'))

        def job():
            try: fn(); res = ok
            except (Exception, SystemExit) as e:                             # SystemExit: un sys.exit dentro del hilo lo mataría en silencio
                log.exception('acción del panel fallida'); res = t('msg.error', err=e)
            self.after(0, lambda: (setattr(self, 'busy', False), self.msg.set(res), self.update_state()))
        threading.Thread(target=job, daemon=True).start()

    def show(self, name):
        for f in self.panes.values(): f.pack_forget()
        for n, b in self.tabs.items(): b.config(fg=T['text'] if n == name else T['text2'], font=(UI_B if n == name else UI, 11))
        self.panes[name].pack(fill='both', expand=True)
        self.title(f'Aura — {t("tab." + name)}')                              # el título refleja el panel activo
        self.conf['pane'] = name; config.update(pane=name)                   # y se restaura la próxima vez

    # ---------- bienvenida ----------
    def build_welcome(self):
        self.geometry(''); f = tk.Frame(self, bg=T['bg'], padx=P(26), pady=P(22)); f.pack()
        try:
            self.logo = tk.PhotoImage(file=str(paths.ICONS / 'aura-512.png')).subsample(6, 6); tk.Label(f, image=self.logo, bg=T['bg']).pack(anchor='w')
        except tk.TclError: pass
        tk.Label(f, text=t('wel.title'), bg=T['bg'], fg=T['text'], font=(UI_B, 20), anchor='w').pack(fill='x', pady=(P(8), 0))
        tk.Label(f, text=t('wel.sub'), bg=T['bg'], fg=T['text2'], font=(UI, 11), anchor='w', wraplength=P(500), justify='left').pack(fill='x', pady=(P(4), P(14)))
        names = [n for n in WELCOME_SCENES if n in cli.scenes()]
        self.pick = tk.StringVar(value=names[0] if names else self.conf['scene'])
        g = tk.Frame(f, bg=T['bg']); g.pack(fill='x')
        self.wcards = {}
        for i, n in enumerate(names):
            c = Card(g, scene_label(n), scene_desc(n), lambda n=n: self.pick_welcome(n)); c.grid(row=i // 2, column=i % 2, padx=(0, P(8)), pady=(0, P(8)), sticky='nsew')
            g.columnconfigure(i % 2, weight=1, uniform='w'); self.wcards[n] = c
        self.pick_welcome(self.pick.get())
        self.wel_auto = tk.BooleanVar(value=True)
        r = tk.Frame(f, bg=T['card'], padx=P(14), pady=P(8)); r.pack(fill='x', pady=(P(4), P(14)))
        tk.Label(r, text=t('wel.autostart'), bg=T['card'], fg=T['text'], font=(UI, 11)).pack(side='left')
        Switch(r, True, lambda v: self.wel_auto.set(v)).pack(side='right')
        self.button(f, t('wel.start'), self.finish_welcome, 'primary').pack(anchor='e')
        tk.Label(f, textvariable=self.msg, bg=T['bg'], fg=T['text2'], font=(UI, 10)).pack(anchor='w', pady=(P(8), 0))

    def pick_welcome(self, name):
        self.pick.set(name)
        for n, c in self.wcards.items(): c.set_active(n == name)

    def finish_welcome(self):
        scene, auto = self.pick.get(), self.wel_auto.get()
        config.update(scene=scene, autostart=auto, first_run_done=True)
        try: autostart.set_enabled(auto)
        except OSError: log.exception('no se pudo configurar el inicio con Windows')
        self.conf = config.load()
        cli.desk('start')
        self.run(lambda: cli.apply_scene(scene), ok=t('bg.applied', name=scene_label(scene)))
        self.after(300, self.build)

    # ---------- Resumen ----------
    def build_overview(self, f):
        self.heading(f, t('ov.title'), t('ov.sub'))
        self.status = {}
        for key, title in (('desk', t('ov.widgets')), ('wall', t('ov.wallpaper'))):
            c = self.card(f); c.pack(fill='x', pady=(0, P(8)))
            dot = tk.Canvas(c, width=P(12), height=P(12), bg=T['card'], highlightthickness=0); dot.pack(side='left', padx=(0, P(10)))
            dot.create_oval(1, 1, P(11), P(11), fill=T['off'], outline='', tags='d')
            col = tk.Frame(c, bg=T['card']); col.pack(side='left')
            tk.Label(col, text=title, bg=T['card'], fg=T['text'], font=(UI_B, 12), anchor='w').pack(fill='x')
            sub = tk.Label(col, text='…', bg=T['card'], fg=T['text2'], font=(UI, 10), anchor='w'); sub.pack(fill='x')
            self.status[key] = (dot, sub)
        self.toggle_all = self.button(f, t('ov.start_all'), self.on_toggle_all, 'primary'); self.toggle_all.pack(anchor='w', pady=(P(10), 0))
        return f

    def on_toggle_all(self):
        d, w = self._state
        running = d or w
        self.run(lambda: (cli.desk('stop'), cli.wall('stop')) if running else (cli.desk('start'), cli.wall('start')), ok=t('ov.stopped_msg') if running else t('ov.started'))

    # ---------- Fondo ----------
    def build_background(self, f):
        from . import live
        self.heading(f, t('bg.title'), t('bg.sub'))

        def grid(title, items, cols=2, wrap=215):
            tk.Label(f, text=title, bg=T['bg'], fg=T['text'], font=(UI_B, 11), anchor='w').pack(fill='x', pady=(P(6), P(4)))
            g = tk.Frame(f, bg=T['bg']); g.pack(fill='x')
            for n, (key, name, desc) in enumerate(items):
                c = Card(g, name, desc, lambda k=key, nm=name: self.run(lambda: cli.apply_scene(k), ok=t('bg.applied', name=nm)), wrap=wrap)
                c.grid(row=n // cols, column=n % cols, padx=(0, P(8)), pady=(0, P(8)), sticky='nsew'); g.columnconfigure(n % cols, weight=1, uniform='c'); self.cards[key] = c

        grid(t('bg.interactive'), [(n, scene_label(n), scene_desc(n)) for n in cli.scenes()])
        tk.Label(f, text=t('bg.interactive_hint'), bg=T['bg'], fg=T['text2'], font=(UI, 10)).pack(anchor='w', pady=(0, P(4)))
        vids = [('video:' + n, media_label(n), t('bg.mine') if mine else t('bg.no_interaction')) for n, mine in live.media_files()]
        if vids: grid(t('bg.video'), vids, cols=3, wrap=140)
        self.button(f, t('bg.add_video'), self.choose_file, 'secondary').pack(anchor='w', pady=(P(2), 0))
        return f

    def refresh_selection(self):
        cur = config.load()['scene']
        for key, card in self.cards.items(): card.set_active(key == cur)

    def choose_file(self):
        f = filedialog.askopenfilename(filetypes=[(t('bg.video_filter'), '*.mp4 *.webm *.gif *.mkv *.mov'), (t('bg.all_files'), '*.*')])
        if f: self.run(lambda: cli.add_video(f), ok=t('bg.applied', name=os.path.basename(f)))

    # ---------- Colores ----------
    def build_colors(self, f):
        self.heading(f, t('col.title'), t('col.sub'))
        self.pal = list(self.conf['palette'])
        self.prev = tk.Canvas(f, width=P(260), height=P(173), bg=T['card'], highlightthickness=0); self.prev.pack(anchor='w')
        self.img = tk.PhotoImage(width=52, height=35)
        tk.Label(f, text=t('col.preview'), bg=T['bg'], fg=T['text2'], font=(UI, 10)).pack(anchor='w', pady=(P(2), P(8)))
        tk.Label(f, text=t('col.palettes'), bg=T['bg'], fg=T['text'], font=(UI_B, 11)).pack(anchor='w', pady=(0, P(4)))
        row = tk.Frame(f, bg=T['bg']); row.pack(anchor='w')
        for name, p in PRESETS.items():                                      # elegir antes que escribir
            b = self.button(row, t('pal.' + name), lambda p=p: self.set_palette(p), 'secondary'); b.config(padx=P(9), pady=P(5), font=(UI, 10)); b.pack(side='left', padx=(0, P(5)))
        tk.Label(f, text=t('col.pick'), bg=T['bg'], fg=T['text'], font=(UI_B, 11)).pack(anchor='w', pady=(P(12), P(4)))
        wells = tk.Frame(f, bg=T['bg']); wells.pack(anchor='w'); self.wells = []
        for i in range(4):
            w = tk.Canvas(wells, width=P(56), height=P(34), highlightthickness=2, highlightbackground=T['sep'], highlightcolor=T['text'], takefocus=1, cursor='hand2'); w.pack(side='left', padx=(0, P(8)))
            w.bind('<Button-1>', lambda e, i=i: self.pick_color(i)); w.bind('<space>', lambda e, i=i: self.pick_color(i)); self.wells.append(w)
        self.button(f, t('col.apply'), lambda: self.run(self.apply_colors, ok=t('col.applied')), 'primary').pack(anchor='w', pady=(P(16), 0))
        self.set_palette(self.pal)
        return f

    def apply_colors(self):
        config.update(palette=config.check_palette(self.pal)); cli.apply_scene(config.load()['scene'])

    def set_palette(self, p):
        self.pal = [c.lstrip('#') for c in p]
        for w, c in zip(self.wells, self.pal): w.config(bg='#' + c)
        c = [hex2rgb(x) for x in self.pal]                                   # esquinas: la escena real es animada, esto solo orienta
        for y in range(35):
            row = []
            for x in range(52):
                top, bot = mix(c[0], c[1], x / 51), mix(c[2], c[3], x / 51)
                row.append('#%02x%02x%02x' % mix(top, bot, y / 34))
            self.img.put('{' + ' '.join(row) + '}', to=(0, y))
        self.big = self.img.zoom(P(5)); self.prev.delete('all'); self.prev.create_image(0, 0, image=self.big, anchor='nw')   # guardar la referencia o Tk la libera

    def pick_color(self, i):
        c = colorchooser.askcolor(color='#' + self.pal[i], title=t('col.dialog'))[1]    # selector del sistema
        if c: p = list(self.pal); p[i] = c.lstrip('#'); self.set_palette(p)

    # ---------- Widgets ----------
    def build_widgets(self, f):
        self.heading(f, t('wd.title'), t('wd.sub'))
        on = self.conf.get('widgets', {})
        box = tk.Frame(f, bg=T['card']); box.pack(fill='x')
        names = [n for n in WIDGETS if n != 'claude' or shutil.which('claude')]
        for i, key in enumerate(names):
            if i: tk.Frame(box, bg=T['sep'], height=1).pack(fill='x', padx=P(14))
            self.row(box, t(f'wd.{key}.name'), t(f'wd.{key}.desc'), lambda r, k=key: Switch(r, on.get(k, True), lambda v, k=k: self.set_widget(k, v)))
        return f

    def set_widget(self, key, value):
        w = dict(config.load()['widgets']); w[key] = value; config.update(widgets=w)
        if self.pending_restart: self.after_cancel(self.pending_restart)
        self.pending_restart = self.after(700, lambda: self.run(lambda: (cli.desk('stop'), cli.desk('start')), ok=t('msg.widgets_updated')))

    # ---------- General ----------
    def build_general(self, f):
        self.heading(f, t('gen.title'), t('gen.sub'))
        box = tk.Frame(f, bg=T['card']); box.pack(fill='x')

        def langs(r):
            fr = tk.Frame(r, bg=T['card'])
            for code, label in (('auto', t('gen.lang_auto')), ('en', t('gen.lang_en')), ('es', t('gen.lang_es'))):
                b = self.button(fr, ('✓ ' if self.conf['lang'] == code else '') + label, lambda c=code: self.set_lang(c), 'secondary')
                b.config(padx=P(8), pady=P(4), font=(UI, 10)); b.pack(side='left', padx=(0, P(4)))
            return fr
        self.row(box, t('gen.language'), '', langs)
        tk.Frame(box, bg=T['sep'], height=1).pack(fill='x', padx=P(14))
        self.row(box, t('gen.autostart'), t('gen.autostart_desc'), lambda r: Switch(r, autostart.is_enabled(), self.set_autostart))
        tk.Frame(box, bg=T['sep'], height=1).pack(fill='x', padx=P(14))
        self.row(box, t('gen.updates'), t('gen.updates_desc'), lambda r: Switch(r, self.conf['autoupdate'], lambda v: config.update(autoupdate=v)))
        acts = tk.Frame(f, bg=T['bg']); acts.pack(anchor='w', pady=(P(14), 0))
        buttons = ((t('gen.check_now'), lambda: threading.Thread(target=self.bg_check, kwargs={'force': True}, daemon=True).start()),
                   (t('gen.open_data'), lambda: os.startfile(paths.DATA)), (t('gen.open_logs'), lambda: os.startfile(paths.LOG_FILE) if paths.LOG_FILE.exists() else None),
                   (t('gen.reset_pos'), lambda: self.run(self.reset_positions, ok=t('gen.pos_reset'))))
        for i, (text, fn) in enumerate(buttons):                             # dos por fila: en cualquier idioma caben sin cortarse
            self.button(acts, text, fn, 'secondary').grid(row=i // 2, column=i % 2, padx=(0, P(6)), pady=(0, P(6)), sticky='w')
        foot = tk.Frame(f, bg=T['bg']); foot.pack(anchor='w', pady=(P(18), 0))
        tk.Label(foot, text=t('gen.version', version=__version__) + '  ·  ' + t('gen.about'), bg=T['bg'], fg=T['text2'], font=(UI, 10)).pack(anchor='w')
        links = tk.Frame(foot, bg=T['bg']); links.pack(anchor='w', pady=(P(4), 0))
        self.button(links, t('gen.github'), lambda: webbrowser.open(f'https://github.com/{REPO}'), 'plain').pack(side='left')
        self.button(links, t('gen.support'), lambda: webbrowser.open(SPONSORS), 'plain').pack(side='left')
        return f

    def set_lang(self, code):
        config.update(lang=code); self.conf = config.load(); i18n.setup(code); self.build()

    def set_autostart(self, on):
        try: autostart.set_enabled(on); config.update(autostart=on); self.msg.set(t('msg.autostart_on' if on else 'msg.autostart_off'))
        except OSError as e: self.msg.set(t('msg.error', err=e))

    def reset_positions(self):
        paths.DESK_CFG.unlink(missing_ok=True); cli.desk('stop'); cli.desk('start')

    # ---------- actualizaciones ----------
    def bg_check(self, force=False):
        if force: self.after(0, lambda: self.msg.set(t('up.checking')))
        try: rel = update.check(force=force)
        except Exception: log.exception('comprobación fallida'); self.after(0, lambda: self.msg.set(t('up.offline'))); return
        if rel: self.after(0, lambda: self.show_update(rel))
        elif force: self.after(0, lambda: self.msg.set(t('up.uptodate')))

    def show_update(self, rel):
        for w in self.banner.winfo_children(): w.destroy()
        b = tk.Frame(self.banner, bg=T['card'], padx=P(12), pady=P(8)); b.pack(fill='x', pady=(P(10), 0))
        tk.Label(b, text=t('up.available', version=rel.version), bg=T['card'], fg=T['accent'], font=(UI_B, 11)).pack(side='left')
        self.button(b, t('up.skip'), lambda: (config.update(skipped_version=rel.version), self.clear_banner()), 'plain').pack(side='right')
        self.button(b, t('up.later'), self.clear_banner, 'plain').pack(side='right')
        self.button(b, t('up.install'), lambda: self.do_update(rel), 'primary').pack(side='right', padx=(0, P(6)))

    def clear_banner(self):
        for w in self.banner.winfo_children(): w.destroy()

    def do_update(self, rel):
        def job():
            try:
                path = update.download(rel, lambda a, b: self.after(0, lambda: self.msg.set(t('up.downloading', pct=a * 100 // max(b, 1)))))
                self.after(0, lambda: self.msg.set(t('up.installing'))); update.install(path); self.after(800, self.destroy)
            except Exception as e:
                log.exception('actualización fallida'); self.after(0, lambda: self.msg.set(t('up.failed', err=e)))
        threading.Thread(target=job, daemon=True).start()

    # ---------- estado ----------
    _state = (False, False)

    def poll(self): self.update_state(); self.after(5000, self.poll)

    def update_state(self):
        def job():
            d, w = cli.snapshot()                                            # lectura de archivos y comprobación de procesos: sin subprocesos
            self.after(0, lambda: self.apply_state(d, w))
        threading.Thread(target=job, daemon=True).start()

    def apply_state(self, d, w):
        self._state = (d, w)
        if not hasattr(self, 'status') or not self.winfo_exists() or not self.conf['first_run_done']: return
        c = config.load(); n = sum(1 for k in WIDGETS if c['widgets'].get(k, True) and (k != 'claude' or shutil.which('claude')))
        scene = c['scene']; name = media_label(scene[6:]) if scene.startswith('video:') else scene_label(scene)
        for key, on, sub in (('desk', d, t('ov.widgets_n', n=n) if d else t('ov.stopped')), ('wall', w, name if w else t('ov.stopped'))):
            dot, lab = self.status[key]
            dot.itemconfig('d', fill=T['ok'] if on else T['off'])
            lab.config(text=(t('ov.active') + ' · ' if on else '') + sub)                                   # estado en texto, no solo en color
        self.toggle_all.config(text=t('ov.stop_all') if d or w else t('ov.start_all')); self.refresh_selection()


def single_instance():
    """Un solo panel: si ya hay uno abierto se le da el foco y este proceso termina."""
    k32 = ctypes.windll.kernel32
    k32.CreateMutexW(None, False, 'Local\\AuraSettingsPanel')
    if k32.GetLastError() == 183:                                            # ERROR_ALREADY_EXISTS
        u = ctypes.windll.user32; found = []
        cb = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(
            lambda h, _: (found.append(h) if (lambda b: (u.GetWindowTextW(h, b, 256), b.value)[1])(ctypes.create_unicode_buffer(256)).startswith(('Aura', t('wel.title'))) else None) or True)
        u.EnumWindows(cb, 0)
        if found: u.ShowWindow(found[0], 9); u.SetForegroundWindow(found[0])
        return False
    return True


def main():
    paths.ensure_dirs()
    if single_instance():
        log.info('panel abierto')
        Panel().mainloop()
