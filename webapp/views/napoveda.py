"""The help page "Jak na to": how to get the files the app needs (Livelox, Garmin) and what the notes of a leg
do. Open without logging in, so that it can be read before making an account."""
from flask import render_template

from . import bp


@bp.route("/jak-na-to")
def help_page():
    return render_template("ob/help.html")
