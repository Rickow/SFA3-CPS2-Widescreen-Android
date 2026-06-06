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
from PIL import Image

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

    # top -> bottom. NB: la profondeur CPS2 varie par stage (priorites par tile).
    # Pour SFA3 (stage coucher de soleil valide), Scroll1 = ciel (FOND),
    # Scroll3 = rochers/bonsai (AVANT). Ordre ajustable dans Photoshop.
    layers = [
        ("Scroll3 (avant)",  imgs[3]),
        ("Scroll2 (median)", imgs[2]),
        ("Scroll1 (fond)",   imgs[1]),
    ]
    psd = os.path.join(outdir, "%s.psd" % prefix)
    write_psd(psd, W, H, layers)

    # flattened preview
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for _, px in reversed(layers):
        base = Image.alpha_composite(base, Image.frombytes("RGBA", (W, H), px))
    base.save(os.path.join(outdir, "%s_preview.png" % prefix))

    print("OK %s  (%dx%d, 3 layers)" % (psd, W, H))
    return 0

if __name__ == "__main__":
    sys.exit(main())
