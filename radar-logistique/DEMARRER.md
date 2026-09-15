# RADAR COMMERCIAL — TEST DEPUIS CMD

Tout ce qui suit se copie-colle tel quel.

---

## 1. INSTALLATION

**Il n'y a rien à compiler et aucun service à lancer.** Le radar n'utilise que
la bibliothèque standard de Python, plus **PyYAML**.

**Windows**

```cmd
python --version
python -m pip install pyyaml
```

Si `python` est introuvable : installez Python 3.11 ou plus récent depuis
python.org, **en cochant « Add python.exe to PATH »**.

**Linux / macOS**

```bash
python3 --version
python3 -m pip install pyyaml
```

Puis placez-vous dans le dossier du projet :

```cmd
cd radar-logistique
```

---

## 2. PREMIER LANCEMENT — est-ce que ça marche ?

**Windows**

```cmd
radar --base radar.sqlite3 statut
```

**Linux / macOS**

```bash
./radar.sh --base radar.sqlite3 statut
```

### Pourquoi `radar` suffit sous CMD

`radar.cmd` est dans le dossier du projet, et **CMD cherche d'abord dans le
répertoire courant**. Être dans `radar-logistique` suffit donc : il n'y a
**aucun PATH à modifier et aucun paquet à installer**.

| vous utilisez | vous tapez |
|---|---|
| **CMD** (invite de commandes) | `radar --base radar.sqlite3 statut` |
| **PowerShell** | `.\radar --base radar.sqlite3 statut` — PowerShell ne cherche **pas** dans le répertoire courant |
| **Linux / macOS** | `./radar.sh --base radar.sqlite3 statut` |

> Le lanceur Unix s'appelle `radar.sh` et non `radar` : `radar` est déjà le nom
> du paquet Python, les deux se marcheraient dessus.

### VOIE DE SECOURS — elle marche toujours

Si `radar` ne répond pas, pour quelque raison que ce soit, **cette commande
fonctionne dans tous les cas**, y compris sous PowerShell :

```cmd
python -m radar.cli --base radar.sqlite3 statut
```

Elle est strictement équivalente : `radar.cmd` ne fait rien d'autre que
l'appeler, après avoir réglé l'encodage de la console. **Toutes les commandes
de ce guide s'écrivent aussi avec `python -m radar.cli`** — remplacez
simplement le mot `radar` par `python -m radar.cli`.

Ce que vous devez voir — **sortie réelle, sur une base vierge** :

```
  Moteur                 OK
  Base                   OK — 0 avis · 0 opportunités
  Sources                PARTIEL — 0/2
  Import                 OK — exige « EXÉCUTÉ HORS RADAR »
  Collecte               JAMAIS CONSULTÉE — aucune page
  Notifications          OK — 0 préparée(s), 0 envoyée(s)
  Surveillance           OK — 0 page(s)

DÉTAILS
  - source brave  : NON DISPONIBLE — CLÉ ABSENTE — clé API non fournie
  - source google : NON DISPONIBLE — CLÉ ABSENTE — clé API et identifiant …

PROCHAINE COMMANDE UTILE
  radar analyse-du-jour --import <fichier.tsv>
```

`0/2` : les deux moteurs déclarés (google, brave) sont sans clé. Après une
analyse avec `--import`, la ligne passe à `PARTIEL — 1/3` : la source
importée s'ajoute, et elle, elle a répondu.

**`PARTIEL` est normal et honnête** : aucune clé de moteur de recherche n'est
fournie, donc aucune recherche web réelle n'est possible. Le radar le dit au
lieu d'afficher « 0 résultat ».

---

## 3. ANALYSE DU JOUR

C'est la commande principale. Elle joue **le cycle complet** : import ou
découverte → déduplication → qualification → identification → classification
→ score → action → notifications préparées → surveillance.

```cmd
radar --base radar.sqlite3 analyse-du-jour --import validation\exports-reels\2026-09-14-premier-export-reel.tsv
```

```bash
./radar.sh --base radar.sqlite3 analyse-du-jour --import validation/exports-reels/2026-09-14-premier-export-reel.tsv
```

Ce que vous devez voir, entre autres :

```
Mode              : IMPORT RÉEL — recherche exécutée HORS RADAR
Statut            : PARTIEL

ÉTAT DE LA BASE APRÈS CE CYCLE
  Résultats en base                  35
  URLs uniques                       28
  Entreprises                        17
  Opportunités                       27

OPPORTUNITÉS PAR CATÉGORIE
  🟢 DIRECT                           1
  🔵 PROSPECT                         4
  ⚪ PAS ENCORE UNE OPPORTUNITÉ      22

SOURCES
  brave     NON DISPONIBLE  — CLÉ ABSENTE
  google    NON DISPONIBLE  — CLÉ ABSENTE
  import:websearch-assistant  EXÉCUTÉE
```

Options :

| option | effet |
|---|---|
| `--import FICHIER` | un export de recherche produit **hors radar** (TSV, CSV ou JSON) |
| `--collecte FICHIER` | des pages lues hors radar |
| `--top N` | combien d'opportunités détailler après la synthèse (défaut 10) |
| `--json` | la même chose, structurée, pour une interface |

**Relancez la même commande une seconde fois.** Rien ne doit doubler :

```
CE QUI EST NEUF
  Nouvelles opportunités              0
  Déjà connues avant ce cycle        27
```

---

## 4. VOIR LES OPPORTUNITÉS

```cmd
radar --base radar.sqlite3 opportunites
```

Par défaut, ⚪ *PAS ENCORE UNE OPPORTUNITÉ* n'est pas affichée — elle n'est
jamais supprimée pour autant :

```cmd
radar --base radar.sqlite3 opportunites --tout
radar --base radar.sqlite3 opportunites --categorie PROSPECT
radar --base radar.sqlite3 opportunites --limite 5
```

---

## 5. VOIR UNE OPPORTUNITÉ

L'identifiant est celui affiché par la commande précédente, en tête de bloc :
`🟢 DIRECT — Opportunité #8`.

```cmd
radar --base radar.sqlite3 opportunites
radar --base radar.sqlite3 opportunite 8
```

> **L'identifiant `8` est reproductible** avec le fichier d'exemple : deux
> bases neuves chargées avec le même TSV donnent les mêmes identifiants —
> c'est vérifié par un test. Avec **vos** données, les identifiants seront
> différents : lancez toujours `radar opportunites` d'abord et reprenez un
> numéro affiché.

La fiche expose les quatre dimensions **séparément** — type d'information,
nature, état de procédure, action — ainsi que la provenance, le score, le
niveau de preuve, les informations manquantes, les contradictions éventuelles
et le suivi commercial.

---

## 6. VOIR LES ENTREPRISES

```cmd
radar --base radar.sqlite3 entreprises
radar --base radar.sqlite3 entreprise colisprive.be
```

Un **domaine n'est pas une raison sociale**. Tant que l'identité n'est pas
établie, la fiche affiche `INCONNUE` — elle n'invente pas de nom.

---

## 7. VOIR LES SIGNAUX

```cmd
radar --base radar.sqlite3 signaux
```

Un signal est un fait observé **chez quelqu'un d'autre**, dont on déduit un
besoin possible. Ce n'est pas une opportunité confirmée, et la fiche le dit :
*« Ce que nous savons » / « Ce que nous supposons »*.

---

## 8. VOIR LE SUIVI COMMERCIAL

```cmd
radar --base radar.sqlite3 suivi
```

Les huit statuts existants : `NOUVELLE`, `CONTACT À FAIRE`, `CONTACTÉE`,
`EN ATTENTE`, `RELANCE`, `GAGNÉE`, `PERDUE`, `ABANDONNÉE`.

Pour en poser un — **c'est un humain qui décide, jamais le moteur** :

```cmd
radar --base radar.sqlite3 suivre --id 8 --statut "CONTACT À FAIRE"
```

---

## 9. VOIR LES NOTIFICATIONS

```cmd
radar --base radar.sqlite3 notifications
```

**Préparée n'est pas envoyée.** Le radar n'envoie aucun courriel, ne contacte
aucune entreprise et ne dépose aucune candidature. Il prépare ; vous décidez.

---

## 10. VOIR L'ÉTAT DES SOURCES

```cmd
radar --base radar.sqlite3 sources
```

Quatre états, jamais confondus :

| état | sens |
|---|---|
| `CONSULTÉE` | elle a répondu — les nombres sont réels |
| `NON DISPONIBLE` | elle ne peut pas être interrogée (clé absente…) |
| `JAMAIS CONSULTÉE` | aucune consultation n'a jamais eu lieu |
| `ERREUR` | elle a échoué — le motif est affiché |

**`NON DISPONIBLE` n'est jamais transformé en « 0 résultat ».**

---

## 11. VOIR LE TABLEAU DE MESURE

```cmd
radar --base radar.sqlite3 tableau
```

Découverte, qualification, qualité, commercial, valeur, verdicts VP/FP/FN,
état des sources. Sous 20 verdicts relus, le tableau affiche
**`ÉCHANTILLON INSUFFISANT`** au lieu d'un pourcentage : un taux calculé sur
douze observations se lit exactement comme un taux calculé sur mille.

Pour juger un résultat vous-même :

```cmd
radar --base radar.sqlite3 verdict https://exemple.be/page VP --motif "vraie piste"
```

---

## 12. MODE JSON

Chaque commande accepte `--json` et rend alors la structure exacte que
consommera la future interface web (voir `CONTRAT-FRONTEND.md`) :

```cmd
radar --base radar.sqlite3 opportunites --json
radar --base radar.sqlite3 sources --json
radar --base radar.sqlite3 analyse-du-jour --import mon-export.tsv --json
```

---

## 13. SI QUELQUE CHOSE NE VA PAS

Les erreurs d'utilisation s'affichent en clair, **sans traceback Python**, et
sortent en code `2` :

```
❌ ANALYSE-DU-JOUR — IMPOSSIBLE

  Élément :  C:\chemin\qui\n_existe\pas.tsv

  Motif :
    fichier introuvable.

  Aucune donnée n'a été créée.
```

Un fichier d'import qui ne déclare pas sa provenance est **refusé** : le radar
ne charge pas un fichier dont il ignore qui a exécuté la recherche.

---

## 14. LANCER LES TESTS

```cmd
python -m unittest discover -s tests
```

```bash
python3 -m unittest discover -s tests
```

Attendu : **1379 tests, 0 échec.** Les tests sont écrits avec `unittest` ;
`pytest -q` les collecte aussi si vous l'avez installé.

L'audit du cahier des charges, règle par règle :

```bash
python3 outils/audit_cahier.py
```

---

## 15. CE QUE LE RADAR NE PEUT PAS FAIRE AUJOURD'HUI

| limite | état réel |
|---|---|
| Recherche Google | **NON DISPONIBLE — CLÉ ABSENTE** |
| Recherche Brave | **NON DISPONIBLE — CLÉ ABSENTE** |
| Collecte directe de pages | aucune page lue par le radar lui-même |
| Précision / rappel | **ÉCHANTILLON INSUFFISANT** — moins de 20 verdicts relus |
| PowerShell | `radar` seul ne marche pas — écrire `.\radar` ou `python -m radar.cli` |

C'est pour cela que l'entrée passe aujourd'hui par `--import` : un moteur
extérieur produit le fichier, le radar le charge en déclarant sa provenance,
et **rien n'est présenté comme une recherche qu'il aurait faite lui-même**.
