import ctypes, ctypes.wintypes as wt
u=ctypes.windll.user32
u.GetWindowLongW.restype=ctypes.c_long
P=ctypes.WINFUNCTYPE(wt.BOOL,wt.HWND,wt.LPARAM)
def info(h):
    c=ctypes.create_unicode_buffer(256);u.GetClassNameW(h,c,256)
    t=ctypes.create_unicode_buffer(256);u.GetWindowTextW(h,t,256)
    r=wt.RECT();u.GetWindowRect(h,ctypes.byref(r))
    return f"{h:#x} {c.value!r} {t.value!r} st={u.GetWindowLongW(h,-16)&0xFFFFFFFF:#x} ex={u.GetWindowLongW(h,-20)&0xFFFFFFFF:#x} vis={bool(u.IsWindowVisible(h))} rect={r.left},{r.top},{r.right},{r.bottom}"
def kids(h,d):
    out=[]
    u.EnumChildWindows(h,P(lambda x,_:(out.append(x),True)[1]),0)
    for x in out:
        if u.GetParent(x)==h:
            print('  '*d+info(x)); kids(x,d+1)
tops=[]
u.EnumWindows(P(lambda x,_:(tops.append(x),True)[1]),0)
for h in tops:
    c=ctypes.create_unicode_buffer(256);u.GetClassNameW(h,c,256)
    if c.value in('Progman','WorkerW'):
        print(info(h)); kids(h,1)
