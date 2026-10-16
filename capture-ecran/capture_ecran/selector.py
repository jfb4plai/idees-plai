"""Sélection d'une zone sur l'image figée (le menu ouvert est déjà dans la capture)."""
from __future__ import annotations

import tkinter as tk

from PIL import Image, ImageEnhance, ImageTk

from . import winapi


def select_region(master: tk.Misc, image: Image.Image) -> Image.Image | None:
    """Affiche `image` plein écran, atténuée ; l'utilisateur trace un rectangle.
    Retourne l'extrait, ou None si annulé (Échap / clic droit / zone minuscule)."""
    vs = winapi.virtual_screen()
    left, top = (vs[0], vs[1]) if vs else (0, 0)
    w, h = image.size
    win = tk.Toplevel(master)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.geometry(f"{w}x{h}{left:+d}{top:+d}")
    canvas = tk.Canvas(win, width=w, height=h, highlightthickness=0, cursor="crosshair")
    canvas.pack()
    dim = ImageTk.PhotoImage(ImageEnhance.Brightness(image).enhance(0.45))
    canvas.create_image(0, 0, image=dim, anchor="nw")
    canvas.create_text(w // 2, 40, fill="white", font=("Segoe UI", 16, "bold"),
                       text="Tracez la zone à capturer  —  Échap pour annuler")
    state = {"start": None, "result": None, "crop": None, "rect": None}

    def press(e):
        state["start"] = (e.x, e.y)

    def drag(e):
        if not state["start"]:
            return
        x0, y0 = state["start"]
        box = (max(0, min(x0, e.x)), max(0, min(y0, e.y)), min(w, max(x0, e.x)), min(h, max(y0, e.y)))
        if box[2] - box[0] < 1 or box[3] - box[1] < 1:
            return
        state["crop"] = ImageTk.PhotoImage(image.crop(box))
        canvas.delete("sel")
        canvas.create_image(box[0], box[1], image=state["crop"], anchor="nw", tags="sel")
        canvas.create_rectangle(*box, outline="#FFD600", width=2, tags="sel")
        state["rect"] = box

    def release(e):
        box = state["rect"]
        if box and box[2] - box[0] >= 6 and box[3] - box[1] >= 6:
            state["result"] = image.crop(box)
        win.destroy()

    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", drag)
    canvas.bind("<ButtonRelease-1>", release)
    for seq in ("<Escape>", "<ButtonPress-3>"):
        win.bind(seq, lambda e: win.destroy())
        canvas.bind(seq, lambda e: win.destroy())
    win.update_idletasks()
    win.focus_force()
    canvas.focus_set()
    win.grab_set()
    master.wait_window(win)
    return state["result"]
