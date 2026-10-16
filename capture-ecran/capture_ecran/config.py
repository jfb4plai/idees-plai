"""Préférences de l'utilisateur (fichier JSON dans le profil, jamais dans le dossier du programme)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    "hotkey_full": "ctrl+shift+f9",
    "hotkey_region": "ctrl+shift+f10",
    "hotkey_window": "ctrl+shift+f11",
    "hotkey_steps": "ctrl+shift+f12",
    "steps_moment": "avant",     # avant | apres
    "draw_cursor": True,
    "click_halo": True,
    "copy_clipboard": True,
    "after_capture": "editor",   # editor | paint | none
    "base_dir": "",
}


def config_path() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home()))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "CaptureEcranPLAI" / "config.json"


def default_base_dir() -> Path:
    pictures = Path.home() / "Pictures"
    return (pictures if pictures.is_dir() else Path.home()) / "Captures PLAI"


def load(path: Path | None = None) -> dict:
    path = path or config_path()
    cfg = dict(DEFAULTS)
    try:
        cfg.update({k: v for k, v in json.loads(path.read_text("utf-8")).items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    if not cfg["base_dir"]:
        cfg["base_dir"] = str(default_base_dir())
    return cfg


def save(cfg: dict, path: Path | None = None) -> None:
    path = path or config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), "utf-8")
    except OSError:
        pass
