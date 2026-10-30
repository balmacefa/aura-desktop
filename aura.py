"""aura: punto de entrada único del monolito Aura (escritorio personalizado para Windows 11).

  python aura.py status                estado de widgets y fondo
  python aura.py start [desk|wall|all] arranca (por defecto all; wall usa media/aura_flow.mp4)
  python aura.py stop  [desk|wall|all]
  python aura.py gen [segundos]        genera el fondo animado propio (media/aura_flow.mp4) con ffmpeg
  python aura.py install | uninstall   accesos del menú Inicio de los widgets (reversible)
  python aura.py ui                    abre el panel de administración (ventana)
  python aura.py scene <nombre>        fondo INTERACTIVO (reacciona al ratón, clics y CPU); `scenes` lista las disponibles
  python aura.py config                muestra la configuración (aura.json)
  python aura.py wallpaper <archivo>   usa un vídeo/GIF propio como fondo (se copia a wall/media) y lo aplica
  python aura.py palette c0 c1 c2 c3   genera un degradado con 4 colores hex (ej. 0e0e18 d97757 1d1b3a 3a1b2a) y lo aplica
  python aura.py speed <0.003-0.05>    velocidad del degradado (0.012 por defecto); regenera y aplica
"""
import os, shutil, subprocess, sys, json

ROOT = os.path.dirname(os.path.abspath(__file__))
DESK = os.path.join(ROOT, 'desk', 'auradesk.py')
WALL = os.path.join(ROOT, 'wall', 'aurawall.py')
LIVE = os.path.join(ROOT, 'wall', 'live', 'live.py')
MEDIA = os.path.join(ROOT, 'wall', 'media')
CONF = os.path.join(ROOT, 'aura.json')
DEFAULT = {'mode': 'video', 'scene': 'estela', 'video': 'wall/media/aura_flow.mp4', 'palette': ['0e0e18', 'd97757', '1d1b3a', '3a1b2a'], 'speed': 0.012, 'seconds': 30}


def load_conf():
    try:
        with open(CONF, encoding='utf-8') as f:
            return {**DEFAULT, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULT)


def save_conf(c):
    with open(CONF, 'w', encoding='utf-8') as f:
        json.dump(c, f, indent=2)


VIDEO = os.path.join(ROOT, *load_conf()['video'].split('/'))
PY, PYW = sys.executable, shutil.which('pythonw') or sys.executable


def desk_pids():
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
        "(Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object CommandLine -match 'auradesk\\.py').ProcessId"],
        capture_output=True, text=True).stdout.split()
    return [int(x) for x in out]


def desk(action):
    if action == 'start':
        if not desk_pids():
            subprocess.Popen([PYW, DESK], creationflags=0x00000008)
    elif action == 'stop':
        for p in desk_pids():
            subprocess.run(['taskkill', '/PID', str(p), '/F'], capture_output=True)


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
        if not os.path.exists(VIDEO):
            sys.exit('falta el fondo: ejecuta  python aura.py gen')
        subprocess.run([PY, WALL, 'start', VIDEO])
    else:
        subprocess.run([PY, LIVE, 'stop'])                                  # también para el vídeo: mata demonio y Edge


def gen(seconds=None, out=None):
    c = load_conf(); seconds = seconds or c['seconds']; out = out or VIDEO
    ffmpeg = shutil.which('ffmpeg') or sys.exit('ffmpeg no encontrado')
    os.makedirs(MEDIA, exist_ok=True)
    # Degradado espiral animado (por defecto azul noche, coral, ciruela); 1500x1000 = proporción de la pantalla
    p = c['palette']
    src = ('gradients=s=1500x1000:d=%s:r=30:speed=%s:type=spiral:nb_colors=4:c0=0x%s:c1=0x%s:c2=0x%s:c3=0x%s'
           % ((seconds, c['speed']) + tuple(p)))
    cmd = [ffmpeg, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', src, '-vf', 'gblur=sigma=18,noise=alls=6:allf=t',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', out]
    subprocess.run(cmd, check=True)
    print('generado:', out, f'({os.path.getsize(out)//1024} KB)')


def apply_video(path):
    """Guarda el vídeo elegido en aura.json y reinicia el fondo."""
    c = load_conf(); c['video'] = os.path.relpath(path, ROOT).replace(os.sep, '/'); c['mode'] = 'video'; save_conf(c)
    wall('stop'); subprocess.run([PY, WALL, 'start', path])


def apply_scene(name):
    """Fondo interactivo: guarda la escena en aura.json y reinicia."""
    if name not in scenes(): sys.exit(f'escena desconocida: {name}. Disponibles: {", ".join(scenes())}')
    c = load_conf(); c['mode'], c['scene'] = 'live', name; save_conf(c)
    wall('stop'); wall('start'); print('escena aplicada:', name)
    print('fondo aplicado:', c['video'])


def status():
    w = subprocess.run([PY, WALL, 'status'], capture_output=True, text=True).stdout.strip()
    print(json.dumps({'desk_pids': desk_pids(), 'wall': json.loads(w or '{}'), 'video': os.path.exists(VIDEO)}, ensure_ascii=False))


if __name__ == '__main__':
    a = sys.argv[1:] or ['']
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
        c = load_conf(); c['palette'] = [x.lstrip('#') for x in a[1:5]]; save_conf(c)
        dst = os.path.join(MEDIA, 'custom.mp4'); gen(out=dst); apply_video(dst)
    elif a[0] == 'speed' and len(a) == 2:
        c = load_conf(); c['speed'] = float(a[1]); save_conf(c)
        dst = os.path.join(MEDIA, 'custom.mp4'); gen(out=dst); apply_video(dst)
    elif a[0] == 'status':
        status()
    elif a[0] in ('install', 'uninstall'):
        script = os.path.join(ROOT, 'desk', 'install.ps1')
        subprocess.run(['pwsh', '-NoProfile', '-File', script] + (['-Uninstall'] if a[0] == 'uninstall' else []))
    else:
        print(__doc__)
