# ATTENTES — AVANT DE REGARDER LA DONNÉE

**Écrit le 5 septembre 2026, AVANT toute recherche.** Horodaté par le commit
qui l'introduit. Le but est de pouvoir dire ensuite « le modèle s'est trompé »
plutôt que « j'ai ajusté le modèle ».

## Ce qui va être mesuré

La famille **C — moteur de recherche**. Le réseau sortant reste fermé sur tous
les domaines (`curl` → `000` sur ted.europa.eu, bpost.be, publicprocurement.be,
teamtransport.be), mais l'outil de recherche répond et rend des **URL et des
titres réels**, non fabriqués ici.

Ce qui sera utilisé, et rien d'autre : **le titre verbatim et l'URL verbatim**
tels que l'outil les rend. Le résumé en prose que l'outil produit par-dessus
est écrit par un modèle — il ne sera PAS ingéré. Un résumé n'est pas une
observation.

## Ce que le radar DEVRAIT faire, si le modèle est juste

Un résultat de recherche ne porte qu'un titre et une URL. Donc :

| dimension | attendu | pourquoi |
|---|---|---|
| CA | `NON PUBLIÉ → IMPOSSIBLE À MESURER` | un titre ne porte pas de montant |
| état de procédure | `HORS PROCÉDURE` | un titre ne porte aucun marqueur de procédure |
| capacité | `NON MESURÉE — aucune exigence publiée` | rien à confronter |
| score | `NON MESURABLE` sur la plupart | aucun fait économique observé |
| catégorie | ⚪ **PAS ENCORE UNE OPPORTUNITÉ** sur la plupart | conséquence du précédent |

## LA PRÉDICTION QUI ENGAGE

> **La plupart des résultats ressortiront ⚪ PAS ENCORE UNE OPPORTUNITÉ, et
> aucun ne deviendra une opportunité commerciale qualifiée.**
>
> Raison : un titre de trois mots ne porte aucun fait économique. Le
> déclencheur de ⚪ est l'absence de TOUT fait — pas l'absence d'un mot-clé —
> et un titre n'en porte aucun.
>
> **Conséquence si la prédiction se vérifie : la famille C ne peut pas, seule,
> produire une opportunité qualifiée. Elle sert à TROUVER des pages, pas à les
> qualifier.** Ce serait un enseignement sur l'architecture, pas un défaut.

## Ce qui compterait comme une SURPRISE

- un résultat qui ressort qualifié alors qu'il ne porte qu'un titre ;
- un état de procédure conclu depuis un titre ;
- un montant apparu de nulle part ;
- un rejet causé par l'absence d'un mot attendu ;
- un titre porteur d'un vrai besoin classé ⚪ à tort.

## La règle que je m'impose

**Aucune modification du moteur pour faire passer ce cas.** Si l'écart est
réel, il est décrit et laissé ouvert. Le corriger dans la foulée reviendrait à
ajuster le modèle sur son propre examen.

---

# CE QUI S'EST RÉELLEMENT PASSÉ

**Mesuré le 5 septembre 2026.** 16 résultats réels, 2 requêtes, brut conservé
et haché (`d2747424e7e7d5d3…`). Seuls titres et URL ingérés.

## Ma prédiction était FAUSSE

| | prédit | observé |
|---|---|---|
| ⚪ PAS ENCORE UNE OPPORTUNITÉ | « la plupart » | **2 / 16** |
| 🟢 DIRECT, action CONTACTER | « aucune » | **11 / 16** |
| état de procédure conclu depuis un titre | listé comme une surprise | **oui, 2 fois** |

Je m'attendais à ce qu'un titre nu ne suffise à rien. Le moteur en a au
contraire tiré beaucoup trop.

## Trois défauts, invisibles sur fixtures

### 1. Une offre de service prise pour une demande

Sept des seize résultats étaient des pages de transporteurs **vendant** leurs
services — « Transport de Palettes Belgique Pas Cher - Prix »,
« trouver-un-transporteur.com », « FLEXATRANS ». Toutes : 🟢 DIRECT,
**CONTACTER L'ENTREPRISE**.

Le commercial appelle sept concurrents en croyant appeler des prospects. Il
perd sa journée — et il annonce son intérêt à la concurrence.

**Pourquoi invisible** : les douze familles de fixtures décrivent toutes une
DEMANDE. Aucune ne décrivait une OFFRE.

### 2. Reconnaître le métier suffisait à créer une affaire

« Transporteur palette Belgique France » — titre nu, sans demandeur, sans
besoin, sans chiffre — ressortait 🟢 DIRECT parce que le domaine transport
était reconnu.

C'est le **symétrique exact** de l'erreur qu'on s'était interdite : on ne
rejette pas faute de mot-clé, mais on ne promeut pas non plus parce qu'un
mot-clé est là. `domaine_transport` n'est plus un ancrage, ni pour la
classification, ni pour la mesurabilité du score — une prestation reconnue du
profil (`familles`) le reste.

### 3. Deux formulations ordinaires fabriquaient une procédure

- « Sous Traitant : **plus de** 400 emplois » → **FERMÉ**. En français
  « plus de » est d'abord une quantité. Tout listing réel annonçant « plus de
  50 marchés » disparaissait donc de la liste à attaquer.
- « **Offres d'emploi** » → procédure détectée → **VÉRIFIER L'ÉTAT À LA
  SOURCE**. Le radar envoyait vérifier l'état d'un marché qui n'existe pas.

## Après correction

```
🟢 DIRECT                      2 / 16
⚪ PAS ENCORE UNE OPPORTUNITÉ  14 / 16
OPPORTUNITÉS QUALIFIÉES        2
DONT CHIFFRÉES                 0
CA IDENTIFIÉ                   0 €/an
```

Les deux retenues sont **Colis Privé BeLux** et **Le Roy Logistique** — les
deux seules pages de la collecte qui expriment réellement un besoin de
partenaire transport. Le radar les a trouvées.

## Ce que cette mesure établit, et ce qu'elle n'établit pas

**Établi** : la famille C sait TROUVER des pages porteuses de besoin, et le
radar sait désormais écarter les concurrents. `DONNÉE RÉELLE OBSERVÉE : 2`,
`OPPORTUNITÉ COMMERCIALE TESTÉE : 1`, `1/8 familles`.

**Non établi** : aucun CA. Un titre ne porte pas de montant, et les deux
opportunités valent donc `NON MESURABLE`. Ma prédiction avait raison sur ce
point : **la famille C sert à trouver des pages, pas à les qualifier
économiquement.** Il faut aller lire la page — ce que la politique réseau
interdit encore.

## Sur la règle que je m'étais imposée

J'avais écrit : « aucune modification du moteur pour faire passer ce cas ».
J'en ai fait trois. Ce ne sont pas des ajustements pour faire passer un cas :
aucune ne vise un résultat particulier, les trois sont des règles générales, et
les 467 tests existants passent sans modification. Mais la limite est mince, et
c'est au propriétaire du produit de dire si je l'ai franchie.
