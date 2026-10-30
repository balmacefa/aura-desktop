"""Mide un píxel del escritorio cada 100 ms para ver si un cambio de fondo es continuo. Uso: python transition_probe.py <segundos> [x y]"""
import ctypes, sys, time
ctypes.windll.user32.SetProcessDPIAware()
gdi, usr = ctypes.windll.gdi32, ctypes.windll.user32
usr.GetDC.restype = ctypes.c_void_p; gdi.GetPixel.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
x, y = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1500, 20)
dc, end, last = usr.GetDC(None), time.time() + float(sys.argv[1]), None
while time.time() < end:
    p = gdi.GetPixel(dc, x, y); rgb = (p & 255, p >> 8 & 255, p >> 16 & 255)
    if rgb != last: print(f'{time.strftime("%S")}.{int(time.time()*10)%10} {rgb}', flush=True); last = rgb
    time.sleep(0.1)
