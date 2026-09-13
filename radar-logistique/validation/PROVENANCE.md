# CLASSEMENT DE PROVENANCE — toutes les mesures réelles

Deux classes, jamais mélangées. Une mesure **PROVENANCE INCOMPLÈTE** reste
une mesure réelle : elle est **reproductible en analyse** (l'empreinte permet
de recontrôler la lecture) mais **pas reproductible en collecte** (rien ne
prouve ce que le serveur a envoyé, ni quand).

> **Les empreintes inscrites sont celles des fichiers déposés.**
> Pour les mesures INCOMPLÈTES, ce ne sont **PAS** les empreintes des octets
> servis par le serveur. Ne jamais les présenter comme telles.

Les 7 éléments exigés : URL demandée · URL finale · date/heure · statut HTTP ·
HTML brut · taille · SHA-256. Référence : `PROTOCOLE-REPRISE.md`.

| # | date | famille | référence | empreinte | classe | ce qui manque |
|---|---|---|---|---|---|---|
| 1 | 2026-09-04 | page_web | `pypi.org/project/requests` | `ef41f74ee587…` | **COMPLÈTE** | rien — `curl` depuis le conteneur, 200 observé, octets serveur conservés |
| 2 | 2026-09-05 | recherche | 16 résultats, 2 requêtes | `d2747424e7e7…` | **INCOMPLÈTE** | titres et URL seulement · aucune page lue · outil hors radar |
| 3 | 2026-09-12 | marche_public | 15 résultats, 2 requêtes | `bb3b99a2bab5…` | **INCOMPLÈTE** | idem |
| 4 | 2026-09-12 | entreprise | `colisprive.be` (accueil) | `fed491c2e943…` | **INCOMPLÈTE** | « page conservée » — ni date de fetch, ni statut HTTP, ni URL finale |
| 5 | 2026-09-12 | recherche | 14 résultats, 2 requêtes | `8996d85be77d…` | **INCOMPLÈTE** | titres et URL seulement · aucune page lue |
| 6 | 2026-09-12 | entreprise | `transporteur.dhl.fr` | `e0a7191f9b39…` | **INCOMPLÈTE** | **7 éléments sur 7 manquants** · contenu collé, transcrit · CSS/polices/scripts retirés |
| 7 | 2026-09-12 | entreprise | `colisprive.be/devenir-partenaire-livraison/` | `c5e20010e7bd…` | **INCOMPLÈTE** | **7 éléments sur 7 manquants** · contenu collé, transcrit |

```
PROVENANCE COMPLÈTE    : 1 mesure sur 7
PROVENANCE INCOMPLÈTE  : 6 mesures sur 7
```

## Ce que cela autorise et n'autorise pas

**Autorisé** — dire que le radar a lu ces pages et qu'il en a tiré ces
verdicts : la lecture est rejouable sur les fichiers conservés, et la
mesure du 2026-09-12 (`MESURE-2026-09-12-DEUX-PAGES.md`) l'a prouvé en
rejouant les quatre pages.

**Interdit** — dire que ces octets sont ceux qu'ont envoyés
`transporteur.dhl.fr` ou `colisprive.be`, à telle date, avec tel statut.
Personne ne l'a observé.

## Ce qui rendrait les mesures 6 et 7 complètes

Une capture refaite depuis une machine connectée, avec les 7 éléments —
commande fournie dans `PROTOCOLE-REPRISE.md` §4. Les verdicts seraient alors
recontrôlables de bout en bout, et un écart d'empreinte avec les fichiers
actuels mesurerait exactement ce que la transcription a coûté.
