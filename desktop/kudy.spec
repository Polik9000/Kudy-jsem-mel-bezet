# PyInstaller: the app on one's own computer as a folder (Windows: then Inno Setup, desktop/kudy.iss) or as an
# .app (macOS: then a .dmg). Build from the repo root:  pyinstaller --noconfirm desktop/kudy.spec
# The package holds the code and its own files only: no maps, no runs, no races (data/ and tests/ stay out).
import os
import sys

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
sys.path.insert(0, ROOT)   # so collect_submodules finds webapp and oroute

from PyInstaller.utils.hooks import collect_data_files, collect_submodules  # noqa: E402
ICONS = os.path.join(ROOT, "build", "icons")   # made by desktop/icons.py before the build
APP = "KudyJsemMelBezet"
NAME = "Kudy jsem měl běžet"
VERSION = os.environ.get("APP_VERSION", "0.0.0")

datas = [
    (os.path.join(ROOT, "analyze.py"), "."),
    (os.path.join(ROOT, "bestroute.py"), "."),
    (os.path.join(ROOT, "LICENSE"), "."),
    (os.path.join(ROOT, "docs", "THIRD_PARTY_NOTICES.md"), "."),
]
# webapp: the pages, styles, scripts and the database schema; oroute: the default speed model and slope shape.
# Their .py go along as files too: the analysis reads its own source (runner.SAMPLE_CODE) and Flask finds the
# templates and static files next to webapp/views/ (that folder has to exist on disk).
for package in ("webapp", "oroute"):
    for folder, dirs, files in os.walk(os.path.join(ROOT, package)):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".pyc"):
                datas.append((os.path.join(folder, f), os.path.relpath(folder, ROOT)))
datas += collect_data_files("certifi")

hidden = (collect_submodules("webapp") + collect_submodules("oroute")
          + ["analyze", "bestroute", "waitress", "scipy.ndimage", "scipy.sparse.csgraph", "scipy.optimize"])
# pywebview picks its platform code at run time, so the analysis of imports does not see it
if sys.platform == "darwin":
    hidden += ["webview.platforms.cocoa"]
elif sys.platform == "win32":
    hidden += ["webview.platforms.edgechromium", "webview.platforms.winforms", "clr"]

a = Analysis(
    [os.path.join(ROOT, "desktop", "app.py")],
    pathex=[ROOT],
    datas=datas,
    hiddenimports=hidden,
    excludes=["pytest", "ruff", "gunicorn", "tkinter", "matplotlib", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)
icon = os.path.join(ICONS, "app.icns" if sys.platform == "darwin" else "app.ico")
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=APP,
    console=os.environ.get("APP_CONSOLE") == "1",   # 1: a console window with the log (for looking into a problem)
    icon=icon if os.path.exists(icon) else None,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name=APP, upx=False)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{NAME}.app",
        icon=icon if os.path.exists(icon) else None,
        bundle_identifier="cz.tobiasotta.kudyjsemmelbezet",
        version=VERSION,
        info_plist={
            "CFBundleDisplayName": NAME,
            "CFBundleShortVersionString": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "NSHumanReadableCopyright": "Copyright 2026 Tobiáš Otta, PolyForm Noncommercial 1.0.0",
        },
    )
