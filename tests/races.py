"""The four analysed races in data/ and the start-to-finish times they must keep giving."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "tests", "golden")


def _s(mmss):
    m, s = mmss.split(":")
    return int(m) * 60 + int(s)


# folder in data/, title (as stored in data/*/fit_samples.npz), start-to-finish time from the GPS track alone
# (what analyze.py gave before the web app). Pohora's official time is 50:22: its finish is found late from GPS,
# which the official ORIS times correct (tests/test_official.py).
RACES = [
    ("azymut-e5", "Azymut Cup 2026 E5", _s("77:02")),
    ("azymut-e4", "Azymut Cup 2026 E4 (Białobrzegi)", _s("55:07")),
    ("pohora", "MO krátká trať 2025, Pohora (H16C)", _s("51:05")),
    ("petrvald", "MO dlouhá trať 2026, Petřvald u Karviné (H18)", _s("80:18")),
]
IDS = [r[0] for r in RACES]


def inputs(folder):
    d = os.path.join(ROOT, "data", folder)
    return os.path.join(d, "course.kmz"), os.path.join(d, "maponly.kmz"), os.path.join(d, "run.fit")


def have_data():
    """True when the race inputs of data/ and their elevation in tests/golden are here. They are maps from
    Livelox and the author's own runs, so they are only in the author's private copy, not in the public repo."""
    return all(os.path.exists(p) for r in IDS for p in inputs(r)) and all(
        os.path.exists(os.path.join(GOLDEN, r, "dem_cache.npz")) for r in IDS)
