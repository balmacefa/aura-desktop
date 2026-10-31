"""Tipografía de Aura: Inter (SIL OFL 1.1, incluida en assets/fonts) con alternativa a Segoe UI.

Se registra solo para este proceso (FR_PRIVATE): no instala nada en el sistema. Importar este módulo antes de crear la primera ventana de Tk.
"""
import ctypes

from . import paths

UI, UI_B, UI_M = 'Segoe UI', 'Segoe UI Semibold', 'Segoe UI'              # regular, semibold, medium (alternativa del sistema)
loaded = False


def _register():
    n = 0
    gdi = ctypes.windll.gdi32
    for f in sorted(paths.FONTS.glob('Inter-*.ttf')) if paths.FONTS.is_dir() else []:
        n += gdi.AddFontResourceExW(str(f), 0x10, 0)                          # FR_PRIVATE: visible solo para este proceso
    return n


if _register() >= 3:
    UI, UI_B, UI_M, loaded = 'Inter', 'Inter SemiBold', 'Inter Medium', True
