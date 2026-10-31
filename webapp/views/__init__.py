"""The `ob` blueprint. Templates live in templates/ob/ and static files under /ob-static,
so nothing collides when the blueprint is registered in another Flask site."""
from flask import Blueprint, jsonify, redirect, request

bp = Blueprint("ob", __name__, template_folder="../templates", static_folder="../static",
               static_url_path="/ob-static")


def go(url):
    """Send the browser to url after a form. A form sent by script (static/ob.js does it to show how much of
    a file is uploaded) cannot be redirected, so it gets the address as JSON and goes there itself."""
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(redirect=url)
    return redirect(url)


# the modules attach their routes to bp
from . import jobs, legs, lost, model, napoveda, photo, races, uploads  # noqa: E402,F401
