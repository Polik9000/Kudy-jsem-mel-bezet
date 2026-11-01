#!/usr/bin/env python3
"""Where the analysis of a race spends time and memory (TODO 39): wall time and peak memory of each step as the web
app runs it, and the most expensive functions of each.

    python tools/profil.py pohora petrvald azymut-e5 [--out DIR] [--top 10]

Races are folders of data/ (course.kmz, maponly.kmz, run.fit); elevation comes from tests/golden, so no network is
needed. Steps: analyze.py (course from the map, track, mistakes), bestroute.py --samples-only (the terrain read
from the map and what the model learns), bestroute.py (the routes, with two alternatives and the average runner),
oroute.relocate (catching features, "Ztratil jsem se"). Each runs in its own process, so the peak memory of one
step is not the peak of an earlier one. Prints a Markdown table; --out keeps the cProfile files.
"""
import argparse
import os
import pstats
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from tests.races import GOLDEN, inputs  # noqa: E402

# runs `python -m cProfile -o FILE script args`, then reports the peak memory of that child (a fresh process each time)
WRAP = ("import resource, subprocess, sys; r = subprocess.run([sys.executable, '-m', 'cProfile', '-o', sys.argv[1], "
        "*sys.argv[2:]], capture_output=True, text=True); "
        "print(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, r.returncode); sys.stderr.write(r.stderr[-2000:])")


def step(name, out_dir, *cmd):
    """Run one step; returns dict(name, seconds, peak_mb, prof)."""
    prof = os.path.join(out_dir, name.replace(" ", "_") + ".prof")
    t = time.time()
    r = subprocess.run([sys.executable, "-c", WRAP, prof, *cmd], capture_output=True, text=True, cwd=HERE)
    seconds = time.time() - t
    peak, code = r.stdout.split()[-2:]
    if int(code):
        raise SystemExit(f"{name} failed:\n{r.stderr}")
    # ru_maxrss is KiB on Linux and bytes on macOS
    mb = int(peak) / (1024 if sys.platform != "darwin" else 1024 * 1024)
    return dict(name=name, seconds=seconds, peak_mb=mb, prof=prof)


def race(folder, work):
    course, maponly, fit = inputs(folder)
    out = os.path.join(work, folder)
    best = os.path.join(out, "best")
    os.makedirs(best)
    shutil.copyfile(os.path.join(GOLDEN, folder, "dem_cache.npz"), os.path.join(best, "dem_cache.npz"))
    cache = os.path.join(work, folder + "_terrain")
    steps = [step("analyze", out, "analyze.py", course, fit, out, "--no-images")]
    common = ["bestroute.py", maponly, os.path.join(out, "course.json"), fit, best, "--title", folder,
              "--dem", "aws", "--no-images", "--terrain-cache", cache]
    steps.append(step("terrain+samples", out, *common, "--samples-only"))
    steps.append(step("routes", out, *common, "--alternatives", "2", "--generic", "terrain"))
    steps.append(step("relocate", out, "-m", "oroute.relocate", maponly, out, os.path.join(out, "relocate.json"),
                      "--dem", "aws", "--terrain-cache", cache))
    return steps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("races", nargs="+")
    ap.add_argument("--out", help="keep the cProfile files here")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    work = os.path.abspath(a.out) if a.out else tempfile.mkdtemp(prefix="profil-")
    os.makedirs(work, exist_ok=True)
    print(f"cores: {os.cpu_count()}, python {sys.version.split()[0]}\n")
    for folder in a.races:
        steps = race(folder, work)
        print(f"### {folder}\n\n| krok | čas | špička paměti |\n|---|---|---|")
        for s in steps:
            print(f"| {s['name']} | {s['seconds']:.0f} s | {s['peak_mb']:.0f} MB |")
        print(f"| **celkem** | {sum(s['seconds'] for s in steps):.0f} s | {max(s['peak_mb'] for s in steps):.0f} MB |\n")
        for s in steps:
            print(f"Nejdražší funkce, {s['name']} (kumulativní čas):\n\n```")
            st = pstats.Stats(s["prof"], stream=sys.stdout)
            st.sort_stats("cumulative").print_stats(a.top)
            print("```\n")
    if not a.out:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
