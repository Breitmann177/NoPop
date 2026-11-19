"""Linux: Ton erkennen und wach halten über PipeWire/PulseAudio (pactl, pacat).

Erkennen: läuft irgendein fremder Wiedergabe-Stream (nicht pausiert)?
Wach halten: pacat spielt den unhörbaren Ton; Python schiebt nur alle 1 s
einen fertigen Block nach (pacat bremst selbst, ~0 % CPU).
"""
import os
import shutil
import subprocess
import threading
import wave

_UMG = dict(os.environ, LC_ALL="C")  # pactl-Ausgabe nicht übersetzen
EIGENE = set()                         # PIDs unserer eigenen Abspieler


def _pactl(*args):
    try:
        r = subprocess.run(["pactl", *args], capture_output=True, text=True, env=_UMG, timeout=3)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def fremder_ton(ausgabe):
    """True, wenn ein nicht pausierter Stream läuft, der nicht von NoPop ist."""
    for block in ausgabe.split("Sink Input #")[1:]:
        if "Corked: yes" in block or 'application.name = "NoPop"' in block:
            continue
        pid = None
        for zeile in block.splitlines():
            zeile = zeile.strip()
            if zeile.startswith("application.process.id = "):
                pid = zeile.split("=", 1)[1].strip().strip('"')
        if pid and pid.isdigit() and int(pid) in EIGENE:
            continue
        return True
    return False


class Messer:
    def __init__(self):
        self.geraet_id = None

    def pruefen(self):
        neu = (_pactl("get-default-sink") or "").strip() or None
        if neu is None and _pactl("info") is not None:
            neu = "standard"  # ältere pactl ohne get-default-sink
        alt, self.geraet_id = self.geraet_id, neu
        return neu != alt

    def spitze(self):
        aus = _pactl("list", "sink-inputs")
        return 1.0 if aus and fremder_ton(aus) else 0.0


class Ton:
    def __init__(self, datei):
        with wave.open(datei, "rb") as w:
            self.rate, self.block = w.getframerate(), w.readframes(w.getnframes())
        self.proc = None

    def _befehl(self):
        if shutil.which("pacat"):
            return ["pacat", "--playback", "--client-name=NoPop", "--stream-name=NoPop",
                    "--raw", "--format=s16le", f"--rate={self.rate}", "--channels=1", "--latency-msec=500"]
        if shutil.which("pw-cat"):
            return ["pw-cat", "--playback", "--raw", "--format=s16", f"--rate={self.rate}", "--channels=1",
                    "-P", "application.name=NoPop", "-"]
        return ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", str(self.rate), "-c", "1"]

    def start(self):
        try:
            self.proc = subprocess.Popen(self._befehl(), stdin=subprocess.PIPE,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            self.proc = None
            return
        EIGENE.add(self.proc.pid)
        threading.Thread(target=self._fuettern, args=(self.proc,), daemon=True).start()

    def _fuettern(self, proc):
        try:
            while proc.poll() is None:
                proc.stdin.write(self.block)
                proc.stdin.flush()
        except (OSError, ValueError):
            pass

    def stopp(self):
        p, self.proc = self.proc, None
        if p:
            try:
                p.stdin.close()
            except OSError:
                pass
            p.terminate()
            try:
                p.wait(2)
            except subprocess.TimeoutExpired:
                p.kill()
            EIGENE.discard(p.pid)
