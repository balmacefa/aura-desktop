"""Preparación común: LOCALAPPDATA temporal ANTES de importar los módulos de Aura, y rutas de importación."""
import atexit, os, shutil, sys, tempfile

TMP = tempfile.mkdtemp(prefix='aura-test-')
os.environ['LOCALAPPDATA'] = TMP
atexit.register(shutil.rmtree, TMP, True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, 'desk'), os.path.join(ROOT, 'wall', 'live'), os.path.join(ROOT, 'wall'), ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)
