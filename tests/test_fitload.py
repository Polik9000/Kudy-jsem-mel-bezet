"""Reading a recording, and the three inputs analyze.py cannot analyse: it says which one in a line the web
app turns into a Czech sentence, never with a traceback."""
import io
import math
import os
import subprocess
import sys
import zipfile

import pytest
from fitfile import fit_bytes, write_fit
from PIL import Image, ImageDraw
from races import ROOT

from oroute import errors, garmin
from oroute.errors import InputError
from oroute.fitload import load_track
from webapp import texts
from webapp.services import runner

PURPLE = (180, 70, 245)
LAT, LON, MPP = 50.0, 18.0, 1.33
KY = 6371008.8 * math.pi / 180
KX = KY * math.cos(math.radians(LAT))


def test_track_is_read_and_a_recording_without_positions_says_so(tmp_path):
    tr = load_track(write_fit(tmp_path / "a.fit", [(t, 50.0 + t * 1e-5, 18.0) for t in range(0, 60, 2)]))
    assert len(tr["t"]) == 30 and tr["t"][-1] == 58 and abs(tr["lat"][-1] - 50.00058) < 1e-6
    with pytest.raises(InputError) as e:
        load_track(write_fit(tmp_path / "b.fit", [(t, None, None) for t in range(0, 60, 2)]))
    assert e.value.code == "no_gps"
    (tmp_path / "c.fit").write_bytes(b"this is no .fit file at all, only some text of the same kind of length")
    with pytest.raises(InputError) as e:
        load_track(str(tmp_path / "c.fit"))
    assert e.value.code == "bad_fit"
    assert "first_gps" not in garmin.scan_fit(fit_bytes([(0, None, None), (5, None, None)]))


def kmz(path, image, header=0):
    """A KMZ like the Livelox export from a picture: MPP metres per pixel, centred on LAT, LON."""
    w, h = image.size
    buf = io.BytesIO()
    image.save(buf, "PNG")
    box = (LAT + h * MPP / 2 / KY, LAT - h * MPP / 2 / KY, LON + w * MPP / 2 / KX, LON - w * MPP / 2 / KX)
    kml = (f"<kml><!-- ob-header-px: {header} --><GroundOverlay><Icon><href>map.png</href></Icon><LatLonBox>"
           f"<north>{box[0]:.9f}</north><south>{box[1]:.9f}</south><east>{box[2]:.9f}</east><west>{box[3]:.9f}</west>"
           "</LatLonBox></GroundOverlay></kml>")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("doc.kml", kml)
        z.writestr("map.png", buf.getvalue())
    return str(path)


COURSE = [(120, 500), (300, 420), (480, 500), (620, 330), (450, 180), (250, 200), (120, 120)]   # S, 1-5, F in pixels


def course_map(path, pts=COURSE, r=28):
    """A white map with a course: start triangle, control circles joined by lines, double circle at the finish."""
    im = Image.new("RGB", (760, 620), (255, 255, 255))
    d = ImageDraw.Draw(im)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / n, (by - ay) / n
        d.line([ax + ux * (r + 6), ay + uy * (r + 6), bx - ux * (r + 6), by - uy * (r + 6)], fill=PURPLE, width=3)
    sx, sy = pts[0]
    d.polygon([(sx + 1.25 * r * math.sin(a), sy - 1.25 * r * math.cos(a)) for a in (0, 2.0944, 4.1888)],
              outline=PURPLE, width=3)
    for x, y in pts[1:-1]:
        d.ellipse([x - r, y - r, x + r, y + r], outline=PURPLE, width=3)
    fx, fy = pts[-1]
    for q in (r + 2, r - 5):        # the rings of the finish as Livelox draws them: 7 pixels apart
        d.ellipse([fx - q, fy - q, fx + q, fy + q], outline=PURPLE, width=3)
    return kmz(path, im)


def run_along(pts, speed=3.0, size=(760, 620)):
    """[(t, lat, lon)] of a run through the pixel points at `speed` m/s, a sample every 2 s."""
    out, t = [], 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) * MPP / speed / 2))
        for i in range(n):
            x, y = ax + (bx - ax) * i / n, ay + (by - ay) * i / n
            out.append((t, LAT - (y - size[1] / 2) * MPP / KY, LON + (x - size[0] / 2) * MPP / KX))
            t += 2.0
    return out


def analyze(*args):
    p = subprocess.run([sys.executable, os.path.join(ROOT, "analyze.py"), *args, "--no-images"], capture_output=True,
                       text=True, cwd=ROOT)
    return p.returncode, (p.stdout + p.stderr).splitlines()


def test_a_run_of_the_course_is_analysed_and_three_bad_inputs_end_in_one_line(tmp_path):
    course = course_map(tmp_path / "course.kmz")
    good = write_fit(tmp_path / "run.fit", run_along(COURSE))
    code, lines = analyze(course, good, str(tmp_path / "out"))
    assert code == 0, lines
    with open(tmp_path / "out" / "legs.csv") as f:
        assert len(f.read().splitlines()) == 7 and "nan" not in f.read().lower()

    # 1. a recording that is no run of this course (another activity: it stays in one corner of the map)
    other = write_fit(tmp_path / "other.fit", run_along([(700, 560), (740, 600), (700, 600), (700, 560)] * 4))
    code, lines = analyze(course, other, str(tmp_path / "out1"))
    assert code == 2 and errors.parse(lines)[0] == "track_off_course" and not any("Traceback" in l for l in lines)
    # ... and one that ends two controls early: analysed, the legs it does not show marked, no NaN anywhere
    short = write_fit(tmp_path / "short.fit", run_along(COURSE[:5]))
    code, lines = analyze(course, short, str(tmp_path / "out1b"))
    assert code == 0, lines
    with open(tmp_path / "out1b" / "legs.csv") as f:
        rows = f.read().splitlines()
    assert sum("no GPS data on this leg" in r for r in rows) == 2 and not any("nan" in r.lower() for r in rows)

    # 2. the map "with the course" has no course printed on it
    blank = kmz(tmp_path / "blank.kmz", Image.new("RGB", (760, 620), (255, 255, 255)))
    code, lines = analyze(blank, good, str(tmp_path / "out2"))
    assert code == 2 and errors.parse(lines)[0] == "no_course_print" and not any("Traceback" in l for l in lines)

    # 3. the recording has no GPS position
    blind = write_fit(tmp_path / "blind.fit", [(t, None, None) for t in range(0, 600, 2)])
    code, lines = analyze(course, blind, str(tmp_path / "out3"))
    assert code == 2 and errors.parse(lines)[0] == "no_gps" and not any("Traceback" in l for l in lines)


def test_web_job_says_in_czech_what_is_wrong_and_keeps_the_details():
    for code in errors.CODES:
        assert texts.analysis_error(code) != "Analýza selhala." and "Traceback" not in texts.analysis_error(code)
    said = texts.analysis_error("track_off_course", "the track does not follow the course: at its closest it is 212 m "
                                "from the controls (median) and 9 of 12 legs are not on it; the recording does not "
                                "cover the official race time (start -480 s from the start of the recording, finish "
                                "+35 s from its end)")
    assert "212 m" in said and "začíná 8:00 po startu" in said and "končí 0:35 před cílem" in said
    with pytest.raises(runner.AnalysisError) as e:
        runner._run("-c", "print('reading'); print('OB-ERROR no_gps: the recording has no GPS track'); raise SystemExit(2)")
    first, _, rest = str(e.value).partition("\n")
    assert first == texts.ANALYSIS_ERRORS["no_gps"] and "OB-ERROR no_gps" in rest
    with pytest.raises(runner.AnalysisError) as e:
        runner._run("-c", "raise ValueError('a bug')")
    first, _, rest = str(e.value).partition("\n")
    assert first.startswith("Výpočet selhal") and "ValueError: a bug" in rest


def test_failed_job_shows_the_sentence_and_hides_the_printout(app, client, user):
    from webapp import db as dbm
    from webapp.services import jobs
    from webapp.worker import load_handlers, run_once
    con = dbm.connect(app.config["OB"].db_path)

    @jobs.handler("test_bad_input")
    def bad_input(ctx, job):
        raise runner.AnalysisError(texts.analysis_error("no_gps") + "\n\nreading\nOB-ERROR no_gps: no GPS track")
    jobs.enqueue(con, "test_bad_input", user_id=user)
    load_handlers()
    run_once(app.config["OB"])
    error = con.execute("SELECT error FROM jobs WHERE kind = 'test_bad_input'").fetchone()["error"]
    assert error.splitlines()[0] == texts.ANALYSIS_ERRORS["no_gps"] and "Traceback" in error
    page = client.get("/jobs").get_data(as_text=True)
    shown, _, hidden = page.partition("<details><summary>Podrobnosti</summary>")
    assert "V záznamu není GPS stopa" in shown and "Traceback" not in shown and "OB-ERROR no_gps" in hidden
    del jobs.HANDLERS["test_bad_input"]
