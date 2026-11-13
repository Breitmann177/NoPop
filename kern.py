"""Kern von NoPop – bewusst ohne Zusatz-Bibliotheken.

* Ton erkennen: Windows-Pegelmesser des Standard-Lautsprechers (direkt per COM).
* Wach halten:  Windows spielt selbst eine Schleife mit einem unhörbaren Ton
                (20 Hz, ca. -70 dB). Digitale Stille reicht nicht: Smart-Verstärker
                (Cirrus Logic, Realtek …) schalten bei Stille ab – genau das ploppt.
                Python rechnet dabei nichts, Windows loopt die Datei selbst.
"""
import ctypes as C
import math
import os
import struct
import threading
import time
import wave
import winsound

from texte import t

# Ab diesem Spitzenpegel zählt etwas als Ton. Unser eigenes Signal misst je nach
# Treiber 0,0003–0,001 – mit Abstand darunter, sonst hielte es sich selbst wach.
# Normale Musik/Videos liegen bei etwa 0,05–1.
SCHWELLE = 0.005
TAKT = 0.5           # Sekunden zwischen zwei Messungen
GERAET_PRUEFEN = 5   # Sekunden zwischen Prüfungen auf Gerätewechsel

ole32 = C.windll.ole32
ole32.CoTaskMemFree.argtypes = [C.c_void_p]


class GUID(C.Structure):
    _fields_ = [("a", C.c_uint32), ("b", C.c_uint16), ("c", C.c_uint16), ("d", C.c_ubyte * 8)]


def _guid(s):
    g = GUID()
    ole32.CLSIDFromString(C.c_wchar_p("{%s}" % s), C.byref(g))
    return g


CLSID_ENUM = _guid("BCDE0395-E52F-467C-8E3D-C4579291692E")
IID_ENUM = _guid("A95664D2-9614-4F35-A746-DE8DB63617E6")
IID_METER = _guid("C02216F6-8C67-4B5B-9D00-D008E73E0064")
CLSCTX_ALL = 23


def _methode(obj, index, *argtypes):
    """COM-Methode Nummer `index` aus der vtable von `obj`."""
    vtbl = C.cast(obj, C.POINTER(C.POINTER(C.c_void_p)))[0]
    f = C.WINFUNCTYPE(C.c_long, C.c_void_p, *argtypes)(vtbl[index])
    return lambda *a: f(obj, *a)


def _freigeben(obj):
    if obj:
        vtbl = C.cast(obj, C.POINTER(C.POINTER(C.c_void_p)))[0]
        C.WINFUNCTYPE(C.c_ulong, C.c_void_p)(vtbl[2])(obj)


class Messer:
    """Spitzenpegel des Standard-Lautsprechers (alle Programme zusammen)."""

    def __init__(self):
        ole32.CoInitializeEx(None, 0)
        self.enum = C.c_void_p()
        ole32.CoCreateInstance(C.byref(CLSID_ENUM), None, CLSCTX_ALL, C.byref(IID_ENUM), C.byref(self.enum))
        self.geraet = C.c_void_p()
        self.meter = C.c_void_p()
        self._peak = None
        self.geraet_id = None

    def _aktuelles_geraet(self):
        dev = C.c_void_p()
        hr = _methode(self.enum, 4, C.c_int, C.c_int, C.POINTER(C.c_void_p))(0, 0, C.byref(dev))
        if hr != 0 or not dev:
            return None, None
        p = C.c_wchar_p()
        _methode(dev, 5, C.POINTER(C.c_wchar_p))(C.byref(p))
        gid = p.value
        ole32.CoTaskMemFree(C.cast(p, C.c_void_p))
        return dev, gid

    def pruefen(self):
        """True, wenn sich das Standardgerät geändert hat (dann neu verbunden)."""
        dev, gid = self._aktuelles_geraet()
        if gid == self.geraet_id and self._peak is not None:
            _freigeben(dev)
            return False
        _freigeben(self.meter)
        _freigeben(self.geraet)
        self.meter, self._peak, self.geraet, self.geraet_id = C.c_void_p(), None, C.c_void_p(), gid
        if dev:
            self.geraet = dev
            hr = _methode(dev, 3, C.POINTER(GUID), C.c_uint32, C.c_void_p, C.POINTER(C.c_void_p))(
                C.byref(IID_METER), CLSCTX_ALL, None, C.byref(self.meter))
            if hr == 0:
                self._peak = _methode(self.meter, 3, C.POINTER(C.c_float))
        return True

    def spitze(self):
        if self._peak is None:
            return 0.0
        wert = C.c_float()
        if self._peak(C.byref(wert)) != 0:
            self._peak = None
            return 0.0
        return wert.value


def signal_datei(ordner):
    """1 s Schleife: 20-Hz-Sinus, Amplitude 10/32768 (~ -70 dB) – unhörbar."""
    pfad = os.path.join(ordner, "wach-20hz-v1.wav")
    if not os.path.exists(pfad):
        os.makedirs(ordner, exist_ok=True)
        rate = 48000
        daten = struct.pack("<%dh" % rate, *(round(10 * math.sin(2 * math.pi * 20 * i / rate))
                                             for i in range(rate)))
        with wave.open(pfad, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(daten)
    return pfad


class Waechter(threading.Thread):
    """Hält die Lautsprecher nach jedem Ton `minuten` lang wach."""

    def __init__(self, einstellungen, ordner, bei_aenderung=None):
        super().__init__(daemon=True, name="Waechter")
        self.e = einstellungen
        self.datei = signal_datei(ordner)
        self.bei_aenderung = bei_aenderung or (lambda: None)
        self.letzter_ton = None
        self.pegel = 0.0
        self.spielt = False
        self.kein_geraet = False
        self._stopp = threading.Event()

    def _start(self):
        winsound.PlaySound(self.datei, winsound.SND_FILENAME | winsound.SND_ASYNC
                           | winsound.SND_LOOP | winsound.SND_NODEFAULT)
        self.spielt = True

    def _ende(self):
        if self.spielt:
            winsound.PlaySound(None, 0)
            self.spielt = False

    def rest_sekunden(self):
        if self.letzter_ton is None:
            return 0
        return max(0.0, self.e.get("minuten") * 60 - (time.monotonic() - self.letzter_ton))

    def zustand(self):
        """aus | bereit | wach"""
        if not self.e.get("an"):
            return "aus"
        return "wach" if self.spielt else "bereit"

    def text(self, sekunden=True):
        z = self.zustand()
        if z == "aus":
            return t("Aus", "Off")
        if self.kein_geraet:
            return t("Kein Lautsprecher gefunden", "No speaker found")
        if z == "bereit":
            return t("Bereit – wartet auf Ton", "Ready – waiting for sound")
        if self.pegel >= SCHWELLE:
            return t("Ton läuft", "Sound playing")
        r = int(self.rest_sekunden())
        if sekunden:
            return t("Wach – noch ", "Awake – ") + f"{r // 60}:{r % 60:02d}" + t("", " left")
        m = max(1, math.ceil(r / 60))
        return t(f"Wach – noch {m} Min", f"Awake – {m} min left")

    def stopp(self):
        self._stopp.set()

    def run(self):
        m = Messer()
        m.pruefen()
        naechste_pruefung = time.monotonic() + GERAET_PRUEFEN
        letzter = None
        while not self._stopp.is_set():
            jetzt = time.monotonic()
            if jetzt >= naechste_pruefung:
                naechste_pruefung = jetzt + GERAET_PRUEFEN
                if m.pruefen() and self.spielt:
                    self._ende()  # auf neuem Gerät neu starten
            self.kein_geraet = m.geraet_id is None
            self.pegel = m.spitze()
            if self.pegel >= SCHWELLE:
                self.letzter_ton = jetzt

            soll = (self.e.get("an") and self.letzter_ton is not None
                    and jetzt - self.letzter_ton < self.e.get("minuten") * 60)
            if soll and not self.spielt:
                self._start()
            elif not soll and self.spielt:
                self._ende()

            st = (self.zustand(), self.text(sekunden=False))
            if st != letzter:
                letzter = st
                self.bei_aenderung()
            self._stopp.wait(TAKT)
        self._ende()
