# PROVENANCE INCOMPLÈTE — deux pages du 2026-09-12

Les deux pages `transporteur.dhl.fr` et `colisprive.be/devenir-partenaire-livraison/`
ont été **collées dans la conversation**, pas transmises comme fichiers.

## Sur les 7 éléments exigés par `PROTOCOLE-REPRISE.md`

| élément | état |
|---|---|
| URL demandée | déduite du `<link rel="canonical">` de la page — **pas observée au transport** |
| URL finale | **NON FOURNI** |
| date/heure de récupération | **NON FOURNI** (la date inscrite est celle du dépôt, pas du fetch) |
| statut HTTP | **NON FOURNI** |
| HTML brut | **transcrit**, pas reçu comme fichier |
| taille d'origine | **NON FOURNI** |
| SHA-256 d'origine | **NON FOURNI** |

Les `sha256` inscrits sont ceux de **ce qui a été déposé**, pas des octets
envoyés par les serveurs. Ils servent à recontrôler la mesure, pas à prouver
la collecte.

## Fidélité de la transcription — une distorsion connue et déclarée

Les deux fichiers sont des transcriptions. Tout le **texte, les titres, les
listes, les libellés et les champs de formulaire** sont repris mot pour mot.
Ont été retirés : blocs CSS en ligne, déclarations `@font-face`, corps des
scripts, et une partie des attributs `data-settings` d'Elementor.

**Conséquence mesurable, à ne pas oublier** : la page DHL déposée fait
49 991 octets là où la page collée en faisait environ 95 000. Le rapport
« texte lisible / taille du fichier » vaut donc **13 %** ici, alors qu'il
serait de l'ordre de **7 %** sur la page réelle. Toute conclusion sur la
densité de balisage tirée de ces deux fichiers est fausse. Les
qualifications, elles, reposent sur le texte, qui est intact.

## Familles

Les deux pages sont inscrites en famille **A `entreprise`** — la famille est
celle du TYPE DE SOURCE (une entreprise privée qui publie son besoin sur son
propre site), jamais celle du thème. Le thème est le partenariat ;
la famille **H `partenariat` reste NON MESURÉE**.

## Ce qui manque encore

Deux cibles sur quatre n'ont rien donné : **Le Roy Logistique** et
**DHL Freight Belgique**.
