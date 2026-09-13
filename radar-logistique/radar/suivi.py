"""LE SUIVI COMMERCIAL — où en est la RELATION, pas où en est la procédure.

Une opportunité détectée et jamais rappelée est une opportunité perdue. Le
radar sait dire « voici une affaire » ; il doit aussi dire « qu'est-ce qu'on
en a fait, et qu'est-ce qui vient ensuite ».

────────────────────────────────────────────────────────────────────────────
TROIS DIMENSIONS, JAMAIS MÉLANGÉES
────────────────────────────────────────────────────────────────────────────

    ÉTAT DE PROCÉDURE    POSTULABLE · ATTRIBUÉ · FERMÉ · HORS PROCÉDURE …
                         → ce que fait LE MARCHÉ. Lu dans la source.

    ACTION MÉTIER        POSTULER · CONTACTER L'ENTREPRISE · SURVEILLER …
                         → ce qu'IL FAUT FAIRE. Calculé par le moteur.

    STATUT COMMERCIAL    NOUVELLE · CONTACTÉE · RELANCE · GAGNÉE …
                         → où en est NOTRE RELATION. Posé par un humain.

Une opportunité privée peut être HORS PROCÉDURE, d'action CONTACTER, et de
statut NOUVELLE : les trois lignes sont vraies en même temps et ne se
déduisent pas l'une de l'autre. Colis Privé est exactement ce cas.

────────────────────────────────────────────────────────────────────────────
CE QUI EXISTAIT DÉJÀ, ET QU'ON NE REFAIT PAS
────────────────────────────────────────────────────────────────────────────

`opportunites.etat` et `opportunites.etat_maj` existaient dans le schéma,
avec le défaut `'non_vu'`, et n'étaient lus ni écrits nulle part. C'était le
créneau du statut commercial, réservé et jamais branché. On le branche ; on
n'ajoute aucune colonne de statut.

Ces colonnes sont absentes de `chaine.RECALCULEES` : une recollecte ne les
écrase donc pas. Ce n'est pas un effet de bord heureux, c'est la garantie —
elle est vérifiée par un test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .base import maintenant

NON_VU = "non_vu"                 # le défaut du schéma : jamais encore regardée
NON_PLANIFIEE = "NON PLANIFIÉE"


class Statut(Enum):
    """Où en est la relation commerciale. Un humain le pose, jamais le moteur."""
    NOUVELLE = "NOUVELLE"
    CONTACT_A_FAIRE = "CONTACT À FAIRE"
    CONTACTEE = "CONTACTÉE"
    EN_ATTENTE = "EN ATTENTE"
    RELANCE = "RELANCE"
    GAGNEE = "GAGNÉE"
    PERDUE = "PERDUE"
    ABANDONNEE = "ABANDONNÉE"

    @property
    def close(self) -> bool:
        """Une affaire close ne demande plus d'action commerciale."""
        return self in (Statut.GAGNEE, Statut.PERDUE, Statut.ABANDONNEE)

    @property
    def contact_effectue(self) -> bool:
        """Déduit, jamais stocké : deux booléens finissent par se contredire."""
        return self in (Statut.CONTACTEE, Statut.EN_ATTENTE, Statut.RELANCE,
                        Statut.GAGNEE, Statut.PERDUE)


class StatutInconnu(ValueError):
    """Un statut hors vocabulaire. On refuse, on ne devine pas."""


class OpportuniteIntrouvable(ValueError):
    """La référence donnée ne désigne aucune opportunité en base."""


class DateInvalide(ValueError):
    """Une date qui n'est pas une date. On refuse, on n'invente pas."""


_JOUR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def lire_statut(valeur) -> Statut:
    """Le seul point d'entrée du vocabulaire. Tolère la casse et les accents
    manquants au clavier, refuse tout le reste."""
    if isinstance(valeur, Statut):
        return valeur
    brut = str(valeur or "").strip()
    if not brut:
        raise StatutInconnu("statut vide")
    for s in Statut:
        if brut.upper() == s.value.upper():
            return s
    sans_accent = brut.upper().replace("É", "E").replace("È", "E").replace("À", "A")
    for s in Statut:
        if sans_accent == s.value.upper().replace("É", "E").replace("È", "E").replace("À", "A"):
            return s
    connus = " · ".join(s.value for s in Statut)
    raise StatutInconnu(f"statut inconnu : « {brut} ». Vocabulaire : {connus}")


def lire_jour(valeur, quoi="date") -> str | None:
    """Une date au format AAAA-MM-JJ, ou rien. Jamais une date calculée."""
    if valeur in (None, "", NON_PLANIFIEE):
        return None
    brut = str(valeur).strip()
    if not _JOUR.match(brut):
        raise DateInvalide(f"{quoi} : « {brut} » n'est pas une date AAAA-MM-JJ")
    annee, mois, jour = (int(x) for x in brut.split("-"))
    if not (1 <= mois <= 12 and 1 <= jour <= 31 and 2000 <= annee <= 2100):
        raise DateInvalide(f"{quoi} : « {brut} » n'est pas une date possible")
    return brut


@dataclass
class Suivi:
    """L'état commercial d'une opportunité, tel qu'il est en base."""
    avis_id: int
    statut: Statut | None = None          # None = jamais regardée (« non_vu »)
    statut_maj: str | None = None
    prochaine_action_le: str | None = None
    dernier_contact_le: str | None = None
    motif: str | None = None

    @property
    def jamais_regardee(self) -> bool:
        return self.statut is None

    def en_lignes(self) -> list[str]:
        """Les lignes de fiche. Affiche le suivi même vide : une opportunité
        sans statut est justement celle qu'on risque d'oublier."""
        statut = self.statut.value if self.statut else "NOUVELLE — jamais regardée"
        L = [f"SUIVI         {statut}"]
        if self.statut_maj:
            L.append(f"              depuis le {self.statut_maj[:10]}")
        L.append(f"PROCHAINE     {self.prochaine_action_le or NON_PLANIFIEE}")
        if self.dernier_contact_le:
            L.append(f"DERNIER CONTACT {self.dernier_contact_le}")
        if self.motif:
            L.append(f"MOTIF         {self.motif}")
        return L


def lire(cx, avis_id: int) -> Suivi:
    ligne = cx.execute(
        "SELECT etat, etat_maj, prochaine_action_le, dernier_contact_le,"
        " motif_commercial FROM opportunites WHERE avis_id=?", (avis_id,)).fetchone()
    if ligne is None:
        raise OpportuniteIntrouvable(f"aucune opportunité pour l'avis {avis_id}")
    brut = ligne["etat"]
    statut = None if brut in (None, "", NON_VU) else lire_statut(brut)
    return Suivi(avis_id=avis_id, statut=statut, statut_maj=ligne["etat_maj"],
                 prochaine_action_le=ligne["prochaine_action_le"],
                 dernier_contact_le=ligne["dernier_contact_le"],
                 motif=ligne["motif_commercial"])


def resoudre(cx, reference: str) -> int:
    """Trouve l'avis par sa référence de source. Une référence ambiguë est
    refusée : on ne choisit pas à la place du commercial."""
    lignes = cx.execute(
        "SELECT a.id, a.ref_source FROM avis a JOIN opportunites o ON o.avis_id=a.id"
        " WHERE a.ref_source = ?", (reference,)).fetchall()
    if not lignes:
        lignes = cx.execute(
            "SELECT a.id, a.ref_source FROM avis a JOIN opportunites o ON o.avis_id=a.id"
            " WHERE a.ref_source LIKE ?", (f"%{reference}%",)).fetchall()
    if not lignes:
        raise OpportuniteIntrouvable(f"aucune opportunité pour « {reference} »")
    if len(lignes) > 1:
        refs = "\n  · ".join(l["ref_source"] for l in lignes[:6])
        raise OpportuniteIntrouvable(
            f"« {reference} » désigne {len(lignes)} opportunités :\n  · {refs}")
    return lignes[0]["id"]


def marquer(cx, avis_id: int, statut, *, motif: str | None = None,
            prochaine_action_le=None, dernier_contact_le=None,
            par: str = "exploitant") -> Suivi:
    """Pose le statut commercial et inscrit l'événement.

    Un statut identique au précédent n'écrit AUCUN événement : l'historique
    commercial doit raconter ce qui s'est passé, pas combien de fois on a
    relu la page.
    """
    avant = lire(cx, avis_id)
    nouveau = lire_statut(statut)
    prochaine = lire_jour(prochaine_action_le, "prochaine action")
    contact = lire_jour(dernier_contact_le, "dernier contact")
    quand = maintenant()

    change = (avant.statut != nouveau)
    cx.execute(
        "UPDATE opportunites SET etat=?, etat_maj=?,"
        " prochaine_action_le=COALESCE(?, prochaine_action_le),"
        " dernier_contact_le=COALESCE(?, dernier_contact_le),"
        " motif_commercial=COALESCE(?, motif_commercial)"
        " WHERE avis_id=?",
        (nouveau.value, quand if change else (avant.statut_maj or quand),
         prochaine, contact, motif, avis_id))
    if change:
        cx.execute(
            "INSERT INTO suivi_commercial(avis_id, ancien, nouveau, motif, fait_le, par)"
            " VALUES(?,?,?,?,?,?)",
            (avis_id, avant.statut.value if avant.statut else None,
             nouveau.value, motif, quand, par))
    return lire(cx, avis_id)


def historique(cx, avis_id: int) -> list:
    return cx.execute(
        "SELECT ancien, nouveau, motif, fait_le, par FROM suivi_commercial"
        " WHERE avis_id=? ORDER BY id", (avis_id,)).fetchall()


def fil(cx, avis_id: int) -> list[str]:
    """Le parcours commercial, lisible : « 12/09 — NOUVELLE → CONTACTÉE »."""
    sortie = []
    for l in historique(cx, avis_id):
        depuis = l["ancien"] or "détectée"
        motif = f"  ({l['motif']})" if l["motif"] else ""
        sortie.append(f"{l['fait_le'][:10]} — {depuis} → {l['nouveau']}{motif}")
    return sortie
