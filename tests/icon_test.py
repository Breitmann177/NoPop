import sys, os, ctypes
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ctypes.windll.shcore.SetProcessDpiAwareness(1)
import nopop
app = nopop.App(); f = nopop.Fenster(app)
u = ctypes.windll.user32; u.SendMessageW.restype = ctypes.c_void_p
u.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p]
hwnd = u.GetParent(f.root.winfo_id())
print("großes Symbol gesetzt:", bool(u.SendMessageW(hwnd, 0x7F, 1, None)), "| kleines:", bool(u.SendMessageW(hwnd, 0x7F, 0, None)))
f.root.after(300, f.root.destroy); f.laufen()
