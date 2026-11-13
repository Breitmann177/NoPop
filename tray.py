"""Tray-Symbol direkt über die Windows-API (ohne pystray/Pillow).

Läuft in einem eigenen Thread mit Windows-Nachrichtenschleife – schläft,
solange nichts passiert (0 % CPU).
"""
import ctypes as C
import threading
from ctypes import wintypes as W

u32 = C.windll.user32
s32 = C.windll.shell32
k32 = C.windll.kernel32

LRESULT = C.c_ssize_t
WNDPROC = C.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)

u32.DefWindowProcW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u32.DefWindowProcW.restype = LRESULT
u32.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, C.c_int, C.c_int, C.c_int, C.c_int,
                                W.HWND, W.HMENU, W.HINSTANCE, W.LPVOID]
u32.CreateWindowExW.restype = W.HWND
u32.LoadImageW.argtypes = [W.HINSTANCE, W.LPCWSTR, W.UINT, C.c_int, C.c_int, W.UINT]
u32.LoadImageW.restype = W.HANDLE
u32.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u32.TrackPopupMenu.argtypes = [W.HMENU, W.UINT, C.c_int, C.c_int, C.c_int, W.HWND, C.c_void_p]
u32.AppendMenuW.argtypes = [W.HMENU, W.UINT, C.c_size_t, W.LPCWSTR]
u32.CreatePopupMenu.restype = W.HMENU
u32.DestroyMenu.argtypes = [W.HMENU]
u32.SetForegroundWindow.argtypes = [W.HWND]
u32.DestroyWindow.argtypes = [W.HWND]
u32.GetMessageW.argtypes = [C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT]
k32.GetModuleHandleW.restype = W.HMODULE


class WNDCLASSW(C.Structure):
    _fields_ = [("style", W.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", C.c_int), ("cbWndExtra", C.c_int),
                ("hInstance", W.HINSTANCE), ("hIcon", W.HICON), ("hCursor", W.HANDLE), ("hbrBackground", W.HBRUSH),
                ("lpszMenuName", W.LPCWSTR), ("lpszClassName", W.LPCWSTR)]


class NOTIFYICONDATAW(C.Structure):
    _fields_ = [("cbSize", W.DWORD), ("hWnd", W.HWND), ("uID", W.UINT), ("uFlags", W.UINT),
                ("uCallbackMessage", W.UINT), ("hIcon", W.HICON), ("szTip", W.WCHAR * 128),
                ("dwState", W.DWORD), ("dwStateMask", W.DWORD), ("szInfo", W.WCHAR * 256),
                ("uVersion", W.UINT), ("szInfoTitle", W.WCHAR * 64), ("dwInfoFlags", W.DWORD),
                ("guidItem", C.c_byte * 16), ("hBalloonIcon", W.HICON)]


s32.Shell_NotifyIconW.argtypes = [W.DWORD, C.POINTER(NOTIFYICONDATAW)]

WM_APP_TRAY = 0x8000 + 1
WM_CLOSE, WM_DESTROY, WM_NULL = 0x0010, 0x0002, 0x0000
WM_LBUTTONUP, WM_RBUTTONUP = 0x0202, 0x0205
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
MF_STRING, MF_CHECKED, MF_SEPARATOR, MF_DEFAULT = 0, 8, 0x800, 0x1000


class Tray(threading.Thread):
    """menue(): Liste aus (text, aktion, haken) oder None für Trennlinie."""

    def __init__(self, icon_pfad, tip, links_klick, menue, bei_designwechsel=None):
        super().__init__(daemon=True, name="Tray")
        self._icon_pfad, self._tip = icon_pfad, tip
        self.links_klick, self.menue = links_klick, menue
        self.bei_designwechsel = bei_designwechsel or (lambda: None)
        self.hwnd = None
        self._icons = {}
        self._bereit = threading.Event()

    def _icon(self, pfad):
        if pfad not in self._icons:
            g = u32.GetSystemMetrics(49)  # SM_CXSMICON (DPI-abhängig)
            self._icons[pfad] = u32.LoadImageW(None, pfad, 1, g, g, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
        return self._icons[pfad]

    def _daten(self):
        d = NOTIFYICONDATAW()
        d.cbSize = C.sizeof(NOTIFYICONDATAW)
        d.hWnd, d.uID = self.hwnd, 1
        d.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        d.uCallbackMessage = WM_APP_TRAY
        d.hIcon = self._icon(self._icon_pfad)
        d.szTip = self._tip[:127]
        return d

    def setzen(self, icon_pfad=None, tip=None):
        """Darf aus jedem Thread aufgerufen werden."""
        if icon_pfad == self._icon_pfad and tip == self._tip:
            return
        self._icon_pfad = icon_pfad or self._icon_pfad
        self._tip = tip or self._tip
        if self.hwnd:
            s32.Shell_NotifyIconW(NIM_MODIFY, C.byref(self._daten()))

    def beenden(self):
        if self.hwnd:
            u32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    def _menue_zeigen(self):
        eintraege = self.menue()
        h = u32.CreatePopupMenu()
        for i, e in enumerate(eintraege, 1):
            if e is None:
                u32.AppendMenuW(h, MF_SEPARATOR, 0, None)
            else:
                text, _, haken = e
                u32.AppendMenuW(h, MF_STRING | (MF_CHECKED if haken else 0) | (MF_DEFAULT if i == 1 else 0),
                                i, text)
        p = W.POINT()
        u32.GetCursorPos(C.byref(p))
        u32.SetForegroundWindow(self.hwnd)
        wahl = u32.TrackPopupMenu(h, 0x100 | 0x80 | 0x2, p.x, p.y, 0, self.hwnd, None)
        u32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        u32.DestroyMenu(h)
        if wahl and eintraege[wahl - 1]:
            eintraege[wahl - 1][1]()

    def _wndproc(self, hwnd, msg, wp, lp):
        if msg == WM_APP_TRAY:
            if lp & 0xFFFF == WM_LBUTTONUP:
                self.links_klick()
            elif lp & 0xFFFF == WM_RBUTTONUP:
                self._menue_zeigen()
            return 0
        if msg == self._taskbar_neu:  # Explorer neu gestartet -> Symbol neu anlegen
            s32.Shell_NotifyIconW(NIM_ADD, C.byref(self._daten()))
            return 0
        if msg == 0x001A:  # WM_SETTINGCHANGE: z. B. Taskleiste hell/dunkel umgestellt
            self.bei_designwechsel()
            return 0
        if msg == WM_CLOSE:
            s32.Shell_NotifyIconW(NIM_DELETE, C.byref(self._daten()))
            u32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            u32.PostQuitMessage(0)
            return 0
        return u32.DefWindowProcW(hwnd, msg, wp, lp)

    def _hinzufuegen(self, versuch=0):
        """Symbol anlegen. Direkt nach der Anmeldung ist die Taskleiste evtl.
        noch nicht bereit – dann bis zu 30 s lang alle 2 s erneut versuchen."""
        if s32.Shell_NotifyIconW(NIM_ADD, C.byref(self._daten())):
            return
        if s32.Shell_NotifyIconW(NIM_MODIFY, C.byref(self._daten())):  # war schon da
            return
        if versuch < 15:
            t = threading.Timer(2, self._hinzufuegen, (versuch + 1,))
            t.daemon = True
            t.start()

    def run(self):
        self._proc = WNDPROC(self._wndproc)  # Referenz halten!
        hinst = k32.GetModuleHandleW(None)
        wc = WNDCLASSW(lpfnWndProc=self._proc, hInstance=hinst, lpszClassName="NoPopTray")
        u32.RegisterClassW(C.byref(wc))
        self._taskbar_neu = u32.RegisterWindowMessageW("TaskbarCreated")
        self.hwnd = u32.CreateWindowExW(0, "NoPopTray", "NoPop", 0, 0, 0, 0, 0, None, None, hinst, None)
        self._hinzufuegen()
        self._bereit.set()
        msg = W.MSG()
        while u32.GetMessageW(C.byref(msg), None, 0, 0) > 0:
            u32.TranslateMessage(C.byref(msg))
            u32.DispatchMessageW(C.byref(msg))
