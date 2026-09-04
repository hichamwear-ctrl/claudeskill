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
class Provenance:
    """D'où vient cette opportunité, et quand elle a été RÉELLEMENT consultée."""
    source: str
    url: str | None = None
    consulte_le: str | None = None
    requete: str | None = None


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
    # Un lot peut avoir son PROPRE état : marché attribué, lot 3 encore ouvert.
    statut_source: str | None = None
    type_information: str | None = None


@dataclass
class Opportunite:
    source: str
    ref_source: str
    intitule: str

    # Un marché sans lot déclaré en a un : lui-même (voir lots.py).
    lots: list[LotBrut] = field(default_factory=list)

    texte: str = ""
    type_avis: str | None = None
    # ── A · ce que le PORTAIL dit être cet objet, tel quel ────────────────
    type_information: str | None = None     # « Marchés en cours », « Résultats »…
    statut_source: str | None = None        # la valeur du champ de statut
    texte_statut: str | None = None         # la phrase qui entoure le statut
    evenements: list = field(default_factory=list)   # [{type, date}]
    documents: list = field(default_factory=list)    # noms des pièces jointes
    actions_possibles: list = field(default_factory=list)  # boutons de la page
    est_signal: bool = False
    signal_code: str | None = None       # recrutement_massif, ouverture_site, ...

    acheteur: str | None = None
    contact: str | None = None
    secteur_acheteur: str | None = None   # public | privé

    echeance_brute: object = None
    publie_le: object = None
    montant: float | None = None
    # « total » (un contrat réparti sur sa durée) ou « par_periode » (un prix
    # qui revient à chaque tournée). DÉCLARÉ par la source, jamais deviné.
    montant_unite: str | None = None
    devise: str = "EUR"
    duree_mois: int | None = None
    cadence: str | None = None            # quotidienne, hebdomadaire, ponctuelle...
    date_demarrage: object = None

    # Effort réel — ce qui distingue un bon contrat d'un gros contrat.
    km_annuels: float | None = None
    distance_depot_km: float | None = None
    travail_nuit: bool | None = None
    travail_weekend: bool | None = None
    vehicules_requis: int | None = None
    chauffeurs_requis: int | None = None

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

    # Lien vers le marché parent quand l'opportunité est un LOT isolé.
    marche_ref: str | None = None
    lot_numero: str | None = None

    # Doublon POSSIBLE : relié, jamais fusionné.
    doublon_possible: str | None = None
    doublon_motif: str | None = None

    # Provenances : un même besoin peut venir de Google ET du BDA.
    provenances: list = field(default_factory=list)   # [{source, url, consulte_le, requete}]

    # Champs publiés mais ILLISIBLES : « 120 000 » là où un nombre est attendu,
    # « douze » pour une durée. La valeur n'est pas inventée, elle n'est pas
    # mise à zéro non plus — elle est signalée, avec ce que la source a écrit.
    champs_illisibles: dict = field(default_factory=dict)   # champ -> valeur brute

    brut: dict = field(default_factory=dict)
