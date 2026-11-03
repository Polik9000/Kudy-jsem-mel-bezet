"""The app on one's own computer: one window, no login, no Docker.

    python -m desktop.app               the window (pywebview); without it the default browser
    python -m desktop.app --browser     always the default browser
    python -m desktop.app --smoke-test  start, answer a few pages, run the analysis scripts with --help, exit

The same Flask app as on the club server (webapp/), with OB_LOCAL=1: one runner, no accounts, no club site. The
database and everything uploaded are in the user's own data folder (data_dir below), never next to the program,
so an update or an uninstall keeps them. The jobs (analysis, ORIS, model) run in a thread of this process instead
of the separate worker of Docker.

Packaged (PyInstaller, desktop/kudy.spec) sys.executable is the app itself. The web layer starts the analysis
scripts as `[sys.executable, "-u", "analyze.py", ...]` or `[sys.executable, "-m", "oroute.x", ...]`
(webapp/services/runner.py), so the app, started like that, behaves like python: see as_python().
"""
import multiprocessing
import os
import runpy
import socket
import sys
import threading
import time

APP_NAME = "Kudy jsem měl běžet"
APP_FOLDER = "KudyJsemMelBezet"   # the data folder: no diacritics, some tools still trip over them


def data_dir():
    """Where the database and the uploaded maps and runs live (OB_INSTANCE wins)."""
    if os.environ.get("OB_INSTANCE"):
        return os.environ["OB_INSTANCE"]
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, APP_FOLDER)


def _fix_streams(unbuffered):
    """A windowed app may have no stdout; the scripts print Czech, the web layer reads UTF-8 (runner.py)."""
    for name, fd in (("stdout", 1), ("stderr", 2)):
        stream = getattr(sys, name)
        if stream is None:
            try:
                stream = open(fd, "w", encoding="utf-8", errors="replace", closefd=False)
            except OSError:
                stream = open(os.devnull, "w", encoding="utf-8")
            setattr(sys, name, stream)
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=unbuffered or name == "stderr")
        except (AttributeError, ValueError):
            pass


def as_python(argv):
    """Run `[-u] script.py args` or `[-u] -m module args` the way python would. False: not such a command line."""
    args = list(argv)
    unbuffered = False
    while args and args[0] in ("-u", "-B", "-I"):
        unbuffered |= args.pop(0) == "-u"
    if len(args) >= 2 and args[0] == "-m":
        module, rest = args[1], args[2:]
    elif args and args[0].endswith(".py"):
        # analyze.py, bestroute.py of the repo root: packaged as modules (hiddenimports in kudy.spec)
        module, rest = os.path.splitext(os.path.basename(args[0]))[0], args[1:]
    else:
        return False
    _fix_streams(unbuffered)
    sys.argv = [module, *rest]
    code = 0
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        if not isinstance(e.code, (int, type(None))):
            print(e.code, file=sys.stderr)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)  # also ends the threads a script may have left behind


def _certificates():
    """Python packaged for macOS does not read the system's certificates: without certifi every https call (ORIS,
    ČÚZK, OpenStreetMap) would fail. Set in the environment, so the analysis scripts get it too."""
    if os.environ.get("SSL_CERT_FILE"):
        return
    try:
        import certifi
    except ImportError:
        return
    if os.path.exists(certifi.where()):
        os.environ["SSL_CERT_FILE"] = certifi.where()


def _environment(instance):
    _certificates()
    os.environ["OB_LOCAL"] = "1"
    os.environ["OB_INSTANCE"] = instance
    os.environ.setdefault("OB_URL_PREFIX", "")
    os.environ.setdefault("OB_CLUB_URL", "")           # no club site: no links to it
    os.environ.setdefault("OB_CLUB_NAME", APP_NAME)
    os.environ.setdefault("OB_CLUB_LOGO", "ob-logo.svg")
    os.environ.setdefault("OB_REGISTRATION", "0")


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Jobs(threading.Thread):
    """The worker of Docker (webapp/worker.py) as a thread: one job at a time, in the order they came."""

    def __init__(self, conf):
        super().__init__(daemon=True, name="jobs")
        self.conf = conf

    def run(self):
        from webapp import db as dbm
        from webapp import worker
        from webapp.services import jobs
        worker.load_handlers()
        con = dbm.connect(self.conf.db_path)
        jobs.requeue_interrupted(con)   # the app was closed in the middle of a job: it runs again
        con.close()
        while True:
            try:
                if not worker.run_once(self.conf):
                    time.sleep(1.5)
            except Exception as e:  # noqa: BLE001  (the database was busy, say; the next round tries again)
                print(f"jobs: {e}", file=sys.stderr, flush=True)
                time.sleep(5)


def start(port=None):
    """Start the pages (waitress on 127.0.0.1 only) and the jobs. Returns (url, server)."""
    from waitress import create_server

    from webapp import create_app
    app = create_app()
    server = create_server(app, host="127.0.0.1", port=port or _free_port(), threads=6,
                           max_request_body_size=app.config["MAX_CONTENT_LENGTH"], channel_timeout=600)
    threading.Thread(target=server.run, daemon=True, name="web").start()
    Jobs(app.config["OB"]).start()
    return f"http://127.0.0.1:{server.effective_port}/", server, app


def _wait_until_up(url, seconds=30):
    import urllib.request
    end = time.time() + seconds
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def smoke_test():
    """What the GitHub Actions build checks on Windows and macOS: the pages answer and every analysis script starts
    (that is, numpy, scipy, Pillow and fitdecode are in the package). No maps, no runs."""
    import subprocess
    import tempfile
    import urllib.request
    _fix_streams(True)
    os.environ["OB_INSTANCE"] = tempfile.mkdtemp(prefix="kudy-smoke-")
    _environment(os.environ["OB_INSTANCE"])
    url, server, _ = start()
    ok = _wait_until_up(url)
    failed = [] if ok else ["the pages do not answer"]
    for path in ("", "profile", "upload", "model", "jak-na-to", "ob-static/ob.css",
                 "ob-static/vendor/leaflet/leaflet.js", "ob-static/ob-logo.svg"):
        try:
            with urllib.request.urlopen(url + path, timeout=30) as r:
                body = r.read()
                print(f"GET /{path}: {r.status}, {len(body)} B", flush=True)
        except Exception as e:  # noqa: BLE001
            failed.append(f"/{path}: {e}")
    from webapp.config import ROOT
    for cmd in (["-u", "analyze.py", "--help"], ["-u", "bestroute.py", "--help"], ["-m", "oroute.slopefit", "--help"],
                ["-u", "-m", "oroute.planned", "--help"], ["-u", "-m", "oroute.lost", "--help"],
                ["-u", "-m", "oroute.relocate", "--help"]):
        # packaged: the app itself runs them (as_python); from the source: python
        p = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
        print(f"{' '.join(cmd)}: exit {p.returncode}", flush=True)
        if p.returncode != 0:
            failed.append(f"{' '.join(cmd)}: {(p.stdout + p.stderr)[-1500:]}")
    import numpy  # noqa: F401
    import PIL.Image  # noqa: F401
    import scipy.ndimage  # noqa: F401
    server.close()
    if failed:
        print("SMOKE TEST FAILED:\n" + "\n".join(failed), flush=True)
        return 1
    print("smoke test ok", flush=True)
    return 0


def _show_error(text):
    """Without a window there is no other place to say it: a dialog where one exists, otherwise stderr."""
    print(text, file=sys.stderr, flush=True)
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, 0x10)
    except Exception:  # noqa: BLE001
        pass


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--smoke-test" in argv:
        return smoke_test()
    instance = data_dir()
    os.makedirs(instance, exist_ok=True)
    _environment(instance)
    _fix_streams(False)
    try:
        url, server, app = start()
    except Exception as e:  # noqa: BLE001
        _show_error(f"Aplikace se nespustila: {e}\nData: {instance}")
        return 1
    _wait_until_up(url)
    done = threading.Event()
    window = None

    def quit_app():
        # a moment later, so the page "Aplikace je ukončená" still gets to the browser
        threading.Timer(1.0, window.destroy if window is not None else done.set).start()
    app.config["OB_QUIT"] = quit_app

    if "--browser" not in argv:
        try:
            import webview
            webview.settings["ALLOW_DOWNLOADS"] = True
            webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
            window = webview.create_window(APP_NAME, url, width=1360, height=900, min_size=(960, 600),
                                           background_color="#10251E",  # the colour of the app, no white flash
                                           text_select=True)
            webview.start(private_mode=False, storage_path=os.path.join(instance, "okno"))
            server.close()
            os._exit(0)  # the window is closed: so is the app (a job half done runs again next time)
        except Exception as e:  # noqa: BLE001  (no WebView2 on an old Windows, say): the browser instead
            print(f"no window ({e}), opening the browser", file=sys.stderr, flush=True)
            window = None
    import webbrowser
    webbrowser.open(url)
    print(f"{APP_NAME} běží na {url} (ukončení: v nabídce Ukončit aplikaci, nebo Ctrl+C)", flush=True)
    try:
        while not done.wait(1):
            pass
    except KeyboardInterrupt:
        pass
    server.close()
    os._exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()   # oroute.slopefit uses a process pool: its children start as this app
    if getattr(sys, "frozen", False):
        as_python(sys.argv[1:])        # returns only when the command line is not a script to run
    sys.exit(main())
