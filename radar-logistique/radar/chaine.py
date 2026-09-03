"""La chaîne complète.

  SOURCE → COLLECTE → NORMALISATION → MARCHÉ → ÉCLATEMENT EN LOTS
         → PRESTATIONS → GÉOGRAPHIE → EXIGENCES → CAPACITÉS
         → CONSTRUCTION 🟣 → CLASSIFICATION → SCORE → DÉDUPLICATION
         → ROUTAGE CAPTER / DÉVELOPPER → NOTIFICATION

CHANGEMENTS par rapport à la version précédente :
  · chaque LOT compatible devient une opportunité indépendante ;
  · l'absence de vocabulaire connu ne rejette plus rien — elle passe par 🟣 ;
  · les cinq catégories remplacent les quatre ;
  · deux moteurs de sortie au lieu d'un seul flux.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import construction, deduplication, envoi, memoire, questions, statut as st
from .comptes import Livre
from .mode import CollecteInvalide, Mode, verifier as verifier_collecte
from .entreprises import Registre as RegistreEntreprises
from .activite import Ontologie
from .base import enregistrer_reponse, maintenant
from .capacite import Bilan, Capacites
from .classification import Moteur as MoteurSortie, Type, classer
from .fiche import Fiche
from .geographie import Geographie
from .lots import eclater
from .role import DetecteurDeRole, Role
from .score import Bareme


@dataclass
class Resultat:
    classement: object
    score: object
    fiche: Fiche
    journal: object
    role: Role
    zone: object
    bilan: Bilan
    correspondance: object
    verdict: object
    construction: object = None


@dataclass
class BilanCycle:
    mode: object = None
    livre: Livre = field(default_factory=Livre)
    lus: int = 0
    lots_eclates: int = 0
    doublons: int = 0
    direct: int = 0
    renforcement: int = 0
    a_construire: int = 0
    prospect: int = 0
    rejet: int = 0
    capter: int = 0
    developper: int = 0
    notifies: int = 0
    attributions: int = 0
    motifs_rejet: dict = field(default_factory=dict)

    def rejeter(self, motif):
        self.motifs_rejet[motif] = self.motifs_rejet.get(motif, 0) + 1


class Moteur:
    def __init__(self, profil, capacites, geographie, ponderations, roles,
                 entreprises: RegistreEntreprises | None = None):
        # Le registre d'entreprises est optionnel : le moteur fonctionne sans,
        # mais avec lui chaque opportunité nourrit la boucle commerciale.
        self.entreprises = entreprises if entreprises is not None else RegistreEntreprises()
        self.profil = profil
        self.libelles = capacites.get("exigences", {})
        self.ontologie = Ontologie(capacites, profil["familles_actives"],
                                   profil.get("familles_exclues"))
        self.geo = Geographie(geographie)
        self.bareme = Bareme(ponderations, profil)
        self.roles = DetecteurDeRole(roles)
        self.capacites = Capacites(profil, self.libelles)

    # ------------------------------------------------------- exigences --
    def _confronter(self, opp) -> Bilan:
        b = Bilan()
        c = self.capacites
        for code, valeur in (opp.exigences or {}).items():
            if valeur in (None, False, ""):
                continue
            if code == "vehicules_min":
                b.ajouter(c.vehicules(int(valeur)))
            elif code == "chauffeurs_min":
                b.ajouter(c.chauffeurs(int(valeur)))
            elif code == "vehicule_type":
                type_, nb = (valeur if isinstance(valeur, (list, tuple)) else (valeur, 1))
                b.ajouter(c.vehicules_par_type(str(type_), int(nb)))
            elif code == "tonnage_min_t":
                b.ajouter(c.tonnage(float(valeur)))
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
        # Une exigence de véhicules implique des chauffeurs : on le signale.
        if opp.chauffeurs_requis:
            b.ajouter(c.chauffeurs(int(opp.chauffeurs_requis)))
        return b

    # --------------------------------------------------------- analyse --
    def analyser(self, opp, maintenant_dt=None) -> Resultat:
        role = self.roles.analyser(f"{opp.intitule} {opp.texte}", opp.cpv)
        corr = self.ontologie.analyser(f"{opp.intitule} {opp.texte}", opp.cpv)
        zone = self.geo.evaluer(opp.pays_collecte, opp.pays_livraison)
        bilan = self._confronter(opp)
        verdict = st.evaluer(opp, maintenant=maintenant_dt)

        # 🟣 : évalué DÈS QUE la prestation n'est pas reconnue. C'est ce qui
        # remplace l'ancien rejet par absence de vocabulaire.
        constr = None
        if not corr.familles and not corr.exclusions:
            jours = None
            dem, _ = st.parse_date(opp.date_demarrage)
            if dem and verdict.echeance:
                jours = (dem - verdict.echeance).days
            elif verdict.jours_restants is not None:
                jours = verdict.jours_restants
            constr = construction.evaluer(
                texte=f"{opp.intitule} {opp.texte}", familles_reconnues=corr.familles,
                jours_avant_demarrage=jours, duree_mois=opp.duree_mois,
                cadence=opp.cadence)

        classement = classer(
            role=role.role,
            activite_reconnue=bool(corr.familles) or corr.domaine_transport,
            exclusion=", ".join(corr.exclusions[:2]) if corr.exclusions else None,
            zone_ok=zone.compatible,
            zone_motif=zone.raisons[0] if zone.raisons else "",
            deadline_ouverte=verdict.statut.depot_possible,
            deadline_motif=verdict.motif,
            attribue=verdict.statut is st.Statut.ATTRIBUE,
            informatif=(opp.type_avis or "").lower() in st.TYPES_INFORMATIFS,
            bilan_capacite=bilan,
            construction=constr,
            est_signal=opp.est_signal,
            source_privee=(opp.secteur_acheteur or "").lower().startswith("priv"))

        score = self.bareme.calculer(correspondance=corr, zone=zone, bilan=bilan, opp=opp,
                                     type_opp=classement.type, cadence=opp.cadence,
                                     jours_restants=verdict.jours_restants)
        journal = questions.interroger(
            opp=opp, role=role.role, correspondance=corr, zone=zone, bilan=bilan,
            classement=classement, verdict=verdict, score=score,
            lots_retenus=[opp.lot_numero] if opp.lot_numero else [])
        fiche = self._fiche(opp, role, corr, zone, bilan, classement, verdict, score, constr)
        return Resultat(classement, score, fiche, journal, role.role, zone, bilan,
                        corr, verdict, constr)

    # ----------------------------------------------------------- fiche --
    def _fiche(self, opp, role, corr, zone, bilan, classement, verdict, score, constr):
        pourquoi = []
        for famille in corr.familles:
            libelle = self.ontologie.cfg["familles"][famille]["libelle"]
            preuves = corr.preuves.get(famille) or []
            pourquoi.append(libelle + (f" — « {preuves[0]} »" if preuves else ""))
        pourquoi += zone.raisons
        if role.preuves:
            pourquoi.append("prestation logistique : " + role.preuves[0])
        if constr and constr.eligible:
            pourquoi.append(constr.motif)

        # Ce qui manque : les blocages, les moyens à mobiliser, les points non
        # confirmés, et ce qui empêche une montée en compétence.
        manque = list(bilan.bloquants) + list(bilan.mobilisations)
        # Les manques du test 🟣 ne concernent QUE les fiches où la montée en
        # compétence est la question posée. Sur un lot de transport bloqué par
        # six véhicules, « aucune formation mentionnée dans la source » n'est
        # pas un manque : c'est du bruit, et le bruit fait des boîtes noires.
        if (constr and not constr.eligible
                and (classement.type is Type.A_CONSTRUIRE
                     or not (corr.familles or corr.domaine_transport))):
            manque += constr.manques
        manque += list(bilan.a_verifier)
        # Un champ publié mais illisible n'est ni ignoré ni deviné : il est dit.
        for champ, valeur in (opp.champs_illisibles or {}).items():
            manque.append(f"{champ} publié mais illisible : « {valeur} » — À VÉRIFIER")

        # Ce que l'entreprise a déjà : les exigences couvertes, plus les leviers
        # que le test 🟣 a identifiés — sinon une fiche « à construire » laisse
        # croire qu'on part de rien.
        j_ai = list(bilan.atouts)
        if constr and constr.leviers:
            j_ai += [f"levier existant : {l}" for l in constr.leviers]

        zone_txt = " → ".join(filter(None, ["/".join(zone.collecte), "/".join(zone.livraison)]))
        return Fiche(
            type=classement.type, moteur=classement.moteur.value,
            action=classement.action.value, titre=opp.intitule,
            client=opp.acheteur or opp.titulaire, secteur=opp.secteur_acheteur,
            contact=opp.contact, marche_parent=opp.marche_ref, lot=opp.lot_numero,
            provenances=[p if isinstance(p, dict) else p.__dict__ for p in opp.provenances],
            zone=zone_txt or (opp.lieu_texte or ""), corridor=zone.zone.value,
            statut_date=f"{verdict.statut.emoji} {verdict.statut.value}",
            echeance=(f"{verdict.echeance:%d/%m/%Y}" if verdict.echeance else "NON PUBLIÉ"),
            demarrage=(str(opp.date_demarrage)[:10] if opp.date_demarrage else "NON PUBLIÉ"),
            jours_restants=verdict.jours_restants, duree_mois=opp.duree_mois,
            cadence=opp.cadence, montant=opp.montant, devise=opp.devise,
            objet=opp.texte[:220] or None,
            pourquoi=pourquoi, j_ai_deja=j_ai, il_me_manque=manque,
            comment_combler=bilan.remedes or bilan.mobilisations,
            raisons_categorie=[classement.motif] + classement.raisons[:3],
            marge=score.marge_estimee, score=score.total, detail_score=score.detail(),
            lien=opp.lien_depot or opp.lien_dossier, source=opp.source,
            reference=opp.ref_source)


def _incident(cx, ligne, opp, etape, motif, mode):
    """Conserve une ligne non traitée. Elle ne disparaît jamais en silence."""
    cx.execute(
        "INSERT INTO incidents(ligne, source, reference, etape, motif, charge, mode,"
        " cree_le) VALUES(?,?,?,?,?,?,?,?)",
        (ligne, getattr(opp, "source", "?"), getattr(opp, "ref_source", None),
         etape, motif, json.dumps(getattr(opp, "brut", {}) or {}, ensure_ascii=False),
         getattr(mode, "value", str(mode)), maintenant()))


def traiter(cx, moteur: Moteur, opportunites, maintenant_dt=None,
            mode: Mode = Mode.DEMO) -> BilanCycle:
    """Traite un lot. En mode RÉEL, refuse toute ligne sans preuve de collecte.

    Le livre de comptes suit chaque ligne : si les totaux ne se réconcilient
    pas en fin de cycle, l'exécution échoue au lieu de continuer.
    """
    bilan = BilanCycle(mode=mode)
    livre = bilan.livre
    index = deduplication.Index()

    for brut in opportunites:
        bilan.lus += 1
        livre.brutes += 1

        # Contrôle d'entrée : une fixture ne peut pas entrer en mode RÉEL.
        # L'avis refusé est CONSERVÉ comme incident, avec son brut et son motif.
        try:
            verifier_collecte(brut.brut or {}, mode)
        except CollecteInvalide as e:
            motif = str(e).split(" (")[0]
            livre.illisible(motif)
            _incident(cx, bilan.lus, brut, "collecte", motif, mode)
            continue

        enfants = eclater(brut)
        livre.normalisees += 1
        livre.lots_ajoutes += max(len(enfants) - 1, 0)
        if len(enfants) > 1:
            bilan.lots_eclates += len(enfants)

        for opp in enfants:
            # Trois empreintes : identique, même page, ou même besoin formulé
            # autrement. C'est ce qui fusionne un avis BDA et une page Google.
            rapp = index.rapprocher(opp)
            if rapp is not None and rapp.confiance.fusionne:
                deduplication.fusionner(rapp.opportunite, opp)
                bilan.doublons += 1
                if rapp.confiance is deduplication.Confiance.CERTAIN:
                    livre.doublons_certains += 1
                else:
                    livre.doublons_probables += 1
                continue
            if rapp is not None:
                # POSSIBLE : on ne fusionne PAS. Les deux fiches vivent, reliées.
                livre.doublons_possibles += 1
                opp.doublon_possible = rapp.opportunite.ref_source
                opp.doublon_motif = rapp.motif
            index.ajouter(opp)
            emp = deduplication.empreinte(opp)
            if cx.execute("SELECT 1 FROM avis WHERE empreinte=? AND ref_source<>?",
                          (emp, opp.ref_source)).fetchone():
                bilan.doublons += 1

            avis_id = enregistrer_reponse(cx, opp.source, opp.ref_source, opp.brut or {}, emp)
            r = moteur.analyser(opp, maintenant_dt)

            if r.verdict.statut is st.Statut.ATTRIBUE:
                m = memoire.memoriser(opp)
                cx.execute(
                    "INSERT OR REPLACE INTO attributions(avis_id, acheteur, titulaire,"
                    " montant, duree_mois, prestation, zone, lots, conclu_le, debut, fin,"
                    " renouvellement, fiabilite, commentaire, contact, taille_apparente,"
                    " besoin_sous_traitance) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (avis_id, m.acheteur, m.titulaire, m.montant, m.duree_mois,
                     m.prestation, m.zone, "; ".join(m.lots),
                     m.conclu_le.isoformat() if m.conclu_le else None,
                     m.debut.isoformat() if m.debut else None,
                     m.fin.isoformat() if m.fin else None,
                     m.remise_en_concurrence.isoformat() if m.remise_en_concurrence else None,
                     m.fiabilite, m.commentaire, m.contact, m.taille_apparente,
                     m.besoin_sous_traitance))
                bilan.attributions += 1
                # Le titulaire entre au registre : il devra exécuter.
                moteur.entreprises.depuis_attribution(opp)
            else:
                moteur.entreprises.depuis_opportunite(opp)

            cx.execute(
                "INSERT INTO opportunites(avis_id, type, moteur, action, role, statut, zone,"
                " familles, marche_ref, lot_numero, intitule, acheteur, montant, devise,"
                " duree_mois, cadence, contact, exigences, echeance,"
                " jours_restants, distance_km,"
                " score, marge, detail_score, journal, motif, fiche, calcule_le)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(avis_id) DO UPDATE SET type=excluded.type, score=excluded.score,"
                " fiche=excluded.fiche, motif=excluded.motif, calcule_le=excluded.calcule_le",
                (avis_id, r.classement.type.value, r.classement.moteur.value,
                 r.classement.action.value, r.role.value, r.verdict.statut.value,
                 r.zone.zone.value, ",".join(r.correspondance.familles),
                 opp.marche_ref, opp.lot_numero, opp.intitule, opp.acheteur, opp.montant,
                 opp.devise, opp.duree_mois, opp.cadence, opp.contact,
                 "; ".join(str(k) for k in (opp.exigences or {})) or None,
                 r.verdict.echeance.isoformat() if r.verdict.echeance else None,
                 r.verdict.jours_restants, opp.distance_depot_km, r.score.total, r.score.marge_estimee,
                 json.dumps(r.score.detail(), ensure_ascii=False),
                 json.dumps(r.journal.en_lignes(), ensure_ascii=False),
                 r.classement.motif, r.fiche.en_texte(), maintenant()))

            t = r.classement.type
            if t is Type.REJET:
                bilan.rejet += 1
                motif = (r.classement.raisons_rejet[0] if r.classement.raisons_rejet
                         else r.classement.motif)
                bilan.rejeter(motif)
                livre.rejeter(motif)
                continue

            for typ, attr in ((Type.DIRECT, "direct"), (Type.RENFORCEMENT, "renforcement"),
                              (Type.A_CONSTRUIRE, "a_construire"), (Type.PROSPECT, "prospect")):
                if t is typ:
                    setattr(bilan, attr, getattr(bilan, attr) + 1)
            if r.classement.moteur is MoteurSortie.CAPTER:
                bilan.capter += 1
                livre.capter += 1
            else:
                bilan.developper += 1
                livre.developper += 1

            if envoi.mettre_en_file(cx, opp.source, opp.ref_source, r.fiche.en_texte()):
                bilan.notifies += 1

    cx.commit()
    # Aucune disparition sans motif : si ça ne tombe pas juste, on échoue.
    livre.verifier()
    return bilan
