import sys, os, time, ctypes
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tray
ok = {}
orig = tray.s32.Shell_NotifyIconW
def spion(cmd, daten):
    r = orig(cmd, daten); ok.setdefault(cmd, []).append(bool(r)); return r
tray.s32.Shell_NotifyIconW = spion
t = tray.Tray(os.path.join("assets", "tray-aus-dunkel.ico"), "NoPop Test", lambda: None, lambda: [])
t.start(); t._bereit.wait(3); time.sleep(0.3)
t.setzen(os.path.join("assets", "tray-blau-dunkel.ico"), "NoPop Test – wach"); time.sleep(0.3)
print("Icon geladen:", bool(t._icons[os.path.join("assets", "tray-aus-dunkel.ico")]))
t.beenden(); t.join(2)
print("Hinzufügen:", ok.get(0), "Ändern:", ok.get(1), "Entfernen:", ok.get(2))
