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
from radar.decouverte import Generateur
from radar.moteurs_recherche import (
    Brave, Google, RechercheIndisponible, depuis_environnement)
from radar.geographie import Geographie, Zone
from radar.lots import eclater
from radar.modele import LotBrut, Opportunite
from radar.boucle import Boucle
from radar.comptes import Livre, ReconciliationImpossible
from radar.deduplication import Confiance, Index, fusionner, libelle_provenances
from radar.mode import CollecteInvalide, Mode, estampiller, verifier as verifier_collecte
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

    def test_sans_cle_aucun_moteur_ne_simule_une_recherche(self):
        for moteur in (Google(), Brave()):
            with self.subTest(moteur=moteur.nom):
                self.assertFalse(moteur.disponible)
                self.assertIn("CLÉ ABSENTE", moteur.motif_indisponibilite)
                with self.assertRaises(RechercheIndisponible):
                    moteur.rechercher(self.g.generer(1)[0])

    def test_le_metier_ne_depend_d_aucun_moteur_particulier(self):
        """Brave remplace Google sans qu'une ligne du moteur métier change."""
        registre = depuis_environnement({"BRAVE_API_KEY": "x"})
        self.assertEqual(registre.disponible().nom, "brave")

    def test_aucun_moteur_disponible_est_dit_explicitement(self):
        registre = depuis_environnement({})
        self.assertIsNone(registre.disponible())
        self.assertIn("Aucun moteur disponible", registre.rapport())

    def test_le_radar_fonctionne_sans_aucun_moteur_de_recherche(self):
        """Aucune source n'est indispensable : sans Google, le reste tourne."""
        cx = ouvrir(":memory:")
        b = traiter(cx, moteur(), [opp()], maintenant_dt=MAINTENANT)
        self.assertEqual(b.capter, 1)


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
        for bloc in ("NATURE", "CLIENT", "VU SUR", "ZONE", "DATE", "VALEUR",
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

    def test_le_meme_besoin_sans_date_commune_reste_un_doublon_possible(self):
        """Similarité sémantique SEULE : on relie, on ne fusionne pas."""
        idx = Index()
        a = self._o(source="bda", ref_source="B1", acheteur="Commune de Namur",
                    intitule="Transport et distribution de colis",
                    provenances=[{"source": "bda", "url": "https://x.be/1"}])
        idx.ajouter(a)
        b = self._o(source="google", ref_source="G1", acheteur="Commune de Namur",
                    intitule="Distribution, transport de colis — commune",
                    provenances=[{"source": "google", "url": "https://y.be/2"}])
        r = idx.rapprocher(b)
        self.assertIs(r.confiance, Confiance.POSSIBLE)
        self.assertFalse(r.confiance.fusionne)
        self.assertIsNone(idx.chercher(b), "aucune fusion sur la similarité seule")

    def test_le_meme_besoin_avec_meme_echeance_est_un_doublon_probable(self):
        idx = Index()
        idx.ajouter(self._o(source="bda", ref_source="B1", acheteur="Commune de Namur",
                            intitule="Transport et distribution de colis",
                            echeance_brute="2026-11-25"))
        r = idx.rapprocher(self._o(source="google", ref_source="G1",
                                   acheteur="Commune de Namur",
                                   intitule="Transport, distribution de colis",
                                   echeance_brute="2026-11-25"))
        self.assertIs(r.confiance, Confiance.PROBABLE)
        self.assertTrue(r.confiance.fusionne)

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


# ══════════════ §13 — DEMO et RÉEL impossibles à confondre
class ModeReel(unittest.TestCase):
    FIXTURE = {"title": "Marché fictif", "id": "DEMO-1"}

    def test_une_fixture_passe_en_demo(self):
        self.assertIsNone(verifier_collecte(self.FIXTURE, Mode.DEMO))

    def test_une_fixture_est_refusee_en_reel(self):
        """C'est le verrou : les dix faux avis BDA n'auraient pas pu entrer."""
        with self.assertRaises(CollecteInvalide):
            verifier_collecte(self.FIXTURE, Mode.REEL)

    def test_une_ligne_reellement_collectee_passe_en_reel(self):
        vrai = estampiller({"id": "2026/S-1"}, source="ted",
                           reference="https://ted.europa.eu/notice/1")
        self.assertEqual(verifier_collecte(vrai, Mode.REEL).source, "ted")

    def test_une_ligne_modifiee_apres_collecte_est_refusee(self):
        vrai = estampiller({"id": "2026/S-1"}, source="ted", reference="https://x/1")
        with self.assertRaises(CollecteInvalide):
            verifier_collecte({**vrai, "id": "TRAFIQUÉ"}, Mode.REEL)

    def test_les_deux_modes_n_utilisent_jamais_la_meme_base(self):
        self.assertNotEqual(Mode.DEMO.base_par_defaut, Mode.REEL.base_par_defaut)

    def test_la_chaine_refuse_les_fixtures_en_mode_reel(self):
        cx = ouvrir(":memory:")
        b = traiter(cx, moteur(), [opp()], maintenant_dt=MAINTENANT, mode=Mode.REEL)
        self.assertEqual(b.capter + b.developper, 0)
        self.assertTrue(b.livre.illisibles)


# ══════════════ §14 — le livre de comptes
class LivreDeComptes(unittest.TestCase):
    def _livre(self, **kw):
        base = dict(brutes=97, normalisees=95, lots_ajoutes=20, doublons_certains=8,
                    doublons_probables=4, capter=40, developper=15)
        base.update(kw)
        l = Livre(**base)
        l.illisible("date illisible"); l.illisible("date illisible")
        for _ in range(48):
            l.rejeter("marché de fourniture")
        return l

    def test_un_cycle_coherent_se_reconcilie(self):
        self._livre().verifier()

    def test_une_disparition_sans_motif_fait_echouer_le_cycle(self):
        """Le bug des sept opportunités perdues serait maintenant impossible."""
        with self.assertRaises(ReconciliationImpossible) as ctx:
            self._livre(capter=33).verifier()
        self.assertIn("7 opportunité", str(ctx.exception))

    def test_des_brutes_non_ventilees_font_echouer_le_cycle(self):
        with self.assertRaises(ReconciliationImpossible):
            Livre(brutes=100, normalisees=95, capter=95).verifier()

    def test_un_doublon_possible_ne_se_soustrait_pas_du_total(self):
        """Il n'est pas fusionné : il ne doit donc pas manquer à l'arrivée."""
        l = self._livre(doublons_possibles=6)
        l.verifier()
        self.assertEqual(l.total_fusionnes, 12)

    def test_le_cycle_reel_se_reconcilie_sur_donnees_estampillees(self):
        cx = ouvrir(":memory:")
        charges = [estampiller({"id": f"R{i}"}, source="ted", reference=f"https://x/{i}")
                   for i in range(3)]
        lot = [opp(ref_source=f"R{i}", intitule=f"Transport de colis {i}", brut=c)
               for i, c in enumerate(charges)]
        b = traiter(cx, moteur(), lot, maintenant_dt=MAINTENANT, mode=Mode.REEL)
        b.livre.verifier()
        self.assertEqual(b.capter + b.developper, 3)


# ══════════════ non-régression : avis hors schéma
class AvisHorsSchema(unittest.TestCase):
    """20 % de données hors schéma ne doivent faire disparaître AUCUN avis."""

    def _o(self, ref):
        return Opportunite(source="ted", ref_source=ref, intitule="(sans intitulé)")

    def test_deux_avis_illisibles_ne_fusionnent_pas(self):
        from radar.deduplication import empreinte_stricte
        self.assertNotEqual(empreinte_stricte(self._o("SANS-REF-a")),
                            empreinte_stricte(self._o("SANS-REF-b")))

    def test_la_fusion_inter_sources_reste_intacte(self):
        from radar.deduplication import empreinte_stricte
        a = opp(source="ted", ref_source="T1", acheteur="CHU")
        b = opp(source="bda", ref_source="B1", acheteur="CHU")
        self.assertEqual(empreinte_stricte(a), empreinte_stricte(b))

    def test_un_avis_hors_schema_est_conserve_pas_perdu(self):
        cx = ouvrir(":memory:")
        lot = [opp(ref_source="OK", intitule="Transport de colis"),
               self._o("SANS-REF-a"), self._o("SANS-REF-b")]
        b = traiter(cx, moteur(), lot, maintenant_dt=MAINTENANT)
        b.livre.verifier()
        n = cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        self.assertEqual(n, 3, "les trois avis doivent exister en base")


# ══════════════ conservation des incidents
class Incidents(unittest.TestCase):
    def test_une_fixture_refusee_en_reel_est_conservee_avec_son_motif(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp()], maintenant_dt=MAINTENANT, mode=Mode.REEL)
        l = cx.execute("SELECT * FROM incidents").fetchone()
        self.assertIsNotNone(l, "l'avis refusé doit être conservé, pas perdu")
        self.assertEqual(l["etape"], "collecte")
        self.assertIn("preuve de collecte", l["motif"])

    def test_le_contenu_brut_de_l_incident_est_conserve(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(brut={"titre": "avis original"})],
                maintenant_dt=MAINTENANT, mode=Mode.REEL)
        charge = cx.execute("SELECT charge FROM incidents").fetchone()["charge"]
        self.assertIn("avis original", charge)


# ══════════════ le rapport ne force jamais un TOP
class RapportDeMesure(unittest.TestCase):
    def test_sans_opportunite_le_rapport_le_dit_au_lieu_d_en_inventer(self):
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        texte = construire(cx, Mode.DEMO).en_texte()
        self.assertIn("AUCUNE OPPORTUNITÉ FORTE DÉTECTÉE", texte)

    def test_le_rapport_porte_son_mode_en_tete(self):
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        self.assertIn("DONNÉES FICTIVES", construire(cx, Mode.DEMO).en_texte())
        self.assertIn("MODE : RÉEL", construire(cx, Mode.REEL).en_texte())


# ══════════════ §15 — jamais une boîte noire
class SeizeQuestions(unittest.TestCase):
    """Chaque opportunité doit pouvoir dire pourquoi elle est là, ce qui manque
    et quelle action suit. Ces tests avaient disparu lors d'une réécriture :
    la règle s'appliquait sans filet."""

    def test_le_journal_repond_aux_seize_questions(self):
        j = moteur().analyser(opp(acheteur="Commune", montant=120000, duree_mois=24),
                              MAINTENANT).journal
        numerotees = [q for q in j.reponses if q[0].isdigit()]
        self.assertEqual(len(numerotees), 16)

    def test_ce_qui_ne_peut_pas_etre_repondu_vaut_a_verifier(self):
        """Jamais une réponse inventée à la place d'une donnée absente."""
        j = moteur().analyser(opp(acheteur=None, montant=None), MAINTENANT).journal
        self.assertIn("1. qui achète ?", j.sans_reponse())

    def test_le_journal_dit_si_je_peux_etre_titulaire(self):
        direct = moteur().analyser(opp(), MAINTENANT).journal
        gros = moteur().analyser(opp(exigences={"vehicules_min": 200}), MAINTENANT).journal
        self.assertIn("oui", direct.reponses["12. puis-je être titulaire ?"])
        self.assertEqual(gros.reponses["12. puis-je être titulaire ?"], "non")

    def test_le_journal_nomme_l_action_suivante(self):
        j = moteur().analyser(opp(), MAINTENANT).journal
        self.assertTrue(j.reponses["16. quelle action maintenant ?"])

    def test_le_journal_est_conserve_en_base(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(acheteur="Commune")], maintenant_dt=MAINTENANT)
        journal = cx.execute("SELECT journal FROM opportunites").fetchone()["journal"]
        self.assertIn("qui achète", journal)

    def test_chaque_rejet_porte_son_motif(self):
        """Pour un rejet aussi, on doit pouvoir comprendre pourquoi."""
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(ref_source="ADR", exigences={"adr": True})],
                maintenant_dt=MAINTENANT)
        l = cx.execute("SELECT type, motif FROM opportunites").fetchone()
        self.assertEqual(l["type"], "REJET")
        self.assertTrue(l["motif"], "un rejet sans motif est une boîte noire")


# ══════════════ ce que la répétition générale a trouvé avant les vraies données
class DonneesReellesMalFormees(unittest.TestCase):
    """Trois défauts trouvés en faisant passer un lot volontairement hostile.

    Chacun aurait coûté cher sur un vrai fichier TED : le premier faisait
    perdre TOUT le cycle, le deuxième déclarait exécutable un lot qui ne
    l'était pas, le troisième bruitait la fiche jusqu'à la rendre illisible.
    """

    @staticmethod
    def _ted():
        from radar.adaptateur import Adaptateur
        cfg = yaml.safe_load((RACINE / "sources" / "ted.yaml").read_text(encoding="utf-8"))
        return Adaptateur.depuis_config(cfg), cfg

    def _lire(self, charge):
        from radar.adaptateur import vers_opportunite
        ad, cfg = self._ted()
        return vers_opportunite(ad, charge, "ted", {"secteur": cfg.get("secteur_par_defaut")})

    def test_un_montant_publie_en_texte_ne_fait_pas_perdre_le_cycle(self):
        """« 120 000 » est un montant, pas une panne."""
        o = self._lire({"publication-number": "X1", "title": {"fra": "Transport"},
                        "estimated-value": {"amount": "120 000", "currency": "EUR"}})
        self.assertEqual(o.montant, 120000.0)
        self.assertEqual(o.champs_illisibles, {})

    def test_un_nombre_illisible_est_signale_jamais_mis_a_zero(self):
        o = self._lire({"publication-number": "X2", "title": {"fra": "Transport"},
                        "duration-months": "douze"})
        self.assertIsNone(o.duree_mois, "une durée illisible ne vaut pas zéro")
        self.assertIn("durée", o.champs_illisibles)
        self.assertEqual(o.champs_illisibles["durée"], "douze")

    def test_un_champ_illisible_apparait_dans_la_fiche(self):
        o = self._lire({"publication-number": "X3", "title": {"fra": "Transport de colis"},
                        "duration-months": "douze",
                        "place-of-delivery": {"country": "BE"}})
        o.echeance_brute = OUVERT
        fiche = moteur().analyser(o, MAINTENANT).fiche.en_texte()
        self.assertIn("illisible", fiche)
        self.assertIn("douze", fiche)

    def test_une_exigence_de_lot_est_lue_avec_la_carte_de_la_source(self):
        """Les exigences d'un lot sont publiées comme celles du marché.
        Les lire avec les seules clés de premier niveau les perdait."""
        o = self._lire({"publication-number": "X4", "title": {"fra": "Marché à lots"},
                        "lots": [{"numero": "3", "intitule": "Distribution régionale",
                                  "requirements": {"min-vehicles": 12}}]})
        self.assertEqual(o.lots[0].exigences, {"vehicules_min": 12})

    def test_un_lot_trop_gros_n_est_jamais_dit_executable_tel_quel(self):
        cx = ouvrir(":memory:")
        o = self._lire({"publication-number": "X5", "title": {"fra": "Marché à lots"},
                        "classification-cpv": ["60000000"],
                        "place-of-delivery": {"country": "BE"},
                        "lots": [{"numero": "3", "intitule": "Distribution régionale",
                                  "requirements": {"min-vehicles": 12}}]})
        o.echeance_brute = OUVERT
        traiter(cx, moteur(), [o], maintenant_dt=MAINTENANT)
        l = cx.execute("SELECT type, fiche FROM opportunites").fetchone()
        self.assertEqual(l["type"], "RENFORCEMENT")
        self.assertIn("à louer", l["fiche"])

    def test_les_manques_du_test_a_construire_ne_polluent_pas_un_lot_de_transport(self):
        """« aucune formation mentionnée » n'a rien à faire sur une fiche
        bloquée par six véhicules : le bruit fabrique des boîtes noires."""
        o = self._lire({"publication-number": "X6",
                        "title": {"fra": "Distribution régionale"},
                        "classification-cpv": ["60000000"],
                        "place-of-delivery": {"country": "BE"},
                        "requirements": {"min-vehicles": 12}})
        o.echeance_brute = OUVERT
        fiche = moteur().analyser(o, MAINTENANT).fiche.en_texte()
        self.assertIn("12 véhicules exigés", fiche)
        self.assertNotIn("aucune formation mentionnée", fiche)


class CollecteurTed(unittest.TestCase):
    def test_un_avis_sans_identifiant_recoit_une_reference_derivee(self):
        from outils.collecter_ted import reference_de
        ref = reference_de({"title": {"fra": "Transport"}})
        self.assertTrue(ref.startswith("SANS-REF-"))

    def test_deux_avis_sans_identifiant_gardent_des_references_distinctes(self):
        """Le bug des sept opportunités disparues, côté collecteur cette fois."""
        from outils.collecter_ted import reference_de
        a = reference_de({"title": {"fra": "Transport de colis"}})
        b = reference_de({"title": {"fra": "Transport de palettes"}})
        self.assertNotEqual(a, b)

    def test_l_identifiant_officiel_prime_sur_la_reference_derivee(self):
        from outils.collecter_ted import reference_de
        self.assertEqual(reference_de({"publication-number": "123-2026"}), "123-2026")


class RepetitionGenerale(unittest.TestCase):
    """Le trajet complet sur un lot hostile. C'est la répétition que le vrai
    fichier TED jouera pour de bon."""

    def test_le_trajet_complet_ne_perd_aucune_ligne(self):
        from outils.repetition_pipeline import lot_hostile, _passer
        cx, b = _passer(lot_hostile(), Mode.DEMO)
        self.assertEqual(b.lus, len(lot_hostile()))
        self.assertEqual(b.livre.ecart(), 0)

    def test_aucune_fixture_n_entre_dans_le_flux_reel(self):
        from outils.repetition_pipeline import lot_hostile, _passer
        cx, b = _passer(lot_hostile(), Mode.REEL)
        self.assertEqual(b.livre.sorties, 0)
        conserves = cx.execute("SELECT count(*) c FROM incidents").fetchone()["c"]
        self.assertEqual(conserves, len(lot_hostile()),
                         "un refus doit être conservé, jamais effacé")


class RapportPremiereValidation(unittest.TestCase):
    """Ce que le premier rapport réel doit porter, section par section."""

    def _rapport(self):
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        o = opp(acheteur="Commune", montant=240000, duree_mois=24)
        traiter(cx, moteur(), [o], maintenant_dt=MAINTENANT)
        return construire(cx, Mode.DEMO,
                          etats_sources={"ted": {"etat": "JAMAIS CONSULTÉE", "motif": None},
                                         "google": {"etat": "NON DISPONIBLE",
                                                    "motif": "clé absente"}},
                          cible={"montant_total_confortable_max": 1500000})

    def test_une_source_jamais_consultee_est_nommee_pas_omise(self):
        texte = self._rapport().en_texte(avec_fiches=False)
        self.assertIn("JAMAIS CONSULTÉE", texte)
        self.assertIn("ted", texte)

    def test_une_source_indisponible_dit_pourquoi(self):
        texte = self._rapport().en_texte(avec_fiches=False)
        self.assertIn("NON DISPONIBLE", texte)
        self.assertIn("clé absente", texte)

    def test_les_selections_sont_toujours_presentes_meme_vides(self):
        texte = self._rapport().en_texte(avec_fiches=False)
        for titre in ("PRÈS DU DÉPÔT", "CORRIDOR ÉTRANGER → BE",
                      "PETITS CONTRATS À MA TAILLE",
                      "TROP GROS SEUL — RENFORT OU PARTENARIAT",
                      "À DÉVELOPPER — MARCHÉS DÉJÀ ATTRIBUÉS"):
            self.assertIn(titre, texte)

    def test_une_marge_non_mesuree_est_comptee_jamais_presentee_comme_nulle(self):
        r = self._rapport()
        self.assertEqual(r.marge_non_mesuree, 1)
        self.assertIn("NON MESURÉE ne veut pas dire nulle",
                      r.en_texte(avec_fiches=False))

    def test_les_lots_sont_comptes_avec_leur_marche_parent(self):
        r = self._rapport()
        self.assertIn("lots", r.lots)
        self.assertIn("marches", r.lots)


class SondageAvantConstruction(unittest.TestCase):
    """`sonder` est l'étape 2 du jour où les vraies données arriveront. Elle
    tournait sur les quatre anciennes catégories et sur un attribut disparu :
    elle levait une exception au lieu de mesurer."""

    def _lot(self):
        return [opp(ref_source="M1", acheteur="Commune", montant=240000),
                opp(ref_source="M2", exigences={"vehicules_min": 12}),
                opp(ref_source="M3", intitule="Fourniture de papier",
                    texte="Achat de ramettes")]

    def test_sonder_mesure_sans_lever_d_exception(self):
        from radar.sondage import sonder
        s = sonder(moteur(), self._lot(), "ted", MAINTENANT)
        self.assertEqual(s.total, 3)
        self.assertTrue(s.rapport())

    def test_sonder_annonce_les_memes_categories_que_la_chaine(self):
        """Un sondage qui promet autre chose que le traitement est un piège."""
        from radar.sondage import sonder
        lot = self._lot()
        s = sonder(moteur(), lot, "ted", MAINTENANT)
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), self._lot(), maintenant_dt=MAINTENANT)
        en_base = {l["type"]: l["n"] for l in cx.execute(
            "SELECT type, count(*) n FROM opportunites GROUP BY type")}
        self.assertEqual(dict(s.par_type), en_base)

    def test_sonder_compte_les_lots_pas_seulement_les_marches(self):
        from radar.sondage import sonder
        marche = opp(ref_source="M4", lots=[
            LotBrut(numero="1", intitule="Transport de mobilier"),
            LotBrut(numero="2", intitule="Transport de palettes")])
        s = sonder(moteur(), [marche], "ted", MAINTENANT)
        self.assertEqual(s.total, 1)
        self.assertEqual(s.lots_analyses, 2)

    def test_un_marche_trop_gros_reste_exploitable_dans_le_verdict(self):
        """« Exploitable » ne veut pas dire « exécutable tel quel » : un marché
        à renforcer compte, il ne se jette pas."""
        from radar.sondage import sonder
        s = sonder(moteur(), [opp(ref_source="M5", exigences={"vehicules_min": 12})],
                   "ted", MAINTENANT)
        self.assertIn("1 opportunité(s) exploitable(s)", s.rapport())


# ══════════════ LE RADAR COMMERCIAL — le centre n'est ni la source ni l'appel d'offres
def _charger(fichier, source):
    """Charge une fixture par son adaptateur déclaré. Aucun format n'est
    privilégié : c'est le même chemin pour les huit."""
    from outils.radar_commercial import charger
    return charger(fichier, source)


class RadarCommercial(unittest.TestCase):
    """Huit formes de besoin, un seul moteur.

    Un marché européen, un marché belge, un résultat de moteur de recherche,
    une page d'entreprise, deux signaux, une tournée de bourse de fret, un
    marché attribué et un métier nouveau. Aucun n'est secondaire.
    """

    def _analyser(self, fichier, source):
        cx = ouvrir(":memory:")
        opportunites = _charger(fichier, source)
        traiter(cx, moteur(), opportunites, maintenant_dt=MAINTENANT)
        return cx.execute(
            "SELECT type, moteur, action, score, intitule FROM opportunites"
            " ORDER BY score DESC").fetchall()

    # ── 1 à 7 : chaque format entre dans le moteur ──────────────────────
    def test_1_un_marche_public_europeen_est_une_opportunite(self):
        l = self._analyser("ted.json", "ted")[0]
        self.assertEqual(l["type"], "DIRECT")
        self.assertEqual(l["moteur"], "CAPTER")

    def test_2_un_besoin_prive_trouve_par_un_moteur_de_recherche_est_une_opportunite(self):
        """« Nous recherchons un partenaire transport » vaut un avis de marché."""
        l = self._analyser("google.json", "google")[0]
        self.assertNotEqual(l["type"], "REJET")
        self.assertEqual(l["moteur"], "CAPTER")

    def test_3_un_marche_belge_est_une_opportunite(self):
        l = self._analyser("bda.json", "bda")[0]
        self.assertNotEqual(l["type"], "REJET")

    def test_4_une_page_d_entreprise_est_une_opportunite(self):
        """Ni CPV, ni référence officielle, ni montant, ni échéance."""
        l = self._analyser("entreprise.json", "entreprise")[0]
        self.assertNotEqual(l["type"], "REJET")
        self.assertIn("CONTACTER", l["action"])

    def test_5_un_signal_d_emploi_est_un_signal_pas_un_contrat_certain(self):
        lignes = self._analyser("signaux.json", "signaux")
        for l in lignes:
            self.assertEqual(l["type"], "PROSPECT")
            self.assertNotIn("POSTULER", l["action"])

    def test_6_une_attribution_va_dans_developper_jamais_postuler(self):
        l = self._analyser("attribution.json", "ted")[0]
        self.assertEqual(l["moteur"], "DEVELOPPER")
        self.assertNotIn("POSTULER", l["action"])

    def test_7_un_metier_nouveau_avec_formation_passe_par_a_construire(self):
        l = self._analyser("nouveau-metier.json", "entreprise")[0]
        self.assertEqual(l["type"], "A_CONSTRUIRE")

    def test_7bis_une_tournee_de_bourse_de_fret_est_une_opportunite(self):
        l = self._analyser("bourse_fret.json", "bourse_fret")[0]
        self.assertNotEqual(l["type"], "REJET")
        self.assertEqual(l["moteur"], "CAPTER")

    # ── 8 : un même besoin vu sur trois sources = une opportunité ───────
    def test_8_un_meme_besoin_vu_sur_trois_sources_garde_ses_trois_provenances(self):
        cx = ouvrir(":memory:")
        commun = dict(intitule="Distribution de colis pour la ville de Namur",
                      texte="tournées quotidiennes de distribution",
                      acheteur="Ville de Namur", montant=540000,
                      echeance_brute=OUVERT, pays_livraison=["BE"])
        trois = [
            opp(source="ted", ref_source="T-1",
                provenances=[{"source": "ted", "url": "https://ex.eu/ted/1"}], **commun),
            opp(source="bda", ref_source="B-1",
                provenances=[{"source": "bda", "url": "https://ex.be/bda/1"}], **commun),
            opp(source="google", ref_source="G-1",
                provenances=[{"source": "google", "url": "https://ex.be/page"}], **commun),
        ]
        b = traiter(cx, moteur(), trois, maintenant_dt=MAINTENANT)
        n = cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        self.assertEqual(n, 1, "le même besoin ne doit produire qu'une opportunité")
        self.assertEqual(b.doublons, 2)
        fiche = cx.execute("SELECT fiche FROM opportunites").fetchone()["fiche"]
        for source in ("ted", "bda", "google"):
            self.assertIn(source, fiche, "chaque provenance reste visible")

    # ── 9 à 11 : aucune source n'est indispensable ──────────────────────
    def _sans(self, exclues):
        from outils.radar_commercial import LOTS
        cx = ouvrir(":memory:")
        m = moteur()
        for fichier, source in LOTS:
            if source in exclues:
                continue
            traiter(cx, m, _charger(fichier, source), maintenant_dt=MAINTENANT)
        return cx.execute("SELECT count(*) c FROM opportunites"
                          " WHERE type <> 'REJET'").fetchone()["c"]

    def test_9_ted_supprime_le_radar_continue(self):
        self.assertGreater(self._sans({"ted"}), 0)

    def test_10_google_supprime_le_radar_continue(self):
        self.assertGreater(self._sans({"google"}), 0)

    def test_11_une_seule_source_suffit_a_faire_tourner_le_moteur(self):
        from outils.radar_commercial import LOTS
        sources = {s for _, s in LOTS}
        for gardee in sorted(sources):
            with self.subTest(source=gardee):
                self.assertGreater(self._sans(sources - {gardee}), 0,
                                   f"le radar doit fonctionner avec « {gardee} » seule")

    # ── 12 et 13 : le score ignore la source ───────────────────────────
    def _identique(self, source):
        return opp(source=source, ref_source=f"X-{source}",
                   intitule="Distribution urbaine de marchandises",
                   texte="tournées quotidiennes de distribution urbaine",
                   acheteur="Client", montant=240000, duree_mois=24,
                   cadence="quotidienne", echeance_brute=OUVERT,
                   pays_livraison=["BE"], distance_depot_km=20)

    def test_12_meme_economie_source_differente_score_identique(self):
        scores = {s: moteur().analyser(self._identique(s), MAINTENANT).score.total
                  for s in ("ted", "google", "bda", "entreprise", "bourse_fret")}
        self.assertEqual(len(set(scores.values())), 1,
                         f"la source a influencé le score : {scores}")

    def test_13_meilleure_economie_source_differente_meilleur_score(self):
        """Google excellent > BDA moyen > TED mauvais. La source apporte
        l'information ; l'économie décide de la priorité."""
        excellent = opp(source="google", ref_source="G",
                        intitule="Distribution urbaine de marchandises",
                        texte="tournées quotidiennes de distribution urbaine",
                        acheteur="Client", montant=240000, duree_mois=36,
                        cadence="quotidienne", echeance_brute=OUVERT,
                        pays_livraison=["BE"], distance_depot_km=15)
        moyen = opp(source="bda", ref_source="B",
                    intitule="Distribution urbaine de marchandises",
                    texte="tournées de distribution urbaine",
                    acheteur="Client", montant=240000, duree_mois=12,
                    cadence="hebdomadaire", echeance_brute=OUVERT,
                    pays_livraison=["BE"], distance_depot_km=90)
        mauvais = opp(source="ted", ref_source="T",
                      intitule="Distribution urbaine de marchandises",
                      texte="tournées de distribution urbaine",
                      acheteur="Client", montant=240000, duree_mois=1,
                      cadence="ponctuelle", echeance_brute=OUVERT,
                      pays_livraison=["BE"], distance_depot_km=400,
                      km_annuels=90000)
        m = moteur()
        s = [m.analyser(o, MAINTENANT).score.total for o in (excellent, moyen, mauvais)]
        self.assertGreater(s[0], s[1], f"Google excellent doit battre BDA moyen : {s}")
        self.assertGreater(s[1], s[2], f"BDA moyen doit battre TED mauvais : {s}")

    # ── 14 : aucun mot-clé connu ne rejette jamais ─────────────────────
    def test_14_aucun_mot_cle_connu_ne_donne_jamais_un_rejet(self):
        inconnu = opp(source="google", ref_source="INC",
                      intitule="Prestation de zorblification des flux",
                      texte="Nous recherchons un prestataire pour la zorblification.",
                      acheteur="Entreprise", echeance_brute=OUVERT,
                      pays_livraison=["BE"], cpv=[])
        r = moteur().analyser(inconnu, MAINTENANT)
        self.assertIsNot(r.classement.type, Type.REJET)


class AucunAvantageAuxSourcesPubliques(unittest.TestCase):
    """Le biais le plus difficile à voir : un marché public portait un CPV
    générique qui confirmait le domaine, une page privée n'avait rien
    d'équivalent. La source décidait, en silence."""

    def test_le_domaine_se_confirme_par_cpv_ou_par_vocabulaire(self):
        from radar.activite import Ontologie
        o = Ontologie(yaml.safe_load((RACINE / "config/capacites.yaml").read_text(
            encoding="utf-8")), PROFIL["familles_actives"], PROFIL.get("familles_exclues"))
        par_cpv = o.analyser("Marché de services", ["60000000"])
        par_texte = o.analyser("Nous cherchons un transporteur pour nos livraisons", [])
        self.assertTrue(par_cpv.domaine_transport)
        self.assertTrue(par_texte.domaine_transport, "une page sans CPV reste du transport")

    def test_le_vocabulaire_de_domaine_ne_ratisse_pas_tout(self):
        from radar.activite import Ontologie
        o = Ontologie(yaml.safe_load((RACINE / "config/capacites.yaml").read_text(
            encoding="utf-8")), PROFIL["familles_actives"], PROFIL.get("familles_exclues"))
        self.assertFalse(o.analyser("Entretien des espaces verts et tonte", []).domaine_transport)

    def test_la_preuve_du_domaine_est_nommee_dans_la_fiche(self):
        o = opp(source="entreprise", ref_source="E1", cpv=[],
                intitule="Devenir partenaire transporteur",
                texte="Nous confions nos tournées à des transporteurs partenaires.",
                acheteur="PME", echeance_brute=OUVERT, pays_livraison=["BE"])
        self.assertIn("domaine reconnu", moteur().analyser(o, MAINTENANT).fiche.en_texte())


class NatureDeLInformation(unittest.TestCase):
    """FAIT, SIGNAL, HYPOTHÈSE — visible, jamais monnayable en points."""

    def test_un_besoin_publie_et_date_est_un_fait(self):
        from radar.nature import Nature, qualifier
        self.assertIs(qualifier(opp(acheteur="Commune", echeance_brute=OUVERT)),
                      Nature.FAIT)

    def test_une_page_sans_demandeur_ni_date_est_une_hypothese(self):
        from radar.nature import Nature, qualifier
        self.assertIs(qualifier(opp(acheteur=None, echeance_brute=None,
                                    date_demarrage=None)), Nature.HYPOTHESE)

    def test_un_marche_attribue_est_un_signal(self):
        from radar.nature import Nature, qualifier
        self.assertIs(qualifier(opp(attribue=True)), Nature.SIGNAL)

    def test_la_nature_ne_se_deduit_jamais_de_la_source(self):
        from radar.nature import qualifier
        commun = dict(acheteur="Client", echeance_brute=OUVERT)
        natures = {s: qualifier(opp(source=s, **commun))
                   for s in ("ted", "google", "entreprise", "bda")}
        self.assertEqual(len(set(natures.values())), 1, natures)

    def test_on_ne_depose_pas_de_dossier_sur_une_hypothese(self):
        hypothese = opp(source="google", ref_source="H", acheteur=None,
                        echeance_brute=None, date_demarrage=None,
                        intitule="Recherche de transporteur",
                        texte="tournées de distribution en Belgique",
                        pays_livraison=["BE"], secteur_acheteur=None)
        action = moteur().analyser(hypothese, MAINTENANT).classement.action.value
        self.assertNotIn("POSTULER", action)

    def test_la_nature_ne_change_pas_le_score(self):
        """Un fait et une hypothèse d'économie identique valent pareil."""
        commun = dict(intitule="Distribution urbaine de marchandises",
                      texte="tournées quotidiennes de distribution urbaine",
                      montant=240000, duree_mois=24, cadence="quotidienne",
                      pays_livraison=["BE"], distance_depot_km=20)
        fait = opp(ref_source="F", acheteur="Client", echeance_brute=OUVERT, **commun)
        hypo = opp(ref_source="H", acheteur="Client", echeance_brute=OUVERT, **commun)
        hypo.est_signal = False
        m = moteur()
        self.assertEqual(m.analyser(fait, MAINTENANT).score.total,
                         m.analyser(hypo, MAINTENANT).score.total)


class RapportCentreSurLesOccasions(unittest.TestCase):
    """On ouvre le radar pour voir ce qu'il y a à gagner, pas pour compter les
    avis publiés par telle source."""

    def _rapport(self):
        from outils.radar_commercial import LOTS
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        m = moteur()
        for fichier, source in LOTS:
            traiter(cx, m, _charger(fichier, source), maintenant_dt=MAINTENANT)
        return construire(cx, Mode.DEMO, cible={"montant_total_confortable_max": 1500000})

    def test_les_occasions_passent_avant_les_statistiques_de_source(self):
        texte = self._rapport().en_texte(avec_fiches=False)
        self.assertLess(texte.index("CAPTER —"), texte.index("COLLECTE"))
        self.assertLess(texte.index("DÉVELOPPER —"), texte.index("COLLECTE"))

    def test_plusieurs_sources_differentes_apparaissent_dans_capter(self):
        r = self._rapport()
        sources = {source for _, _, _, source, _ in r.capter}
        self.assertGreaterEqual(len(sources), 4,
                                f"le radar doit être multi-sources : {sources}")

    def test_le_rendement_est_observe_jamais_declare(self):
        r = self._rapport()
        self.assertTrue(r.rendement)
        for nom, compteurs in r.rendement.items():
            self.assertLessEqual(compteurs["retenues"], compteurs["lues"])


class UnResultatDeRechercheDevientUneOpportunite(unittest.TestCase):
    """Le pont qui manquait : un résultat web ne servait qu'à découvrir des
    entreprises, il ne devenait jamais une occasion de chiffre d'affaires."""

    def _resultat(self):
        from radar.moteurs_recherche import Resultat
        return Resultat(
            titre="Nous recherchons un transporteur partenaire en Belgique",
            url="https://exemple.be/partenaires",
            extrait="Distribution de nos produits depuis Anvers vers nos clients belges, "
                    "tournées hebdomadaires.",
            requete="recherche transporteur partenaire Belgique",
            fournisseur="google", consulte_le="2026-09-01T09:00:00+00:00")

    def test_un_resultat_web_se_convertit_en_charge_lisible(self):
        c = self._resultat().en_charge()
        self.assertEqual(c["url"], "https://exemple.be/partenaires")
        self.assertIn("transporteur", c["titre"])

    def test_il_traverse_le_moteur_et_ressort_classe(self):
        from radar.adaptateur import Adaptateur, vers_opportunite
        cfg = yaml.safe_load((RACINE / "sources" / "google.yaml").read_text(encoding="utf-8"))
        o = vers_opportunite(Adaptateur.depuis_config(cfg), self._resultat().en_charge(),
                             "google", {"secteur": cfg.get("secteur_par_defaut")})
        o.pays_livraison = ["BE"]
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [o], maintenant_dt=MAINTENANT)
        l = cx.execute("SELECT type, moteur, action FROM opportunites").fetchone()
        self.assertNotEqual(l["type"], "REJET")
        self.assertEqual(l["moteur"], "CAPTER")

    def test_rien_n_est_fabrique_a_partir_d_un_resultat_web(self):
        """Ni acheteur, ni montant, ni échéance : ce que la page ne dit pas
        reste absent."""
        from radar.adaptateur import Adaptateur, vers_opportunite
        cfg = yaml.safe_load((RACINE / "sources" / "google.yaml").read_text(encoding="utf-8"))
        o = vers_opportunite(Adaptateur.depuis_config(cfg), self._resultat().en_charge(),
                             "google", {})
        self.assertIsNone(o.montant)
        self.assertIsNone(o.acheteur)
        self.assertIsNone(o.echeance_brute)

    def test_la_boucle_ne_presume_pas_que_le_moteur_est_google(self):
        """Brave, ou n'importe quel moteur branché plus tard, s'inscrit pareil."""
        from radar.boucle import Boucle
        from radar.entreprises import Registre as RegistreEnt
        from radar.moteurs_recherche import Resultat

        class Faux:
            def generer(self, limite=None):
                return ["une requête"]

            def pour_entreprise(self, nom, domaine=None):
                return []

        r = Resultat(titre="Société Exemple SA cherche un transporteur",
                     url="https://exemple.be/a", extrait="", requete="q",
                     fournisseur="brave")
        reg = RegistreEnt()
        Boucle(Faux(), reg, profondeur_max=0, budget=1).parcourir(lambda q: [r])
        origines = {e.origine for e in reg.entreprises.values()}
        self.assertTrue(any("brave" in (o or "") for o in origines), origines)
        self.assertFalse(any("google" in (o or "") for o in origines), origines)
