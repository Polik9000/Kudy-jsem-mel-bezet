"""Run the four races in data/ with run_race.py and store their CSVs in tests/golden/.

usage (inside the container): python tests/make_golden.py [WORK_DIR]

Only rerun this on purpose: the golden files are the reference that later changes to
analyze.py / bestroute.py must reproduce byte for byte (tests/test_regression.py).
The elevation tiles each race downloaded are kept too (dem_cache.npz), so the tests run offline.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from races import GOLDEN, RACES, ROOT, inputs  # noqa: E402

KEEP = ["legs.csv", "course.json", "best/best_legs.csv", "best/dem_cache.npz"]


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
    for folder, title, _ in RACES:
        out = os.path.join(work, folder)
        t0 = time.time()
        subprocess.run([sys.executable, os.path.join(ROOT, "run_race.py"), *inputs(folder), out, "--title", title],
                       check=True, cwd=ROOT)
        print(f"== {folder}: {time.time() - t0:.0f} s", flush=True)
        for name in KEEP:
            dst = os.path.join(GOLDEN, folder, os.path.basename(name))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(out, name), dst)


if __name__ == "__main__":
    main()
