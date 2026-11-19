"""Linux-Test (läuft in GitHub Actions mit PulseAudio + Null-Sink):
fremder Ton -> NoPop spielt den Wachhalte-Ton; der eigene Ton zählt nicht als Ton."""
import os, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import threading
import kern, kern_linux

FEHLER = []
threading.excepthook = lambda a: FEHLER.append(a.exc_value)


class E(dict):
    def get(self, k):
        return self[k]


ordner = tempfile.mkdtemp()
w = kern.Waechter(E(an=True, minuten=1), ordner)
w.start()
time.sleep(2)
assert not w.spielt, "sollte ohne Ton nicht spielen"
fremd = subprocess.Popen(["paplay", "--client-name=Test", kern.signal_datei(ordner)])
for _ in range(20):
    time.sleep(0.5)
    if w.spielt:
        break
assert w.spielt, "fremder Ton nicht erkannt"
fremd.wait()
time.sleep(1.5)
aus = kern_linux._pactl("list", "sink-inputs")
assert 'application.name = "NoPop"' in aus, "eigener Stream fehlt"
assert not kern_linux.fremder_ton(aus), "eigener Ton wird als fremd gezählt"
assert w.pegel == 0.0
w.stopp(); w.join(3)
assert not kern_linux.EIGENE, "Abspieler nicht beendet"
assert not FEHLER, FEHLER
print("linux ok")
