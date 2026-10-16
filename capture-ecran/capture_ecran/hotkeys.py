"""Raccourcis clavier globaux.

Sous Windows on utilise RegisterHotKey : le raccourci est reçu SANS que la fenêtre
active perde le focus, donc un menu déroulant ouvert reste ouvert pendant la capture.
Le parseur est indépendant de la plateforme (testable partout).
"""
from __future__ import annotations

import sys
import threading

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x1, 0x2, 0x4, 0x8
MOD_NOREPEAT = 0x4000

_MODS = {"alt": MOD_ALT, "ctrl": MOD_CONTROL, "control": MOD_CONTROL, "maj": MOD_SHIFT,
         "shift": MOD_SHIFT, "win": MOD_WIN}
_SPECIAL = {"impr": 0x2C, "printscreen": 0x2C, "pause": 0x13, "inser": 0x2D, "insert": 0x2D,
            "suppr": 0x2E, "delete": 0x2E, "debut": 0x24, "home": 0x24, "fin": 0x23, "end": 0x23}


def parse_hotkey(spec: str) -> tuple[int, int]:
    """'ctrl+maj+f9' -> (modificateurs, code de touche virtuelle). ValueError si invalide."""
    parts = [p.strip().lower() for p in spec.replace(" ", "").split("+") if p.strip()]
    if len(parts) < 2:
        raise ValueError("Il faut au moins un modificateur (Ctrl, Maj, Alt) et une touche.")
    *mod_names, key = parts
    mods = 0
    for m in mod_names:
        if m not in _MODS:
            raise ValueError(f"Modificateur inconnu : « {m} ». Utilisez Ctrl, Maj, Alt ou Win.")
        mods |= _MODS[m]
    if mods == 0:
        raise ValueError("Il faut au moins un modificateur (Ctrl, Maj, Alt).")
    if mods & MOD_CONTROL and mods & MOD_ALT:
        raise ValueError("Évitez Ctrl+Alt : sur un clavier belge c'est la touche AltGr (@, |, €…).")
    if key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    elif len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    elif key in _SPECIAL:
        vk = _SPECIAL[key]
    else:
        raise ValueError(f"Touche non reconnue : « {key} ». Exemples : F9, S, 1, Impr.")
    return mods, vk


def pretty(spec: str) -> str:
    """'ctrl+shift+f9' -> 'Ctrl+Maj+F9'."""
    out = []
    for p in spec.lower().replace(" ", "").split("+"):
        out.append({"shift": "Maj", "maj": "Maj", "ctrl": "Ctrl", "control": "Ctrl",
                    "alt": "Alt", "win": "Win"}.get(p, p.upper() if len(p) <= 3 else p.capitalize()))
    return "+".join(out)


class HotkeyListener(threading.Thread):
    """Enregistre les raccourcis dans un thread dédié (boucle de messages Windows)."""

    def __init__(self, bindings: dict[str, str], callback):
        super().__init__(daemon=True)
        self.bindings = bindings
        self.callback = callback
        self.ready = threading.Event()
        self.errors: dict[str, str] = {}
        self._tid = 0

    def run(self):
        if sys.platform != "win32":
            self.errors = {k: "Raccourcis globaux disponibles uniquement sous Windows." for k in self.bindings}
            self.ready.set()
            return
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32")
        self._tid = kernel32.GetCurrentThreadId()
        ids: dict[int, str] = {}
        for i, (name, spec) in enumerate(self.bindings.items(), start=1):
            try:
                mods, vk = parse_hotkey(spec)
            except ValueError as e:
                self.errors[name] = str(e)
                continue
            if user32.RegisterHotKey(None, i, mods | MOD_NOREPEAT, vk):
                ids[i] = name
            else:
                self.errors[name] = "Raccourci déjà utilisé par un autre programme."
        self.ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312 and msg.wParam in ids:  # WM_HOTKEY
                self.callback(ids[msg.wParam])
        for i in ids:
            user32.UnregisterHotKey(None, i)

    def stop(self):
        if sys.platform == "win32" and self._tid:
            import ctypes
            ctypes.WinDLL("user32").PostThreadMessageW(self._tid, 0x0012, 0, 0)  # WM_QUIT
