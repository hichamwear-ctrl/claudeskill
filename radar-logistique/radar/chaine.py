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
from datetime import datetime, timezone


def _maintenant_utc():
    return datetime.now(timezone.utc)


def _libelle_etat(lecture) -> str:
    if lecture is None:
        return ""
    if not lecture.procedure_detectee and lecture.etat is proc.Etat.INCONNU:
        return "— aucune procédure : besoin exprimé directement, pas de dépôt à faire"
    return f"{lecture.etat.emoji} {lecture.etat.value} — {lecture.etat.libelle_long}"


def proc_collecte(opp):
    """La preuve de collecte portée par le brut, si elle existe."""
    from .mode import lire_collecte
    return lire_collecte(getattr(opp, "brut", None) or {})

from . import (chiffre_affaires, construction, deduplication, envoi,
               priorite as prio,
               fiabilite as fia, memoire,
               nature as nat, procedure as proc, questions, statut as st,
               transitions as tr)
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
    nature: object = None
    lecture: object = None          # l'état de procédure et ses preuves
    fiabilite: object = None        # à quel point c'est prouvé — JAMAIS dans le score
    ca: object = None               # PUBLIÉ · ESTIMATION · NON PUBLIÉ
    priorite: object = None         # adéquation ET potentiel, jamais fondus


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
    transitions: int = 0
    alertes: list = field(default_factory=list)   # les changements qui valent un appel
    motifs_rejet: dict = field(default_factory=dict)

    def rejeter(self, motif):
        self.motifs_rejet[motif] = self.motifs_rejet.get(motif, 0) + 1


class Moteur:
    def __init__(self, profil, capacites, geographie, ponderations, roles,
                 entreprises: RegistreEntreprises | None = None,
                 vocabulaires: dict | None = None):
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
        # Un vocabulaire de procédure PAR SOURCE. Le moteur ne connaît aucun
        # portail : il reçoit ce que chaque adaptateur a déclaré avoir observé.
        self.vocabulaires = dict(vocabulaires or {})

    def vocabulaire(self, source):
        return self.vocabulaires.get(source) or proc.Vocabulaire()

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
    def analyser(self, opp, maintenant_dt=None, fil=None) -> Resultat:
        nature = nat.qualifier(opp)
        role = self.roles.analyser(f"{opp.intitule} {opp.texte}", opp.cpv)
        corr = self.ontologie.analyser(f"{opp.intitule} {opp.texte}", opp.cpv)
        zone = self.geo.evaluer(opp.pays_collecte, opp.pays_livraison)
        bilan = self._confronter(opp)
        verdict = st.evaluer(opp, maintenant=maintenant_dt)

        # ── B · l'état de la procédure, avec ses preuves ──────────────────
        # Les dates n'arrivent qu'en rang 1 : elles éclairent, elles ne
        # tranchent pas. Un « attribué » explicite les écrase ; une date
        # dépassée ne produit jamais un ATTRIBUÉ.
        lecture = proc.lire(
            statut_source=opp.statut_source,
            type_information=opp.type_information or opp.type_avis,
            titre=opp.intitule, texte=opp.texte,
            texte_autour_du_statut=opp.texte_statut or "",
            documents=opp.documents, evenements=opp.evenements,
            actions_possibles=opp.actions_possibles,
            echeance=verdict.echeance, maintenant=maintenant_dt or _maintenant_utc(),
            date_attribution=opp.attribue_le,
            titulaire=opp.titulaire if opp.attribue else None,
            vocabulaire=self.vocabulaire(opp.source), source=opp.source,
            est_signal=opp.est_signal, lien_depot=opp.lien_depot)
        if opp.attribue and lecture.etat is not proc.Etat.ATTRIBUE:
            lecture.a_verifier.append(
                "la source déclare le marché attribué mais l'interprétation "
                "ne le confirme pas — à vérifier")

        # 🟣 : évalué DÈS QUE la prestation n'est pas reconnue. C'est ce qui
        # remplace l'ancien rejet par absence de vocabulaire.
        constr = None
        if not corr.familles and not corr.exclusions:
            # Combien de jours entre la clôture du dépôt et le démarrage —
            # c'est ce délai qui décide si une montée en compétence est possible.
            #
            # Une échéance POSTÉRIEURE au démarrage est une contradiction dans
            # les données publiées : on ne dépose pas une offre après le début
            # du contrat. Elle produisait un nombre de jours négatif — jusqu'à
            # -25 551 — traité comme « délai insuffisant », et le 🟣 était
            # refusé sur une donnée absurde plutôt que signalé comme illisible.
            jours = None
            dem, _ = st.parse_date(opp.date_demarrage)
            if dem and verdict.echeance:
                ecart = (dem - verdict.echeance).days
                jours = ecart if ecart >= 0 else None
            elif verdict.jours_restants is not None:
                jours = verdict.jours_restants
            constr = construction.evaluer(
                texte=f"{opp.intitule} {opp.texte}", familles_reconnues=corr.familles,
                jours_avant_demarrage=jours, duree_mois=opp.duree_mois,
                cadence=opp.cadence)

        # L'ANCRAGE COMMERCIAL : y a-t-il, sur cette page, le moindre fait
        # exploitable ? On ne cherche pas un mot — on cherche un FAIT : un
        # métier reconnu, un chiffre, une date, une exigence, un besoin
        # exprimé, un événement. Aucun des huit n'est un vocabulaire métier :
        # une page rédigée dans un jargon inconnu qui annonce « démarrage en
        # mars, 12 tournées par semaine » reste ancrée.
        ancrage = bool(
            corr.familles or corr.domaine_transport
            or opp.montant or opp.cadence or opp.duree_mois
            or opp.echeance_brute or opp.date_demarrage
            or opp.exigences or opp.exigences_texte
            or opp.vehicules_requis or opp.chauffeurs_requis
            or opp.km_annuels or opp.lots and len(opp.lots) > 1
            or opp.est_signal or nature is not nat.Nature.HYPOTHESE
            or lecture.procedure_detectee)

        classement = classer(
            role=role.role,
            ancrage_commercial=ancrage,
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
            nature=nature, etat=lecture.etat,
            procedure_detectee=lecture.procedure_detectee,
            depot_organise=lecture.depot_organise)

        # Le score mesure la valeur ÉCONOMIQUE : chiffre d'affaires, effort,
        # investissement, risque, marge, adéquation. L'état de la procédure n'y
        # entre pas. Un marché fermé vaut ce qu'il vaut — c'est l'ACTION qui
        # change, pas le potentiel. On classe donc une seconde fois « toutes
        # portes ouvertes » pour obtenir le type qui traduit la capacité seule.
        type_economique = classer(
            role=role.role,
            activite_reconnue=bool(corr.familles) or corr.domaine_transport,
            exclusion=", ".join(corr.exclusions[:2]) if corr.exclusions else None,
            zone_ok=zone.compatible,
            zone_motif=zone.raisons[0] if zone.raisons else "",
            deadline_ouverte=True, deadline_motif="", attribue=False, informatif=False,
            bilan_capacite=bilan, construction=constr,
            # AUCUNE des quatre dimensions n'entre ici. Ni l'état (B), ni la
            # nature (C), ni la provenance. Un signal dont le besoin sous-jacent
            # vaut 92 vaut 92 : ce qui change, c'est la CONFIANCE qu'on a dans
            # l'information — et elle a son propre champ, la fiabilité.
            # Le pondérer à la baisse reviendrait à cacher une bonne affaire
            # parce qu'elle a été découverte autrement qu'en lisant un avis.
            est_signal=False, nature=None,
            etat=proc.Etat.POSTULABLE, procedure_detectee=False).type
        # LE CHIFFRE D'AFFAIRES, avec son ÉTAT : publié, estimé, ou inconnu.
        # Mesuré AVANT le score, parce que le score doit noter le MÊME chiffre
        # que celui affiché sur la fiche.
        ca = chiffre_affaires.mesurer(opp, self.profil)
        score = self.bareme.calculer(correspondance=corr, zone=zone, bilan=bilan, opp=opp,
                                     type_opp=type_economique, cadence=opp.cadence,
                                     jours_restants=verdict.jours_restants, ca=ca)
        # FIABILITÉ — calculée APRÈS le score, et volontairement pas passée au
        # barème. Une information peu sûre remonte haut si elle vaut de
        # l'argent ; elle porte alors « FIABILITÉ : FAIBLE · ACTION : VÉRIFIER ».
        fiab = fia.evaluer(opp, nature=nature, lecture=lecture,
                           collecte=proc_collecte(opp))

        journal = questions.interroger(
            opp=opp, role=role.role, correspondance=corr, zone=zone, bilan=bilan,
            classement=classement, verdict=verdict, score=score,
            lots_retenus=[opp.lot_numero] if opp.lot_numero else [])
        fiche = self._fiche(opp, role, corr, zone, bilan, classement, verdict, score,
                            constr, nature, lecture, fiab, fil)
        # PRIORITÉ — assemble adéquation et potentiel SANS les écraser l'un
        # dans l'autre. Le score dit « puis-je le faire » ; le CA dit
        # « combien ça rapporte ». Les additionner reviendrait à refaire le
        # défaut qu'on vient de mesurer.
        priorite = prio.evaluer(ca, score, bilan, classement, opp)
        return Resultat(classement, score, fiche, journal, role.role, zone, bilan,
                        corr, verdict, constr, nature, lecture, fiab, ca, priorite)

    # ----------------------------------------------------------- fiche --
    def _fiche(self, opp, role, corr, zone, bilan, classement, verdict, score, constr,
               nature=None, lecture=None, fiab=None, fil=None):
        pourquoi = []
        for famille in corr.familles:
            libelle = self.ontologie.cfg["familles"][famille]["libelle"]
            preuves = corr.preuves.get(famille) or []
            pourquoi.append(libelle + (f" — « {preuves[0]} »" if preuves else ""))
        if not corr.familles and corr.preuve_domaine:
            pourquoi.append(f"domaine reconnu — {corr.preuve_domaine}")
        # « POURQUOI C'EST INTÉRESSANT » ne prend que des faits POSITIFS. Une
        # zone A_VERIFIER produisait la raison « aucun lieu publié — zone à
        # vérifier », et une page réelle sans le moindre rapport avec le
        # transport affichait donc une absence en guise d'argument commercial.
        # Ce qui manque a déjà sa rubrique, plus bas.
        from .geographie import Zone as _Zone
        if zone.zone is not _Zone.A_VERIFIER:
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
        if lecture is not None:
            manque += list(lecture.a_verifier)
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
            marge=score.marge_estimee, score=score.total, score_affiche=score.affichage,
            detail_score=score.detail(),
            lien=opp.lien_depot or opp.lien_dossier, source=opp.source,
            reference=opp.ref_source, nature=nature,
            etat=lecture.etat if lecture else None,
            etat_libelle=_libelle_etat(lecture),
            confiance_etat=lecture.confiance.value if lecture else "",
            type_information=lecture.type_information_source if lecture else "",
            preuves_etat=[str(p) for p in (lecture.preuves[:3] if lecture else [])],
            contradictions=list(lecture.contradictions) if lecture else [],
            fiabilite=fiab.niveau.value if fiab else "",
            fiabilite_motif=fiab.motif() if fiab else "",
            fil_de_vie=list(fil or []))


# Colonnes recalculées à chaque passage. Le bug qu'elles corrigent : `moteur`
# et `action` n'étaient PAS mis à jour, donc une opportunité passée de
# POSTULABLE à ATTRIBUÉ gardait « POSTULER » en base pendant que sa fiche
# disait « ATTRIBUÉ ». Une ligne qui se contredit elle-même est pire qu'une
# ligne absente : on agit dessus.
RECALCULEES = ("type", "moteur", "action", "role", "statut", "zone", "familles",
               "etat_procedure", "confiance_etat", "type_information", "nature",
               "secteur",
               "fiabilite", "fiabilite_motif", "echeance", "jours_restants",
               "score", "score_mesurable", "marge", "detail_score", "journal",
               "motif", "fiche", "manques", "leviers", "risques",
               "ca_ligne", "ca_mensuel", "ca_etat", "capacite",
               "ca_annuel", "intensite", "priorite", "calcule_le")

_COLONNES = ("avis_id", "type", "moteur", "action", "role", "statut", "zone",
             "familles", "marche_ref", "lot_numero", "intitule", "acheteur",
             "montant", "devise", "duree_mois", "cadence", "contact", "exigences",
             "echeance", "jours_restants", "distance_km", "etat_procedure",
             "confiance_etat", "type_information", "nature", "secteur",
             "fiabilite", "fiabilite_motif",
             "score", "score_mesurable", "marge", "detail_score", "journal",
             "motif", "fiche", "manques", "leviers", "risques",
             "ca_ligne", "ca_mensuel", "ca_etat", "capacite",
             "ca_annuel", "intensite", "priorite", "calcule_le")


def _valeurs(avis_id, opp, r) -> tuple:
    lecture = r.lecture
    return (avis_id, r.classement.type.value, r.classement.moteur.value,
            r.classement.action.value, r.role.value, r.verdict.statut.value,
            r.zone.zone.value, ",".join(r.correspondance.familles),
            opp.marche_ref, opp.lot_numero, opp.intitule, opp.acheteur, opp.montant,
            opp.devise, opp.duree_mois, opp.cadence, opp.contact,
            "; ".join(str(k) for k in (opp.exigences or {})) or None,
            r.verdict.echeance.isoformat() if r.verdict.echeance else None,
            r.verdict.jours_restants, opp.distance_depot_km,
            lecture.etat_affiche if lecture else None,
            lecture.confiance.value if lecture else None,
            lecture.type_information_source if lecture else None,
            r.nature.value if r.nature else None,
            opp.secteur_acheteur,
            r.fiabilite.niveau.value if r.fiabilite else None,
            r.fiabilite.motif() if r.fiabilite else None,
            r.score.total, 1 if r.score.mesurable else 0, r.score.marge_estimee,
            json.dumps(r.score.detail(), ensure_ascii=False),
            json.dumps(r.journal.en_lignes(), ensure_ascii=False),
            r.classement.motif, r.fiche.en_texte(),
            json.dumps(_manques_de_capacite(r), ensure_ascii=False),
            json.dumps(_leviers_de(r), ensure_ascii=False),
            json.dumps(_risques(r), ensure_ascii=False),
            r.ca.ligne(), r.ca.mensuel, r.ca.etat.value, _capacite_de(r),
            r.priorite.rang_ca or None, r.priorite.intensite, r.priorite.ligne(),
            maintenant())


def _capacite_de(r) -> str:
    """« 8/10 véhicules » — ce que je couvre du besoin, en une ligne."""
    part = r.bilan.part_couverte()
    if part is not None and r.bilan.couverture:
        besoin = sum(b for b, _ in r.bilan.couverture)
        couvert = sum(c for _, c in r.bilan.couverture)
        return f"{couvert}/{besoin} — {part:.0%} du besoin"
    if r.bilan.mobilisations:
        return "après mobilisation : " + r.bilan.mobilisations[0][:48]
    if r.bilan.atouts:
        return "exécutable avec la structure actuelle"
    return "NON MESURÉE — aucune exigence publiée"


def _leviers_de(r) -> list:
    """COMMENT combler. Les remèdes chiffrés, les moyens mobilisables, et ce
    que le test 🟣 a identifié comme levier existant."""
    leviers = list(r.bilan.remedes or [])
    # Quand un blocage est objectif, le plan chiffré remplace le silence.
    leviers += r.bilan.plan_de_faisabilite()
    if r.construction is not None and r.construction.leviers:
        leviers += [f"moyen déjà en place, réutilisable : {l}"
                    for l in r.construction.leviers]
    return leviers


def _manques_de_capacite(r) -> list:
    """CE QUI MANQUE POUR EXÉCUTER — rien d'autre.

    `fiche.il_me_manque` mélange trois choses pour un lecteur humain : les
    capacités qui manquent, les points à vérifier, et les manques du test 🟣.
    C'est bien pour lire une fiche, et faux pour répondre à « quelle capacité
    me manque » : la question 6 du rapport listait « TYPE D'INFORMATION
    INCONNU » comme s'il fallait acheter un camion pour le combler.
    Un manque se COMBLE (louer, recruter, former, s'associer) ; un point à
    vérifier se LÈVE en passant un appel — il est en question 9, le risque.
    """
    manques = list(r.bilan.bloquants) + list(r.bilan.mobilisations)
    if r.construction is not None and not r.construction.eligible:
        from .classification import Type
        if (r.classement.type is Type.A_CONSTRUIRE
                or not (r.correspondance.familles or r.correspondance.domaine_transport)):
            manques += list(r.construction.manques)
    return manques


def _risques(r) -> list:
    """Ce qui peut faire PERDRE l'affaire — distinct de ce qui manque pour
    l'exécuter. Un risque se lève en vérifiant ; un manque se comble."""
    risques = []
    if r.fiabilite is not None and r.fiabilite.niveau.value in ("FAIBLE", "NULLE"):
        risques.append(f"information peu prouvée ({r.fiabilite.niveau.value}) — "
                       f"{r.fiabilite.motif()}")
    if r.lecture is not None:
        risques += [c for c in r.lecture.contradictions]
        risques += [a for a in r.lecture.a_verifier]
    if r.nature is not None and r.nature.value == "HYPOTHÈSE":
        risques.append("besoin non confirmé : personne n'a encore dit le vouloir")
    if r.verdict.jours_restants is not None and 0 <= r.verdict.jours_restants <= 7:
        risques.append(f"il reste {r.verdict.jours_restants} jour(s) — "
                       "délai très court pour monter un dossier")
    for champ, valeur in (r.fiche.__dict__.get("champs_illisibles") or {}).items():
        risques.append(f"{champ} illisible : « {valeur} »")
    return risques


def _ecrire_opportunite(cx, avis_id: int, opp, r) -> None:
    """Écrit ou réécrit la ligne. TOUT ce qui est recalculé est réécrit."""
    maj = ", ".join(f"{c}=excluded.{c}" for c in RECALCULEES)
    cx.execute(
        f"INSERT INTO opportunites({', '.join(_COLONNES)})"
        f" VALUES({', '.join('?' * len(_COLONNES))})"
        f" ON CONFLICT(avis_id) DO UPDATE SET {maj}",
        _valeurs(avis_id, opp, r))


def _reecrire(cx, avis_id: int, r, opp) -> None:
    """Met à jour une opportunité déjà écrite, après fusion avec un doublon.

    On ne réécrit que ce que la fusion peut changer : la fiche, le score, le
    motif et les provenances. Le brut d'origine n'est jamais touché.
    """
    cx.execute(
        "UPDATE opportunites SET type=?, moteur=?, action=?, score=?,"
        " score_mesurable=?, marge=?,"
        " motif=?, fiche=?, journal=?, acheteur=COALESCE(acheteur, ?),"
        " montant=COALESCE(montant, ?), echeance=COALESCE(echeance, ?),"
        " contact=COALESCE(contact, ?), calcule_le=? WHERE avis_id=?",
        (r.classement.type.value, r.classement.moteur.value, r.classement.action.value,
         r.score.total, 1 if r.score.mesurable else 0,
         r.score.marge_estimee, r.classement.motif, r.fiche.en_texte(),
         json.dumps(r.journal.en_lignes(), ensure_ascii=False),
         opp.acheteur, opp.montant,
         r.verdict.echeance.isoformat() if r.verdict.echeance else None,
         opp.contact, maintenant(), avis_id))
    for p in opp.provenances or []:
        d = p if isinstance(p, dict) else p.__dict__
        cx.execute(
            "INSERT OR IGNORE INTO provenances(avis_id, source, url, requete, consulte_le)"
            " VALUES(?,?,?,?,?)",
            (avis_id, d.get("source") or "?", d.get("url"), d.get("requete"),
             d.get("consulte_le")))


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
    # id(opportunité conservée) -> avis_id, pour pouvoir la RÉÉCRIRE quand une
    # autre source apporte le même besoin.
    deja_ecrites: dict[int, int] = {}

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
                gardee = rapp.opportunite
                deduplication.fusionner(gardee, opp)
                bilan.doublons += 1
                if rapp.confiance is deduplication.Confiance.CERTAIN:
                    livre.doublons_certains += 1
                else:
                    livre.doublons_probables += 1
                # La fusion enrichit l'opportunité conservée : provenances
                # cumulées, trous comblés. Sans réécriture, la fiche en base
                # resterait celle d'AVANT la fusion et n'afficherait qu'une
                # seule source — la promesse multi-sources tomberait en silence.
                ancien = deja_ecrites.get(id(gardee))
                if ancien is not None:
                    _reecrire(cx, ancien, moteur.analyser(gardee, maintenant_dt), gardee)
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
            deja_ecrites[id(opp)] = avis_id
            # Le fil de vie déjà connu : la fiche doit montrer d'où vient
            # cette opportunité, pas seulement où elle en est aujourd'hui.
            fil = [f"{l['constate_le'][:10]} {l['ancien_etat'] or 'découverte'}"
                   f" → {l['nouvel_etat']}" for l in tr.fil_de_vie(cx, avis_id)]
            r = moteur.analyser(opp, maintenant_dt, fil=fil)
            # Toute formulation de statut jamais rencontrée est conservée, avec
            # son contexte, pour être tranchée une fois — jamais devinée.
            if r.lecture is not None and r.lecture.inconnues:
                proc.memoriser(cx, opp.source, r.lecture, opp.intitule or "",
                               langue=moteur.vocabulaire(opp.source).langue)

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

            # L'ordre compte : on compare à l'état DÉJÀ en base, avant de
            # l'écraser. Constater après la réécriture reviendrait à comparer
            # la ligne à elle-même — aucune transition ne serait jamais vue.
            transition = None
            if r.lecture is not None:
                transition = tr.constater(cx, avis_id, r.lecture, opp.source)
                if transition is not None:
                    bilan.transitions += 1
                    if transition.alerte:
                        bilan.alertes.append(
                            f"{opp.intitule[:48]} — {transition.libelle()}")
            _ecrire_opportunite(cx, avis_id, opp, r)

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
            # Un seul passage : il annule ce qui est périmé ET met en file
            # l'alerte quand la transition en mérite une.
            if transition is not None:
                if tr.appliquer(cx, transition, opp, r.fiche.en_texte()):
                    bilan.notifies += 1

    cx.commit()
    # Aucune disparition sans motif : si ça ne tombe pas juste, on échoue.
    livre.verifier()
    return bilan
