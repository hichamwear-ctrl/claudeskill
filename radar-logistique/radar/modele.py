"""Le modèle commun. Toute source produit CECI, quelle que soit sa nature.

C'est le contrat qui rend le noyau indépendant des sources : rien en aval ne
sait d'où vient une opportunité.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

A_VERIFIER = "A_VERIFIER"
NON_MESURE = "NON MESURÉ"


@dataclass
class LotBrut:
    """Un lot tel que la source le publie."""
    numero: str = ""
    intitule: str = ""
    texte: str = ""
    cpv: list[str] = field(default_factory=list)
    montant: float | None = None
    duree_mois: int | None = None
    exigences: dict = field(default_factory=dict)
    pays_collecte: list[str] = field(default_factory=list)
    pays_livraison: list[str] = field(default_factory=list)


@dataclass
class Opportunite:
    source: str
    ref_source: str
    intitule: str

    # Un marché sans lot déclaré en a un : lui-même (voir lots.py).
    lots: list[LotBrut] = field(default_factory=list)

    texte: str = ""
    type_avis: str | None = None
    est_signal: bool = False
    signal_code: str | None = None       # recrutement_massif, ouverture_site, ...

    acheteur: str | None = None
    contact: str | None = None
    secteur_acheteur: str | None = None   # public | privé

    echeance_brute: object = None
    publie_le: object = None
    montant: float | None = None
    devise: str = "EUR"
    duree_mois: int | None = None
    cadence: str | None = None            # quotidienne, hebdomadaire, ponctuelle...

    pays_collecte: list[str] = field(default_factory=list)
    pays_livraison: list[str] = field(default_factory=list)
    lieu_texte: str | None = None

    cpv: list[str] = field(default_factory=list)
    exigences: dict = field(default_factory=dict)
    exigences_texte: list[str] = field(default_factory=list)

    lien_dossier: str | None = None
    lien_depot: str | None = None
    plateforme: str | None = None

    attribue: bool = False
    titulaire: str | None = None
    attribue_le: datetime | None = None

    brut: dict = field(default_factory=dict)
