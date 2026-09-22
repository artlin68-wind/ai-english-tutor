"""Generate PWA app icons for the AI English Tutor.
Draws a rounded gradient tile with a white speech bubble containing "Aあ英"-style
mark (we use "Aa" + a small globe dot) — clean, recognizable at small sizes.
Outputs: icons/icon-192.png, icon-512.png, maskable-512.png, apple-touch-icon.png
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "icons")
os.makedirs(OUT, exist_ok=True)

# brand gradient stops (light orange -> orange -> deep orange), matches app theme
C1 = (251, 176, 100)   # light orange
C2 = (249, 115, 22)    # orange
C3 = (234, 88, 12)     # deep orange
INK = (194, 65, 12)    # bubble text color (deep orange, contrasts on white)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(size):
    """Diagonal 3-stop gradient."""
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            if t < 0.5:
                col = lerp(C1, C2, t / 0.5)
            else:
                col = lerp(C2, C3, (t - 0.5) / 0.5)
            px[x, y] = col
    return img


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def load_font(size):
    for name in ["arialbd.ttf", "seguisb.ttf", "segoeui.ttf", "Arial.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_bubble(img, size, pad_ratio=0.0):
    """Draw a white speech bubble with 'Aa' text centered on img (in place)."""
    d = ImageDraw.Draw(img, "RGBA")
    # bubble box
    inset = size * (0.22 + pad_ratio)
    bx0, by0 = inset, inset * 0.9
    bx1, by1 = size - inset, size - inset * 1.15
    r = (by1 - by0) * 0.32
    # soft shadow
    sh = int(size * 0.012)
    d.rounded_rectangle([bx0 + sh, by0 + sh, bx1 + sh, by1 + sh],
                        radius=r, fill=(0, 0, 0, 60))
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=r, fill=(255, 255, 255, 255))
    # bubble tail
    tail_w = (bx1 - bx0) * 0.16
    tx = bx0 + (bx1 - bx0) * 0.30
    ty = by1 - 1
    d.polygon([(tx, ty - 2), (tx + tail_w, ty - 2),
               (tx + tail_w * 0.15, ty + tail_w * 0.9)], fill=(255, 255, 255, 255))
    # text "Aa"
    fsize = int((by1 - by0) * 0.62)
    font = load_font(fsize)
    text = "Aa"
    tb = d.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    cx = (bx0 + bx1) / 2 - tw / 2 - tb[0]
    cy = (by0 + by1) / 2 - th / 2 - tb[1]
    d.text((cx, cy), text, font=font, fill=INK)


def make(size, radius_ratio, out_name, bubble_pad=0.0, bg_full=False):
    base = gradient(size)
    draw_bubble(base, size, bubble_pad)
    if bg_full:
        base.save(os.path.join(OUT, out_name))
    else:
        radius = int(size * radius_ratio)
        mask = rounded_mask(size, radius)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(base, (0, 0), mask)
        out.save(os.path.join(OUT, out_name))
    print("wrote", out_name, size)


# Standard PWA icons (rounded — but manifest 'any' can be square; keep subtle round)
make(192, 0.0, "icon-192.png", bg_full=True)
make(512, 0.0, "icon-512.png", bg_full=True)
# Maskable: full-bleed background, bubble pulled in to survive safe-zone crop
make(512, 0.0, "maskable-512.png", bubble_pad=0.06, bg_full=True)
# Apple touch icon: iOS rounds corners itself, so full square
make(180, 0.0, "apple-touch-icon.png", bg_full=True)
print("done ->", OUT)
