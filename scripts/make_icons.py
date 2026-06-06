#!/usr/bin/env python3
# Generate Android launcher icons (legacy + adaptive foreground) from icone.png.
# - Beige background (208,208,176) is keyed out to transparency for the foreground.
# - Adaptive background color is set to the same beige in colors.xml.
# - Legacy icon = beige square + logo composited.
import os
from PIL import Image

SRC   = r"E:/CLAUDE CODE/sfa3-widescreen-android/icone.png"
RESD  = r"E:/RetroArch/pkg/android/phoenix-common/res"
BEIGE = (208, 208, 176)

# density -> (legacy size, adaptive foreground size)
DENS = {
    "mdpi":    (48, 108),
    "hdpi":    (72, 162),
    "xhdpi":   (96, 216),
    "xxhdpi":  (144, 324),
    "xxxhdpi": (192, 432),
}

src = Image.open(SRC).convert("RGBA")

# --- 1) Key out the beige -> transparent logo (feathered edges) ---
lo, hi = 30.0, 80.0
px = src.load()
W, H = src.size
keyed = Image.new("RGBA", (W, H), (0, 0, 0, 0))
kp = keyed.load()
for y in range(H):
    for x in range(W):
        r, g, b, a = px[x, y]
        d = abs(r - BEIGE[0]) + abs(g - BEIGE[1]) + abs(b - BEIGE[2])
        if d <= lo:
            alpha = 0
        elif d >= hi:
            alpha = 255
        else:
            alpha = int(255 * (d - lo) / (hi - lo))
        kp[x, y] = (r, g, b, alpha)

# --- 2) Crop logo to its bbox (+small margin) ---
bbox = keyed.getbbox()
mx = 8
bbox = (max(0, bbox[0] - mx), max(0, bbox[1] - mx),
        min(W, bbox[2] + mx), min(H, bbox[3] + mx))
logo = keyed.crop(bbox)
lw, lh = logo.size

def fit(canvas_px, target_frac):
    """Return logo resized so its WIDTH = target_frac*canvas, keeping aspect."""
    tw = int(canvas_px * target_frac)
    th = int(lh * tw / lw)
    return logo.resize((tw, th), Image.LANCZOS), tw, th

def centered(canvas_px, bg, target_frac):
    im = Image.new("RGBA", (canvas_px, canvas_px), bg)
    rl, tw, th = fit(canvas_px, target_frac)
    im.alpha_composite(rl, ((canvas_px - tw) // 2, (canvas_px - th) // 2))
    return im

for dens, (legacy, fg) in DENS.items():
    d = os.path.join(RESD, "mipmap-" + dens)
    os.makedirs(d, exist_ok=True)
    # Legacy: beige square + logo at 82% width
    leg = centered(legacy, BEIGE + (255,), 0.82)
    leg.convert("RGBA").save(os.path.join(d, "ic_launcher.png"))
    # Adaptive foreground: transparent + logo at 66% width (safe zone)
    fgi = centered(fg, (0, 0, 0, 0), 0.66)
    fgi.save(os.path.join(d, "ic_launcher_foreground.png"))
    print("wrote", dens, "legacy", legacy, "fg", fg)

# --- 3) Set adaptive background color to beige ---
colors = os.path.join(RESD, "values", "colors.xml")
hexb = "#%02X%02X%02X" % BEIGE
with open(colors, "r", encoding="utf-8") as f:
    txt = f.read()
import re
txt = re.sub(r'(<color name="ic_launcher_background">)[^<]*(</color>)',
             r'\g<1>' + hexb + r'\g<2>', txt)
with open(colors, "w", encoding="utf-8") as f:
    f.write(txt)
print("ic_launcher_background ->", hexb)
print("DONE")
