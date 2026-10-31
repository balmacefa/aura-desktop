"""Coste de Aura con el escritorio TAPADO, por tipo de fondo (web, Godot, vídeo), con una ventana maximizada de Tk y con Chrome real.
Uso: python bench/covered.py   (minimiza las ventanas, abre ventanas temporales y restaura tu fondo al terminar)"""
import os, subprocess, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench                                                              # utilidades de medida (fija AURA_BENCH=1: sin pausa por batería)
import aura

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
SECS = 6


def widgets_cpu():
    pids = aura.desk_pids()
    return bench.cpu_pct(pids, SECS) if pids else 0.0


def family_of(st):
    return [st['daemon']] + bench.family(st['player'])


def real_chrome():
    """Ventana de Chrome real, maximizada, con un perfil temporal (no toca tu sesión)."""
    prof = tempfile.mkdtemp(prefix='aura_chrome_')
    p = subprocess.Popen([CHROME, f'--user-data-dir={prof}', '--no-first-run', '--start-maximized', '--new-window', 'about:blank'])
    return p, prof


def main():
    orig = aura.load_conf(); rows = []
    bench.shell_windows(True)
    try:
        for label, apply in (('web (Estela)', lambda: aura.apply_scene('estela')), ('Godot (cristales 3D)', lambda: aura.apply_scene('godot-cristal')),
                             ('vídeo (Cristal)', lambda: aura.apply_video(os.path.join(aura.MEDIA, 'cristal.mp4')))):
            apply(); time.sleep(4.0)
            st = aura.read_state(); fam = family_of(st)
            vis = bench.cpu_pct(fam, SECS); vis_rss = sum(bench.rss_mb(p) for p in fam)
            tk = bench.covered_cpu(fam, SECS)
            row = {'fondo': label, 'visible_%': round(vis, 1), 'tapado_tk_%': round(tk, 1), 'ram_MB': round(vis_rss)}
            if label.startswith('web') and os.path.exists(CHROME):
                p, prof = real_chrome(); time.sleep(5.0)
                try:
                    row['tapado_chrome_%'] = round(bench.cpu_pct(fam, SECS), 1)
                    import ctypes; sys.path.insert(0, os.path.join(aura.ROOT, 'wall')); import aurawall
                    row['detecta_cobertura'] = aurawall.covered_by_fullscreen()
                finally:
                    subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True); time.sleep(1)
                    import shutil; shutil.rmtree(prof, ignore_errors=True)
            rows.append(row); print(row, file=sys.stderr, flush=True)
        w = widgets_cpu()
    finally:
        bench.shell_windows(False)
        os.environ.pop('AURA_BENCH', None)
        aura.save_conf(orig)
        (aura.apply_scene(orig['scene']) if orig['mode'] == 'live' else aura.apply_video(aura.video_path()))
    import json
    print(json.dumps({'widgets_%': round(w, 2), 'filas': rows}, ensure_ascii=False))


if __name__ == '__main__':
    main()
