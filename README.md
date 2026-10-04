# idees-plai

Journal des idées d'applications PLAI générées par la routine hebdomadaire de scouting (agent cloud planifié).

## Fonctionnement

Chaque semaine (lundi 8h), une routine cloud lit ce dépôt (`ideas/log.md`) pour éviter de reproposer une idée déjà loguée, cherche de nouvelles pistes, et produit un rapport — visible sur la page de la routine : https://claude.ai/code/routines/trig_01Gm2ujsQSwAZgSAG9KRVLJn

**Étape manuelle nécessaire** : les sessions cloud n'ont aucun accès en écriture sur ce dépôt (limitation Git/GitHub App confirmée le 2026-08-10, voir la mémoire du projet pour le détail du diagnostic). La routine ne peut donc pas committer elle-même — copier le tableau produit et l'ajouter en haut de [`ideas/log.md`](ideas/log.md) chaque semaine.

Le tableau produit couvre, pour chaque idée : le besoin de terrain identifié, le potentiel/valeur ajoutée, les risques (RGPD, coûts API/stockage), et un plan de développement aligné sur le pipeline habituel (Claude Workspace → GitHub → Vercel → Supabase si besoin).

**La validation scientifique RISS n'est pas faite ici** — RISS reste local (`D:\RISS`), inaccessible au cloud. Après réception, passer le rapport au skill `moulinette-riss` en local pour l'annoter d'un ancrage RISS par idée.

## Historique

Voir [`ideas/log.md`](ideas/log.md) — une section par semaine, la plus récente en haut.

## Licences

- **Code** : [PolyForm Noncommercial 1.0.0](LICENSE). Usage non commercial uniquement.
- **Contenus pédagogiques** : [CC BY-NC-SA 4.0](LICENSE-CONTENT.md). Réutilisation et adaptation non commerciales, avec attribution et partage dans les mêmes conditions.
- **Logo et identité visuelle PLAI** : tous droits réservés (voir `LICENSE-CONTENT.md`).

Auteur : Jean-François Beguin, Référent numérique, https://jfb4plai.com
