"""Le modèle commun. Toute source, quelle qu'elle soit, produit CECI.

C'est le contrat qui rend le noyau indépendant des sources : rien en aval ne
sait d'où vient une opportunité.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

A_VERIFIER = "A_VERIFIER"
NON_MESURE = "NON MESURÉ"


class Nature(Enum):
    """Un appel d'offres est certain ; un signal ne l'est pas. On veut les deux,
    clairement séparés."""
    OPPORTUNITE_DIRECTE = "OPPORTUNITE_DIRECTE"
    SIGNAL_COMMERCIAL = "SIGNAL_COMMERCIAL"


@dataclass
class Opportunite:
    """Une opportunité normalisée, avant analyse."""
    source: str
    ref_source: str
    intitule: str
    nature: Nature = Nature.OPPORTUNITE_DIRECTE

    texte: str = ""                       # objet + description, pour l'analyse sémantique
    type_avis: str | None = None
    acheteur: str | None = None
    contact: str | None = None
    secteur_acheteur: str | None = None    # public | prive

    echeance_brute: object = None
    publie_le: object = None
    montant: float | None = None
    devise: str = "EUR"
    duree_mois: int | None = None
    recurrent: bool | None = None

    pays_collecte: list[str] = field(default_factory=list)
    pays_livraison: list[str] = field(default_factory=list)
    lieu_texte: str | None = None

    cpv: list[str] = field(default_factory=list)
    exigences: dict = field(default_factory=dict)   # code -> valeur, depuis champs normés
    exigences_texte: list[str] = field(default_factory=list)  # lues en texte libre

    lien_dossier: str | None = None
    lien_depot: str | None = None
    plateforme: str | None = None

    # Renseigné pour un avis d'attribution — jamais notifié, gardé en mémoire.
    attribue: bool = False
    titulaire: str | None = None
    attribue_le: datetime | None = None

    brut: dict = field(default_factory=dict)
