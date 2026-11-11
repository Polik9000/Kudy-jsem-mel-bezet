"""The help page "Jak na to": how to get the files the app needs (Livelox, Garmin) and what the notes of a leg
do. Open without logging in, so that it can be read before making an account."""
import sys

from flask import render_template

from .. import cfg
from . import bp


@bp.route("/jak-na-to")
def help_page():
    # the app on one's own computer knows the system; a server lets the browser decide (script in the page)
    default_os = ("mac" if sys.platform == "darwin" else "win") if cfg().local else None
    return render_template("ob/help.html", default_os=default_os)


@bp.route("/o-aplikaci")
def about_page():
    """What the app does, how it computes and what it cannot do (the limits are written down on purpose)."""
    return render_template("ob/about.html")
