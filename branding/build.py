#!/usr/bin/env python3
"""Regenera toda la identidad visual de Aura. Uso: python branding/build.py
Requiere Microsoft Edge (render SVG->PNG headless). Solo libreria estandar."""
import os, struct, zlib, subprocess, tempfile, pathlib, shutil

ROOT = pathlib.Path(__file__).resolve().parent
EDGE = os.environ.get("EDGE", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
INK, NIGHT, PLUM, EMBER = "#0e0e18", "#1d1b3a", "#3a1b2a", "#d97757"


def icon_body(x=0, y=0, s=512, bg=True):
    """Icono en cuadro 512 escalado a s: anillo abierto con degradado de brasa + punto de luz."""
    k = s / 512
    b = f'<g transform="translate({x} {y}) scale({k})">'
    if bg:
        b += '<rect width="512" height="512" rx="116" fill="url(#bg)"/>'
        b += '<rect width="512" height="512" rx="116" fill="url(#glow)"/>'
    b += ('<path d="M 333.7 112.9 A 156 156 0 1 0 404.6 288" fill="none" stroke="url(#ring)" '
          'stroke-width="58" stroke-linecap="round"/>'
          '<circle cx="388" cy="168" r="30" fill="#ffd2b8"/>')
    return b + '</g>'


DEFS = f'''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{NIGHT}"/><stop offset="1" stop-color="{INK}"/></linearGradient>
<radialGradient id="glow" cx="0.5" cy="0.55" r="0.6"><stop offset="0" stop-color="{PLUM}" stop-opacity="0.85"/><stop offset="1" stop-color="{PLUM}" stop-opacity="0"/></radialGradient>
<linearGradient id="ring" x1="0.1" y1="0" x2="0.9" y2="1"><stop offset="0" stop-color="#ffb18a"/><stop offset="0.5" stop-color="{EMBER}"/><stop offset="1" stop-color="#9c3d4f"/></linearGradient>
</defs>'''


def svg(w, h, inner, vb=None):
    vb = vb or f"0 0 {w} {h}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{vb}">'
            f'{DEFS}{inner}</svg>\n')


# «Aura» dibujada a trazos (sin fuentes). Caja x 170..433, y 40..110
LETTERS = ('M170 110 L205 40 L240 110 M184 84 H226 '
           'M262 62V92C262 104 270 110 281 110C292 110 300 104 300 92 M300 62V110 '
           'M322 62V110 M322 84C322 68 332 62 348 62 '
           'M425 86 A24 24 0 1 0 377 86 A24 24 0 1 0 425 86 M425 62V110')


def letters(color, x=0, y=0, k=1.0):
    return (f'<g transform="translate({x} {y}) scale({k})"><path d="{LETTERS}" fill="none" stroke="{color}" '
            'stroke-width="13" stroke-linecap="round" stroke-linejoin="round"/></g>')


def wordmark(color):
    return svg(470, 150, icon_body(10, 15, 120) + letters(color))


def tray_inner(color):
    return (f'<path d="M 21.5 6.6 A 10.5 10.5 0 1 0 26.5 19" fill="none" stroke="{color}" '
            'stroke-width="3.8" stroke-linecap="round"/>'
            f'<circle cx="25.5" cy="9.5" r="2.4" fill="{color}"/>')


def backdrop(w, h):
    return (f'<defs><linearGradient id="pg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{INK}"/>'
            f'<stop offset="0.6" stop-color="{NIGHT}"/><stop offset="1" stop-color="{PLUM}"/></linearGradient>'
            f'<radialGradient id="pe" cx="0.82" cy="0.3" r="0.55"><stop offset="0" stop-color="{EMBER}" stop-opacity="0.35"/>'
            f'<stop offset="1" stop-color="{EMBER}" stop-opacity="0"/></radialGradient></defs>'
            f'<rect width="{w}" height="{h}" fill="url(#pg)"/><rect width="{w}" height="{h}" fill="url(#pe)"/>')


def hero(w, h, isz, tag):
    k = isz / 120 * 1.1          # escala de las letras
    ix, iy = w * 0.16, h / 2 - isz / 2
    tx = ix + isz + isz * 0.25
    wy = h / 2 - 75 * k - tag * 0.8   # centra bloque palabra + lema
    inner = backdrop(w, h) + icon_body(ix, iy, isz)
    inner += letters("#f4efe9", tx - 170 * k, wy, k)
    inner += (f'<text x="{tx:.0f}" y="{wy + 110 * k + tag * 1.9:.0f}" '
              f'font-family="Segoe UI, Helvetica Neue, Arial, sans-serif" font-size="{tag}" fill="#c9bfd0">'
              'Fondos animados e interactivos para Windows</text>')
    return svg(w, h, inner)


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def read_png(path):
    b = pathlib.Path(path).read_bytes()
    p, idat = 8, b""
    while p < len(b):
        n, t = struct.unpack(">I4s", b[p:p + 8])
        c = b[p + 8:p + 8 + n]
        p += 12 + n
        if t == b"IHDR":
            w, h, bd, ct, _, _, il = struct.unpack(">IIBBBBB", c)
        elif t == b"IDAT":
            idat += c
    assert bd == 8 and ct in (2, 6) and il == 0, "PNG no soportado"
    bpp = 4 if ct == 6 else 3
    raw, stride = zlib.decompress(idat), w * bpp
    rows, prev, q = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[q]
        cur = bytearray(raw[q + 1:q + 1 + stride])
        q += 1 + stride
        for i in range(stride):
            a = cur[i - bpp] if i >= bpp else 0
            up = prev[i]
            c_ = prev[i - bpp] if i >= bpp else 0
            if f == 1: cur[i] = (cur[i] + a) & 255
            elif f == 2: cur[i] = (cur[i] + up) & 255
            elif f == 3: cur[i] = (cur[i] + (a + up) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(up - c_), abs(a - c_), abs(a + up - 2 * c_)
                pr = a if pa <= pb and pa <= pc else (up if pb <= pc else c_)
                cur[i] = (cur[i] + pr) & 255
        rows.append(cur)
        prev = cur
    return w, h, bpp, rows


def render(svg_text, out, w, h, transparent=True):
    """SVG -> PNG con Edge headless. Se renderiza en lienzo mayor y se recorta si el viewport sale corto."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    html = tmp / "r.html"
    html.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;padding:0;'
                    'background:transparent;overflow:hidden}svg{display:block}</style>' + svg_text,
                    encoding="utf-8")
    out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    bg = "00000000" if transparent else "0e0e18ff"
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--hide-scrollbars", f"--screenshot={out}",
                    f"--window-size={w},{h}", f"--default-background-color={bg}", html.as_uri()],
                   check=True, capture_output=True, timeout=90)
    shutil.rmtree(tmp, ignore_errors=True)
    d = read_png(out)
    if (d[0], d[1]) != (w, h):
        raise SystemExit(f"{out}: salio {d[0]}x{d[1]}, se esperaba {w}x{h}")


def write_bmp(png, out):
    w, h, bpp, rows = read_png(png)
    pad = (4 - (w * 3) % 4) % 4
    data = bytearray()
    for r in reversed(rows):
        for x in range(w):
            R, G, B = r[x * bpp:x * bpp + 3]
            if bpp == 4:
                a = r[x * bpp + 3] / 255
                R, G, B = (int(c * a + v * (1 - a)) for c, v in zip((R, G, B), (14, 14, 24)))
            data += bytes((B, G, R))
        data += b"\0" * pad
    hdr = struct.pack("<2sIHHI", b"BM", 54 + len(data), 0, 0, 54)
    dib = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(data), 2835, 2835, 0, 0)
    (ROOT / out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / out).write_bytes(hdr + dib + bytes(data))


def main():
    write("icon/aura.svg", svg(512, 512, icon_body()))
    pngs = []
    for s in (16, 24, 32, 48, 64, 128, 256):
        o = f"_tmp/i{s}.png"
        render(svg(s, s, icon_body(0, 0, s)), o, s, s)
        pngs.append((s, (ROOT / o).read_bytes()))
    ico = struct.pack("<HHH", 0, 1, len(pngs))
    off, body = 6 + 16 * len(pngs), b""
    for s, d in pngs:
        ico += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(d), off + len(body))
        body += d
    (ROOT / "icon/aura.ico").write_bytes(ico + body)
    render(svg(512, 512, icon_body()), "icon/aura-512.png", 512, 512)

    for name, col in (("light", "#16161f"), ("dark", "#ffffff")):  # light = barra clara (glifo oscuro)
        render(svg(32, 32, tray_inner(col)), f"tray/tray-{name}.png", 32, 32)
        render(svg(16, 16, tray_inner(col), "0 0 32 32"), f"tray/tray-{name}-16.png", 16, 16)

    write("logo/wordmark.svg", wordmark("#f4efe9"))   # para fondos oscuros
    write("logo/wordmark-light.svg", wordmark(INK))   # para fondos claros

    wiz = backdrop(164, 314) + icon_body(26, 60, 112) + letters("#f4efe9", 26 - 170 * 0.46 + 10, 180, 0.46)
    render(svg(164, 314, wiz), "_tmp/wiz.png", 164, 314, False)
    write_bmp(ROOT / "_tmp/wiz.png", "installer/wizard.bmp")
    sm = f'<rect width="55" height="58" fill="{INK}"/>' + icon_body(6.5, 8, 42)
    render(svg(55, 58, sm), "_tmp/sm.png", 55, 58, False)
    write_bmp(ROOT / "_tmp/sm.png", "installer/small.bmp")

    render(hero(1280, 640, 220, 32), "social/social-preview.png", 1280, 640, False)
    render(hero(1600, 500, 190, 30), "social/banner.png", 1600, 500, False)
    shutil.rmtree(ROOT / "_tmp", ignore_errors=True)
    print("ok")


if __name__ == "__main__":
    main()
