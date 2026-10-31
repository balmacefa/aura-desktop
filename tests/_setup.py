"""Entorno común de las pruebas: datos en una carpeta temporal y el paquete `aura` importable desde `src/`."""
import atexit, os, shutil, sys, tempfile

DATA = tempfile.mkdtemp(prefix='aura_tests_')
os.environ['AURA_DATA_DIR'] = DATA
atexit.register(shutil.rmtree, DATA, ignore_errors=True)
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def reset_data():
    """Vacía la carpeta de datos entre pruebas."""
    for name in os.listdir(DATA):
        p = os.path.join(DATA, name)
        shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.remove(p)
