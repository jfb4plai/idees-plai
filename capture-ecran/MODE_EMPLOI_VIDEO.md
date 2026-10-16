# Créer une petite vidéo sous-titrée à partir de vos captures

*Dernière vérification des informations sur Clipchamp : 16/10/2026, par recherche web (sources secondaires). À re-contrôler dans l'application, les menus évoluent.*

## Voie 1 — directe, un seul clic (recommandée)
1. Prenez vos captures, annotez-les, **écrivez une légende par capture** (c'est le sous-titre).
2. Classez-les avec ▲ ▼.
3. Cliquez **🎬 Vidéo avec sous-titres**.
4. Le dossier `video` contient :
   - `image_001.png`, … : images 1920×1080, **sous-titre incrusté** (bande noire en bas) ;
   - `soustitres.srt` : les mêmes textes avec leur minutage ;
   - `durees.txt` : durée de chaque image ;
   - **`video.mp4`** si le programme `ffmpeg` est présent (voir plus bas).

La durée de chaque image est calculée selon la longueur de la légende (minimum 3 s, maximum 15 s). **Si vous avez enregistré votre voix**, l'image reste affichée au moins aussi longtemps que la voix (+ 0,6 s) : la parole n'est jamais coupée. Le dossier contient alors aussi `voixoff.wav`, la piste complète déjà synchronisée avec les images, et le MP4 la contient.

## Voie 2 — sans ffmpeg : assembler dans Clipchamp (Windows 11)
Clipchamp est intégré à Windows 11 (version gratuite : export 1080p sans filigrane d'après des sources secondaires, à vérifier).
1. Ouvrez **Clipchamp** → *Créer une vidéo*.
2. Glissez les `image_001.png`… dans la médiathèque, puis sur la ligne de temps, **dans l'ordre**.
3. Réglez la durée de chaque image en tirant son bord (voir `durees.txt`).
4. *(Facultatif)* Glissez `voixoff.wav` sur la ligne de temps, sous les images : elle est déjà synchronisée (si vous avez gardé les durées par défaut de `durees.txt`).
5. **Exporter → 1080p** → fichier MP4.

Les sous-titres sont **déjà dans les images** : inutile d'importer le `.srt`. (Je n'ai pas pu confirmer que Clipchamp accepte l'import d'un fichier .srt ; ne comptez pas dessus.)

## Voie 3 — installer ffmpeg pour obtenir le MP4 automatiquement
Dans une invite de commande : `winget install Gyan.FFmpeg` (puis fermez/rouvrez le programme). Ou placez `ffmpeg.exe` à côté de `Capture-ecran-PLAI.exe`. Pensez à faire valider l'installation par votre service informatique.

## Conseils pédagogiques pour de bonnes vidéos
- **Une idée par écran**, 6 à 12 mots de légende ; verbes d'action (« Cliquez », « Choisissez »).
- Pas plus de **8 à 10 écrans** par vidéo ; faites plusieurs vidéos plutôt qu'une longue.
- Masquez (▦) toute donnée d'élève avant de partager.
- Pour des élèves à besoins spécifiques : contraste élevé (le texte blanc sur bande noire l'est déjà), phrases courtes, et proposez aussi la **fiche pas à pas** imprimée.
- Ajoutez votre voix si possible : elle double l'information écrite.
