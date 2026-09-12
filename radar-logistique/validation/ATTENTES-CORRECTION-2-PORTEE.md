# CORRECTION 2 — PORTÉE DES EXCLUSIONS · prédiction figée AVANT le code

Figée le 2026-09-12, avant toute modification du moteur.
Commit de cette prédiction : à faire AVANT le commit de la correction.

## Ce qui a été mesuré d'abord (état réel, moteur intact `1af6344`)

Page conservée : `validation/pages_reelles/2026-09-12-entreprise-fed491c2e943.html`

```
CHAMPS LUS PAR LE LECTEUR DE PAGE
  intitule    59 car.   « Colis Privé : le transporteur de colis qui fait un carton ! »
  acheteur    17 car.   « Colis Privé BeLux »
  objet      148 car.   « La livraison rapide et flexible, c'est notre spécialité… »
  texte     3326 car.   (la page entière)

CE QUI ATTEINT LE MOTEUR AUJOURD'HUI
  opp.intitule  59 car.
  opp.texte    210 car.   (objet + intitulé)
  opp.corps    148 car.   (objet seul)

OÙ EST « ADR » ?
  intitulé       non
  texte          non
  corps          non
  page entière   OUI, position 3285 :
      « …À propos CGU Mentions légales Normes ADR © 2026 Colis Privé par CEVA Logistics »

VERDICT ACTUEL
  ⚪ PAS ENCORE UNE OPPORTUNITÉ · CAPTER · CLASSER SANS SUITE
  motif    : « aucun fait commercial observé sur cette page »
  familles : []
  score    : 45 — NON MESURABLE
  rejets   : aucun
```

## CORRECTION À MA PROPRE DÉMONSTRATION D

La démonstration D annoncée avant approbation disait :

> `corps complet (tel quel)  exclusions=['adr']  → 🔴 REJET · ABANDONNER`

Elle était juste sur le **mécanisme** et fausse sur l'**état du dépôt** : elle
avait été obtenue en injectant à la main les 3 326 caractères de la page dans
`corps`, c'est-à-dire dans l'état *postérieur* à la CORRECTION 1.

**Sur le dépôt tel qu'il est aujourd'hui, la page Colis Privé n'est pas
rejetée pour ADR.** Le mot n'atteint jamais le moteur. GAP 2 est **latent** :
il ne se déclenche qu'une fois GAP 1 corrigé. C'est GAP 1, et lui seul, qui
bloque la page aujourd'hui — faute de matière, pas faute d'un mot.

## PRÉDICTION — ce que CORRECTION 2 SEULE doit produire

| | prédiction |
|---|---|
| Catégorie | ⚪ PAS ENCORE UNE OPPORTUNITÉ — **inchangée** |
| Action | CLASSER SANS SUITE — inchangée |
| Score | 45, NON MESURABLE — inchangé |
| Familles | `[]` — inchangées |
| Rejet ADR | **non** : origine « pied de page » → non caractérisante |
| Réserve ADR | **oui, visible**, avec origine et extrait |

**Je ne prédis PAS 🟢 DIRECT.** Le résultat attendu énoncé à l'approbation
(« 🟢 DIRECT / CONTACTER ou POSTULER avec une réserve ADR ») ne peut pas être
atteint par la CORRECTION 2 seule : les 148 caractères disponibles ne
contiennent aucun fait commercial. Obtenir 🟢 à ce stade signifierait que j'ai
forcé le verdict. Si 🟢 sort, c'est un défaut, pas un succès.

Le 🟢 attendu, s'il doit venir, viendra de la CORRECTION 1.

## CE QUI DOIT RESTER BLOQUANT

- « ADR » dans l'intitulé → 🔴 REJET
- « ADR » dans l'objet, les conditions, les exigences → 🔴 REJET
- « matières dangereuses » porté par une rubrique ou un CPV → 🔴 REJET
- origine inconnue ou non déclarée → **caractérisante par défaut** → 🔴 REJET
- exclusion bloquante ET exclusion de pied de page ensemble → 🔴 REJET

## CE QUI NE DOIT RIEN CHANGER

- Une source sans segments (toutes les fixtures, tous les portails) :
  verdict strictement identique, 483 assertions vertes, aucune réécrite.
- Une exclusion écartée pour portée ne promeut rien : score, catégorie,
  priorité identiques à ceux d'une page où le mot est absent.
- `POTENTIEL = NON MESURABLE` ne bloque rien, ni avant ni après.
