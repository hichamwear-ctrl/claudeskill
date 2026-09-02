"""L'enchaînement : d'une réponse brute à une fiche d'action notifiée."""

from __future__ import annotations

import json
from dataclasses import dataclass

from . import actionnabilite, eligibilite, envoi, score as notation
from .base import enregistrer_reponse, maintenant
from .fiche import Fiche


@dataclass
class Bilan:
    lus: int = 0
    actionnables: int = 0
    notifies: int = 0
    ecartes: dict = None

    def __post_init__(self):
        if self.ecartes is None:
            self.ecartes = {}

    def ecarter(self, motif: str):
        self.ecartes[motif] = self.ecartes.get(motif, 0) + 1


def _libelle(e) -> str:
    """Formule lisible d'une exigence, avec sa valeur quand elle en porte une."""
    from .score import LIBELLES
    base = LIBELLES.get(e.code, e.code.replace("_", " "))
    if e.code == "surface_min_m2":
        return f"{base} d'au moins {e.valeur} m²"
    if e.code == "vehicules_min":
        return f"flotte d'au moins {e.valeur} véhicules"
    if e.code == "reference_segment":
        return f"référence en « {e.valeur} »"
    return base


def _exigences(champs: dict) -> list[eligibilite.Exigence]:
    """Traduit les exigences publiées en exigences comparables au profil.

    `structuree=True` uniquement quand la valeur vient d'un champ normé. Une
    exigence devinée dans un texte libre ne peut produire qu'une réserve.
    """
    sortie = []
    for code, cle in (("afsca_requis", "exige_afsca"),
                      ("licence_transport_requise", "exige_licence"),
                      ("froid_requis", "exige_froid"),
                      ("tri_colis_requis", "exige_tri")):
        if champs.get(cle):
            sortie.append(eligibilite.Exigence(code, True, structuree=True))
    if champs.get("surface_min_m2"):
        sortie.append(eligibilite.Exigence("surface_min_m2", champs["surface_min_m2"],
                                           structuree=True))
    if champs.get("vehicules_min"):
        sortie.append(eligibilite.Exigence("vehicules_min", champs["vehicules_min"],
                                           structuree=True))
    if champs.get("reference_exigee"):
        sortie.append(eligibilite.Exigence("reference_segment", champs["reference_exigee"],
                                           structuree=False))
    return sortie


def traiter(cx, source: str, charges: list[dict], corr, profil: dict,
            maintenant_dt=None) -> Bilan:
    """Traite un lot de réponses brutes. Ne notifie QUE l'actionnable."""
    bilan = Bilan()

    for charge in charges:
        bilan.lus += 1
        champs = corr.extraire(charge)
        ref = str(champs.get("identifiant") or charge.get("id") or f"sans-ref-{bilan.lus}")
        avis_id = enregistrer_reponse(cx, source, ref, charge)

        verdict = actionnabilite.evaluer(
            type_avis=champs.get("type_avis"),
            echeance=champs.get("echeance"),
            maintenant=maintenant_dt)

        commun = dict(statut_action=verdict.statut.value,
                      actionnable=int(verdict.actionnable),
                      echeance=verdict.echeance.isoformat() if verdict.echeance else None,
                      montant=champs.get("montant"),
                      acheteur=champs.get("acheteur"),
                      intitule=champs.get("intitule"),
                      motif=verdict.motif)

        if not verdict.actionnable:
            # Stocké — il alimente le calendrier et la référence de prix —
            # mais il ne remonte jamais dans les opportunités à traiter.
            _ecrire(cx, avis_id, **commun, statut_elig=None, peut_deposer=0,
                    score=0, fiche=None)
            bilan.ecarter(verdict.statut.value)
            continue

        bilan.actionnables += 1
        exigences = _exigences(champs)
        elig = eligibilite.evaluer(exigences, profil)

        if not elig.peut_deposer:
            _ecrire(cx, avis_id, **commun, statut_elig=elig.statut.value, peut_deposer=0,
                    score=0, fiche=json.dumps(elig.blocages, ensure_ascii=False))
            bilan.ecarter("non_eligible")
            continue

        pts, explications = notation.calculer(
            exigences, elig, jours_restants=verdict.jours_restants,
            montant=champs.get("montant"))

        f = Fiche(
            reference=ref, intitule=champs.get("intitule") or "(sans intitulé)",
            acheteur=champs.get("acheteur"), contact=champs.get("contact_email"),
            objet=champs.get("objet"), montant=champs.get("montant"),
            devise=champs.get("devise") or "EUR",
            echeance_texte=verdict.motif, jours_restants=verdict.jours_restants,
            plateforme=champs.get("plateforme"), lien_depot=champs.get("plateforme"),
            lien_documents=champs.get("lien_documents"),
            conditions=[e.texte or _libelle(e) for e in exigences],
            atouts=elig.atouts, reserves=elig.reserves,
            signalements=verdict.signalements + explications,
            score=pts, source=source)

        _ecrire(cx, avis_id, **commun, statut_elig=elig.statut.value, peut_deposer=1,
                score=pts, fiche=f.en_texte())

        if envoi.mettre_en_file(cx, source, ref, f.en_texte()):
            bilan.notifies += 1

    cx.commit()
    return bilan


def _ecrire(cx, avis_id, **champs):
    champs["calcule_le"] = maintenant()
    colonnes = ", ".join(champs)
    trous = ", ".join("?" * len(champs))
    maj = ", ".join(f"{c}=excluded.{c}" for c in champs)
    cx.execute(
        f"INSERT INTO opportunites(avis_id, {colonnes}) VALUES(?, {trous}) "
        f"ON CONFLICT(avis_id) DO UPDATE SET {maj}",
        (avis_id, *champs.values()))
