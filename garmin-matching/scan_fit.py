"""Scan a folder of Garmin .fit files; print one JSON line per activity file
(start UTC, sport, duration, distance, start lat/lon, device). Non-activity files
(monitoring, sleep, settings...) are counted by file type."""
import sys, os, json, collections
from concurrent.futures import ProcessPoolExecutor
import fitdecode

SEMI = 180.0 / 2**31

def scan(path):
    info = {"file": os.path.basename(path)}
    try:
        with fitdecode.FitReader(path, check_crc=fitdecode.CrcCheck.DISABLED) as f:
            for fr in f:
                if not isinstance(fr, fitdecode.FitDataMessage):
                    continue
                if fr.name == "file_id":
                    info["type"] = str(fr.get_value("type", fallback=None))
                    info["product"] = str(fr.get_value("garmin_product", fallback=fr.get_value("product", fallback="")))
                    if info["type"] != "activity":
                        return info
                elif fr.name == "session":
                    v = {fd.name: fd.value for fd in fr.fields}
                    info.update(
                        start=v.get("start_time").isoformat() if v.get("start_time") else None,
                        sport=str(v.get("sport")), sub_sport=str(v.get("sub_sport")),
                        elapsed=v.get("total_elapsed_time"), timer=v.get("total_timer_time"),
                        dist=v.get("total_distance"), ascent=v.get("total_ascent"),
                        lat=v["start_position_lat"] * SEMI if v.get("start_position_lat") is not None else None,
                        lon=v["start_position_long"] * SEMI if v.get("start_position_long") is not None else None)
                elif fr.name == "record" and "first_gps" not in info and fr.get_value("position_lat", fallback=None) is not None:
                    info["first_gps"] = [fr.get_value("position_lat") * SEMI, fr.get_value("position_long") * SEMI]
    except Exception as e:
        info["error"] = repr(e)[:120]
    return info

if __name__ == "__main__":
    d = sys.argv[1]
    files = [os.path.join(d, x) for x in os.listdir(d) if x.endswith(".fit")]
    types = collections.Counter()
    with ProcessPoolExecutor() as ex:
        for info in ex.map(scan, files, chunksize=50):
            types[info.get("type", "error" if "error" in info else "?")] += 1
            if info.get("type") == "activity":
                print(json.dumps(info))
    print(json.dumps(dict(types)), file=sys.stderr)
