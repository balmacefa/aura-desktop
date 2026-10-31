"""Línea de comandos y despacho de roles de Aura.

  aura                         abre Aura (icono junto al reloj + fondo + widgets)
  aura ui                      abre la ventana de ajustes
  aura start [desk|wall|all]   arranca widgets y/o fondo        aura stop [desk|wall|all]
  aura status                  estado en JSON
  aura scene <nombre>          aplica un fondo (con fundido); `aura scenes` los lista
  aura video <archivo>         usa un vídeo/GIF propio como fondo
  aura palette c0 c1 c2 c3     colores (4 hex de 6 dígitos) y reaplica el fondo
  aura config                  muestra la configuración
  aura update                  comprueba e instala una versión nueva desde GitHub
  aura quit                    cierra todo Aura (icono, ajustes, widgets y fondo)
  aura doctor                  comprueba requisitos y estado (para soporte)
  aura version | logs | serve [puerto]

Internos (los lanza Aura): `--role ui|desk|live|tray`.
"""
import json, os, shutil, subprocess, sys, time

from . import __version__, autostart, config, log as _log, paths
from .procs import spawn
from .state import read_state, wall_running
from .win import alive, create_time

log = _log.get('cli')
CLAUDE_HINT = 'claude'


# ---------- widgets ----------
def desk_pids():
    """PID de los widgets. Archivo .pid (pid:instante de creación) + comprobación del proceso: sin subprocesos."""
    try:
        pid, ct = (int(x) for x in paths.DESK_PID.read_text().split(':'))
    except (OSError, ValueError):
        return []
    return [pid] if alive(pid) and create_time(pid) == ct else []


def desk(action):
    if action == 'start':
        if not desk_pids():
            spawn('desk'); log.info('widgets: arrancados')
    elif action == 'stop':
        for p in desk_pids():
            subprocess.run(['taskkill', '/PID', str(p), '/F'], capture_output=True, creationflags=0x08000000)
        log.info('widgets: detenidos')


# ---------- fondo ----------
def scenes():
    from . import live
    return live.scenes()


def wall(action):
    from . import live
    if action == 'start':
        c = config.load()
        live.start(c['scene'], ','.join(c['palette']))
    else:
        live.stop()


def wait_started(expected, previous_daemon, timeout):
    """Espera a que un demonio NUEVO publique el fondo esperado; si no, el fallo se ve (antes quedaba mudo sin consola)."""
    end = time.time() + timeout
    while time.time() < end:
        st = read_state()
        if st.get('file') == expected and st.get('daemon') != previous_daemon and alive(st.get('daemon')):
            return
        time.sleep(0.25)
    raise RuntimeError(f'the wallpaper did not start within {timeout} s; see the log: {paths.LOG_FILE}')


def apply_scene(name):
    """Guarda la escena y la aplica con fundido (sin parar el fondo anterior: este se retira cuando el nuevo termina de aparecer)."""
    from . import live
    if not live.valid_scene(name):
        raise ValueError(f'unknown scene: {name}. Available: {", ".join(scenes())}')
    c = config.update(scene=name)
    before = read_state().get('daemon')
    live.start(name, ','.join(c['palette']))
    wait_started('live:' + name, before, 45 if name.startswith('godot-') else 25)
    log.info('escena aplicada: %s', name)


def add_video(path):
    """Copia un vídeo/GIF a la carpeta de datos y lo aplica."""
    from . import live
    path = os.path.abspath(path)
    if not os.path.isfile(path) or os.path.splitext(path)[1].lower() not in live.VIDEO_EXT:
        raise ValueError(f'not a supported video/GIF: {path}')
    paths.ensure_dirs()
    dst = paths.USER_MEDIA / os.path.basename(path)
    if os.path.abspath(dst) != path: shutil.copy2(path, dst)
    apply_scene('video:' + dst.name)


def snapshot():
    """(widgets en marcha, fondo en marcha): lo que refresca el panel cada 5 s. Sin subprocesos."""
    return bool(desk_pids()), wall_running()


def status():
    d, w = snapshot()
    print(json.dumps({'version': __version__, 'desk_pids': desk_pids(), 'wall': {**read_state(), 'active': w}, 'scene': config.load()['scene']}, ensure_ascii=False))


def doctor():
    """Lista de comprobaciones para soporte. Devuelve 0 si todo lo imprescindible está bien."""
    from . import live
    import ctypes
    checks, bad = [], 0

    def add(name, ok, detail='', required=True):
        nonlocal bad
        checks.append((name, ok, detail, required))
        if required and not ok: bad += 1
    add('Windows', sys.platform == 'win32', sys.platform)
    add('Aura', True, f'{__version__} ({"installed build" if paths.FROZEN else "from source, Python " + sys.version.split()[0]})')
    try:
        import tkinter; add('tkinter', True, f'Tk {tkinter.TkVersion}')
    except ImportError:
        add('tkinter', False, 'reinstall Python with tcl/tk')
    add('Desktop (Progman)', bool(ctypes.windll.user32.FindWindowW('Progman', None)), 'needed for the animated wallpaper')
    browser, edge = live.find_browser()
    add('Microsoft Edge / Chrome', bool(browser), browser or 'needed for the interactive wallpapers')
    add('Godot 4', bool(live.find_godot()), live.find_godot() or 'only for the optional 3D scene', required=False)
    add('Scenes', bool(scenes()), ', '.join(scenes()))
    add('Fonts (Inter)', __import__('aura.fonts', fromlist=['x']).loaded, 'bundled', required=False)
    try:
        paths.ensure_dirs(); add('Data folder writable', os.access(paths.DATA, os.W_OK), str(paths.DATA))
    except OSError as e:
        add('Data folder writable', False, str(e))
    try:
        config.load(); add('Config', True, str(paths.CONF) if paths.CONF.exists() else 'will be created on first change')
    except Exception as e:
        add('Config', False, str(e))
    add('Start with Windows', autostart.is_enabled(), 'registry Run entry', required=False)
    st = read_state()
    add('Wallpaper', True, (st.get('file') or 'stopped') + (' (running)' if wall_running() else ''), required=False)
    for name, ok, detail, req in checks:
        print(f"  {'OK   ' if ok else ('FAIL ' if req else 'warn ')} {name:<24} {detail}")
    print(f"\nAura {__version__}: " + ('all good.' if not bad else f'{bad} required check(s) failed.'))
    return 1 if bad else 0


def quit_all():
    """Cierra todo Aura (icono, ajustes, widgets, fondo). Lo usa el instalador antes de actualizar o desinstalar."""
    import ctypes
    u = ctypes.windll.user32
    h = u.FindWindowW('AuraTrayWindow', None)
    if h:
        u.PostMessageW(h, 0x0010, 0, 0)                                    # WM_CLOSE: el anfitrión para widgets y fondo y se despide
        time.sleep(1.5)
    desk('stop'); wall('stop')
    if paths.FROZEN:                                                       # lo que quede (p. ej. la ventana de ajustes)
        subprocess.run(['taskkill', '/F', '/IM', 'Aura.exe', '/FI', f'PID ne {os.getpid()}'], capture_output=True, creationflags=0x08000000)


def run_role(role, args):
    """Procesos de fondo que Aura se lanza a sí misma (el mismo .exe o `python -m aura`)."""
    if role == 'ui':
        from . import ui; ui.main()
    elif role == 'desk':
        from . import desk as d; d.main()
    elif role == 'live':
        from . import live; live.main(args)
    elif role == 'tray':
        from . import tray; tray.main(background='--background' in args)
    else:
        raise SystemExit(f'unknown role: {role}')


def main(argv):
    if '--role' in argv:
        i = argv.index('--role'); run_role(argv[i + 1], argv[i + 2:]); return 0
    if not argv or argv == ['--background']:
        from . import tray; tray.main(background='--background' in argv); return 0
    a = argv; target = a[1] if len(a) > 1 else 'all'
    if a[0] == 'start':
        if target in ('desk', 'all'): desk('start')
        if target in ('wall', 'all'): wall('start')
    elif a[0] == 'stop':
        if target in ('desk', 'all'): desk('stop')
        if target in ('wall', 'all'): wall('stop')
    elif a[0] == 'ui':
        spawn('ui')
    elif a[0] == 'scene' and len(a) > 1:
        apply_scene(a[1]); print('scene applied:', a[1])
    elif a[0] == 'scenes':
        print(', '.join(scenes()))
    elif a[0] == 'video' and len(a) > 1:
        add_video(a[1])
    elif a[0] == 'palette' and len(a) == 5:
        config.update(palette=config.check_palette(a[1:5])); apply_scene(config.load()['scene'])
    elif a[0] == 'config':
        print(json.dumps(config.load(), indent=2, ensure_ascii=False))
    elif a[0] == 'status':
        status()
    elif a[0] == 'doctor':
        return doctor()
    elif a[0] in ('version', '--version'):
        print(__version__)
    elif a[0] == 'logs':
        print(paths.LOG_FILE)
    elif a[0] == 'quit':
        quit_all()
    elif a[0] == 'update':
        from . import update; return update.cli()
    elif a[0] == 'serve':
        from . import live; live.serve(int(a[1]) if len(a) > 1 else 8765)
    elif a[0] == 'desk-check':
        from . import desk as d; d.check()
    else:
        print(__doc__)
    return 0


def _attach_console():
    """El .exe es de ventana (sin consola): para `Aura.exe doctor` etc. se engancha a la terminal desde la que se llamó, si la hay."""
    if sys.stdout is not None and sys.stderr is not None: return
    import ctypes
    if ctypes.windll.kernel32.AttachConsole(-1):                            # ATTACH_PARENT_PROCESS
        try: sys.stdout = open('CONOUT$', 'w', encoding='utf-8'); sys.stderr = sys.stdout
        except OSError: pass


def entry():
    if paths.FROZEN and len(sys.argv) > 1 and '--role' not in sys.argv: _attach_console()
    for stream in (sys.stdout, sys.stderr):                                 # acentos correctos también al redirigir la salida
        try: stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError): pass
    try:
        sys.exit(main(sys.argv[1:]))
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as e:
        log.error('%s: %s', sys.argv[1:2], e)
        print(f'error: {e}', file=sys.stderr)
        sys.exit(1)
