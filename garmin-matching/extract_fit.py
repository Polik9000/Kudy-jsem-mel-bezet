"""Pull activity .fit files out of a Garmin GDPR export zip (the .fit files sit in a zip inside the zip).

usage: python3 extract_fit.py EXPORT.zip OUT_DIR NAME [NAME ...]
NAME = file name from matches.csv (column fit_file), or just its number, e.g. 421896337251."""
import io
import os
import sys
import zipfile

INNER = "DI_CONNECT/DI-Connect-Uploaded-Files/"


def main():
    export, out, names = sys.argv[1], sys.argv[2], sys.argv[3:]
    os.makedirs(out, exist_ok=True)
    left = set(names)
    with zipfile.ZipFile(export) as z:
        for inner in [n for n in z.namelist() if n.startswith(INNER) and n.endswith(".zip")]:
            with zipfile.ZipFile(io.BytesIO(z.read(inner))) as zz:
                for n in zz.namelist():
                    hit = next((k for k in left if os.path.basename(n) == k or n.endswith(f"_{k}.fit")), None)
                    if hit:
                        dst = os.path.join(out, os.path.basename(n))
                        with open(dst, "wb") as f:
                            f.write(zz.read(n))
                        print(dst)
                        left.discard(hit)
    if left:
        sys.exit(f"not found: {', '.join(sorted(left))}")


if __name__ == "__main__":
    main()
