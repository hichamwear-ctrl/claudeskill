"""INTERPRÉTATION DE L'ÉTAT D'UNE PROCÉDURE — comprendre, pas reconnaître des mots.

Le piège à éviter, écrit noir sur blanc pour qu'il ne revienne pas :

    si le texte contient « attribué » → ATTRIBUÉ, sinon → POSTULABLE

Ce serait faux à peu près partout. « Aucun soumissionnaire n'a encore été
désigné » contient le vocabulaire de l'attribution et signifie l'inverse. Un
document annexe nommé « avis d'attribution » ne dit rien de l'état de la page
qu'on analyse. Et une date limite dépassée ne prouve pas qu'un marché a été
attribué — seulement qu'on ne peut plus déposer.

────────────────────────────────────────────────────────────────────────────
QUATRE DIMENSIONS, JAMAIS MÉLANGÉES
────────────────────────────────────────────────────────────────────────────

  A  TYPE D'INFORMATION   ce que le portail appelle l'objet — « Marchés en
                          cours », « Avis de préinformation », « Résultats »,
                          « Appels à projets ». Déclaré par la source.
  B  ÉTAT DE PROCÉDURE    POSTULABLE · ATTRIBUÉ · FERMÉ · ANNULÉ ·
                          INFRUCTUEUX · INFORMATIF · INCONNU.  ← ce module
  C  NATURE               FAIT · SIGNAL · HYPOTHÈSE.              nature.py
  D  ACTION               POSTULER · CONTACTER · SURVEILLER…  classification.py

Ce module ne produit que B, et les preuves qui l'ont fait choisir.

────────────────────────────────────────────────────────────────────────────
HIÉRARCHIE DES PREUVES
────────────────────────────────────────────────────────────────────────────

    statut officiel déclaré  >  type d'information  >  événement de procédure
    >  formulation interprétée  >  information temporelle  >  inférence

Le rang le plus élevé l'emporte. Une contradiction entre deux rangs n'est pas
tue : le rang fort décide, la contradiction est affichée, et la confiance
baisse. Deux preuves de même rang qui se contredisent ne produisent PAS un
gagnant arbitraire : elles produisent INCONNU.

────────────────────────────────────────────────────────────────────────────
CE QUI N'EST JAMAIS FAIT
────────────────────────────────────────────────────────────────────────────

  · INCONNU n'est jamais promu en POSTULABLE « par défaut ».
  · Une date limite dépassée ne devient jamais ATTRIBUÉ.
  · Un nom de document ne conclut jamais sur l'état de la procédure.
  · Une formulation jamais rencontrée n'est pas devinée : elle est mémorisée
    pour être interprétée par un humain, et l'état reste INCONNU.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum


# ═══════════════════════════════════════════════════════ B — état de procédure
class Etat(Enum):
    POSTULABLE = "POSTULABLE"
    ATTRIBUE = "ATTRIBUÉ"
    FERME = "FERMÉ"
    ANNULE = "ANNULÉ"
    INFRUCTUEUX = "INFRUCTUEUX"
    INFORMATIF = "INFORMATIF"
    INCONNU = "INCONNU"

    @property
    def emoji(self) -> str:
        return {"POSTULABLE": "🟢", "ATTRIBUÉ": "🔵", "FERMÉ": "🟠",
                "ANNULÉ": "⚫", "INFRUCTUEUX": "⚪", "INFORMATIF": "🟣",
                "INCONNU": "❓"}[self.value]

    @property
    def depot_possible(self) -> bool:
        """Seul POSTULABLE autorise à affirmer qu'on peut encore déposer.

        INCONNU ne l'autorise PAS : on ne sait pas. L'opportunité reste dans
        le radar avec « ÉTAT À VÉRIFIER » — elle n'est ni jetée, ni promue.
        """
        return self is Etat.POSTULABLE

    @property
    def libelle_long(self) -> str:
        return {
            "POSTULABLE": "candidature encore possible",
            "ATTRIBUÉ": "marché attribué — le titulaire devra exécuter",
            "FERMÉ": "candidature terminée — attribution non publiée",
            "ANNULÉ": "procédure annulée",
            "INFRUCTUEUX": "procédure sans suite",
            "INFORMATIF": "annonce d'un besoin futur — rien à déposer aujourd'hui",
            "INCONNU": "ÉTAT À VÉRIFIER — la source ne permet pas de conclure",
        }[self.value]


class Confiance(Enum):
    ELEVEE = "élevée"
    MOYENNE = "moyenne"
    FAIBLE = "faible"
    NULLE = "nulle"


# Rangs de la hiérarchie. Plus haut = plus fort.
#
#   statut officiel  >  état explicite  >  rubrique du portail
#                    >  formulation indirecte  >  dates  >  inférence
#
# Le rang 4 est celui qui a coûté le plus de réflexion. Une annonce rangée dans
# « Marchés en cours » dont le texte dit « la procédure est clôturée » n'est
# PAS postulable : la rubrique est un classement de listing, souvent en retard
# d'une mise à jour ; la phrase, elle, parle de CETTE procédure. L'état
# explicite passe donc devant la rubrique — et la contradiction reste affichée.
RANG_STATUT_DECLARE = 5     # champ de statut normé, valeur connue de l'adaptateur
RANG_ETAT_EXPLICITE = 4     # « la procédure est clôturée », « attribué le … à … »
RANG_TYPE_INFORMATION = 3   # la rubrique du portail : « Résultats », « Marchés en cours »
RANG_FORMULATION = 2        # une formulation indirecte, négations comprises
RANG_TEMPOREL = 1           # les dates seules
RANG_INFERENCE = 0

RANG_EVENEMENT = RANG_ETAT_EXPLICITE   # un fait daté vaut une déclaration

NOM_DU_RANG = {
    RANG_STATUT_DECLARE: "statut officiel déclaré par la source",
    RANG_ETAT_EXPLICITE: "état de procédure explicite",
    RANG_TYPE_INFORMATION: "rubrique du portail",
    RANG_FORMULATION: "formulation interprétée",
    RANG_TEMPOREL: "information temporelle",
    RANG_INFERENCE: "inférence",
}


# Ces trois états impliquent FERMÉ et disent en plus POURQUOI c'est fermé.
PLUS_PRECIS_QUE_FERME = frozenset({Etat.ATTRIBUE, Etat.ANNULE, Etat.INFRUCTUEUX})


@dataclass
class Preuve:
    """Pourquoi le moteur a conclu ça. Affichée sur la fiche, toujours."""
    rang: int
    observation: str            # ce qui a été lu, tel quel
    conclusion: Etat | None     # None = la preuve exclut sans conclure
    confiance: Confiance = Confiance.MOYENNE
    exclut: tuple = ()          # états que cette preuve rend impossibles

    def __str__(self) -> str:
        quoi = self.conclusion.value if self.conclusion else "n'élit aucun état"
        return f"[{NOM_DU_RANG[self.rang]}] « {self.observation} » → {quoi}"


@dataclass
class Lecture:
    """Le résultat complet. Jamais un simple état nu."""
    etat: Etat = Etat.INCONNU
    type_information: str = ""          # normalisé par l'adaptateur
    type_information_source: str = ""   # ce que le portail a écrit, verbatim
    confiance: Confiance = Confiance.NULLE
    preuves: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    a_verifier: list = field(default_factory=list)
    inconnues: list = field(default_factory=list)   # expressions à mémoriser
    date_attribution: object = None
    titulaire: str | None = None
    # Y a-t-il seulement une PROCÉDURE à qualifier ?
    #
    # « Devenir partenaire transporteur » sur le site d'une PME n'est pas une
    # procédure dont l'état serait inconnu : c'est une invitation permanente.
    # Lui coller « ÉTAT À VÉRIFIER » serait une fausse alerte, et pousserait
    # l'utilisateur à vérifier quelque chose qui n'existe pas.
    procedure_detectee: bool = False

    @property
    def postulable(self) -> bool | None:
        """True, False, ou None quand on ne sait pas. Jamais False par défaut."""
        if self.etat is Etat.INCONNU:
            return None
        return self.etat.depot_possible

    def en_lignes(self) -> list[str]:
        L = [f"ÉTAT          {self.etat.emoji} {self.etat.value} — {self.etat.libelle_long}"]
        if self.type_information_source:
            L.append(f"TYPE (source) {self.type_information_source}"
                     + (f"  → {self.type_information}" if self.type_information else ""))
        L.append(f"CONFIANCE     {self.confiance.value}")
        for p in self.preuves[:4]:
            L.append(f"PREUVE        {p}")
        for c in self.contradictions:
            L.append(f"CONTRADICTION {c}")
        for v in self.a_verifier:
            L.append(f"À VÉRIFIER    {v}")
        return L


# ═══════════════════════════════════════════════════ atomes de sens, pas de mots
def normaliser(texte) -> str:
    if not texte:
        return " "
    plat = unicodedata.normalize("NFKD", str(texte))
    plat = "".join(c for c in plat if not unicodedata.combining(c)).lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", plat).strip() + " "


# Chaque marqueur est un CONCEPT, décliné dans les quatre langues où paraissent
# les avis belges, néerlandais, français et allemands. Le moteur ne cherche pas
# « la phrase du portail X » : il cherche de quoi la phrase parle.
MARQUEURS = {
    # ── ce dont on parle ──────────────────────────────────────────────────
    "depot": [
        "offre", "offres", "soumission", "soumissions", "candidature", "candidatures",
        "remise des offres", "manifestation d interet",
        # « dépôt » tout court est un piège : dans ce métier, c'est d'abord un
        # ENTREPÔT. « Nous disposons d'un dépôt en Belgique » ne parle pas de
        # remise d'offre. On exige donc la forme désambiguïsée.
        "depot des offres", "depot de l offre", "depot des candidatures",
        "depot du dossier", "date de depot", "depot electronique",
        "depot des soumissions",
        "offerte", "offertes", "inschrijving", "inschrijvingen", "indienen",
        "bid", "bids", "tender", "tenders", "submission", "submissions", "proposal",
        "angebot", "angebote", "teilnahmeantrag", "einreichung", "eingereicht",
        "einreichen",
    ],
    "procedure": [
        "procedure", "consultation", "consultations", "marche", "marches",
        "appel", "appels", "concurrence", "adjudication", "phase",
        "aanbesteding", "opdracht", "procedure", "vergabe", "verfahren",
    ],
    # ── ce qu'on en dit ───────────────────────────────────────────────────
    "ouverture": [
        "ouvert", "ouverte", "ouverts", "ouvertes", "en cours", "active", "actif",
        "actuel", "actuelle", "actuellement", "recevable", "recevables", "recevabilite",
        "accepte", "acceptees", "acceptes", "possible", "disponible", "en ligne",
        "publie", "publication", "courant", "courante",
        "peuvent etre deposees", "peut etre deposee", "peuvent etre remises",
        "open", "lopend", "lopende", "mogelijk", "actief", "beschikbaar",
        "kunnen ingediend", "kunnen worden ingediend",
        "can be submitted", "may be submitted", "now accepting",
        "konnen eingereicht", "eingereicht werden", "kann eingereicht",
        "ongoing", "current", "available", "accepting", "live",
        "laufend", "offen", "aktuell", "moglich",
    ],
    "cloture": [
        "cloture", "cloturee", "cloturees", "ferme", "fermee", "termine", "terminee",
        "expire", "expiree", "depasse", "depassee", "echu", "echue", "close", "closes",
        "fin de", "plus de",
        "gesloten", "afgesloten", "beeindigd", "verstreken", "verlopen",
        "closed", "expired", "ended", "no longer",
        "abgelaufen", "geschlossen", "beendet",
    ],
    "attribution": [
        "attribue", "attribuee", "attribution", "adjuge", "adjugee", "adjudicataire",
        "octroye", "octroyee", "octroi", "retenu", "retenue", "designe", "designee",
        "conclu", "conclue", "titulaire", "lauréat", "laureat",
        "gegund", "gunning", "gegunde", "winnaar", "toegewezen", "opdrachtnemer",
        "award", "awarded", "awardee", "contract awarded", "winner", "successful bidder",
        "zuschlag", "vergeben", "auftragnehmer", "erteilt",
    ],
    "resultat": [
        "resultat", "resultats", "decision", "notification", "avis de resultat",
        "uitslag", "resultaat", "beslissing", "kennisgeving",
        "result", "results", "outcome", "decision",
        "ergebnis", "ergebnisse", "entscheidung", "bekanntmachung",
    ],
    "annulation": [
        "annule", "annulee", "annulation", "retire", "retiree", "retrait", "abandonne",
        "abandon", "sans objet",
        "ingetrokken", "geannuleerd", "annulering",
        "cancelled", "canceled", "withdrawn", "cancellation",
        "aufgehoben", "annulliert", "zuruckgezogen",
    ],
    "infructueux": [
        # « aucune offre » seul serait trop gourmand : « aucune offre ne peut
        # désormais être déposée » veut dire FERMÉ, pas INFRUCTUEUX. On exige
        # donc le verbe qui dit qu'on en attendait.
        "infructueux", "infructueuse", "sans suite", "declare sans suite",
        "aucune offre recue", "aucune offre n a ete recue", "sans offre recue",
        "aucune candidature recue", "non attribue faute",
        "zonder gevolg", "geen inschrijvingen ontvangen", "mislukt",
        "unsuccessful", "no bids received", "no tenders received", "failed procedure",
        "ergebnislos", "erfolglos", "aufgehoben ohne",
    ],
    "preinformation": [
        "preinformation", "pre information", "prealable", "preavis", "planification",
        "intention", "programmation", "futur marche", "a venir", "envisage",
        "vooraankondiging", "voorafgaande", "voornemen",
        "prior information", "planned", "forthcoming", "future", "intention to",
        "vorinformation", "vorabinformation", "geplant",
    ],
    "appel_a_projets": [
        "appel a projets", "appel a projet", "appel a candidatures", "appel a manifestation",
        "subvention", "subventions",
        "projectoproep", "oproep tot projecten",
        "call for projects", "call for proposals", "grant",
        "projektaufruf", "forderaufruf",
    ],
    "rectificatif": [
        "rectificatif", "rectification", "modificatif", "avis modifie", "erratum",
        "corrigendum", "rechtzetting", "wijziging", "berichtigung",
    ],
    # ── modificateurs ─────────────────────────────────────────────────────
    "negation": [
        "ne", "n", "pas", "plus", "aucun", "aucune", "sans", "jamais", "ni",
        "niet", "geen", "nooit", "niet meer",
        "no", "not", "none", "without", "cannot", "can no longer", "nor",
        "nicht", "kein", "keine", "ohne", "nie",
    ],
    "futur": [
        "sera", "seront", "prochainement", "bientot", "a venir", "prevu", "prevue",
        "va etre", "devrait",
        "zal", "binnenkort", "weldra", "gepland",
        "will be", "shortly", "upcoming", "to be", "expected",
        "wird", "demnachst", "voraussichtlich",
    ],
    "pas_encore": [
        "pas encore", "n a pas encore", "aucun encore", "en attente", "en cours d examen",
        "en cours d analyse", "en cours de selection", "selection en cours",
        "nog niet", "in behandeling", "in afwachting",
        "not yet", "pending", "under evaluation", "under review", "being evaluated",
        "noch nicht", "in prufung", "ausstehend",
    ],
}

_MARQUEURS_PLATS = {concept: sorted({normaliser(m).strip() for m in mots}, key=len,
                                    reverse=True)
                    for concept, mots in MARQUEURS.items()}


def trouver(concept: str, plat: str) -> list[str]:
    """Les expressions d'un concept réellement présentes dans le texte."""
    return [m for m in _MARQUEURS_PLATS.get(concept, []) if m and f" {m} " in plat]


# Fenêtre autour d'un marqueur dans laquelle une négation le concerne. Au-delà,
# le « pas » de la phrase suivante ne nie plus rien.
FENETRE_NEGATION = 60


def _nie(plat: str, expression: str) -> bool:
    """Une négation porte-t-elle sur cette expression ?

    « les offres ne sont plus acceptées » nie « acceptees ».
    « les offres sont acceptées, aucun document n'est requis » ne la nie pas :
    la négation est trop loin, et elle vient après.

    On ne regarde QUE ce qui précède. Sinon « déclaré sans suite » se nierait
    lui-même : « sans » est à la fois un mot de négation et un morceau de
    l'expression qu'on teste.
    """
    pos = plat.find(f" {expression} ")
    if pos < 0:
        return False
    avant = plat[max(0, pos - FENETRE_NEGATION):pos + 1]
    return any(f" {n} " in avant for n in _MARQUEURS_PLATS["negation"])


def _porte(plat: str, concept: str, modificateur: str) -> bool:
    """Un modificateur (futur, pas_encore) porte-t-il sur ce concept ?"""
    for expression in trouver(concept, plat):
        pos = plat.find(f" {expression} ")
        zone = plat[max(0, pos - FENETRE_NEGATION):pos + len(expression) + FENETRE_NEGATION]
        if any(f" {m} " in zone for m in _MARQUEURS_PLATS[modificateur]):
            return True
    return False


# ═════════════════════════════════════════════ lecture d'une formulation libre
def interpreter_formulation(texte: str, *, origine: str = "texte") -> list[Preuve]:
    """Lit une phrase et en tire des preuves — négations et futur compris.

    Cette fonction ne connaît AUCUN portail. Elle est utilisée telle quelle
    pour « les soumissions peuvent être déposées jusqu'au… » sur un portail
    public, pour « nous cherchons actuellement un partenaire logistique »
    trouvé par un moteur de recherche, et pour « capacité recherchée sur la
    liaison Rotterdam-Bruxelles » d'une bourse de fret.
    """
    plat = normaliser(texte)
    if plat.strip() == "":
        return []
    preuves: list[Preuve] = []

    def dire(conclusion, observation, confiance=Confiance.MOYENNE, exclut=()):
        # Une formulation dont on est SÛR de la lecture — « procédure clôturée »,
        # « marché attribué », « les offres ne sont plus acceptées » — n'est pas
        # une impression : c'est l'état de la procédure, dit en toutes lettres.
        rang = RANG_ETAT_EXPLICITE if confiance is Confiance.ELEVEE else RANG_FORMULATION
        preuves.append(Preuve(rang, observation, conclusion, confiance, exclut=exclut))

    annulation = [m for m in trouver("annulation", plat) if not _nie(plat, m)]
    infructueux = [m for m in trouver("infructueux", plat) if not _nie(plat, m)]
    attribution = trouver("attribution", plat)
    attribution_affirmee = [m for m in attribution if not _nie(plat, m)]
    attribution_niee = [m for m in attribution if _nie(plat, m)]
    cloture = [m for m in trouver("cloture", plat) if not _nie(plat, m)]
    ouverture = trouver("ouverture", plat)
    ouverture_affirmee = [m for m in ouverture if not _nie(plat, m)]
    ouverture_niee = [m for m in ouverture if _nie(plat, m)]
    depot = trouver("depot", plat)
    depot_nie = [m for m in depot if _nie(plat, m)]
    preinfo = [m for m in trouver("preinformation", plat) if not _nie(plat, m)]
    projets = trouver("appel_a_projets", plat)

    # 1. Les états terminaux non ambigus.
    if annulation:
        dire(Etat.ANNULE, f"{origine} : « {annulation[0]} »", Confiance.ELEVEE)
    if infructueux:
        dire(Etat.INFRUCTUEUX, f"{origine} : « {infructueux[0]} »", Confiance.ELEVEE)

    # 2. L'attribution — le point le plus piégeux du module.
    if attribution_affirmee:
        futur = _porte(plat, "attribution", "futur")
        pas_encore = _porte(plat, "attribution", "pas_encore")
        if pas_encore or attribution_niee:
            # « aucun soumissionnaire n'a encore été désigné » : ce n'est PAS
            # une attribution, et ce n'est surtout pas une ouverture non plus.
            dire(None, f"{origine} : attribution explicitement PAS encore prononcée",
                 Confiance.MOYENNE, exclut=(Etat.ATTRIBUE, Etat.POSTULABLE))
        elif futur:
            # « le marché sera attribué prochainement » : procédure avancée.
            # Ni attribuée, ni forcément fermée — on exclut, on ne conclut pas.
            dire(None, f"{origine} : attribution ANNONCÉE mais non prononcée",
                 Confiance.MOYENNE, exclut=(Etat.ATTRIBUE,))
        else:
            dire(Etat.ATTRIBUE, f"{origine} : « {attribution_affirmee[0]} »",
                 Confiance.ELEVEE)
    elif attribution_niee:
        dire(None, f"{origine} : « {attribution_niee[0]} » est nié",
             Confiance.MOYENNE, exclut=(Etat.ATTRIBUE,))

    # 2 bis. « sélection en cours », « en cours d'évaluation », « pending » :
    #         la phase de dépôt est derrière, la décision n'est pas prise.
    #         On EXCLUT, on ne conclut pas — c'est le contraire d'une certitude.
    attente = [m for m in trouver("pas_encore", plat) if not _nie(plat, m)]
    if attente and not attribution_affirmee:
        dire(None, f"{origine} : « {attente[0]} » — décision en attente",
             Confiance.MOYENNE, exclut=(Etat.POSTULABLE, Etat.ATTRIBUE))

    # 3. Un résultat publié dit qu'il s'est passé quelque chose — pas quoi.
    resultat = [m for m in trouver("resultat", plat) if not _nie(plat, m)]
    if resultat and not attribution_affirmee and not preuves:
        dire(Etat.FERME, f"{origine} : « {resultat[0]} » — issue publiée, "
                         f"attribution non nommée", Confiance.FAIBLE)

    # 4. La clôture, et le dépôt nié — deux façons de dire « c'est fini ».
    if cloture:
        dire(Etat.FERME, f"{origine} : « {cloture[0]} »", Confiance.ELEVEE)
    if depot_nie or (depot and ouverture_niee):
        quoi = (depot_nie or depot)[0]
        dire(Etat.FERME, f"{origine} : « {quoi} » sous négation — "
                         f"plus de dépôt possible", Confiance.ELEVEE)

    # 5. L'ouverture — seulement si elle parle bien d'un dépôt ou d'une procédure.
    #    « la société est active depuis 1998 » ne rend rien postulable.
    if ouverture_affirmee and (depot or trouver("procedure", plat)):
        if not cloture and not depot_nie:
            dire(Etat.POSTULABLE,
                 f"{origine} : « {ouverture_affirmee[0]} » porte sur "
                 f"« {(depot or trouver('procedure', plat))[0]} »", Confiance.MOYENNE)

    # 6. Préinformation et appels à projets : des types, pas des états ouverts.
    if preinfo:
        dire(Etat.INFORMATIF, f"{origine} : « {preinfo[0]} »", Confiance.ELEVEE)
    if projets:
        dire(None, f"{origine} : « {projets[0]} » — objet et conditions à "
                   f"analyser avant de conclure", Confiance.FAIBLE,
             exclut=(Etat.POSTULABLE,))
    return preuves


# ═══════════════════════════════════════════════════════ le registre par source
# Interprétations qu'un adaptateur peut déclarer pour ses propres valeurs.
INTERPRETATIONS = {
    "postulable": Etat.POSTULABLE,
    "attribue": Etat.ATTRIBUE,
    "ferme": Etat.FERME,
    "annule": Etat.ANNULE,
    "infructueux": Etat.INFRUCTUEUX,
    "informatif": Etat.INFORMATIF,
    "inconnu": Etat.INCONNU,
    "a_evaluer": None,          # reconnu, mais ne conclut pas seul
}
CONFIANCES = {"elevee": Confiance.ELEVEE, "moyenne": Confiance.MOYENNE,
              "faible": Confiance.FAIBLE, "nulle": Confiance.NULLE}


class Vocabulaire:
    """Ce qu'UNE source dit, et ce que ça veut dire chez elle.

    Rien n'est inventé ici : seules les valeurs réellement observées sur le
    portail y figurent. Une valeur absente du registre ne devient pas
    POSTULABLE par ressemblance — elle ressort « STATUT SOURCE INCONNU », est
    mémorisée, et l'interprétation générale prend le relais sans autorité.
    """

    def __init__(self, config: dict | None = None):
        cfg = (config or {}).get("procedure", {}) or {}
        self.statuts = self._table(cfg.get("statuts", {}))
        self.types = self._table(cfg.get("types_information", {}))

    @staticmethod
    def _table(brut: dict) -> dict:
        table = {}
        for valeur, spec in (brut or {}).items():
            spec = spec or {}
            table[normaliser(valeur).strip()] = {
                "libelle": str(valeur),
                "etat": INTERPRETATIONS.get(str(spec.get("interpretation", "")).lower(),
                                            "ABSENT"),
                "confiance": CONFIANCES.get(str(spec.get("confiance", "moyenne")).lower(),
                                            Confiance.MOYENNE),
                "note": spec.get("note"),
                "normalise": spec.get("normalise") or str(valeur),
            }
        return table

    def lire_statut(self, valeur) -> dict | None:
        return self.statuts.get(normaliser(valeur).strip()) if valeur else None

    def lire_type(self, valeur) -> dict | None:
        return self.types.get(normaliser(valeur).strip()) if valeur else None


# ═══════════════════════════════════════════════════════════ la lecture complète
def lire(*, statut_source=None, type_information=None, titre="", texte="",
         texte_autour_du_statut="", documents=(), evenements=(), actions_possibles=(),
         echeance=None, date_attribution=None, titulaire=None, maintenant=None,
         vocabulaire: Vocabulaire | None = None, source="") -> Lecture:
    """Assemble toutes les preuves disponibles et applique la hiérarchie.

    `documents` et `actions_possibles` sont volontairement séparés du texte :
    un document nommé « avis d'attribution » NE conclut PAS sur l'état de la
    procédure — il produit au mieux un point à vérifier. C'est la différence
    entre le statut d'un document et le statut d'une procédure.
    """
    voc = vocabulaire or Vocabulaire()
    lecture = Lecture(titulaire=titulaire, date_attribution=date_attribution)
    preuves: list[Preuve] = []

    plat_global = normaliser(" ".join(str(x) for x in
                                      (titre, texte, texte_autour_du_statut) if x))
    lecture.procedure_detectee = bool(
        statut_source or type_information or evenements or echeance is not None
        or date_attribution or trouver("procedure", plat_global)
        or trouver("depot", plat_global))

    # ── rang 5 : le statut déclaré par la source ────────────────────────────
    if statut_source:
        connu = voc.lire_statut(statut_source)
        if connu is None:
            lecture.inconnues.append(("statut", str(statut_source)))
            lecture.a_verifier.append(
                f"STATUT SOURCE INCONNU « {statut_source} » — à évaluer ; "
                f"l'adaptateur « {source or '?'} » ne connaît pas cette valeur")
        elif connu["etat"] not in (None, "ABSENT"):
            preuves.append(Preuve(RANG_STATUT_DECLARE,
                                  f"statut déclaré « {connu['libelle']} »",
                                  connu["etat"], connu["confiance"]))
        elif connu["etat"] is None:
            lecture.a_verifier.append(
                connu["note"] or f"statut « {connu['libelle']} » reconnu mais "
                                 f"non concluant à lui seul")

    # ── rang 4 : le type d'information du portail ───────────────────────────
    if type_information:
        lecture.type_information_source = str(type_information)
        connu = voc.lire_type(type_information)
        if connu is None:
            lecture.inconnues.append(("type_information", str(type_information)))
            lecture.a_verifier.append(
                f"TYPE D'INFORMATION INCONNU « {type_information} » — à évaluer")
            # On tente quand même de comprendre l'intitulé, sans autorité.
            for p in interpreter_formulation(type_information,
                                             origine="type d'information"):
                # Rubrique inconnue : on tente de la comprendre, mais elle ne
                # pèse pas plus qu'une phrase — surtout pas autant qu'une
                # rubrique réellement déclarée par l'adaptateur.
                p.rang = RANG_FORMULATION
                p.confiance = Confiance.FAIBLE
                preuves.append(p)
        else:
            lecture.type_information = connu["normalise"]
            if connu["etat"] not in (None, "ABSENT"):
                preuves.append(Preuve(RANG_TYPE_INFORMATION,
                                      f"catégorie « {connu['libelle']} »",
                                      connu["etat"], connu["confiance"]))
            elif connu["etat"] is None:
                lecture.a_verifier.append(
                    connu["note"] or f"catégorie « {connu['libelle']} » : "
                                     f"analyse au cas par cas")

    # ── rang 3 : les événements de procédure, datés ─────────────────────────
    for ev in evenements or ():
        nom = ev.get("type") if isinstance(ev, dict) else str(ev)
        quand = ev.get("date") if isinstance(ev, dict) else None
        for p in interpreter_formulation(nom, origine="événement de procédure"):
            if p.conclusion is not None:
                p.rang = RANG_EVENEMENT
                p.observation += f" (le {quand})" if quand else ""
                preuves.append(p)
    if date_attribution or titulaire:
        detail = " · ".join(filter(None, [f"titulaire {titulaire}" if titulaire else "",
                                          f"attribué le {date_attribution}"
                                          if date_attribution else ""]))
        preuves.append(Preuve(RANG_EVENEMENT, detail, Etat.ATTRIBUE, Confiance.ELEVEE))

    # ── rang 2 : les formulations libres ────────────────────────────────────
    for morceau, origine in ((texte_autour_du_statut, "texte du statut"),
                             (titre, "intitulé"), (texte, "description")):
        if morceau:
            preuves += interpreter_formulation(morceau, origine=origine)

    # Les actions offertes par la page valent une formulation, pas plus.
    for action in actions_possibles or ():
        for p in interpreter_formulation(str(action), origine="action proposée"):
            preuves.append(p)

    # ── les documents ne concluent JAMAIS ───────────────────────────────────
    for doc in documents or ():
        indices = interpreter_formulation(str(doc), origine="document joint")
        etats = {p.conclusion for p in indices if p.conclusion}
        if etats:
            lecture.a_verifier.append(
                f"un document « {doc} » évoque "
                f"{'/'.join(sorted(e.value for e in etats))} — "
                f"le statut d'un document n'est pas celui de la procédure")

    # ── rang 1 : les dates ──────────────────────────────────────────────────
    if echeance is not None and maintenant is not None:
        if echeance <= maintenant:
            # Une date limite dépassée ferme le dépôt. Elle ne prouve
            # AUCUNE attribution : c'est la confusion que ce module existe
            # pour empêcher.
            preuves.append(Preuve(RANG_TEMPOREL,
                                  f"date limite dépassée ({echeance:%d/%m/%Y})",
                                  Etat.FERME, Confiance.MOYENNE))
        else:
            preuves.append(Preuve(RANG_TEMPOREL,
                                  f"date limite à venir ({echeance:%d/%m/%Y})",
                                  Etat.POSTULABLE, Confiance.FAIBLE))

    return _trancher(lecture, preuves)


def _seulement_temporel(preuves) -> bool:
    return bool(preuves) and all(p.rang <= RANG_TEMPOREL for p in preuves
                                 if p.conclusion is not None)


def _trancher(lecture: Lecture, preuves: list) -> Lecture:
    """Applique la hiérarchie, garde les contradictions visibles."""
    lecture.preuves = sorted(preuves, key=lambda p: -p.rang)

    # La source a publié un STATUT, et on n'a pas su le lire. Conclure sur le
    # seul calendrier reviendrait à substituer notre calcul à sa déclaration :
    # une date future ne dit pas ce que « phase gamma » voulait dire.
    #
    # Une RUBRIQUE inconnue ne déclenche pas ce verrou : une rubrique de listing
    # est un classement, pas une déclaration d'état. Le verrou est réservé au
    # champ que la source a rempli pour dire où en est sa procédure.
    statut_illisible = any(champ == "statut" for champ, _ in lecture.inconnues)
    if statut_illisible and _seulement_temporel(preuves):
        lecture.etat = Etat.INCONNU
        lecture.confiance = Confiance.NULLE
        lecture.a_verifier.append(
            "la source publie un statut non interprétable : la date seule ne "
            "suffit pas à conclure")
        return lecture

    interdits: set = set()
    for p in preuves:
        interdits |= set(p.exclut)

    concluantes = [p for p in lecture.preuves
                   if p.conclusion is not None and p.conclusion not in interdits]
    ecartees = [p for p in lecture.preuves
                if p.conclusion is not None and p.conclusion in interdits]
    for p in ecartees:
        lecture.contradictions.append(
            f"{p.conclusion.value} écarté : une preuve plus précise l'exclut "
            f"({p.observation})")

    if not concluantes:
        lecture.etat = Etat.INCONNU
        lecture.confiance = Confiance.NULLE
        exclusions = [p for p in lecture.preuves if p.exclut]
        if exclusions:
            # On a compris quelque chose : ce que ce N'EST PAS. C'est déjà une
            # information, et beaucoup plus honnête qu'un POSTULABLE par défaut.
            lecture.a_verifier.append(
                f"interprété sans conclure : {exclusions[0].observation} — "
                f"état à confirmer à la source")
        elif not lecture.a_verifier:
            lecture.a_verifier.append(
                "aucune formulation interprétable — état à confirmer à la source")
        return lecture

    meilleur = concluantes[0].rang
    tete = [p for p in concluantes if p.rang == meilleur]
    etats = {p.conclusion for p in tete}

    # FERMÉ dit « on ne peut plus déposer ». ATTRIBUÉ, ANNULÉ et INFRUCTUEUX
    # disent la même chose ET pourquoi. Ce n'est donc pas une contradiction :
    # c'est la même réalité, dite avec plus de précision.
    if len(etats) > 1 and Etat.FERME in etats:
        precis = etats - {Etat.FERME}
        if len(precis) == 1 and precis <= PLUS_PRECIS_QUE_FERME:
            etats = precis
            tete = [p for p in tete if p.conclusion in precis]

    if len(etats) > 1:
        # Deux preuves de même force qui se contredisent : on ne tranche pas.
        lecture.etat = Etat.INCONNU
        lecture.confiance = Confiance.NULLE
        lecture.contradictions.append(
            "preuves de même rang contradictoires : "
            + " / ".join(sorted(e.value for e in etats)))
        lecture.a_verifier.append("état à confirmer manuellement à la source")
        return lecture

    lecture.etat = tete[0].conclusion
    lecture.confiance = max((p.confiance for p in tete),
                            key=lambda c: list(Confiance).index(c) * -1)

    # Une preuve de rang inférieur qui dit autre chose est une contradiction :
    # le rang fort décide, mais la contradiction reste affichée et fait baisser
    # la confiance.
    for p in concluantes[len(tete):]:
        if p.conclusion is not lecture.etat:
            lecture.contradictions.append(
                f"{NOM_DU_RANG[p.rang]} dit {p.conclusion.value} "
                f"({p.observation}) — écarté par « {tete[0].observation} »")
            if lecture.confiance is Confiance.ELEVEE:
                lecture.confiance = Confiance.MOYENNE
            elif lecture.confiance is Confiance.MOYENNE:
                lecture.confiance = Confiance.FAIBLE
    return lecture


# ═══════════════════════════════════════ mémoire du vocabulaire rencontré
def memoriser(cx, source: str, lecture: Lecture, contexte: str = "") -> int:
    """Conserve les expressions que l'adaptateur ne connaissait pas.

    Rien n'est interprété ici : on enregistre ce qui a été LU, pour qu'un
    humain tranche une fois et que la collecte suivante n'ait plus à
    réinterpréter. `interpretation` reste NULL tant que personne n'a décidé —
    et tant qu'elle est NULL, l'état de la procédure reste INCONNU.
    """
    from .base import maintenant
    n = 0
    for champ, expression in lecture.inconnues:
        cx.execute(
            "INSERT INTO vocabulaire(source, champ, expression, contexte, vu_le)"
            " VALUES(?,?,?,?,?)"
            " ON CONFLICT(source, champ, expression) DO UPDATE SET"
            " occurrences = occurrences + 1, vu_le = excluded.vu_le",
            (source, champ, str(expression), contexte[:200], maintenant()))
        n += 1
    return n


def reviser(cx, source: str, champ: str, expression: str, interpretation: str,
            *, confiance: str = "moyenne", motif: str = "", par: str = "") -> None:
    """Tranche — ou corrige — une expression, sans effacer l'ancienne lecture.

    Une interprétation fausse découverte plus tard ne doit pas disparaître :
    les fiches produites avec elle existent, et il faut pouvoir les retrouver.
    """
    from .base import maintenant
    if interpretation not in INTERPRETATIONS:
        raise ValueError(
            f"interprétation inconnue « {interpretation} » — "
            f"attendu : {', '.join(sorted(INTERPRETATIONS))}")
    ligne = cx.execute(
        "SELECT id, interpretation, confiance FROM vocabulaire"
        " WHERE source=? AND champ=? AND expression=?",
        (source, champ, expression)).fetchone()
    if ligne is None:
        cx.execute(
            "INSERT INTO vocabulaire(source, champ, expression, interpretation,"
            " confiance, preuve, vu_le, revise_le, revise_par)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (source, champ, expression, interpretation, confiance, motif,
             maintenant(), maintenant(), par or "?"))
        return
    cx.execute(
        "INSERT INTO vocabulaire_historique(vocabulaire_id, interpretation,"
        " confiance, motif, remplace_le, par) VALUES(?,?,?,?,?,?)",
        (ligne["id"], ligne["interpretation"], ligne["confiance"], motif,
         maintenant(), par or "?"))
    cx.execute(
        "UPDATE vocabulaire SET interpretation=?, confiance=?, preuve=?,"
        " revise_le=?, revise_par=? WHERE id=?",
        (interpretation, confiance, motif, maintenant(), par or "?", ligne["id"]))


def vocabulaire_appris(cx, source: str) -> Vocabulaire:
    """Le vocabulaire tranché en base, prêt à compléter celui de l'adaptateur.

    Seules les expressions RÉELLEMENT tranchées entrent : une expression vue
    mais non interprétée reste inconnue, et c'est voulu.
    """
    voc = Vocabulaire()
    for l in cx.execute(
            "SELECT champ, expression, interpretation, confiance FROM vocabulaire"
            " WHERE source=? AND interpretation IS NOT NULL", (source,)):
        table = voc.statuts if l["champ"] == "statut" else voc.types
        table[normaliser(l["expression"]).strip()] = {
            "libelle": l["expression"],
            "etat": INTERPRETATIONS.get(l["interpretation"], "ABSENT"),
            "confiance": CONFIANCES.get(l["confiance"] or "moyenne", Confiance.MOYENNE),
            "note": None,
            "normalise": l["expression"],
        }
    return voc


def fusionner_vocabulaires(*vocabulaires) -> Vocabulaire:
    """Le vocabulaire déclaré par l'adaptateur, complété par celui appris.

    L'adaptateur passe en dernier : ce qu'un humain a écrit dans le YAML prime
    toujours sur ce que la mémoire a retenu.
    """
    fusion = Vocabulaire()
    for v in vocabulaires:
        if v is None:
            continue
        fusion.statuts.update(v.statuts)
        fusion.types.update(v.types)
    return fusion
