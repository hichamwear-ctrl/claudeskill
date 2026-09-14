# CONTRAT DE DONNÉES — ce qu'une interface web reçoit du moteur

```
INTERFACE WEB  →  radar/service.py  →  MOTEUR RADAR  →  BASE  →  SOURCES
```

**Le moteur reste la source de vérité. Le frontend n'en devient jamais une.**

Ce document décrit ce que `radar/service.py` rend, et **ce que l'interface n'a
pas le droit de recalculer**. Il ne décrit aucun écran : il décrit le contrat.

---

## 1. LA RÈGLE QUI GOUVERNE TOUT LE RESTE

Chaque champ arrive **déjà décidé**. Il n'y a rien à en déduire.

| le frontend REÇOIT | le frontend ne doit JAMAIS |
|---|---|
| `categorie.code` + `categorie.emoji` | choisir une couleur depuis le score |
| `score` + `score_mesurable` | recalculer, pondérer ou arrondir un score |
| `action_recommandee` | décider d'une action depuis la catégorie |
| `nature` (FAIT · SIGNAL · HYPOTHÈSE) | déduire la nature de la source |
| `niveau_de_preuve` | inventer un indice de confiance |
| `etat_procedure` | déduire « postulable » d'une échéance |
| `statuts_suivi` (la liste) | inventer une colonne de kanban |

Un écran qui referait l'un de ces calculs referait le radar une seconde fois,
en moins testé — et les deux divergeraient au premier ajout.

Ces interdits sont **verrouillés par des tests**
(`tests/test_service.py::F_LeServiceNeDecideRien`) : aucun calcul
arithmétique, aucun seuil, aucun nom de catégorie en dur dans la couche.

---

## 2. CE QU'ON IGNORE S'ÉCRIT — ET N'EST JAMAIS `null` EN SILENCE

| valeur rendue | ce qu'elle signifie |
|---|---|
| `"À CONFIRMER"` | la donnée n'a pas été publiée par la source |
| `"NON MESURÉ"` / `"NON MESURÉE"` | la mesure n'a pas eu lieu — ce n'est pas zéro |
| `"JAMAIS CONSULTÉE"` | la source ou la page n'a jamais été interrogée |
| `"NON PUBLIÉE"` | l'échéance existe peut-être, elle n'est pas publiée |
| `"NON DÉCLARÉ PAR LA SOURCE"` | le champ n'était pas dans la source |
| `"INCONNUE"` (identité) | un domaine n'est pas une raison sociale |

`null` reste possible **uniquement** pour un nombre absent (`distance_km`,
`montant`, `duree_mois`) — l'affichage voisin porte alors le texte
(`effort.distance` = `"distance À CONFIRMER"`).

**L'interface doit afficher ces chaînes telles quelles.** Les remplacer par
« — » ou « 0 » ferait croire que l'information a été cherchée et vaut zéro.

---

## 3. LES RESPONSABILITÉS

| HTTP | fonction | rend |
|---|---|---|
| `POST /analyse` | `service.analyser()` | un **cycle** |
| `GET /analyses` | `service.analyses()` | liste de **cycles** |
| `GET /opportunites` | `service.opportunites()` | liste de **cartes** |
| `GET /opportunites/{id}` | `service.opportunite()` | une **carte** ou `null` |
| `GET /entreprises` | `service.entreprises()` | liste d'**entreprises** |
| `GET /entreprises/{id}` | `service.entreprise()` | une **entreprise** + pages + opportunités |
| `GET /signaux` | `service.signaux()` | cartes + `avertissement` |
| `GET /sources` | `service.sources()` | état réel de chaque source |
| `GET /notifications` | `service.notifications()` | cartes à lire, `envoyee: false` |
| `GET /suivi` | `service.suivi()` | l'état commercial de chaque affaire |
| `POST /verdict` | `service.poser_verdict()` | le verdict inscrit |
| `POST /action` | `service.poser_action()` | le statut commercial posé |
| `POST /surveillance` | `service.poser_surveillance()` | la page et son statut |

Deux vues de référence, sans équivalent HTTP obligatoire :

| fonction | rend |
|---|---|
| `service.categories_possibles()` | les **six** catégories + emoji |
| `service.statuts_possibles()` | les **huit** statuts de suivi |
| `service.a_collecter()` | les pages à lire |
| `service.qualite()` | VP/FP/FN + précision et rappel, ou `ÉCHANTILLON INSUFFISANT` |

**Exerçable dès aujourd'hui, sans serveur :**

```bash
python3 -m radar.cli --base radar.sqlite3 api analyse-du-jour \
        --import validation/exports-reels/2026-09-14-premier-export-reel.tsv
python3 -m radar.cli --base radar.sqlite3 api opportunites --limite 20
python3 -m radar.cli --base radar.sqlite3 api sources
python3 -m radar.cli --base radar.sqlite3 api contrat
```

---

## 4. LA CARTE — le contrat du premier écran

Tous les champs demandés pour une carte de tableau/kanban. Exemple **réel**,
issu du jeu du 14/09 (aucun champ inventé) :

```json
{
  "avis_id": 3,
  "entreprise": {
    "nom": null,
    "domaine": "europages.fr",
    "identite": { "etat": "INCONNUE", "raison_sociale": null },
    "libelle": "domaine europages.fr"
  },
  "opportunite": "Transport routier - Sous-traitant - Belgique",
  "categorie": { "code": "PAS ENCORE UNE OPPORTUNITÉ", "emoji": "⚪" },
  "nature": "HYPOTHÈSE",
  "etat_procedure": { "etat": "HORS PROCÉDURE", "confiance": "nulle" },
  "type_information": "NON DÉCLARÉ PAR LA SOURCE",
  "sources": [
    { "source": "import:websearch-assistant",
      "reference": "https://www.europages.fr/…/transport%20routier.html",
      "vue_le": "2026-09-14T21:27:33+00:00" }
  ],
  "zone": "A_VERIFIER",
  "distance_km": null,
  "montant": null,
  "ca_annuel": null,
  "ca_etat": "NON PUBLIÉ",
  "duree_mois": null,
  "effort": { "distance": "distance À CONFIRMER",
              "capacite": "NON MESURÉE — aucune exigence publiée" },
  "score": 55,
  "score_mesurable": true,
  "niveau_de_preuve": "FAIBLE",
  "action_recommandee": "CLASSER SANS SUITE — REVENIR SI UN BESOIN APPARAÎT",
  "raison_principale": "aucun fait commercial observé sur cette page",
  "manques": [],
  "risques": ["information peu prouvée (FAIBLE) — …"],
  "leviers": [],
  "decouverte_le": "2026-09-14T21:27:33+00:00",
  "echeance": "NON PUBLIÉE",
  "surveillance": { "statut": "CANDIDATE", "acces": "JAMAIS CONSULTÉE",
                    "qualification": "NON QUALIFIÉE",
                    "derniere_visite": "JAMAIS CONSULTÉE" },
  "suivi": { "statut": "NOUVELLE", "depuis": null },
  "autres_lectures": [],
  "lectures_divergentes": false
}
```

### Correspondance champ demandé → champ rendu

| demandé | rendu |
|---|---|
| entreprise | `entreprise.libelle` (+ `domaine`, `identite`) |
| opportunité | `opportunite` |
| catégorie | `categorie.code` + `categorie.emoji` |
| nature | `nature` |
| état de procédure | `etat_procedure.etat` + `.confiance` |
| source(s) | `sources[]` — **toutes**, une entrée par lecture |
| zone | `zone` |
| distance si connue | `distance_km` + `effort.distance` |
| montant si connu | `montant` · `ca_annuel` · `ca_etat` |
| durée si connue | `duree_mois` |
| effort opérationnel | `effort.distance` + `effort.capacite` |
| score | `score` + `score_mesurable` |
| niveau de preuve | `niveau_de_preuve` |
| action recommandée | `action_recommandee` |
| raison principale | `raison_principale` |
| date de découverte | `decouverte_le` |
| date limite si connue | `echeance` |
| statut de surveillance | `surveillance.statut` |

---

## 5. UNE ADRESSE, PLUSIEURS LECTURES

Une même URL peut être vue par plusieurs chemins — montrée par un moteur,
puis relue sur la page collectée. **Les deux avis restent en base**, clé
`UNIQUE (source, ref_source)` intacte, pour que l'apport propre de chaque
moteur reste mesurable.

`GET /opportunites` rend **une carte par adresse** : la lecture la mieux
étayée ouvre la fiche, les autres sont dans `autres_lectures`. L'ordre vient
de l'axe **NIVEAU DE PREUVE** existant (`FORTE > MOYENNE > FAIBLE > NULLE`),
puis du score, puis de la lecture la plus récente.

Quand les lectures **divergent**, la contradiction est rendue — jamais
masquée :

```json
{
  "lectures_divergentes": true,
  "divergence": {
    "libelle": "⚠️ LECTURES DIVERGENTES",
    "principale": { "categorie": {"code": "DIRECT", "emoji": "🟢"},
                    "nature": "FAIT",
                    "action": "CONTACTER L'ENTREPRISE",
                    "niveau_de_preuve": "MOYENNE" },
    "autres": [{ "categorie": {"code": "PAS ENCORE UNE OPPORTUNITÉ", "emoji": "⚪"},
                 "nature": "HYPOTHÈSE",
                 "action": "CLASSER SANS SUITE — …",
                 "niveau_de_preuve": "FAIBLE",
                 "sources": [{ "source": "import:moteur", "reference": "…",
                               "vue_le": "…" }] }]
  }
}
```

**L'interface doit l'afficher.** Ce désaccord est une information : il dit
que le titre ne suffisait pas et que la page, elle, le disait.

---

## 6. LE CYCLE — ce que rend `[ ANALYSE DU JOUR ]`

```json
{
  "id": "20260914T212726.682-8d63",
  "debut": "…", "fin": "…",
  "statut": "PARTIEL",
  "entonnoir": {
    "resultats_bruts": 35, "urls_uniques": 28, "doublons": 7,
    "pages_analysees": 0, "candidats": 28, "entreprises": 17,
    "opportunites": 27, "signaux": 2, "postulables": 0,
    "attribues": 0, "rejetes": 0, "notifications": 5
  },
  "sources": {
    "demandees":       ["brave", "google", "import:websearch-assistant"],
    "executees":       ["import:websearch-assistant"],
    "en_erreur":       [],
    "non_disponibles": ["brave", "google"],
    "non_mesurees":    []
  },
  "detail_sources": [
    { "nom": "google", "etat": "NON DISPONIBLE",
      "resultats": "NON MESURÉE", "opportunites": "NON MESURÉE",
      "motif": "CLÉ ABSENTE — clé API et identifiant de moteur non fournis",
      "derniere_consultation": "JAMAIS CONSULTÉE" },
    { "nom": "import:websearch-assistant", "etat": "EXÉCUTÉE",
      "resultats": 35, "opportunites": 27,
      "motif": "EXÉCUTÉ HORS RADAR — 0 refusée(s)",
      "derniere_consultation": "2026-09-14T21:27:26+00:00" }
  ],
  "erreurs": [],
  "avertissement": "NON MESURÉE n'est pas zéro : la source n'a pas été interrogée."
}
```

### LES CINQ ÉTATS DE SOURCE NE S'ADDITIONNENT JAMAIS

| état | ce que l'écran doit dire |
|---|---|
| `EXÉCUTÉE` | elle a répondu — `resultats` et `opportunites` sont des nombres |
| `ERREUR` | elle a échoué — `motif` dit pourquoi |
| `NON DISPONIBLE` | elle ne peut pas être interrogée (clé absente…) — `motif` dit pourquoi |
| `NON MESURÉE` | elle **n'a pas été interrogée** par ce cycle |
| `JAMAIS CONSULTÉE` | aucune consultation n'a jamais été journalisée |

Les fondre en un « 3 sources OK » ferait disparaître la différence entre
**« a rendu zéro »** et **« n'a pas été interrogée »**. Aucune source ne
rend jamais un résultat fabriqué : si elle n'a pas pu être lue, elle le dit.

`statut` vaut `COMPLET`, `PARTIEL` ou `ERREUR` — posé par le moteur.

---

## 7. LES COLONNES DU PREMIER ÉCRAN

Deux familles de colonnes, qui viennent de **deux endroits différents** et ne
doivent pas être confondues :

**Les CATÉGORIES** — ce que le moteur décide (`categories_possibles()`) :

```
🟢 DIRECT   🟡 RENFORCEMENT   🟣 A_CONSTRUIRE   🔵 PROSPECT
⚪ PAS ENCORE UNE OPPORTUNITÉ   🔴 REJET
```

**Les STATUTS DE SUIVI** — ce qu'un humain pose (`statuts_possibles()`) :

```
NOUVELLE · CONTACT À FAIRE · CONTACTÉE · EN ATTENTE · RELANCE
GAGNÉE · PERDUE · ABANDONNÉE
```

Le kanban demandé s'obtient en juxtaposant les deux : les colonnes
d'entrée sont des **catégories**, les colonnes de travail sont des
**statuts**. Une carte porte les deux (`categorie` et `suivi.statut`), et
l'interface ne doit **jamais** en dériver l'autre.

`POST /action` déplace une carte entre statuts. Un statut hors de la liste
est **refusé**, jamais deviné.

---

## 8. CE QUE L'INTERFACE NE DOIT PAS FAIRE

1. Recalculer un score, un seuil, une couleur, une action.
2. Supprimer une opportunité parce que son score est faible.
3. Hiérarchiser les sources — aucune n'est meilleure par nature.
4. Afficher un signal comme une opportunité confirmée.
5. Présenter une attribution comme postulable.
6. Remplacer `À CONFIRMER` / `NON MESURÉ` par un vide ou un zéro.
7. Masquer une contradiction entre deux lectures.
8. Perdre une provenance en consolidant.
9. Afficher « 0 résultat » pour une source non consultée.
10. Déclarer une notification « envoyée » — le bot n'envoie rien.
