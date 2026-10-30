import sys,os,subprocess,shutil,time,ctypes
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import aurawall as a
w,h=a.screen_size()
p=subprocess.Popen([shutil.which('ffplay'),'-noborder','-loop','0','-an','-loglevel','quiet','-x',str(w),'-y',str(h),'-left','0','-top','0','-window_title',a.TITLE,'media/aura_flow.mp4'],creationflags=0x08000000,env={**os.environ,'SDL_RENDER_DRIVER':os.environ.get('RD','direct3d11')})
hw=a.find_by_title(a.TITLE); time.sleep(1)
print('player',hex(hw),a._cls(hw),'ex before',hex(a.u32.GetWindowLongW(hw,-20)&0xFFFFFFFF),flush=True)
a.embed(hw,a.find_workerw())
print('ex after',hex(a.u32.GetWindowLongW(hw,-20)&0xFFFFFFFF),'parent',hex(a.u32.GetParent(hw) or 0),flush=True)
time.sleep(int(sys.argv[1]) if len(sys.argv)>1 else 25); p.kill()
a.u32.SystemParametersInfoW(0x0014,0,None,3)
