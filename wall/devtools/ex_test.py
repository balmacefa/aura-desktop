import sys,os,subprocess,shutil,time,ctypes
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import aurawall as a
u=a.u32
w,h=a.screen_size()
p=subprocess.Popen([shutil.which('ffplay'),'-noborder','-loop','0','-an','-loglevel','quiet','-x',str(w),'-y',str(h),'-window_title',a.TITLE,'media/aura_flow.mp4'],creationflags=0x08000000)
hw=a.find_by_title(a.TITLE); time.sleep(1)
for label,fn in [('top-level',lambda:None),('child',lambda:(u.SetParent(hw,u.FindWindowW('Progman',None))))]:
    fn()
    ctypes.windll.kernel32.SetLastError(0)
    r=u.SetWindowLongW(hw,-20,0x80000|0x80|0x08000000)
    print(label,'ret',hex(r&0xFFFFFFFF),'err',ctypes.windll.kernel32.GetLastError(),'ex now',hex(u.GetWindowLongW(hw,-20)&0xFFFFFFFF),flush=True)
p.kill()
