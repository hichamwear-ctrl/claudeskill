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
    # LE CORPS RÉEL, sans l'intitulé recopié dedans.
    #
    # `texte` agrège titre + objet + lieu + conditions : c'est ce qu'il faut
    # pour reconnaître le métier, et il doit le rester. Mais la lecture de
    # l'ÉTAT a besoin de savoir ce que la source a écrit EN PLUS du titre —
    # sinon « intitulé : attribution » et « description : attribution » se
    # présentent comme deux observations indépendantes alors que c'est la
    # même, vue deux fois.
    corps: str = ""
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
    # LE CORPS RÉEL, sans l'intitulé recopié dedans.
    #
    # `texte` agrège titre + objet + lieu + conditions : c'est ce qu'il faut
    # pour reconnaître le métier, et il doit le rester. Mais la lecture de
    # l'ÉTAT a besoin de savoir ce que la source a écrit EN PLUS du titre —
    # sinon « intitulé : attribution » et « description : attribution » se
    # présentent comme deux observations indépendantes alors que c'est la
    # même, vue deux fois.
    corps: str = ""
    # LE MÊME TEXTE, MAIS QUI SAIT D'OÙ IL VIENT : [(texte, origine)].
    #
    # Une source capable de dire « ceci a été lu dans le pied de page » le
    # déclare ici. Les exclusions — et elles seules — s'y lisent : un mot lu
    # dans un menu décrit le site, pas le besoin. Vide pour toute source qui
    # ne sait pas le dire : l'origine est alors réputée caractériser.
    segments: list = field(default_factory=list)
    # `champ -> chemin de la source qui a répondu`. Sans cela, « objet » lu
    # dans une <meta description> et « objet » lu dans le corps du document
    # se présentent comme la même chose.
    champs_origine: dict = field(default_factory=dict)
    # LE CORPS, TEL QUE LA SOURCE L'A DÉCOUPÉ : [(texte, zone), …].
    #
    # Deux fragments d'un même texte libre ne se combinent que dans une même
    # unité de discours (voir radar/portee.py). Les blocs sont la meilleure
    # unité disponible ; sans eux on retombe sur la phrase, puis sur la
    # fenêtre. Vide pour toute source qui ne sait pas découper.
    blocs: list = field(default_factory=list)
    # QUELS CHAMPS ont composé `corps` et `texte`, et dans quel ordre.
    #
    # `corps` agrège `objet`, `contenu` et `conditions` en une chaîne. Sans
    # cette liste, la portée voit une seule provenance là où il y en a trois,
    # et deux champs réels ne peuvent plus se corroborer. Aucune valeur n'est
    # dupliquée : ce sont les mêmes morceaux, simplement encore nommés.
    corps_champs: list = field(default_factory=list)   # [(nom, valeur)]
    texte_champs: list = field(default_factory=list)
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


# ═══════════════════════ QUELLES PROVENANCES DÉCRIVENT LE MÊME OBJET ═══════
#
# `portee.py` sait OÙ une preuve a été observée. Il ne sait pas — et ne doit
# pas savoir — si deux provenances parlent de la même chose. C'est une
# question de MODÈLE, et elle se tranche ici, explicitement, paire par paire.
#
# La règle qu'on remplace était : « champ différent ⇒ même référent ». Elle
# est fausse. Trois contre-exemples mesurés :
#
#   · le titre d'un LOT et le corps de son MARCHÉ cohabitent dans le même
#     enregistrement et décrivent deux objets différents ;
#   · une <meta description> décrit la PAGE, pas le besoin qu'elle contient ;
#   · deux rubriques d'un même portail sont deux objets, pas un seul.
#
# Une paire absente de cette table ne se corrobore pas. L'ajout d'une paire
# est une décision de produit : elle s'écrit ici, elle se relit, elle se teste.

INTITULE = "intitulé"
CORPS = "corps du document"
CONDITIONS = "conditions"
TEXTE_DU_STATUT = "texte du statut"
DESCRIPTION = "description"          # métadonnée : décrit le document, pas le besoin
# Les champs que l'adaptateur agrège dans `corps`. Ils décrivent tous le
# besoin porté par CET enregistrement — c'est pourquoi ils se corroborent.
OBJET = "objet"
CONTENU = "contenu"

CORROBORATIONS = frozenset({
    # Le titre d'un enregistrement et son corps décrivent le même besoin.
    frozenset({INTITULE, CORPS}),
    # Les conditions sont celles du besoin que le titre nomme et que le
    # corps décrit.
    frozenset({INTITULE, CONDITIONS}),
    frozenset({CORPS, CONDITIONS}),
    # La phrase qui entoure le champ de statut porte sur CETTE procédure.
    frozenset({INTITULE, TEXTE_DU_STATUT}),
    frozenset({CORPS, TEXTE_DU_STATUT}),
    # Les trois champs agrégés dans `corps` décrivent le même besoin.
    frozenset({OBJET, CONTENU}),
    frozenset({OBJET, CONDITIONS}),
    frozenset({CONTENU, CONDITIONS}),
    frozenset({INTITULE, OBJET}),
    frozenset({INTITULE, CONTENU}),
    frozenset({OBJET, TEXTE_DU_STATUT}),
    frozenset({CONTENU, TEXTE_DU_STATUT}),
})


def corroborables(champ_a: str, champ_b: str) -> bool:
    """Ces deux provenances décrivent-elles le même objet ?

    Le même champ avec lui-même n'est pas une corroboration entre
    provenances : c'est du texte libre, et l'unité de discours décide.
    """
    if not champ_a or not champ_b or champ_a == champ_b:
        return False
    return frozenset({champ_a, champ_b}) in CORROBORATIONS
