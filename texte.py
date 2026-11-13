"""Sprache: Deutsch bei deutschem Windows, sonst Englisch.
Erzwingen mit der Umgebungsvariable NOPOP_LANG=de oder NOPOP_LANG=en."""
import ctypes
import os

_wahl = os.environ.get("NOPOP_LANG", "").lower()
DEUTSCH = _wahl == "de" if _wahl in ("de", "en") else \
    (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x07


def t(de, en):
    return de if DEUTSCH else en
