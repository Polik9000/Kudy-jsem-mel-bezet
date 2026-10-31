"""Match races from my_runs.html to Garmin activities.

usage: python3 match.py races.json activities.jsonl summarizedActivities.json OUT_DIR
races.json from parse_runs.py, activities.jsonl from scan_fit.py.
Rule: activities on the race's local date (Europe/Prague); prefer running, then the one
whose moving time is closest to the official race time. Confidence:
  high   = one plausible run, its duration within -2/+25 min of the race time
  medium = plausible, but several candidates or duration off
  low    = only a non-running or very different activity that day
  none   = no activity that day (or before the export starts)."""
import sys, json, csv, datetime as dt
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Prague")
RUN = {"running"}

races = json.load(open(sys.argv[1]))
acts = [json.loads(l) for l in open(sys.argv[2])]
summ = json.load(open(sys.argv[3]))[0]["summarizedActivitiesExport"]
names = {int(s["startTimeGmt"] // 1000): s for s in summ}
for a in acts:
    t = dt.datetime.fromisoformat(a["start"])
    a["local"] = t.astimezone(TZ)
    s = names.get(int(t.timestamp())) or next((v for k, v in names.items() if abs(k - t.timestamp()) < 120), {})
    a["name"] = s.get("name", "")
    a["place"] = s.get("locationName", "")
    a["activity_id"] = s.get("activityId", "")
first = min(a["local"].date() for a in acts)

rows = []
for r in races:
    d = dt.date.fromisoformat(r["date"])
    if r["category"].endswith("souhrn"):
        continue  # multi-day total, not a race
    cands = [a for a in acts if a["local"].date() == d]
    best, conf, note = None, "none", ""
    if d < first:
        note = "before the Garmin export starts"
    elif not cands:
        note = "no activity that day"
    else:
        rt = r["time_s"] or 0
        runs = [a for a in cands if a["sport"] in RUN and a["sub_sport"] != "treadmill"]
        pool = runs or cands
        best = min(pool, key=lambda a: abs((a["timer"] or 0) - rt) if rt else 0)
        diff = ((best["timer"] or 0) - rt) / 60 if rt else None
        plaus = [a for a in runs if rt and -2 <= ((a["timer"] or 0) - rt) / 60 <= 25]
        if not runs:
            conf, note = "low", f"only {best['sport']} that day"
        elif diff is not None and -2 <= diff <= 25:
            others = [a for a in plaus if a is not best]
            clear = all(abs((a["timer"] or 0) - rt) - abs(diff * 60) > 300 for a in others)
            conf = "high" if clear else "medium"
            if others:
                note = f"{len(plaus)} runs that day, picked the one closest to the race time"
        else:
            conf = "medium" if diff is None else "low"
            note = f"activity {diff:+.0f} min vs race time" if diff is not None else f"{r['place'] or 'no official time'}, matched by date only"
        if not best.get("first_gps"):
            conf, note = "low", "activity has no GPS (watch not started properly?)"
        if len(cands) > 1 and not note:
            note = f"{len(cands)} activities that day, picked the one matching the race time"
    rows.append(dict(
        date=r["date"], race=r["name"], category=r["category"], country=r["country"],
        detail=r["detail"], race_time=str(dt.timedelta(seconds=r["time_s"])) if r["time_s"] else "",
        link=r["link"], confidence=conf, note=note,
        fit_file=best["file"] if best else "", activity_id=best["activity_id"] if best else "",
        start_local=best["local"].strftime("%H:%M") if best else "",
        act_sport=best["sport"] if best else "", act_name=best["name"] if best else "",
        act_place=best["place"] if best else "",
        act_time=str(dt.timedelta(seconds=round(best["timer"]))) if best and best["timer"] else "",
        act_km=round(best["dist"] / 1000, 2) if best and best["dist"] else "",
        has_gps="yes" if best and best.get("first_gps") else ("no" if best else ""),
        lat=round(best["first_gps"][0], 5) if best and best.get("first_gps") else "",
        lon=round(best["first_gps"][1], 5) if best and best.get("first_gps") else ""))

out = sys.argv[4]
with open(f"{out}/matches.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
json.dump(rows, open(f"{out}/matches.json", "w"), ensure_ascii=False, indent=1)
