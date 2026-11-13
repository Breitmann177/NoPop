"""Baut das Download-Paket: dist/NoPop-<version>-windows-x64.zip

Inhalt: offizielles, signiertes Python (embeddable, python.org) + tkinter
aus der lokalen Python-Installation (gleiche Version) + NoPop.
Aufruf:  python packaging/build.py   (mit dem Python 3.12, dessen Version genutzt wird)
"""
import hashlib
import os
import shutil
import sys
import urllib.request
import zipfile

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
VERSION = open(os.path.join(WURZEL, "VERSION")).read().strip()
PY = "%d.%d.%d" % sys.version_info[:3]
EMBED = f"python-{PY}-embed-amd64.zip"
URL = f"https://www.python.org/ftp/python/{PY}/{EMBED}"
CACHE = os.path.join(HIER, "cache")
DIST = os.path.join(WURZEL, "dist")
ZIEL = os.path.join(DIST, "NoPop")
APP_DATEIEN = ["nopop.py", "kern.py", "tray.py", "texte.py", "VERSION", "LICENSE"]


def laden():
    os.makedirs(CACHE, exist_ok=True)
    pfad = os.path.join(CACHE, EMBED)
    if not os.path.exists(pfad):
        print("lade", URL)
        urllib.request.urlretrieve(URL, pfad)
    print("sha256", EMBED, hashlib.sha256(open(pfad, "rb").read()).hexdigest())
    return pfad


def main():
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(ZIEL)
    with zipfile.ZipFile(laden()) as z:
        z.extractall(ZIEL)

    # tkinter (fehlt in der embeddable-Version) aus der gleichen Python-Version
    basis = sys.base_prefix
    for datei in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll", "zlib1.dll"):
        shutil.copy2(os.path.join(basis, "DLLs", datei), ZIEL)
    shutil.copytree(os.path.join(basis, "Lib", "tkinter"), os.path.join(ZIEL, "tkinter"),
                    ignore=shutil.ignore_patterns("__pycache__", "test*"))
    for teil in ("tcl8.6", "tk8.6"):
        shutil.copytree(os.path.join(basis, "tcl", teil), os.path.join(ZIEL, "tcl", teil),
                        ignore=shutil.ignore_patterns("demos", "images", "msgs", "tzdata", "*.html"))

    # Suchpfad: Python-Bibliothek, Programmordner und app/
    pth = [n for n in os.listdir(ZIEL) if n.endswith("._pth")][0]
    with open(os.path.join(ZIEL, pth), "w") as f:
        f.write(f"python{sys.version_info[0]}{sys.version_info[1]}.zip\n.\napp\n")

    app = os.path.join(ZIEL, "app")
    os.makedirs(app)
    for d in APP_DATEIEN:
        shutil.copy2(os.path.join(WURZEL, d), app)
    shutil.copytree(os.path.join(WURZEL, "assets"), os.path.join(app, "assets"),
                    ignore=shutil.ignore_patterns("logo-512.png"))
    for d in ("install.ps1", "uninstall.ps1", "Install.cmd"):
        shutil.copy2(os.path.join(HIER, d), ZIEL)

    archiv = os.path.join(DIST, f"NoPop-{VERSION}-windows-x64.zip")
    with zipfile.ZipFile(archiv, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for wurzel, _, dateien in os.walk(ZIEL):
            for d in dateien:
                voll = os.path.join(wurzel, d)
                z.write(voll, os.path.join("NoPop", os.path.relpath(voll, ZIEL)))
    print("fertig:", archiv, round(os.path.getsize(archiv) / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
