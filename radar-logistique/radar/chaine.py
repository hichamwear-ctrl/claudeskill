"""La chaîne complète, dans l'ordre spécifié.

  SOURCES -> COLLECTE -> NORMALISATION -> DÉDUPLICATION -> STATUT
          -> ÉLIGIBILITÉ -> MATCH PROFIL -> SCORING -> CLASSIFICATION -> NOTIFICATION

Aucun étage après la collecte ne sait de quelle source vient l'opportunité.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import classification, deduplication, eligibilite, envoi, memoire, statut as st
from .activite import Ontologie
from .base import enregistrer_reponse, maintenant
from .fiche import Fiche
from .geographie import Geographie
from .modele import Nature
from .score import Bareme


@dataclass
class Bilan:
    lus: int = 0
    doublons: int = 0
    postulables: int = 0
    a_verifier: int = 0
    non_postulables: int = 0
    signaux: int = 0
    notifies: int = 0
    attributions_memorisees: int = 0
    motifs_rejet: dict = field(default_factory=dict)

    def rejeter(self, motif: str):
        self.motifs_rejet[motif] = self.motifs_rejet.get(motif, 0) + 1


class Moteur:
    """Assemble les étages à partir des fichiers de configuration."""

    def __init__(self, profil: dict, capacites: dict, geographie: dict, ponderations: dict):
        self.profil = profil
        self.exigences_connues = capacites.get("exigences", {})
        self.ontologie = Ontologie(capacites, profil["familles_actives"],
                                   profil.get("familles_exclues"))
        self.geo = Geographie(geographie)
        self.bareme = Bareme(ponderations)

    def _exigences(self, opp, correspondance) -> list[eligibilite.Exigence]:
        """Structurées d'abord, puis celles suggérées par la famille d'activité —
        ces dernières ne sont jamais présumées satisfaites."""
        sortie = [eligibilite.Exigence(code, valeur, structuree=True)
                  for code, valeur in (opp.exigences or {}).items() if valeur not in (None, False)]
        vus = {e.code for e in sortie}
        for texte in opp.exigences_texte or []:
            sortie.append(eligibilite.Exigence(texte, True, texte=texte, structuree=False))
        for code in correspondance.exigences_suggerees:
            if code not in vus:
                sortie.append(eligibilite.Exigence(code, True, structuree=False,
                                                   obligatoire=False))
        return sortie

    def analyser(self, opp, maintenant_dt=None):
        """Un seul passage d'analyse. Renvoie (verdict, elig, score, corr, zone, classe)."""
        corr = self.ontologie.analyser(f"{opp.intitule} {opp.texte}", opp.cpv)
        zone = self.geo.evaluer(opp.pays_collecte, opp.pays_livraison)
        exigences = self._exigences(opp, corr)
        elig = eligibilite.evaluer(exigences, self.profil, self.exigences_connues)

        raison_act = ""
        if corr.exclusions:
            raison_act = f"activité exclue ({', '.join(corr.exclusions[:2])})"
        elif not corr.familles:
            raison_act = "aucune famille d'activité reconnue"

        verdict = st.evaluer(
            opp,
            zone_compatible=zone.compatible,
            zone_raison=zone.raisons[0] if zone.raisons else "",
            activite_compatible=corr.correspond,
            activite_raison=raison_act,
            eligibilite=elig,
            maintenant=maintenant_dt)

        note = self.bareme.calculer(correspondance=corr, zone=zone, eligibilite=elig,
                                    opp=opp, jours_restants=verdict.jours_restants)
        classe = classification.classer(opp)
        return verdict, elig, note, corr, zone, classe

    def fiche(self, opp, verdict, elig, note, corr, zone, classe) -> Fiche:
        pourquoi = list(elig.atouts)
        for famille in corr.familles:
            libelle = self.ontologie.cfg["familles"][famille]["libelle"]
            preuves = corr.preuves.get(famille) or []
            pourquoi.append(f"{libelle}" + (f" — repéré via « {preuves[0]} »" if preuves else ""))
        pourquoi += zone.raisons
        if classe.pourquoi:
            pourquoi.append(classe.pourquoi)

        return Fiche(
            statut_emoji=verdict.statut.emoji, statut=verdict.statut.value,
            titre=opp.intitule, nature=opp.nature, nature_libelle=classe.libelle,
            acheteur=opp.acheteur, secteur=opp.secteur_acheteur, contact=opp.contact,
            collecte=zone.collecte, livraison=zone.livraison, lieu_texte=opp.lieu_texte,
            echeance=(f"{verdict.echeance:%d/%m/%Y}" if verdict.echeance else "A_VERIFIER"),
            jours_restants=verdict.jours_restants,
            montant=opp.montant, devise=opp.devise, duree_mois=opp.duree_mois,
            pourquoi=pourquoi, a_verifier=verdict.a_verifier + classe.a_verifier,
            score=note.total, detail_score=note.detail(),
            lien=opp.lien_depot or opp.lien_dossier, plateforme=opp.plateforme,
            source=opp.source, reference=opp.ref_source)


def traiter(cx, moteur: Moteur, opportunites: list, maintenant_dt=None) -> Bilan:
    bilan = Bilan()
    vues: dict[str, object] = {}

    for opp in opportunites:
        bilan.lus += 1

        # --- déduplication, avant toute analyse ---
        emp = deduplication.empreinte(opp)
        if emp in vues:
            deduplication.fusionner(vues[emp], opp)
            bilan.doublons += 1
            continue
        deja = cx.execute("SELECT id FROM avis WHERE empreinte=? AND ref_source<>?",
                          (emp, opp.ref_source)).fetchone()
        vues[emp] = opp

        avis_id = enregistrer_reponse(cx, opp.source, opp.ref_source, opp.brut or {}, emp)
        if deja:
            bilan.doublons += 1

        verdict, elig, note, corr, zone, classe = moteur.analyser(opp, maintenant_dt)

        # --- un marché attribué : mémorisé, jamais notifié ---
        if opp.attribue or (opp.type_avis or "").lower() in st.TYPES_ATTRIBUTION:
            r = memoire.memoriser(opp)
            cx.execute(
                "INSERT OR REPLACE INTO attributions(avis_id, acheteur, titulaire, montant, "
                "duree_mois, prestation, conclu_le, renouvellement, fiabilite, commentaire) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (avis_id, r.acheteur, r.titulaire, r.montant, r.duree_mois, r.prestation,
                 r.conclu_le.isoformat() if r.conclu_le else None,
                 r.remise_en_concurrence.isoformat() if r.remise_en_concurrence else None,
                 r.fiabilite, r.commentaire))
            bilan.attributions_memorisees += 1

        f = moteur.fiche(opp, verdict, elig, note, corr, zone, classe)
        cx.execute(
            "INSERT INTO opportunites(avis_id, nature, statut, eligibilite, zone, familles, "
            "intitule, acheteur, montant, echeance, jours_restants, score, detail_score, motif, "
            "fiche, calcule_le) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(avis_id) DO UPDATE SET statut=excluded.statut, score=excluded.score, "
            "fiche=excluded.fiche, calcule_le=excluded.calcule_le, motif=excluded.motif",
            (avis_id, opp.nature.value, verdict.statut.value, elig.statut.value,
             zone.zone.value, ",".join(corr.familles), opp.intitule, opp.acheteur, opp.montant,
             verdict.echeance.isoformat() if verdict.echeance else None,
             verdict.jours_restants, note.total, json.dumps(note.detail(), ensure_ascii=False),
             verdict.motif, f.en_texte(), maintenant()))

        if verdict.statut is st.Statut.NON_POSTULABLE:
            bilan.non_postulables += 1
            bilan.rejeter(verdict.bloquants[0] if verdict.bloquants else verdict.motif)
            continue

        if verdict.statut is st.Statut.POSTULABLE:
            bilan.postulables += 1
        else:
            bilan.a_verifier += 1
        if opp.nature is Nature.SIGNAL_COMMERCIAL:
            bilan.signaux += 1

        if envoi.mettre_en_file(cx, opp.source, opp.ref_source, f.en_texte()):
            bilan.notifies += 1

    cx.commit()
    return bilan
