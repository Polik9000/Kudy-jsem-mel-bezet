"""Read the course (start triangle, control circles, finish) from the purple overprint."""
import itertools
import json

import numpy as np
from scipy import ndimage as ndi

# What the course read from a map is for the same map: raised when that changes, so the web app reads the course of
# older analyses again (runner._analyse_in). 1: the finish told apart from a thick ring, circles cut open for a detail
# of the map looked for where the watch was at the punch, a control number left out (November 2026).
VERSION = 1

RING_M = 35.0            # inner radius of a control circle on the maps the radii below were set on (1:10 000)
RING_SAME = (0.86, 1.15)  # a map whose closed circles are within this of RING_M is read with those radii as they are
START_NEAR_M = 200.0     # the start triangle is looked for this far from where the recording begins
HOLLOW = 0.25            # a control circle is empty inside: with more purple than this in it, it is a circle found
                         # in the hatching of an out-of-bounds area (measured: circles up to 0.15, hatching 0.33+)
FINISH_SPREAD_PX = 5     # the radii of one centre that make the finish differ at least this much (pixels) ...
FINISH_SPREAD = 0.12     # ... and this share of the larger one (above 41 px of radius; no map read before had them)


def purple_mask(img_rgb):
    a = np.asarray(img_rgb).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # IOF course purple; Livelox renders it around (180, 70, 245)
    return (r > 140) & (b > 200) & (g < 140) & (b - g > 100)


def hough_circles(mask, radii, min_votes=0.35, min_sep=12):
    """Simple Hough transform for circle outlines. Returns list of (cx, cy, r, score)."""
    H, W = mask.shape
    ys, xs = np.nonzero(mask)
    angles = np.linspace(0, 2 * np.pi, 90, endpoint=False)
    found = []
    for r in radii:
        votes = []
        for a in angles:
            cx = np.round(xs - r * np.cos(a)).astype(int)
            cy = np.round(ys - r * np.sin(a)).astype(int)
            ok = (cx >= 0) & (cx < W) & (cy >= 0) & (cy < H)
            # one vote per (pixel, angle); count distinct angles hitting a centre
            votes.append((cy[ok] * W + cx[ok]).astype(np.int32))
        # counted in one go for the radius: the same numbers as np.add.at vote by vote, many times faster
        acc = np.bincount(np.concatenate(votes), minlength=H * W).reshape(H, W)
        # normalise: a perfect ring of ~3 px width gives ~ 3*90 votes; use fraction of angles
        score = acc / (len(angles) * 2.0)
        cand = np.argwhere(score >= min_votes)
        for cy, cx in cand:
            found.append((float(cx), float(cy), r, float(score[cy, cx])))
    found.sort(key=lambda c: -c[3])
    keep = []
    for c in found:
        if all(np.hypot(c[0] - k[0], c[1] - k[1]) > min_sep or abs(c[2] - k[2]) > 6 for k in keep):
            keep.append(c)
    return keep


def closed_shapes(mask):
    """What the purple print closes in: (inner radius in pixels of the control circles, or None;
    [(u, v, r)] of the holes shaped like a triangle, r = the distance of their corners from the centre).

    A control circle that nothing cuts closes in a round hole, and so does the inner ring of the finish and
    the 0, 6, 8 and 9 of the control numbers; the circles are the largest kind of round hole that there are
    at least three of. They say how large the course is printed (a sprint map 1:4 000 has circles a third
    of those of a forest map in metres). The start triangle closes in a hole whose inscribed circle is half
    of the circumscribed one and which fills 41 % of it."""
    holes, n = ndi.label(ndi.binary_fill_holes(mask) & ~mask)
    round_r, tri = [], []
    for i, sl in enumerate(ndi.find_objects(holes), 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h * w < 60 or max(h, w) > 4 * min(h, w):
            continue
        part = holes[sl] == i
        a = float(part.sum())
        if a < 60:
            continue
        v, u = np.nonzero(part)
        cv, cu = v.mean(), u.mean()
        r_out = float(np.hypot(v - cv, u - cu).max()) + 0.5
        r_in = float(ndi.distance_transform_edt(np.pad(part, 1)).max())
        if abs(h - w) <= 0.12 * max(h, w) and a > 0.72 * h * w and r_in > 0.85 * r_out:
            round_r.append((h + w) / 4)
        elif 0.44 <= r_in / r_out <= 0.58 and 0.36 <= a / (np.pi * r_out * r_out) <= 0.5:
            tri.append((float(cu + sl[1].start), float(cv + sl[0].start), r_out))
    ring = None
    for r in sorted(round_r, reverse=True):
        if sum(abs(q - r) <= 0.06 * r for q in round_r) >= 3:
            ring = float(np.median([q for q in round_r if abs(q - r) <= 0.06 * r]))
            break
    return ring, tri


def _inside(m, cx, cy, r):
    """Share of purple inside a circle (up to three quarters of its radius)."""
    q = int(r) + 1
    y0, x0 = max(int(cy) - q, 0), max(int(cx) - q, 0)
    part = m[y0:int(cy) + q + 1, x0:int(cx) + q + 1]
    yy, xx = np.mgrid[y0:y0 + part.shape[0], x0:x0 + part.shape[1]]
    return float(part[np.hypot(xx - cx, yy - cy) <= 0.75 * r].mean())


def _circles(m, mpp, radius_m):
    """(finish (x, y) or None, controls [(x, y, r)]) among the circles of these radii (metres)."""
    radii = list(range(int(radius_m[0] / mpp), int(radius_m[1] / mpp) + 1, 1))
    circles = hough_circles(m, radii)
    # merge circles with the same centre: two concentric radii = finish
    groups = []
    for c in circles:
        for g in groups:
            if np.hypot(c[0] - g[0][0], c[1] - g[0][1]) < 10:
                g.append(c)
                break
        else:
            groups.append([c])
    finish, controls = None, []
    for g in groups:
        rs = sorted({round(c[2]) for c in g})
        # two rings of clearly different size: the inner ring of the finish is about 0.76 of the outer one. A thick
        # ring of a map exported at high resolution (7 px at 0.43 m/px) matches several radii by itself, up to
        # its width apart; with a fixed 5 px all of its circles were taken for finishes (Bohemia 2025 E1: 2 of 11)
        if len(rs) >= 2 and rs[-1] - rs[0] >= max(FINISH_SPREAD_PX, FINISH_SPREAD * rs[-1]):
            if finish is None:
                finish = (g[0][0], g[0][1])
            continue
        best = max(g, key=lambda c: c[3])
        if _inside(m, best[0], best[1], best[2]) <= HOLLOW:
            controls.append((best[0], best[1], best[2]))
    # remove the finish's rings that also matched as a control
    if finish:
        controls = [c for c in controls if np.hypot(c[0] - finish[0], c[1] - finish[1]) > 15]
    return finish, controls


def detect_course(geomap, radius_m=(30, 45), start_hint_px=None):
    """Detect controls on the map image.

    Returns dict with pixel coords: start (x,y) or None, controls [(x,y,r)], finish (x,y) or None.
    Order is NOT known from the image; use order_by_track() for that.

    radius_m fits a course printed for 1:10 000 or 1:15 000. Where the closed circles of the map say the
    course is printed in another size (closed_shapes), the radii follow it; when that finds no finish or
    fewer than two controls, radius_m as given is tried.
    start_hint_px: where the recording begins. The start is the centre of the start triangle: the one near
    the purple blob that lies at the hint (the blob itself may be the line where the time starts, a marked
    route away from the triangle, or the triangle with a control number printed over it), and without a
    blob or with no triangle within START_NEAR_M of it (the watch was started elsewhere) the triangle the
    course line runs from. A map whose triangle is not closed keeps the blob.
    """
    m = purple_mask(geomap.image)
    mpp = (geomap.m_per_px_x + geomap.m_per_px_y) / 2
    ring, shapes = closed_shapes(m)
    tries = [radius_m]
    if ring is not None and not RING_SAME[0] <= ring * mpp / RING_M <= RING_SAME[1]:
        k = ring * mpp / RING_M
        tries = [(radius_m[0] * k - mpp, radius_m[1] * k), radius_m]
    for rng in tries:
        finish, controls = _circles(m, mpp, rng)
        if finish is not None and len(controls) >= 2:
            break

    start = None
    if start_hint_px is not None:
        start = _find_triangle(m, controls, finish, start_hint_px, int(START_NEAR_M / mpp))
    if controls:
        rc = float(np.median([c[2] for c in controls]))
        tri = [t for t in shapes if 0.95 * rc <= t[2] <= 1.4 * rc
               and all(np.hypot(t[0] - c[0], t[1] - c[1]) > c[2] for c in controls)]
        far = lambda t: np.hypot(start[0] - t[0], start[1] - t[1])
        near = [t for t in tri if start is not None and far(t) * mpp <= START_NEAR_M]
        if near:
            start = min(near, key=far)[:2]
        elif tri:
            start = max(tri, key=lambda t: max(line_score(m, t, c, t[2], c[2]) for c in controls))[:2]
    return {"start": start, "controls": controls, "finish": finish, "mask": m}


def ring_cover(mask, cx, cy, r, sectors=72, width=1.5):
    """How much of a circle outline is printed: (share of the sectors with purple on the ring, the largest
    run of empty sectors in degrees, the number of such gaps). A control circle the cartographer cut open for
    a detail of the map (ISOM: the circle must not hide what it points at) keeps arcs; a line crossing the
    spot only touches two sectors."""
    H, W = mask.shape
    hit = np.zeros(sectors, bool)
    for s in range(sectors):
        for a in np.linspace(s, s + 1, 4, endpoint=False) * 2 * np.pi / sectors:
            for q in (r - width, r, r + width):
                x, y = int(round(cx + q * np.cos(a))), int(round(cy + q * np.sin(a)))
                if 0 <= x < W and 0 <= y < H and mask[y, x]:
                    hit[s] = True
    if hit.all():
        return 1.0, 0.0, 0
    # runs of empty sectors around the circle, starting just after a printed one
    k0 = int(np.argmax(hit))
    runs, run = [], 0
    for s in range(sectors):
        if hit[(k0 + s) % sectors]:
            if run:
                runs.append(run)
            run = 0
        else:
            run += 1
    if run:
        runs.append(run)
    return float(hit.mean()), (max(runs) * 360.0 / sectors if runs else 360.0), len(runs)


MISSING_WINDOW_M = 80.0   # a missed circle is looked for this far from where the watch was at its official punch
MISSING_VOTES = 0.12      # Hough share for such a circle: a cut circle keeps only arcs (detect_course needs 0.35)
MISSING_COVER = 0.4       # ... and it is taken with at least this share of its outline printed
MISSING_GAP = 150.0       # ... no gap wider than this (degrees; real cut circles: 25 to 55)
MISSING_LINE = 0.4        # ... and a leg line ending at it, or
MISSING_ALONE = 0.6       # ... this share of its outline without a line (a control the lines of the map hide)


def find_missing(mask, mpp, start, controls, finish, hints, want):
    """The control circles detect_course did not find, looked for only where the organiser's times say a control
    is: hints are [(u, v) or None] in pixels, where the watch was at each official punch, in the order of the
    course. A hint with no circle near it gets the cut-open circle nearest to it that has the radius of the
    others, enough of its outline printed (ring_cover), no purple inside (not the hatching of an out-of-bounds
    area) and a leg line from the neighbouring control ending at it. Nothing is looked for once there are
    `want` circles (the number of controls in the official results).
    Returns ([(x, y, r)] added, [dict per hint looked at: k, found, cover, gap, line]) for the record."""
    added, notes = [], []
    if not controls or len(controls) >= want:
        return added, notes
    r = int(round(float(np.median([c[2] for c in controls]))))
    near = (r + 40.0 / mpp)
    have = lambda h, cs: any(np.hypot(h[0] - c[0], h[1] - c[1]) <= near for c in cs)
    H, W = mask.shape
    win = int(MISSING_WINDOW_M / mpp) + r + 3

    def neighbour(k, step):
        """The course point next to control k: the circle at the next hint (where the watch was, when that control
        has no circle either), else the start or the finish."""
        j = k + step
        while 0 <= j < len(hints):
            h = hints[j]
            if h is not None:
                cs = [c for c in controls + added if np.hypot(h[0] - c[0], h[1] - c[1]) <= near]
                if cs:
                    return min(cs, key=lambda c: np.hypot(h[0] - c[0], h[1] - c[1]))
                return (h[0], h[1], r)
            j += step
        end = start if step < 0 else finish
        return None if end is None else (end[0], end[1], r)

    for k, h in enumerate(hints):
        if len(controls) + len(added) >= want:
            break
        if h is None or have(h, controls + added):
            continue
        x0, y0 = max(int(h[0]) - win, 0), max(int(h[1]) - win, 0)
        sub = mask[y0:min(int(h[1]) + win, H), x0:min(int(h[0]) + win, W)]
        best, note = None, dict(k=k + 1, found=False)
        for cx, cy, cr, _ in hough_circles(sub, range(max(r - 2, 3), r + 3), min_votes=MISSING_VOTES, min_sep=r):
            cx, cy = cx + x0, cy + y0
            d = np.hypot(cx - h[0], cy - h[1])
            if d * mpp > MISSING_WINDOW_M:
                continue
            if any(np.hypot(cx - c[0], cy - c[1]) <= max(c[2], cr) for c in controls + added):
                continue
            if any(p is not None and np.hypot(cx - p[0], cy - p[1]) <= 1.5 * cr for p in (start, finish)):
                continue
            if _inside(mask, cx, cy, cr) > HOLLOW:
                continue
            cover, gap, _ = ring_cover(mask, cx, cy, cr)
            line = max((line_score(mask, (cx, cy), q, cr, q[2]) for q in (neighbour(k, -1), neighbour(k, 1))
                        if q is not None), default=0.0)
            ok = cover >= MISSING_COVER and gap <= MISSING_GAP and (line >= MISSING_LINE or cover >= MISSING_ALONE)
            seen = dict(k=k + 1, found=ok, cover=round(cover, 2), gap=round(gap), line=round(line, 2),
                        off_m=round(float(d * mpp), 1), px=[round(float(cx), 1), round(float(cy), 1)])
            if ok and (best is None or d < best[0]):
                best, note = (d, (float(cx), float(cy), cr)), seen
            elif best is None and cover > note.get("cover", -1):
                note = seen          # the best one that was not taken, for the record
        notes.append(note)
        if best is not None:
            added.append(best[1])
    return added, notes


def drop_extra(controls, hints, want, mpp):
    """Circles that are no control: a control number read as a circle (the 0 of a "10" printed over a "4",
    Přebor BFM+SFM 2026). Only when the organiser's times show every punch (hints [(u, v)], none None), and only
    the circles farther than MISSING_WINDOW_M from every place the watch was at a punch, and only when leaving
    those out gives exactly `want` circles: a map with far more circles than controls (its purple read wrong) is
    left as it is for the person to correct. Returns the circles to leave out."""
    if len(controls) <= want or not hints or any(h is None for h in hints):
        return []
    far = [c for c in controls if all(np.hypot(c[0] - h[0], c[1] - h[1]) * mpp > MISSING_WINDOW_M for h in hints)]
    return far if len(controls) - len(far) == want else []


def _find_triangle(mask, controls, finish, hint, search_px, box=35):
    """Densest purple blob near the hint that is not a control ring: the start triangle."""
    m = mask.copy()
    H, W = m.shape
    yy, xx = np.mgrid[0:H, 0:W]
    for c in controls + ([finish + (40,)] if finish else []):
        m &= np.hypot(xx - c[0], yy - c[1]) > c[2] + 8
    ys, xs = np.nonzero(m)
    near = np.hypot(xs - hint[0], ys - hint[1]) < search_px
    xs, ys = xs[near], ys[near]
    if len(xs) == 0:
        return None
    best, best_n = None, 0
    for x, y in zip(xs[::3], ys[::3]):
        n = np.count_nonzero((np.abs(xs - x) < box) & (np.abs(ys - y) < box))
        if n > best_n:
            best_n, best = n, (x, y)
    sel = (np.abs(xs - best[0]) < box) & (np.abs(ys - best[1]) < box)
    return (float(xs[sel].mean()), float(ys[sel].mean()))


def save_course(path, geomap, course_px):
    """Write course as JSON (pixel + lat/lon) so it can be hand-corrected and reused."""
    def pt(p):
        lat, lon = geomap.px_to_latlon(p[0], p[1])
        return {"px": [round(p[0], 1), round(p[1], 1)], "lat": float(lat), "lon": float(lon)}
    out = {
        "start": pt(course_px["start"]) if course_px.get("start") else None,
        "controls": [dict(pt(c), code=i + 1) for i, c in enumerate(course_px["controls"])],
        "finish": pt(course_px["finish"]) if course_px.get("finish") else None,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    return out


def load_course(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def line_score(mask, p, q, rp, rq, step=1.0):
    """Fraction of purple pixels along the straight segment between two circle rims."""
    p, q = np.asarray(p[:2], float), np.asarray(q[:2], float)
    d = np.linalg.norm(q - p)
    if d <= rp + rq + 10:
        return 0.0
    u = (q - p) / d
    ts = np.arange(rp + 4, d - rq - 4, step)
    H, W = mask.shape
    hits = 0
    for t in ts:
        x, y = p + u * t
        xi, yi = int(round(x)), int(round(y))
        y0, y1, x0, x1 = max(yi - 2, 0), min(yi + 3, H), max(xi - 2, 0), min(xi + 3, W)
        hits += bool(mask[y0:y1, x0:x1].any())
    return hits / max(len(ts), 1)


EXACT_UP_TO = 20  # controls; the table over all subsets of controls doubles with each one (20: 335 MB)


def _search_order(S, k):
    """Order of the controls on a strong start -> ... -> finish path, for a course with too many controls for
    the table of all subsets. First a greedy path: from the start always along the strongest line to a control
    not visited yet. Then stretches of it are reversed or moved for as long as the sum of the line scores
    grows (the same moves as order_by_track). The usual trap of the greedy path, a control lying on the line
    of another leg and taken too early, is one such move away from the right order. Not proved to be the best
    path as the table is; the GPS track checks the order afterwards (order_by_track).
    Returns indices into the controls."""
    def total(perm):
        seq = np.r_[0, np.asarray(perm, int) + 1, k + 1]
        return float(S[seq[:-1], seq[1:]].sum())

    perm, free, u = [], set(range(k)), 0
    while free:
        c = max(sorted(free), key=lambda c: S[u, c + 1])
        perm.append(c)
        free.discard(c)
        u = c + 1
    best = total(perm)
    while True:
        cand, cand_v = None, best + 1e-9
        for i in range(k):
            for j in range(i + 1, k + 1):
                seg, rest = perm[i:j], perm[:i] + perm[j:]
                for p in [perm[:i] + seg[::-1] + perm[j:]] + [rest[:q] + seg + rest[q:]
                                                                for q in range(len(rest) + 1) if q != i]:
                    v = total(p)
                    if v > cand_v:
                        cand, cand_v = p, v
        if cand is None:
            return perm
        perm, best = cand, cand_v


def order_by_lines(mask, start, controls, finish, tri_r=25, fin_r=30):
    """Recover course order from the purple leg lines: best start->...->finish path
    through all controls, maximising total line coverage (bitmask DP up to EXACT_UP_TO controls,
    above that a greedy path improved by moving stretches of it, _search_order)."""
    nodes = [(start[0], start[1], tri_r)] + [tuple(c) for c in controls] + [(finish[0], finish[1], fin_r)]
    n = len(nodes)
    S = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            S[i, j] = S[j, i] = line_score(mask, nodes[i], nodes[j], nodes[i][2], nodes[j][2])
    k = len(controls)
    if k > EXACT_UP_TO:
        order = _search_order(S, k)
        seq = [0] + [o + 1 for o in order] + [n - 1]
        return [controls[o] for o in order], [S[a, b] for a, b in zip(seq, seq[1:])]
    NEG = -1e9
    dp = np.full((1 << k, k), NEG)
    par = np.full((1 << k, k), -1, int)
    for j in range(k):
        dp[1 << j, j] = S[0, j + 1]
    # All sets of the same size at once: a set of p + 1 controls needs only the sets of p. For every set and
    # every control nx outside it, the best control j to come from. Entries of controls outside the set stay
    # at NEG and never win; of equal ones np.argmax takes the first, the lowest j, exactly as going through
    # j in order and replacing only on a strictly better value does. (In plain Python loops this took over a
    # minute for 19 controls and doubled with every further one.)
    sets = np.arange(1 << k)
    size = sum((sets >> b) & 1 for b in range(k))
    Sc = S[1:k + 1, 1:k + 1]
    for p in range(1, k):
        of_size = sets[size == p]
        for nx in range(k):
            src = of_size[((of_size >> nx) & 1) == 0]
            v = dp[src] + Sc[:, nx]
            j = np.argmax(v, axis=1)
            dp[src | 1 << nx, nx] = v[np.arange(len(src)), j]
            par[src | 1 << nx, nx] = j
    full = (1 << k) - 1
    last = int(np.argmax(dp[full] + S[1:k + 1, n - 1]))
    order, mset = [], full
    while last != -1:
        order.append(last)
        prev = par[mset, last]
        mset ^= 1 << last
        last = prev
    order.reverse()
    seq = [0] + [o + 1 for o in order] + [n - 1]
    scores = [S[a, b] for a, b in zip(seq, seq[1:])]
    return [controls[o] for o in order], scores


def fill_order(mask, start, controls, finish, order, tri_r=25, fin_r=30):
    """Complete an order of the controls that has None where the organiser's times could not say which
    circle it was (official.order_controls on a recording that shows only a part of the race): the circles
    left over go into those places the way the purple lines run best. order: indices into controls or None."""
    slots = [k for k, o in enumerate(order) if o is None]
    if not slots:
        return list(order)
    left = [i for i in range(len(controls)) if i not in order]
    nodes = [(start[0], start[1], tri_r)] + [tuple(c) for c in controls] + [(finish[0], finish[1], fin_r)]
    S = _line_matrix(mask, nodes)
    best, best_v = None, -1.0
    for perm in itertools.permutations(left):
        full = list(order)
        for k, c in zip(slots, perm):
            full[k] = c
        seq = [0] + [o + 1 for o in full] + [len(nodes) - 1]
        v = float(sum(S[a, b] for a, b in zip(seq, seq[1:])))
        if v > best_v:
            best, best_v = full, v
    return best


def _line_matrix(mask, nodes):
    n = len(nodes)
    S = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            S[i, j] = S[j, i] = line_score(mask, nodes[i], nodes[j], nodes[i][2], nodes[j][2])
    return S


def order_by_track(mask, start, controls, finish, ordered, to_xy, tx, ty, tri_r=25, fin_r=30,
                   drop_near_finish_m=25.0, gps_weight=0.05):
    """Fix the course order with the GPS track (no manual editing of course.json).

    The purple leg lines alone can be read backwards or start in the wrong place
    (Pohora, Petřvald). Starting from the line order, a local search reverses or moves
    stretches of controls and keeps a change when
        sum(line scores) - gps_weight * sum(excess punch distance in m)
    improves, where punch distances come from find_punches (track visits the controls in
    this order, forward in time only). A control circle that lies on the finish circle
    is dropped (the double finish ring is sometimes also found as a control).
    Returns (ordered_controls, line_scores, dropped_controls)."""
    from .analysis import find_punches

    fxy = to_xy(finish)
    keep, dropped = [], []
    for c in ordered:
        cx, cy = to_xy(c)
        (dropped if np.hypot(cx - fxy[0], cy - fxy[1]) < drop_near_finish_m else keep).append(c)
    nodes = [(start[0], start[1], tri_r)] + [tuple(c) for c in keep] + [(finish[0], finish[1], fin_r)]
    S = _line_matrix(mask, nodes)
    xy = [to_xy(p) for p in nodes]
    t = np.arange(len(tx), dtype=float)
    k = len(keep)

    def score(perm):
        seq = [0] + [p + 1 for p in perm] + [k + 1]
        lines = sum(S[a, b] for a, b in zip(seq, seq[1:]))
        pts = [xy[i] for i in seq]
        idx = find_punches(t, tx, ty, pts)
        d = [np.hypot(tx[i] - p[0], ty[i] - p[1]) for i, p in zip(idx[1:-1], pts[1:-1])]
        gps = sum(max(0.0, min(v, 300.0) - 15.0) for v in d)
        return lines - gps_weight * gps

    perm = list(range(k))
    best = score(perm)
    improved = True
    while improved:
        improved = False
        cands = []
        for i in range(k):
            for j in range(i + 1, k + 1):
                cands.append(perm[:i] + perm[i:j][::-1] + perm[j:])          # reverse a stretch
                seg, rest = perm[i:j], perm[:i] + perm[j:]
                for p in range(len(rest) + 1):                               # move a stretch
                    if p != i:
                        cands.append(rest[:p] + seg + rest[p:])
        for c in cands:
            v = score(c)
            if v > best + 1e-9:
                best, perm, improved = v, c, True
    seq = [0] + [p + 1 for p in perm] + [k + 1]
    return [keep[p] for p in perm], [S[a, b] for a, b in zip(seq, seq[1:])], dropped
