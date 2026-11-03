"""Texts to translate and what is missing in webapp/lang_en.py.

    python tools/i18n_extract.py            list the Czech texts that have no English text yet
    python tools/i18n_extract.py --all      list every text (templates, Python, scripts)

A text is the Czech wording itself: _("..."), N_("..."), _n(n, one, few, many) in Python and in the templates
({{ _('...') }}, {% trans %}...{% endtrans %}), T("...") in webapp/static/*.js. tests/test_i18n.py runs the same
check. Add the English text to EN (pages, messages) or EN_JS (scripts) in webapp/lang_en.py."""
import ast
import glob
import os
import re
import sys

from jinja2 import Environment, nodes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBAPP = os.path.join(ROOT, "webapp")
SKIP_PY = {"texts_en.py", "lang_en.py", "i18n.py"}


def templates():
    env = Environment(extensions=["jinja2.ext.i18n"])
    env.newstyle_gettext = True      # as in the app: a literal % in a {% trans %} block is %%
    env.policies["ext.i18n.trimmed"] = True
    found = {}
    for path in sorted(glob.glob(os.path.join(WEBAPP, "templates", "**", "*.html"), recursive=True)):
        with open(path, encoding="utf-8") as f:
            tree = env.parse(f.read())
        for call in tree.find_all(nodes.Call):
            if isinstance(call.node, nodes.Name) and call.node.name in ("_", "gettext") and call.args \
                    and isinstance(call.args[0], nodes.Const) and isinstance(call.args[0].value, str):
                found.setdefault(call.args[0].value, os.path.relpath(path, ROOT))
    return found


def python():
    found = {}
    for path in sorted(glob.glob(os.path.join(WEBAPP, "**", "*.py"), recursive=True)) \
            + [os.path.join(ROOT, "desktop", "app.py")]:
        if os.path.basename(path) in SKIP_PY:
            continue
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)):
                continue
            if n.func.id in ("_", "N_"):
                picks = n.args[:1]
            elif n.func.id == "_n":
                picks = [n.args[1], n.args[2], n.args[3]] if len(n.args) >= 4 else []
            else:
                continue
            for a in picks:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    found.setdefault(a.value, os.path.relpath(path, ROOT))
    return found


def scripts():
    found = {}
    for path in sorted(glob.glob(os.path.join(WEBAPP, "static", "*.js"))):
        with open(path, encoding="utf-8") as f:
            src = f.read()
        for m in re.finditer(r'(?<![\w.])[Tt]\(\s*"((?:[^"\\]|\\.)*)"', src):
            text = m.group(1).encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8") \
                if "\\" in m.group(1) else m.group(1)
            found.setdefault(text, os.path.relpath(path, ROOT))
    return found


def catalogs():
    sys.path.insert(0, ROOT)
    from webapp import lang_en
    return lang_en.EN, lang_en.EN_JS


def collect():
    """({text: file} for pages and messages, {text: file} for the scripts)."""
    pages = dict(python())
    for k, v in templates().items():
        pages.setdefault(k, v)
    return pages, scripts()


def missing():
    pages, js = collect()
    en, en_js = catalogs()
    return ({k: v for k, v in pages.items() if k not in en},
            {k: v for k, v in js.items() if k not in en_js},
            [k for k in en if k not in pages], [k for k in en_js if k not in js])


if __name__ == "__main__":
    if "--all" in sys.argv:
        pages, js = collect()
        for kind, d in (("page", pages), ("script", js)):
            for k, v in d.items():
                print(f"{kind}\t{v}\t{k}")
    else:
        no_page, no_js, extra, extra_js = missing()
        for k, v in no_page.items():
            print(f"missing\t{v}\t{k}")
        for k, v in no_js.items():
            print(f"missing-js\t{v}\t{k}")
        for k in extra + extra_js:
            print(f"unused\t\t{k}")
        sys.exit(1 if no_page or no_js else 0)
