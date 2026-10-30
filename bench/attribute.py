"""Atribución de coste: qué proceso de la escena activa consume la CPU. Uso: python bench/attribute.py [segundos]  (la escena ya debe estar activa)"""
import ctypes, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench                                                              # mismas utilidades de medida
import aura

secs = float(sys.argv[1]) if len(sys.argv) > 1 else 6
st = aura.read_state()
fam = [st['daemon']] + bench.family(st['player'])
names = {}
snap = bench.k32.CreateToolhelp32Snapshot(2, 0); pe = bench.PE(); pe.size = ctypes.sizeof(pe)
ok = bench.k32.Process32First(snap, ctypes.byref(pe))
while ok:
    names[pe.pid] = pe.exe.decode(errors='replace'); ok = bench.k32.Process32Next(snap, ctypes.byref(pe))
a = {p: bench.cpu_s(p) for p in fam}
t0 = time.time(); time.sleep(secs); dt = time.time() - t0
rows = sorted(((100 * ((bench.cpu_s(p) or a[p]) - a[p]) / dt, p) for p in fam if a[p] is not None), reverse=True)
total = sum(r for r, _ in rows)
print(f'escena {st.get("file")}: total {total:.1f} % de un núcleo, {len(fam)} procesos, {sum(bench.rss_mb(p) for p in fam):.0f} MB')
for pct, p in rows[:6]:
    print(f'  {pct:6.1f} %  {names.get(p, "?"):<16} pid {p:<6} {bench.rss_mb(p):6.0f} MB')
