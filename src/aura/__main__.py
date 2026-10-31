"""`python -m aura` y punto de entrada del ejecutable empaquetado (Aura.exe)."""
import sys

if __name__ == '__main__':
    from aura.cli import entry
    entry()
