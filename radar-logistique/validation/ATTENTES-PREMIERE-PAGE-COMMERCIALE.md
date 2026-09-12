# ATTENTES — PREMIÈRE PAGE COMMERCIALE RÉELLE

**Écrit le 12 septembre 2026, AVANT que la page n'existe dans le dépôt.**
Horodaté par le commit qui l'introduit.

## État de l'accès

```
https://colisprive.be/devenir-partenaire-livraison/            000
https://www.leroylogistique.com/demande-partenaire-transport/  000
https://colisprive.be/                                         000
https://www.leroylogistique.com/                               000
```

Le réseau sortant reste fermé. La page doit être fournie.

## CE QUE LE HARNAIS SAIT LIRE AUJOURD'HUI — mesuré, pas supposé

`sources/page_web.yaml` déclare **6 pistes de lecture HTML** : intitulé,
acheteur, objet, contact_email, téléphone, langue, canonique. Confronté aux
18 informations demandées :

| | voie d'extraction |
|---|---|
| entreprise / demandeur, besoin exact, contact | ✅ piste HTML déclarée |
| zone, cadence, véhicules, chauffeurs, échéance, montant | ⚠ **carte de champ JSON seulement** — inutile sur une page HTML |
| type de prestation, volume, durée, horaires, kilomètres, exigences, conditions d'accès, procédure, unité du montant | ❌ **aucune voie** |

**9 des 18 informations n'ont aucun moyen d'être extraites. 6 autres n'ont
qu'une carte JSON, inopérante sur du HTML brut.**

## LA PRÉDICTION QUI ENGAGE

> **1.** Le radar extraira **3 à 6 champs structurés** sur 18. Les autres
> sortiront `INCONNU`.
>
> **2.** `POTENTIEL = NON MESURABLE` — et **pas** parce que la page ne
> contient pas l'information, mais parce que **le lecteur n'a aucun moyen de
> tirer un nombre d'une phrase**. Volume, cadence, véhicules, kilomètres,
> durée : tout cela vit en prose sur une page commerciale, et rien ne va le
> chercher.
>
> **3.** Les couches sémantiques, elles, fonctionneront : nature, métier,
> rôle, absence de procédure sont lus sur le TEXTE VISIBLE ENTIER, pas sur
> des champs. J'attends `NATURE = FAIT`, `ÉTAT = HORS PROCÉDURE`,
> `ACTION = CONTACTER L'ENTREPRISE`.
>
> **4.** Verdict attendu : **🟠 À QUALIFIER** — un besoin réel, reconnu, sans
> aucune économie mesurable.

## Ce que ça voudrait dire

Si la prédiction se vérifie, le constat n'est pas « le radar échoue ». C'est :

> **La chaîne DÉCOUVERTE → PAGE → QUALIFICATION fonctionne.
> La chaîne PAGE → ÉCONOMIE n'existe pas encore.**

Le chaînon manquant est un **extracteur de faits économiques en prose** :
lire « 15 à 20 tournées par jour » ou « véhicule utilitaire de 12 m³ exigé »
et en faire un nombre. Aucune ligne du dépôt ne fait ça aujourd'hui.

## Ce qui compterait comme une SURPRISE

- un montant ou un volume extrait alors qu'aucune piste ne le cherche ;
- un état de procédure conclu sur une page qui n'en contient pas ;
- un verdict 🟢 À ATTAQUER sans aucune donnée économique ;
- un besoin réel classé ⚪ PAS ENCORE UNE OPPORTUNITÉ.

## La règle que je m'impose pour cette campagne

**Aucune piste d'extraction ajoutée avant d'avoir vu la page.** En ajouter
maintenant reviendrait à deviner ce qu'elle contient, puis à mesurer ma propre
devinette. Le harnais reste exactement dans l'état ci-dessus.
