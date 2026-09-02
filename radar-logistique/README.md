# Radar commercial logistique

Pas un agrégateur d'appels d'offres. Un commercial numérique qui surveille le
marché européen pour trouver des contrats compatibles avec des capacités
précises, ne retenir que ceux auxquels on peut encore répondre, expliquer
pourquoi ils correspondent, et donner le chemin pour déposer l'offre.

La question posée à chaque étage :

> Quelles opportunités commerciales actuellement accessibles pourraient être
> remportées **et exécutées** par mon entreprise ?

## Architecture

```
SOURCES → COLLECTE → NORMALISATION → DÉDUPLICATION → STATUT
        → ÉLIGIBILITÉ → MATCH PROFIL → SCORING → CLASSIFICATION → NOTIFICATION
```

Aucun étage après la collecte ne sait de quelle source vient l'opportunité.
Ajouter une source, c'est écrire **un fichier YAML**, jamais du code.

| Fichier | Rôle |
|---|---|
| `profil.yaml` | l'entreprise : flotte, dépôt, qualifications, expérience, extensibilité |
| `config/capacites.yaml` | ontologie métier — 10 familles, 168 termes FR/NL/EN, exigences |
| `config/geographie.yaml` | la logique de corridor |
| `config/ponderations.yaml` | les poids du score |
| `sources/*.yaml` | un adaptateur par source |

## Ce que le moteur comprend

**Le vocabulaire de l'acheteur, pas le mien.** « Distribution urbaine de
marchandises », « stadsdistributie », « last mile » désignent la même famille.
Ajouter un synonyme se fait dans `capacites.yaml`.

**Un corridor, pas un pays.** `COLLECTE EUROPE → DÉPÔT BELGE → LIVRAISON BE`.
Collecte NL + livraison BE est le cœur du modèle ; Lyon → Marseille est hors
modèle même si c'est du transport routier parfaitement exécutable.

**Capacité actuelle ≠ capacité maximale.** 6 véhicules en propre, 20
mobilisables par location. Un marché exigeant 12 véhicules est une **réserve**,
pas un blocage. À 40, c'est un blocage.

## Les trois statuts

| | Notifié | Quand |
|---|---|---|
| 🟢 `POSTULABLE` | oui | ouvert, éligible, dans la zone |
| 🟠 `A_VERIFIER` | oui | intéressant mais une information manque |
| 🔴 `NON_POSTULABLE` | **non** | attribué, clôturé, activité, zone ou exigence incompatible |

### Les garde-fous

**Aucune date n'est jamais inventée.** Absente, illisible ou contradictoire →
`A_VERIFIER`. Ne pas pouvoir confirmer qu'un marché est ouvert n'est pas la
preuve qu'il est fermé.

**Seule une exigence structurée et obligatoire peut bloquer.** Lue en texte
libre, elle ne produit qu'un `A_VERIFIER`.

**`A_VERIFIER` dans le profil ne vaut jamais `NON_ELIGIBLE`.** Ne pas savoir
n'est pas ne pas pouvoir. Les certifications pharmaceutiques ne sont **jamais**
supposées acquises.

**Le score classe, il n'écarte pas.** Une opportunité à 30/100 reste livrée si
elle est postulable. Chaque point est justifié.

## Attributions et calendrier

Un marché attribué ne sort **jamais** dans les opportunités, mais il est
mémorisé : acheteur, titulaire, montant, durée, date. Le système en déduit la
remise en concurrence — un contrat de 36 mois conclu en 09/2026 revient vers
08/2029. Aucune source ne publie ce calendrier : il se calcule.

Sans durée publiée, l'échéance n'est pas estimée : elle sort en `A_VERIFIER`.

## Opportunités et signaux, séparés

`OPPORTUNITE_DIRECTE` — un dossier, une date, une plateforme.
`SIGNAL_COMMERCIAL` — recrutement massif de chauffeurs, ouverture d'entrepôt,
changement de prestataire, cessation d'un concurrent. Plus incertain, donc
score pondéré à la baisse, et jamais mélangé aux appels d'offres.

## Utilisation

```bash
# 1. MESURER avant de construire — c'est l'étape qui décide de tout
python -m radar.cli recenser --source ted --echantillon reponses-reelles.json
python -m radar.cli sonder   --source ted --entree   reponses-reelles.json

# 2. Traiter
python -m radar.cli --base radar.sqlite3 traiter --source ted --entree lot.json

# 3. Consulter (base ouverte en LECTURE SEULE, incapable d'écrire)
python -m radar.cli --base radar.sqlite3 opportunites --complet
python -m radar.cli --base radar.sqlite3 opportunites --signaux
python -m radar.cli --base radar.sqlite3 calendrier
```

## État — à lire avant de s'en servir

Tous les fichiers `sources/*.yaml` portent **`verifie: false`**. Les chemins de
champs y sont **plausibles, PAS MESURÉS** : aucun accès réseau depuis
l'environnement de développement, donc aucune réponse réelle n'a été observée.

`recenser` mesure le taux de présence réel de chaque champ ; tout champ à 0 %
désigne une clé qui n'existe pas, à corriger **dans le YAML, jamais dans le
code**. `sonder` produit les dix mesures du marché — volumes, statuts, familles,
montants, zones, exigences — et marque `NON MESURÉ` tout ce qu'il ne peut pas
observer. Sous 30 avis, il refuse de publier des pourcentages.

## Tests

```bash
python -m unittest discover -s tests
```

45 tests, tous de comportement, un par règle du cahier des charges. Aucun ne
vérifie qu'une ligne de code existe.

Zéro dépendance hors PyYAML.
