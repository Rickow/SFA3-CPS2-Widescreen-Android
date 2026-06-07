#!/usr/bin/env python3
# Assemble a layered PSD from the aligned RGBA layer dumps produced by F7
# (CpsDumpStageLayers) in the SDL FBNeo build.
#
# Input : <prefix>_scroll1.bin, _scroll2.bin, _scroll3.bin  (header "RGBA W H\n" + W*H*4)
# Output: <prefix>.psd          (3 named layers, aligned, transparent)
#         <prefix>_scrollN.png  (each layer)
#         <prefix>_preview.png  (flattened composite)
#
# Usage: python assemble_psd.py <prefix> [indir] [outdir]
#   e.g. python assemble_psd.py stage00 "E:/CLAUDE CODE/fbneo-libretro" "./out_stages"

import sys, os, struct
from PIL import Image, ImageDraw

# Geometrie de capture (doit matcher cps_dump.cpp)
MARGIN_X, MARGIN_Y = 128, 128     # decalage ecran(0,0) dans le canevas
SCR_W, SCR_H       = 384, 224     # ecran 4:3 d'origine
WIDE_W             = 448          # cible widescreen 16:9 (meme hauteur)

def read_rgba(path):
    with open(path, "rb") as f:
        data = f.read()
    nl = data.index(b"\n")
    tag, w, h = data[:nl].split()
    assert tag == b"RGBA", "bad header in %s" % path
    w, h = int(w), int(h)
    px = data[nl + 1: nl + 1 + w * h * 4]
    assert len(px) == w * h * 4, "truncated %s" % path
    return w, h, px

def s16(v): return struct.pack(">h", v)
def s32(v): return struct.pack(">i", v)
def u16(v): return struct.pack(">H", v)
def u32(v): return struct.pack(">I", v)

def pascal_pad4(name):
    b = name.encode("latin-1")[:255]
    s = bytes([len(b)]) + b
    while len(s) % 4:
        s += b"\x00"
    return s

def write_psd(path, W, H, layers):
    """layers: list of (name, rgba_bytes) ordered TOP first; stored bottom-first."""
    order = list(reversed(layers))  # PSD stores bottom -> top

    # --- merged composite (for the flattened preview channels) ---
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for _, px in order:
        base = Image.alpha_composite(base, Image.frombytes("RGBA", (W, H), px))
    merged = base.tobytes()

    records, chan_data = [], []
    for name, px in order:
        R, G, B, A = px[0::4], px[1::4], px[2::4], px[3::4]
        rec = s32(0) + s32(0) + s32(H) + s32(W)        # top,left,bottom,right
        rec += u16(4)                                   # 4 channels
        for cid, plane in ((0, R), (1, G), (2, B), (-1, A)):
            rec += s16(cid) + u32(2 + len(plane))       # +2 for compression word
        rec += b"8BIM" + b"norm"                        # blend mode
        rec += bytes([255, 0, 0, 0])                    # opacity, clip, flags, filler
        nm = pascal_pad4(name)
        extra = u32(0) + u32(0) + nm                    # mask len, ranges len, name
        rec += u32(len(extra)) + extra
        records.append(rec)
        for plane in (R, G, B, A):
            chan_data.append(u16(0) + plane)            # 0 = raw

    layers_block = s16(len(order)) + b"".join(records) + b"".join(chan_data)
    if len(layers_block) % 2:
        layers_block += b"\x00"
    layer_info = u32(len(layers_block)) + layers_block
    lmi = layer_info + u32(0)                            # + global layer mask info (0)
    layer_mask_section = u32(len(lmi)) + lmi

    header = b"8BPS" + u16(1) + b"\x00" * 6 + u16(4) + u32(H) + u32(W) + u16(8) + u16(3)
    color_mode = u32(0)
    image_res = u32(0)

    mR, mG, mB, mA = merged[0::4], merged[1::4], merged[2::4], merged[3::4]
    merged_data = u16(0) + mR + mG + mB + mA            # raw planar

    with open(path, "wb") as f:
        f.write(header + color_mode + image_res + layer_mask_section + merged_data)

def main():
    if len(sys.argv) < 2:
        print("usage: assemble_psd.py <prefix> [indir] [outdir]"); return 1
    prefix = sys.argv[1]
    indir = sys.argv[2] if len(sys.argv) > 2 else "."
    outdir = sys.argv[3] if len(sys.argv) > 3 else "."
    os.makedirs(outdir, exist_ok=True)

    sizes = set()
    imgs = {}
    for n in (1, 2, 3):
        p = os.path.join(indir, "%s_scroll%d.bin" % (prefix, n))
        w, h, px = read_rgba(p)
        sizes.add((w, h))
        imgs[n] = px
        Image.frombytes("RGBA", (w, h), px).save(os.path.join(outdir, "%s_scroll%d.png" % (prefix, n)))
    assert len(sizes) == 1, "layers have different sizes: %s" % sizes
    W, H = sizes.pop()

    # --- decor (top -> bottom). NB: la profondeur CPS2 varie par stage. ---
    decor = [
        ("Scroll3 (avant)",  imgs[3]),
        ("Scroll2 (median)", imgs[2]),
        ("Scroll1 (fond)",   imgs[1]),
    ]
    # composite decor seul (pour detecter les trous transparents)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for _, px in reversed(decor):
        base = Image.alpha_composite(base, Image.frombytes("RGBA", (W, H), px))

    # --- geometrie depuis le .meta du dumper (placement EXACT des reperes) ---
    meta = {}
    mp = os.path.join(indir, "%s.meta" % prefix)
    if os.path.exists(mp):
        for line in open(mp):
            p = line.split()
            if len(p) == 2:
                try: meta[p[0]] = int(p[1])
                except ValueError: pass
    mx = meta.get("margin_x", (W - 448) // 2)   # canvas x de la colonne 0 du rendu
    my = meta.get("margin_y", (H - 224) // 2)
    sw = meta.get("screen_w", 448)              # largeur AVEC patch (rendu courant)
    sh = meta.get("screen_h", 224)
    gx = meta.get("gx", (sw - SCR_W) // 2)      # offset du natif dans le rendu
    gy = meta.get("gy", (sh - SCR_H) // 2)
    nw = meta.get("native_w", SCR_W)            # 384 (sans patch)
    nh = meta.get("native_h", SCR_H)            # 224

    nat = (mx + gx, my + gy, mx + gx + nw, my + gy + nh)   # viewport SANS patch
    pat = (mx, my, mx + sw, my + sh)                       # viewport AVEC patch

    # "A combler" : rouge la ou c'est transparent DANS le viewport AVEC patch
    fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bp, fp = base.load(), fill.load()
    for y in range(max(0, pat[1]), min(H, pat[3])):
        for x in range(max(0, pat[0]), min(W, pat[2])):
            if bp[x, y][3] == 0:
                fp[x, y] = (255, 0, 0, 90)

    # Reperes : cadres + libelles
    guides = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(guides)
    d.rectangle([nat[0], nat[1], nat[2] - 1, nat[3] - 1], outline=(255, 255, 255, 255), width=1)
    d.rectangle([pat[0], pat[1], pat[2] - 1, pat[3] - 1], outline=(0, 255, 255, 255), width=2)
    d.text((nat[0] + 3, nat[1] + 3), "sans patch %dx%d" % (nw, nh), fill=(255, 255, 255, 255))
    d.text((pat[0] + 3, pat[3] - 12), "avec patch %dx%d" % (sw, sh), fill=(0, 255, 255, 255))

    # --- PSD : reperes + a combler au-dessus du decor ---
    layers = [("Reperes 4:3 / 16:9", guides.tobytes()),
              ("A combler (16:9)",   fill.tobytes())] + decor
    psd = os.path.join(outdir, "%s.psd" % prefix)
    write_psd(psd, W, H, layers)

    # --- apercus ---
    base.save(os.path.join(outdir, "%s_preview.png" % prefix))                 # decor seul
    annot = Image.alpha_composite(Image.alpha_composite(base, fill), guides)
    annot.save(os.path.join(outdir, "%s_preview_zones.png" % prefix))          # avec reperes
    cw = round(W * 0.7777)  # PAR CPS2 ~0.778 -> pixels carres (apercu rond)
    base.resize((cw, H), Image.LANCZOS).save(os.path.join(outdir, "%s_preview_43.png" % prefix))
    annot.resize((cw, H), Image.LANCZOS).save(os.path.join(outdir, "%s_preview_zones_43.png" % prefix))

    print("OK %s  (%dx%d, %d layers + reperes)" % (psd, W, H, len(decor)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
