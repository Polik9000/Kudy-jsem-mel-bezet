"""Text colours of the app keep 4.5 : 1 against their backgrounds in both modes (tools/kontrast.py, docs/vzhled.md)."""
import importlib.util
import os

HERE = os.path.dirname(__file__)


def test_text_contrast_is_at_least_4_5():
    spec = importlib.util.spec_from_file_location("kontrast", os.path.join(HERE, "..", "tools", "kontrast.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    text, worst = mod.table()
    assert worst >= 4.5, text
