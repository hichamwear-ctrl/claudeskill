# CAR SNIPER

Détecteur d'écart entre la décote que le marché applique à un défaut mécanique
et ce que ce défaut coûte réellement à un pro.

## Installation

```bash
pip install pyyaml
python run.py init          # base + lexique
```

Variables d'environnement pour Telegram :

```bash
export TELEGRAM_TOKEN="..."     # via @BotFather
export TELEGRAM_CHAT_ID="..."   # via @userinfobot
```

Sans ces variables, les alertes s'affichent dans la console.

## Utilisation

```bash
python run.py bootstrap    # sweep complet — une nuit, à lancer une fois
python run.py loop         # tourne en continu : rapide (3 min) + nocturne (3h)
python run.py top 20       # classement des meilleures annonces actives
python run.py stats        # état de la base
python tests/test_engine.py
```

## Configuration

Tout est dans `config/` et modifiable sans toucher au code :

| Fichier | Contenu |
|---|---|
| `profile.yaml` | budget, rayon, marques, seuils par segment, anti-spam, cadence |
| `defects.yaml` | lexique FR/NL — `market_discount` vs `pro_cost` |
| — | les pondérations du score sont dans `carsniper/engine.py` (`WEIGHTS`) |

## Le principe

### Caractéristique ou panne ?

Le lexique distingue **le nom d'un organe** de **l'annonce d'une panne** :

```yaml
- code: aircon
  components_nl: [airco]          # NEUTRE seul — la voiture EN EST ÉQUIPÉE
  faults_nl:     [airco bijvullen] # défaut à lui seul
```

Un composant ne devient un défaut que si un **marqueur de panne**
(`kapot`, `defect`, `versleten`, `à refaire`…) apparaît dans la **même
proposition**. Les annonces sont des listes d'équipement — chercher un
marqueur trop loin faisait de `airco` un défaut dès qu'un mot négatif
traînait dans la description.

| Texte | v1 | v2 |
|---|---|---|
| `airco` | défaut clim | rien |
| `airco kapot` | défaut clim | défaut clim |
| `handgeschakelde versnellingsbak` | défaut boîte (sévérité 4) | rien |
| `schadewagen` | rien | dommage |
| `schadevrij` | rien | rien |

### Le coût réel

Chaque défaut porte **deux fourchettes** :

```yaml
- code: clutch
  market_discount: [1800, 3000]   # ce que le marché retire par peur
  pro_cost: [350, 1100]           # ce que ça te coûte réellement
```

L'écart entre les deux est le signal. Le système cherche les annonces où
le marché sur-décote un défaut que tu sais traiter à bas coût.

Cas particulier : `corrosion` a un écart **négatif** (marché 600–1800 €,
coût réel 800–4000 €). Le système l'utilise comme repoussoir.

## Architecture

```
sources/ (SourceAdapter)  →  ingestion  →  normalisation  →  défauts
   →  marché  →  réparations  →  risque  →  revente  →  urgence
   →  Deal Score  →  anti-spam  →  Telegram
```

Ajouter une source = écrire une classe qui implémente `SourceAdapter`.
Rien d'autre ne bouge.

`raw_payloads` n'est jamais modifié : quand le lexique s'améliore, tout
l'historique est rejoué sans recollecter.

## Points de conception

**La confiance mesure la compréhension, pas l'échantillon.** Elle répond à
« ai-je compris cette annonce ? », pas seulement « ai-je assez de
comparables ? ». Elle s'effondre si la marque est incertaine, si l'année
manque, si le pool est hétérogène, si le défaut n'est que déduit du
contexte — et surtout en cas de **décote inexpliquée**.

**Décote inexpliquée.** Une voiture très en dessous du marché n'est une
affaire que si les défauts détectés expliquent l'écart. Sont comptés comme
explications légitimes : la décote de marché des défauts trouvés, la
dispersion naturelle du marché (p50 → pmin), et les baisses de prix
réellement observées. Ce qui reste inexpliqué fait chuter la confiance.
C'est ce garde-fou qui bloque une épave à 2 500 € face à un marché à
18 000 €, **même quand le lexique rate le mot** qui la signalait.

**Défauts non chiffrables.** `accident`, `corrosion`, `engine`, `for_parts` :
un choc peut être un pare-choc à 300 € comme un châssis au marbre à 6 000 €.
Aucune estimation honnête n'est possible depuis un texte d'annonce — la
confiance est plafonnée à 0,45, donc sous le seuil d'alerte.

**La marge hypothétique est séparée.** L'alerte distingue ce qui est *tenu*
au prix affiché de ce qui *dépend de la négociation*. Une marge qui
n'existe que grâce à la remise supposée ne peut pas produire de GREAT DEAL.

**Urgence inversée.** Une voiture saine sous-évaluée part en une heure :
urgence maximale. Une voiture à défaut reste des semaines : l'urgence **monte**
avec l'âge et les baisses de prix. Ce sont les meilleures opportunités, et
elles sont invisibles sur le site.

**Marché sain uniquement.** Les annonces portant un défaut sont exclues du
calcul des comparables. Sinon on compare des épaves à des épaves et la décote
disparaît.

**Une disparition n'est pas une vente.** Le système stocke `p_sold`, jamais
`sold = true`. Une annonce peut être retirée, expirée ou repostée.

## Limites connues

- La valeur de marché repose sur des prix **demandés**, pas des prix de
  transaction. Biais de +8 à 15 %.
- **Les taux de `estimate_negotiation` sont des hypothèses, pas des mesures.**
  Le système n'observe aucun prix de transaction ; une baisse affichée n'est
  pas une remise obtenue au téléphone. Ces taux ne pourront être calibrés
  que sur des prix réellement négociés (bouton 💰 du feedback).
- `listing_outcomes` / `p_sold` existent dans le schéma mais **ne sont
  alimentés par aucun code**. La correction du biais par les prix de
  disparition n'est pas implémentée.
- Les tables `vehicle_refs`, `run_log`, `profiles` sont inutilisées.
- Le lexique se trompera. Prévoir 8 à 15 corrections le premier mois.
- Les paramètres de l'endpoint de collecte peuvent nécessiter un ajustement.
- Le scraping est contraire aux CGU de la plateforme. Usage personnel,
  cadence lente, arrêt propre sur 429 : aucun contournement n'est implémenté.
