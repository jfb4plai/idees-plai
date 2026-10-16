# Capture d'écran PLAI — mode d'emploi

Pour photographier un **menu déroulant** (qui se ferme dès qu'on clique ailleurs), l'ajouter des **flèches, textes, numéros**, puis en faire une **fiche** ou une **vidéo sous-titrée**.

## 1. Installer (une seule fois)
**Option A — le fichier `Capture-ecran-PLAI.exe`** : copiez-le où vous voulez, double-cliquez. Windows peut afficher « Windows a protégé votre ordinateur » (le programme n'est pas signé) : cliquez sur *Informations complémentaires* puis *Exécuter quand même*.

**Option B — avec Python** (si votre école l'autorise) : installez Python 3 depuis python.org (cochez « Add to PATH »), puis double-cliquez sur `Lancer.bat`.

Rien n'est envoyé sur Internet. Les captures restent dans `Images\Captures PLAI`.

## 2. Photographier un menu déroulant
1. Lancez le programme (une petite fenêtre s'ouvre ; vous pouvez la réduire).
2. Ouvrez votre menu comme d'habitude (clic sur *Fichier*, clic droit…).
3. **Sans cliquer ailleurs**, appuyez sur le raccourci :

| Raccourci | Effet |
|---|---|
| **Ctrl + Maj + F9** | tout l'écran |
| **Ctrl + Maj + F10** | vous choisissez une zone (le menu est déjà « figé ») |
| **Ctrl + Maj + F11** | la fenêtre active seulement |
| **Ctrl + Maj + F12** | démarre / arrête la **série de clics** (voir ci-dessous) |

Un bip confirme la capture. Sur certains portables, ajoutez la touche **Fn**.
Les raccourcis se changent via le bouton *Raccourcis…* (évitez Ctrl+Alt : c'est la touche AltGr du clavier belge).

**Si le raccourci ne marche pas** : bouton **« Dans 3 secondes »**, ouvrez votre menu pendant le décompte.
Le pointeur est dessiné avec un halo jaune pour montrer où vous avez cliqué (désactivable).

### La série de clics (une capture numérotée par clic)
Idéal pour expliquer une manipulation : faites-la **une fois**, le programme prend une image à chaque clic.
1. Cliquez sur **● Enregistrer mes clics** (ou `Ctrl+Maj+F12`). La fenêtre se réduit ; la barre de titre indique l'enregistrement.
2. Faites votre manipulation normalement. **Un bip = une étape enregistrée.** Chaque image reçoit un **cercle rouge** autour du clic, une **pastille numérotée** et la légende « Cliquez ici ».
3. Arrêtez avec `Ctrl+Maj+F12` (évitez de cliquer sur la barre des tâches pour rouvrir la fenêtre : ce clic serait enregistré).
4. Améliorez chaque étape (double-clic sur la ligne) : légende, flèche, voix.

*Moment de l'image* : **juste avant le clic** (recommandé : on voit le menu ouvert et le pointeur sur l'élément à cliquer) ou **0,5 s après** (on voit le résultat). Un double-clic est fusionné en une seule étape. Les clics dans notre propre fenêtre sont ignorés ; les clics gauche et droit sont enregistrés (pas le glisser-déposer ni le clavier).
Si vous supprimez ou déplacez des étapes : bouton **↻ Renuméroter**.

## 3. Annoter (l'éditeur s'ouvre tout seul)
Choisissez un outil, une couleur, une taille, puis glissez sur l'image.

| Outil | Usage |
|---|---|
| ➚ Flèche | montrer un bouton (Maj = flèche bien droite) |
| ▭ Cadre / ◯ Ovale / ▮ Surligner | entourer, mettre en évidence |
| T Texte | cliquer puis écrire |
| ① Numéro | poser 1, 2, 3… pour les étapes |
| ✎ Crayon | dessin libre |
| ▦ **Masquer** | pixelliser un prénom, un nom d'élève, une adresse (**RGPD**) |
| ✂ Recadrer | garder seulement une zone |
| ☝ Déplacer | déplacer un objet (Suppr pour l'effacer) |

`Ctrl+Z` annule, `Ctrl+Y` rétablit. **Copier l'image** → collez avec `Ctrl+V` dans Word, Teams, un courriel.
**Ouvrir dans Paint** : les annotations sont fixées dans l'image, puis Paint s'ouvre (vous ne pourrez plus les déplacer dans notre éditeur).

> ⚠ Masquer ne protège que **l'image enregistrée** : relisez toujours avant de partager.

**La légende** en bas de l'éditeur sera le **sous-titre** de la vidéo : une phrase courte par étape, à l'impératif (« Cliquez sur *Fichier* »).

**Ma voix** : bouton **🎙 Enregistrer ma voix**, lisez la légende, **⏹ Arrêter**, **▶ Écouter** pour vérifier (**✖ Effacer** pour recommencer). Il faut un micro (celui du portable convient) autorisé dans *Paramètres Windows › Confidentialité › Microphone*. Parlez dans une pièce calme, à 20 cm du micro.

## 4. Fabriquer une fiche ou une vidéo
Dans la fenêtre principale, réorganisez avec ▲ ▼ puis :
- **📝 Document Word** : `document.docx` (A4) avec un titre « Étape n », la légende et l'image ; police Verdana 12, vrais titres Word (navigation, lecteurs d'écran) et **texte alternatif** sur chaque image. À retoucher dans Word.
- **📄 Fiche HTML/PDF** : page web numérotée, imprimable ou « Enregistrer au format PDF ».
- **🎬 Vidéo** : crée le dossier `video` dans la série (sous-titres, et votre voix si enregistrée).

Voir **[MODE_EMPLOI_VIDEO.md](MODE_EMPLOI_VIDEO.md)** pour les détails.

## 5. Problèmes fréquents
| Problème | Solution |
|---|---|
| Message « raccourci déjà utilisé » | changer le raccourci (*Raccourcis…*) |
| Le menu se ferme avant la capture | utiliser « Dans 3 secondes » |
| Écran flou/décalé sur écran à zoom 125 % | normal sur d'anciens Windows : signalez-le avec votre version de Windows |
| « Impossible d'utiliser le micro » | autoriser le micro dans Windows (voir ci-dessus) et vérifier qu'il est le micro par défaut |
| Aucune étape enregistrée avec la série de clics | un antivirus ou une stratégie d'école peut bloquer l'écoute des clics : essayer les captures par raccourci |
| Rien dans le presse-papiers | cochez l'option « Copier aussi dans le presse-papiers » |

*Limites connues* : écrit pour Windows ; non testé sur Mac/Linux (la capture se fait, pas les raccourcis globaux). Une fenêtre exécutée « en administrateur » peut ne pas laisser passer les raccourcis.
