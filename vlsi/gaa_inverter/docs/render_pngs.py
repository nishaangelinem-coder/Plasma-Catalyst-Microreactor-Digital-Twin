#!/usr/bin/env python3
"""render_pngs.py -- 2x PNG renderings of every schematic and layout SVG in docs/figures with headless
Chromium. The new headless mode counts window chrome inside --window-size, so the viewport is shorter
than requested: a probe page measures the offset once and each capture is cropped back to size."""
import os, re, shutil, struct, subprocess, zlib
R = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(R, "figures")
CH = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
NAMES = ["schematic_inv", "schematic_nand2", "schematic_ro11", "schematic_sram6t",
         "virtuoso_inv", "virtuoso_nand2", "virtuoso_ro11", "virtuoso_sram6t",
         "viva_inv_dc", "viva_inv_tran", "viva_nand2_tran", "viva_ro11_tran", "viva_sram_butterfly",
         "drc_inv", "drc_nand2", "drc_ro11", "drc_sram6t", "lvs_inv", "lvs_nand2", "lvs_ro11", "lvs_sram6t",
         "pex_inv", "pex_nand2", "pex_ro11", "pex_sram6t", "viva_inv_postlayout", "viva_ro11_postlayout",
         "innovus_inverter", "innovus_nand2", "innovus_ring_osc", "genus_ring_osc", "genus_gates_ring_osc", "timing_inverter", "timing_nand2", "timing_ring_osc",
         "layout_inv", "layout_nand2", "layout_ro11", "layout_sram6t"]

def png_read(path):
    d = open(path, "rb").read(); pos = 8; idat = b""; w = h = bpp = 0
    while pos < len(d):
        n, t = struct.unpack(">I4s", d[pos:pos + 8]); body = d[pos + 8:pos + 8 + n]; pos += 12 + n
        if t == b"IHDR": w, h, _bd, ct = struct.unpack(">IIBB", body[:10]); bpp = {2: 3, 6: 4}[ct]
        elif t == b"IDAT": idat += body
    raw = zlib.decompress(idat); stride = w * bpp; rows = []; prev = bytearray(stride); p = 0
    for _ in range(h):
        f = raw[p]; line = bytearray(raw[p + 1:p + 1 + stride]); p += 1 + stride
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0; b = prev[i]; c = prev[i - bpp] if i >= bpp else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                pp = a + b - c; pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line)); prev = line
    return w, h, bpp, rows

def png_write(path, w, h, bpp, rows):
    def chunk(t, b): return struct.pack(">I", len(b)) + t + b + struct.pack(">I", zlib.crc32(t + b) & 0xffffffff)
    raw = b"".join(b"\x00" + r for r in rows)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6 if bpp == 4 else 2, 0, 0, 0)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))

def shoot(html, w, h, out):
    subprocess.run([CH, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={w},{h}", f"--screenshot={out}", "file://" + html],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)

def probe():
    html = os.path.join(F, "_probe.html")
    open(html, "w").write('<!doctype html><html><head><style>html,body{margin:0;background:#fff}div{width:400px;height:3000px;background:#000}</style></head><body><div></div></body></html>')
    shoot(html, 400, 800, os.path.join(F, "_probe.png"))
    w, h, bpp, rows = png_read(os.path.join(F, "_probe.png"))
    visible = sum(1 for r in rows if r[0] == 0)
    os.remove(html); os.remove(os.path.join(F, "_probe.png"))
    return 800 - visible

if __name__ == "__main__":
    for src, dst in (("gaa_inverter", "layout_inv"), ("gaa_nand2", "layout_nand2"), ("gaa_ro11", "layout_ro11"), ("gaa_sram6t", "layout_sram6t")):
        shutil.copy(os.path.join(R, "..", "layout", src + ".svg"), os.path.join(F, dst + ".svg"))
    off = probe(); print("viewport offset:", off, "px")
    for name in NAMES:
        svg = open(os.path.join(F, name + ".svg")).read()
        m = re.search(r'viewBox="0 0 ([0-9.]+) ([0-9.]+)"', svg)
        W, H = int(float(m.group(1)) * 2), int(float(m.group(2)) * 2)
        html = os.path.join(F, "_wrap.html")
        open(html, "w").write('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff;overflow:hidden}'
                              f'svg{{display:block;max-width:none!important;width:{W}px!important;height:{H}px!important}}</style></head><body>{svg}</body></html>')
        out = os.path.join(F, name + ".png")
        shoot(html, W, H + off, out)
        w, h, bpp, rows = png_read(out)
        png_write(out, w, min(h, H), bpp, rows[:H])
        print(f"rendered {name}.png {w}x{min(h, H)}")
    os.remove(html)
