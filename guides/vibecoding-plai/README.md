# Fabriquer un outil PLAI en un seul fichier, avec Claude

**Codage conversationnel · prompts prêts à copier · style PLAI**

> [!NOTE]
> Adaptation PLAI du guide de François Jourde, [*Fabriquer un outil sur mesure, en un seul fichier*](https://github.com/jourde/training/blob/main/ai/vibecoding.md), sous licence CC BY-SA 4.0.
> Ce qui change : contexte FWB, usage de Claude, charte graphique PLAI intégrée aux prompts.
> Licence de cette page : **CC BY-SA 4.0**, imposée par la source (voir pied de page).

---

## Le principe

Vous n'écrivez pas de code. Vous **décrivez** l'outil à Claude, en français.
Claude produit une page HTML. Vous l'essayez, vous décrivez ce qui cloche, Claude corrige.

C'est le **codage conversationnel** (*vibe coding*, terme d'Andrej Karpathy, 2025).

Le résultat : **un seul fichier `.html`**. Il s'ouvre hors ligne, s'envoie par mail, se dépose sur une clé USB.

---

## Avec Claude : où et comment

### Sur claude.ai (web, app Windows/Mac, iPad)

- Collez le prompt. Claude affiche l'outil dans un **panneau latéral** (Artifact) et le fait tourner.
- Testez directement dans ce panneau. Puis **téléchargez** le fichier via le menu de l'Artifact.
- **Testez toujours le fichier téléchargé**, ouvert hors connexion. L'aperçu Claude n'est pas votre navigateur : certaines fonctions (copie dans le presse-papiers, mémoire locale) peuvent s'y comporter autrement. Comportement non vérifié pour la version actuelle de claude.ai : le contrôle sur fichier réel tranche.

### Un Projet Claude « Atelier outils PLAI »

Pour fabriquer plusieurs outils, créez un **Projet** sur claude.ai (selon votre offre).
Collez le bloc ci-dessous dans les **instructions du projet**.
Chaque conversation du projet hérite alors des contraintes et du style PLAI. Votre prompt se réduit au besoin.

```
Tu fabriques des outils web pour des enseignants de la FWB (Belgique).

Chaque outil :
- tient dans UN SEUL fichier HTML autonome (HTML, CSS, JS dedans) ;
- s'affiche en Artifact HTML ;
- ne fait aucune requête réseau, ne charge aucune bibliothèque externe, aucune police distante ;
- fonctionne hors ligne, ouvert directement dans un navigateur ;
- n'envoie aucune donnée : tout reste dans le navigateur ;
- respecte WCAG 2.2 AA : HTML sémantique, clavier complet, focus visible,
  libellés liés aux champs, messages d'état annoncés (aria-live) ;
- reste utilisable à 200 % de zoom et sur largeur de téléphone ;
- est en français de Belgique (septante, nonante ; niveaux P1-P6, S1-S7) ;
- respecte le STYLE PLAI ci-dessous ;
- porte un commentaire d'en-tête et un pied de page :
  « Jean-François Beguin · PLAI, [année] — licence PolyForm Noncommercial 1.0.0 ».

[coller ici le bloc STYLE PLAI]

Réponse attendue : le fichier complet, puis trois lignes sans jargon :
ce que fait l'outil, ce que je dois vérifier en l'essayant.
Pour une correction : la plus petite possible, sans rien réécrire d'autre.
```

### Avec Claude Code

Pour un outil qui grossit, passe en dépôt Git, ou part sur Vercel : **Claude Code**.
Même méthode, mais Claude lit et modifie le fichier directement dans le dépôt. Pas de copier-coller.

---

## Le cadre, non négociable

- **Données personnelles** : RGPD et règles de votre pouvoir organisateur (PO). Aucune donnée réelle d'élève dans une conversation Claude grand public.
- **Service d'IA** : priorité à celui approuvé par votre PO ou votre établissement. Une offre sous contrat autorise ce qu'une offre grand public interdit.
- **Mise en ligne sur un réseau d'école** : décision de l'établissement, pas la vôtre. Hébergement, données, accessibilité, maintenance. Le **prompt d'audit** (plus bas) prépare exactement ces questions.

Interlocuteurs selon l'établissement : direction, délégué à la protection des données (DPO) du PO, service informatique.

**Sur votre ordinateur, pour vous seul ?** Rien à demander, tant qu'aucune donnée personnelle n'est traitée. Dès que l'outil traite des données ou passe à un collègue : audit.

---

## Deux règles de bon sens

- **Données fictives.** Jamais besoin de vrais noms pour tester un outil.
- **Un outil, une fonction.** Plus facile à corriger, à partager, à refaire.

---

## Le bloc STYLE PLAI

À coller dans les prompts (ou une fois dans les instructions du Projet).
Il reprend la charte `plai-style.css` de HubActif, avec **trois corrections d'accessibilité** :

- `--text3` passe de `#9a958c` à `#6f6a62` : contraste 2,8:1 → 5,1:1 sur `--bg` (seuil texte : 4,5:1) ;
- nouvelle variable `--border-input` `#857f76` pour les champs : 1,5:1 → 3,8:1 (seuil composant : 3:1) ;
- focus : contour plein `--teal` au lieu d'une ombre à 10 % d'opacité, peu visible.

Les polices DM Sans / DM Serif Display ne sont **pas** chargées depuis Google Fonts : ce serait une requête réseau. Elles s'appliquent si elles sont installées, sinon repli système.

```
# STYLE PLAI — à respecter
Variables CSS (:root) :
--bg #faf9f7 ; --surface #ffffff ; --surface2 #f4f2ee ;
--border #e8e4dd ; --border-input #857f76 ;
--text #1a1814 ; --text2 #5a564f ; --text3 #6f6a62 ;
--teal #0f6e56 ; --teal-bg #e1f5ee ; --teal-border #1d9e75 ;
--error #a32d2d ; --error-bg #fcebeb ; --error-border #e24b4a ;
--radius 10px ; --radius-sm 6px.
Polices, sans aucun chargement externe :
titres "'DM Serif Display', Georgia, serif" ;
texte "'DM Sans', system-ui, -apple-system, 'Segoe UI', sans-serif".
Corps 15px, interligne 1.7, fond --bg, texte --text.
Conteneur centré, largeur max 760px, marges latérales 1.5rem.
En-tête : bandeau sobre, titre en DM Serif Display, filet bas 1px --border.
Sections séparées par un filet 1px --border ; h2 en DM Serif Display 22px.
Cartes : fond --surface, bordure 1px --border, rayon --radius, padding 1.25rem 1.5rem.
Bouton principal : fond --teal, texte blanc, rayon --radius-sm, padding 9px 18px, 14px, graisse 500.
Bouton secondaire : fond transparent, bordure 1px --border-input, texte --text2.
Libellés : 13px, graisse 500, --text2, au-dessus du champ.
Champs : largeur 100 %, bordure 1px --border-input, rayon --radius-sm, fond --bg, padding 9px 12px.
Focus visible sur tout élément interactif : outline 2px solid --teal, outline-offset 2px.
Succès : fond --teal-bg, bordure --teal-border, texte --teal.
Erreur : fond --error-bg, bordure --error-border, texte --error.
Pied de page : centré, 13px, --text2, filet haut 1px --border.
Aucun logo, aucune image, aucun émoji. Transitions désactivées si prefers-reduced-motion.
```

---

## Le prompt minimal, pour essayer tout de suite

Une seule zone à remplir.

```
Crée un outil web dans UN SEUL fichier HTML autonome, en Artifact.
Hors ligne, sans bibliothèque externe, sans police distante, sans envoyer de données.
Style sobre : fond #faf9f7, texte #1a1814, boutons #0f6e56 texte blanc, focus visible.

Besoin : [ce que l'outil doit faire, et pour qui]

Donne le fichier complet, puis trois lignes : ce que je dois vérifier.
```

Rapide, mais sans prise sur l'accessibilité, les champs, la charte complète. Pour un outil à garder ou à partager : gabarit complet.

---

## Le gabarit complet

Remplacez les zones entre crochets. Ne touchez pas au reste.
**Seule la zone BESOIN est obligatoire.** Pour les deux autres, écrivez *à toi de proposer, je corrigerai* si vous ne savez pas encore.

Vaut pour un formulaire, un calculateur, un minuteur, une liste de vérification, un tirage au sort, un tableau de suivi.

```
Tu es développeur web. Crée une application d'une seule page,
dans UN SEUL fichier HTML autonome, affichée en Artifact.

# BESOIN
[Deux ou trois phrases : ce que fait l'outil, pour qui (niveau, filière),
ce que la personne y gagne.]

# CE QUE LA PERSONNE FAIT
[Ce qu'elle saisit, choisit, coche, déplace ou déclenche
— ou : à toi de proposer, je corrigerai]

# CE QU'ELLE OBTIENT
[Un texte à copier, un calcul, une liste, un tableau, un minuteur,
un fichier à télécharger…
— ou : à toi de proposer, je corrigerai]

# CONTRAINTES TECHNIQUES — à ne pas modifier
- Un seul fichier .html : HTML, CSS et JavaScript dedans. Aucun fichier séparé.
- Aucune requête réseau, aucune bibliothèque externe, aucune police distante,
  aucun compte utilisateur.
- Fonctionne hors ligne, ouvert directement dans un navigateur.
- Aucune donnée envoyée : tout reste dans le navigateur.
- Accessible WCAG 2.2 AA : HTML sémantique, clavier complet, focus visible,
  libellés liés aux champs, messages d'état annoncés (aria-live).
- Adaptatif : utilisable à 200 % de zoom et sur largeur de téléphone.
- Français de Belgique. Terminologie FWB (P1-P6, S1-S7).
- Code court et lisible, sans framework.
- Commentaire en tête du fichier et pied de page discret :
  « [votre nom] · PLAI, [année] — licence [PolyForm Noncommercial 1.0.0 / EUPL-1.2 / MIT] ».

[coller ici le bloc STYLE PLAI]

# RÉPONSE ATTENDUE
1. Le fichier HTML complet.
2. Trois lignes maximum, sans jargon : ce que fait l'outil, ce que je dois vérifier.
```

---

## Un exemple rempli

Un générateur de prompt pédagogique structuré, pour collègues peu à l'aise avec les consignes à l'IA.
**Observez le niveau de détail du besoin** : quoi, pour qui, quel gain. C'est ce qui évite de tout reprendre au deuxième essai.

Résultat obtenu avec ce prompt : [`exemple-generateur-prompt.html`](exemple-generateur-prompt.html).

```
Tu es développeur web. Crée une application d'une seule page,
dans UN SEUL fichier HTML autonome, affichée en Artifact.

# BESOIN
Un formulaire qui rédige un prompt pédagogique structuré, pour des
enseignants FWB qui utilisent une IA sans savoir formuler une consigne.
Ils remplissent des champs, l'outil écrit le prompt : ils disent ce qu'ils
veulent, sans apprendre à rédiger un prompt.

# CE QUE LA PERSONNE FAIT
Elle remplit, dans cet ordre : tâche demandée, niveau (liste P1 à P6,
S1 à S7), discipline, durée en minutes, besoins spécifiques (cases :
DYS, TDAH, TSA, HP, FLE), objectif, format de sortie.
Chaque champ a un exemple court en texte d'aide.

# CE QU'ELLE OBTIENT
Le prompt structuré par champs (Contexte classe, Objectif, Activité,
Format), affiché en permanence, mis à jour à chaque frappe.
Un bouton « Copier le prompt » confirme la copie par un message annoncé.
Un bouton « Effacer » vide le formulaire.

# CONTRAINTES TECHNIQUES — à ne pas modifier
- Un seul fichier .html : HTML, CSS et JavaScript dedans. Aucun fichier séparé.
- Aucune requête réseau, aucune bibliothèque externe, aucune police distante,
  aucun compte utilisateur.
- Fonctionne hors ligne, ouvert directement dans un navigateur.
- Aucune donnée envoyée : tout reste dans le navigateur.
- Accessible WCAG 2.2 AA : HTML sémantique, clavier complet, focus visible,
  libellés liés aux champs, messages d'état annoncés (aria-live).
- Adaptatif : utilisable à 200 % de zoom et sur largeur de téléphone.
- Français de Belgique. Terminologie FWB (P1-P6, S1-S7).
- Code court et lisible, sans framework.
- Commentaire en tête du fichier et pied de page discret :
  « Jean-François Beguin · PLAI, 2026 — licence PolyForm Noncommercial 1.0.0 ».

[coller ici le bloc STYLE PLAI]

# RÉPONSE ATTENDUE
1. Le fichier HTML complet.
2. Trois lignes maximum, sans jargon : ce que fait l'outil, ce que je dois vérifier.
```

---

## Récupérer le fichier

**Sur claude.ai** : menu de l'Artifact → télécharger. Le fichier arrive en `.html`. Double-clic : il s'ouvre.

**Si vous copiez le code à la main** :

1. Copiez tout, de `<!DOCTYPE html>` à `</html>`.
2. Collez dans un éditeur de **texte brut**.
3. Enregistrez sous un nom en `.html`, par exemple `generateur-prompt.html`.
4. Double-cliquez.

> [!WARNING]
> **Deux pièges** qui affichent du code au lieu de l'outil :
> - **Mac, TextEdit** : format texte enrichi par défaut. Avant d'enregistrer : *Format → Convertir au format texte*.
> - **Windows, Bloc-notes** : ajoute parfois `.txt`. À l'enregistrement : *Type : Tous les fichiers*.

---

## Réparer

```
Voici mon outil : [coller le fichier complet, ou : l'Artifact ci-dessus]

Problème :
- Ce que je voulais : [décrire]
- Ce qui se passe : [décrire]

Trouve l'origine. Propose la correction la plus petite possible.
Ne modifie ni le style PLAI ni le reste du comportement.
Renvoie le fichier complet, puis trois lignes : ce que tu as changé.
```

**« La correction la plus petite possible »** : sans elle, l'IA réécrit tout et casse autre chose.

Dans une même conversation Claude, inutile de recoller le fichier : Claude modifie l'Artifact en place. Recollez-le dans une **nouvelle** conversation.

---

## Ajouter une fonction

```
Voici mon outil : [coller le fichier complet, ou : l'Artifact ci-dessus]

Ajoute : [la fonction, en une ou deux phrases].

Ne change rien d'autre. Garde les contraintes d'origine :
un seul fichier, aucune requête réseau, clavier complet, style PLAI.
Renvoie le fichier complet.
```

---

## Auditer, avant de partager

Constat seulement. Vous choisissez ensuite quoi faire corriger, avec le prompt de réparation.

```
Analyse ce fichier. Réponds en français, sans jargon :
1. Envoie-t-il des données quelque part ?
2. Charge-t-il quelque chose depuis internet (script, police, image) ?
3. Est-il utilisable entièrement au clavier, et avec un lecteur d'écran ?
4. S'affiche-t-il correctement sur téléphone et à 200 % de zoom ?
5. Que se passe-t-il avec un champ vide, un texte très long collé,
   des caractères inattendus ?
6. Respecte-t-il le style PLAI (variables, focus, pied de page) ?
7. Qu'est-ce qui pourrait mal tourner pour la personne qui l'utilise ?

Pour chaque point : constat, niveau (critique / majeur / mineur),
correction proposée.

Ne modifie rien. Pas de code : le constat seulement.

Voici le fichier : [coller le fichier complet]
```

---

## Nettoyer, quand le fichier grossit

Après test seulement. Retestez aussitôt après.

```
Nettoie ce fichier sans changer son comportement ni son apparence.

Autorisé : supprimer le code mort, regrouper les répétitions,
renommer ce qui est obscur, simplifier ce qui est compliqué.

Interdit : ajouter ou retirer une fonction, modifier le style PLAI,
introduire une bibliothèque externe.

Renvoie le fichier complet, puis cinq lignes maximum :
ce que tu as changé, ce que je dois réessayer en priorité.

Voici le fichier : [coller le fichier complet]
```

---

## Accessibilité : constater, puis corriger

Le gabarit exige déjà WCAG 2.2 AA. Ces deux prompts révisent un outil existant.

**1. Constater**

```
Évalue l'accessibilité de ce fichier au regard de WCAG 2.2 niveau AA.
Français, sans jargon, sans code.

Vérifie au moins :
- langue de la page déclarée (lang="fr-BE"), titre de page explicite
- titres hiérarchisés, sans niveau sauté
- chaque champ a une étiquette réellement liée ; erreurs rattachées au champ
- tout est atteignable au clavier, ordre logique, aucun piège,
  focus visible et jamais masqué
- messages d'état (« copié », erreur) annoncés aux lecteurs d'écran
- la couleur n'est jamais le seul indice
- contrastes : 4,5:1 texte, 3:1 composants (bordures de champs comprises)
- cibles cliquables assez grandes et espacées
- utilisable à 200 % de zoom et sur largeur de téléphone
- animations coupées si mouvement réduit demandé

Pour chaque point : constat, niveau (critique / majeur / mineur), correction.

Termine par la liste de ce que tu N'AS PAS pu vérifier en lisant le code,
et qui demande un essai réel.

Voici le fichier : [coller le fichier complet]
```

**2. Corriger**

```
Corrige les points signalés, du plus grave au moins grave.
Ne change ni le comportement ni le style PLAI au-delà de ce qu'exige la correction.

Renvoie le fichier complet, puis une ligne par correction :
ce qu'elle change pour la personne qui utilise l'outil.
```

**Quatre vérifications à faire vous-même**, deux minutes, sans outil :

1. Parcourez la page à la touche Tab : vous voyez toujours où vous êtes, vous n'êtes jamais bloqué.
2. Zoomez à 200 %.
3. Réduisez la fenêtre à la largeur d'un téléphone.
4. Déclenchez un message (copie, erreur) : il se voit.

Une relecture par Claude ne remplace pas cet essai. Elle ne permet pas de déclarer l'outil conforme.

---

## Quelle licence ?

Une licence dit ce que les autres peuvent faire de votre outil.

- **PolyForm Noncommercial 1.0.0** : choix des dépôts PLAI. Réutilisation libre, **usage commercial interdit**. Ce n'est pas une licence open source au sens strict. Texte en anglais uniquement, à ma connaissance. [Texte officiel](https://polyformproject.org/licenses/noncommercial/1.0.0/).
- **EUPL-1.2** : licence de l'Union européenne, texte officiel en français. Partage à l'identique : qui reprend l'outil le laisse aussi libre. [Texte officiel](https://interoperable-europe.ec.europa.eu/collection/eupl/eupl-text-eupl-12).
- **MIT** : toute liberté, à condition de garder votre nom. [Texte officiel](https://opensource.org/licenses/MIT).

Pour un outil déjà fabriqué :

```
Ajoute la licence [PolyForm Noncommercial 1.0.0 / EUPL-1.2 / MIT] à cet outil,
sans rien changer d'autre :
- avis de licence en commentaire en tête du fichier, avec [votre nom] et [année] ;
- pied de page discret : « [votre nom] · PLAI, [année] — licence [nom] »,
  le nom de la licence étant un lien vers son texte officiel.

Ne modifie ni le comportement, ni le style, ni le contenu.
Renvoie le fichier complet.

Voici le fichier : [coller le fichier complet]
```

Sur GitHub, ajoutez aussi un fichier `LICENSE` avec le texte officiel.

> [!WARNING]
> Le statut juridique du code produit par une IA reste incertain et varie selon les pays. Sans apport créatif humain, il n'est pas toujours protégeable. La mention de licence vaut alors surtout **déclaration d'intention**. Suffisant entre collègues. Pour un usage à enjeu : votre PO.

---

## Annexe · Notions techniques

### Un fichier, trois couches

| Couche | Rôle |
|---|---|
| **HTML** | structure et contenu |
| **CSS** | mise en forme (ici : le style PLAI) |
| **JavaScript** | comportement, interactivité |

### Pourquoi un seul fichier

| Avantage | Effet |
|---|---|
| **Autonome** | rien à installer |
| **Portable** | un fichier à envoyer, sauvegarder, déposer |
| **Modifiable par Claude** | « voici mon outil, ajoute ceci » suffit |
| **Durable** | rien à mettre à jour quand l'écosystème change |

### Dépendances, CDN, polices distantes

Une **dépendance** est une bibliothèque externe : graphiques, calendrier, rendu Markdown. Un **CDN** la charge depuis le web à l'ouverture. Une **police Google Fonts** fonctionne de la même façon.

Claude en propose spontanément. Conséquence : l'outil **ne marche plus hors ligne**, **émet une requête vers un tiers** à chaque ouverture, et **cessera de fonctionner** si l'adresse change. D'où la contrainte. Accepter une dépendance, c'est renoncer à ces trois propriétés.

### Rester petit

Un petit outil se comprend, se corrige et se refait facilement. Avec Claude, une raison de plus : **le fichier entier tient dans sa fenêtre de contexte**. Claude le lit en entier et peut le régénérer d'un bloc. Au-delà d'une certaine taille, il travaille par fragments, et les corrections cassent autre chose.

### Versionner

Déposer le fichier sur GitHub (comme les outils PLAI) :

- **sauvegarder sans écraser** : chaque version reste récupérable ;
- **revenir en arrière** si une modification casse l'outil ;
- **partager** par un lien ;
- **publier** : GitHub Pages ou Vercel sert le fichier tel quel ;
- **documenter** : l'historique garde la trace des décisions.

---

## Pour aller plus loin

- Guide d'origine : [*Fabriquer un outil sur mesure, en un seul fichier*](https://github.com/jourde/training/blob/main/ai/vibecoding.md), François Jourde
- [Constructeur d'instructions](https://github.com/jourde/prompt-builder), François Jourde
- **CréeIAppli**, Arnaud Champollion — formulaire qui rédige le prompt de création d'une application web — [bidouiage.forge.apps.education.fr/creiappli](https://bidouiage.forge.apps.education.fr/creiappli/)
- **EDUVAIBE**, Marie-Charlotte Hoyer — parcours en sept étapes vers le prompt d'une application pédagogique — [mchoyer.forge.apps.education.fr/eduvibe](https://mchoyer.forge.apps.education.fr/eduvibe/)
- **La Ressourcerie** de la Forge des communs numériques éducatifs (France) — [ressourcerie.forge.apps.education.fr](https://ressourcerie.forge.apps.education.fr/)
- Outils PLAI — [jfb4plai.com](https://jfb4plai.com)

---

Cette page est une adaptation, par Jean-François Beguin (PLAI), du guide de **François Jourde** [*Fabriquer un outil sur mesure, en un seul fichier*](https://github.com/jourde/training/blob/main/ai/vibecoding.md), publié sous licence CC BY-SA 4.0.
Modifications : contexte FWB, usage de Claude (Artifacts, Projets, Claude Code), bloc de style PLAI, exemple rempli, choix de licence.
L'adaptation est publiée sous la même licence : [Creative Commons Attribution – Partage dans les Mêmes Conditions 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/deed.fr).
Elle déroge donc, pour ce dossier seulement, à la licence CC BY-NC-SA 4.0 des autres contenus du dépôt.
