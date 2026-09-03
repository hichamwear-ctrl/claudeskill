# Première validation sur données réelles — protocole

Ce fichier décrit ce qui se passera **exactement** quand un vrai export TED
arrivera. Il est écrit avant, pas après : le but est qu'aucune décision ne
soit prise au moment où les chiffres seront là et où la tentation de « faire
apparaître le bon résultat » sera la plus forte.

---

## Ce qui est vérifié aujourd'hui, et ce qui ne l'est pas

| | état |
|---|---|
| le trajet complet supporte un lot volontairement hostile | **vérifié** — `outils/repetition_ted.py` |
| aucune ligne ne se perd entre l'entrée et la sortie | **vérifié** — livre de comptes, écart 0 |
| une fixture ne peut pas entrer dans la base RÉELLE | **vérifié** — 17 refus, 17 incidents conservés |
| une ligne réellement collectée passe en RÉEL | **vérifié** |
| l'endpoint TED répond, et avec quelle forme | **NON VÉRIFIÉ** — aucun accès réseau ici |
| les chemins de `sources/ted.yaml` correspondent aux vraies clés | **NON VÉRIFIÉ** — `verifie: false` |
| ce que le marché contient réellement | **NON MESURÉ** |

Les trois dernières lignes ne seront pas devinées. `recenser` les mesure.

---

## La séquence, dans l'ordre

```bash
# 0. COLLECTE — depuis une machine ayant un accès réseau.
#    Le collecteur n'interprète rien : il enregistre le brut et l'estampille.
python3 outils/collecter_ted.py --pages 20 --sortie reponses-ted.json

# 1. RECENSER — mesurer quelles clés existent VRAIMENT.
#    Tout champ à 0 % est une clé inexistante : on la corrige dans
#    sources/ted.yaml, JAMAIS dans le code.
python -m radar.cli recenser --source ted --echantillon reponses-ted.json

# 2. SONDER — mesurer le marché AVANT d'écrire quoi que ce soit en base.
python -m radar.cli sonder --source ted --entree reponses-ted.json

# 3. TRAITER — en mode RÉEL, dans la base réelle, séparée de la démo.
python -m radar.cli traiter --reel --source ted --entree reponses-ted.json

# 4. RAPPORT
python -m radar.cli rapport --reel --top 20
```

À l'étape 3, le cycle **échoue** si le livre de comptes ne se réconcilie pas.
C'est voulu : un rapport partiel qui ne le dit pas est pire que pas de rapport.

Répétition avant tout ça, à relancer après toute modification du moteur :

```bash
python3 outils/repetition_ted.py    # sortie 0 = le trajet tient
python3 outils/audit_cahier.py      # sortie 0 = les 17 règles sont tenues
python3 -m unittest discover -s tests
```

---

## Ce que le premier rapport réel contiendra

Chaque élément a sa source dans le code — rien n'est rédigé à la main.

| ce qui est demandé | d'où ça vient |
|---|---|
| documents réellement collectés | `avis` × `reponses`, section COLLECTE |
| sources consultées / jamais consultées / indisponibles | registre des sources, avec le motif |
| date et heure de collecte | bloc `_collecte` posé par le collecteur |
| complétude des données | section COMPLÉTUDE, champ par champ |
| erreurs et incidents | table `incidents`, brut conservé |
| lots créés | section LOTS, avec les marchés parents |
| doublons CERTAIN / PROBABLE / POSSIBLE | section QUALITÉ + livre de comptes |
| rejets par motif | section MOTIFS DE REJET |
| CAPTER / DÉVELOPPER | section CLASSIFICATION |
| 🟢 🟡 🟣 🔵 🔴 | section CLASSIFICATION |
| opportunités près du dépôt | sélection PRÈS DU DÉPÔT |
| NL/FR/DE → BE | sélection CORRIDOR ÉTRANGER → BE |
| petits contrats intéressants | sélection PETITS CONTRATS À MA TAILLE |
| gros contrats à renfort ou partenariat | sélection TROP GROS SEUL |
| attributions intéressantes | sélection À DÉVELOPPER |
| données manquantes | COMPLÉTUDE + points À VÉRIFIER |
| `MARGE NON MESURÉE` | section ÉCONOMIE |

Une sélection vide reste affichée avec la raison de son vide. Une section qui
disparaît se lit « il n'y a rien » ; ce n'est pas la même chose.

Et pour chaque opportunité retenue, la fiche porte : ce que j'ai déjà, ce qui
me manque, comment le combler, l'effort, le risque, le potentiel économique,
l'action suivante.

---

## Si le moteur classe mal une opportunité réelle

**Le score ne sera pas ajusté pour faire apparaître le résultat attendu.**
Un seuil déplacé après coup pour qu'un cas précis tombe juste est une
falsification lente : il fait mentir tous les autres cas en silence.

La procédure est fixe, et elle produit sept éléments :

1. **la donnée source** — le brut, tel que la source l'a publié ;
2. **ce que le moteur a compris** — champs extraits, familles reconnues,
   exigences lues, zone, échéance ;
3. **la classification obtenue** — catégorie, moteur, score, motif ;
4. **pourquoi elle est incorrecte, ou correcte** — la démonstration, pas
   l'impression ;
5. **la règle du cahier des charges concernée** — numérotée ;
6. **la correction proposée** — et à quel étage elle est faite ;
7. **le test de non-régression ajouté** — qui échoue avant, passe après.

Cinq cas déjà passés par cette procédure figurent plus bas.

---

## Ce que la répétition générale a déjà trouvé

La répétition a été jouée sur un lot de 17 enregistrements volontairement
sales, avant l'arrivée de toute donnée réelle. Elle a trouvé cinq défauts —
trois dans le moteur, un dans l'étape de sondage, un dans le collecteur.

### A — un montant écrit « 120 000 » faisait perdre tout le cycle

1. **donnée source** : `"estimated-value": {"amount": "120 000", "currency": "EUR"}`
2. **ce que le moteur a compris** : rien — `float("120 000")` a levé une
   `ValueError` dans la déduplication.
3. **classification obtenue** : aucune. Le cycle s'est arrêté, et **les
   16 autres avis du lot sont partis avec.**
4. **incorrect** : un fichier réel est sale par nature. Une valeur sale coûte
   sa propre ligne, jamais celles des autres.
5. **règle** : 8 — données manquantes jamais inventées ; 12 — aucune
   disparition silencieuse.
6. **correction** : lecture tolérante des nombres dans `adaptateur.py`
   (`_nombre`, `_entier`). Trois issues seulement : absent → `None` ;
   lisible → un nombre ; publié mais illisible → `None` **et** une trace.
   Jamais un zéro inventé, jamais une exception.
7. **tests** : `test_un_montant_publie_en_texte_ne_fait_pas_perdre_le_cycle`,
   `test_un_nombre_illisible_est_signale_jamais_mis_a_zero`,
   `test_un_champ_illisible_apparait_dans_la_fiche`.

### B — un lot exigeant 12 véhicules était déclaré exécutable tel quel

1. **donnée source** : lot 3, `"requirements": {"min-vehicles": 12}`.
2. **ce que le moteur a compris** : `exigences = {}`. L'extraction des lots
   ne lisait que les clés de premier niveau, pas la carte déclarée dans
   `sources/ted.yaml`.
3. **classification obtenue** : 🟢 DIRECT — *« exécutable avec la structure
   actuelle »*, avec 6 véhicules au parc pour 12 exigés.
4. **incorrect, et dangereux** : ce n'est pas une note trop haute, c'est une
   affirmation fausse sur la capacité. Répondre à ce marché sans louer six
   véhicules, c'est perdre la consultation ou pire, gagner et ne pas exécuter.
5. **règle** : 9 — analyse lot par lot ; 5 — la taille n'est jamais un rejet,
   mais elle n'est jamais non plus une capacité présumée.
6. **correction** : chaque lot est désormais lu avec la carte de sa source
   (`{**lot, **adaptateur.extraire(lot)}`), donc `requirements.min-vehicles`
   devient `vehicules_min` comme pour le marché parent.
7. **tests** : `test_une_exigence_de_lot_est_lue_avec_la_carte_de_la_source`,
   `test_un_lot_trop_gros_n_est_jamais_dit_executable_tel_quel`.

Après correction, le même lot ressort 🟡 RENFORCEMENT :
*« 12 véhicules exigés — 6 en propre, 6 à louer (mobilisable jusqu'à 16) »*,
remède chiffré : *« location de 6 véhicule(s), 30 j »*. Ce n'est pas un rejet.
C'est un chantier nommé.

### C — la fiche d'un lot de transport portait des manques de formation

1. **donnée source** : le même lot 3.
2. **ce que le moteur a compris** : correct.
3. **classification obtenue** : 🟡 RENFORCEMENT — correcte, mais la fiche
   listait aussi *« aucune formation mentionnée dans la source »* et
   *« durée insuffisante pour amortir une montée en compétence »*.
4. **correct sur le fond, faux sur la forme** : le test 🟣 ne pose sa question
   que pour un métier non reconnu. Sur un lot de transport, ces deux lignes
   sont du bruit — et le bruit refabrique la boîte noire qu'on a interdite.
5. **règle** : 15 — jamais une boîte noire.
6. **correction** : les manques du test 🟣 n'entrent dans la fiche que si la
   montée en compétence est bien la question posée.
7. **test** : `test_les_manques_du_test_a_construire_ne_polluent_pas_un_lot_de_transport`.

### D — `sonder` mesurait autre chose que ce que la chaîne traite

1. **donnée source** : n'importe quel lot, à l'étape 2 de la séquence.
2. **ce que le moteur a compris** : rien — `sonder` levait une
   `AttributeError` sur un attribut supprimé lors du passage aux cinq
   catégories, et référençait encore `Type.SOUS_TRAITANCE`, qui n'existe plus.
3. **classification obtenue** : aucune, l'étape 2 était inutilisable.
4. **incorrect** : c'est l'étape qui mesure la source **avant** d'écrire quoi
   que ce soit en base. De plus, elle n'éclatait pas les lots : elle aurait
   annoncé un marché là où le traitement en trouve trois.
5. **règle** : 9 — lot par lot ; 14 — rapport de mesure.
6. **correction** : `sonder` éclate désormais les lots comme la chaîne, compte
   les cinq catégories, et considère exploitable tout ce qui n'est pas un rejet
   — un marché à renforcer n'est pas un marché perdu.
7. **tests** : `test_sonder_annonce_les_memes_categories_que_la_chaine`,
   `test_sonder_compte_les_lots_pas_seulement_les_marches`,
   `test_un_marche_trop_gros_reste_exploitable_dans_le_verdict`.

### Et un cinquième, côté collecteur

`outils/collecter_ted.py` construisait la référence d'un avis sans identifiant
à partir d'une variable `url` **qui n'existait pas** : `NameError` au premier
avis TED sans `publication-number`. Corrigé par `reference_de()`, qui dérive
une référence stable du contenu — c'est le correctif du bug des sept
opportunités disparues, appliqué cette fois à l'entrée du réseau.
Tests : `test_deux_avis_sans_identifiant_gardent_des_references_distinctes`,
`test_l_identifiant_officiel_prime_sur_la_reference_derivee`.

---

## Rappels qui tiennent quoi qu'il arrive

- **TED n'est pas le produit.** Si TED tombe, si l'endpoint change, si l'API
  se ferme, le radar continue sur les autres sources. Aucune source n'est
  indispensable, et aucune n'a de priorité acquise : la priorité se mesure au
  rendement observé.
- **Un marché public n'est ni supérieur ni inférieur à un contrat privé.**
  Le type de source n'entre pas dans le score — vérifiable : `score.py` ne
  mentionne ni `source` ni `type_avis`.
- **`NON MESURÉE` n'est pas `0`.** Une source jamais consultée n'a pas un
  mauvais rendement : elle n'en a pas encore.
- **Une donnée absente reste absente.** `À VÉRIFIER`, `NON PUBLIÉ`,
  `INCONNU`, `NON MESURÉ` — jamais une valeur plausible à la place.
