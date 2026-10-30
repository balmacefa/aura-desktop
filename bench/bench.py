"""Benchmark de rendimiento de Aura (solo stdlib). Imprime UN objeto JSON en la última línea de stdout; el progreso va a stderr.

Mide el coste de tener Aura funcionando en reposo (sin tocar el ratón) con procesos reales:
  widgets_cpu_pct      CPU de AuraDesk (% de un núcleo)
  panel_cpu_pct        coste de refrescar el panel cada 5 s (la función que usa la interfaz)
  scene_cpu_pct        CPU del demonio + Edge de cada escena (media)
  idle_cost_cpu_pct    SUMA de los tres: métrica principal, menor es mejor
  fps_min / frame_p95_ms_max   fluidez medida DENTRO de la página (puerta de calidad)
  bridge_rps           peticiones/s al puente /state; status_ms, refresh_ms, *_rss_mb, switch_s: diagnóstico
  tests_ok             1 si pasan las pruebas unittest (puerta)
  scenes_ok            1 si todas las escenas arrancaron (puerta)

Uso:  python bench/bench.py [--scenes estela,orbes] [--seconds 8] [--quick]
Efectos: cambia el fondo del escritorio mientras mide y lo restaura al terminar. No mover el ratón durante la medición.
"""
import ctypes, ctypes.wintypes as wt, http.client, json, os, statistics, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ['AURA_BENCH'] = '1'                                            # activa /perf y los informes de fotogramas (solo en este benchmark)
import aura

k32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
NCPU = os.cpu_count() or 1


def log(*a): print(*a, file=sys.stderr, flush=True)


# ---------- procesos: CPU, memoria, árbol ----------
class FT(ctypes.Structure): _fields_ = [('lo', wt.DWORD), ('hi', wt.DWORD)]


def cpu_s(pid):
    h = k32.OpenProcess(0x1000, False, int(pid))
    if not h: return None
    c, e, k, u = FT(), FT(), FT(), FT()
    ok = k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)); k32.CloseHandle(h)
    return (((k.hi << 32) | k.lo) + ((u.hi << 32) | u.lo)) / 1e7 if ok else None


class PMC(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('pf', wt.DWORD)] + [(n, ctypes.c_size_t) for n in ('peak', 'ws', 'qpp', 'qp', 'qnpp', 'qnp', 'pf2', 'ppf')]


def rss_mb(pid):
    h = k32.OpenProcess(0x1000, False, int(pid))
    if not h: return 0.0
    m = PMC(); m.cb = ctypes.sizeof(m); ok = psapi.GetProcessMemoryInfo(h, ctypes.byref(m), m.cb); k32.CloseHandle(h)
    return m.ws / 2**20 if ok else 0.0


class PE(ctypes.Structure):
    _fields_ = [('size', wt.DWORD), ('usage', wt.DWORD), ('pid', wt.DWORD), ('heap', ctypes.c_size_t), ('mod', wt.DWORD), ('threads', wt.DWORD),
                ('ppid', wt.DWORD), ('pri', wt.LONG), ('flags', wt.DWORD), ('exe', ctypes.c_char * 260)]


def family(root_pid):
    """root_pid y todos sus descendientes."""
    snap = k32.CreateToolhelp32Snapshot(2, 0); pe = PE(); pe.size = ctypes.sizeof(pe); kids = {}
    ok = k32.Process32First(snap, ctypes.byref(pe))
    while ok:
        kids.setdefault(pe.ppid, []).append(pe.pid); ok = k32.Process32Next(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    out, todo = [], [int(root_pid)]
    while todo:
        p = todo.pop()
        if p not in out: out.append(p); todo.extend(kids.get(p, []))
    return out


def cpu_pct(pids, seconds):
    """% de UN núcleo consumido por pids durante `seconds`."""
    a = {p: cpu_s(p) for p in pids}; t0 = time.time(); time.sleep(seconds); dt = time.time() - t0
    return 100 * sum(max(0.0, (cpu_s(p) or a[p]) - a[p]) for p in pids if a[p] is not None) / dt


def covered_cpu(fam, seconds):
    """CPU de la escena mientras una ventana maximizada tapa el escritorio (el uso más habitual)."""
    import tkinter as tk
    root = tk.Tk(); root.title('bench-cover'); root.state('zoomed'); root.configure(bg='white'); root.update(); root.focus_force(); root.update()
    for _ in range(100): root.update(); time.sleep(0.02)                      # 2 s para que el demonio detecte la cobertura
    try: return cpu_pct(fam, seconds)
    finally: root.destroy()


def shell_windows(minimize):
    """Despeja el escritorio (o restaura las ventanas): sin esto una ventana a pantalla completa pausa el fondo y la medición sale vacía."""
    verb = 'MinimizeAll' if minimize else 'UndoMinimizeAll'
    subprocess.run(['powershell', '-NoProfile', '-Command', f'(New-Object -ComObject Shell.Application).{verb}()'], capture_output=True, creationflags=0x08000000)
    time.sleep(1.5)


def perf_dump(port):
    try:
        c = http.client.HTTPConnection('127.0.0.1', port, timeout=3); c.request('GET', '/perfdump'); r = c.getresponse()
        return json.loads(r.read()) if r.status == 200 else None
    except OSError:
        return None


# ---------- la acción que hace el panel cada 5 s ----------
def refresh():
    snap = getattr(aura, 'snapshot', None)
    if snap: return snap()
    d = bool(aura.desk_pids())
    w = json.loads(subprocess.run([aura.PY, aura.WALL, 'status'], capture_output=True, text=True, creationflags=0x08000000).stdout or '{}').get('activo')
    return d, w


def med_ms(fn, n=5):
    xs = []
    for _ in range(n):
        t = time.perf_counter(); fn(); xs.append((time.perf_counter() - t) * 1000)
    return statistics.median(xs)


def main():
    argv = sys.argv[1:]
    quick = '--quick' in argv
    seconds = float(argv[argv.index('--seconds') + 1]) if '--seconds' in argv else (4 if quick else 8)
    names = (argv[argv.index('--scenes') + 1] if '--scenes' in argv else ('estela' if quick else 'estela,orbes')).split(',')
    orig = aura.load_conf(); m = {}

    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'], cwd=ROOT, capture_output=True, creationflags=0x08000000)
    m['tests_ok'] = int(r.returncode == 0); log('pruebas:', 'ok' if r.returncode == 0 else 'FALLAN')

    m['status_ms'] = round(med_ms(lambda: subprocess.run([sys.executable, os.path.join(ROOT, 'aura.py'), 'status'], capture_output=True, creationflags=0x08000000)), 1)
    m['refresh_ms'] = round(med_ms(refresh), 1)
    m['panel_cpu_pct'] = round(m['refresh_ms'] / 5000 * 100, 3)                # la interfaz refresca cada 5 s; spawn-bound: ms de reloj ≈ ms de CPU
    log('status_ms', m['status_ms'], 'refresh_ms', m['refresh_ms'])

    aura.desk('stop'); time.sleep(1.0); aura.desk('start')                   # widgets con el código actual
    for _ in range(40):
        pids = aura.desk_pids()
        if pids: break
        time.sleep(0.25)
    time.sleep(2.0)
    if pids:
        m['widgets_cpu_pct'] = round(cpu_pct(pids, seconds), 2); m['widgets_rss_mb'] = round(sum(rss_mb(p) for p in pids), 1)
    else:
        m['widgets_cpu_pct'], m['widgets_rss_mb'] = 99.0, 0.0
    log('widgets_cpu_pct', m['widgets_cpu_pct'])

    cpus, fpss, p95s, rps, rss, sw, ok_all = [], [], [], [], [], [], 1
    shell_windows(True)
    try:
      for name in names:
        t = time.time()
        try: aura.apply_scene(name); started = 1
        except Exception as e: log('no arrancó', name, e); started = 0; ok_all = 0
        sw.append(time.time() - t)
        if not started: continue
        time.sleep(3.5)                                                       # fundido y asentamiento
        st = aura.read_state(); fam = [st['daemon']] + family(st['player']); port = st.get('port')
        d0 = perf_dump(port) if port else None; t0 = time.time()
        cpu = cpu_pct(fam, seconds); d1 = perf_dump(port) if port else None
        cpus.append(cpu); rss.append(sum(rss_mb(p) for p in fam))
        if d0 and d1: rps.append((d1['requests'] - d0['requests']) / (time.time() - t0))
        if d1 and d1['perf']:
            last = d1['perf'][-3:]; avg = statistics.mean(x['avg'] for x in last)
            fpss.append(1000 / avg); p95s.append(max(x['p95'] for x in last))
            m[f'{name}_fps'] = round(1000 / avg, 1)
        if name == names[0] and not name.startswith('godot-'):
            m['covered_cpu_pct'] = round(covered_cpu(fam, max(3, seconds / 2)), 2); log('covered_cpu_pct', m['covered_cpu_pct'])
        m[f'{name}_cpu_pct'] = round(cpu, 2); m[f'{name}_procs'] = len(fam)
        log(name, 'cpu%', round(cpu, 1), 'fps', m.get(f'{name}_fps'), 'procs', len(fam))
    finally:
        shell_windows(False)                                                  # devuelve las ventanas del usuario
    m['scene_cpu_pct'] = round(statistics.mean(cpus), 2) if cpus else 99.0
    m['scene_rss_mb'] = round(statistics.mean(rss), 1) if rss else 0.0
    m['fps_min'] = round(min(fpss), 1) if fpss else 0.0
    m['frame_p95_ms_max'] = round(max(p95s), 1) if p95s else 999.0
    m['bridge_rps'] = round(statistics.mean(rps), 1) if rps else 0.0
    m['switch_s'] = round(statistics.mean(sw), 2)
    m['scenes_ok'] = ok_all
    m['idle_cost_cpu_pct'] = round(m['widgets_cpu_pct'] + m['panel_cpu_pct'] + m['scene_cpu_pct'], 2)

    os.environ.pop('AURA_BENCH', None)                                         # el fondo del usuario se restaura SIN modo benchmark
    try:
        aura.save_conf(orig)
        if orig['mode'] == 'live': aura.apply_scene(orig['scene'])
        else: aura.apply_video(aura.video_path())
    except Exception as e:
        log('no se pudo restaurar el fondo original:', e)
    print(json.dumps(m))


if __name__ == '__main__':
    main()
