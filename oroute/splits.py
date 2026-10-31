"""Split-time analysis of a whole class (the WinSplits method), from official times only: no GPS, no map.

Input: for every runner the cumulative official times, seconds from the start to each control and, last,
to the finish (None = no punch). That is what ORIS getSplits gives (webapp.oris.parse_class_splits).

  reference time of a leg   mean of the best 25 % of the times run on it (at least one runner)
  performance index         reference / runner's time on the leg (1.0 = as fast as the reference)
  normal of a runner        the median of their indices over the legs: how fast they usually are
                            against the reference when nothing goes wrong
  expected time of a leg    reference / normal
  loss                      time - expected
  mistake                   loss over MISTAKE_S seconds and at the same time over MISTAKE_PCT of the
                            expected time (WinSplits defaults: 30 s and 25 %)
  superman                  the sum of the best time on every leg

Also here: how well a model's leg times agree in *order and proportion* with the class (rank_agreement),
the check from docs/pruzkum.md part 6, and the difficulty of a race against another one.
"""
import math

import numpy as np

TOP_SHARE = 0.25
MISTAKE_S = 30.0
MISTAKE_PCT = 0.25
MIN_LEG_S = 3  # shorter "times" are punching errors


def leg_times(cum):
    """Cumulative times -> time of each leg; None where one of its two punches is missing or the clock goes back."""
    out, prev = [], 0
    for c in cum:
        t = None if c is None or prev is None else c - prev
        out.append(t if t is not None and t >= MIN_LEG_S else None)
        prev = c
    return out


def reference(all_legs, share=TOP_SHARE):
    """Reference time per leg: the mean of the best `share` of the times on it. all_legs: one list per runner.
    None for a leg nobody has a time on."""
    n = max((len(l) for l in all_legs), default=0)
    ref = []
    for k in range(n):
        ts = sorted(l[k] for l in all_legs if k < len(l) and l[k] is not None)
        if not ts:
            ref.append(None)
            continue
        m = max(1, math.ceil(share * len(ts)))
        ref.append(float(np.mean(ts[:m])))
    return ref


def analyse(legs, ref, mistake_s=MISTAKE_S, mistake_pct=MISTAKE_PCT):
    """One runner against the reference. Returns dict(normal, legs=[dict(time, ref, index, expected, loss,
    mistake)], mistakes = seconds lost in mistakes, clean = time without them); values are None where the
    leg has no time."""
    idx = [r / t if t and r else None for t, r in zip(legs, ref)]
    have = [i for i in idx if i is not None]
    normal = float(np.median(have)) if have else None
    rows, lost = [], 0.0
    for t, r, i in zip(legs, ref, idx):
        if i is None or not normal:
            rows.append(dict(time=t, ref=r, index=None, expected=None, loss=None, mistake=False))
            continue
        exp = r / normal
        loss = t - exp
        bad = loss > mistake_s and loss > mistake_pct * exp
        lost += loss if bad else 0.0
        rows.append(dict(time=t, ref=r, index=i, expected=exp, loss=loss, mistake=bool(bad)))
    total = sum(t for t in legs if t is not None)
    return dict(normal=normal, legs=rows, mistakes=lost, clean=total - lost)


def class_table(runners, regno=None):
    """Everything the page shows for a class. runners: [dict(name, regno, club, place, time_s, status, cum)].
    Returns dict(n_legs, ref, ref_cum, best, superman, runners=[... + legs, analysis], me = index or None,
    ranks = rank of `me` on every leg (1 = fastest) or None)."""
    rows = [dict(r, legs=leg_times(r["cum"])) for r in runners]
    n = max((len(r["legs"]) for r in rows), default=0)
    rows = [r for r in rows if len(r["legs"]) == n]
    ref = reference([r["legs"] for r in rows])
    best = []
    for k in range(n):
        ts = [r["legs"][k] for r in rows if r["legs"][k] is not None]
        best.append(min(ts) if ts else None)
    for r in rows:
        r["analysis"] = analyse(r["legs"], ref)
    ref_cum, acc = [], 0.0
    for v in ref:
        acc += v or 0.0
        ref_cum.append(acc)
    me = next((i for i, r in enumerate(rows) if regno and (r.get("regno") or "").upper() == regno.upper()), None)
    ranks = None
    if me is not None:
        ranks = []
        for k in range(n):
            t = rows[me]["legs"][k]
            ranks.append(None if t is None else 1 + sum(1 for r in rows if r["legs"][k] is not None and r["legs"][k] < t))
    return dict(n_legs=n, ref=ref, ref_cum=ref_cum, best=best,
                superman=sum(b for b in best if b is not None) if all(b is not None for b in best) else None,
                runners=rows, me=me, ranks=ranks)


def _ranks(a):
    """Average ranks (ties share the mean rank), 1-based."""
    a = np.asarray(a, float)
    order = np.argsort(a, kind="stable")
    r = np.empty(len(a))
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    """Rank correlation of two equally long lists; None for fewer than 3 pairs or no spread."""
    if len(a) < 3 or len(a) != len(b):
        return None
    ra, rb = _ranks(a), _ranks(b)
    sa, sb = ra.std(), rb.std()
    if sa == 0 or sb == 0:
        return None
    return float(((ra - ra.mean()) * (rb - rb.mean())).mean() / (sa * sb))


def rank_agreement(model, ref, names=None):
    """Does the model order the legs by difficulty as the class does?

    model: model time of the best route per leg, ref: reference time of the class per leg (None = skip).
    The two need not agree in absolute terms (the class is another runner), only in order and proportion:
    a leg the model thinks is twice as long should be twice as long for the class.
    Returns dict(n, rho = rank correlation, scale = median ref/model, legs=[dict(leg, name, model, ref,
    dev = how far the leg is from the common proportion, as a ratio: 1.3 = the class needs 30 % more than
    the model's proportion says, i.e. the model is optimistic there)] sorted by the size of dev), or None
    when there are fewer than 3 usable legs.
    """
    ok = [k for k, (m, r) in enumerate(zip(model, ref)) if m and r and m > 0 and r > 0]
    if len(ok) < 3:
        return None
    lm = np.log([model[k] for k in ok])
    lr = np.log([ref[k] for k in ok])
    shift = float(np.median(lr - lm))
    dev = np.exp(lr - lm - shift)
    legs = [dict(leg=k + 1, name=(names[k] if names else str(k + 1)), model=float(model[k]), ref=float(ref[k]),
                 dev=float(d)) for k, d in zip(ok, dev)]
    legs.sort(key=lambda l: -abs(math.log(l["dev"])))
    return dict(n=len(ok), rho=spearman(lm, lr), scale=float(np.exp(shift)), legs=legs,
                spread=float(np.median(np.abs(np.log(dev)))))


def race_speed(ref, straight_m):
    """How fast the class reference runs this race in a straight line (m/s over the legs with a reference):
    a measure of the difficulty of the terrain that needs no GPS. None when nothing can be compared."""
    pairs = [(r, d) for r, d in zip(ref, straight_m) if r and d and d > 0]
    if not pairs:
        return None
    return float(sum(d for _, d in pairs) / sum(r for r, _ in pairs))
