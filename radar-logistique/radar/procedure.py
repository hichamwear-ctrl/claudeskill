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
    ANNONCE = "ANNONCÉ"          # le besoin existe, la procédure n'est pas ouverte
    ATTRIBUE = "ATTRIBUÉ"
    FERME = "FERMÉ"
    ANNULE = "ANNULÉ"
    INFRUCTUEUX = "INFRUCTUEUX"
    INFORMATIF = "INFORMATIF"
    INCONNU = "INCONNU"

    @property
    def emoji(self) -> str:
        return {"POSTULABLE": "🟢", "ANNONCÉ": "🟡", "ATTRIBUÉ": "🔵",
                "FERMÉ": "🟠", "ANNULÉ": "⚫", "INFRUCTUEUX": "⚪",
                "INFORMATIF": "🟣", "INCONNU": "❓"}[self.value]

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
            "ANNONCÉ": "besoin identifié — la procédure n'est pas encore ouverte",
            "ATTRIBUÉ": "marché attribué — le titulaire devra exécuter",
            "FERMÉ": "candidature terminée — attribution non publiée",
            "ANNULÉ": "procédure annulée",
            "INFRUCTUEUX": "procédure sans suite",
            "INFORMATIF": "information sans besoin identifié — aucune action directe",
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

# Noms utilisables dans `procedure.hierarchie` d'un adaptateur. Un portail dont
# les rubriques sont notoirement en retard peut les rétrograder sous les dates,
# sans que le moteur ait à connaître ce portail.
RANGS_CONFIGURABLES = {
    "statut": RANG_STATUT_DECLARE,
    "etat_explicite": RANG_ETAT_EXPLICITE,
    "evenement": RANG_EVENEMENT,
    "rubrique": RANG_TYPE_INFORMATION,
    "formulation": RANG_FORMULATION,
    "date": RANG_TEMPOREL,
}

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
    # Y a-t-il quelque chose OÙ DÉPOSER ? Question distincte de la précédente.
    # Une bourse de fret porte une date de validité — donc une procédure à
    # qualifier — mais aucun dossier à remettre. C'est ce champ, et lui seul,
    # qui autorise l'action POSTULER.
    depot_organise: bool = False

    @property
    def etat_affiche(self) -> str:
        """Ce qu'on écrit sur la fiche et en base.

        Quand aucune procédure n'existe — une page qui dit « devenez notre
        transporteur partenaire » n'en est pas une — annoncer « état INCONNU »
        serait une fausse alerte : on ferait vérifier quelque chose qui n'existe
        pas. On dit alors ce qui est vrai : il n'y a pas de procédure.
        """
        if self.etat is Etat.INCONNU and not self.procedure_detectee:
            return "HORS PROCÉDURE"
        return self.etat.value

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
        # Ces mots doivent désigner une PROCÉDURE, pas n'importe quel appel.
        # « Appel à sous-traitants » sur le site d'une PME est un besoin
        # exprimé directement, pas une consultation dont l'état serait inconnu.
        # Le mot « appel » seul faisait inventer une procédure fantôme, et
        # l'opportunité ressortait « VÉRIFIER L'ÉTAT » au lieu de « CONTACTER ».
        # Même prudence pour « marché », qui veut aussi dire « le marché ».
        "procedure", "procedure de passation", "consultation", "consultations",
        "appel d offres", "appel a la concurrence", "appel a concurrence",
        "appel a candidatures", "en concurrence", "soumissionner",
        "mise en concurrence", "marche public", "marches publics",
        "adjudication", "cahier des charges", "pouvoir adjudicateur",
        "aanbesteding", "overheidsopdracht", "bestek", "lopende opdracht",
        "public procurement", "call for tenders", "contract notice",
        "vergabeverfahren", "ausschreibung",
    ],
    # ── ce qu'on en dit ───────────────────────────────────────────────────
    "ouverture": [
        "ouvert", "ouverte", "ouverts", "ouvertes", "en cours", "active", "actif",
        "actuel", "actuelle", "actuellement", "recevable", "recevables", "recevabilite",
        "accepte", "acceptees", "acceptes", "possible", "disponible", "en ligne",
        "publie", "publication", "courant", "courante",
        # « introduire une offre » est la formulation belge standard. Son absence
        # laissait « les soumissions peuvent encore être introduites » en INCONNU.
        "peuvent etre deposees", "peut etre deposee", "peuvent etre remises",
        "peuvent etre introduites", "peut etre introduite", "peuvent encore etre",
        "encore ouvertes", "encore ouvert", "encore possible", "toujours ouvert",
        "toujours ouverte", "introduire une offre", "introduire votre offre",
        "open", "lopend", "lopende", "mogelijk", "actief", "beschikbaar",
        "kunnen ingediend", "kunnen worden ingediend",
        "can be submitted", "may be submitted", "now accepting",
        "konnen eingereicht", "eingereicht werden", "kann eingereicht",
        "ongoing", "current", "available", "accepting", "live",
        "currently being accepted", "are being accepted", "now open",
        "lopend", "lopende opdracht", "demande de prix", "demandes de prix",
        "laufend", "laufendes", "laufende", "offen", "aktuell", "moglich",
    ],
    "cloture": [
        "cloture", "cloturee", "cloturees", "ferme", "fermee", "termine", "terminee",
        "expire", "expiree", "depasse", "depassee", "echu", "echue", "close", "closes",
        "fin de",
        # « plus de » SEUL est un piège que seule une vraie donnée a révélé :
        # « Sous Traitant : plus de 400 emplois » ressortait FERMÉ. En français
        # « plus de » est d'abord une QUANTITÉ. Le sens de clôture demande une
        # négation devant — « il n'y a plus de », « ne sont plus » — et celle-ci
        # est déjà couverte par les marqueurs de négation.
        # Conséquence du défaut : tout listing réel annonçant « plus de 50
        # marchés » disparaissait de la liste à attaquer.
        "n y a plus de", "il n y a plus", "plus aucune", "plus aucun",
        # « achevee » manquait : « procédure achevée » ressortait POSTULABLE —
        # le pire des états à se tromper, puisqu'il envoie préparer un dossier
        # sur un marché fini. Ajouté avec ses voisins du même registre.
        "acheve", "achevee", "achevees", "aboutie", "soldee", "revolue",
        "n'est plus", "n est plus", "hors delai", "forclos", "forclose",
        "gesloten", "afgesloten", "beeindigd", "verstreken", "verlopen",
        "voltooid", "afgerond", "niet meer",
        "closed", "expired", "ended", "no longer", "deadline has passed",
        "has passed", "past the deadline", "completed", "concluded",
        "abgelaufen", "geschlossen", "beendet", "abgeschlossen", "nicht mehr",
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
        # « non » manquait. « offres non recevables » ressortait POSTULABLE :
        # le pire cas possible — affirmer qu'on peut déposer sur un marché fermé.
        "ne", "n", "pas", "plus", "non", "aucun", "aucune", "sans", "jamais", "ni",
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
        "phase de selection", "dossier en traitement", "en traitement",
        "decision a venir", "sera annoncee", "sera annonce", "annoncee ulterieurement",
        "nog niet", "in behandeling", "in afwachting", "volgt later", "beslissing volgt",
        "not yet", "pending", "under evaluation", "under review", "being evaluated",
        "evaluation in progress", "decision to follow",
        "noch nicht", "in prufung", "ausstehend", "steht noch aus", "folgt spater",
    ],
}

_MARQUEURS_PLATS = {concept: sorted({normaliser(m).strip() for m in mots}, key=len,
                                    reverse=True)
                    for concept, mots in MARQUEURS.items()}


# Un marqueur suivi de l'un de ces mots ne parle PAS de procédure. Mesuré sur
# une donnée réelle : « Offres d'emploi » faisait détecter une procédure, donc
# un état INCONNU, donc « VÉRIFIER L'ÉTAT À LA SOURCE » sur une annonce
# d'embauche. Le radar envoyait vérifier l'état d'un marché qui n'existe pas.
SUITES_QUI_ANNULENT = {
    "offre": ("d emploi", "d emplois", "de stage", "de service", "de services",
              "speciale", "promotionnelle", "commerciale"),
    "offres": ("d emploi", "d emplois", "de stage", "de service", "de services",
               "speciales", "promotionnelles", "commerciales"),
    "candidature": ("spontanee", "spontanees"),
    "candidatures": ("spontanees",),
}


def trouver(concept: str, plat: str) -> list[str]:
    """Les expressions d'un concept réellement présentes dans le texte.

    Un marqueur immédiatement suivi d'une suite qui l'annule n'est pas retenu :
    « offres d'emploi » n'est pas « offres » au sens d'une remise d'offre.
    """
    sortie = []
    for m in _MARQUEURS_PLATS.get(concept, []):
        if not m or f" {m} " not in plat:
            continue
        suites = SUITES_QUI_ANNULENT.get(m)
        if suites and all(f" {m} {suite} " in plat
                          for suite in [s for s in suites if f" {m} {s} " in plat]) \
                and any(f" {m} {suite} " in plat for suite in suites):
            # Toutes les occurrences repérables sont annulées par leur suite.
            reste = plat.replace(f" {m} ", " § ")
            for suite in suites:
                reste = reste.replace(f" § {suite} ", " ")
            if f" § " not in reste:
                continue
        sortie.append(m)
    return sortie


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
            # « Le marché sera attribué prochainement » : la procédure est
            # avancée. Elle n'est pas attribuée — mais elle n'est PAS ouverte
            # non plus : on ne dépose pas une offre sur un marché dont
            # l'attribution est annoncée. Exclure ATTRIBUÉ sans exclure
            # POSTULABLE laissait la rubrique du portail conclure « en cours »,
            # et le radar invitait à monter un dossier pour rien.
            dire(None, f"{origine} : attribution ANNONCÉE mais non prononcée",
                 Confiance.MOYENNE, exclut=(Etat.ATTRIBUE, Etat.POSTULABLE))
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
    if preinfo and not attribution:
        # Un avis de préinformation dit qu'un besoin EXISTE et qu'il sera mis en
        # concurrence. Ce n'est pas « pas utile » : c'est la meilleure fenêtre
        # commerciale du cycle, avant que tout le monde arrive.
        #
        # Mais « décision d'ATTRIBUTION à venir » n'annonce pas un marché : elle
        # annonce la fin de celui-ci. Le « à venir » porte sur l'attribution,
        # pas sur le besoin — et confondre les deux transformait une procédure
        # qui se termine en occasion qui commence.
        dire(Etat.ANNONCE, f"{origine} : « {preinfo[0]} »", Confiance.ELEVEE)
    if projets:
        dire(None, f"{origine} : « {projets[0]} » — objet et conditions à "
                   f"analyser avant de conclure", Confiance.FAIBLE,
             exclut=(Etat.POSTULABLE,))
    return preuves


# ═══════════════════════════════════════════════════════ le registre par source
# Interprétations qu'un adaptateur peut déclarer pour ses propres valeurs.
INTERPRETATIONS = {
    "postulable": Etat.POSTULABLE,
    "annonce": Etat.ANNONCE,
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
        self.langue = cfg.get("langue") or (config or {}).get("langue")
        # Hiérarchie propre à cette source, quand la générale ne convient pas.
        self.rangs = dict(RANGS_CONFIGURABLES)
        for nom, rang in (cfg.get("hierarchie") or {}).items():
            if nom not in RANGS_CONFIGURABLES:
                raise ValueError(
                    f"rang inconnu « {nom} » dans la hiérarchie : "
                    f"attendu parmi {', '.join(sorted(RANGS_CONFIGURABLES))}")
            self.rangs[nom] = int(rang)

    def rang(self, nom: str) -> int:
        return self.rangs.get(nom, RANGS_CONFIGURABLES[nom])

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
         vocabulaire: Vocabulaire | None = None, source="", est_signal=False,
         lien_depot=None) -> Lecture:
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
    # Un SIGNAL n'a pas d'état de procédure : « l'entreprise recrute quinze
    # chauffeurs » n'est pas une consultation dont le dépôt serait ouvert ou
    # clos. Confondre la dimension C (nature) et la dimension B (état) ferait
    # afficher « ÉTAT INCONNU · VÉRIFIER » sur un signal parfaitement lisible.
    lecture.procedure_detectee = (not est_signal) and bool(
        statut_source or type_information or evenements or echeance is not None
        or date_attribution or trouver("procedure", plat_global)
        or trouver("depot", plat_global))

    # ── « Y A-T-IL QUELQUE CHOSE OÙ DÉPOSER ? » — une question distincte ──
    #
    # `procedure_detectee` est LARGE à dessein : une simple date limite suffit
    # à mériter qu'on regarde l'état. Mais elle ne suffit PAS à conclure qu'il
    # existe un dossier à remettre.
    #
    # Une annonce de bourse de fret porte une date de validité. Elle a donc
    # `procedure_detectee = True` — et si l'ACTION se décidait là-dessus, le
    # radar dirait « POSTULER » sur une tournée qu'on prend en décrochant son
    # téléphone. Une bourse de fret n'est pas une consultation.
    #
    # `depot_organise` demande une preuve qu'un dépôt EXISTE : un mécanisme de
    # remise (bouton, lien), un vocabulaire de dépôt dans le texte, ou une
    # rubrique/un statut normé qui désigne une procédure. Une date seule, non.
    actions_plates = normaliser(" ".join(str(a) for a in (actions_possibles or [])))
    lecture.depot_organise = bool(
        lien_depot
        or trouver("depot", plat_global)
        or trouver("depot", actions_plates)
        or trouver("procedure", plat_global)
        or statut_source or type_information or evenements)

    # ── rang 5 : le statut déclaré par la source ────────────────────────────
    if statut_source:
        connu = voc.lire_statut(statut_source)
        if connu is None:
            lecture.inconnues.append(("statut", str(statut_source)))
            lecture.a_verifier.append(
                f"STATUT SOURCE INCONNU « {statut_source} » — à évaluer ; "
                f"l'adaptateur « {source or '?'} » ne connaît pas cette valeur")
        elif connu["etat"] not in (None, "ABSENT"):
            preuves.append(Preuve(voc.rang("statut"),
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
                p.rang = voc.rang("formulation")
                p.confiance = Confiance.FAIBLE
                preuves.append(p)
        else:
            lecture.type_information = connu["normalise"]
            if connu["etat"] not in (None, "ABSENT"):
                preuves.append(Preuve(voc.rang("rubrique"),
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
                p.rang = voc.rang("evenement")
                p.observation += f" (le {quand})" if quand else ""
                preuves.append(p)
    if date_attribution or titulaire:
        detail = " · ".join(filter(None, [f"titulaire {titulaire}" if titulaire else "",
                                          f"attribué le {date_attribution}"
                                          if date_attribution else ""]))
        preuves.append(Preuve(voc.rang("evenement"), detail, Etat.ATTRIBUE,
                              Confiance.ELEVEE))

    # ── rang 2 : les formulations libres ────────────────────────────────────
    def _reranger(liste):
        for p in liste:
            p.rang = (voc.rang("etat_explicite") if p.confiance is Confiance.ELEVEE
                      else voc.rang("formulation"))
        return liste

    for morceau, origine in ((texte_autour_du_statut, "texte du statut"),
                             (titre, "intitulé"), (texte, "description")):
        if morceau:
            preuves += _reranger(interpreter_formulation(morceau, origine=origine))

    # Les actions offertes par la page valent une formulation, pas plus.
    for action in actions_possibles or ():
        preuves += _reranger(
            interpreter_formulation(str(action), origine="action proposée"))

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
            # Une date limite dépassée est un FAIT vérifiable, pas une étiquette
            # de rangement. Elle doit donc primer sur la rubrique du portail,
            # qui n'est qu'un classement et se met à jour en retard. L'inverse
            # laissait « Marchés en cours » l'emporter sur une échéance passée.
            preuves.append(Preuve(max(voc.rang("date"), voc.rang("rubrique") + 1),
                                  f"date limite dépassée ({echeance:%d/%m/%Y})",
                                  Etat.FERME, Confiance.MOYENNE))
        else:
            preuves.append(Preuve(voc.rang("date"),
                                  f"date limite à venir ({echeance:%d/%m/%Y})",
                                  Etat.POSTULABLE, Confiance.FAIBLE))

    return _trancher(lecture, preuves)


def _absorber_ferme(etats: set) -> set:
    """FERMÉ dit « on ne peut plus déposer ». ATTRIBUÉ, ANNULÉ et INFRUCTUEUX
    disent la même chose ET pourquoi. Ce n'est pas une contradiction : c'est la
    même réalité, dite avec plus de précision."""
    if len(etats) > 1 and Etat.FERME in etats:
        precis = etats - {Etat.FERME}
        if len(precis) == 1 and precis <= PLUS_PRECIS_QUE_FERME:
            return precis
    return etats


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

    # ══ ZONE DE FORCE ÉGALE ══
    #
    # La hiérarchie sert à départager des preuves NON CONTRADICTOIRES. Elle ne
    # sert pas à faire gagner un champ structuré périmé contre une phrase qui
    # dit le contraire. Deux preuves de confiance ÉLEVÉE qui s'excluent ne
    # produisent donc aucun gagnant, quel que soit leur rang.
    #
    # Un portail n'est pas la vérité : sa rubrique peut être en retard, son
    # champ mal renseigné, sa page de résultat mise à jour après coup.
    fortes = [p for p in concluantes if p.confiance is Confiance.ELEVEE]
    etats_forts = _absorber_ferme({p.conclusion for p in fortes})
    if len(etats_forts) > 1:
        lecture.etat = Etat.INCONNU
        lecture.confiance = Confiance.NULLE
        detail = " / ".join(
            f"{p.conclusion.value} ({NOM_DU_RANG.get(p.rang, 'preuve')} : "
            f"{p.observation})" for p in fortes if p.conclusion in etats_forts)
        lecture.contradictions.append(f"CONTRADICTION À VÉRIFIER — {detail}")
        lecture.a_verifier.append(
            "deux informations de confiance élevée s'excluent : "
            "état à confirmer à la source avant d'engager du temps")
        return lecture

    meilleur = concluantes[0].rang
    tete = [p for p in concluantes if p.rang == meilleur]
    etats = {p.conclusion for p in tete}

    absorbes = _absorber_ferme(etats)
    if absorbes != etats:
        etats = absorbes
        tete = [p for p in tete if p.conclusion in etats]

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
def memoriser(cx, source: str, lecture: Lecture, contexte: str = "",
              langue: str | None = None) -> int:
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
            "INSERT INTO vocabulaire(source, champ, expression, langue, contexte, vu_le)"
            " VALUES(?,?,?,?,?,?)"
            " ON CONFLICT(source, champ, expression) DO UPDATE SET"
            " occurrences = occurrences + 1, vu_le = excluded.vu_le,"
            " langue = COALESCE(vocabulaire.langue, excluded.langue)",
            (source, champ, str(expression), langue or "INCONNUE",
             contexte[:200], maintenant()))
        n += 1
    return n


def reviser(cx, source: str, champ: str, expression: str, interpretation: str,
            *, confiance: str = "moyenne", motif: str = "", par: str = "",
            langue: str | None = None) -> int:
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
        "SELECT id, interpretation, confiance, version FROM vocabulaire"
        " WHERE source=? AND champ=? AND expression=?",
        (source, champ, expression)).fetchone()
    if ligne is None:
        cx.execute(
            "INSERT INTO vocabulaire(source, champ, expression, langue, interpretation,"
            " confiance, preuve, version, vu_le, revise_le, revise_par)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (source, champ, expression, langue or "INCONNUE", interpretation,
             confiance, motif, 1, maintenant(), maintenant(), par or "?"))
        return 1
    # L'ancienne lecture est ARCHIVÉE avec son numéro de version. Les fiches
    # produites sous cette version restent retrouvables : sans ça, une
    # correction effacerait la trace de ce qu'on a cru pendant des semaines.
    cx.execute(
        "INSERT INTO vocabulaire_historique(vocabulaire_id, version, interpretation,"
        " confiance, motif, remplace_le, par) VALUES(?,?,?,?,?,?,?)",
        (ligne["id"], ligne["version"], ligne["interpretation"], ligne["confiance"],
         motif, maintenant(), par or "?"))
    version = (ligne["version"] or 0) + 1
    cx.execute(
        "UPDATE vocabulaire SET interpretation=?, confiance=?, preuve=?, version=?,"
        " revise_le=?, revise_par=? WHERE id=?",
        (interpretation, confiance, motif, version, maintenant(), par or "?",
         ligne["id"]))
    return version


def version_vocabulaire(cx, source: str) -> int:
    """Somme des versions tranchées d'une source. Elle identifie l'état du
    vocabulaire au moment où une lecture a été produite."""
    n = cx.execute("SELECT COALESCE(SUM(version), 0) v FROM vocabulaire"
                   " WHERE source=?", (source,)).fetchone()
    return int(n["v"] if hasattr(n, "keys") else n[0])


def concerne(cx, source: str, champ: str, expression: str) -> list:
    """Les opportunités dont la lecture dépend de cette expression.

    Sert au recalcul contrôlé : avant de corriger un mot, on veut savoir
    combien de fiches vont bouger, et lesquelles.
    """
    colonne = "type_information" if champ == "type_information" else None
    if colonne:
        return cx.execute(
            "SELECT o.avis_id, o.intitule, o.etat_procedure FROM opportunites o"
            " JOIN avis a ON a.id = o.avis_id"
            " WHERE a.source = ? AND o.type_information = ?",
            (source, expression)).fetchall()
    # Pour un statut, la valeur brute n'est pas en colonne : on retrouve les
    # avis par leur contenu brut conservé, jamais par supposition.
    return cx.execute(
        "SELECT DISTINCT o.avis_id, o.intitule, o.etat_procedure"
        " FROM opportunites o JOIN avis a ON a.id = o.avis_id"
        " JOIN reponses r ON r.avis_id = a.id"
        " WHERE a.source = ? AND r.charge LIKE ?",
        (source, f"%{expression}%")).fetchall()


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
