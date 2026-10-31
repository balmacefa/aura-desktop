r"""Genera las capturas del README (docs/img/*.png) sin datos personales: carpeta de datos temporal, escritorio despejado y SIN iconos
mientras dura la captura (se restauran al terminar). Uso: python tools/devtools/shots.py   (no tocar el ratón durante ~1 minuto)."""
import ctypes, ctypes.wintypes as wt, json, os, shutil, struct, subprocess, sys, tempfile, time, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC, OUT = ROOT / 'src', ROOT / 'docs' / 'img'
u, g = ctypes.windll.user32, ctypes.windll.gdi32
u.SetProcessDPIAware()
u.GetDC.restype = ctypes.c_void_p
u.FindWindowW.restype = u.FindWindowExW.restype = wt.HWND


def grab():
    """Pantalla completa como (ancho, alto, bytes BGRA)."""
    W, H = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    sdc = u.GetDC(None); mdc = g.CreateCompatibleDC(ctypes.c_void_p(sdc)); bmp = g.CreateCompatibleBitmap(ctypes.c_void_p(sdc), W, H)
    g.SelectObject(ctypes.c_void_p(mdc), ctypes.c_void_p(bmp)); g.BitBlt(ctypes.c_void_p(mdc), 0, 0, W, H, ctypes.c_void_p(sdc), 0, 0, 0x00CC0020 | 0x40000000)
    bi = struct.pack('<IiiHHIIiiII', 40, W, -H, 1, 32, 0, 0, 0, 0, 0, 0); buf = ctypes.create_string_buffer(W * H * 4)
    g.GetDIBits(ctypes.c_void_p(mdc), ctypes.c_void_p(bmp), 0, H, buf, bi, 0)
    g.DeleteObject(ctypes.c_void_p(bmp)); g.DeleteDC(ctypes.c_void_p(mdc)); u.ReleaseDC(None, ctypes.c_void_p(sdc))
    return W, H, buf.raw


def save_png(path, W, bgra, box):
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0; raw = bytearray()
    for y in range(y0, y1):
        row = bgra[(y * W + x0) * 4:(y * W + x1) * 4]; rgb = bytearray(w * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = row[2::4], row[1::4], row[0::4]
        raw += b'\0' + rgb
    chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b''))


def window_rect(prefix):
    found = []
    cb = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def each(h, _):
        b = ctypes.create_unicode_buffer(256); u.GetWindowTextW(h, b, 256)
        if u.IsWindowVisible(h) and b.value.startswith(prefix):
            r = wt.RECT(); u.GetWindowRect(h, ctypes.byref(r)); found.append((r.left + 8, r.top, r.right - 8, r.bottom - 8))
        return True
    u.EnumWindows(cb(each), 0)
    return found[0] if found else None


def toggle_icons():
    dv = u.FindWindowExW(u.FindWindowW('Progman', None), None, 'SHELLDLL_DefView', None)
    if dv: u.SendMessageW(dv, 0x111, 0x7402, 0)                              # «Mostrar iconos del escritorio» (alterna)


def shell(verb):
    subprocess.run(['powershell', '-NoProfile', '-Command', f'(New-Object -ComObject Shell.Application).{verb}()'], capture_output=True, creationflags=0x08000000); time.sleep(1.5)


def aura(env, *args, wait=True):
    cmd = [sys.executable, '-m', 'aura', *args]
    return subprocess.run(cmd, cwd=SRC, env=env, capture_output=True) if wait else subprocess.Popen(cmd, cwd=SRC, env=env)


def kill_ui(env): subprocess.run(['powershell', '-NoProfile', '-Command', "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'role ui' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"], capture_output=True)


def main():
    data = tempfile.mkdtemp(prefix='aura_shots_'); env = {**os.environ, 'AURA_DATA_DIR': data, 'AURA_BENCH': '1'}; Path(data).mkdir(exist_ok=True)
    conf = lambda **c: Path(data, 'aura.json').write_text(json.dumps({'scene': 'aurora', 'first_run_done': True, 'lang': 'en', 'autoupdate': False, 'widgets': {'claude': False}, **c}))
    conf(); shell('MinimizeAll'); toggle_icons()
    try:
        aura(env, 'start'); time.sleep(9)
        W, H, img = grab(); save_png(OUT / 'desktop.png', W, img, (0, 0, W, H - 98))                       # sin la barra de tareas
        for pane, name in (('background', 'panel-background'), ('general', 'panel-general')):
            kill_ui(env); conf(pane=pane, autoupdate=True); aura(env, 'ui'); time.sleep(3.5)
            r = window_rect('Aura'); W, H, img = grab()
            if r: save_png(OUT / f'{name}.png', W, img, r)
        kill_ui(env); aura(env, 'stop'); time.sleep(1)
        conf(first_run_done=False); aura(env, 'ui'); time.sleep(3.5)
        r = window_rect('Welcome') or window_rect('Aura'); W, H, img = grab()
        if r: save_png(OUT / 'welcome.png', W, img, r)
    finally:
        kill_ui(env); aura(env, 'quit'); aura(env, 'stop'); toggle_icons(); shell('UndoMinimizeAll'); shutil.rmtree(data, ignore_errors=True)
    print('capturas en', OUT, [p.name for p in OUT.glob('*.png')])


if __name__ == '__main__':
    main()
