"""Extract the two characters from the source screenshot into transparent PNGs.
Source background is a transparency checkerboard (light grays 235/238/252/255).
Method: flood-fill from the borders over 'background-like' (bright, near-gray)
pixels -> alpha 0. Interior white shirt is enclosed, so it stays opaque.
Outputs into avatars/:
  emma_full.png / ryan_full.png  (full body)
  emma_head.png / ryan_head.png  (square head crop for small round avatars)
Left character = Emma (female), right = Ryan (male).
"""
from PIL import Image
import numpy as np
from collections import deque
import os

SRC = 'D:/螢幕擷取畫面 2026-08-17 102821.jpg'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'avatars')
os.makedirs(OUT, exist_ok=True)

im = Image.open(SRC).convert('RGB')
a = np.asarray(im).astype(int)
h, w, _ = a.shape

# background-like: bright AND near-gray (low saturation)
mx = a.max(axis=2)
mn = a.min(axis=2)
bg_like = (mn >= 218) & ((mx - mn) <= 14)

# flood fill from all border pixels through bg_like region
visited = np.zeros((h, w), dtype=bool)
dq = deque()
for x in range(w):
    for y in (0, h - 1):
        if bg_like[y, x] and not visited[y, x]:
            visited[y, x] = True
            dq.append((y, x))
for y in range(h):
    for x in (0, w - 1):
        if bg_like[y, x] and not visited[y, x]:
            visited[y, x] = True
            dq.append((y, x))
while dq:
    y, x = dq.popleft()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and bg_like[ny, nx]:
            visited[ny, nx] = True
            dq.append((ny, nx))

alpha = np.where(visited, 0, 255).astype('uint8')

# Feather the edge a touch: set semi-transparent where opaque pixel neighbors background
rgba = np.dstack([a.astype('uint8'), alpha])
img = Image.fromarray(rgba, 'RGBA')

# find vertical split (a fully-transparent column band near center)
opaque = alpha > 0
colcount = opaque.sum(axis=0)
mid = w // 2
# widen from mid to find a zero column
split = mid
for off in range(0, w // 2):
    if mid + off < w and colcount[mid + off] == 0:
        split = mid + off; break
    if mid - off >= 0 and colcount[mid - off] == 0:
        split = mid - off; break
print('split column =', split)


def bbox_of(mask):
    ys, xs = np.where(mask)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def crop_char(x0, x1, name):
    sub = opaque[:, x0:x1]
    bx0, by0, bx1, by1 = bbox_of(sub)
    # to absolute coords
    ax0, ax1 = x0 + bx0, x0 + bx1
    ay0, ay1 = by0, by1
    pad = 6
    fx0, fy0 = max(ax0 - pad, 0), max(ay0 - pad, 0)
    fx1, fy1 = min(ax1 + pad, w), min(ay1 + pad, h)
    full = img.crop((fx0, fy0, fx1, fy1))
    full.save(os.path.join(OUT, name + '_full.png'))
    # head crop: square, width = char width, from top
    cw = ax1 - ax0
    cx = (ax0 + ax1) // 2
    side = int(cw * 1.05)
    hx0 = max(cx - side // 2, 0)
    hx1 = min(hx0 + side, w)
    hy0 = max(ay0 - 4, 0)
    hy1 = min(hy0 + side, h)
    head = img.crop((hx0, hy0, hx1, hy1))
    head.save(os.path.join(OUT, name + '_head.png'))
    print(name, 'full', full.size, 'head', head.size)


crop_char(0, split, 'emma')       # left = female
crop_char(split, w, 'ryan')       # right = male
print('done ->', OUT)
