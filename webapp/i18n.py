"""Interface language: Czech (the default, and the language the source is written in) or English.

The Czech text is the message id: `_("Czech sentence %(n)d", n=3)` in Python, `_("...")` and
`{% trans %}...{% endtrans %}` in templates, `t("...")` in the scripts. For English the id is looked up in
webapp/lang_en.py; a text without an entry stays Czech (tests/test_i18n.py checks that none is missing).

Which language a page uses: ?lang=en|cs (also remembered in the cookie `ob_lang`, see ob.set_language),
else the cookie, else OB_LANG (default cs). Background jobs run in the language of the page that started them
(jobs.lang), so the sentences the worker stores for the job list come out in the reader's language.
"""
import contextlib
import contextvars
import os
import re

from flask import has_request_context, request

LANGS = {"cs": "Čeština", "en": "English"}
DEFAULT = os.environ.get("OB_LANG", "cs") if os.environ.get("OB_LANG", "cs") in LANGS else "cs"
COOKIE = "ob_lang"

_forced = contextvars.ContextVar("ob_lang", default=None)
_catalog = {}


def _load():
    if not _catalog:
        from . import lang_en
        _catalog["en"] = lang_en.EN
        _catalog["en-js"] = lang_en.EN_JS
    return _catalog


def lang():
    """The language of this request (or of the job the worker runs)."""
    forced = _forced.get()
    if forced:
        return forced
    if has_request_context():
        for pick in (request.args.get("lang"), request.cookies.get(COOKIE)):
            if pick in LANGS:
                return pick
    return DEFAULT


@contextlib.contextmanager
def use(code):
    """Run a piece of code (a job of the worker) in the given language."""
    token = _forced.set(code if code in LANGS else DEFAULT)
    try:
        yield
    finally:
        _forced.reset(token)


def gettext(msgid):
    """The text in the current language, with `%(name)s` places still unfilled."""
    if lang() == "en":
        return _load()["en"].get(msgid, msgid)
    return msgid


def _(msgid, **kw):
    """Translate and fill `%(name)s` places: _("%(n)d legs", n=3)."""
    text = gettext(msgid)
    return text % kw if kw else text


def _n(n, one, few, many, **kw):
    """The message for the count n: one / few / many in Czech (1 | 2-4 | 5 and more), one / many in English.
    The count is available to the message as %(n)s."""
    if lang() == "cs":
        msg = one if n == 1 else few if 2 <= n <= 4 else many
    else:
        msg = one if n == 1 else many
    return _(msg, n=n, **kw)


def js_catalog():
    """What the scripts need in this language ({} for Czech: the scripts' own texts are Czech)."""
    return dict(_load()["en-js"]) if lang() == "en" else {}


def num(x, digits=1):
    """A decimal number in the decimal sign of the language: 2,7 (Czech) or 2.7 (English)."""
    s = f"{x:.{digits}f}"
    return s.replace(".", ",") if lang() == "cs" else s


MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def date_text(d):
    """A date as the language writes it: '3. 10. 2026' or '3 Oct 2026'."""
    if lang() == "en":
        return f"{d.day} {MONTHS_EN[d.month - 1]} {d.year}"
    return f"{d.day}. {d.month}. {d.year}"


def plural(n, one, few, many):
    """Czech forms for 1, 2-4 and 5+ ('1 kolečko', '3 kolečka', '7 koleček'); English uses `one` and `many`."""
    if lang() != "cs":
        return one if n == 1 else many
    return one if n == 1 else few if 2 <= n <= 4 else many


def normalize(msgid):
    """The id of a `{% trans %}` block as the template engine passes it (whitespace collapsed)."""
    return re.sub(r"\s+", " ", msgid).strip()


def init_app(app):
    """Templates: {% trans %}, _() and the language in every page."""
    app.jinja_env.add_extension("jinja2.ext.i18n")
    app.jinja_env.policies["ext.i18n.trimmed"] = True
    app.jinja_env.install_gettext_callables(gettext, lambda s, p, n: gettext(s if n == 1 else p), newstyle=True)

    @app.context_processor
    def _lang():
        return dict(lang=lang(), languages=LANGS, js_i18n=js_catalog(), plural=plural, num=num)


def N_(msgid):
    """Marks a text for translation where it is written at module level (the language is not known yet); the code that
    uses it calls _() on it."""
    return msgid
