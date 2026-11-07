"""Czech letters must survive on Windows, where open() without encoding writes cp1252 (no Č): every text file the
analysis writes or reads names its encoding, and the packaged app runs Python in UTF-8 mode."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CODE = ["analyze.py", "bestroute.py", "oroute", "webapp", "desktop"]
OPEN = re.compile(r"(?<![\w.])open\(([^()]|\([^()]*\))*\)")
BINARY = re.compile(r"""["'][rwax]\+?b["']""")


def sources():
    for name in CODE:
        p = ROOT / name
        yield from ([p] if p.is_file() else sorted(p.rglob("*.py")))


def test_text_files_name_their_encoding():
    bad = []
    for path in sources():
        text = path.read_text(encoding="utf-8")
        for m in OPEN.finditer(text):
            call = m.group(0)
            if "encoding" in call or BINARY.search(call) or "mode=" in call and "b" in call:
                continue
            bad.append(f"{path.relative_to(ROOT)}: {call[:60]}")
        for m in re.finditer(r"\.(read_text|write_text)\(([^()]|\([^()]*\))*\)", text):
            if "encoding" not in m.group(0):
                bad.append(f"{path.relative_to(ROOT)}: {m.group(0)[:60]}")
    assert not bad, "text file without encoding:\n" + "\n".join(bad)


def test_packaged_app_runs_in_utf8_mode():
    assert '"X utf8"' in (ROOT / "desktop" / "kudy.spec").read_text(encoding="utf-8")
    assert 'PYTHONUTF8' in (ROOT / "desktop" / "app.py").read_text(encoding="utf-8")
