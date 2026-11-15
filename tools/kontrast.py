"""Contrast of the text colours of the app against its backgrounds (WCAG 2), in the dark and the light mode.

Reads the tokens of webapp/static/les.css and prints a Markdown table (docs/vzhled.md). Normal text needs 4.5 : 1.
    python tools/kontrast.py
"""
import os
import re
import sys

CSS = os.path.join(os.path.dirname(__file__), "..", "webapp", "static", "les.css")

# (text token, background token, where it is used); a background "a+b@k" is b mixed into a at k (an rgba overlay)
PAIRS = [
    ("--text-primary", "--bg-app", "text na pozadí stránky"),
    ("--text-primary", "--bg-panel-primary", "text na panelu"),
    ("--text-secondary", "--bg-panel-primary", "vedlejší text na panelu"),
    ("--text-secondary", "--bg-panel-secondary", "vedlejší text v záhlaví tabulky"),
    ("--text-muted", "--bg-panel-primary", "tlumený text na panelu"),
    ("--text-muted", "--bg-app", "tlumený text na pozadí (patička)"),
    ("--odkaz", "--bg-panel-primary", "odkaz na panelu"),
    ("--odkaz", "--bg-app", "odkaz na pozadí"),
    ("--on-brand", "--zelena", "hlavní tlačítko"),
    ("--text-primary", "--bg-panel-secondary", "tlačítko"),
    ("--status-model-green", "--bg-panel-primary", "štítek „hotovo“ / Nahráno"),
    ("--status-loss-amber", "--bg-panel-primary", "ztráta, štítek „chybí“"),
    ("--status-loss-amber", "--bg-panel-primary+--status-loss-dim", "štítek „chybí“ na podbarvení"),
    ("--cerv-cit", "--bg-panel-primary", "chyba"),
    ("--zelena", "--bg-panel-primary", "aktivní filtr, odkaz Další krok"),
]


def tokens(css, selector):
    block = css[css.index(selector):]
    block = block[block.index("{") + 1:block.index("}")]
    return dict(re.findall(r"(--[\w-]+):\s*([^;]+);", block))


def rgba(value):
    value = value.strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", value)
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (1.0,)
    m = re.fullmatch(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", value)
    if m:
        return tuple(int(m.group(i)) for i in (1, 2, 3)) + (float(m.group(4)),)
    raise ValueError(value)


def over(top, bottom):
    a = top[3]
    return tuple(top[i] * a + bottom[i] * (1 - a) for i in range(3)) + (1.0,)


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def table():
    css = open(CSS, encoding="utf-8").read()
    dark = tokens(css, ":root, :root:not")
    light = dict(dark, **tokens(css, ':root[data-theme="svetly"] {'))
    rows, worst = [], 99.0
    for fg, bg, where in PAIRS:
        cells = []
        for t in (dark, light):
            parts = bg.split("+")
            back = rgba(t[parts[0]])
            for p in parts[1:]:
                back = over(rgba(t[p]), back)
            r = ratio(rgba(t[fg]), back)
            worst = min(worst, r)
            cells.append(f"{r:.1f} : 1" + ("" if r >= 4.5 else " ✗"))
        rows.append(f"| {where} | `{fg}` na `{bg}` | {cells[0]} | {cells[1]} |")
    head = "| Kde | Barvy | Tmavý | Světlý |\n|---|---|---|---|\n"
    return head + "\n".join(rows), worst


if __name__ == "__main__":
    text, worst = table()
    print(text)
    print(f"\nNejhorší: {worst:.1f} : 1")
    sys.exit(0 if worst >= 4.5 else 1)
