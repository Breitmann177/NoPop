import sys, os, time, ctypes, ctypes.wintypes
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ctypes.windll.shcore.SetProcessDpiAwareness(1)
import nopop as kw
from PIL import ImageGrab
ziel = sys.argv[1]
app = kw.App()
f = kw.Fenster(app)
from PIL import Image
def shot(name):
    """Fenster per PrintWindow abfotografieren (auch wenn etwas davor liegt)."""
    r = f.root; r.update()
    hwnd = ctypes.windll.user32.GetParent(r.winfo_id())
    W = ctypes.wintypes
    rc = W.RECT(); ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rc))
    w, h = rc.right - rc.left, rc.bottom - rc.top
    g = ctypes.windll.gdi32; u = ctypes.windll.user32
    hdc = u.GetWindowDC(hwnd); mdc = g.CreateCompatibleDC(hdc); bmp = g.CreateCompatibleBitmap(hdc, w, h)
    g.SelectObject(mdc, bmp); u.PrintWindow(hwnd, mdc, 2)
    class BIH(ctypes.Structure):
        _fields_ = [("biSize", W.DWORD), ("biWidth", W.LONG), ("biHeight", W.LONG), ("biPlanes", W.WORD),
                    ("biBitCount", W.WORD), ("biCompression", W.DWORD), ("biSizeImage", W.DWORD),
                    ("a", W.LONG), ("b", W.LONG), ("c", W.DWORD), ("d", W.DWORD)]
    bi = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    g.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(f"{ziel}-{name}.png")
    g.DeleteObject(bmp); g.DeleteDC(mdc); u.ReleaseDC(hwnd, hdc)
def s1():
    shot("bereit")
    app.w.spielt = True; app.w.letzter_ton = time.monotonic() - (app.e.get("minuten") * 60 - 462)
    f.aktualisieren(nur_zeichnen=True); f.root.after(700, s2)
def s2():
    shot("wach"); f.einstellungen(); f.root.after(700, s3)
def s3():
    shot("einst"); app.w.spielt = False; f.root.destroy()
f.root.after(800, s1)
f.laufen()
