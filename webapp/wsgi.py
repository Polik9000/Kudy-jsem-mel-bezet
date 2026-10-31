"""WSGI entry point (gunicorn webapp.wsgi:app). The app is served under OB_URL_PREFIX (default /ob), so it can
sit behind the same domain as the club site: the proxy there only forwards /ob/... to this process."""
import os

from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import redirect

from . import create_app

app = create_app()
_prefix = app.config["OB"].url_prefix
if _prefix:
    def _to_prefix(environ, start_response):
        return redirect(_prefix + "/")(environ, start_response)

    app.wsgi_app = DispatcherMiddleware(_to_prefix, {_prefix: app.wsgi_app})
    app.config["SESSION_COOKIE_PATH"] = _prefix
if os.environ.get("OB_PROXY") == "1":
    # behind the club site's proxy: trust its X-Forwarded-For/Proto/Host (exactly one proxy)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    # the club site is served over https only, so the login cookie never travels in the clear
    app.config["SESSION_COOKIE_SECURE"] = True
