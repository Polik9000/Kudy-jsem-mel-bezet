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


def skipped():
    """Flash the files the page left out before sending because they were larger than the server takes (static/ob.js:
    the field "vynechano", one "name|limit in bytes" per file), so the others could go."""
    from flask import flash

    from ..i18n import _
    for item in request.form.getlist("vynechano")[:50]:
        name, _sep, limit = item.rpartition("|")
        mb = int(limit) // (1024 * 1024) if limit.isdecimal() else None
        flash(_("%(filename)s je větší než %(mb)s MB, a tak se nenahrál. Ostatní soubory ano.",
                filename=name[:200] or item[:200], mb=mb) if mb else
              _("%(filename)s je větší, než server přijme, a tak se nenahrál. Ostatní soubory ano.",
                filename=name[:200] or item[:200]), "error")


# the modules attach their routes to bp
from . import coursefix, jobs, language, legs, lost, model, napoveda, photo, races, uploads  # noqa: E402,F401
