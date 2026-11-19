"""Sprache: Deutsch bei deutschem System, sonst Englisch.
Erzwingen mit der Umgebungsvariable NOPOP_LANG=de oder NOPOP_LANG=en."""
import os
import sys


def _deutsch():
    wahl = os.environ.get("NOPOP_LANG", "").lower()
    if wahl in ("de", "en"):
        return wahl == "de"
    if sys.platform == "win32":
        import ctypes
        return (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x07
    for v in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        if os.environ.get(v):
            return os.environ[v].lower().startswith("de")
    return False


DEUTSCH = _deutsch()


def t(de, en):
    return de if DEUTSCH else en
