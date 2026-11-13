"""NoPop – hält deine Lautsprecher wach, damit nichts ploppt.

Leicht gebaut: nur Python-Standardbibliothek. Im Hintergrund laufen nur
Tray-Symbol und Wächter (2 Messungen pro Sekunde). Das Fenster wird erst
beim Öffnen geladen und beim Schließen wieder freigegeben.
Start mit --versteckt öffnet kein Fenster (für den Windows-Autostart).
"""
import ctypes
import ctypes.wintypes
import gc
import json
import os
import queue
import sys
import threading
import winreg

from kern import Waechter
from texte import t
from tray import Tray

APP = "NoPop"
HIER = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP)
DATEI = os.path.join(ORDNER, "einstellungen.json")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
MAX_MIN = 240

STANDARD = {"an": True, "minuten": 10, "farbe": "silber", "erster_start": True}
FARBEN = {"silber": "#d0d0d6", "gruen": "#55d375", "blau": "#4f9cf0",
          "lila": "#a57cf0", "orange": "#f39e43", "rot": "#ea6060"}
BG, FG, DIM, LINIE, FELD = "#0e0e0f", "#e8e8ea", "#8a8a90", "#26262a", "#18181b"


def asset(name):
    return os.path.join(HIER, "assets", name)


def taskleiste():
    """'hell' oder 'dunkel' – passend dazu wird das Tray-Symbol gewählt."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return "hell" if winreg.QueryValueEx(k, "SystemUsesLightTheme")[0] else "dunkel"
    except OSError:
        return "dunkel"


# ---------------------------------------------------------------- Einstellungen
class Einstellungen:
    def __init__(self):
        self._lock = threading.Lock()
        self._d = dict(STANDARD)
        try:
            with open(DATEI, encoding="utf-8") as f:
                alt = json.load(f)
            if "modus" in alt and "an" not in alt:  # ältere Version
                alt["an"] = alt.pop("modus") != "aus"
            self._d.update({k: v for k, v in alt.items() if k in STANDARD})
        except Exception:
            pass
        if self._d["farbe"] not in FARBEN:
            self._d["farbe"] = "silber"

    def get(self, k):
        with self._lock:
            return self._d[k]

    def set(self, k, v):
        with self._lock:
            self._d[k] = v
            try:
                os.makedirs(ORDNER, exist_ok=True)
                with open(DATEI, "w", encoding="utf-8") as f:
                    json.dump(self._d, f, indent=2)
            except Exception:
                pass


# ---------------------------------------------------------------- Autostart
# Über die Aufgabenplanung statt über den Run-Schlüssel: Windows hat den
# Run-Eintrag beim Anmelden kommentarlos übersprungen. Die Aufgabe startet
# bei der Anmeldung – ausdrücklich auch im Akkubetrieb.
AUFGABE = APP


def _schtasks(*args):
    import subprocess
    return subprocess.run(["schtasks", *args], capture_output=True, text=True, encoding="oem", errors="replace",
                          creationflags=0x08000000)  # CREATE_NO_WINDOW


def _aufgabe_xml():
    from xml.sax.saxutils import escape
    benutzer = escape(f'{os.environ.get("USERDOMAIN", "")}\\{os.environ.get("USERNAME", "")}')
    pyw = escape(os.path.join(sys.base_prefix, "pythonw.exe"))  # signiertes Basis-Python
    skript = escape(os.path.abspath(__file__))
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{escape(t('NoPop – hält die Lautsprecher wach', 'NoPop – keeps your speakers awake'))}</Description></RegistrationInfo>
  <Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{benutzer}</UserId></LogonTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>{benutzer}</UserId><LogonType>InteractiveToken</LogonType>
    <RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RestartOnFailure><Interval>PT1M</Interval><Count>3</Count></RestartOnFailure>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author"><Exec><Command>"{pyw}"</Command><Arguments>"{skript}" --versteckt</Arguments>
    <WorkingDirectory>{escape(HIER)}</WorkingDirectory></Exec></Actions>
</Task>
"""


def autostart_an():
    return _schtasks("/Query", "/TN", AUFGABE).returncode == 0


def autostart_setzen(an):
    if an:
        import tempfile
        pfad = os.path.join(tempfile.gettempdir(), "nopop-aufgabe.xml")
        with open(pfad, "w", encoding="utf-16") as f:
            f.write(_aufgabe_xml())
        try:
            r = _schtasks("/Create", "/TN", AUFGABE, "/XML", pfad, "/F")
        finally:
            os.remove(pfad)
        if r.returncode != 0:
            raise OSError(r.stderr.strip() or r.stdout.strip())
    else:
        _schtasks("/Delete", "/TN", AUFGABE, "/F")
    _run_eintrag_entfernen(APP)


def _run_eintrag_entfernen(name):
    """Alten Run-Eintrag löschen. True, wenn einer da war."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_ALL_ACCESS) as k:
            winreg.QueryValueEx(k, name)
            winreg.DeleteValue(k, name)
            return True
    except OSError:
        return False


# ---------------------------------------------------------------- Nur eine Instanz
k32 = ctypes.windll.kernel32
k32.CreateEventW.restype = ctypes.c_void_p
k32.OpenEventW.restype = ctypes.c_void_p
EVENT_NAME = "Local\\NoPopFensterZeigen"


def schon_offen():
    """True, wenn NoPop schon läuft – dann wird dort das Fenster geöffnet."""
    k32.CreateMutexW(None, False, "Local\\NoPopEinzeln")
    if k32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        h = k32.OpenEventW(0x0002, False, EVENT_NAME)
        if h:
            k32.SetEvent(ctypes.c_void_p(h))
        return True
    return False


# ---------------------------------------------------------------- App
class App:
    def __init__(self):
        self.e = Einstellungen()
        self.q = queue.Queue()
        self.w = Waechter(self.e, ORDNER, bei_aenderung=self.tray_aktualisieren)
        self.tray = Tray(asset(f"tray-aus-{taskleiste()}.ico"), APP, lambda: self.q.put("zeigen"),
                         self.tray_menue, bei_designwechsel=self.tray_aktualisieren)

    def tray_menue(self):
        return [(t("Öffnen", "Open"), lambda: self.q.put("zeigen"), False),
                (t("An", "On"), self.umschalten, self.e.get("an")),
                None,
                (t("Beenden", "Quit"), lambda: self.q.put("beenden"), False)]

    def tray_aktualisieren(self):
        wach = self.w.zustand() == "wach"
        name = self.e.get("farbe") if wach else "aus"
        self.tray.setzen(asset(f"tray-{name}-{taskleiste()}.ico"),
                         f"{APP} – {self.w.text(sekunden=False)}")

    def umschalten(self):
        self.e.set("an", not self.e.get("an"))
        self.tray_aktualisieren()

    def _auf_zweite_instanz_warten(self):
        h = k32.CreateEventW(None, False, False, EVENT_NAME)
        while True:
            k32.WaitForSingleObject(ctypes.c_void_p(h), 0xFFFFFFFF)
            self.q.put("zeigen")

    def run(self, zeigen):
        self.tray.start()
        self.w.start()
        threading.Thread(target=self._auf_zweite_instanz_warten, daemon=True).start()
        if self.e.get("erster_start"):
            self.e.set("erster_start", False)
            try:
                autostart_setzen(True)
            except Exception:
                pass
            zeigen = True
        elif autostart_an() and os.path.abspath(__file__) not in _schtasks("/Query", "/TN", AUFGABE, "/XML").stdout:
            try:  # NoPop wurde verschoben/neu installiert -> Autostart auf diesen Ort umstellen
                autostart_setzen(True)
            except Exception:
                pass
        if zeigen:
            self.q.put("zeigen")
        # Hauptthread schläft hier, bis jemand das Fenster öffnet oder beendet
        while True:
            befehl = self.q.get()
            if befehl == "zeigen" and Fenster(self).laufen():
                break
            if befehl == "beenden":
                break
            gc.collect()
        self.w.stopp()
        self.tray.beenden()
        self.w.join(2)


# ---------------------------------------------------------------- Fenster
class Fenster:
    """Schlichtes Fenster mit tkinter (wird nur bei Bedarf geladen)."""

    def __init__(self, app):
        import tkinter as tk
        self.tk, self.app, self.e, self.w = tk, app, app.e, app.w
        self.beenden_gewuenscht = False
        r = self.root = tk.Tk()
        r.title(APP)
        r.configure(bg=BG)
        r.resizable(False, False)
        try:
            r.iconbitmap(asset("nopop.ico"))
        except Exception:
            pass
        self.k = r.winfo_fpixels("1i") / 96  # DPI-Faktor
        try:  # dunkle Titelleiste + NoPop-Logo auf dem Taskleisten-Knopf (statt Python-Symbol)
            r.update_idletasks()
            u32 = ctypes.windll.user32
            hwnd = u32.GetParent(r.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
            u32.LoadImageW.restype = ctypes.c_void_p
            u32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p]
            for art, metrik in ((1, 11), (0, 49)):  # ICON_BIG/SM_CXICON, ICON_SMALL/SM_CXSMICON
                g = u32.GetSystemMetrics(metrik)
                h = u32.LoadImageW(None, asset("nopop.ico"), 1, g, g, 0x10)
                if h:
                    u32.SendMessageW(hwnd, 0x0080, art, h)  # WM_SETICON
        except Exception:
            pass
        self.einst_offen = False
        self._zeichen = None

        kopf = tk.Frame(r, bg=BG)
        kopf.pack(fill="x", padx=self.px(16), pady=(self.px(12), 0))
        tk.Label(kopf, text="NoPop", bg=BG, fg=FG, font=("Segoe UI Semibold", 11)).pack(side="left")
        self.zahnrad = tk.Label(kopf, text="⚙", bg=BG, fg=DIM, font=("Segoe UI Symbol", 13), cursor="hand2")
        self.zahnrad.pack(side="right")
        self.zahnrad.bind("<Button-1>", lambda _: self.einstellungen())
        self.zahnrad.bind("<Enter>", lambda _: self.zahnrad.configure(fg=FG))
        self.zahnrad.bind("<Leave>", lambda _: self.zahnrad.configure(fg=DIM))

        g = self.px(104)
        self.knopf = tk.Canvas(r, width=g, height=g, bg=BG, highlightthickness=0, cursor="hand2")
        self.knopf.pack(pady=(self.px(10), self.px(6)))
        self.knopf.bind("<Button-1>", lambda _: self.umschalten())

        self.status = tk.Label(r, text="", bg=BG, fg=FG, font=("Segoe UI", 10))
        self.status.pack(pady=(0, self.px(14)))

        self.einst = self._einstellungen_bauen()
        r.bind("<space>", lambda _: self.umschalten() if r.focus_get() is not self.min_feld else None)
        r.protocol("WM_DELETE_WINDOW", r.destroy)
        self.aktualisieren()
        self._platzieren()

    def px(self, n):
        return int(round(n * self.k))

    # ---------- Einstellungen ----------
    def _einstellungen_bauen(self):
        tk = self.tk
        f = tk.Frame(self.root, bg=BG)
        tk.Frame(f, bg=LINIE, height=1).pack(fill="x", padx=self.px(16))
        innen = tk.Frame(f, bg=BG)
        innen.pack(fill="x", padx=self.px(16), pady=self.px(8))
        innen.grid_columnconfigure(0, weight=1)

        def zeile(nr, text):
            tk.Label(innen, text=text, bg=BG, fg=FG, font=("Segoe UI", 10)).grid(
                row=nr, column=0, sticky="w", pady=self.px(6))
            rechts = tk.Frame(innen, bg=BG)
            rechts.grid(row=nr, column=1, sticky="e")
            return rechts

        # Minuten eintippen (Mausrad geht auch)
        rechts = zeile(0, t("Wach halten", "Keep awake"))
        self.min_feld = tk.Entry(rechts, width=4, justify="center", bg=FELD, fg=FG, insertbackground=FG,
                                 relief="flat", font=("Segoe UI Semibold", 10), highlightthickness=1,
                                 highlightbackground=LINIE, highlightcolor=FARBEN[self.e.get("farbe")])
        self.min_feld.insert(0, str(self.e.get("minuten")))
        self.min_feld.pack(side="left", ipady=self.px(2))
        tk.Label(rechts, text="Min", bg=BG, fg=DIM, font=("Segoe UI", 9)).pack(side="left", padx=(self.px(5), 0))
        for ev in ("<Return>", "<FocusOut>", "<KP_Enter>"):
            self.min_feld.bind(ev, lambda _: self._minuten())
        self.min_feld.bind("<MouseWheel>", self._rad)

        # Farbe
        rechts = zeile(1, t("Farbe", "Color"))
        d = self.px(18)
        self.farben = tk.Canvas(rechts, width=d * len(FARBEN) + self.px(4) * (len(FARBEN) - 1), height=d,
                                bg=BG, highlightthickness=0, cursor="hand2")
        self.farben.pack()
        self.farben.bind("<Button-1>", self._farbe_klick)
        self._farben_zeichnen()

        # Autostart
        rechts = zeile(2, t("Mit Windows starten", "Start with Windows"))
        self.schalter = tk.Canvas(rechts, width=self.px(34), height=self.px(18), bg=BG, highlightthickness=0,
                                  cursor="hand2")
        self.schalter.pack()
        self.schalter.bind("<Button-1>", lambda _: self._autostart())
        self._schalter_zeichnen()

        ende = tk.Label(f, text=t("NoPop beenden", "Quit NoPop"), bg=BG, fg=DIM, font=("Segoe UI", 9), cursor="hand2")
        ende.pack(pady=(0, self.px(10)))
        ende.bind("<Button-1>", lambda _: self.beenden())
        return f

    def einstellungen(self):
        self.einst_offen = not self.einst_offen
        if self.einst_offen:
            self.einst.pack(fill="x")
        else:
            self._minuten()
            self.einst.pack_forget()
        self._platzieren()

    def _minuten(self):
        try:
            m = int("".join(ch for ch in self.min_feld.get() if ch.isdigit()))
        except ValueError:
            m = self.e.get("minuten")
        self._minuten_setzen(m)

    def _rad(self, ev):
        self._minuten_setzen(self.e.get("minuten") + (1 if ev.delta > 0 else -1))

    def _minuten_setzen(self, m):
        m = max(1, min(MAX_MIN, m))
        if m != self.e.get("minuten"):
            self.e.set("minuten", m)
        self.min_feld.delete(0, "end")
        self.min_feld.insert(0, str(m))

    def _farben_zeichnen(self):
        c, d, a = self.farben, self.px(18), self.px(4)
        c.delete("all")
        for i, (name, farbe) in enumerate(FARBEN.items()):
            x = i * (d + a)
            if name == self.e.get("farbe"):
                c.create_oval(x + 1, 1, x + d - 1, d - 1, outline=FG, width=max(1, self.px(1.5)))
            c.create_oval(x + self.px(4), self.px(4), x + d - self.px(4), d - self.px(4), fill=farbe, outline="")

    def _farbe_klick(self, ev):
        i = int(ev.x // (self.px(18) + self.px(4)))
        namen = list(FARBEN)
        if 0 <= i < len(namen):
            self.e.set("farbe", namen[i])
            self._farben_zeichnen()
            self._schalter_zeichnen()
            self.min_feld.configure(highlightcolor=FARBEN[namen[i]])
            self._zeichen = None
            self.aktualisieren(nur_zeichnen=True)
            self.app.tray_aktualisieren()

    def _schalter_zeichnen(self):
        c = self.schalter
        c.delete("all")
        an = autostart_an()
        w, h = self.px(34), self.px(18)
        farbe = FARBEN[self.e.get("farbe")] if an else LINIE
        c.create_oval(0, 0, h, h, fill=farbe, outline="")
        c.create_oval(w - h, 0, w, h, fill=farbe, outline="")
        c.create_rectangle(h / 2, 0, w - h / 2, h, fill=farbe, outline="")
        m = self.px(3)
        x = w - h if an else 0
        c.create_oval(x + m, m, x + h - m, h - m, fill=BG if an else DIM, outline="")

    def _autostart(self):
        try:
            autostart_setzen(not autostart_an())
        except Exception:
            pass
        self._schalter_zeichnen()

    # ---------- Knopf + Status ----------
    def umschalten(self):
        self.app.umschalten()
        self.aktualisieren(nur_zeichnen=True)

    def _knopf_zeichnen(self, zustand):
        c, g = self.knopf, self.px(104)
        akzent = FARBEN[self.e.get("farbe")]
        c.delete("all")
        m = self.px(6)
        if zustand == "wach":      # dicker Ring = Lautsprecher werden wach gehalten
            c.create_oval(m, m, g - m, g - m, outline=akzent, width=self.px(5))
        elif zustand == "bereit":  # dünner Ring = an, wartet auf Ton
            c.create_oval(m, m, g - m, g - m, outline=akzent, width=self.px(2))
        else:
            c.create_oval(m, m, g - m, g - m, outline="#2a2a2e", width=self.px(2))
        c.create_oval(self.px(14), self.px(14), g - self.px(14), g - self.px(14), fill="#151517", outline="")
        mitte, r, b = g / 2, self.px(17), self.px(4)
        sym = akzent if zustand != "aus" else "#6a6a70"
        c.create_arc(mitte - r, mitte - r, mitte + r, mitte + r, start=125, extent=290,
                     style="arc", outline=sym, width=b)
        c.create_line(mitte, mitte - r - self.px(3), mitte, mitte - self.px(2), fill=sym, width=b,
                      capstyle="round")

    def aktualisieren(self, nur_zeichnen=False):
        z = self.w.zustand()
        if z != self._zeichen:
            self._zeichen = z
            self._knopf_zeichnen(z)
        self.status.configure(text=self.w.text(), fg=DIM if z == "aus" else FG)
        if nur_zeichnen:
            return
        try:
            while True:
                befehl = self.app.q.get_nowait()
                if befehl == "zeigen":
                    self._vorholen()
                elif befehl == "beenden":
                    self.beenden()
                    return
        except queue.Empty:
            pass
        self.root.after(500, self.aktualisieren)

    # ---------- Fenster ----------
    def _platzieren(self):
        """Unten rechts über der Taskleiste, wie ein Tray-Fenster."""
        r = self.root
        r.update_idletasks()
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0)  # Arbeitsbereich
        b = max(r.winfo_reqwidth(), self.px(270))
        h = r.winfo_reqheight()
        r.geometry(f"{b}x{h}+{rect.right - b - self.px(24)}+{rect.bottom - h - self.px(48)}")

    def _vorholen(self):
        r = self.root
        r.deiconify()
        r.lift()
        r.attributes("-topmost", True)
        r.after(150, lambda: r.attributes("-topmost", False))
        r.focus_force()

    def beenden(self):
        self.beenden_gewuenscht = True
        self.root.destroy()

    def laufen(self):
        """Zeigt das Fenster, bis es geschlossen wird. True = App beenden."""
        self._vorholen()
        self.root.mainloop()
        self.root = None
        return self.beenden_gewuenscht


if __name__ == "__main__":
    if schon_offen():
        sys.exit(0)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("NoPop.App")
    App().run(zeigen="--versteckt" not in sys.argv)
