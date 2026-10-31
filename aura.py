"""aura: punto de entrada único de Aura (escritorio personalizado para Windows 10/11).

  python aura.py status                estado de widgets y fondo
  python aura.py start [desk|wall|all] arranca (por defecto all)
  python aura.py stop  [desk|wall|all]
  python aura.py gen [segundos]        genera el degradado animado propio (media/custom.mp4) con ffmpeg
  python aura.py install | uninstall   accesos del menú Inicio (reversible)
  python aura.py ui                    abre el panel de ajustes
  python aura.py scene <nombre>        fondo INTERACTIVO (reacciona al ratón, clics y CPU); `scenes` lista las disponibles
  python aura.py config                muestra la configuración (aura.json)
  python aura.py wallpaper <archivo>   usa un vídeo/GIF propio como fondo (se copia a wall/media) y lo aplica
  python aura.py palette c0 c1 c2 c3   genera un degradado con 4 colores hex (ej. 0e0e18 d97757 1d1b3a 3a1b2a) y lo aplica
  python aura.py speed <0.003-0.05>    velocidad del degradado (0.012 por defecto); regenera y aplica
  python aura.py doctor                comprueba requisitos y estado (para soporte)
  python aura.py version | logs        versión / ruta del registro
"""
__version__ = '1.1.0'
import ctypes, ctypes.wintypes as wt, json, os, re, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
DESK = os.path.join(ROOT, 'desk', 'auradesk.py')
WALL = os.path.join(ROOT, 'wall', 'aurawall.py')
LIVE = os.path.join(ROOT, 'wall', 'live', 'live.py')
MEDIA = os.path.join(ROOT, 'wall', 'media')
CONF = os.path.join(ROOT, 'aura.json')
DESK_PID = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'AuraDesk', 'desk.pid')
STATE = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'AuraWall', 'state.json')
DEFAULT = {'mode': 'video', 'scene': 'estela', 'video': 'wall/media/aura_flow.mp4', 'palette': ['0e0e18', 'd97757', '1d1b3a', '3a1b2a'], 'speed': 0.012, 'seconds': 30}
HEX6 = re.compile(r'^[0-9a-fA-F]{6}$')

import aura_log
log = aura_log.get('cli')


# ---------- configuración (validada y con escritura atómica) ----------
def atomic_write(path, text):
    """Escribe a un temporal y lo renombra: un corte a medias no deja el archivo corrupto."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


def check_palette(p):
    p = [str(x).lstrip('#') for x in p]
    if len(p) != 4 or not all(HEX6.match(x) for x in p):
        raise ValueError('la paleta necesita 4 colores hexadecimales de 6 dígitos (ej. 0e0e18)')
    return [x.lower() for x in p]


def load_conf():
    conf = dict(DEFAULT)
    try:
        with open(CONF, encoding='utf-8') as f:
            raw = json.load(f)
    except FileNotFoundError:
        return conf
    except (OSError, ValueError) as e:
        log.warning('aura.json ilegible (%s): se usan los valores por defecto', e)
        try: os.replace(CONF, CONF + '.bad')                                # se conserva para diagnóstico
        except OSError: pass
        return conf
    if isinstance(raw, dict):
        conf.update({k: v for k, v in raw.items() if k in DEFAULT or k in ('pane', 'widgets')})
    try: conf['palette'] = check_palette(conf['palette'])
    except (ValueError, TypeError): conf['palette'] = list(DEFAULT['palette'])
    try: conf['speed'] = min(0.05, max(0.003, float(conf['speed'])))
    except (TypeError, ValueError): conf['speed'] = DEFAULT['speed']
    if conf['mode'] not in ('video', 'live'): conf['mode'] = 'video'
    full = os.path.normpath(os.path.join(ROOT, *str(conf['video']).split('/')))
    if not full.startswith(ROOT + os.sep): conf['video'] = DEFAULT['video']     # nunca fuera de la carpeta del proyecto
    return conf


def save_conf(c):
    atomic_write(CONF, json.dumps(c, indent=2, ensure_ascii=False))


def video_path():
    return os.path.join(ROOT, *load_conf()['video'].split('/'))


VIDEO = video_path()
PY, PYW = sys.executable, shutil.which('pythonw') or sys.executable


# ---------- procesos ----------
def _alive(pid):
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid or 0))
    if not h: return False
    code = wt.DWORD(); ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code)); ctypes.windll.kernel32.CloseHandle(h)
    return code.value == 259


def read_state():
    try:
        with open(STATE, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return {}


def _ctime(pid):
    """Instante de creación del proceso (identifica el proceso aunque Windows reutilice el PID)."""
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid or 0))
    if not h: return None
    c, e, k, u = (wt.FILETIME() for _ in range(4))
    ok = ctypes.windll.kernel32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)); ctypes.windll.kernel32.CloseHandle(h)
    return ((c.dwHighDateTime << 32) | c.dwLowDateTime) if ok else None


def desk_pids(deep=False):
    """PIDs de los widgets. Rápido (archivo .pid + comprobación del proceso, sin subprocesos); `deep` añade un escaneo con PowerShell
    para detectar instancias antiguas que no escriben el archivo (solo se usa al arrancar o parar)."""
    try:
        with open(DESK_PID) as f: pid, ct = (int(x) for x in f.read().split(':'))
        if _alive(pid) and _ctime(pid) == ct: return [pid]
    except (OSError, ValueError):
        pass
    if not deep: return []
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
        "(Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object CommandLine -match 'auradesk\\.py').ProcessId"],
        capture_output=True, text=True).stdout.split()
    return [int(x) for x in out]


def snapshot():
    """(widgets en marcha, fondo en marcha): lo que refresca el panel cada 5 s. Sin subprocesos."""
    st = read_state()
    return bool(desk_pids()), bool(st.get('daemon') and _alive(st['daemon']))


def desk(action):
    if action == 'start':
        if not desk_pids(deep=True):
            subprocess.Popen([PYW, DESK], creationflags=0x00000008)
            log.info('widgets: arrancados')
    elif action == 'stop':
        for p in desk_pids(deep=True):
            subprocess.run(['taskkill', '/PID', str(p), '/F'], capture_output=True)
        log.info('widgets: detenidos')


def scenes():
    d = os.path.join(ROOT, 'wall', 'live', 'scenes')
    web = sorted(f[:-5] for f in os.listdir(d) if f.endswith('.html')) if os.path.isdir(d) else []
    g = os.path.join(ROOT, 'wall', 'godot')                                 # proyectos Godot: wall/godot/<nombre>/project.godot
    gd = sorted('godot-' + n for n in os.listdir(g) if os.path.exists(os.path.join(g, n, 'project.godot'))) if os.path.isdir(g) else []
    return web + gd


def wall(action):
    c = load_conf()
    if action == 'start' and c.get('mode') == 'live':                       # fondo interactivo (Aura Live)
        subprocess.run([PY, LIVE, 'start', c['scene'], ','.join(c['palette'])])
    elif action == 'start':
        if not os.path.exists(video_path()):
            raise RuntimeError('falta el fondo en vídeo: ejecuta  python aura.py gen')
        subprocess.run([PY, WALL, 'start', video_path()])
    else:
        subprocess.run([PY, LIVE, 'stop'])                                  # también para el vídeo: mata demonio y Edge


def wait_started(expected, previous_daemon, timeout):
    """Espera a que un demonio NUEVO publique el fondo esperado; si no, el fallo se ve (antes quedaba mudo bajo pythonw)."""
    end = time.time() + timeout
    while time.time() < end:
        st = read_state()
        if st.get('file') == expected and st.get('daemon') != previous_daemon and _alive(st.get('daemon')):
            return
        time.sleep(0.25)
    raise RuntimeError(f'el fondo no arrancó en {timeout} s; mira el registro: {aura_log.LOG_FILE}')


def ensure_ffmpeg():
    exe = shutil.which('ffmpeg')
    if not exe: raise RuntimeError('ffmpeg no está instalado (winget install Gyan.FFmpeg)')
    return exe


def gen(seconds=None, out=None):
    c = load_conf(); seconds = int(seconds or c['seconds']); out = out or os.path.join(MEDIA, 'custom.mp4')
    p = check_palette(c['palette'])                                         # validado: va a un filtro de ffmpeg
    os.makedirs(MEDIA, exist_ok=True)
    # Degradado espiral animado (por defecto azul noche, coral, ciruela); 1500x1000 = proporción de la pantalla
    src = 'gradients=s=1500x1000:d=%d:r=30:speed=%.4f:type=spiral:nb_colors=4:c0=0x%s:c1=0x%s:c2=0x%s:c3=0x%s' % ((seconds, c['speed']) + tuple(p))
    cmd = [ensure_ffmpeg(), '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', src, '-vf', 'gblur=sigma=18,noise=alls=6:allf=t',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', out]
    subprocess.run(cmd, check=True)
    log.info('degradado generado: %s', out)
    print('generado:', out, f'({os.path.getsize(out)//1024} KB)')


def apply_video(path):
    """Guarda el vídeo elegido en aura.json y lo aplica con fundido (sin parar el fondo anterior)."""
    path = os.path.abspath(path)
    if not os.path.isfile(path): raise ValueError(f'no existe el vídeo: {path}')
    c = load_conf(); c['video'] = os.path.relpath(path, ROOT).replace(os.sep, '/'); c['mode'] = 'video'; save_conf(c)
    before = read_state().get('daemon')
    subprocess.run([PY, WALL, 'start', path])
    wait_started(path, before, 25)
    log.info('fondo en vídeo aplicado: %s', path)


def apply_scene(name):
    """Fondo interactivo: guarda la escena en aura.json y la aplica con fundido."""
    if name not in scenes(): raise ValueError(f'escena desconocida: {name}. Disponibles: {", ".join(scenes())}')
    c = load_conf(); c['mode'], c['scene'] = 'live', name; save_conf(c)
    before = read_state().get('daemon')
    wall('start')
    wait_started('live:' + name, before, 45 if name.startswith('godot-') else 25)
    log.info('escena aplicada: %s', name)
    print('escena aplicada:', name)


def status():
    st = read_state(); d, w = snapshot()
    print(json.dumps({'desk_pids': desk_pids(), 'wall': {**st, 'activo': w}, 'video': os.path.exists(video_path())}, ensure_ascii=False))


def doctor():
    """Lista de comprobaciones para soporte. Devuelve 0 si todo lo imprescindible está bien."""
    checks, bad = [], 0

    def add(name, ok, detail='', required=True):
        nonlocal bad
        checks.append((name, ok, detail, required))
        if required and not ok: bad += 1
    add('Windows', sys.platform == 'win32', sys.platform)
    add('Python >= 3.10', sys.version_info >= (3, 10), sys.version.split()[0])
    try:
        import tkinter; add('tkinter', True, f'Tk {tkinter.TkVersion}')
    except ImportError:
        add('tkinter', False, 'reinstala Python marcando "tcl/tk"')
    add('Escritorio (Progman)', bool(ctypes.windll.user32.FindWindowW('Progman', None)), 'necesario para el fondo animado')
    add('ffmpeg / ffplay', bool(shutil.which('ffmpeg') and shutil.which('ffplay')), 'fondos en vídeo y degradado (winget install Gyan.FFmpeg)')
    edge = next((p for p in (r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe') if os.path.exists(p)), None)
    add('Microsoft Edge', bool(edge), 'fondos interactivos web', required=False)
    godot = any(f.lower().startswith('godot') and f.lower().endswith('win64.exe') for d in os.environ['PATH'].split(os.pathsep) if os.path.isdir(d) for f in os.listdir(d))
    add('Godot 4', godot, 'solo para la escena 3D (opcional)', required=False)
    add('Escenas', bool(scenes()), ', '.join(scenes()))
    try:
        os.makedirs(aura_log.LOG_DIR, exist_ok=True); add('Registro escribible', os.access(aura_log.LOG_DIR, os.W_OK), aura_log.LOG_FILE)
    except OSError as e:
        add('Registro escribible', False, str(e))
    try:
        load_conf(); add('aura.json', True, 'válido' if os.path.exists(CONF) else 'se creará al primer cambio')
    except Exception as e:
        add('aura.json', False, str(e))
    st = read_state()
    add('Fondo', True, (st.get('file') or 'detenido') + (' (activo)' if st.get('daemon') and _alive(st.get('daemon')) else ''), required=False)
    for name, ok, detail, req in checks:
        print(f"  {'OK ' if ok else ('FALTA' if req else 'aviso')}  {name:<24} {detail}")
    print(f"\nAura {__version__}: " + ('todo en orden.' if not bad else f'{bad} requisito(s) sin cumplir.'))
    return 1 if bad else 0


def main(a):
    target = a[1] if len(a) > 1 else 'all'
    if a[0] == 'start':
        if target in ('desk', 'all'): desk('start')
        if target in ('wall', 'all'): wall('start')
    elif a[0] == 'stop':
        if target in ('desk', 'all'): desk('stop')
        if target in ('wall', 'all'): wall('stop')
    elif a[0] == 'gen':
        gen(int(a[1]) if len(a) > 1 else None)
    elif a[0] == 'ui':
        subprocess.Popen([PYW, os.path.join(ROOT, 'aura_ui.py')], cwd=ROOT, creationflags=0x00000008)
    elif a[0] == 'scene' and len(a) > 1:
        apply_scene(a[1])
    elif a[0] == 'scenes':
        print(', '.join(scenes()))
    elif a[0] == 'config':
        print(json.dumps(load_conf(), indent=2, ensure_ascii=False))
    elif a[0] == 'wallpaper' and len(a) > 1 and os.path.isfile(a[1]):
        os.makedirs(MEDIA, exist_ok=True); dst = os.path.join(MEDIA, os.path.basename(a[1]))
        if os.path.abspath(a[1]) != dst: shutil.copy2(a[1], dst)
        apply_video(dst)
    elif a[0] == 'palette' and len(a) == 5:
        c = load_conf(); c['palette'] = check_palette(a[1:5]); save_conf(c)
        dst = os.path.join(MEDIA, 'custom.mp4'); gen(out=dst); apply_video(dst)
    elif a[0] == 'speed' and len(a) == 2:
        c = load_conf(); c['speed'] = min(0.05, max(0.003, float(a[1]))); save_conf(c)
        dst = os.path.join(MEDIA, 'custom.mp4'); gen(out=dst); apply_video(dst)
    elif a[0] == 'status':
        status()
    elif a[0] == 'doctor':
        return doctor()
    elif a[0] in ('version', '--version'):
        print(__version__)
    elif a[0] == 'logs':
        print(aura_log.LOG_FILE)
    elif a[0] in ('install', 'uninstall'):
        script = os.path.join(ROOT, 'desk', 'install.ps1')
        subprocess.run(['pwsh', '-NoProfile', '-File', script] + (['-Uninstall'] if a[0] == 'uninstall' else []))
    else:
        print(__doc__)
    return 0


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):                                 # acentos correctos también al redirigir la salida
        try: stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError): pass
    try:
        sys.exit(main(sys.argv[1:] or ['']))
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as e:
        log.error('%s: %s', sys.argv[1:2], e)
        print(f'error: {e}', file=sys.stderr)
        sys.exit(1)
