import sys,os,time,ctypes,ctypes.wintypes as wt
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import aurawall as a
u=a.u32; u.CreateWindowExW.restype=wt.HWND
u.CreateWindowExW.argtypes=[wt.DWORD,wt.LPCWSTR,wt.LPCWSTR,wt.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wt.HWND,wt.HMENU,wt.HINSTANCE,wt.LPVOID]
w,h=a.screen_size()
hw=u.CreateWindowExW(0x80000|0x80|0x08000000,'STATIC','x',0x10000000|0x00000000,0,0,w,h,None,None,None,None)  # SS_BLACKRECT=4 -> use SS_WHITERECT=6
u.SetWindowLongW(hw,-16,0x10000000|0x6)
pm=u.FindWindowW('Progman',None); dv=u.FindWindowExW(pm,None,'SHELLDLL_DefView',None)
u.SetParent.argtypes=[wt.HWND,wt.HWND]; u.SetWindowPos.argtypes=[wt.HWND,wt.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wt.UINT]
u.SetParent(hw,pm)
u.SetWindowLongW(hw,-16,0x56000006)
u.SetLayeredWindowAttributes.argtypes=[wt.HWND,wt.DWORD,ctypes.c_ubyte,wt.DWORD]
print(u.SetLayeredWindowAttributes(hw,0,255,2))
u.SetWindowPos(hw,dv,0,0,w,h,0x10|0x40)
u.InvalidateRect(hw,None,True)
print(hex(hw),u.IsWindowVisible(hw),flush=True)
time.sleep(30); u.DestroyWindow(hw)
