"""Fenêtre principale : déclenche les captures, liste la série, lance les exports."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageTk

from . import APP_NAME, __version__, config, exporter, grabber, steps, winapi
from .editor import Editor, launch_paint
from .hotkeys import HotkeyListener, parse_hotkey, pretty
from .selector import select_region
from .session import Session

MODES = {"full": "Écran entier", "region": "Zone", "window": "Fenêtre active", "steps": "Série de clics"}


class App(tk.Tk):
    def __init__(self):
        winapi.set_dpi_aware()
        super().__init__()
        self.title(f"{APP_NAME} {__version__}")
        self.geometry("740x780")
        self.minsize(700, 700)
        self.cfg = config.load()
        self.session: Session | None = None
        self.busy = False
        self.events: queue.Queue[str] = queue.Queue()
        self.listener: HotkeyListener | None = None
        self.recorder: steps.StepRecorder | None = None
        self.frames: steps.FrameBuffer | None = None
        self.hook: winapi.MouseHook | None = None
        self.clicks: queue.Queue = queue.Queue()
        self._thumb = None
        self._build_ui()
        self._start_hotkeys()
        self.after(100, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._quit)

    # ------------------------------------------------------------------ interface
    def _build_ui(self):
        pad = {"padx": 10, "pady": 4}
        head = ttk.Frame(self)
        head.pack(fill="x", **pad)
        self.hint = ttk.Label(head, justify="left", font=("Segoe UI", 10), wraplength=700)
        self.hint.pack(anchor="w")

        btns = ttk.LabelFrame(self, text=" Prendre une capture ")
        btns.pack(fill="x", **pad)
        for col, (text, cmd) in enumerate([("📷  Écran entier", lambda: self.request("full")),
                                           ("✂  Zone", lambda: self.request("region")),
                                           ("🪟  Fenêtre active", lambda: self.request("window")),
                                           ("⏱  Dans 3 secondes", lambda: self.request("full", delay=3))]):
            ttk.Button(btns, text=text, command=cmd).grid(row=0, column=col, padx=4, pady=6, sticky="ew")
            btns.columnconfigure(col, weight=1)
        self.steps_btn = ttk.Button(btns, text="●  Enregistrer mes clics (une capture numérotée par clic)",
                                    command=lambda: self.request("steps"))
        self.steps_btn.grid(row=1, column=0, columnspan=4, padx=4, pady=(0, 2), sticky="ew")
        self.v_moment = tk.StringVar(value=self.cfg["steps_moment"])
        mrow = ttk.Frame(btns)
        mrow.grid(row=2, column=0, columnspan=4, pady=(0, 4))
        ttk.Label(mrow, text="Image prise :").pack(side="left")
        for val, txt in (("avant", "juste avant le clic (recommandé)"), ("apres", "0,5 s après le clic")):
            ttk.Radiobutton(mrow, text=txt, value=val, variable=self.v_moment,
                            command=self._save_opts).pack(side="left", padx=6)

        opts = ttk.LabelFrame(self, text=" Options ")
        opts.pack(fill="x", **pad)
        self.v_cursor = tk.BooleanVar(value=self.cfg["draw_cursor"])
        self.v_halo = tk.BooleanVar(value=self.cfg["click_halo"])
        self.v_clip = tk.BooleanVar(value=self.cfg["copy_clipboard"])
        self.v_after = tk.StringVar(value=self.cfg["after_capture"])
        ttk.Checkbutton(opts, text="Montrer le pointeur de la souris", variable=self.v_cursor,
                        command=self._save_opts).grid(row=0, column=0, sticky="w", padx=8)
        ttk.Checkbutton(opts, text="Entourer le pointeur d'un halo jaune", variable=self.v_halo,
                        command=self._save_opts).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Checkbutton(opts, text="Copier aussi dans le presse-papiers (Ctrl+V)", variable=self.v_clip,
                        command=self._save_opts).grid(row=1, column=0, columnspan=2, sticky="w", padx=8)
        ttk.Label(opts, text="Après la capture :").grid(row=2, column=0, sticky="w", padx=8, pady=(4, 0))
        fr = ttk.Frame(opts)
        fr.grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))
        for val, txt in (("editor", "Ouvrir l'éditeur"), ("paint", "Ouvrir Paint"), ("none", "Rien (juste enregistrer)")):
            ttk.Radiobutton(fr, text=txt, value=val, variable=self.v_after, command=self._save_opts).pack(side="left", padx=6)

        serie = ttk.LabelFrame(self, text=" Ma série de captures ")
        serie.pack(fill="both", expand=True, **pad)
        self.title_lbl = ttk.Label(serie, text="(aucune série pour l'instant)", font=("Segoe UI", 10, "bold"))
        self.title_lbl.pack(anchor="w", padx=8, pady=(4, 0))
        mid = ttk.Frame(serie)
        mid.pack(fill="both", expand=True, padx=8, pady=4)
        self.listbox = tk.Listbox(mid, height=5, activestyle="dotbox", font=("Segoe UI", 10), exportselection=False)
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda e: self.edit_selected())
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._show_thumb())
        self.thumb_lbl = ttk.Label(mid, text="Aperçu", anchor="center", width=30)
        self.thumb_lbl.pack(side="left", padx=(8, 0), fill="y")
        row = ttk.Frame(serie)
        row.pack(fill="x", padx=8, pady=(0, 6))
        for text, cmd in [("✎ Modifier", self.edit_selected), ("▲", lambda: self.move(-1)), ("▼", lambda: self.move(1)),
                          ("🗑 Supprimer", self.delete_selected), ("📁 Dossier", self.open_folder),
                          ("Nouvelle série", self.new_session), ("Rouvrir…", self.open_session),
                          ("↻ Renuméroter", self.renumber)]:
            ttk.Button(row, text=text, command=cmd, width=3 if text in "▲▼" else None).pack(side="left", padx=2)

        out = ttk.LabelFrame(self, text=" Créer à partir de la série ")
        out.pack(fill="x", **pad)
        ttk.Button(out, text="🎬 Vidéo", command=self.export_video).pack(side="left", padx=4, pady=6)
        ttk.Button(out, text="📝 Document Word", command=self.export_word).pack(side="left", padx=4)
        ttk.Button(out, text="📄 Fiche HTML/PDF", command=self.export_html).pack(side="left", padx=4)
        ttk.Button(out, text="⚙ Réglages…", command=self.settings).pack(side="right", padx=4)

        self.status = ttk.Label(self, text="Prêt.", anchor="w", relief="sunken", padding=(6, 2), wraplength=700)
        self.status.pack(fill="x", side="bottom")

    def _refresh_hint(self):
        k = self.cfg
        txt = (f"1. Ouvrez votre menu déroulant, puis 2. appuyez sur :\n"
               f"   {pretty(k['hotkey_full'])} écran entier   •   {pretty(k['hotkey_region'])} zone   •   "
               f"{pretty(k['hotkey_window'])} fenêtre\n"
               f"   {pretty(k['hotkey_steps'])} démarrer / arrêter la série de clics   (portable : + touche Fn)")
        self.hint.config(text=txt)

    def _save_opts(self):
        self.cfg.update(draw_cursor=self.v_cursor.get(), click_halo=self.v_halo.get(),
                        copy_clipboard=self.v_clip.get(), after_capture=self.v_after.get(),
                        steps_moment=self.v_moment.get())
        config.save(self.cfg)

    def say(self, text: str):
        self.status.config(text=text)

    # ------------------------------------------------------------------ raccourcis
    def _start_hotkeys(self):
        if self.listener:
            self.listener.stop()
        self.listener = HotkeyListener(
            {"full": self.cfg["hotkey_full"], "region": self.cfg["hotkey_region"],
             "window": self.cfg["hotkey_window"], "steps": self.cfg["hotkey_steps"]}, self.events.put)
        self.listener.start()
        self.listener.ready.wait(2)
        self._refresh_hint()
        if self.listener.errors:
            self.say("⚠ " + " ; ".join(f"{MODES[k]} : {v}" for k, v in self.listener.errors.items()))

    def _poll(self):
        self._drain_clicks()
        try:
            while True:
                self.request(self.events.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._poll)

    # ------------------------------------------------------------------ série de clics
    def toggle_steps(self):
        if self.recorder:
            self.stop_steps()
        elif not self.busy:
            self.start_steps()

    def start_steps(self):
        if self.session and self.session.captures:
            ans = messagebox.askyesnocancel(
                APP_NAME, "Ajouter les clics à la série en cours ?\n\nOui = à la suite\nNon = nouvelle série", parent=self)
            if ans is None:
                return
            if not ans:
                self.session = None
        if self.session is None:
            self.session = Session.new(Path(self.cfg["base_dir"]))
            self.title_lbl.config(text=self.session.title)
        self.hook = winapi.MouseHook(self._hook_click)
        if not self.hook.start():
            messagebox.showerror(APP_NAME, self.hook.error)
            self.hook = None
            return
        vs = winapi.virtual_screen()
        self.recorder = steps.StepRecorder(self.session, (vs[0], vs[1]) if vs else (0, 0), self.v_cursor.get())
        self.frames = None
        if self.v_moment.get() == "avant":
            self.frames = steps.FrameBuffer()
            self.frames.start()
        self._was_visible = self.state() == "normal"
        self.iconify()
        self.title(f"● Enregistrement des clics — {pretty(self.cfg['hotkey_steps'])} pour arrêter")
        winapi.beep()

    def _hook_click(self, button: str, x: int, y: int):
        """Thread du hook, avant que l'application ne reçoive le clic : rester ultra rapide."""
        if winapi.foreground_is_own_process():
            return
        frame = self.frames.latest if self.frames else None
        self.clicks.put((button, (x, y), frame, time.monotonic()))

    def _drain_clicks(self):
        while True:
            try:
                button, pos, frame, t = self.clicks.get_nowait()
            except queue.Empty:
                return
            if not self.recorder or self.busy:
                continue
            if frame is None:  # mode « après » : on attend le résultat du clic
                self.after(500, lambda b=button, p=pos, tt=t: self._click_after(b, p, tt))
            else:
                self._record_click(button, pos, frame, t)

    def _click_after(self, button, pos, t):
        if self.recorder:
            frame, _ = grabber.grab_screen(draw_cursor=False)
            self._record_click(button, pos, frame, t)

    def _record_click(self, button, pos, frame, t):
        try:
            self.recorder.on_click(button, pos, frame, t)
            winapi.beep()
            self.title(f"● {self.recorder.count} clic(s) — {pretty(self.cfg['hotkey_steps'])} pour arrêter")
        except Exception as e:
            self.say("Erreur pendant l'enregistrement d'un clic : " + str(e))

    def stop_steps(self):
        rec, self.recorder = self.recorder, None
        if self.hook:
            self.hook.stop()
            self.hook = None
        if self.frames:
            self.frames.stop()
            self.frames = None
        while not self.clicks.empty():
            self.clicks.get_nowait()
        self.title(f"{APP_NAME} {__version__}")
        self.deiconify()
        self._fill_list(select=len(self.session.captures) - 1 if self.session and self.session.captures else None)
        n = rec.count if rec else 0
        self.say(f"{n} étape(s) enregistrée(s). Double-cliquez une ligne pour l'améliorer (légende, flèches, voix).")
        winapi.beep()

    def renumber(self):
        if not (self.session and self.session.captures):
            return
        n = steps.renumber_steps(self.session)
        self._fill_list(keep=True)
        self.say(f"{n} pastille(s) renumérotée(s)." if n else "Les numéros sont déjà dans le bon ordre.")

    # ------------------------------------------------------------------ capture
    def request(self, mode: str, delay: int = 0):
        if mode == "steps":
            self.toggle_steps()
            return
        if self.recorder:
            self.say("Une série de clics est en cours : arrêtez-la d'abord.")
            return
        if self.busy:
            self.say("Terminez d'abord l'action en cours (éditeur ou sélection ouvert).")
            return
        self.busy = True
        self._was_visible = self.state() == "normal"
        if delay:
            self.iconify()
            self._countdown(mode, delay)
        else:
            if self._was_visible:
                self.withdraw()  # pour que notre fenêtre n'apparaisse pas dans la capture
            self.after(250 if self._was_visible else 30, lambda: self._capture(mode))

    def _countdown(self, mode: str, n: int):
        if n == 0:
            self.title(f"{APP_NAME} {__version__}")
            self.after(150, lambda: self._capture(mode))
            return
        self.title(f"Capture dans {n}…")
        self.bell()
        self.after(1000, lambda: self._countdown(mode, n - 1))

    def _capture(self, mode: str):
        try:
            img, _ = grabber.grab_screen(self.v_cursor.get(), self.v_halo.get())
            if mode == "window":
                img = self._crop_window(img)
            elif mode == "region":
                img = select_region(self, img)
            if img is None:
                self._finish("Capture annulée.")
                return
            winapi.beep()
            if self.v_clip.get():
                winapi.copy_image_to_clipboard(img)
            if self.session is None:
                self.session = Session.new(Path(self.cfg["base_dir"]))
                self.title_lbl.config(text=self.session.title)
            cap = self.session.add(img)
            self._fill_list(select=len(self.session.captures) - 1)
            after = self.v_after.get()
            if after == "editor":
                Editor(self, self.session, cap, on_close=lambda: self._finish(f"Capture {cap.id} enregistrée."))
                return
            if after == "paint":
                launch_paint(str(self.session.final_path(cap)))
            self._finish(f"Capture {cap.id} enregistrée dans {self.session.folder}")
        except Exception as e:  # une capture ratée ne doit jamais fermer le programme
            self._finish("Erreur : " + str(e))
            messagebox.showerror(APP_NAME, f"La capture a échoué :\n{e}")

    def _crop_window(self, img):
        vs = winapi.virtual_screen()
        return grabber.crop_active_window(img, (vs[0], vs[1]) if vs else (0, 0))

    def _finish(self, msg: str):
        self.busy = False
        if getattr(self, "_was_visible", True):
            self.deiconify()
        self._fill_list(keep=True)
        self.say(msg)

    # ------------------------------------------------------------------ série
    def _fill_list(self, select: int | None = None, keep: bool = False):
        cur = self.listbox.curselection()
        self.listbox.delete(0, "end")
        if not self.session:
            return
        for i, c in enumerate(self.session.captures, start=1):
            self.listbox.insert("end", f"{i}.  {c.caption or '(sans légende)'}")
        idx = select if select is not None else (cur[0] if keep and cur else None)
        if idx is not None and idx < self.listbox.size():
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
        self._show_thumb()

    def _selected(self):
        sel = self.listbox.curselection()
        if not (self.session and sel):
            self.say("Sélectionnez d'abord une capture dans la liste.")
            return None
        return self.session.captures[sel[0]]

    def _show_thumb(self):
        sel = self.listbox.curselection()
        if not (self.session and sel):
            self.thumb_lbl.config(image="", text="Aperçu")
            return
        try:
            im = self.session.load_final(self.session.captures[sel[0]])
            im.thumbnail((240, 150))
            self._thumb = ImageTk.PhotoImage(im)
            self.thumb_lbl.config(image=self._thumb, text="")
        except OSError:
            self.thumb_lbl.config(image="", text="(image introuvable)")

    def edit_selected(self):
        cap = self._selected()
        if cap and not self.busy:
            self.busy, self._was_visible = True, True
            Editor(self, self.session, cap, on_close=lambda: self._finish("Modification enregistrée."))

    def delete_selected(self):
        cap = self._selected()
        if cap and messagebox.askyesno(APP_NAME, "Supprimer cette capture définitivement ?"):
            self.session.remove(cap)
            self._fill_list()

    def move(self, delta: int):
        cap = self._selected()
        if cap:
            i = self.session.captures.index(cap)
            self.session.move(cap, delta)
            self._fill_list(select=max(0, min(len(self.session.captures) - 1, i + delta)))

    def new_session(self):
        title = simpledialog.askstring(APP_NAME, "Titre de la nouvelle série (ex. : Créer un compte ENT) :", parent=self)
        if title is None:
            return
        self.session = Session.new(Path(self.cfg["base_dir"]), title.strip())
        self.session.title = title.strip() or "Ma série de captures"
        self.session.save()
        self.title_lbl.config(text=self.session.title)
        self._fill_list()
        self.say(f"Nouvelle série : {self.session.folder}")

    def open_session(self):
        d = filedialog.askdirectory(initialdir=self.cfg["base_dir"], title="Choisir le dossier d'une série")
        if not d:
            return
        try:
            self.session = Session.open(Path(d))
        except (OSError, ValueError):
            messagebox.showerror(APP_NAME, "Ce dossier ne contient pas de série (fichier session.json manquant).")
            return
        self.title_lbl.config(text=self.session.title)
        self._fill_list()

    def open_folder(self):
        folder = self.session.folder if self.session else Path(self.cfg["base_dir"])
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(folder)])

    # ------------------------------------------------------------------ exports
    def _need_session(self) -> bool:
        if self.session and self.session.captures:
            return True
        messagebox.showinfo(APP_NAME, "Prenez d'abord au moins une capture.")
        return False

    def export_video(self):
        if not self._need_session():
            return
        missing = [i for i, c in enumerate(self.session.captures, 1) if not c.caption.strip()]
        if missing and not messagebox.askyesno(
                APP_NAME, f"{len(missing)} capture(s) n'ont pas de légende (sous-titre) : {', '.join(map(str, missing))}.\n"
                          "Les écrans sans légende seront montrés sans sous-titre.\nContinuer ?"):
            return
        out = self.session.folder / "video"
        self.say("Création de la vidéo en cours…")
        self.update_idletasks()
        try:
            res = exporter.export_video_pack(self.session, out)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Échec de l'export : {e}")
            return
        self.say(res.message)
        messagebox.showinfo(APP_NAME, f"{res.message}\n\nDossier : {out}\n"
                                      f"• {len(res.frames)} images 1920×1080 avec sous-titres incrustés\n"
                                      "• soustitres.srt\n" + ("• voixoff.wav (votre voix)\n" if res.voice else "")
                                      + ("• video.mp4\n" if res.mp4 else ""))
        self._open(out)

    def export_word(self):
        if not self._need_session():
            return
        try:
            path = exporter.export_docx(self.session, self.session.folder / "document.docx")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Échec de l'export Word : {e}")
            return
        self.say(f"Document créé : {path}")
        self._open(path)

    def export_html(self):
        if not self._need_session():
            return
        path = exporter.export_html_guide(self.session, self.session.folder / "fiche_pas_a_pas.html")
        self.say(f"Fiche créée : {path}")
        self._open(path)

    @staticmethod
    def _open(path):
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError:
            pass

    # ------------------------------------------------------------------ réglages
    def settings(self):
        dlg = tk.Toplevel(self)
        dlg.title("Raccourcis clavier et dossier")
        dlg.transient(self)
        dlg.grab_set()
        fields = {}
        rows = [("hotkey_full", "Écran entier"), ("hotkey_region", "Zone"), ("hotkey_window", "Fenêtre active"),
                ("hotkey_steps", "Série de clics (début/fin)")]
        ttk.Label(dlg, text="Format : ctrl+maj+f9   (évitez Ctrl+Alt = AltGr du clavier belge)").grid(
            row=0, column=0, columnspan=2, padx=10, pady=8)
        for i, (key, label) in enumerate(rows, start=1):
            ttk.Label(dlg, text=label + " :").grid(row=i, column=0, sticky="e", padx=8, pady=3)
            v = tk.StringVar(value=self.cfg[key].replace("shift", "maj"))
            ttk.Entry(dlg, textvariable=v, width=22).grid(row=i, column=1, padx=8)
            fields[key] = v
        ttk.Label(dlg, text="Dossier des captures :").grid(row=5, column=0, sticky="e", padx=8, pady=8)
        vdir = tk.StringVar(value=self.cfg["base_dir"])
        ttk.Entry(dlg, textvariable=vdir, width=40).grid(row=5, column=1, padx=8)
        ttk.Button(dlg, text="Parcourir…",
                   command=lambda: vdir.set(filedialog.askdirectory(initialdir=vdir.get()) or vdir.get())
                   ).grid(row=5, column=2, padx=4)

        def apply():
            for key, v in fields.items():
                try:
                    parse_hotkey(v.get())
                except ValueError as e:
                    messagebox.showerror(APP_NAME, f"{dict(rows)[key]} : {e}", parent=dlg)
                    return
            for key, v in fields.items():
                self.cfg[key] = v.get().lower().replace(" ", "").replace("maj", "shift")
            self.cfg["base_dir"] = vdir.get()
            config.save(self.cfg)
            dlg.destroy()
            self._start_hotkeys()
            if not (self.listener and self.listener.errors):
                self.say("Réglages enregistrés.")

        ttk.Button(dlg, text="Enregistrer", command=apply).grid(row=6, column=0, columnspan=3, pady=10)

    def _quit(self):
        if self.listener:
            self.listener.stop()
        self.destroy()


def main():
    App().mainloop()
