"""LE RACCORD — d'une trouvaille jusqu'à une opportunité, par les rails existants.

    TROUVAILLES → DÉDUPLICATION → ENTREPRISE → PAGE CANDIDATE
                → ANALYSE COMMERCIALE → OPPORTUNITÉ → 🟢🟡🟣🔵🔴 → ACTION

Ce module n'invente AUCUNE règle métier. Il ne classe pas, ne note pas, ne
qualifie pas, ne décide d'aucune action. Il branche bout à bout des modules
déjà validés :

    recoupement   le même besoin vu par plusieurs moteurs      (8d)
    chainage      trouvaille → entreprise possible → candidate (8c)
    adaptateur    la FORME d'un résultat web → une opportunité (sources/recherche.yaml)
    chaine        déduplication, classification, action, suivi (le moteur)

Et il compte ce qui s'est passé, étape par étape, pour qu'on puisse répondre
à la seule question qui compte : « ce radar va-t-il trouver du business ? »

CE QU'UN EXTRAIT DE MOTEUR PERMET, ET CE QU'IL NE PERMET PAS
============================================================

Un résultat de moteur porte un titre et deux lignes d'extrait. C'est peu, et
le rapport doit le dire : la plupart de ces opportunités seront des SIGNAUX ou
des HYPOTHÈSES, pas des FAITS. C'est le moteur commercial qui en décide, sur
le contenu — jamais ce module, et jamais parce que « ça vient d'un moteur ».

La page elle-même n'a PAS été lue. Tant qu'elle ne l'est pas, tout ce qu'elle
contient et que l'extrait ne dit pas reste INCONNU. Le chemin complet passe
ensuite par la collecte réelle et la qualification de 7b — que l'absence de
réseau laisse pour l'instant hors d'atteinte, et le rapport l'écrit.

LA PREUVE DE COLLECTE D'UNE LIGNE IMPORTÉE
==========================================

En mode RÉEL, `chaine.traiter` refuse toute ligne sans preuve de collecte.
Une ligne importée en porte une, et elle dit EXACTEMENT ce qui s'est passé :

    source    = le nom qualifié « import:<moteur> »
    reference = l'URL montrée
    collecte_le = quand la ligne est ENTRÉE dans le radar

Elle n'affirme pas que le radar a lu la page, ni qu'il a interrogé le moteur.
La date de la recherche elle-même, celle que l'export déclare, vit dans le
journal des exécutions et n'est pas écrasée par celle-ci.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import (chainage, execution as mod_execution, pages as mod_pages,
               recoupement, trouvailles as mod_trouvailles)
from .adaptateur import vers_opportunite
from .circuit import DECOUVERTE as CIRCUIT_DECOUVERTE
from .mode import Mode, estampiller

A_CONFIRMER = "À CONFIRMER"
NON_MESURE = "NON MESURÉ"

# Les quatre dimensions, et elles ne se mélangent jamais. Ce module ne fait que
# les LIRE sur l'opportunité : elles sont décidées ailleurs, chacune par son
# module. Les rassembler dans un rapport ne les fusionne pas.
DIMENSIONS = ("TYPE D'INFORMATION", "NATURE", "ÉTAT DE PROCÉDURE", "ACTION")

# LES QUATRE AXES DE LECTURE — quatre questions, quatre colonnes, jamais un
# seul nombre. Ils existaient déjà, chacun dans son module ; ce qui manquait,
# c'était de les montrer CÔTE À CÔTE.
#
#   ADÉQUATION       « puis-je le faire ? »        score.py     → score
#   NIVEAU DE PREUVE « j'en suis sûr ? »           fiabilite.py → fiabilite
#   NATURE           « est-ce un fait ? »          nature.py    → nature
#   POTENTIEL        « combien ça rapporte ? »     priorite.py  → ca_annuel
#
# C'est parce qu'ils sont séparés que le score n'a PAS à porter la nature :
# une hypothèse de presse et un besoin écrit peuvent être également
# exécutables, et c'est le niveau de preuve qui les distingue — pas le score.
AXES = ("ADÉQUATION", "NIVEAU DE PREUVE", "NATURE", "POTENTIEL")

# La MATURITÉ, et non une sixième catégorie commerciale.
#
# `classification.Type` porte six valeurs, mais elles ne répondent pas toutes
# à la même question. Cinq disent COMMENT ENTRER sur le marché ; ⚪ dit qu'on
# n'en est pas encore là — c'est une page lue qui ne porte, à cette date,
# aucun fait commercial. Un rapport qui l'aligne comme une sixième catégorie
# laisse croire à un sixième mode d'entrée, qui n'existe pas.
CATEGORIES_COMMERCIALES = ("DIRECT", "RENFORCEMENT", "A_CONSTRUIRE",
                           "PROSPECT", "REJET")
MATURITE_NON_QUALIFIEE = "PAS ENCORE UNE OPPORTUNITÉ"

# Les six catégories. ⚪ n'était pas dans la demande — elle existe pourtant
# depuis longtemps dans `classification.py`, et l'omettre ici l'aurait
# affichée comme « · », c'est-à-dire l'aurait rendue illisible dans le seul
# rapport que l'exploitant lira. ⚪ n'est NI une opportunité NI un rejet :
# c'est une page lue qui ne porte, à cette date, aucun fait commercial.
EMOJI = {"DIRECT": "🟢", "RENFORCEMENT": "🟡", "A_CONSTRUIRE": "🟣",
         "PROSPECT": "🔵", "PAS ENCORE UNE OPPORTUNITÉ": "⚪", "REJET": "🔴"}


def charge_de(trouvaille, *, mode: Mode) -> dict:
    """Ce que la source « recherche » sait lire, et rien de plus.

    Les mots sont ceux du moteur, repris tels quels. Aucun champ n'est
    complété, deviné ou déduit : ce que l'extrait ne dit pas reste absent, et
    le moteur commercial écrira À CONFIRMER plutôt qu'un chiffre inventé.
    """
    charge = {
        "url": trouvaille.url,
        "titre": trouvaille.titre or "",
        "extrait": trouvaille.extrait or "",
        "requete": trouvaille.requete,
        "consulte_le": trouvaille.decouverte_le,
        "fournisseur": trouvaille.source,
    }
    if trouvaille.page_source:
        charge["page_source"] = trouvaille.page_source
    if mode is Mode.DEMO:
        return charge
    return estampiller(charge, source=trouvaille.source, reference=trouvaille.url)


def opportunites_de(adaptateur, trouvailles, *, mode: Mode, defauts=None):
    """Traduit des trouvailles en opportunités candidates — sans rien décider.

    La PROVENANCE est celle de la source réelle, jamais celle de l'adaptateur :
    étiqueter un résultat importé comme une recherche du radar ferait mentir le
    rendement par source, et l'on ne saurait plus qui a trouvé quoi.
    """
    sortie = []
    for t in trouvailles or []:
        charge = charge_de(t, mode=mode)
        sortie.append(vers_opportunite(
            adaptateur, charge, t.source,
            {**(defauts or {}), "circuit": t.circuit or CIRCUIT_DECOUVERTE}))
    return sortie


# ═══════════════════════════════════════════════════ le bilan de bout en bout
@dataclass
class Parcours:
    """Ce que la chaîne a RÉELLEMENT produit, étape par étape.

    Chaque nombre est un compte d'observations. Aucun n'est une promesse de
    chiffre d'affaires, et aucun ne dit qu'une affaire est gagnable.
    """
    mode: object = None
    # découverte
    resultats: int = 0
    requetes: int = 0
    urls_uniques: int = 0
    multi_sources: int = 0
    doublons_regroupes: int = 0
    sources: list = field(default_factory=list)
    natures_execution: dict = field(default_factory=dict)
    # identification
    entreprises_decouvertes: int = 0
    entreprises_connues: int = 0
    rattachements_non_etablis: int = 0
    # pages
    pages_candidates: int = 0
    pages_deja_connues: int = 0
    pages_surveillees: int = 0
    qualifications_positives: int = 0
    pages_collectees: int = 0
    # commercial
    besoins: int = 0
    opportunites: int = 0
    direct: int = 0
    renforcement: int = 0
    a_construire: int = 0
    prospect: int = 0
    rejet: int = 0
    observation: int = 0
    actions: dict = field(default_factory=dict)
    motifs_rejet: dict = field(default_factory=dict)
    incidents: int = 0

    @property
    def retenues(self) -> int:
        return self.direct + self.renforcement + self.a_construire + self.prospect

    def entonnoir(self) -> list[str]:
        """Chaque marche, et ce qu'on a perdu entre deux. Rien ne disparaît
        sans qu'on puisse dire où."""
        marches = [
            ("résultats importés / trouvés", self.resultats),
            ("URL uniques après regroupement", self.urls_uniques),
            ("entreprises au registre", self.entreprises_decouvertes
             + self.entreprises_connues),
            ("pages candidates (dont déjà connues)",
             self.pages_candidates + self.pages_deja_connues),
            ("besoins lus par le moteur", self.besoins),
            ("opportunités écrites", self.opportunites),
            ("opportunités retenues (hors 🔴)", self.retenues),
        ]
        L = []
        for libelle, n in marches:
            L.append(f"  {libelle:<36} {n:>6}")
        return L


# ═══════════════════════════════════════════════════ exécution
def executer(cx, moteur, adaptateur, *, mode: Mode, defauts=None,
             trouvailles=None, registre=None) -> Parcours:
    """Fait passer les trouvailles par TOUTE la chaîne, dans l'ordre.

    `moteur` est le moteur commercial (`chaine.Moteur`), `adaptateur` celui de
    la source « recherche ». Ce module n'en construit aucun : il ne choisit ni
    le profil, ni les pondérations, ni la géographie.
    """
    from . import entreprises as mod_entreprises
    from .chaine import traiter

    liste = list(trouvailles if trouvailles is not None
                 else mod_trouvailles.toutes(cx, mode=mode))
    p = Parcours(mode=mode)
    p.resultats = len(liste)
    p.natures_execution = mod_execution.repartition(cx)

    # 1. DÉDUPLICATION D'URL — deux moteurs qui montrent la même page font
    #    deux observations et une seule page. On garde les deux observations.
    groupes = recoupement.grouper(liste)
    p.urls_uniques = len(groupes)
    p.multi_sources = sum(1 for g in groupes if g.multi_source)
    p.doublons_regroupes = len(liste) - len(groupes)
    p.requetes = len({t.requete for t in liste if t.requete})
    p.sources = sorted({t.source for t in liste})

    # 2. IDENTIFICATION — par le DOMAINE, jamais par un nom lu dans un titre.
    reg = registre if registre is not None else mod_entreprises.charger(cx)
    bilan = chainage.chainer(cx, liste, reg, ontologie=moteur.ontologie,
                             detecteur=moteur.roles)
    mod_entreprises.enregistrer(cx, reg)
    chainage.marquer_identites(cx, reg)
    p.entreprises_decouvertes = bilan.entreprises_nouvelles
    p.entreprises_connues = bilan.entreprises_connues
    p.rattachements_non_etablis = bilan.rattachements_non_etablis
    p.pages_candidates = bilan.pages_candidates
    p.pages_deja_connues = bilan.pages_deja_connues

    # 3. ANALYSE COMMERCIALE — le MÊME moteur que pour toutes les sources.
    #    Un résultat de moteur n'a ni avantage ni handicap ; un marché public
    #    non plus.
    opportunites = opportunites_de(adaptateur, liste, mode=mode, defauts=defauts)
    p.besoins = len(opportunites)
    if opportunites:
        b = traiter(cx, moteur, opportunites, mode=mode)
        p.direct, p.renforcement = b.direct, b.renforcement
        p.a_construire, p.prospect, p.rejet = b.a_construire, b.prospect, b.rejet
        p.motifs_rejet = dict(b.motifs_rejet)
        p.incidents = b.livre.total_illisibles

    # 4. CE QUI EST EN BASE, APRÈS COUP — lu, jamais recalculé de tête.
    p.opportunites = cx.execute(
        "SELECT count(*) c FROM opportunites").fetchone()["c"]
    p.observation = cx.execute(
        "SELECT count(*) c FROM opportunites WHERE type=?",
        ("PAS ENCORE UNE OPPORTUNITÉ",)).fetchone()["c"]
    p.actions = {l["action"]: l["n"] for l in cx.execute(
        "SELECT action, count(*) n FROM opportunites"
        " WHERE action IS NOT NULL AND type <> 'REJET' GROUP BY action")}
    p.pages_surveillees = len(mod_pages.a_surveiller(cx))
    p.qualifications_positives = cx.execute(
        "SELECT count(*) c FROM pages_surveillees WHERE qualification=?",
        (mod_pages.Qualification.PREUVE.value,)).fetchone()["c"]
    p.pages_collectees = cx.execute(
        "SELECT count(*) c FROM pages_surveillees WHERE acces=?",
        (mod_pages.Acces.CONSULTEE.value,)).fetchone()["c"]
    return p


# ═══════════════════════════════════════════════════ top opportunités
def top_opportunites(cx, limite: int = 20) -> list:
    """Les opportunités retenues, les plus fortes d'abord.

    Le tri est un ORDRE DE LECTURE, pas un verdict : une affaire classée
    dixième reste une affaire. Rien n'est filtré ici sauf le REJET, qui n'est
    pas un score faible mais un rejet OBJECTIF déjà établi et motivé.
    """
    return cx.execute(
        "SELECT o.*, a.ref_source, a.source AS source_avis"
        " FROM opportunites o JOIN avis a ON a.id = o.avis_id"
        " WHERE o.type <> 'REJET'"
        " ORDER BY o.score DESC, o.echeance IS NULL, o.echeance"
        f" LIMIT {int(limite)}").fetchall()


def _effort(l) -> str:
    """L'effort opérationnel, tel qu'il a été calculé. Jamais complété.

    La distance entre dans l'effort et dans le classement. Elle ne supprime
    JAMAIS une affaire : une opportunité lointaine est une opportunité chère
    à servir, pas une opportunité inexistante.
    """
    morceaux = []
    if l["distance_km"] is not None:
        morceaux.append(f"{l['distance_km']:.0f} km")
    else:
        morceaux.append(f"distance {A_CONFIRMER}")
    morceaux.append(l["capacite"] or f"capacité {A_CONFIRMER}")
    if l["cadence"]:
        morceaux.append(str(l["cadence"]))
    return " · ".join(m for m in morceaux if m)


def _liste(valeur, vide: str) -> str:
    """Une liste stockée en JSON, rendue lisible. Une liste VIDE se dit.

    Écrire « [] » laisserait croire à une panne d'affichage ; écrire « — »
    laisserait croire que rien n'a été cherché. Une liste vide veut dire
    « on a regardé et on n'a rien identifié », et c'est ce qui s'écrit.
    """
    import json
    try:
        items = json.loads(valeur) if valeur else []
    except (TypeError, ValueError):
        return str(valeur)
    if not items:
        return vide
    return " · ".join(str(i) for i in items)


def _entite(cx, l) -> str:
    """L'ENTITÉ QUI SERT la page — par son domaine, avec l'état de son identité.

    L'acheteur nommé prime s'il a été lu dans le contenu. Sinon on affiche le
    domaine, qui est un FAIT observable, accompagné de ce que le radar sait
    vraiment de son identité — le plus souvent INCONNUE. Ce n'est pas un nom
    d'entreprise et cela ne doit pas se lire comme tel.
    """
    if l["acheteur"]:
        return str(l["acheteur"])
    from .entreprises import domaine_de
    domaine = domaine_de(l["ref_source"])
    if not domaine:
        return f"entité {A_CONFIRMER}"
    try:
        from . import identite as mod_identite
        etat = mod_identite.lire(cx, domaine).etat.value
    except Exception:                                            # noqa: BLE001
        etat = "INCONNUE"
    return f"domaine {domaine}  (identité {etat} — ce n'est pas une raison sociale)"


def axes(l) -> str:
    """Les quatre axes en une ligne. Chacun répond à SA question.

    Le score seul n'a jamais suffi à décider : il dit « puis-je le faire »,
    pas « est-ce vrai » ni « combien ça rapporte ». Les afficher séparément
    est la raison pour laquelle il n'a pas besoin d'absorber la nature.
    """
    ca = (f"{l['ca_annuel']:,.0f} €/an".replace(",", " ")
          if l["ca_annuel"] else (l["ca_etat"] or NON_MESURE))
    adequation = (f"{l['score']}/100" if l["score_mesurable"]
                  else "NON MESURABLE — aucun fait économique observé")
    return (f"ADÉQUATION {adequation}"
            f"   ·   PREUVE {l['fiabilite'] or A_CONFIRMER}"
            f"   ·   NATURE {l['nature'] or A_CONFIRMER}"
            f"   ·   POTENTIEL {ca}")


def est_signal(l) -> bool:
    """Un SIGNAL n'est pas un besoin. On ne les mélange jamais dans une liste
    d'actions : « ouverture d'un entrepôt » ne dit à personne qu'on cherche un
    sous-traitant, et le présenter à côté d'un besoin écrit ferait perdre une
    matinée à l'exploitant."""
    return (l["nature"] or "").upper() != "FAIT"


def top_actions(cx, limite: int = 10) -> str:
    """« Qu'est-ce que je fais demain matin ? » — la réponse, en deux blocs.

    BESOINS ÉNONCÉS d'abord : quelqu'un a écrit qu'il cherchait.
    SIGNAUX ensuite : il se passe quelque chose, et personne n'a rien demandé.

    Les deux blocs existent parce que confondre les deux est l'erreur la plus
    coûteuse qu'un radar commercial puisse faire.
    """
    lignes = top_opportunites(cx, limite * 3)
    besoins = [l for l in lignes if not est_signal(l)][:limite]
    signaux = [l for l in lignes if est_signal(l)][:limite]

    L = ["TOP ACTIONS COMMERCIALES", "=" * 88, ""]
    L.append("BESOINS ÉNONCÉS — quelqu'un a ÉCRIT qu'il cherchait")
    L.append("-" * 88)
    if not besoins:
        L.append("  AUCUN. Ce n'est pas une panne : rien dans cet échantillon ne")
        L.append("  portait un besoin écrit. Le radar ne promeut jamais un signal")
        L.append("  au rang de besoin pour remplir une liste.")
    for n, l in enumerate(besoins, start=1):
        L += _bloc_action(cx, n, l)

    L.append("")
    L.append("SIGNAUX — il se passe quelque chose, PERSONNE N'A RIEN DEMANDÉ")
    L.append("-" * 88)
    if not signaux:
        L.append("  aucun")
    for n, l in enumerate(signaux, start=1):
        L += _bloc_action(cx, n, l, signal=True)

    L.append("")
    L.append("  Un signal n'est PAS un contrat, et ne le devient pas en montant")
    L.append("  dans la liste. Il justifie un contact, jamais une offre.")
    return "\n".join(L)


def _bloc_action(cx, n: int, l, *, signal: bool = False) -> list[str]:
    emoji = EMOJI.get(l["type"], "·")
    intitule = "Signal" if signal else "Besoin"
    L = ["",
         f"{n}.  {emoji} {l['type']}        {_entite(cx, l)}",
         f"    {intitule}    : {(l['intitule'] or A_CONFIRMER)[:72]}",
         f"    Zone      : {l['zone'] or A_CONFIRMER}"
         f"   ·   Effort : {_effort(l)}",
         f"    ACTION    : {l['action'] or A_CONFIRMER}",
         f"    {axes(l)}",
         f"    Pourquoi  : {(l['motif'] or A_CONFIRMER)[:74]}"]
    manque = _liste(l["manques"], "")
    if manque:
        L.append(f"    Manque    : {manque[:74]}")
    if signal:
        L.append("    Attention : AUCUN besoin n'a été exprimé ici. Ce n'est pas")
        L.append("                une demande adressée à votre entreprise.")
    L.append(f"    Preuve    : {l['ref_source']}")
    return L


def fiche_courte(cx, l) -> list[str]:
    """Les éléments demandés, et aucun n'est deviné.

    Les quatre dimensions restent SÉPARÉES : type d'information, nature, état
    de procédure et action ne se résument jamais l'une l'autre. Ce qui manque
    s'écrit en clair ; un tiret vide laisserait croire que l'information a été
    cherchée et qu'elle vaut zéro.
    """
    emoji = EMOJI.get(l["type"], "·")
    return [
        f"{emoji} [{l['score']:>3}] {(l['intitule'] or 'sans intitulé')[:64]}",
        f"     ENTREPRISE   {_entite(cx, l)}",
        f"     BESOIN       {l['intitule'] or A_CONFIRMER}"[:104],
        f"     SOURCE       {l['source_avis']}",
        f"     PREUVE       {l['ref_source']}",
        f"     TYPE D'INFO  {l['type_information'] or 'NON DÉCLARÉ PAR LA SOURCE'}"
        f"   ·   SECTEUR {l['secteur'] or A_CONFIRMER}"
        f"   ·   RÔLE {l['role'] or A_CONFIRMER}",
        f"     AXES         {axes(l)}",
        f"     ÉTAT         {l['etat_procedure'] or 'INCONNU'}"
        f"   (confiance {l['confiance_etat'] or A_CONFIRMER})",
        f"     CATÉGORIE    {emoji} {l['type']}   ·   MOTEUR {l['moteur'] or '—'}",
        f"     ACTION       {l['action'] or A_CONFIRMER}",
        f"     ZONE         {l['zone'] or A_CONFIRMER}",
        f"     EFFORT       {_effort(l)}",
        f"     MANQUE       {_liste(l['manques'], 'rien d’identifié')}",
        f"     LEVIERS      {_liste(l['leviers'], 'aucun identifié')}",
        f"     RISQUES      {_liste(l['risques'], 'aucun identifié')}",
        f"     CLASSÉ AINSI {(l['motif'] or A_CONFIRMER)[:88]}",
    ]


# ═══════════════════════════════════════════════════ rapport
def rapport(cx, p: Parcours, *, limite_top: int = 20,
            donnees_reelles: bool | None = None) -> str:
    """Le rapport qui doit permettre de juger le radar, pas de s'y fier.

    Il affiche le rappel À CÔTÉ de la précision : un moteur qui rend cent
    résultats déjà connus ne vaut pas un moteur qui en rend dix inédits, et
    une requête muette n'est pas une mauvaise requête.
    """
    L = ["RAPPORT COMMERCIAL — DÉCOUVERTE IMPORTÉE", "=" * 88, ""]

    reelles = (donnees_reelles if donnees_reelles is not None
               else p.mode is Mode.REEL and p.resultats > 0)
    if not reelles:
        L.append("  DONNÉES RÉELLES : NON MESURÉES")
        L.append("  Ce rapport porte sur des données FABRIQUÉES. Il éprouve la")
        L.append("  chaîne, il ne mesure aucun marché belge.")
        L.append("")

    L.append("NATURE DES EXÉCUTIONS")
    for cle, n in sorted(p.natures_execution.items()):
        L.append(f"  {cle:<40} {n:>6}")
    L.append(f"  {'sources distinctes':<40} {len(p.sources):>6}"
             + (f"   ({', '.join(p.sources[:4])})" if p.sources else ""))
    L.append("")

    L.append("ENTONNOIR — de ce qu'on a vu à ce qu'on peut travailler")
    L += p.entonnoir()
    L.append("")

    L.append("RAPPEL — ce que la découverte a couvert")
    for libelle, n in (("requêtes contributrices", p.requetes),
                       ("résultats bruts", p.resultats),
                       ("URL uniques", p.urls_uniques),
                       ("vues par PLUSIEURS sources", p.multi_sources),
                       ("doublons regroupés", p.doublons_regroupes)):
        L.append(f"  {libelle:<36} {n:>6}")
    L.append("  Une requête qui ne rend rien n'est pas une mauvaise requête :")
    L.append("  c'est une mesure. Une source qui rend beaucoup de résultats")
    L.append("  déjà connus n'est pas pour autant la meilleure.")
    L.append("")

    L.append("IDENTIFICATION — par le DOMAINE, jamais par un nom lu dans un titre")
    for libelle, n in (("entreprises nouvelles", p.entreprises_decouvertes),
                       ("entreprises déjà connues", p.entreprises_connues),
                       ("rattachements NON ÉTABLIS", p.rattachements_non_etablis)):
        L.append(f"  {libelle:<36} {n:>6}")
    L.append("")

    L.append("PAGES")
    for libelle, n in (("candidates NOUVELLES", p.pages_candidates),
                       ("candidates déjà connues", p.pages_deja_connues),
                       ("surveillées", p.pages_surveillees),
                       ("réellement collectées", p.pages_collectees),
                       ("qualifications POSITIVES", p.qualifications_positives)):
        L.append(f"  {libelle:<36} {n:>6}")
    if p.pages_collectees == 0:
        L.append("  AUCUNE PAGE N'A ÉTÉ LUE. Tout ce que ces pages contiennent")
        L.append("  et que l'extrait ne dit pas reste INCONNU. La qualification")
        L.append("  sur contenu réel exige une collecte, et elle n'a pas eu lieu.")
    L.append("")

    L.append("COMMERCIAL — catégories")
    for emoji, libelle, n in (("🟢", "DIRECT", p.direct),
                              ("🟡", "RENFORCEMENT", p.renforcement),
                              ("🟣", "À CONSTRUIRE", p.a_construire),
                              ("🔵", "PROSPECT / PARTENARIAT", p.prospect),
                              ("🔴", "REJET", p.rejet)):
        L.append(f"  {emoji} {libelle:<34} {n:>6}")
    L.append("  🔴 n'est pas « score faible » : c'est un rejet OBJECTIF établi.")
    L.append("  Une affaire difficile, lointaine, volumineuse ou exigeant du")
    L.append("  recrutement reste 🟡, 🟣 ou 🔵 — elle n'est jamais supprimée.")
    if p.motifs_rejet:
        L.append("  motifs de rejet : " + " · ".join(
            f"{m} ×{n}" for m, n in sorted(p.motifs_rejet.items(),
                                           key=lambda x: -x[1])[:6]))
    L.append("")

    L.append("MATURITÉ — un AXE À PART, jamais une sixième catégorie")
    L.append(f"  ⚪ {MATURITE_NON_QUALIFIEE:<34} {p.observation:>6}")
    L.append("  Les cinq catégories ci-dessus répondent à « COMMENT entrer sur")
    L.append("  ce marché ». ⚪ répond à autre chose : « on n'en est pas encore")
    L.append("  là ». C'est une page lue qui ne porte, à cette date, aucun fait")
    L.append("  commercial. Elle reste au registre et pourra en porter un demain.")
    L.append("  L'aligner avec les cinq autres laisserait croire à un sixième")
    L.append("  mode d'entrée sur le marché, qui n'existe pas.")
    L.append("")

    L.append("COMMERCIAL — actions")
    if p.actions:
        for action, n in sorted(p.actions.items(), key=lambda x: -x[1]):
            L.append(f"  {action:<36} {n:>6}")
    else:
        L.append("  aucune action — aucune opportunité retenue")
    L.append("")

    L.append(top_actions(cx))
    L.append("")

    lignes = top_opportunites(cx, limite_top)
    L.append(f"TOP OPPORTUNITÉS COMMERCIALES — {len(lignes)} affichée(s)")
    L.append("  Les QUATRE dimensions restent séparées : TYPE D'INFORMATION,")
    L.append("  NATURE, ÉTAT DE PROCÉDURE et ACTION ne se résument jamais")
    L.append("  l'une l'autre. Une affaire peut être exécutable (🟢) ET n'être")
    L.append("  qu'une HYPOTHÈSE : « pouvons-nous le faire » et « est-ce réel »")
    L.append("  sont deux questions, et le rapport répond aux deux.")
    L.append("-" * 88)
    if not lignes:
        L.append("  AUCUNE. Ce n'est pas une panne : rien dans cet échantillon")
        L.append("  ne portait un besoin économique lisible. Le radar ne force")
        L.append("  jamais un classement pour remplir une page.")
    for l in lignes:
        L += fiche_courte(cx, l)
        L.append("")

    L.append("-" * 88)
    L.append("CE QUI RESTE INCONNU, ET QUI LE RESTERA SANS COLLECTE")
    L.append("  véhicules · tonnage · chauffeurs · CA · marge · coût/km ·")
    L.append("  rémunération · durée · volume · certifications · licences ·")
    L.append("  agréments · capacité exacte · échéance non prouvée")
    L.append(f"  Tout cela s'écrit « {A_CONFIRMER} ». Une déduction n'est pas")
    L.append("  un fait, et la marge reste NON MESURÉE tant que les coûts")
    L.append("  réels ne sont pas au profil.")
    return "\n".join(L)
