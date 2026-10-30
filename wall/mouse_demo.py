import ctypes, math, time, sys
u=ctypes.windll.user32; u.SetProcessDPIAware()
w,h=u.GetSystemMetrics(0),u.GetSystemMetrics(1); end=time.time()+float(sys.argv[1] if len(sys.argv)>1 else 8)
while time.time()<end:
    t=time.time()*2.2
    u.SetCursorPos(int(w*.5+w*.3*math.cos(t)), int(h*.5+h*.28*math.sin(t*1.3))); time.sleep(.008)
