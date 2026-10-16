# Capture d'écran PLAI

Outil gratuit pour enseignants : capture par **raccourci clavier** (menus déroulants compris), **annotation** (flèches, textes, numéros, masquage RGPD), puis **fiche pas à pas** ou **vidéo sous-titrée**.

- Mode d'emploi enseignants : [MODE_EMPLOI.md](MODE_EMPLOI.md)
- Créer une vidéo : [MODE_EMPLOI_VIDEO.md](MODE_EMPLOI_VIDEO.md)

## Pour le développeur
Python ≥ 3.10, Tkinter + Pillow, aucune autre dépendance. Cible : Windows 10/11.

```
pip install -r requirements-dev.txt
python -m pytest tests          # logique testée sous Linux/Windows
python -m capture_ecran         # lancer
construire_exe.bat              # .exe autonome (PyInstaller) ; ou workflow GitHub « exécutable Windows »
```

Pourquoi le menu reste ouvert : le raccourci est enregistré avec `RegisterHotKey` (Windows), la fenêtre active ne perd donc pas le focus ; la capture est prise **avant** toute fenêtre de l'outil, et le mode « zone » se fait sur l'image figée.

Structure : `hotkeys` (raccourcis) · `grabber` (capture + pointeur) · `selector` (zone) · `annotate` (modèle + rendu Pillow) · `editor` (Tk) · `session` (série, JSON) · `exporter` (SRT, images, MP4 via ffmpeg, HTML, .docx écrit à la main) · `audio` (voix off : MCI Windows, aucune dépendance) · `steps` (série de clics : hook souris WH_MOUSE_LL + image tampon) · `app` (fenêtre).

Licence : voir le dépôt parent (PolyForm Noncommercial 1.0.0).

## Non vérifié sous Windows (écrit selon la documentation, testé seulement par simulation)
Raccourcis globaux, hook souris `WH_MOUSE_LL`, enregistrement MCI du micro, presse-papiers, Paint, DPI.
La logique (rendu, sessions, clics → captures, voix → piste audio, MP4, .docx) est couverte par `pytest` (30 tests).
