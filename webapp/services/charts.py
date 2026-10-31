"""Charts as plain SVG written by hand (no library, nothing from another origin: the club site's CSP).
Colours come from the classes in static/ob.css (.ob-graf .ja, .ostatni, .ref, .chyba ...), so they follow
the light and dark mode."""
import math

from markupsafe import Markup, escape


def ticks(lo, hi, n=6):
    """About n round values covering lo..hi."""
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / max(n, 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    first = math.ceil(lo / step - 1e-9) * step
    out = []
    v = first
    while v <= hi + 1e-9:
        out.append(round(v, 10))
        v += step
    return out


def _fmt(v):
    return f"{v:g}"


class Frame:
    """Plot area with linear axes; turns data values into SVG coordinates."""

    def __init__(self, xr, yr, width=760, height=320, left=52, right=14, top=14, bottom=38, flip_y=False):
        self.w, self.h, self.l, self.r, self.t, self.b = width, height, left, right, top, bottom
        self.x0, self.x1 = xr
        self.y0, self.y1 = yr
        if self.x1 <= self.x0:
            self.x1 = self.x0 + 1
        if self.y1 <= self.y0:
            self.y1 = self.y0 + 1
        self.flip_y = flip_y

    def x(self, v):
        return self.l + (v - self.x0) / (self.x1 - self.x0) * (self.w - self.l - self.r)

    def y(self, v):
        f = (v - self.y0) / (self.y1 - self.y0)
        if not self.flip_y:
            f = 1 - f
        return self.t + f * (self.h - self.t - self.b)

    def path(self, pts):
        return " ".join(f"{'M' if i == 0 else 'L'}{self.x(px):.1f} {self.y(py):.1f}" for i, (px, py) in enumerate(pts))

    def axes(self, xt, yt, xlabel="", ylabel="", xfmt=_fmt, yfmt=_fmt):
        o = []
        for v in yt:
            o.append(f'<path class="mrizka" d="M{self.l} {self.y(v):.1f}H{self.w - self.r}"/>')
            o.append(f'<text x="{self.l - 6}" y="{self.y(v) + 4:.1f}" text-anchor="end">{escape(yfmt(v))}</text>')
        for v in xt:
            o.append(f'<path class="osa" d="M{self.x(v):.1f} {self.h - self.b}v4"/>')
            o.append(f'<text x="{self.x(v):.1f}" y="{self.h - self.b + 16}" text-anchor="middle">{escape(xfmt(v))}</text>')
        o.append(f'<path class="osa" d="M{self.l} {self.t}V{self.h - self.b}H{self.w - self.r}"/>')
        if xlabel:
            o.append(f'<text x="{(self.l + self.w - self.r) / 2:.0f}" y="{self.h - 6}" text-anchor="middle">'
                     f'{escape(xlabel)}</text>')
        if ylabel:
            o.append(f'<text x="12" y="{(self.t + self.h - self.b) / 2:.0f}" text-anchor="middle" '
                     f'transform="rotate(-90 12 {(self.t + self.h - self.b) / 2:.0f})">{escape(ylabel)}</text>')
        return o

    def svg(self, parts, title):
        return Markup(f'<svg class="ob-graf" viewBox="0 0 {self.w} {self.h}" role="img" '
                      f'aria-label="{escape(title)}"><title>{escape(title)}</title>' + "".join(parts) + "</svg>")


def mmss(s):
    s = int(round(s))
    return f"{'-' if s < 0 else ''}{abs(s) // 60}:{abs(s) % 60:02d}"


def slope_chart(model, curve=(), lo=-30, hi=30):
    """Time multiplier of the speed model by slope (%), with the measured bins when the slope was fitted
    on the runner's own activities (curve = [{grade, pace_mult, n}])."""
    import numpy as np
    g = np.arange(lo, hi + 0.5, 1.0)
    mult = model.slope_mult(g / 100)
    curve = [c for c in curve if lo <= c["grade"] * 100 <= hi]
    top = max(float(mult.max()), max((c["pace_mult"] for c in curve), default=0)) * 1.05
    fr = Frame((lo, hi), (0, top), height=300)
    parts = fr.axes(ticks(lo, hi, 12), ticks(0, top, 6), "sklon ve směru běhu (%)", "čas × proti rovině",
                    xfmt=lambda v: f"{v:+g}" if v else "0", yfmt=lambda v: f"{v:g}×")
    parts.append(f'<path class="ref" d="M{fr.l} {fr.y(1):.1f}H{fr.w - fr.r}"/>')
    parts.append(f'<path class="ja" d="{fr.path(list(zip(g.tolist(), mult.tolist())))}"/>')
    for c in curve:
        parts.append(f'<circle class="bod" cx="{fr.x(c["grade"] * 100):.1f}" cy="{fr.y(c["pace_mult"]):.1f}" r="3">'
                     f'<title>{c["grade"] * 100:+.1f} %: {c["pace_mult"]:.2f}× ({c["n"]} úseků po 30 s)</title></circle>')
    return fr.svg(parts, "Křivka sklonu: kolikrát déle trvá metr běhu podle sklonu")


SPLITS_TOP = 42      # room above the plot of the split-time graph for the numbers of the controls (px), two rows
SPLITS_HEADROOM = 0.06   # ... and above the fastest runner inside it (share of the height)


def splits_chart(runners, ref_cum, me=None, mistakes=(), max_others=60):
    """Time behind the reference runner (y, down = more behind) against the reference time (x), one line per
    runner: the classic split-time graph. runners: [{name, cum: [s or None per control + finish]}];
    ref_cum: reference cumulative times; me: index into runners; mistakes: leg numbers (1-based) of `me`.

    The numbers of the controls are above the plot, and the plot reaches above the fastest runner, so no line runs
    into them. Every line carries its runner's name and the loss at every control (data-jmeno, data-body: "x,loss;"
    in SVG units and seconds) for static/ob.js, which shows them under the pointer (or the finger) and highlights the
    line; a wider invisible copy of each line (class zasah) is what the pointer hits."""
    ok = [(i, r) for i, r in enumerate(runners) if r["cum"] and r["cum"][-1] is not None]
    if not ok or not ref_cum:
        return None
    behind = lambda r: [(0.0, 0.0)] + [(ref_cum[k], c - ref_cum[k]) for k, c in enumerate(r["cum"]) if c is not None]
    ymax = max(max(p[1] for p in behind(r)) for _, r in ok)
    ymin = min(0.0, min(min(p[1] for p in behind(r)) for _, r in ok))
    pad = SPLITS_HEADROOM * max(ymax - ymin, 60.0)
    ymin -= pad
    fr = Frame((0, ref_cum[-1]), (ymin, ymax + pad / 3), height=440, top=SPLITS_TOP, flip_y=True)
    step = 300 if ref_cum[-1] <= 3600 else 600
    xt = [v for v in range(0, int(ref_cum[-1]) + 1, step)]
    parts = fr.axes(xt, [v for v in ticks(ymin, ymax, 8) if v >= ymin],
                    "referenční čas (průměr nejlepší čtvrtiny na úseku)", "ztráta na referenci", xfmt=mmss, yfmt=mmss)
    parts.append(f'<text x="{fr.l - 6}" y="{fr.t - 8}" text-anchor="end">kontrola</text>')
    last = [-1e9, -1e9]          # x of the last number in the lower and the upper row: close ones go to the other
    for k, c in enumerate(ref_cum[:-1]):
        x = fr.x(c)
        row = 0 if x - last[0] >= 16 else 1 if x - last[1] >= 16 else 0
        last[row] = x
        parts.append(f'<path class="mrizka" d="M{x:.1f} {fr.t}V{fr.h - fr.b}"/>')
        parts.append(f'<text class="kontrola" x="{x:.1f}" y="{fr.t - 8 - 14 * row}" text-anchor="middle">{k + 1}</text>')

    def line(cls, r):
        pts = behind(r)
        d = fr.path(pts)
        body = ";".join(f"{fr.x(x):.1f},{v:.0f}" for x, v in pts[1:])
        name = escape(r["name"])
        return (f'<path class="{cls}" d="{d}"><title>{name} {mmss(r["cum"][-1])}</title></path>'
                f'<path class="zasah" d="{d}" data-jmeno="{name}" data-body="{body}"/>')
    others = [r for i, r in ok if i != me]
    others.sort(key=lambda r: r["cum"][-1])
    for r in others[:max_others]:
        parts.append(line("ostatni", r))
    if me is not None and runners[me]["cum"] and runners[me]["cum"][-1] is not None:
        r = runners[me]
        parts.append(line("ja", r))
        for n in mistakes:
            c = r["cum"][n - 1]
            if c is not None:
                parts.append(f'<circle class="chyba" cx="{fr.x(ref_cum[n - 1]):.1f}" cy="{fr.y(c - ref_cum[n - 1]):.1f}" '
                             f'r="4.5"><title>chyba na úseku {n}</title></circle>')
    return fr.svg(parts, "Graf mezičasů kategorie")


def bars_chart(values, labels, flagged=(), ylabel="", title="", yfmt=mmss):
    """One bar per leg (e.g. time lost against the runner's own normal); flagged = indices drawn as mistakes."""
    if not values:
        return None
    vals = [v or 0.0 for v in values]
    lo, hi = min(0.0, min(vals)), max(vals) or 1.0
    fr = Frame((0, len(vals)), (lo, hi), height=240)
    parts = fr.axes([], ticks(lo, hi, 5), "", ylabel, yfmt=yfmt)
    bw = (fr.w - fr.l - fr.r) / len(vals)
    for i, v in enumerate(vals):
        y0, y1 = fr.y(max(v, 0)), fr.y(min(v, 0))
        parts.append(f'<rect class="sloupec{" zle" if i in flagged else ""}" x="{fr.x(i) + bw * .15:.1f}" y="{y0:.1f}" '
                     f'width="{bw * .7:.1f}" height="{max(y1 - y0, 0.5):.1f}"><title>{escape(labels[i])}: '
                     f'{escape(yfmt(v))}</title></rect>')
        if len(vals) <= 32:
            parts.append(f'<text x="{fr.x(i + .5):.1f}" y="{fr.h - fr.b + 16}" text-anchor="middle">'
                         f'{escape(labels[i])}</text>')
    return fr.svg(parts, title or ylabel)
