"""The app icon (.ico for Windows, .icns for macOS, .png) drawn from the control flag of webapp/static/ob-logo.svg,
so no binary picture has to live in the repo.   python desktop/icons.py build/icons"""
import os
import sys

from PIL import Image, ImageDraw


def flag(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m, w = round(size * 0.06), max(1, round(size * 0.035))
    box = [m, m, size - 1 - m, size - 1 - m]
    d.rectangle(box, fill=(255, 255, 255, 255))
    d.polygon([(box[2], box[1]), (box[2], box[3]), (box[0], box[3])], fill=(242, 107, 29, 255))
    d.rectangle(box, outline=(58, 58, 58, 255), width=w)
    return im


def main(out):
    os.makedirs(out, exist_ok=True)
    big = flag(1024)
    big.save(os.path.join(out, "app.png"))
    big.save(os.path.join(out, "app.ico"), sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    big.save(os.path.join(out, "app.icns"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join("build", "icons"))
