"""La chaîne complète.

  SOURCE → COLLECTE → NORMALISATION → MARCHÉ → LOTS → PRESTATIONS
         → GÉOGRAPHIE → EXIGENCES → CAPACITÉS → ÉLIGIBILITÉ
         → CLASSIFICATION → SCORE → DÉDUPLICATION → NOTIFICATION

Aucun étage après la collecte ne sait de quelle source vient l'opportunité.
L'analyse descend au niveau du LOT : un marché est retenu dès qu'un seul de
ses lots est compatible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import deduplication, envoi, memoire, questions, statut as st
from .activite import Ontologie
from .base import enregistrer_reponse, maintenant
from .capacite import Bilan, Capacites
from .classification import Type, classer
from .fiche import Fiche
from .geographie import Geographie
from .lots import lots_de
from .role import DetecteurDeRole, Role
from .score import Bareme


@dataclass
class Resultat:
    """Ce que l'analyse d'une opportunité produit."""
    classement: object
    score: object
    fiche: Fiche
    journal: questions.Journal
    role: Role
    zone: object
    bilan: Bilan
    correspondance: object
    verdict: object
    lots_retenus: list[str] = field(default_factory=list)


@dataclass
class BilanCycle:
    lus: int = 0
    doublons: int = 0
    direct: int = 0
    sous_traitance: int = 0
    prospect: int = 0
    rejet: int = 0
    notifies: int = 0
    attributions: int = 0
    motifs_rejet: dict = field(default_factory=dict)

    def rejeter(self, motif):
        self.motifs_rejet[motif] = self.motifs_rejet.get(motif, 0) + 1


class Moteur:
    def __init__(self, profil, capacites, geographie, ponderations, roles):
        self.profil = profil
        self.libelles = capacites.get("exigences", {})
        self.ontologie = Ontologie(capacites, profil["familles_actives"],
                                   profil.get("familles_exclues"))
        self.geo = Geographie(geographie)
        self.bareme = Bareme(ponderations)
        self.roles = DetecteurDeRole(roles)
        self.capacites = Capacites(profil, self.libelles)

    # ------------------------------------------------------ exigences --
    def _confronter(self, exigences: dict) -> Bilan:
        """Confronte chaque exigence aux trois niveaux de capacité."""
        b = Bilan()
        c = self.capacites
        for code, valeur in (exigences or {}).items():
            if valeur in (None, False, ""):
                continue
            if code == "vehicules_min":
                b.ajouter(c.vehicules(int(valeur)))
            elif code == "surface_min_m2":
                b.ajouter(c.surface(float(valeur)))
            elif code == "anciennete_min_annees":
                b.ajouter(c.anciennete(float(valeur)))
            elif code == "chiffre_affaires_min":
                b.ajouter(c.chiffre_affaires(float(valeur)))
            elif code == "references_min":
                b.ajouter(c.references(int(valeur)))
            else:
                b.ajouter(c.qualification(code))
        return b

    # -------------------------------------------------- analyse d'un lot --
    def _analyser_lot(self, lot):
        role = self.roles.analyser(f"{lot.intitule} {lot.texte}", lot.cpv)
        corr = self.ontologie.analyser(f"{lot.intitule} {lot.texte}", lot.cpv)
        zone = self.geo.evaluer(lot.pays_collecte, lot.pays_livraison)
        bilan = self._confronter(lot.exigences)
        return role, corr, zone, bilan

    # ------------------------------------------------------- analyse --
    def analyser(self, opp, maintenant_dt=None) -> Resultat:
        # Étage LOTS : on cherche le meilleur lot, pas le titre du marché.
        meilleur = None
        retenus = []
        for lot in lots_de(opp):
            role, corr, zone, bilan = self._analyser_lot(lot)
            compatible = (role.role is not Role.FOURNISSEUR and corr.correspond
                          and zone.compatible and not bilan.bloquants)
            rang = (compatible, role.role is Role.PRESTATAIRE, len(corr.familles))
            if compatible and lot.numero:
                retenus.append(lot.libelle)
            if meilleur is None or rang > meilleur[0]:
                meilleur = (rang, lot, role, corr, zone, bilan)

        _, lot, role, corr, zone, bilan = meilleur

        verdict = st.evaluer(opp, maintenant=maintenant_dt)
        activite_motif = ""
        if corr.exclusions:
            activite_motif = f"activité exclue ({', '.join(corr.exclusions[:2])})"
        elif not corr.familles:
            activite_motif = "aucune prestation reconnue dans mes familles d'activité"

        classement = classer(
            role=role.role,
            activite_ok=corr.correspond, activite_motif=activite_motif,
            zone_ok=zone.compatible, zone_motif=zone.raisons[0] if zone.raisons else "",
            deadline_ouverte=verdict.statut is not st.Statut.NON_POSTULABLE
                             or bool(opp.attribue),
            deadline_motif=verdict.motif,
            attribue=bool(opp.attribue) or (opp.type_avis or "").lower() in st.TYPES_ATTRIBUTION,
            informatif=(opp.type_avis or "").lower() in st.TYPES_INFORMATIFS,
            bilan_capacite=bilan,
            est_signal=opp.est_signal)

        score = self.bareme.calculer(
            correspondance=corr, zone=zone, bilan=bilan, opp=opp,
            type_opp=classement.type, cadence=opp.cadence,
            jours_restants=verdict.jours_restants)

        journal = questions.interroger(
            opp=opp, role=role.role, correspondance=corr, zone=zone, bilan=bilan,
            classement=classement, verdict=verdict, score=score, lots_retenus=retenus)

        fiche = self._fiche(opp, role, corr, zone, bilan, classement, verdict,
                            score, retenus)
        return Resultat(classement, score, fiche, journal, role.role, zone, bilan,
                        corr, verdict, retenus)

    # --------------------------------------------------------- fiche --
    def _fiche(self, opp, role, corr, zone, bilan, classement, verdict, score, retenus):
        compatible = list(bilan.atouts)
        for famille in corr.familles:
            libelle = self.ontologie.cfg["familles"][famille]["libelle"]
            preuves = corr.preuves.get(famille) or []
            compatible.append(libelle + (f" — « {preuves[0]} »" if preuves else ""))
        compatible += zone.raisons
        if role.preuves:
            compatible.append("prestation logistique : " + role.preuves[0])

        zone_txt = " → ".join(filter(None, ["/".join(zone.collecte), "/".join(zone.livraison)]))
        return Fiche(
            type=classement.type, titre=opp.intitule,
            acheteur=opp.acheteur, secteur=opp.secteur_acheteur, contact=opp.contact,
            lots_retenus=retenus, zone=zone_txt or (opp.lieu_texte or ""),
            collecte=zone.collecte, livraison=zone.livraison,
            echeance=(f"{verdict.echeance:%d/%m/%Y}" if verdict.echeance else "A_VERIFIER"),
            jours_restants=verdict.jours_restants,
            montant=opp.montant, devise=opp.devise, duree_mois=opp.duree_mois,
            cadence=opp.cadence,
            compatible=compatible, a_verifier=bilan.a_verifier + verdict.a_verifier,
            a_mobiliser=bilan.mobilisations,
            score=score.total, detail_score=score.detail(),
            action=classement.action,
            lien_dossier=opp.lien_dossier or opp.plateforme, lien_depot=opp.lien_depot,
            titulaire=opp.titulaire, signal=opp.signal_code,
            source=opp.source, reference=opp.ref_source)


def traiter(cx, moteur: Moteur, opportunites, maintenant_dt=None) -> BilanCycle:
    bilan = BilanCycle()
    vues = {}

    for opp in opportunites:
        bilan.lus += 1
        emp = deduplication.empreinte(opp)
        if emp in vues:
            deduplication.fusionner(vues[emp], opp)
            bilan.doublons += 1
            continue
        vues[emp] = opp
        if cx.execute("SELECT 1 FROM avis WHERE empreinte=? AND ref_source<>?",
                      (emp, opp.ref_source)).fetchone():
            bilan.doublons += 1

        avis_id = enregistrer_reponse(cx, opp.source, opp.ref_source, opp.brut or {}, emp)
        r = moteur.analyser(opp, maintenant_dt)

        if opp.attribue or (opp.type_avis or "").lower() in st.TYPES_ATTRIBUTION:
            m = memoire.memoriser(opp)
            cx.execute(
                "INSERT OR REPLACE INTO attributions(avis_id, acheteur, titulaire, montant,"
                " duree_mois, prestation, conclu_le, renouvellement, fiabilite, commentaire)"
                " VALUES(?,?,?,?,?,?,?,?,?,?)",
                (avis_id, m.acheteur, m.titulaire, m.montant, m.duree_mois, m.prestation,
                 m.conclu_le.isoformat() if m.conclu_le else None,
                 m.remise_en_concurrence.isoformat() if m.remise_en_concurrence else None,
                 m.fiabilite, m.commentaire))
            bilan.attributions += 1

        cx.execute(
            "INSERT INTO opportunites(avis_id, type, role, statut, zone, familles, lots_retenus,"
            " intitule, acheteur, montant, echeance, jours_restants, score, detail_score,"
            " journal, motif, fiche, calcule_le) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(avis_id) DO UPDATE SET type=excluded.type, score=excluded.score,"
            " fiche=excluded.fiche, motif=excluded.motif, calcule_le=excluded.calcule_le",
            (avis_id, r.classement.type.value, r.role.value, r.verdict.statut.value,
             r.zone.zone.value, ",".join(r.correspondance.familles),
             "; ".join(r.lots_retenus), opp.intitule, opp.acheteur, opp.montant,
             r.verdict.echeance.isoformat() if r.verdict.echeance else None,
             r.verdict.jours_restants, r.score.total,
             json.dumps(r.score.detail(), ensure_ascii=False),
             json.dumps(r.journal.en_lignes(), ensure_ascii=False),
             r.classement.motif, r.fiche.en_texte(), maintenant()))

        t = r.classement.type
        if t is Type.REJET:
            bilan.rejet += 1
            bilan.rejeter(r.classement.raisons_rejet[0] if r.classement.raisons_rejet
                          else r.classement.motif)
            continue
        setattr(bilan, {"DIRECT": "direct", "SOUS_TRAITANCE": "sous_traitance",
                        "PROSPECT": "prospect"}[t.value],
                getattr(bilan, {"DIRECT": "direct", "SOUS_TRAITANCE": "sous_traitance",
                                "PROSPECT": "prospect"}[t.value]) + 1)
        if envoi.mettre_en_file(cx, opp.source, opp.ref_source, r.fiche.en_texte()):
            bilan.notifies += 1

    cx.commit()
    return bilan
