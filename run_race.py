#!/usr/bin/env python3
"""Whole analysis of one race in one command, no manual steps.

usage: python3 run_race.py COURSE.kmz MAPONLY.kmz RUN.fit OUT_DIR --title "Race name" [--refit other/fit_samples.npz ...]

1. analyze.py   course from the purple print, order checked against the GPS track -> OUT_DIR
2. bestroute.py fastest route per leg with the personal model                     -> OUT_DIR/best
3. with --refit: refit oroute/personal_model.json from this race plus the listed fit_samples.npz
   of earlier races, then run bestroute again so this race is drawn with the updated model.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(*cmd):
    print("$", " ".join(cmd), flush=True)
    subprocess.run([sys.executable, *cmd], check=True, cwd=HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("course_kmz")
    ap.add_argument("maponly_kmz")
    ap.add_argument("fit")
    ap.add_argument("out")
    ap.add_argument("--title", required=True)
    ap.add_argument("--refit", nargs="*", metavar="NPZ", help="fit_samples.npz of the other races to pool")
    ap.add_argument("--official", help="JSON with official start and split times (see oroute/official.py)")
    ap.add_argument("--alternatives", type=int, metavar="K", help="passed on to bestroute.py: K more routes per leg")
    ap.add_argument("--barriers", metavar="FILE", help="passed on to bestroute.py: forbidden lines and areas")
    ap.add_argument("--dem", choices=("aws", "cuzk", "auto"), help="passed on to bestroute.py: the elevation source")
    ap.add_argument("--generic", nargs="?", const="auto", choices=("auto", "all", "terrain"),
                    help="passed on to bestroute.py: the best route of an average runner next to yours")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    best = os.path.join(out, "best")
    paths = [os.path.abspath(p) for p in (a.course_kmz, a.maponly_kmz, a.fit)]
    official = ["--official", os.path.abspath(a.official)] if a.official else []
    run("analyze.py", paths[0], paths[2], out, *official)
    bestroute = ["bestroute.py", paths[1], os.path.join(out, "course.json"), paths[2], best, "--title", a.title,
                 *official]
    if a.alternatives:
        bestroute += ["--alternatives", str(a.alternatives)]
    if a.barriers:
        bestroute += ["--barriers", os.path.abspath(a.barriers)]
    if a.dem:
        bestroute += ["--dem", a.dem]
    if a.generic:
        bestroute += ["--generic", a.generic]
    run(*bestroute)
    if a.refit is not None:
        run("-m", "oroute.personal", os.path.join(HERE, "oroute", "personal_model.json"),
            os.path.join(best, "fit_samples.npz"), *[os.path.abspath(p) for p in a.refit])
        run(*bestroute)


if __name__ == "__main__":
    main()
