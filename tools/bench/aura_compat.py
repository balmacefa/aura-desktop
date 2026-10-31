"""Capa de compatibilidad: las herramientas de benchmark se escribieron contra la API de Aura 1.x; aquí se adaptan al paquete `aura` actual."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from aura import cli, config, paths, state                                  # noqa: E402

PY, ROOT_DIR, MEDIA = sys.executable, ROOT, str(paths.MEDIA)
apply_scene, desk, desk_pids, wall, snapshot = cli.apply_scene, cli.desk, cli.desk_pids, cli.wall, cli.snapshot
read_state = state.read_state


def load_conf(): return {**config.load(), 'mode': 'live'}
def save_conf(c): config.save({k: v for k, v in c.items() if k != 'mode'})
def apply_video(path): cli.apply_scene('video:' + os.path.basename(path))
def video_path(): return ''
