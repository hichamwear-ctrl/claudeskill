"""Tests de COMPORTEMENT — un par règle du cahier des charges.

Aucun ne vérifie qu'une ligne de code existe. Chacun pose une question dont la
mauvaise réponse coûte un contrat.
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from radar import construction, envoi, statut as st
from radar.activite import Ontologie
from radar.base import ouvrir
from radar.capacite import Capacites, Niveau
from radar.chaine import Moteur, traiter
from radar.classification import Action, Moteur as MoteurSortie, Type
from radar.decouverte import ConnecteurGoogle, ConnecteurIndisponible, Generateur
from radar.geographie import Geographie, Zone
from radar.lots import eclater
from radar.modele import LotBrut, Opportunite
from radar.boucle import Boucle
from radar.deduplication import Index, fusionner, libelle_provenances
from radar.entreprises import Etat as EtatEnt, Registre as RegistreEnt, nom_probable
from radar.memoire import memoriser
from radar.registre import Etat, Registre
from radar.role import DetecteurDeRole, Role

MAINTENANT = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
OUVERT = "2026-11-15T11:00:00+01:00"


def cfg(n):
    return yaml.safe_load((RACINE / n).read_text(encoding="utf-8"))


PROFIL, CAPACITES = cfg("profil.yaml"), cfg("config/capacites.yaml")
GEO, PONDS = cfg("config/geographie.yaml"), cfg("config/ponderations.yaml")
ROLES, DECOUVERTE = cfg("config/roles.yaml"), cfg("config/decouverte.yaml")


def moteur():
    return Moteur(PROFIL, CAPACITES, GEO, PONDS, ROLES)


def opp(**kw):
    base = dict(source="bda", ref_source="R1", intitule="Transport de colis",
                texte="transport routier de marchandises et distribution",
                type_avis="appel-offres", cpv=["60000000"], pays_livraison=["BE"],
                echeance_brute=OUVERT)
    base.update(kw)
    return Opportunite(**base)


# ══════════════ §2 — l'entreprise est un point de départ, pas une limite
class CapacitesEnTroisNiveaux(unittest.TestCase):
    def setUp(self):
        self.c = Capacites(PROFIL, CAPACITES["exigences"])

    def test_dans_le_parc_actuel(self):
        self.assertIs(self.c.vehicules(4).niveau, Niveau.ACTUELLE)

    def test_douze_vehicules_est_une_mobilisation_pas_un_blocage(self):
        r = self.c.vehicules(12)
        self.assertIs(r.niveau, Niveau.MOBILISABLE)
        self.assertIn("louer", r.message)

    def test_le_parc_n_est_pas_un_total_unique(self):
        """6 véhicules au total, mais seulement 2 de type 20 m³."""
        r = self.c.vehicules_par_type("20m3", 6)
        self.assertIs(r.niveau, Niveau.MOBILISABLE)
        self.assertIn("2 au parc", r.message)

    def test_dix_chauffeurs_couvrent_un_besoin_de_huit(self):
        self.assertIs(self.c.chauffeurs(8).niveau, Niveau.ACTUELLE)

    def test_un_besoin_de_chauffeurs_superieur_devient_un_recrutement(self):
        r = self.c.chauffeurs(14)
        self.assertIs(r.niveau, Niveau.MOBILISABLE)
        self.assertIn("recruter", r.message)

    def test_le_tonnage_des_20m3_est_signale_et_jamais_tranche(self):
        r = self.c.tonnage(3.5)
        self.assertIs(r.niveau, Niveau.A_VERIFIER)
        self.assertIn("n'est pas confirmé", r.message)

    def test_une_qualification_ne_se_loue_pas(self):
        self.assertIs(self.c.qualification("adr").niveau, Niveau.NON_DISPONIBLE)

    def test_une_qualification_inconnue_n_est_jamais_presumee(self):
        self.assertIs(self.c.qualification("gdp").niveau, Niveau.A_VERIFIER)


# ══════════════ §3 — les cinq catégories
class CinqCategories(unittest.TestCase):
    def _type(self, **kw):
        return moteur().analyser(opp(**kw), MAINTENANT).classement.type

    def test_structure_actuelle_donne_direct(self):
        self.assertIs(self._type(), Type.DIRECT)

    def test_location_necessaire_donne_renforcement(self):
        """CHANGEMENT : 🟡 signifie renforcement, plus sous-traitance."""
        self.assertIs(self._type(exigences={"vehicules_min": 12}), Type.RENFORCEMENT)

    def test_recrutement_necessaire_donne_renforcement(self):
        self.assertIs(self._type(exigences={"chauffeurs_min": 15}), Type.RENFORCEMENT)

    def test_trop_gros_pour_moi_seul_donne_prospect_jamais_rejet(self):
        r = moteur().analyser(opp(exigences={"vehicules_min": 30}), MAINTENANT)
        self.assertIs(r.classement.type, Type.PROSPECT)
        self.assertIn(r.classement.action,
                      (Action.PROPOSER_GROUPEMENT, Action.PROPOSER_SOUS_TRAITANCE))

    def test_qualification_impossible_donne_rejet(self):
        self.assertIs(self._type(exigences={"adr": True}), Type.REJET)

    def test_un_signal_donne_prospect(self):
        self.assertIs(self._type(est_signal=True), Type.PROSPECT)


# ══════════════ §4 et §5 — 🟣 à construire
class MetiersAConstruire(unittest.TestCase):
    PORTES = ("Recherche entreprise pour le dépannage de portes sectionnelles chez nos "
              "clients. Formation complète des techniciens assurée, 2 semaines. "
              "Accompagnement au démarrage.")

    def test_un_metier_inconnu_avec_formation_devient_a_construire(self):
        r = moteur().analyser(opp(intitule="Dépannage de portes sectionnelles",
                                  texte=self.PORTES, cpv=[], duree_mois=36,
                                  cadence="hebdomadaire"), MAINTENANT)
        self.assertIs(r.classement.type, Type.A_CONSTRUIRE)

    def test_sans_formation_mentionnee_ce_n_est_jamais_a_construire(self):
        r = moteur().analyser(opp(intitule="Dépannage de portes sectionnelles",
                                  texte="Dépannage de portes sectionnelles chez nos clients.",
                                  cpv=[], duree_mois=36, cadence="hebdomadaire"), MAINTENANT)
        self.assertIsNot(r.classement.type, Type.A_CONSTRUIRE)

    def test_la_comptabilite_reste_hors_perimetre_meme_avec_formation(self):
        v = construction.evaluer(
            texte="Prestation de comptabilité. Formation complète assurée.",
            familles_reconnues=[], jours_avant_demarrage=180, duree_mois=36,
            cadence="mensuelle")
        self.assertFalse(v.eligible)
        self.assertIn("hors périmètre", v.motif)

    def test_une_formation_n_efface_pas_une_obligation_legale(self):
        v = construction.evaluer(
            texte="Installation sur site. Formation complète assurée. "
                  "Agrément obligatoire requis avant intervention.",
            familles_reconnues=[], jours_avant_demarrage=200, duree_mois=36,
            cadence="mensuelle")
        self.assertFalse(v.eligible)
        self.assertIsNotNone(v.obligation_legale)

    def test_un_delai_trop_court_bloque_la_montee_en_competence(self):
        v = construction.evaluer(
            texte="Dépannage sur site. Formation complète des techniciens, 4 semaines.",
            familles_reconnues=[], jours_avant_demarrage=10, duree_mois=24,
            cadence="mensuelle")
        self.assertIn("délai suffisant", v.echecs())

    def test_une_mission_ponctuelle_ne_justifie_pas_une_formation(self):
        v = construction.evaluer(
            texte="Installation sur site. Formation complète assurée.",
            familles_reconnues=[], jours_avant_demarrage=200, duree_mois=2,
            cadence="ponctuelle")
        self.assertIn("cohérence économique", v.echecs())


# ══════════════ §7 et §10 — jamais de rejet par mot-clé
class JamaisDeRejetParMotCle(unittest.TestCase):
    def test_un_metier_inconnu_n_est_jamais_rejete(self):
        r = moteur().analyser(opp(intitule="Prestation inclassable",
                                  texte="activité sans vocabulaire connu", cpv=[]),
                              MAINTENANT)
        self.assertIsNot(r.classement.type, Type.REJET)

    def test_il_devient_un_prospect_a_qualifier(self):
        r = moteur().analyser(opp(intitule="Prestation inclassable",
                                  texte="activité sans vocabulaire connu", cpv=[]),
                              MAINTENANT)
        self.assertIs(r.classement.type, Type.PROSPECT)
        self.assertIs(r.classement.action, Action.SURVEILLER)


# ══════════════ §6 — prestation contre fourniture
class PrestationOuFourniture(unittest.TestCase):
    def setUp(self):
        self.d = DetecteurDeRole(ROLES)

    def test_fourniture_et_livraison_de_poissons_n_est_pas_du_transport(self):
        self.assertIs(self.d.analyser("Fourniture et livraison de poissons frais",
                                      ["15200000"]).role, Role.FOURNISSEUR)

    def test_transport_pour_le_compte_de_est_une_prestation(self):
        self.assertIs(self.d.analyser("Transport de poissons pour le compte de l'hôpital",
                                      ["60000000"]).role, Role.PRESTATAIRE)

    def test_un_marche_de_fourniture_n_est_jamais_notifie(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(ref_source="POISSON",
                                   intitule="Fourniture et livraison de poissons",
                                   texte="fourniture et livraison de poissons frais",
                                   cpv=["15200000"])], maintenant_dt=MAINTENANT)
        self.assertEqual(cx.execute("SELECT count(*) c FROM envois").fetchone()["c"], 0)


# ══════════════ §6 — un lot = une opportunité indépendante
class UneOpportuniteParLot(unittest.TestCase):
    MARCHE = dict(
        ref_source="M-102", intitule="Fourniture, livraison et installation d'équipements",
        texte="marché d'équipements techniques", cpv=["42000000"],
        lots=[LotBrut(numero="1", intitule="Fourniture de machines-outils",
                      texte="fourniture de machines", cpv=["42600000"]),
              LotBrut(numero="15", intitule="Déménagement de postes de soudure",
                      texte="déménagement et manutention entre sites",
                      cpv=["98392000"], montant=45000, duree_mois=12)])

    def test_le_marche_est_eclate_en_autant_d_opportunites_que_de_lots(self):
        self.assertEqual(len(eclater(opp(**self.MARCHE))), 2)

    def test_chaque_lot_garde_le_lien_vers_son_marche_parent(self):
        for e in eclater(opp(**self.MARCHE)):
            self.assertEqual(e.marche_ref, "M-102")

    def test_seul_le_lot_compatible_est_notifie(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(**self.MARCHE)], maintenant_dt=MAINTENANT)
        refs = {l["ref_source"] for l in cx.execute("SELECT ref_source FROM envois")}
        self.assertIn("M-102#L15", refs)
        self.assertNotIn("M-102#L1", refs)

    def test_le_lot_porte_son_propre_montant(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(**self.MARCHE)], maintenant_dt=MAINTENANT)
        l = cx.execute("SELECT montant FROM opportunites o JOIN avis a ON a.id=o.avis_id "
                       "WHERE a.ref_source='M-102#L15'").fetchone()
        self.assertEqual(l["montant"], 45000)

    def test_un_lot_sans_montant_n_herite_pas_de_celui_du_marche(self):
        """Hériter serait inventer une valeur."""
        e = eclater(opp(montant=900000, **self.MARCHE))
        self.assertIsNone(e[0].montant)


# ══════════════ §9 — CAPTER et DÉVELOPPER
class DeuxMoteurs(unittest.TestCase):
    def test_un_marche_ouvert_va_dans_capter(self):
        r = moteur().analyser(opp(), MAINTENANT)
        self.assertIs(r.classement.moteur, MoteurSortie.CAPTER)

    def test_une_attribution_va_dans_developper(self):
        r = moteur().analyser(opp(attribue=True, titulaire="Grand opérateur"), MAINTENANT)
        self.assertIs(r.classement.moteur, MoteurSortie.DEVELOPPER)
        self.assertIs(r.classement.action, Action.CONTACTER_TITULAIRE)

    def test_une_attribution_ne_dit_jamais_postuler(self):
        r = moteur().analyser(opp(attribue=True), MAINTENANT)
        self.assertIsNot(r.classement.action, Action.POSTULER)

    def test_une_echeance_depassee_bascule_en_developper(self):
        r = moteur().analyser(opp(echeance_brute="2026-08-01T11:00:00+02:00"), MAINTENANT)
        self.assertIs(r.classement.moteur, MoteurSortie.DEVELOPPER)
        self.assertIs(r.classement.action, Action.SURVEILLER)


# ══════════════ §14 — les quatre états de date
class EtatsDeDate(unittest.TestCase):
    def _statut(self, **kw):
        return st.evaluer(opp(**kw), maintenant=MAINTENANT).statut

    def test_ouvert(self):
        self.assertIs(self._statut(), st.Statut.OUVERT)

    def test_bientot_ferme(self):
        self.assertIs(self._statut(echeance_brute="2026-09-05T11:00:00+02:00"),
                      st.Statut.BIENTOT_FERME)

    def test_depasse(self):
        self.assertIs(self._statut(echeance_brute="2026-08-01T11:00:00+02:00"),
                      st.Statut.DEPASSE)

    def test_attribue(self):
        self.assertIs(self._statut(attribue=True), st.Statut.ATTRIBUE)

    def test_inconnue_et_jamais_ecartee(self):
        s = self._statut(echeance_brute="prochainement")
        self.assertIs(s, st.Statut.INCONNUE)
        self.assertTrue(s.depot_possible)

    def test_aucune_date_n_est_jamais_inventee(self):
        self.assertIsNone(st.parse_date("prochainement")[0])
        self.assertIsNone(st.parse_date(None)[0])


# ══════════════ §12 et §19 — l'économie, pas le montant
class EconomieAvantMontant(unittest.TestCase):
    def _score(self, **kw):
        return moteur().analyser(opp(**kw), MAINTENANT).score.total

    def test_un_petit_contrat_recurrent_proche_bat_un_gros_marche_lointain(self):
        petit = self._score(montant=288000, duree_mois=36, cadence="quotidienne",
                            distance_depot_km=25, km_annuels=18000)
        gros = self._score(montant=500000, duree_mois=36, cadence="quotidienne",
                           distance_depot_km=200, km_annuels=90000,
                           travail_nuit=True, travail_weekend=True,
                           exigences={"vehicules_min": 10})
        self.assertGreater(petit, gros)

    def test_la_proximite_du_depot_est_valorisee(self):
        self.assertGreater(self._score(distance_depot_km=20),
                           self._score(distance_depot_km=250))

    def test_le_kilometrage_lourd_penalise(self):
        self.assertGreater(self._score(km_annuels=15000), self._score(km_annuels=90000))

    def test_la_nuit_et_le_week_end_penalisent(self):
        self.assertGreater(self._score(),
                           self._score(travail_nuit=True, travail_weekend=True))

    def test_la_marge_reste_non_mesuree_sans_couts_au_profil(self):
        r = moteur().analyser(opp(montant=200000, duree_mois=24), MAINTENANT)
        self.assertEqual(r.score.marge_estimee, "NON MESURÉE")

    def test_un_score_faible_ne_supprime_jamais_une_opportunite(self):
        cx = ouvrir(":memory:")
        b = traiter(cx, moteur(), [opp(ref_source="FAIBLE", cadence="ponctuelle",
                                       montant=900, km_annuels=95000)],
                    maintenant_dt=MAINTENANT)
        self.assertEqual(b.notifies, 1)

    def test_chaque_point_est_justifie(self):
        for l in moteur().analyser(opp(montant=250000, duree_mois=24), MAINTENANT).score.lignes:
            self.assertTrue(l.raison, f"« {l.critere} » n'explique pas ses points")


# ══════════════ §7 — Google, découverte
class DecouverteGoogle(unittest.TestCase):
    def setUp(self):
        self.g = Generateur(DECOUVERTE)

    def test_des_requetes_sont_reellement_generees(self):
        self.assertGreater(len(self.g.generer()), 500)

    def test_les_requetes_locales_passent_avant_les_nationales(self):
        premieres = self.g.generer(30)
        self.assertTrue(any("Bruxelles" in q.texte for q in premieres))

    def test_le_besoin_explicite_prime_sur_le_signal_indirect(self):
        familles = [q.famille for q in self.g.generer(20)]
        self.assertIn("besoin_explicite", familles)

    def test_une_entreprise_decouverte_declenche_ses_propres_requetes(self):
        reqs = self.g.pour_entreprise("Transports Dupont", "dupont.be")
        self.assertTrue(any("site:dupont.be" in q.texte for q in reqs))

    def test_sans_cle_le_connecteur_est_indisponible_et_ne_simule_rien(self):
        c = ConnecteurGoogle()
        self.assertFalse(c.disponible)
        self.assertIn("CLÉ ABSENTE", c.motif_indisponibilite)
        with self.assertRaises(ConnecteurIndisponible):
            c.rechercher(self.g.generer(1)[0])


# ══════════════ §21 et §22 — le registre ne ment jamais
class RegistreHonnete(unittest.TestCase):
    def test_une_source_est_jamais_consultee_par_defaut(self):
        r = Registre()
        s = r.declarer("ted", "publics", "api")
        self.assertIs(s.etat, Etat.JAMAIS_CONSULTEE)
        self.assertIsNone(s.derniere_consultation)

    def test_une_source_non_consultee_n_a_pas_de_priorite(self):
        """On ne classe pas ce qu'on n'a pas mesuré."""
        r = Registre()
        self.assertIsNone(r.declarer("bda", "publics", "api").rendement.priorite())

    def test_une_source_consultee_porte_une_date(self):
        r = Registre()
        s = r.declarer("bda", "publics", "api")
        s.consultee(42)
        self.assertIs(s.etat, Etat.ACTIVE)
        self.assertIsNotNone(s.derniere_consultation)

    def test_le_rapport_annonce_ce_qui_n_a_jamais_ete_consulte(self):
        r = Registre()
        r.declarer("ted", "publics", "api")
        self.assertIn("JAMAIS été consultées", r.rapport())

    def test_une_petite_source_productive_passe_devant_une_grosse_sterile(self):
        r = Registre()
        grosse = r.declarer("grosse", "publics", "api")
        grosse.consultee(500); grosse.rendement.retenues = 2
        petite = r.declarer("petite", "prive", "navigation")
        petite.consultee(30); petite.rendement.retenues = 15
        self.assertEqual(r.par_priorite()[0].nom, "petite")


# ══════════════ §11 — corridors
class Corridors(unittest.TestCase):
    def setUp(self):
        self.g = Geographie(GEO)

    def test_pays_bas_vers_belgique_est_le_modele(self):
        r = self.g.evaluer(["NL"], ["BE"])
        self.assertIs(r.zone, Zone.CORRIDOR)
        self.assertTrue(r.corridor_eprouve)

    def test_toute_l_europe_vers_la_belgique_reste_ouvert(self):
        for p in ("FR", "DE", "LU", "ES", "IT", "PL"):
            with self.subTest(pays=p):
                self.assertIs(self.g.evaluer([p], ["BE"]).zone, Zone.CORRIDOR)

    def test_france_vers_france_est_hors_modele(self):
        self.assertFalse(self.g.evaluer(["FR"], ["FR"]).compatible)

    def test_un_lieu_absent_ne_fait_pas_disparaitre_l_opportunite(self):
        self.assertTrue(self.g.evaluer([], []).compatible)


# ══════════════ §18 — la fiche
class LaFiche(unittest.TestCase):
    def test_elle_porte_tous_les_blocs_demandes(self):
        t = moteur().analyser(opp(acheteur="Commune", montant=200000, duree_mois=24,
                                  exigences={"vehicules_min": 12}), MAINTENANT).fiche.en_texte()
        for bloc in ("CLIENT", "SOURCE", "ZONE", "DATE", "VALEUR",
                     "CE QU'IL FAUT FAIRE", "POURQUOI C'EST INTÉRESSANT",
                     "CE QUE J'AI DÉJÀ", "CE QUI ME MANQUE", "COMMENT COMBLER",
                     "NIVEAU", "ÉCONOMIE", "ACTION"):
            self.assertIn(bloc, t)

    def test_elle_nomme_le_lot_et_son_marche_parent(self):
        m = eclater(opp(ref_source="M-9", lots=[LotBrut(numero="3", intitule="Déménagement",
                                                        texte="déménagement de matériel")]))[0]
        t = moteur().analyser(m, MAINTENANT).fiche.en_texte()
        self.assertIn("LOT 3", t)
        self.assertIn("M-9", t)

    def test_un_montant_absent_n_est_jamais_invente(self):
        t = moteur().analyser(opp(montant=None), MAINTENANT).fiche.en_texte()
        self.assertIn("NON PUBLIÉ", t)
        self.assertNotIn("0 EUR", t)

    def test_elle_porte_une_action_unique(self):
        t = moteur().analyser(opp(), MAINTENANT).fiche.en_texte()
        self.assertIn("ACTION        👉", t)


# ══════════════ garanties d'envoi et déduplication
class Garanties(unittest.TestCase):
    def test_le_meme_besoin_vu_deux_fois_ne_notifie_qu_une_fois(self):
        cx = ouvrir(":memory:")
        a = opp(source="google", ref_source="G1", acheteur="CHU")
        b = opp(source="bda", ref_source="B1", acheteur="CHU")
        bilan = traiter(cx, moteur(), [a, b], maintenant_dt=MAINTENANT)
        self.assertEqual(bilan.doublons, 1)
        self.assertEqual(cx.execute("SELECT count(*) c FROM envois").fetchone()["c"], 1)

    def test_un_envoi_interrompu_n_est_jamais_reemis(self):
        cx = ouvrir(":memory:")
        envoi.mettre_en_file(cx, "bda", "R1", "corps")
        cx.execute("UPDATE envois SET etat='en_cours'")
        self.assertEqual(envoi.reprendre_interrompus(cx), 1)
        self.assertEqual(len(envoi.a_envoyer(cx)), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ══════════════ §9 — aucune source hiérarchisée d'avance
class AucuneHierarchieDeSource(unittest.TestCase):
    def test_toutes_les_priorites_initiales_sont_non_mesurees(self):
        cat = cfg("config/sources.yaml")["categories"]
        self.assertEqual({v["priorite_initiale"] for v in cat.values()}, {None})

    def test_le_score_ne_depend_pas_de_la_source(self):
        """Un appel d'offres public n'est ni meilleur ni moins bon par nature."""
        commun = dict(intitule="Transport de colis", texte="transport de marchandises",
                      montant=200000, duree_mois=24, cadence="quotidienne")
        public = moteur().analyser(opp(source="bda", secteur_acheteur="public", **commun),
                                   MAINTENANT).score.total
        prive = moteur().analyser(opp(source="google", secteur_acheteur="privé", **commun),
                                  MAINTENANT).score.total
        self.assertEqual(public, prive)


# ══════════════ §6 — groupement et consortium
class GroupementEtSousTraitance(unittest.TestCase):
    def _classer(self, vehicules):
        return moteur().analyser(opp(exigences={"vehicules_min": vehicules}), MAINTENANT)

    def test_une_part_suffisante_ouvre_un_groupement(self):
        r = self._classer(30)
        self.assertIs(r.classement.action, Action.PROPOSER_GROUPEMENT)
        self.assertTrue(any("%" in x for x in r.classement.raisons))

    def test_une_part_trop_faible_renvoie_a_la_sous_traitance(self):
        self.assertIs(self._classer(200).classement.action, Action.PROPOSER_SOUS_TRAITANCE)

    def test_la_part_couverte_est_chiffree_et_jamais_supposee(self):
        r = self._classer(50)
        self.assertAlmostEqual(r.bilan.part_couverte(), 16 / 50, places=3)

    def test_aucun_de_ces_cas_n_est_un_rejet(self):
        for n in (30, 50, 200, 1000):
            with self.subTest(vehicules=n):
                self.assertIsNot(self._classer(n).classement.type, Type.REJET)


# ══════════════ §12 — fusion public / privé
class FusionMultiSources(unittest.TestCase):
    def _o(self, **kw):
        base = dict(source="bda", ref_source="R", intitule="Transport de colis",
                    texte="", provenances=[])
        base.update(kw)
        return Opportunite(**base)

    def test_le_meme_besoin_formule_autrement_est_fusionne(self):
        idx = Index()
        a = self._o(source="bda", ref_source="B1", acheteur="Commune de Namur",
                    intitule="Transport et distribution de colis",
                    provenances=[{"source": "bda", "url": "https://x.be/1"}])
        idx.ajouter(a)
        b = self._o(source="google", ref_source="G1", acheteur="Commune de Namur",
                    intitule="Distribution, transport de colis — commune",
                    provenances=[{"source": "google", "url": "https://y.be/2"}])
        self.assertIsNotNone(idx.chercher(b))

    def test_un_autre_acheteur_n_est_jamais_fusionne(self):
        idx = Index()
        idx.ajouter(self._o(ref_source="B1", acheteur="Commune de Namur"))
        self.assertIsNone(idx.chercher(self._o(ref_source="G1", acheteur="Ville de Liège")))

    def test_la_meme_page_est_reconnue_malgre_www_et_parametres(self):
        idx = Index()
        idx.ajouter(self._o(ref_source="B1", acheteur="X",
                            provenances=[{"source": "bda", "url": "https://a.be/n/1"}]))
        autre = self._o(ref_source="G1", acheteur=None, intitule="Titre différent",
                        provenances=[{"source": "google",
                                      "url": "https://www.a.be/n/1?utm_source=z"}])
        self.assertIsNotNone(idx.chercher(autre))

    def test_la_fusion_cumule_les_provenances_et_comble_les_trous(self):
        a = self._o(ref_source="B1", acheteur="Commune",
                    provenances=[{"source": "bda", "url": "https://x.be/1"}])
        b = self._o(source="google", ref_source="G1", acheteur="Commune",
                    contact="achats@commune.be",
                    provenances=[{"source": "google", "url": "https://y.be/2"}])
        fusionner(a, b)
        self.assertEqual(a.contact, "achats@commune.be")
        self.assertEqual(libelle_provenances(a), "BDA + GOOGLE")


# ══════════════ §11 — registre d'entreprises et boucle
class RegistreEntreprises(unittest.TestCase):
    def test_un_titulaire_entre_au_registre_et_est_surveille(self):
        r = RegistreEnt()
        e = r.depuis_attribution(opp(attribue=True, titulaire="Grand Opérateur",
                                     montant=2400000))
        self.assertIs(e.etat, EtatEnt.SURVEILLEE)
        self.assertEqual(e.marches_gagnes, 1)

    def test_une_entreprise_peut_etre_surveillee_manuellement(self):
        r = RegistreEnt()
        e = r.surveiller("Transports Dupont", domaine="dupont.be")
        self.assertIs(e.etat, EtatEnt.SURVEILLEE)
        self.assertIn(e, r.a_surveiller())

    def test_une_entreprise_ecartee_garde_son_motif(self):
        r = RegistreEnt()
        r.surveiller("X", domaine="x.be")
        r.ecarter("x.be", "robots.txt interdit la lecture")
        self.assertNotIn(r.entreprises["x.be"], r.a_surveiller())
        self.assertEqual(r.entreprises["x.be"].motif_ecart,
                         "robots.txt interdit la lecture")

    def test_un_nom_d_entreprise_n_est_jamais_invente(self):
        self.assertIsNone(nom_probable("une phrase sans raison sociale"))
        self.assertEqual(nom_probable("Logistique BE SRL recherche"), "Logistique BE SRL")

    def test_la_boucle_descend_par_entreprise_et_respecte_son_budget(self):
        from types import SimpleNamespace
        g = Generateur(DECOUVERTE)
        reg = RegistreEnt()

        def chercher(_):
            return [SimpleNamespace(titre="Logistique BE SRL cherche un transporteur",
                                    url="https://logistiquebe.be/a", extrait="")]

        trace = Boucle(g, reg, profondeur_max=2, budget=6).parcourir(
            chercher, requetes_generales=g.generer(2), analyser=lambda r: len(r))
        self.assertEqual(trace.budget_utilise, 6)
        self.assertTrue(any(e.profondeur == 1 for e in trace.etapes))


# ══════════════ §10 — DÉVELOPPER enrichi
class MemoireDesAttributions(unittest.TestCase):
    def test_l_echeance_est_calculee_quand_la_duree_est_publiee(self):
        a = memoriser(opp(attribue=True, titulaire="X", duree_mois=36,
                          attribue_le="2026-09-01"))
        self.assertEqual(a.fiabilite, "calculée")
        self.assertTrue(str(a.remise_en_concurrence).startswith("2029"))

    def test_sans_duree_rien_n_est_estime(self):
        a = memoriser(opp(attribue=True, titulaire="X", duree_mois=None))
        self.assertIsNone(a.remise_en_concurrence)
        self.assertIn("NON PUBLIÉE", a.commentaire)

    def test_la_taille_du_titulaire_n_est_pas_devinee_sans_montant(self):
        a = memoriser(opp(attribue=True, titulaire="X", montant=None))
        self.assertEqual(a.taille_apparente, "A_VERIFIER")

    def test_un_gros_montant_signale_un_besoin_probable_de_sous_traitants(self):
        a = memoriser(opp(attribue=True, titulaire="X", montant=6000000))
        self.assertIn("probable", a.besoin_sous_traitance)


# ══════════════ non-régression : un identifiant manquant ne fusionne rien
class ReferenceManquante(unittest.TestCase):
    def _ad(self):
        from radar.adaptateur import Adaptateur
        return Adaptateur.depuis_config(cfg("sources/ted.yaml"))

    def test_deux_avis_sans_identifiant_gardent_des_references_distinctes(self):
        """Deux références vides ont la même empreinte et se fusionneraient en
        silence — c'est-à-dire feraient disparaître une opportunité."""
        from radar.adaptateur import vers_opportunite
        ad = self._ad()
        a = vers_opportunite(ad, {"title": {"fra": "Marché A"}}, "ted")
        b = vers_opportunite(ad, {"title": {"fra": "Marché B"}}, "ted")
        self.assertNotEqual(a.ref_source, b.ref_source)
        self.assertTrue(a.ref_source.startswith("SANS-REF-"))

    def test_la_reference_derivee_est_stable(self):
        from radar.adaptateur import vers_opportunite
        ad = self._ad()
        charge = {"title": {"fra": "Marché A"}, "buyer": {"name": "X"}}
        self.assertEqual(vers_opportunite(ad, charge, "ted").ref_source,
                         vers_opportunite(ad, dict(charge), "ted").ref_source)

    def test_les_lots_d_un_meme_marche_ne_fusionnent_jamais(self):
        cx = ouvrir(":memory:")
        marche = opp(ref_source="M-1", intitule="Marché à lots",
                     plateforme="https://x.be/marche/1",
                     lots=[LotBrut(numero="1", intitule="Déménagement de bureaux",
                                   texte="déménagement et manutention"),
                           LotBrut(numero="2", intitule="Transport de matériel",
                                   texte="transport de marchandises")])
        b = traiter(cx, moteur(), [marche], maintenant_dt=MAINTENANT)
        self.assertEqual(b.doublons, 0)
        self.assertEqual(cx.execute("SELECT count(*) c FROM envois").fetchone()["c"], 2)
