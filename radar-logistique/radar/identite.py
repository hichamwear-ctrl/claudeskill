"""Savons-nous DE QUI on parle ?

    ATTRIBUTION → TITULAIRE → IDENTITÉ → ENTREPRISE → URL → PAGE

Une attribution donne une raison sociale : « Transports Exemple SRL ». Elle ne
donne ni numéro d'entreprise, ni site. Ce module dit ce que le radar sait —
et, bien plus souvent, ce qu'il ne sait pas.

CE QUE CE MODULE NE FERA JAMAIS
===============================

Il ne fabrique pas de domaine à partir d'un nom. La fonction n'existe pas, et
ce n'est pas un oubli : « Transports Exemple SRL » ne devient pas
« transports-exemple.be ». Un domaine inventé ferait consulter le site d'un
tiers et polluerait le registre pour toujours.

Il ne tranche pas entre deux homonymes. Deux entités portant le même nom
donnent AMBIGUË, et les deux candidats sont conservés. En Belgique l'homonymie
est fréquente ; choisir au hasard, c'est se tromper une fois sur deux en
prétendant savoir.

Il ne consulte rien. Aucun réseau, aucun moteur de recherche, aucune API. Il
enregistre ce que des sources lui apportent. La recherche d'identité par un
moteur appartient au circuit DÉCOUVERTE, qui n'est pas accessible aujourd'hui.

QUATRE ÉTATS
============

    INCONNUE   un nom, rien d'autre. Par défaut — et c'est honnête.
               INCONNUE ≠ 0 : le radar n'en sait pas assez, l'entreprise
               existe tout de même.
    AMBIGUË    plusieurs entités portent ce nom. Les candidats sont conservés.
    CONFIRMÉE  une source nommée et datée rattache ce nom à une entité.
    SANS SITE  l'entité est identifiée, et elle n'a pas de site connu. C'est
               une MESURE, pas un échec — au même titre que CONFIRMÉE.

ENTREPRISE ET PAGE NE SE FORCENT PAS L'UNE L'AUTRE
==================================================

    ENTREPRISE CONFIRMÉE + SITE INCONNU     parfaitement valide
    PAGE CONNUE + ENTREPRISE À CONFIRMER    parfaitement valide

On ne déduit pas l'une de l'autre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

# Les sources d'identité admises. L'exploitant en est une ; un moteur de
# recherche en serait une autre, le jour où il y en aura un d'accessible.
EXPLOITANT = "exploitant"
REGISTRE_OFFICIEL = "registre officiel"      # BCE/KBO, ou équivalent étranger
SOURCE_PUBLIQUE = "source publique"          # un avis qui publie le site
DECOUVERTE = "découverte web"                # pas disponible aujourd'hui


class Etat(Enum):
    INCONNUE = "INCONNUE"
    AMBIGUE = "AMBIGUË"
    CONFIRMEE = "CONFIRMÉE"
    SANS_SITE = "SANS SITE"

    @property
    def identifiee(self) -> bool:
        """L'entité est désignée sans ambiguïté. Avoir un site est une autre
        question : SANS SITE est identifiée, elle n'a simplement pas de site."""
        return self in (Etat.CONFIRMEE, Etat.SANS_SITE)

    @property
    def surveillable(self) -> bool:
        """Peut-on ouvrir une surveillance à partir de cette identité ?

        Seulement CONFIRMÉE — et encore, seulement si un domaine a été
        réellement fourni. SANS SITE est identifiée mais n'a rien à surveiller,
        et c'est un état parfaitement valide.
        """
        return self is Etat.CONFIRMEE


class IdentiteIncertaine(ValueError):
    """Levée quand on tente de confirmer sans preuve, ou de choisir à la place
    d'une source."""


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def lire_etat(valeur) -> Etat:
    """Une valeur absente ou illisible reste INCONNUE. On ne promeut jamais
    une identité par défaut."""
    for e in Etat:
        if e.value == valeur:
            return e
    return Etat.INCONNUE


@dataclass
class Candidat:
    """Une entité qui POURRAIT être celle qu'on cherche. Jamais celle qu'on
    a choisie."""
    nom: str
    bce: str | None = None
    domaine: str | None = None
    detail: str | None = None          # ce qui le distingue : zone, activité…
    source: str = EXPLOITANT

    def ligne(self) -> str:
        parties = [self.nom]
        if self.bce:
            parties.append(f"BCE {self.bce}")
        if self.domaine:
            parties.append(self.domaine)
        if self.detail:
            parties.append(self.detail)
        return " · ".join(parties)


@dataclass
class Identite:
    """Ce que le radar sait de l'identité d'une entreprise."""
    etat: Etat = Etat.INCONNUE
    source: str | None = None
    confirmee_le: str | None = None
    preuve: str | None = None
    bce: str | None = None
    domaine: str | None = None
    candidats: list = field(default_factory=list)

    def ligne(self) -> str:
        if self.etat is Etat.INCONNUE:
            return "INCONNUE — le radar ne sait pas encore de qui il s'agit"
        if self.etat is Etat.AMBIGUE:
            return (f"AMBIGUË — {len(self.candidats)} candidat(s) conservé(s), "
                    "aucun choisi")
        quoi = self.domaine or "aucun site connu"
        return (f"{self.etat.value} — {quoi} · source {self.source or '?'} · "
                f"{(self.confirmee_le or '')[:10]}")


# ══════════════════════════════════════════════════ base de données
def lire(cx, cle) -> Identite:
    l = cx.execute("SELECT identite, identite_source, identite_le,"
                   " identite_preuve, bce, domaine FROM entreprises WHERE cle=?",
                   (cle,)).fetchone()
    if l is None:
        return Identite()
    return Identite(etat=lire_etat(l["identite"]), source=l["identite_source"],
                    confirmee_le=l["identite_le"], preuve=l["identite_preuve"],
                    bce=l["bce"], domaine=l["domaine"],
                    candidats=candidats_de(cx, cle))


def candidats_de(cx, cle) -> list[Candidat]:
    return [Candidat(nom=l["nom"], bce=l["bce"], domaine=l["domaine"],
                     detail=l["detail"], source=l["source"])
            for l in cx.execute(
                "SELECT nom, bce, domaine, detail, source FROM identites_candidates"
                " WHERE entreprise=? ORDER BY id", (cle,)).fetchall()]


def proposer(cx, cle, candidats, *, source=EXPLOITANT) -> Identite:
    """Enregistre un ou plusieurs candidats, SANS choisir.

    Un seul candidat ne confirme pas non plus : proposer, c'est apporter une
    piste. Confirmer est une décision, et elle passe par `confirmer()`.
    """
    for c in candidats or []:
        cx.execute(
            "INSERT OR IGNORE INTO identites_candidates"
            "(entreprise, nom, bce, domaine, detail, source, vue_le)"
            " VALUES(?,?,?,?,?,?,?)",
            (cle, c.nom, c.bce, c.domaine, c.detail, c.source or source,
             _maintenant()))
    restants = candidats_de(cx, cle)
    if len(restants) > 1:
        # PLUSIEURS ENTITÉS PORTENT CE NOM. On ne choisit pas. On le dit.
        cx.execute("UPDATE entreprises SET identite=?, identite_source=?,"
                   " identite_le=?, identite_preuve=? WHERE cle=?",
                   (Etat.AMBIGUE.value, source, _maintenant(),
                    f"{len(restants)} entités portent ce nom — aucune choisie",
                    cle))
    return lire(cx, cle)


def confirmer(cx, cle, *, source, preuve, bce=None, domaine=None) -> Identite:
    """Rattache ce nom à une entité, avec sa preuve et sa date.

    `preuve` est obligatoire : une confirmation sans trace relisible est une
    affirmation, pas une identification.

    Aucun domaine n'est dérivé du nom. Si `domaine` est None, l'identité est
    CONFIRMÉE quand même — voir `sans_site()` pour dire explicitement qu'il
    n'y en a pas.
    """
    if not source or not preuve:
        raise IdentiteIncertaine(
            "confirmer une identité exige une source ET une preuve relisible")
    cx.execute("UPDATE entreprises SET identite=?, identite_source=?,"
               " identite_le=?, identite_preuve=?,"
               " bce=COALESCE(?, bce), domaine=COALESCE(?, domaine)"
               " WHERE cle=?",
               (Etat.CONFIRMEE.value, source, _maintenant(), preuve,
                bce, domaine, cle))
    return lire(cx, cle)


def sans_site(cx, cle, *, source, preuve) -> Identite:
    """L'entité est identifiée et n'a PAS de site connu.

    C'est une mesure au même titre qu'une confirmation : elle ferme la
    question au lieu de la laisser traîner en INCONNUE.
    """
    if not source or not preuve:
        raise IdentiteIncertaine("« sans site » se constate, il ne se suppose pas")
    cx.execute("UPDATE entreprises SET identite=?, identite_source=?,"
               " identite_le=?, identite_preuve=? WHERE cle=?",
               (Etat.SANS_SITE.value, source, _maintenant(), preuve, cle))
    return lire(cx, cle)


def trancher(cx, cle, nom_candidat, *, source, preuve) -> Identite:
    """AMBIGUË → CONFIRMÉE, sur une information qui DISTINGUE réellement.

    Le candidat doit être l'un de ceux déjà conservés : on ne confirme pas une
    entité dont personne n'a jamais parlé. Les autres candidats ne sont pas
    supprimés — ils restent consultables, comme la trace de ce qui a été écarté.
    """
    candidats = candidats_de(cx, cle)
    choisi = next((c for c in candidats if c.nom == nom_candidat), None)
    if choisi is None:
        raise IdentiteIncertaine(
            f"« {nom_candidat} » ne figure pas parmi les candidats conservés "
            f"({', '.join(c.nom for c in candidats) or 'aucun'})")
    return confirmer(cx, cle, source=source,
                     preuve=f"{preuve} — retenu parmi {len(candidats)} candidats",
                     bce=choisi.bce, domaine=choisi.domaine)


# ══════════════════════════════════════ titulaires d'un marché
def enregistrer_titulaires(cx, avis_id, titulaire, registre=None) -> list[str]:
    """Un marché, un ou plusieurs titulaires — chacun garde sa ligne.

    `titulaire` est pris TEL QUE LA SOURCE LE DONNE : une chaîne pour un
    titulaire unique, une liste pour un groupement. Aucune chaîne n'est
    découpée automatiquement : deviner des membres dans un texte libre
    fabriquerait des entreprises qui n'existent pas.

    Si un registre d'entreprises est fourni, chaque membre y entre séparément
    et reçoit sa PROPRE identité. Un groupement dont un membre est CONFIRMÉ et
    deux INCONNUS est une information juste ; « le groupement est confirmé »
    serait une information fausse.
    """
    noms = ([t for t in titulaire if t] if isinstance(titulaire, (list, tuple))
            else ([titulaire] if titulaire else []))
    inscrits = []
    for rang, nom in enumerate(noms):
        nom = str(nom).strip()
        if not nom:
            continue
        cle = None
        if registre is not None:
            from .entreprises import Motif
            e = registre.decouvrir(nom, motif=Motif.TITULAIRE, origine="attribution")
            cle = e.cle
        cx.execute("INSERT OR IGNORE INTO titulaires(avis_id, rang, nom, entreprise)"
                   " VALUES(?,?,?,?)", (avis_id, rang, nom, cle))
        inscrits.append(nom)
    return inscrits


def titulaires_de(cx, avis_id) -> list[dict]:
    return [dict(l) for l in cx.execute(
        "SELECT rang, nom, entreprise FROM titulaires WHERE avis_id=?"
        " ORDER BY rang, id", (avis_id,)).fetchall()]


def groupement(cx, avis_id) -> str:
    """L'état d'identification d'un marché à plusieurs titulaires, sans
    arrondir : « 1 membre CONFIRMÉ, 2 INCONNUS » et non « identifié »."""
    membres = titulaires_de(cx, avis_id)
    if not membres:
        return "aucun titulaire enregistré"
    compte: dict[str, int] = {}
    for m in membres:
        etat = lire(cx, m["entreprise"]).etat if m["entreprise"] else Etat.INCONNUE
        compte[etat.value] = compte.get(etat.value, 0) + 1
    detail = " · ".join(f"{n} membre(s) {etat}" for etat, n in compte.items())
    return f"{len(membres)} titulaire(s) — {detail}"


def rapport(cx) -> str:
    L = ["IDENTITÉ DES ENTREPRISES", "=" * 92, ""]
    lignes = cx.execute("SELECT cle, nom, identite, domaine, bce FROM entreprises"
                        " ORDER BY nom").fetchall()
    if not lignes:
        return "\n".join(L + ["  aucune entreprise au registre."])
    compte: dict[Etat, int] = {e: 0 for e in Etat}
    for l in lignes:
        etat = lire_etat(l["identite"])
        compte[etat] += 1
        L.append(f"  {(l['nom'] or '')[:38]:<40} {etat.value:<11} "
                 f"{l['domaine'] or '—':<28} {l['bce'] or ''}")
    L.append("")
    L.append("  " + " · ".join(f"{e.value} {compte[e]}" for e in Etat if compte[e]))
    if compte[Etat.INCONNUE]:
        L.append(f"  {compte[Etat.INCONNUE]} identité(s) INCONNUE(S) : le radar")
        L.append("  n'en sait pas assez. Cela ne dit RIEN de leur existence.")
    return "\n".join(L)


def depuis_decouverte(cx, cle, url, *, source=None) -> Identite:
    """Un moteur a montré cette entreprise. Ce n'est pas une identification.

    On écrit d'où elle vient et sur quelle URL on l'a vue — la provenance est
    une information, et elle se conserve. Mais l'état reste INCONNUE : qu'un
    moteur ait affiché un nom ne prouve ni que l'entité existe sous ce nom, ni
    qu'elle est celle qu'on croit, ni qu'elle tient ce domaine.

    Une identité déjà établie n'est JAMAIS dégradée : si l'entreprise est
    CONFIRMÉE, AMBIGUË ou SANS SITE, une découverte de plus n'y touche pas.
    """
    actuelle = lire(cx, cle)
    if actuelle.etat is not Etat.INCONNUE:
        return actuelle
    cx.execute("UPDATE entreprises SET identite=?, identite_source=?,"
               " identite_le=?, identite_preuve=? WHERE cle=?",
               (Etat.INCONNUE.value, source or DECOUVERTE, _maintenant(),
                f"vue à l'adresse {url} — aucune identification",
                cle))
    return lire(cx, cle)
