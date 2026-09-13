# MESURE DE RÉFÉRENCE — deux pages réelles, 2026-09-12

Ce document **fige** un résultat de mesure. Ce n'est pas une vérité
commerciale : c'est ce que LE RADAR a lu sur DEUX pages, un jour donné,
avec une provenance incomplète.

---

## 1. RÉSULTATS FIGÉS

### Colis Privé BeLux — `colisprive.be/devenir-partenaire-livraison/`
`sha256 c5e20010e7bd…` · 64 190 o · **PROVENANCE INCOMPLÈTE**

| | |
|---|---|
| besoin | **confirmé par lecture réelle** — « Vous êtes une entreprise de livraison ? Rejoignez dès maintenant notre réseau de partenaires. » |
| nature | ◆ FAIT |
| état | 🟢 POSTULABLE — **sous réserve expresse** : le verdict repose sur une preuve non pertinente (§3) |
| action | POSTULER |
| contact | `donnees-personnelles@colisprive.com`, observé littéralement dans le texte · formulaire à 15 champs |
| CA | **NON MESURABLE** — aucun montant publié |
| catégorie / score | 🟢 DIRECT · 55/100 |

### DHL transporteur — `transporteur.dhl.fr`
`sha256 e0a7191f9b39…` · 49 991 o · **PROVENANCE INCOMPLÈTE**

| | |
|---|---|
| besoin | **confirmé par lecture réelle** — « Nous recherchons des partenaires de transport qualifiés sur une base indépendante » |
| nature | ◆ FAIT |
| état | ❓ À VÉRIFIER — le moteur refuse de conclure, et dit pourquoi |
| action | VÉRIFIER L'ÉTAT À LA SOURCE |
| contact | **aucun e-mail lisible** · formulaire de candidature à 25 champs observé |
| CA | **NON MESURABLE** |
| catégorie / score | 🔵 PROSPECT · 55/100 |

---

## 2. TITRE + URL  vs  PAGE COMPLÈTE

Mesure faite avec le **même adaptateur** (`entreprise`), le **même mode**
(RÉEL), le **même moteur**. Seul le contenu de l'entrée change.

| | TITRE + URL | PAGE COMPLÈTE |
|---|---|---|
| **Colis Privé** — catégorie | 🟢 DIRECT | 🟢 DIRECT |
| score | 45/100 | **55/100** |
| nature | FAIT | FAIT |
| état | HORS PROCÉDURE *(confiance nulle)* | **POSTULABLE** *(moyenne)* |
| action | CONTACTER L'ENTREPRISE | **POSTULER** |
| contact | AUCUN | **`donnees-personnelles@colisprive.com`** |
| **DHL** — catégorie | 🟢 DIRECT | **🔵 PROSPECT** |
| score | 45/100 | **55/100** |
| nature | FAIT | FAIT |
| état | HORS PROCÉDURE *(nulle)* | **INCONNU — À VÉRIFIER** *(nulle)* |
| action | CONTACTER L'ENTREPRISE | **VÉRIFIER L'ÉTAT À LA SOURCE** |
| contact | AUCUN | AUCUN |

### Ce que le titre permettait de détecter
Le titre seul suffit à établir **la nature (FAIT), le demandeur et le
domaine**. Les deux pages sortent 🟢 DIRECT · 45 · CONTACTER L'ENTREPRISE.
Un commercial peut agir sur cette seule base : il sait qui appeler.

### Champs supplémentaires réellement observés grâce à la page
`acheteur` (og:site_name) · `objet` (meta description) · `langue` ·
`canonique` · et pour Colis Privé seulement **`contact_email`**, le seul
champ à valeur commerciale directe.

### Pourquoi les verdicts changent
- **Score +10, sur une seule ligne.** `adéquation opérationnelle` passe de
  **12,5 → 25**. Titre : « domaine reconnu, **spécialité NON IDENTIFIÉE** —
  « transport » ». Page : « dans mon métier : `dernier_kilometre`,
  `logistique_entrepot` — « coursier » ». Les sept autres lignes du barème
  sont **identiques** — toutes `NON PUBLIÉ`.
- **État.** Le titre ne contient aucune formulation d'état → HORS PROCÉDURE.
  La page en contient, et c'est là que les deux se séparent : DHL passe en
  ❓ À VÉRIFIER *parce que le moteur détecte des marqueurs qu'il refuse
  d'apparier* ; Colis Privé passe en POSTULABLE **par une preuve fausse**.
- **DHL descend de 🟢 à 🔵.** Lire la page a **dégradé** sa catégorie. Ce
  n'est pas une régression : le moteur a découvert qu'il ne savait pas, et
  l'a dit. INCERTAIN vaut mieux qu'INCORRECT.

### Ce qui est réellement exploitable commercialement
1. **Le contact Colis Privé** — un e-mail qu'aucun titre n'aurait donné.
2. **Les deux formulaires** (15 et 25 champs) : la porte d'entrée est
   identifiée et le coût d'approche estimable.
3. **Le besoin cité mot pour mot**, utilisable dans un message de prospection.
4. **Le périmètre DHL** : 5 domaines nommés (enlèvement/livraison, enveloppe,
   linehaul, dépôt en opérateur agréé, vélo) et 7 conditions préalables.
5. **Les exigences DHL** (K bis < 3 mois, licence, URSSAF, régularité
   fiscale) : de quoi décider d'y aller ou pas, avant d'y passer du temps.

### Le résultat négatif, qui compte autant
Lire la page entière **n'a révélé aucun** montant, échéance, cadence, durée,
véhicule requis ni exigence exploitable par l'adaptateur. `recenser` le
confirme : **13 champs sur 20 à 0 %**. La qualification apporte le contact
et la spécialité. Elle **n'apporte pas** le CA. `sources/entreprise.yaml`
reste donc honnêtement `verifie: false`.

---

## 3. ANOMALIE — le verdict d'état de Colis Privé repose sur une preuve fausse

**Reproduite**, sur la page réelle, et sur cas minimal.

### La preuve exacte, telle que le moteur l'imprime
```
[formulation interprétée] [corps du document]
« corps du document : « actuellement » porte sur « offres »
  — contenu, unité 47 : « Fondée par Kris en 2001 … la société emploie
  actuellement 47 personnes à temps plein… » »  → POSTULABLE
```

### Unité et concept
| | |
|---|---|
| unité | `contenu`, unité 47 (et 48) — niveau **bloc** |
| « actuellement » | concept **`ouverture`** (`procedure.py:302`) · provient d'un **témoignage de partenaire sur les effectifs** |
| « offres » | concept **`depot`** (`procedure.py:270`) · provient de la **`<meta name="description">`** : « des **offres complètes** avec différents modes de livraison » |

### Pourquoi la preuve atteint l'interprétation d'état
`trouver("depot", …)` est une recherche **globale** sur le texte aplati.
La page contient trois « offres » : deux sont « offres **commerciales** »
(cases de consentement RGPD), correctement annulées par
`SUITES_QUI_ANNULENT`. La troisième, « offres **complètes** », **n'est pas
dans la liste d'annulation** — elle survit. Le lecteur de page place la
`<meta description>` **en tête du champ `texte`** ; ce marqueur entre donc
dans la matière de l'interprétation alors qu'**il est invisible pour un
lecteur humain**. Un mot d'`ouverture` trouvé ailleurs s'apparie alors avec
lui.

### Mesure d'ablation — lequel des deux porte le verdict
| variante | état | preuves | action | catégorie / score |
|---|---|---|---|---|
| page telle quelle | POSTULABLE | 2 | POSTULER | 🟢 DIRECT · 55 |
| sans « actuellement » | **POSTULABLE** | 2 | POSTULER | 🟢 DIRECT · 55 |
| sans « offres complètes » | **HORS PROCÉDURE** | **0** | **CONTACTER L'ENTREPRISE** | 🟢 DIRECT · 55 |
| sans les deux | HORS PROCÉDURE | 0 | CONTACTER L'ENTREPRISE | 🟢 DIRECT · 55 |

**Deux enseignements.**
1. **« actuellement » n'est pas la cause.** Retiré, le verdict tient — porté
   par une **seconde preuve tout aussi fausse** : « « accepte » porte sur
   « offres » », tirée de « **J'accepte** de recevoir les **offres**
   commerciales ». Une case à cocher RGPD.
   L'élément porteur est le marqueur `depot` issu de la **meta description**.
2. **Le score et la catégorie ne bougent pas** (55, 🟢 DIRECT) dans les
   quatre variantes. L'état n'alimente ni le score ni la classification —
   la séparation tient. **Seule l'action change**, et c'est là que ça coûte.

### Vrai positif ou faux positif ?
**Vrai positif, preuve fausse, action fausse.** La page invite bel et bien à
candidater — un humain conclurait « c'est ouvert ». Mais le chemin y mène
par des mots sans rapport, et l'action produite, **POSTULER**, est
inadaptée : il n'y a aucune procédure à laquelle postuler, il y a une
entreprise à contacter. Sans la preuve fausse, le moteur dit
**CONTACTER L'ENTREPRISE** — ce qui est **plus juste**.

### Le phénomène existe-t-il sur d'autres pages ?
Testé sur les 4 pages réelles conservées.

| page | marqueurs `depot` | marqueurs `ouverture` | état conclu |
|---|---|---|---|
| Colis Privé /devenir-partenaire | `offres` | `actuellement`, `accepte` | **POSTULABLE** ⚠ |
| DHL transporteur | `candidature`, `offres`, `offre` | `disponible`, `en ligne`, `possible`, `active` | INCONNU — refuse d'apparier |
| Colis Privé accueil | `offre` | `disponible` | INCONNU |
| pypi.org/project/requests | — | — | HORS PROCÉDURE |

**1 cas sur 4.** DHL porte *plus* de marqueurs des deux concepts et conclut
quand même correctement « je ne sais pas » : la portée sémantique fonctionne
dans 3 cas sur 4. Le défaut n'est pas la règle d'appariement en général —
c'est un marqueur qui entre par une porte non surveillée.

### Hypothèse minimale, NON appliquée
> Un marqueur de concept issu d'une zone **invisible pour le lecteur humain**
> (`<meta description>`, balisage) ne devrait pas pouvoir porter à lui seul
> une lecture d'état. C'est la même règle que `portee_exclusions` applique
> déjà à la navigation et au pied de page.

Portée supposée : 1 page sur 4 mesurées. Bénéfice attendu : l'action passe
de POSTULER à CONTACTER L'ENTREPRISE sur un besoin privé. Risque : les vrais
marchés publics dont l'état n'apparaît QUE dans la description seraient
perdus — **non mesuré, et c'est la question à trancher avant de coder.**

**Aucune correction n'est appliquée.** Le moteur reste inchangé.
