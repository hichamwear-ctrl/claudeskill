# PROTOCOLE — produire un export externe et le faire entrer dans le radar

Cinq étapes. Aucune ne demande de toucher au code.

```
1. EXÉCUTER les requêtes          (sur une machine qui atteint Internet)
2. EXPORTER les résultats          (JSON ou CSV)
3. DÉPOSER le fichier              (n'importe où dans le projet)
4. LANCER une commande             (radar import-recherche <fichier>)
5. LIRE le rapport commercial      (TOP OPPORTUNITÉS)
```

---

## 1 · Exécuter les requêtes

La liste est dans le radar :

```bash
python -m radar.cli requetes-prioritaires            # par famille, lisible
python -m radar.cli requetes-prioritaires --brut     # une par ligne, à copier
python -m radar.cli requetes-prioritaires --famille A
```

Six familles : **A** besoin explicite · **B** logistique et distribution ·
**C** signaux d'entreprise · **D** partenariats · **E** métiers à construire ·
**F** marchés et attributions.

**Le radar n'exécute aucune de ces requêtes** et ne peut pas le faire : aucun
hôte d'API de recherche n'est joignable depuis son environnement. C'est vous
qui choisissez le moyen — une API dont vous détenez la clé, l'export d'un
compte que vous possédez, ou une copie à la main.

Pour un premier test, **3 requêtes et une dizaine de résultats chacune
suffisent**. Mieux vaut un petit échantillon regardé sérieusement qu'un gros
qu'on ne relit pas.

## 2 · Exporter

Deux formats. Le fichier **doit** déclarer sa provenance, mot pour mot :
`EXÉCUTÉ HORS RADAR`. Un fichier qui ne le déclare pas est refusé — le radar
ne devine pas qui a exécuté une recherche.

### JSON

```json
{
  "provenance": "EXÉCUTÉ HORS RADAR",
  "moteur": "le-nom-du-moteur-que-vous-avez-utilisé",
  "date_execution": "2026-09-13T09:30:00+00:00",
  "resultats": [
    {"requete": "recherche transporteur Belgique",
     "url": "https://…", "titre": "…", "extrait": "…", "rang": 1}
  ]
}
```

`moteur` et `date_execution` peuvent aussi figurer **sur chaque ligne** : un
seul fichier peut donc porter les résultats de plusieurs moteurs, et c'est
même souhaitable — c'est ainsi qu'on mesure ce que chacun apporte seul.

### CSV

```
provenance,moteur,date_execution,requete,url,titre,extrait,rang
EXÉCUTÉ HORS RADAR,mon-moteur,2026-09-13T09:30:00+00:00,recherche transporteur Belgique,https://…,Titre,Extrait,1
```

### Le format aussi est souple

Le format se lit dans le **contenu**, pas dans l'extension. Sont acceptés :

| Forme | Détail |
|---|---|
| JSON | objet avec en-tête, ou tableau nu de lignes complètes |
| CSV | séparateur `,` **ou** `;` (tableur FR/NL) — détecté tout seul |
| TSV / collage de navigateur | tabulations, `.tsv`, `.txt`, ou sans extension |
| Marque d'ordre d'octets | retirée à la lecture (un tableur en pose une) |
| Espaces autour des valeurs | ignorés |

Un collage brut **URL + titre seulement** passe : sans extrait, sans rang et
sans date, rien n'est inventé pour combler — le rang reste inconnu, la date
devient `INCONNUE`, et l'adéquation ressort `NON MESURABLE`, ce qui est la
vérité.

### Les noms de champs sont souples

Vous n'avez pas à renommer ce que votre outil produit. Sont reconnus :

| champ | orthographes acceptées |
|---|---|
| url | `url` · `lien` · `link` |
| titre | `titre` · `title` · `intitule` |
| extrait | `extrait` · `snippet` · `description` · `resume` |
| rang | `rang` · `rank` · `position` |
| requête | `requete` · `query` · `q` · `recherche` |
| moteur | `moteur` · `engine` · `moteur_utilise` |
| date | `date_execution` · `date` · `executed_at` · `executee_le` |

**Sauf `provenance`**, qui n'a aucun alias : c'est la seule déclaration qui
engage, et elle s'écrit exactement.

### Une requête qui n'a rien donné se déclare aussi

```json
{"provenance": "EXÉCUTÉ HORS RADAR", "moteur": "mon-moteur",
 "requete": "sous-traitance frigorifique Namur",
 "date_execution": "2026-09-13T09:30:00+00:00", "resultats": []}
```

`0 résultat` est une **mesure** — le moteur a répondu. Ne pas la déclarer
laisserait croire que la requête n'a jamais été passée, ce qui est
`NON MESURÉ`, et ce n'est pas la même chose.

## 3 · Déposer le fichier

N'importe où. Aucun emplacement imposé.

## 4 · Lancer

```bash
python -m radar.cli import-recherche mon-export.json
```

Ce qui se passe, dans cet ordre :

```
import contrôlé → trouvailles → regroupement d'URL → entreprises (par domaine)
→ pages candidates → analyse commerciale → opportunités → 🟢🟡🟣🔵🔴 → actions
```

Options :

```
--sans-analyse     s'arrêter aux trouvailles
--top 30           détailler 30 opportunités au lieu de 20
--base chemin.db   écrire ailleurs que dans la base réelle
```

La commande écrit dans **`radar-reel.sqlite3`**, parce qu'un import porte des
résultats réels : un vrai moteur les a rendus, sur le vrai web. Il n'y a pas
de mode à choisir, et en laisser un ouvrirait la porte à des lignes réelles
écrites dans la base de démonstration.

## 5 · Lire

Le rapport sort directement. Ensuite, à tout moment :

```bash
python -m radar.cli opportunites            # la liste, la plus forte d'abord
python -m radar.cli opportunites --complet  # les fiches entières
python -m radar.cli entreprises             # ce qui est entré au registre
python -m radar.cli trouvailles             # ce qu'un moteur a montré
python -m radar.cli recoupement             # ce que chaque moteur apporte SEUL
python -m radar.cli suivre <id> --statut …  # le suivi commercial
```

---

## Ce que le radar N'AFFIRMERA JAMAIS sur un import

- qu'il a interrogé le moteur — la source reste marquée `import:` et le
  journal des exécutions porte `EXÉCUTÉ HORS RADAR` ;
- qu'il a lu la page — un titre et deux lignes d'extrait ne sont pas une
  page. `PAGES → réellement collectées` restera à `0` tant qu'aucune collecte
  n'aura eu lieu ;
- qu'une entreprise est identifiée — l'entité est désignée par son
  **domaine**, avec l'état de son identité, presque toujours `INCONNUE`. Un
  nom cité dans un titre n'est jamais pris pour le propriétaire du site ;
- un chiffre qu'il n'a pas lu — véhicules, tonnage, chauffeurs, CA, marge,
  coût/km, durée, volume, certifications, licences, agréments, capacité,
  échéance non prouvée : tout cela reste `À CONFIRMER`, et la marge reste
  `NON MESURÉE`.

## Et ce qu'il ne fera jamais non plus

- **supprimer une affaire parce qu'elle est loin.** La distance entre dans
  l'effort opérationnel et le classement, nulle part ailleurs ;
- **rejeter sur un score faible.** 🔴 est un rejet *objectif* établi et
  motivé. Une affaire difficile, volumineuse ou exigeant du recrutement reste
  🟡, 🟣 ou 🔵 ;
- **avantager un marché public.** Un avis de marché passe par le même moteur
  qu'une page d'entreprise. La question est « comment entrer sur ce marché »,
  jamais « d'où vient l'avis » ;
- **jeter un marché déjà attribué.** S'il porte un titulaire identifiable, il
  devient une piste : `DÉVELOPPER` / `CONTACTER LE TITULAIRE` ;
- **fusionner deux besoins sur une ressemblance de vocabulaire.** Le
  rapprochement exige la même organisation ; sinon les deux restent séparés,
  et le refus est compté.

---

## Modèle prêt à remplir

`fixtures/modele-export-externe.json` — trois requêtes, la structure complète,
et rien à inventer d'autre que vos résultats.
