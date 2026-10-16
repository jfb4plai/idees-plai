"""Petits appels Windows via ctypes (aucune dépendance). Sans effet hors Windows."""
from __future__ import annotations

import io
import sys

IS_WIN = sys.platform == "win32"


def set_dpi_aware() -> None:
    """À appeler AVANT de créer la fenêtre : coordonnées Tk = pixels réels de l'écran."""
    if not IS_WIN:
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def virtual_screen() -> tuple[int, int, int, int] | None:
    """(gauche, haut, largeur, hauteur) de tous les écrans réunis."""
    if not IS_WIN:
        return None
    import ctypes
    gm = ctypes.windll.user32.GetSystemMetrics
    return gm(76), gm(77), gm(78), gm(79)


def cursor_pos() -> tuple[int, int] | None:
    if not IS_WIN:
        return None
    import ctypes
    from ctypes import wintypes
    pt = wintypes.POINT()
    if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        return pt.x, pt.y
    return None


def foreground_window_rect() -> tuple[int, int, int, int] | None:
    """Rectangle (x0, y0, x1, y1) de la fenêtre active, bordure invisible exclue."""
    if not IS_WIN:
        return None
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    r = wintypes.RECT()
    try:  # DWMWA_EXTENDED_FRAME_BOUNDS = 9 : rectangle réellement visible
        ok = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd), 9, ctypes.byref(r), ctypes.sizeof(r)) == 0
    except Exception:
        ok = False
    if not ok and not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return r.left, r.top, r.right, r.bottom


def copy_image_to_clipboard(img) -> bool:
    """Copie l'image au format CF_DIB (collable dans Word, Teams, Paint…)."""
    if not IS_WIN:
        return False
    import ctypes
    out = io.BytesIO()
    img.convert("RGB").save(out, "BMP")
    data = out.getvalue()[14:]  # on retire l'en-tête de fichier BMP
    k32 = ctypes.WinDLL("kernel32")
    u32 = ctypes.WinDLL("user32")
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    u32.OpenClipboard.argtypes = [ctypes.c_void_p]
    h = k32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
    if not h:
        return False
    ptr = k32.GlobalLock(h)
    ctypes.memmove(ptr, data, len(data))
    k32.GlobalUnlock(h)
    if not u32.OpenClipboard(None):
        return False
    try:
        u32.EmptyClipboard()
        return bool(u32.SetClipboardData(8, h))  # CF_DIB
    finally:
        u32.CloseClipboard()


def beep() -> None:
    if IS_WIN:
        try:
            import winsound
            winsound.MessageBeep()
        except Exception:
            pass


def foreground_is_own_process() -> bool:
    """Vrai si la fenêtre active appartient à ce programme (pour ignorer nos propres clics)."""
    if not IS_WIN:
        return False
    import ctypes
    import os
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == os.getpid()


class MouseHook:
    """Écoute globale des clics (WH_MOUSE_LL) dans un thread dédié.

    callback(bouton, x, y) est appelé DANS le thread du hook, AVANT que l'application
    cliquée ne reçoive le clic : il doit rester très rapide (mettre dans une file, rien d'autre).
    """

    def __init__(self, callback):
        import threading
        self.callback = callback
        self.ready = threading.Event()
        self.error = ""
        self._tid = 0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()
        self.ready.wait(2)
        return not self.error

    def _run(self):
        if not IS_WIN:
            self.error = "L'enregistrement des clics n'existe que sous Windows."
            self.ready.set()
            return
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.GetModuleHandleW.restype = ctypes.c_void_p
        kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
        self._tid = kernel32.GetCurrentThreadId()
        LRESULT = ctypes.c_ssize_t
        HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD), ("flags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, wintypes.DWORD]
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = LRESULT
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]

        def proc(n_code, w_param, l_param):
            if n_code >= 0 and w_param in (0x0201, 0x0204):  # WM_LBUTTONDOWN / WM_RBUTTONDOWN
                try:
                    s = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    self.callback("left" if w_param == 0x0201 else "right", s.pt.x, s.pt.y)
                except Exception:
                    pass  # un hook ne doit jamais lever
            return user32.CallNextHookEx(None, n_code, w_param, l_param)

        self._proc = HOOKPROC(proc)  # référence conservée : sinon le ramasse-miettes détruit le callback
        hook = user32.SetWindowsHookExW(14, self._proc, kernel32.GetModuleHandleW(None), 0)  # WH_MOUSE_LL
        if not hook:
            self.error = "Windows a refusé l'écoute des clics (antivirus ou stratégie de l'école ?)."
            self.ready.set()
            return
        self.ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            pass
        user32.UnhookWindowsHookEx(hook)

    def stop(self):
        if IS_WIN and self._tid:
            import ctypes
            ctypes.WinDLL("user32").PostThreadMessageW(self._tid, 0x0012, 0, 0)  # WM_QUIT
