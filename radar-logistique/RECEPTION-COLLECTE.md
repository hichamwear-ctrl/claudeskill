# TEST DE RÉCEPTION — brancher une vraie source

**À exécuter depuis une machine ayant un accès sortant.** L'environnement de
développement n'en a pas : la passerelle répond `403` au `CONNECT` pour
`publicprocurement.be`, `ted.europa.eu` et `data.gov.be`. Aucun sélecteur du
BDA n'a donc jamais rencontré la vraie page, et `sources/bda.yaml` porte
`verifie: false`.

Ce protocole ne demande aucune compétence en Python. Il produit, à chaque
étape, un **chiffre** — et s'arrête franchement quand quelque chose ne va pas.

---

## Avant de commencer

```bash
git clone <ce dépôt> && cd radar-logistique
python3 --version        # 3.11 ou plus
pip install pyyaml       # seule dépendance
```

---

## 1 · robots.txt et accès HTTP

```bash
curl -sS -o /dev/null -w "robots %{http_code}\n" https://www.publicprocurement.be/robots.txt
curl -sS -o /dev/null -w "page   %{http_code}\n" https://www.publicprocurement.be/bda
```

**Attendu :** deux fois `200`.
**Si `403`, `000` ou un blocage :** arrêter ici et le noter. Ce n'est pas un
défaut du radar — c'est un accès à obtenir.

---

## 2 · Collecte, sans ouvrir les fiches

Un premier passage court, pour voir si les sélecteurs de LISTE répondent.

```bash
python3 outils/collecter_bda.py --pages 2 --sans-detail \
        --sortie bda-brut.json --html-brut bda-pages
echo "code de sortie : $?"
```

| code | signification | quoi faire |
|---|---|---|
| `6` | **collecté, non vérifié** — le cas normal au premier essai | passer à l'étape 3 |
| `5` | aucune ligne extraite, pages HTML conservées | passer à l'étape 3, les sélecteurs sont faux |
| `4` | la page ne répond pas | relever le code HTTP affiché |
| `3` | chemin interdit par robots.txt | **s'arrêter** — pas de contournement |
| `2` | robots.txt illisible | **s'arrêter** — ne pas savoir n'autorise pas |
| `0` | impossible tant que `verifie: false` | — |

Le script affiche déjà : nombre de lignes par page, nouvelles, champs
réellement extraits, et **champs déclarés jamais trouvés**.

---

## 3 · Mesurer les sélecteurs sur les pages conservées

```bash
python3 outils/bac_a_sable_bda.py --html bda-pages/<une-page>.html
```

Sortie : combien de conteneurs, combien de lignes, et **pour chaque champ**
le taux de réponse avec un exemple. Tout champ à `0 %` désigne un sélecteur
faux.

> **Corriger `sources/bda.yaml`, jamais le code.** C'est un fichier de
> déclaration ; le moteur n'y touche pas.

Répéter 2 → 3 jusqu'à ce que tous les champs de liste répondent.

---

## 4 · Mesurer la FICHE d'un avis

C'est l'étape qui décide si le radar produira des opportunités attaquables
ou un nouveau tas de titres. Enregistrer la page d'un avis (clic droit →
enregistrer), puis :

```bash
python3 outils/bac_a_sable_bda.py --html bda-pages/<liste>.html \
                                  --avis bda-pages/<un-avis>.html
```

Sortie : `CHAMPS LISIBLES  n/8` sur `objet · montant · duree_mois ·
plateforme · lien_depot · lien_documents · contact_email · lots`.

**Seuil de réception :** `lien_depot` et `objet` doivent répondre. Sans le
guichet de dépôt, le radar ne pourra jamais dire POSTULER ; sans l'objet, il
ne pourra pas qualifier le métier.

Corriger `sources/bda.yaml` et recommencer.

---

## 5 · Quand tous les champs répondent

```bash
python3 outils/collecter_bda.py --pages 5 --sortie bda-brut.json
python3 -m radar.cli recenser --source bda --echantillon bda-brut.json
```

`recenser` mesure le taux de réponse de chaque clé. **Quand il affiche
« Tous les champs répondent »**, et alors seulement :

```yaml
# sources/bda.yaml
verifie: true
```

Relancer le collecteur : il sort maintenant en code `0`.

---

## 6 · Le cycle complet

```bash
python3 -m radar.cli --base radar.sqlite3 --reel traiter --source bda --entree bda-brut.json
python3 -m radar.cli --base radar.sqlite3 --reel rapport
python3 -m radar.cli --base radar.sqlite3 notifier --pour-de-vrai --dossier alertes
```

Puis **relancer les trois commandes à l'identique**. Attendu au second
passage : `nouveaux 0`, `alertes créées 0`, `fichiers écrits 0`. C'est la
preuve que la déduplication et l'idempotence tiennent sur données réelles.

---

## Ce qu'il faut rapporter

```
1. robots.txt              code HTTP
2. page de liste           code HTTP
3. lignes par page         n
4. champs de liste à 0 %   lesquels
5. fiches ouvertes         n
6. taux de fiches lisibles %
7. champs de fiche à 0 %   lesquels
8. lien_depot présent      oui / non
9. avis en base            n
10. opportunités POSTULABLES  n
11. CA identifié           €
12. alertes écrites        n
13. second passage         nouveaux / alertes  (attendu : 0 / 0)
```

Les lignes **8, 10 et 11** sont celles qui disent si le radar est devenu
commercialement exploitable. Les autres disent s'il fonctionne.

---

## Ce que ce protocole ne fait pas

Il ne contourne aucun blocage, ne fabrique aucune page, et ne corrige aucun
sélecteur à la place de l'opérateur. Tant qu'aucune page réelle n'a été
mesurée, `verifie: false` reste la vérité et le collecteur sort en code `6`.
