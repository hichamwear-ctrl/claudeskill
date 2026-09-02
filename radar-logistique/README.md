# Radar de contrats logistiques

Trouve des marchés **sur lesquels on peut encore déposer une offre**. Ce n'est
pas une veille informative : un avis clôturé, attribué ou purement informatif
n'apparaît jamais dans les opportunités à traiter.

## Le critère unique

> Est-ce que je peux encore postuler aujourd'hui ?

Le filtre porte sur l'**actionnabilité** — des faits vérifiables : une date de
clôture, un type d'avis, une exigence de sélection. Il ne porte jamais sur le
jugement : « est-ce une bonne affaire » reste la décision de l'exploitant, et le
score ne fait que trier et annoter.

| Statut | Notifié | Pourquoi |
|---|---|---|
| `ouvert` | oui | échéance à venir |
| `echeance_inconnue` | **oui** | date illisible — livré par précaution, signalé |
| `cloture` | non | échéance dépassée |
| `attribue` | non | marché déjà attribué — mais **conservé** pour le calendrier |
| `informatif` | non | aucun dépôt attendu |

### Les deux garde-fous

**Une échéance illisible ne fait jamais disparaître une annonce.** Rater un
marché ouvert coûte un contrat ; recevoir un marché clôturé coûte trente
secondes. Les coûts sont asymétriques : en cas de doute, ça part.

**Seule une exigence structurée peut bloquer.** Une exigence lue dans un texte
libre ne produit qu'une réserve, et une capacité non vérifiée au profil ne
bloque jamais — « je ne sais pas » n'est pas « je ne peux pas ».

## La fiche d'action

Sept champs, dans cet ordre. Un champ absent est écrit `NON PUBLIÉ`, jamais
comblé par une valeur plausible :

date limite · montant estimé · organisme acheteur · ce qui est demandé ·
conditions pour répondre · où déposer · **pourquoi tu corresponds**

## Utilisation

```bash
# 1. Mesurer les clés RÉELLES d'une source avant de lui faire confiance
python -m radar.cli recenser --source ted --echantillon reponses-reelles.json

# 2. Traiter un lot de réponses
python -m radar.cli --base radar.sqlite3 traiter --source ted --entree lot.json

# 3. Voir ce sur quoi on peut encore déposer (base ouverte en LECTURE SEULE)
python -m radar.cli --base radar.sqlite3 opportunites --complet
```

## État — à lire avant de s'en servir

`sources/ted.yaml` porte `verifie: false`. Les chemins de champs y sont
**plausibles, pas mesurés** : aucun accès réseau depuis l'environnement de
développement, donc aucune réponse réelle n'a été observée. La commande
`recenser` existe pour les corriger par la mesure ; tout champ à 0 % désigne une
clé qui n'existe pas. On la corrige **dans le fichier de source, jamais dans le
code**.

Tant que le recensement n'a pas eu lieu, `traiter` affiche un avertissement.

## Tests

```bash
python -m unittest discover -s tests
```

26 tests, tous de comportement. Aucun ne vérifie qu'une ligne de code existe :
ils posent les questions qui comptent — « est-ce que ça peut disparaître de mes
opportunités ? », « est-ce que ça peut partir deux fois ? ».

Zéro dépendance hors PyYAML.
