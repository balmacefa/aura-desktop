"""Iniciar Aura con Windows: una entrada del usuario en HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run (sin permisos de administrador)."""
import subprocess, sys, winreg

from . import paths

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'Aura'


def command():
    exe = paths.executable_command()
    return ' '.join(f'"{p}"' for p in exe) + ' --background'


def is_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k:
            winreg.QueryValueEx(k, NAME); return True
    except OSError:
        return False


def set_enabled(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, command())
        else:
            try: winreg.DeleteValue(k, NAME)
            except OSError: pass
