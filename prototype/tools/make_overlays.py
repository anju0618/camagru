"""Generate the overlay PNGs in public/overlays (run: python3 tools/make_overlays.py)."""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app import png  # noqa: E402

W, H = 640, 480
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "overlays")


def canvas():
    return bytearray(W * H * 4)


def put(img, x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 4
        img[i:i + 4] = bytes(color)


def ellipse(img, cx, cy, rx, ry, color):
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                put(img, x, y, color)


def rect(img, x0, y0, x1, y1, color):
    for y in range(y0, y1):
        for x in range(x0, x1):
            put(img, x, y, color)


def frame():
    img = canvas()
    for y in range(H):
        for x in range(W):
            d = min(x, y, W - 1 - x, H - 1 - y)
            if d < 6:
                put(img, x, y, (255, 255, 255, 255))
            elif d < 30:
                put(img, x, y, (232, 74, 140, 255))
            elif d < 34:
                put(img, x, y, (255, 255, 255, 255))
    return img


def glasses():
    img = canvas()
    dark = (20, 20, 24, 235)
    ellipse(img, 215, 210, 78, 52, dark)
    ellipse(img, 425, 210, 78, 52, dark)
    rect(img, 290, 196, 350, 212, dark)
    rect(img, 0, 196, 140, 208, dark)
    rect(img, 500, 196, 640, 208, dark)
    ellipse(img, 190, 190, 22, 12, (255, 255, 255, 90))
    ellipse(img, 400, 190, 22, 12, (255, 255, 255, 90))
    return img


def confetti():
    img = canvas()
    rnd = random.Random(7)
    colors = [(255, 82, 82), (255, 193, 7), (76, 175, 80), (33, 150, 243), (156, 39, 176)]
    for _ in range(90):
        ellipse(img, rnd.randrange(W), rnd.randrange(H), rnd.randrange(3, 9),
                rnd.randrange(3, 9), rnd.choice(colors) + (230,))
    return img


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("frame", frame), ("glasses", glasses), ("confetti", confetti)):
        with open(os.path.join(OUT, name + ".png"), "wb") as f:
            f.write(png.encode(W, H, fn()))
        print("wrote", name)
