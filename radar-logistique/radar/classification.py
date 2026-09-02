"""OPPORTUNITE_DIRECTE contre SIGNAL_COMMERCIAL.

Un appel d'offres est un fait : il y a un dossier, une date, une plateforme.
Un signal est une inférence : un recrutement massif de chauffeurs, un entrepôt
qui ouvre, un prestataire qui change. On veut les deux — jamais mélangés.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .modele import Nature

# Un signal n'a ni dossier ni date de dépôt : il donne une PISTE et une fenêtre.
SIGNAUX = {
    "recrutement_massif": ("Recrutement massif de chauffeurs",
                           "besoin logistique en tension — proposer une équipe et un dépôt"),
    "ouverture_site": ("Ouverture d'un entrepôt ou d'une agence",
                       "besoin de transport et de distribution dans les mois qui suivent"),
    "changement_prestataire": ("Changement de prestataire logistique",
                               "fenêtre de sous-traitance ouverte"),
    "contrat_signe": ("Gros contrat commercial signé",
                      "le titulaire va devoir exécuter — besoin de sous-traitants"),
    "cessation_concurrent": ("Cessation d'un transporteur",
                             "zone libérée, donneur d'ordre à réaffecter sous quelques jours"),
    "attribution_gagnee": ("Marché remporté par un tiers",
                           "le titulaire cherchera des sous-traitants avant le démarrage"),
}


@dataclass
class Classification:
    nature: Nature
    libelle: str
    pourquoi: str = ""
    fenetre: str = ""
    a_verifier: list[str] = field(default_factory=list)


def classer(opp) -> Classification:
    if opp.nature is Nature.SIGNAL_COMMERCIAL:
        code = (opp.type_avis or "").strip().lower()
        libelle, pourquoi = SIGNAUX.get(code, ("Signal commercial",
                                               "indice d'un besoin logistique à venir"))
        return Classification(
            Nature.SIGNAL_COMMERCIAL, libelle, pourquoi,
            fenetre="à traiter par prise de contact directe, pas par dépôt d'offre",
            a_verifier=["signal déduit — aucun dossier officiel à déposer",
                        "le besoin réel reste à confirmer auprès de l'entreprise"])
    return Classification(Nature.OPPORTUNITE_DIRECTE, "Appel d'offres",
                          "dossier officiel avec date limite et plateforme de dépôt")
