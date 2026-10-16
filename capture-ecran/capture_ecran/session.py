"""Une « série » de captures : dossier + session.json (légendes, annotations, ordre)."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import Image


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:40]


@dataclass
class Capture:
    id: int
    caption: str = ""
    items: list = field(default_factory=list)
    created: str = ""

    @property
    def name(self) -> str:
        return f"capture_{self.id:03d}.png"


class Session:
    def __init__(self, folder: Path, title: str = ""):
        self.folder = Path(folder)
        self.title = title
        self.captures: list[Capture] = []
        self._next_id = 1

    # ---- création / ouverture -------------------------------------------------
    @classmethod
    def new(cls, base_dir: Path, title: str = "") -> "Session":
        stamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
        name = stamp + (f"_{slugify(title)}" if slugify(title) else "")
        folder = Path(base_dir) / name
        n = 2
        while folder.exists():
            folder = Path(base_dir) / f"{name}-{n}"
            n += 1
        (folder / "originales").mkdir(parents=True)
        s = cls(folder, title or "Ma série de captures")
        s.save()
        return s

    @classmethod
    def open(cls, folder: Path) -> "Session":
        folder = Path(folder)
        data = json.loads((folder / "session.json").read_text("utf-8"))
        s = cls(folder, data.get("title", ""))
        s.captures = [Capture(c["id"], c.get("caption", ""), [_fix_item(i) for i in c.get("items", [])],
                              c.get("created", "")) for c in data.get("captures", [])]
        s._next_id = max([c.id for c in s.captures], default=0) + 1
        return s

    def save(self) -> None:
        data = {"version": 1, "title": self.title, "captures": [asdict(c) for c in self.captures]}
        tmp = self.folder / "session.json.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(self.folder / "session.json")

    # ---- fichiers ---------------------------------------------------------------
    def final_path(self, cap: Capture) -> Path:
        return self.folder / cap.name

    def original_path(self, cap: Capture) -> Path:
        return self.folder / "originales" / cap.name

    def audio_path(self, cap: Capture) -> Path:
        return self.folder / "audio" / f"capture_{cap.id:03d}.wav"

    def has_audio(self, cap: Capture) -> bool:
        return self.audio_path(cap).is_file()

    def load_original(self, cap: Capture) -> Image.Image:
        with Image.open(self.original_path(cap)) as im:
            return im.convert("RGB")

    def load_final(self, cap: Capture) -> Image.Image:
        with Image.open(self.final_path(cap)) as im:
            return im.convert("RGB")

    # ---- opérations ---------------------------------------------------------------
    def add(self, image: Image.Image) -> Capture:
        cap = Capture(self._next_id, created=datetime.now().isoformat(timespec="seconds"))
        self._next_id += 1
        (self.folder / "originales").mkdir(exist_ok=True)
        image.convert("RGB").save(self.original_path(cap))
        image.convert("RGB").save(self.final_path(cap))
        self.captures.append(cap)
        self.save()
        return cap

    def update(self, cap: Capture, base: Image.Image, final: Image.Image, items: list, caption: str) -> None:
        base.convert("RGB").save(self.original_path(cap))
        final.convert("RGB").save(self.final_path(cap))
        cap.items = items
        cap.caption = caption.strip()
        self.save()

    def remove(self, cap: Capture) -> None:
        for p in (self.final_path(cap), self.original_path(cap), self.audio_path(cap)):
            p.unlink(missing_ok=True)
        self.captures.remove(cap)
        self.save()

    def move(self, cap: Capture, delta: int) -> None:
        i = self.captures.index(cap)
        j = i + delta
        if 0 <= j < len(self.captures):
            self.captures[i], self.captures[j] = self.captures[j], self.captures[i]
            self.save()


def _fix_item(it: dict) -> dict:
    """JSON donne des listes ; le reste du code attend des tuples pour les points."""
    for k in ("p1", "p2", "pos"):
        if k in it:
            it[k] = tuple(it[k])
    if "points" in it:
        it["points"] = [tuple(p) for p in it["points"]]
    return it
