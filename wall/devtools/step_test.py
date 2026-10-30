import sys,os,subprocess,shutil,time,ctypes,ctypes.wintypes as wt
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import aurawall as a
u=a.u32
w,h=a.screen_size()
p=subprocess.Popen([shutil.which('ffplay'),'-noborder','-loop','0','-an','-loglevel','quiet','-x',str(w),'-y',str(h),'-window_title',a.TITLE,'media/aura_flow.mp4'],creationflags=0x08000000)
hw=a.find_by_title(a.TITLE); time.sleep(1)
ex=lambda s:print(s,hex(u.GetWindowLongW(hw,-20)&0xFFFFFFFF),'style',hex(u.GetWindowLongW(hw,-16)&0xFFFFFFFF),flush=True)
pm=u.FindWindowW('Progman',None); dv=u.FindWindowExW(pm,None,'SHELLDLL_DefView',None)
u.SetParent.argtypes=[wt.HWND,wt.HWND]; u.SetWindowPos.argtypes=[wt.HWND,wt.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wt.UINT]
ex('start'); u.SetWindowLongW(hw,-20,0x80000|0x80|0x08000000); ex('ex-toplevel'); u.SetParent(hw,pm); ex('parent')
u.SetWindowLongW(hw,-20,0x80000|0x80|0x08000000); ex('exset-first')
u.SetWindowLongW(hw,-16,0x56000000); ex('style')
u.SetLayeredWindowAttributes.argtypes=[wt.HWND,wt.DWORD,ctypes.c_ubyte,wt.DWORD]
print('sla',u.SetLayeredWindowAttributes(hw,0,255,2)); ex('sla')
u.SetWindowPos(hw,dv,0,0,w,h,0x10|0x40); ex('pos')
time.sleep(3); ex('later')
p.kill()
