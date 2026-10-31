"""Decide conservar/revertir con el decisor del skill ce-optimize. Uso: python bench/decide.py <base> <candidato>"""
import json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, '.context', 'compound-engineering', 'ce-optimize', 'aura-idle-cost')
CANDIDATES = (r'~\.claude\skills\ce-optimize\scripts\decide.mjs', r'~\.agents\skills\ce-optimize\scripts\decide.mjs')
SKILL = next(p for p in (os.path.expanduser(c) for c in CANDIDATES) if os.path.exists(p))
SPEC = {'metric': {'primary': {'type': 'hard', 'name': 'idle_cost_cpu_pct', 'direction': 'minimize'},
                   'objectives': [{'name': 'covered_cpu_pct', 'direction': 'minimize', 'role': 'required', 'max_regression': {'type': 'relative', 'value': 0.15}}],
                   'degenerate_gates': [{'name': 'tests_ok', 'check': '== 1'}, {'name': 'scenes_ok', 'check': '== 1'}, {'name': 'scenes_visible', 'check': '== 1'},
                                        {'name': 'fps_min', 'check': '>= 28'}, {'name': 'frame_p95_ms_max', 'check': '<= 45'}]},
        'measurement': {'stability': {'mode': 'repeat', 'repeat_count': 3, 'aggregation': 'median', 'noise_threshold': 2.0}}}


def load(label):
    with open(os.path.join(STATE, label, 'snapshot.json')) as f:
        return json.load(f)


r = subprocess.run([shutil.which('node'), SKILL], input=json.dumps({'spec': SPEC, 'baseline': load(sys.argv[1]), 'candidate': load(sys.argv[2])}),
                   capture_output=True, text=True)
out = json.loads(r.stdout)
print(json.dumps({k: out.get(k) for k in ('decision', 'reason', 'primary_delta', 'comparisons') if k in out}, indent=1, ensure_ascii=False)[:1800])
