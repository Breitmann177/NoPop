import sys, os, time, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kern import Waechter, SCHWELLE
class E(dict):
    def get(self, k): return dict.get(self, k)
e = E(an=True, minuten=1)
w = Waechter(e, os.path.join(tempfile.gettempdir(), "nopop-test")); w.start(); time.sleep(1.2)
print("vorher:", w.zustand(), w.text(), "geraet:", bool(w.kein_geraet) is False)
p = subprocess.Popen(["powershell", "-NoProfile", "-c", r"(New-Object Media.SoundPlayer 'C:\Windows\Media\Windows Ding.wav').PlaySync()"])
p.wait(); time.sleep(1.2)
print("nach Ding:", w.zustand(), w.text())
# eigenes Signal messen: max Pegel über 3 s, während nur unser Signal läuft
mx = 0
for _ in range(12):
    time.sleep(0.25); mx = max(mx, w.pegel)
print("Pegel eigenes Signal: %.6f (Schwelle %.4f) -> %s" % (mx, SCHWELLE, "OK unter Schwelle" if mx < SCHWELLE else "ZU LAUT"))
from pycaw.pycaw import AudioUtilities
ses = [s for s in AudioUtilities.GetAllSessions() if s.ProcessId == os.getpid()]
print("eigene Audio-Sitzung aktiv:", [s.State for s in ses], "(1 = aktiv)")
e["an"] = False; time.sleep(0.8); print("aus:", w.zustand(), w.text())
e["an"] = True; w.letzter_ton = time.monotonic() - 61; time.sleep(0.8); print("abgelaufen:", w.zustand(), w.text())
w.stopp(); time.sleep(0.6)
