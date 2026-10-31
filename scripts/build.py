"""Construye Aura para Windows: PyInstaller (carpeta autocontenida) + instalador Inno Setup + zip portable + SHA256SUMS.txt en dist/.

Uso:  python scripts/build.py [--skip-installer]
Requisitos de construcción (no de uso): Python 3.10+, `pip install pyinstaller`, Inno Setup 6 (`winget install JRSoftware.InnoSetup`).
"""
import hashlib, os, re, shutil, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'


def version():
    return re.search(r"__version__ = '([^']+)'", (ROOT / 'src' / 'aura' / '__init__.py').read_text(encoding='utf-8')).group(1)


def write_version_info(v):
    n = tuple(int(x) for x in v.split('.')) + (0,)
    (ROOT / 'installer' / 'version_info.txt').write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={n}, prodvers={n}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'balmacefa'), StringStruct('FileDescription', 'Aura'), StringStruct('FileVersion', '{v}.0'),
    StringStruct('InternalName', 'Aura'), StringStruct('LegalCopyright', 'MIT License - balmacefa'), StringStruct('OriginalFilename', 'Aura.exe'),
    StringStruct('ProductName', 'Aura'), StringStruct('ProductVersion', '{v}')])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])
""", encoding='utf-8')


def find_iscc():
    cands = [os.environ.get('ISCC'), shutil.which('ISCC')]
    for base in (os.environ.get('ProgramFiles(x86)'), os.environ.get('ProgramFiles'), os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs')):
        if base: cands.append(os.path.join(base, 'Inno Setup 6', 'ISCC.exe'))
    return next((c for c in cands if c and os.path.exists(c)), None)


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()


def main():
    v = version(); skip_installer = '--skip-installer' in sys.argv
    print(f'== Aura {v}')
    shutil.rmtree(DIST, ignore_errors=True); shutil.rmtree(ROOT / 'build', ignore_errors=True)
    write_version_info(v)
    subprocess.run([sys.executable, '-m', 'PyInstaller', str(ROOT / 'installer' / 'aura.spec'), '--noconfirm', '--distpath', str(DIST), '--workpath', str(ROOT / 'build')], check=True, cwd=ROOT)
    app = DIST / 'Aura'
    assert (app / 'Aura.exe').exists(), 'PyInstaller no generó Aura.exe'
    print('== zip portable')
    portable = DIST / f'Aura-portable-{v}.zip'
    with zipfile.ZipFile(portable, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in app.rglob('*'):
            if f.is_file(): z.write(f, Path('Aura') / f.relative_to(app))
    if not skip_installer:
        iscc = find_iscc()
        if not iscc: sys.exit('Inno Setup 6 no encontrado (winget install JRSoftware.InnoSetup)')
        print('== instalador'); subprocess.run([iscc, f'/DAppVersion={v}', str(ROOT / 'installer' / 'aura.iss')], check=True, cwd=ROOT)
    files = sorted(p for p in DIST.iterdir() if p.is_file() and p.suffix in ('.exe', '.zip'))
    (DIST / 'SHA256SUMS.txt').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in files), encoding='utf-8')
    for p in files + [DIST / 'SHA256SUMS.txt']: print(f'   {p.name}  {p.stat().st_size / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
