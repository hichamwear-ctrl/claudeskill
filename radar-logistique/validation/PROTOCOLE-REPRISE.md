# PROTOCOLE DE REPRISE — qualification externe

Ce document CLÔT un chantier. Il n'en ouvre aucun.

Il ne contient aucun code, aucune heuristique, aucun adaptateur. Le prochain
gain ne viendra pas d'une modification du moteur : il viendra de l'accès aux
données réelles.

---

## 1. VERDICT FINAL

> **Détection commerciale effectuée, qualification externe bloquée par
> l'egress de l'environnement.**

Mesuré le 2026-09-12, journal complet dans
`validation/acces/2026-09-12-trois-prospects.json` :

| fait mesuré | valeur |
|---|---|
| URL candidates testées | **4** |
| DNS résolu | **4 / 4** |
| pages externes réellement reçues | **0** |
| contenus lisibles | **0** |
| besoins commerciaux confirmés par lecture de page | **0** |
| octets reçus provenant des sites visés | **0** |

Cinq voies essayées, cinq refus identiques : curl HTTPS via proxy
(`CONNECT tunnel failed, 403`), curl HTTP via proxy
(`x-deny-reason: host_not_allowed`), curl hors proxy (même gateway),
Chromium 1194 via Playwright (`net::ERR_TUNNEL_CONNECTION_FAILED`),
WebFetch (`EGRESS_BLOCKED`).

Témoin de sanité, même commande, mêmes réglages : `pypi.org` répond
**200 · 251 417 octets**. L'outil de test est sain ; le mur existe.

**Le blocage est la liste blanche d'egress du réseau.** Ce n'est ni une
panne, ni un refus des sites visés, ni un défaut du radar.

**`NON MESURÉ ≠ 0`.** Les barreaux « formulaire/contact » et « besoin
commercial observable » sont NON MESURÉS, jamais « non » : personne n'a
regardé. Le potentiel de ces prospects n'est pas nul, il est inconnu.

### Interdiction portée par ce verdict

**Aucun nouvel adaptateur, aucun collecteur, aucun relais, aucun
contournement réseau ne doit être développé pour franchir ce blocage.**
Un mur d'egress ne se contourne pas par du code ; le tenter produirait de
l'infrastructure invérifiable et zéro donnée.

---

## 2. TERMINOLOGIE — ce que la mesure dit exactement

La mesure `recherche` du 2026-09-12 (empreinte `8996d85be77d…`) vaut :

| | |
|---|---|
| résultats de recherche observés | **14** |
| signaux commerciaux forts détectés **sur titre + URL uniquement** | **3** |
| pages externes réellement lues | **0** |
| besoins confirmés par lecture du contenu | **0** |
| CA mesuré | **0 €** |

> **« prospects / signaux détectés » ≠ « opportunités confirmées ».**

Les trois signaux forts — Le Roy Logistique, transporteur DHL, Colis Privé
BeLux — sont des **prospects commerciaux détectés sur un titre**. Aucun
n'est une opportunité confirmée. La frontière reste
`DÉCOUVERTE (titre + URL)` → `QUALIFICATION (page réellement lue)`.

### Un piège de lecture à connaître

`python -m radar.cli validation` affiche `OPPORTUNITÉS RÉELLES : 3`.

Ce 3-là **n'est pas** celui des 3 signaux ci-dessus. Il compte les *mesures*
dont `porte_un_besoin` est vrai (recherche du 05/09, marchés publics du
12/09, recherche du 12/09). La coïncidence des deux chiffres est
trompeuse, et l'intitulé « OPPORTUNITÉS RÉELLES » désigne en réalité des
mesures, pas des opportunités.

C'est un défaut d'intitulé dans `radar/validation.py`. **Il n'est pas
corrigé ici** : ce chantier interdit toute modification du moteur. Il est
consigné pour que personne ne lise ce 3 comme trois affaires gagnées.

---

## 3. ÉTAT DU MOTEUR — figé

Aucun fichier sous `radar/`, `tests/`, `sources/`, `config/` ou `outils/`
n'a été modifié depuis `4e72a04` (vérifiable : `git diff 4e72a04..HEAD --
radar/ tests/ sources/ config/ outils/` est vide).

Inchangés, et à ne pas changer avant d'avoir observé de vraies pages :
qualification · procédure · nature · activité · portée · rôle · score · CA ·
capacité · classification · priorité · alertes · vocabulaire · collecteurs ·
persistance.

Pas de correction P1-B. Pas de nouvelle heuristique.

---

## 4. CE QU'IL FAUT CAPTURER, DEPUIS UNE MACHINE CONNECTÉE

Quatre cibles :

| # | prospect | URL demandée |
|---|---|---|
| 1 | Le Roy Logistique | `https://www.leroylogistique.com/demande-partenaire-transport/` |
| 2 | DHL transporteur | `https://transporteur.dhl.fr/` |
| 3 | DHL Freight Belgique | `https://www.dhl.com/be-fr/home/nos-divisions/fret/service-client/devenir-partenaire.html` |
| 4 | Colis Privé BeLux | `https://colisprive.be/devenir-partenaire-livraison/` |

Pour **chacune**, conserver les sept éléments suivants — la capture sans sa
provenance ne vaut rien, car on ne saurait plus ce qui a été réellement reçu :

1. **URL demandée** (telle quelle, avant toute redirection)
2. **URL finale** (après redirections ; si elle diffère, c'est un fait)
3. **date et heure** de la requête, avec fuseau
4. **statut HTTP** réellement renvoyé
5. **HTML brut réellement reçu** — octets tels quels, sans reformatage,
   sans « nettoyage », sans rendu JavaScript décrit comme du HTML reçu
6. **taille** en octets
7. **SHA-256** des octets du fichier

Commande suffisante, depuis une machine connectée :

```sh
for u in \
  https://www.leroylogistique.com/demande-partenaire-transport/ \
  https://transporteur.dhl.fr/ \
  https://www.dhl.com/be-fr/home/nos-divisions/fret/service-client/devenir-partenaire.html \
  https://colisprive.be/devenir-partenaire-livraison/
do
  f="capture-$(echo "$u" | sha256sum | cut -c1-12).html"
  curl -sSL --compressed -o "$f" \
       -w '%{url_effective}\t%{http_code}\t%{size_download}\n' "$u" \
       | tee -a provenance.tsv
  printf '%s\t%s\t%s\n' "$u" "$(date -Is)" "$(sha256sum "$f" | cut -d' ' -f1)" \
       >> provenance.tsv
done
```

### Règles de dépôt

- Les HTML vont dans `validation/pages_reelles/`, **jamais** dans les
  fixtures de test : une page réelle qui devient une fixture cesse d'être
  une mesure.
- Chaque HTML est accompagné de sa provenance. **Une capture sans
  provenance est refusée**, quelle que soit sa qualité apparente.
- Un HTML récupéré par un tiers est recevable **à condition** que sa
  provenance dise qui l'a récupéré, quand, et comment. Sinon, c'est une
  donnée inventée.
- **Ne jamais** déposer un résumé, une transcription, une reformulation ou
  une description de page à la place du HTML. Un résumé écrit par un modèle
  n'est pas une observation.

---

## 5. CE QU'ON EXÉCUTE ENSUITE — LE PIPELINE EXISTANT, INCHANGÉ

```
recenser  →  sonder  →  traiter  →  rapport  →  notifier
```

Aucune option nouvelle, aucun paramètre ajusté, aucun poids retouché.
`recenser` en premier : il mesure quelles clés existent réellement dans les
pages, avant que quoi que ce soit ne les interprète.

Pour **chaque page**, mesurer **séparément** — et ne jamais déduire l'un de
l'autre :

| mesure | ce qu'elle vaut |
|---|---|
| page réellement reçue | octets reçus > 0, statut HTTP à l'appui |
| contenu lisible | du texte a été extrait du HTML |
| besoin commercial observable | la page énonce un besoin, cité mot pour mot |
| nature | FAIT · SIGNAL · HYPOTHÈSE |
| état | tel que la page l'affiche |
| action | ce que le moteur propose |
| CA | mesuré, ou `NON MESURÉ` |
| contact / formulaire | **uniquement si réellement observé dans la page** |

Si l'egress est ouvert au lieu d'être contourné par des captures :
**relancer exactement les mêmes tests sur exactement les mêmes URL**, et ne
rien changer au moteur avant d'avoir observé les résultats. Une
qualification discutable sur une vraie page se **mesure d'abord** ; elle ne
se corrige pas dans le même geste.

---

## 6. TABLEAU FINAL

État au 2026-09-12. Ce tableau se remplit après capture ou ouverture de
l'egress — pas avant.

| Prospect | HTTP | Page reçue | Besoin observé | Nature | État | Action | CA |
|---|---|---|---|---|---|---|---|
| Le Roy Logistique | 403 *(gateway)* | NON — 0 o | NON MESURÉ | NON MESURÉ | NON MESURÉ | NON MESURÉ | NON MESURÉ |
| DHL transporteur | 403 *(gateway)* | NON — 0 o | NON MESURÉ | NON MESURÉ | NON MESURÉ | NON MESURÉ | NON MESURÉ |
| DHL Freight Belgique | 403 *(gateway)* | NON — 0 o | NON MESURÉ | NON MESURÉ | NON MESURÉ | NON MESURÉ | NON MESURÉ |
| Colis Privé BeLux | 403 *(gateway)* | NON — 0 o | NON MESURÉ | NON MESURÉ | NON MESURÉ | NON MESURÉ | NON MESURÉ |

Le `403` est celui du gateway d'egress (`host_not_allowed`), **pas** celui
des sites : aucun de ces quatre serveurs n'a jamais été joint.

Les colonnes Nature · État · Action · CA sont vides parce qu'elles
qualifient une **page**. Le moteur a bien produit une détection sur les
titres (Le Roy 55 · DHL transporteur 45 · Colis Privé 45, tous trois
🟢 DIRECT · FAIT · CONTACTER L'ENTREPRISE ; DHL Freight 45 ⚪ HYPOTHÈSE) —
mais c'est une **détection de titre**, et elle n'a pas sa place dans ces
colonnes-là. Les y écrire ferait passer un titre pour une page lue.

---

## 7. CRITÈRE DE RÉUSSITE DU PROCHAIN JALON

Le prochain vrai jalon n'est **pas** « plus de tests verts ». 617 tests
verts ne valent pas une affaire.

```
SOURCE ACCESSIBLE
  → PAGE RÉELLEMENT LUE
    → BESOIN COMMERCIAL OBSERVÉ
      → QUALIFICATION
        → PERSISTANCE
          → RAPPORT
            → ALERTE
```

La chaîne entière, sur une seule page réelle. Aujourd'hui elle s'arrête au
premier maillon, et c'est un problème d'accès, pas de logiciel.
