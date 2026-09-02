"""🟢 DIRECT · 🟡 SOUS-TRAITANCE · 🔵 PROSPECT · 🔴 REJET

La règle qui compte : un marché hors gabarit par sa TAILLE n'est pas un rejet,
c'est une opportunité de sous-traitance. Un marché hors gabarit par son OBJET,
sa ZONE ou une QUALIFICATION manquante en est un.

Autrement dit : ce que je ne peux pas porter seul, un autre le portera — et il
lui faudra des bras. Ce que je ne sais pas faire, personne ne me le sous-traitera.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .role import Role


class Type(Enum):
    DIRECT = "DIRECT"
    SOUS_TRAITANCE = "SOUS_TRAITANCE"
    PROSPECT = "PROSPECT"
    REJET = "REJET"

    @property
    def emoji(self) -> str:
        return {"DIRECT": "🟢", "SOUS_TRAITANCE": "🟡",
                "PROSPECT": "🔵", "REJET": "🔴"}[self.value]

    @property
    def notifiable(self) -> bool:
        return self is not Type.REJET


# Motifs de blocage qui n'interdisent PAS la sous-traitance : ils disent que le
# marché est trop gros pour être porté seul, pas qu'on ne sait pas le faire.
BLOCAGES_DE_TAILLE = ("véhicules exigés", "chiffre d'affaires", "m² exigés")


@dataclass
class Classement:
    type: Type
    motif: str
    action: str = ""
    raisons_rejet: list[str] = field(default_factory=list)
    sous_traitance_possible: bool = False


def _est_blocage_de_taille(message: str) -> bool:
    return any(marque in message for marque in BLOCAGES_DE_TAILLE)


def classer(*, role, activite_ok, activite_motif, zone_ok, zone_motif,
            deadline_ouverte, deadline_motif, attribue, informatif,
            bilan_capacite, est_signal=False) -> Classement:
    """Décide de la catégorie. L'ordre des tests est celui du raisonnement."""

    # ── 1. Ce qui disqualifie l'objet même, quelle que soit la suite ──
    if role is Role.FOURNISSEUR:
        return Classement(Type.REJET, "marché de fourniture — l'acheteur veut un bien",
                          raisons_rejet=["l'entreprise vend une prestation, pas un produit"])
    if not activite_ok:
        return Classement(Type.REJET, activite_motif or "activité hors métier",
                          raisons_rejet=[activite_motif or "activité hors métier"])
    if not zone_ok:
        return Classement(Type.REJET, zone_motif or "zone incompatible",
                          raisons_rejet=[zone_motif or "zone incompatible"])

    # ── 2. Un signal n'est jamais un marché : c'est un prospect ──
    if est_signal:
        return Classement(Type.PROSPECT, "signal d'un besoin logistique",
                          action="contacter l'entreprise et identifier le responsable logistique")

    # ── 3. Marché attribué : plus de dépôt possible, mais le gagnant recrutera ──
    if attribue:
        return Classement(
            Type.SOUS_TRAITANCE, "marché déjà attribué — le titulaire devra exécuter",
            action="contacter le titulaire comme transporteur sous-traitant",
            sous_traitance_possible=True)

    if informatif:
        return Classement(Type.REJET, "avis informatif — aucun dépôt attendu",
                          raisons_rejet=["avis purement informatif"])
    if not deadline_ouverte:
        return Classement(Type.REJET, deadline_motif or "date limite dépassée",
                          raisons_rejet=[deadline_motif or "date limite dépassée"])

    # ── 4. Blocages de capacité : taille ou nature ? ──
    if bilan_capacite.bloquants:
        de_taille = [b for b in bilan_capacite.bloquants if _est_blocage_de_taille(b)]
        autres = [b for b in bilan_capacite.bloquants if not _est_blocage_de_taille(b)]
        if autres:
            # Qualification ou infrastructure manquante : personne ne sous-traite ça.
            return Classement(Type.REJET, autres[0], raisons_rejet=autres)
        return Classement(
            Type.SOUS_TRAITANCE,
            f"trop grand pour être porté seul — {de_taille[0]}",
            action="se positionner comme sous-traitant auprès des candidats probables",
            sous_traitance_possible=True)

    # ── 5. Reste le cas normal ──
    motif = "postulable" if role is Role.PRESTATAIRE else "postulable — rôle à confirmer"
    return Classement(Type.DIRECT, motif, action="déposer une offre")
