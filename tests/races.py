"""The four analysed races in data/ and the start-to-finish times they must keep giving."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The real races (other people's maps and the author's runs) are not in the public repository. They are read from
# data/ and tests/golden, or from the folder OB_TEST_DATA (with the races as folders and the golden files in golden/).
# Without them the tests that need them are skipped and the others use the made-up races of tests/synthetic.py.
DATA = os.environ.get("OB_TEST_DATA") or os.path.join(ROOT, "data")
GOLDEN = os.path.join(os.environ["OB_TEST_DATA"], "golden") if os.environ.get("OB_TEST_DATA") \
    else os.path.join(ROOT, "tests", "golden")


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


def real_inputs(folder):
    d = os.path.join(DATA, folder)
    return os.path.join(d, "course.kmz"), os.path.join(d, "maponly.kmz"), os.path.join(d, "run.fit")


def inputs(folder):
    """(course.kmz, maponly.kmz, run.fit) of a race: the real one, or a made-up one at the same place and time."""
    if all(os.path.exists(p) for p in real_inputs(folder)):
        return real_inputs(folder)
    import synthetic
    return synthetic.inputs(folder)


def have_data():
    """True when the race inputs of data/ and their elevation in tests/golden are here. They are maps from
    Livelox and the author's own runs, so they are only in the author's private copy, not in the public repo."""
    return all(os.path.exists(p) for r in IDS for p in real_inputs(r)) and all(
        os.path.exists(os.path.join(GOLDEN, r, "dem_cache.npz")) for r in IDS)
