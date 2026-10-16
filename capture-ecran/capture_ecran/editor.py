"""Éditeur d'annotations : flèches, formes, texte, numéros d'étapes, masquage, recadrage."""
from __future__ import annotations

import copy
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from . import annotate, audio, winapi
from .session import Capture, Session

TOOLS = [  # clé, pictogramme, libellé, aide
    ("select", "☝", "Déplacer", "Cliquer sur un objet pour le déplacer (Suppr pour l'effacer)"),
    ("arrow", "➚", "Flèche", "Glisser de la queue vers la pointe"),
    ("rect", "▭", "Cadre", "Entourer une zone d'un cadre"),
    ("ellipse", "◯", "Ovale", "Entourer d'un ovale"),
    ("highlight", "▮", "Surligner", "Surligner une zone"),
    ("text", "T", "Texte", "Cliquer à l'endroit voulu, puis écrire"),
    ("step", "①", "Numéro", "Cliquer pour poser 1, 2, 3… (étapes)"),
    ("pen", "✎", "Crayon", "Dessiner à main levée"),
    ("blur", "▦", "Masquer", "Pixelliser une zone (prénoms, données personnelles)"),
    ("crop", "✂", "Recadrer", "Glisser pour garder seulement une zone"),
]
WIDTHS = {"Fin": (3, 22, 14), "Moyen": (6, 32, 20), "Épais": (10, 46, 28)}  # trait, texte, rayon du numéro


def ask_text(parent: tk.Misc, title: str, initial: str = "") -> str | None:
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.transient(parent)
    dlg.resizable(False, False)
    ttk.Label(dlg, text="Écrivez votre texte (Entrée = valider, Maj+Entrée = nouvelle ligne) :").pack(padx=12, pady=(12, 4))
    box = tk.Text(dlg, width=44, height=4, font=("Segoe UI", 12), wrap="word")
    box.pack(padx=12)
    box.insert("1.0", initial)
    out: dict[str, str | None] = {"v": None}

    def ok(_=None):
        out["v"] = box.get("1.0", "end").strip()
        dlg.destroy()
        return "break"

    box.bind("<Return>", ok)
    row = ttk.Frame(dlg)
    row.pack(pady=10)
    ttk.Button(row, text="OK", command=ok).pack(side="left", padx=6)
    ttk.Button(row, text="Annuler", command=dlg.destroy).pack(side="left", padx=6)
    box.focus_set()
    dlg.grab_set()
    parent.wait_window(dlg)
    return out["v"] or None


class Editor(tk.Toplevel):
    def __init__(self, master, session: Session, cap: Capture, on_close=None, recorder=None):
        super().__init__(master)
        self.recorder = recorder if recorder is not None else audio.make_recorder()
        self.recording = False
        self.session, self.cap, self.on_close = session, cap, on_close
        self.base = session.load_original(cap)
        self.items: list[dict] = copy.deepcopy(cap.items)
        self.undo_stack: list[tuple] = []
        self.redo_stack: list[tuple] = []
        self.draft: dict | None = None
        self.selected: int | None = None
        self.drag_last = None
        self._moved = False
        self.scale, self.offset = 1.0, (0, 0)
        self.base_view = self.base
        self._cache: Image.Image | None = None
        self._photo = None
        self._fit_job = None
        self.dirty = False
        self.color = annotate.PALETTE["Rouge"]
        self.tool = tk.StringVar(value="arrow")
        self.width_name = tk.StringVar(value="Moyen")
        self.caption = tk.StringVar(value=cap.caption)

        self.title(f"Modifier la capture {session.captures.index(cap) + 1}")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{int(sw * 0.85)}x{int(sh * 0.85)}+{int(sw * 0.075)}+{int(sh * 0.04)}")
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Delete>", lambda e: self.delete_selected())
        self.bind("<Control-s>", lambda e: self.save_and_close())
        self.bind("<Control-c>", lambda e: self.copy_clip())
        self.after(50, self.lift)
        self.after(80, self.focus_force)

    # ------------------------------------------------------------------ interface
    def _build_ui(self):
        top = ttk.Frame(self, padding=4)
        top.pack(fill="x")
        for key, glyph, label, tip in TOOLS:
            b = tk.Radiobutton(top, text=f"{glyph}\n{label}", variable=self.tool, value=key, indicatoron=False,
                               width=8, font=("Segoe UI", 10), selectcolor="#BBDEFB", pady=3,
                               command=self._tool_changed)
            b.pack(side="left", padx=1)
            _Tip(b, tip)
        row2 = ttk.Frame(self, padding=(4, 0, 4, 4))
        row2.pack(fill="x")
        ttk.Label(row2, text="Couleur :").pack(side="left")
        self.swatches = {}
        for name, hexv in annotate.PALETTE.items():
            sw = tk.Button(row2, bg=hexv, activebackground=hexv, width=3, relief="raised",
                           command=lambda h=hexv: self._set_color(h))
            sw.pack(side="left", padx=2)
            _Tip(sw, name)
            self.swatches[hexv] = sw
        self._set_color(self.color)
        ttk.Label(row2, text="   Taille :").pack(side="left")
        for name in WIDTHS:
            tk.Radiobutton(row2, text=name, variable=self.width_name, value=name, indicatoron=False,
                           padx=8).pack(side="left", padx=1)
        ttk.Separator(row2, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(row2, text="↶ Annuler", command=self.undo).pack(side="left", padx=2)
        ttk.Button(row2, text="↷ Rétablir", command=self.redo).pack(side="left", padx=2)
        ttk.Button(row2, text="🗑 Supprimer l'objet", command=self.delete_selected).pack(side="left", padx=2)

        bottom = ttk.Frame(self, padding=(6, 4))
        bottom.pack(side="bottom", fill="x")
        voice_row = ttk.Frame(bottom)
        voice_row.pack(fill="x", pady=(0, 4))
        self.rec_btn = ttk.Button(voice_row, text="🎙 Enregistrer ma voix", command=self.toggle_record)
        self.rec_btn.pack(side="left", padx=2)
        self.play_btn = ttk.Button(voice_row, text="▶ Écouter", command=self.play_voice)
        self.play_btn.pack(side="left", padx=2)
        self.del_btn = ttk.Button(voice_row, text="✖ Effacer la voix", command=self.delete_voice)
        self.del_btn.pack(side="left", padx=2)
        self.voice_lbl = ttk.Label(voice_row, text="", foreground="#555")
        self.voice_lbl.pack(side="left", padx=8)
        if self.recorder is None:
            for b in (self.rec_btn, self.play_btn, self.del_btn):
                b.state(["disabled"])
            self.voice_lbl.config(text="(voix off disponible sous Windows)")
        else:
            self._update_voice_label()
        cap_row = ttk.Frame(bottom)
        cap_row.pack(fill="x")
        ttk.Label(cap_row, text="Légende (sous-titre de la vidéo, facultatif) :").pack(side="left")
        ttk.Entry(cap_row, textvariable=self.caption).pack(side="left", padx=6, fill="x", expand=True)
        btn_row = ttk.Frame(bottom)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="✔ Enregistrer et fermer", command=self.save_and_close).pack(side="right", padx=2)
        ttk.Button(btn_row, text="Fermer sans enregistrer", command=self._cancel).pack(side="right", padx=2)
        ttk.Button(btn_row, text="Ouvrir dans Paint", command=self.open_in_paint).pack(side="right", padx=2)
        ttk.Button(btn_row, text="Copier l'image", command=self.copy_clip).pack(side="right", padx=2)

        self.status = ttk.Label(self, text=TOOLS[1][3], anchor="w", padding=(6, 0), wraplength=1000)
        self.status.pack(side="bottom", fill="x")
        self.canvas = tk.Canvas(self, bg="#3a3a3a", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.img_id = self.canvas.create_image(0, 0, anchor="nw")
        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)

    def _tool_changed(self):
        tip = next(t[3] for t in TOOLS if t[0] == self.tool.get())
        self.status.config(text=tip)
        self.selected = None
        self.canvas.config(cursor="fleur" if self.tool.get() == "select" else "crosshair")
        self._refresh()

    def _set_color(self, hexv: str):
        self.color = hexv
        for h, b in getattr(self, "swatches", {}).items():
            b.config(relief="sunken" if h == hexv else "raised", bd=4 if h == hexv else 2)

    # ------------------------------------------------------------------ affichage
    def _on_configure(self, _=None):
        if self._fit_job:
            self.after_cancel(self._fit_job)
        self._fit_job = self.after(120, self._fit)

    def _fit(self):
        self._fit_job = None
        cw, ch = max(50, self.canvas.winfo_width()), max(50, self.canvas.winfo_height())
        iw, ih = self.base.size
        self.scale = min((cw - 20) / iw, (ch - 20) / ih, 1.0)
        vw, vh = max(1, int(iw * self.scale)), max(1, int(ih * self.scale))
        self.base_view = self.base.resize((vw, vh), Image.LANCZOS) if self.scale < 1 else self.base
        self.offset = ((cw - vw) // 2, (ch - vh) // 2)
        self.canvas.coords(self.img_id, *self.offset)
        self._cache = None
        self._refresh()

    def _refresh(self):
        if self._cache is None:
            self._cache = annotate.render(self.base_view, self.items, self.scale)
        img = self._cache
        if self.draft and self.draft["type"] != "crop":
            img = annotate.render_over(img.copy(), [self.draft], self.scale)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.itemconfig(self.img_id, image=self._photo)
        self.canvas.delete("overlay")
        ox, oy = self.offset
        if self.draft and self.draft["type"] == "crop":
            x0, y0, x1, y1 = annotate.norm_box(self.draft["p1"], self.draft["p2"])
            self.canvas.create_rectangle(ox + x0 * self.scale, oy + y0 * self.scale, ox + x1 * self.scale,
                                         oy + y1 * self.scale, outline="#FFD600", width=2, dash=(6, 4), tags="overlay")
        if self.selected is not None and self.selected < len(self.items):
            x0, y0, x1, y1 = annotate.item_bbox(self.items[self.selected])
            self.canvas.create_rectangle(ox + x0 * self.scale, oy + y0 * self.scale, ox + x1 * self.scale,
                                         oy + y1 * self.scale, outline="#00B0FF", width=2, dash=(4, 3), tags="overlay")

    def _invalidate(self):
        self._cache = None
        self._refresh()

    # ------------------------------------------------------------------ souris
    def _to_img(self, e):
        x = (e.x - self.offset[0]) / self.scale
        y = (e.y - self.offset[1]) / self.scale
        return (min(max(x, 0), self.base.width), min(max(y, 0), self.base.height))

    def _style(self):
        w, tsize, radius = WIDTHS[self.width_name.get()]
        return {"color": self.color, "width": w}, tsize, radius

    def _press(self, e):
        self.canvas.focus_set()
        pt = self._to_img(e)
        t = self.tool.get()
        style, tsize, radius = self._style()
        if t == "select":
            self.selected = next((i for i in range(len(self.items) - 1, -1, -1)
                                  if annotate.hit_test(self.items[i], pt, 8 / self.scale)), None)
            self.drag_last, self._moved = pt, False
            self._refresh()
        elif t == "text":
            txt = ask_text(self, "Texte")
            if txt:
                self._add({"type": "text", "pos": pt, "text": txt, "size": tsize, "color": self.color})
        elif t == "step":
            n = sum(1 for i in self.items if i["type"] == "step") + 1
            self._add({"type": "step", "pos": pt, "number": n, "radius": radius, "color": self.color})
        elif t == "pen":
            self.draft = {"type": "pen", "points": [pt], **style}
        else:
            self.draft = {"type": t, "p1": pt, "p2": pt, **style}

    def _drag(self, e):
        pt = self._to_img(e)
        if self.tool.get() == "select":
            if self.selected is not None and self.drag_last:
                if not self._moved:
                    self._snapshot()
                    self._moved = True
                dx, dy = pt[0] - self.drag_last[0], pt[1] - self.drag_last[1]
                self.items[self.selected] = annotate.translate(self.items[self.selected], dx, dy)
                self.drag_last = pt
                self._invalidate()
            return
        if not self.draft:
            return
        if self.draft["type"] == "pen":
            self.draft["points"].append(pt)
        else:
            self.draft["p2"] = pt
            if e.state & 0x1 and self.draft["type"] in ("arrow", "rect", "ellipse", "highlight", "blur"):
                self._constrain(self.draft)  # Maj : angle à 45° / carré parfait
        self._refresh()

    @staticmethod
    def _constrain(d):
        (x0, y0), (x1, y1) = d["p1"], d["p2"]
        dx, dy = x1 - x0, y1 - y0
        if d["type"] == "arrow":
            if abs(dx) > 2 * abs(dy):
                d["p2"] = (x1, y0)
            elif abs(dy) > 2 * abs(dx):
                d["p2"] = (x0, y1)
            else:
                m = max(abs(dx), abs(dy))
                d["p2"] = (x0 + m * (1 if dx >= 0 else -1), y0 + m * (1 if dy >= 0 else -1))
        else:
            m = max(abs(dx), abs(dy))
            d["p2"] = (x0 + m * (1 if dx >= 0 else -1), y0 + m * (1 if dy >= 0 else -1))

    def _release(self, e):
        d, self.draft = self.draft, None
        if self.tool.get() == "select" or not d:
            return
        if d["type"] == "pen":
            if len(d["points"]) >= 2:
                self._add(d)
            else:
                self._refresh()
            return
        if abs(d["p2"][0] - d["p1"][0]) < 4 and abs(d["p2"][1] - d["p1"][1]) < 4:
            self._refresh()
            return
        if d["type"] == "crop":
            self._crop(d)
        else:
            self._add(d)

    # ------------------------------------------------------------------ historique
    def _snapshot(self):
        self.undo_stack.append((self.base, copy.deepcopy(self.items)))
        self.redo_stack.clear()
        self.dirty = True

    def _add(self, item):
        self._snapshot()
        self.items.append(item)
        self.selected = None
        self._invalidate()

    def _crop(self, d):
        x0, y0, x1, y1 = (int(v) for v in annotate.norm_box(d["p1"], d["p2"]))
        self._snapshot()
        self.base = self.base.crop((x0, y0, x1, y1))
        self.items = [annotate.translate(i, -x0, -y0) for i in self.items]
        self.selected = None
        self._fit()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append((self.base, copy.deepcopy(self.items)))
            self._restore(self.undo_stack.pop())

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append((self.base, copy.deepcopy(self.items)))
            self._restore(self.redo_stack.pop())

    def _restore(self, state):
        size_before = self.base.size
        self.base, self.items = state
        self.selected = None
        self.dirty = True
        if self.base.size != size_before:
            self._fit()
        else:
            self._invalidate()

    def delete_selected(self):
        if self.selected is not None and self.selected < len(self.items):
            self._snapshot()
            del self.items[self.selected]
            self.selected = None
            self._invalidate()

    # ------------------------------------------------------------------ voix off
    def _update_voice_label(self):
        has = self.session.has_audio(self.cap)
        if self.recording:
            self.voice_lbl.config(text="● Enregistrement… lisez votre légende, puis cliquez sur « Arrêter »")
        elif has:
            secs = audio.wav_duration(self.session.audio_path(self.cap))
            self.voice_lbl.config(text=f"Voix enregistrée : {secs:.1f} s")
        else:
            self.voice_lbl.config(text="Pas de voix pour cette capture")
        self.play_btn.state(["!disabled"] if has and not self.recording else ["disabled"])
        self.del_btn.state(["!disabled"] if has and not self.recording else ["disabled"])

    def toggle_record(self):
        if self.recorder is None:
            return
        if not self.recording:
            audio.stop_play()
            try:
                self.recorder.start()
            except audio.AudioError as e:
                messagebox.showerror("Micro", str(e), parent=self)
                return
            self.recording = True
            self.rec_btn.config(text="⏹ Arrêter")
            self.status.config(text="Dites : « " + (self.caption.get().strip() or "…") + " »")
        else:
            self._stop_recording()
        self._update_voice_label()

    def _stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        self.rec_btn.config(text="🎙 Enregistrer ma voix")
        try:
            self.recorder.stop(self.session.audio_path(self.cap))
            self.status.config(text="Voix enregistrée : cliquez sur « Écouter » pour la vérifier.")
        except audio.AudioError as e:
            messagebox.showerror("Micro", str(e), parent=self)

    def play_voice(self):
        if self.session.has_audio(self.cap):
            audio.play(self.session.audio_path(self.cap))

    def delete_voice(self):
        audio.stop_play()
        self.session.audio_path(self.cap).unlink(missing_ok=True)
        self._update_voice_label()

    # ------------------------------------------------------------------ sortie
    def _final(self) -> Image.Image:
        return annotate.render(self.base, self.items, 1.0)

    def _save(self) -> Image.Image:
        final = self._final()
        self.session.update(self.cap, self.base, final, copy.deepcopy(self.items), self.caption.get())
        self.dirty = False
        return final

    def _close(self):
        self._stop_recording()
        audio.stop_play()
        self.destroy()
        if self.on_close:
            self.on_close()

    def save_and_close(self):
        self._save()
        self._close()

    def _cancel(self):
        if self.dirty or self.caption.get().strip() != self.cap.caption:
            ans = messagebox.askyesnocancel("Enregistrer ?", "Enregistrer les modifications de cette capture ?",
                                            parent=self)
            if ans is None:
                return
            if ans:
                self._save()
        self._close()

    def copy_clip(self):
        if winapi.copy_image_to_clipboard(self._final()):
            self.status.config(text="Image copiée : vous pouvez la coller (Ctrl+V) dans Word, Teams, un mail…")
        else:
            self.status.config(text="Copie dans le presse-papiers disponible uniquement sous Windows.")

    def open_in_paint(self):
        """Les annotations sont « aplaties » dans l'image, puis Paint prend le relais."""
        final = self._final()
        self.session.update(self.cap, final, final, [], self.caption.get())
        path = str(self.session.final_path(self.cap))
        self._close()
        launch_paint(path)


def launch_paint(path: str) -> None:
    try:
        if sys.platform == "win32":
            subprocess.Popen(["mspaint.exe", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError:
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception:
            messagebox.showerror("Paint", "Impossible d'ouvrir Paint. Ouvrez le fichier manuellement :\n" + path)


class _Tip:
    """Info-bulle minimale."""

    def __init__(self, widget, text):
        self.w, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _):
        x, y = self.w.winfo_rootx() + 10, self.w.winfo_rooty() + self.w.winfo_height() + 4
        self.tip = tk.Toplevel(self.w)
        self.tip.overrideredirect(True)
        self.tip.geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg="#FFFFE0", relief="solid", bd=1, padx=4).pack()

    def _hide(self, _):
        if self.tip:
            self.tip.destroy()
            self.tip = None
