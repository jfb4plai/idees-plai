"""Mode « série de clics » : une capture numérotée à chaque clic, façon enregistreur d'étapes.

Deux moments de capture :
  avant  – l'image montre l'écran TEL QU'IL ÉTAIT juste avant le clic (menu ouvert, pointeur sur
           l'élément à cliquer) : idéal pour « Cliquez ici ». Une image est rafraîchie en arrière-plan.
  apres  – l'image est prise ~0,5 s après le clic : montre le résultat du clic.
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass

from PIL import Image, ImageGrab

from . import annotate
from .grabber import draw_pointer
from .session import Capture, Session

CAPTIONS = {"left": "Cliquez ici", "right": "Faites un clic droit ici", "double": "Double-cliquez ici"}
DOUBLE_CLICK_S = 0.45
DOUBLE_CLICK_PX = 6


class FrameBuffer(threading.Thread):
    """Garde en mémoire la dernière image d'écran complète (rafraîchie ~4 fois par seconde)."""

    def __init__(self, grab=None, interval: float = 0.25):
        super().__init__(daemon=True)
        self._grab = grab or (lambda: ImageGrab.grab(all_screens=True))
        self.interval = interval
        self._lock = threading.Lock()
        self._frame: Image.Image | None = None
        self._halt = threading.Event()

    @property
    def latest(self) -> Image.Image | None:
        with self._lock:
            return self._frame

    def run(self):
        while not self._halt.is_set():
            t0 = time.monotonic()
            try:
                frame = self._grab()
                with self._lock:
                    self._frame = frame
            except Exception:
                pass
            self._halt.wait(max(0.02, self.interval - (time.monotonic() - t0)))

    def stop(self):
        self._halt.set()


def build_step(frame: Image.Image, click: tuple[int, int], number: int, kind: str = "left",
               show_pointer: bool = True) -> tuple[Image.Image, list[dict], str]:
    """Image de base (avec pointeur), annotations (anneau + pastille numérotée), légende."""
    base = frame.convert("RGB")
    cx, cy = click
    if show_pointer and 0 <= cx < base.width and 0 <= cy < base.height:
        base = draw_pointer(base, cx, cy, halo=False)
    k = max(1.0, base.height / 1080)
    r = 30 * k
    red = annotate.PALETTE["Rouge"]
    items = [
        {"type": "ellipse", "p1": (cx - r, cy - r), "p2": (cx + r, cy + r), "color": red,
         "width": max(4, int(5 * k))},
        {"type": "step", "pos": (cx - r * 0.95, cy - r * 0.95), "number": number,
         "radius": int(17 * k), "color": red},
    ]
    return base, items, CAPTIONS.get(kind, CAPTIONS["left"])


@dataclass
class _Last:
    cap: Capture
    base: Image.Image
    items: list
    button: str
    pos: tuple[int, int]
    t: float


class StepRecorder:
    """Transforme des clics (bouton, position, image) en captures de la série."""

    def __init__(self, session: Session, origin: tuple[int, int] = (0, 0), show_pointer: bool = True):
        self.session, self.origin, self.show_pointer = session, origin, show_pointer
        self.count = 0
        self._last: _Last | None = None

    def on_click(self, button: str, pos: tuple[int, int], frame: Image.Image, t: float) -> Capture:
        """Enregistre l'étape. Deux clics gauches rapprochés = un double-clic : même capture."""
        last = self._last
        if (last and button == "left" and last.button == "left" and t - last.t <= DOUBLE_CLICK_S
                and math.hypot(pos[0] - last.pos[0], pos[1] - last.pos[1]) <= DOUBLE_CLICK_PX):
            final = annotate.render(last.base, last.items)
            self.session.update(last.cap, last.base, final, last.items, CAPTIONS["double"])
            last.t = t
            return last.cap
        local = (pos[0] - self.origin[0], pos[1] - self.origin[1])
        number = len(self.session.captures) + 1
        base, items, caption = build_step(frame, local, number, button, self.show_pointer)
        cap = self.session.add(base)
        self.session.update(cap, base, annotate.render(base, items), items, caption)
        self.count += 1
        self._last = _Last(cap, base, items, button, pos, t)
        return cap


def renumber_steps(session: Session) -> int:
    """Renumérote les pastilles « étape » selon l'ordre actuel de la série (après un déplacement
    ou une suppression). Seules les captures qui contiennent des pastilles sont réécrites."""
    changed = 0
    for pos, cap in enumerate(session.captures, start=1):
        steps = [i for i in cap.items if i.get("type") == "step"]
        if len(steps) == 1 and steps[0].get("number") != pos:
            steps[0]["number"] = pos
            base = session.load_original(cap)
            session.update(cap, base, annotate.render(base, cap.items), cap.items, cap.caption)
            changed += 1
    return changed
