"""Prueba de la técnica DwmThumbnailPlayer de Lively: ffplay como ventana normal fuera de pantalla y su imagen
proyectada en el escritorio con DwmRegisterThumbnail. Uso: python dwm_test.py <workerw|progman> <video> [segundos]"""
import ctypes, ctypes.wintypes as wt, os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aurawall as a

u, dwm = a.u32, ctypes.windll.dwmapi
which, video = sys.argv[1], sys.argv[2]
secs = int(sys.argv[3]) if len(sys.argv) > 3 else 40
W, H = a.screen_size()

proc = subprocess.Popen([shutil.which('ffplay'), '-noborder', '-loop', '0', '-an', '-loglevel', 'quiet', '-x', str(W), '-y', str(H),
                         '-left', str(-W - 200), '-top', '0', '-window_title', a.TITLE, video],
                        creationflags=0x08000000, env={**os.environ, 'SDL_RENDER_DRIVER': 'software'})
src = a.find_by_title(a.TITLE)
u.SetWindowLongW(src, -20, (u.GetWindowLongW(src, -20) & 0xFFFFFFFF) | 0x80)       # TOOLWINDOW: fuera de la barra de tareas
progman = u.FindWindowW('Progman', None)
# Ventana anfitriona PROPIA (DWM exige destino del mismo proceso) colgada del escritorio, como hace Lively
import tkinter as tk
root = tk.Tk(); root.overrideredirect(True); root.config(bg='black'); root.geometry(f'{W}x{H}+0+0'); root.update()
dest = u.GetParent(root.winfo_id()) or root.winfo_id()
host_parent = a.find_workerw() if which == 'workerw' else progman


class PROPS(ctypes.Structure):
    _fields_ = [('flags', wt.DWORD), ('dst', wt.RECT), ('src', wt.RECT), ('opacity', ctypes.c_ubyte),
                ('visible', wt.BOOL), ('client_only', wt.BOOL)]


dwm.DwmRegisterThumbnail.argtypes = [wt.HWND, wt.HWND, ctypes.POINTER(ctypes.c_void_p)]
dwm.DwmUpdateThumbnailProperties.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROPS)]
th = ctypes.c_void_p()
hr = dwm.DwmRegisterThumbnail(dest, src, ctypes.byref(th))
p = PROPS(0x1 | 0x4 | 0x8 | 0x10, wt.RECT(0, 0, W, H), wt.RECT(0, 0, 0, 0), 255, True, True)
hr2 = dwm.DwmUpdateThumbnailProperties(th, ctypes.byref(p))
print(which, 'register hr=', hex(hr & 0xFFFFFFFF), 'update hr=', hex(hr2 & 0xFFFFFFFF), flush=True)
# Solo ahora (con la miniatura ya registrada sobre una ventana de nivel superior) se cuelga del escritorio
u.SetParent.argtypes = [wt.HWND, wt.HWND]
u.SetParent(dest, host_parent)
u.SetWindowLongW(dest, -16, 0x40000000 | 0x10000000)            # WS_CHILD | WS_VISIBLE
u.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
u.SetWindowPos(dest, 0, 0, 0, W, H, 0x0004 | 0x0010 | 0x0040)
root.update()
print('host', hex(dest), 'parent', hex(u.GetParent(dest) or 0), 'visible', bool(u.IsWindowVisible(dest)), flush=True)
end = time.time() + secs
while time.time() < end:
    root.update(); time.sleep(0.05)
dwm.DwmUnregisterThumbnail(th)
proc.kill()
