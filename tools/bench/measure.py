"""Ejecuta bench.py N veces y guarda las muestras como instantánea para decide.py. Uso: python bench/measure.py <etiqueta> [repeticiones]"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE = os.path.join(ROOT, '.context', 'compound-engineering', 'ce-optimize', 'aura-idle-cost')
GATES = ('tests_ok', 'scenes_ok', 'scenes_visible', 'fps_min', 'frame_p95_ms_max')
label, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3
runs = []
for i in range(n):
    print(f'[{label}] medición {i + 1}/{n}', file=sys.stderr, flush=True)
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'bench', 'bench.py')], capture_output=True, text=True, cwd=ROOT, encoding='utf-8')
    if r.returncode:
        print(r.stderr[-1500:], file=sys.stderr); sys.exit(1)
    runs.append(json.loads(r.stdout.strip().splitlines()[-1]))
keys = sorted({k for r in runs for k in r})
mid = lambda xs: sorted(xs)[len(xs) // 2]
snap = {'gates': {k: mid([r[k] for r in runs if k in r]) for k in GATES},
        'metrics': {k: {'samples': [r[k] for r in runs if k in r]} for k in keys if k not in GATES}}
os.makedirs(os.path.join(STATE, label), exist_ok=True)
json.dump(snap, open(os.path.join(STATE, label, 'snapshot.json'), 'w'), indent=1)
show = ('idle_cost_cpu_pct', 'covered_cpu_pct', 'widgets_cpu_pct', 'panel_cpu_pct', 'scene_cpu_pct', 'bridge_rps', 'scene_rss_mb')
print(json.dumps({**{k: mid(snap['metrics'][k]['samples']) for k in show if k in snap['metrics']}, **snap['gates']}))
