"""Kern von NoPop – bewusst ohne Zusatz-Bibliotheken.

* Ton erkennen: Windows-Pegelmesser (kern_win.py) bzw. PipeWire/PulseAudio (kern_linux.py).
* Wach halten:  Windows spielt selbst eine Schleife mit einem unhörbaren Ton
                (20 Hz, ca. -70 dB). Digitale Stille reicht nicht: Smart-Verstärker
                (Cirrus Logic, Realtek …) schalten bei Stille ab – genau das ploppt.
"""
import math
import os
import struct
import threading
import time
import sys
import wave

if sys.platform == "win32":
    from kern_win import Messer, Ton
else:
    from kern_linux import Messer, Ton

from texte import t

# Ab diesem Spitzenpegel zählt etwas als Ton. Unser eigenes Signal misst je nach
# Treiber 0,0003–0,001 – mit Abstand darunter, sonst hielte es sich selbst wach.
# Normale Musik/Videos liegen bei etwa 0,05–1.
SCHWELLE = 0.005
TAKT = 0.5           # Sekunden zwischen zwei Messungen
GERAET_PRUEFEN = 5   # Sekunden zwischen Prüfungen auf Gerätewechsel

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
        self.ton = Ton(signal_datei(ordner))
        self.bei_aenderung = bei_aenderung or (lambda: None)
        self.letzter_ton = None
        self.pegel = 0.0
        self.spielt = False
        self.kein_geraet = False
        self._stopp = threading.Event()

    def _start(self):
        self.ton.start()
        self.spielt = True

    def _ende(self):
        if self.spielt:
            self.ton.stopp()
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
