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
