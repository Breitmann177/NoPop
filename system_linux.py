"""Linux: Autostart (~/.config/autostart), nur eine Instanz (Unix-Socket), kein Tray."""
import os
import socket
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
SKRIPT = os.path.join(HIER, "nopop.py")
AUTOSTART = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                         "autostart", "nopop.desktop")
SOCKET = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", f"nopop-{os.getuid()}.sock")


def _exec():
    return f'"{sys.executable}" "{SKRIPT}" --versteckt'


def autostart_an():
    return os.path.exists(AUTOSTART)


def autostart_aktuell():
    try:
        return _exec() in open(AUTOSTART, encoding="utf-8").read()
    except OSError:
        return True


def autostart_setzen(an):
    if an:
        os.makedirs(os.path.dirname(AUTOSTART), exist_ok=True)
        with open(AUTOSTART, "w", encoding="utf-8") as f:
            f.write("[Desktop Entry]\nType=Application\nName=NoPop\n"
                    "Comment=Keeps your speakers awake so they don't pop\n"
                    f"Exec={_exec()}\nIcon=nopop\nX-GNOME-Autostart-enabled=true\nTerminal=false\n")
    elif os.path.exists(AUTOSTART):
        os.remove(AUTOSTART)


_server = None


def schon_offen():
    """True, wenn NoPop schon läuft – dann wird dort das Fenster geöffnet."""
    global _server
    try:
        with socket.socket(socket.AF_UNIX) as s:
            s.connect(SOCKET)
            s.sendall(b"zeigen")
        return True
    except OSError:
        pass
    try:
        os.unlink(SOCKET)
    except OSError:
        pass
    _server = socket.socket(socket.AF_UNIX)
    _server.bind(SOCKET)
    _server.listen(2)
    return False


def auf_zweite_instanz_warten(zeigen):
    while _server:
        try:
            c, _ = _server.accept()
            c.close()
            zeigen()
        except OSError:
            return


class Tray:
    """Platzhalter: unter Linux öffnet man NoPop über das App-Menü erneut."""

    def __init__(self, *_, **__):
        pass

    def start(self):
        pass

    def setzen(self, *_):
        pass

    def beenden(self):
        pass
