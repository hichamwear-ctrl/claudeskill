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


def vocabulaires():
    """Le vocabulaire réellement déclaré par chaque source.

    Le banc d'essai construisait le moteur SANS vocabulaire. Conséquence
    mesurée : `statut_source` et `type_information` — les rangs 5 et 4, les
    deux preuves les plus fortes de la hiérarchie — ressortaient toujours
    « INCONNU » dans les 390 tests. Toute la partie haute de la hiérarchie des
    preuves n'était donc jamais exercée, et une contradiction entre deux
    preuves fortes ne pouvait pas se produire ici. C'est le même défaut que le
    banc à 94 % en forme de marché public : le moteur était correct, son banc
    d'essai ne savait pas le mettre à l'épreuve.
    """
    from radar.procedure import Vocabulaire
    return {(c := cfg(f"sources/{f.name}")).get("source", f.stem): Vocabulaire(c)
            for f in sorted((RACINE / "sources").glob("*.yaml"))}


VOCABULAIRES = vocabulaires()


def moteur(avec_vocabulaire=True):
    return Moteur(PROFIL, CAPACITES, GEO, PONDS, ROLES,
                  vocabulaires=VOCABULAIRES if avec_vocabulaire else None)


def opp(**kw):
    """LE BESOIN PAR DÉFAUT DU BANC D'ESSAI — et il n'est PAS un appel d'offres.

    Ce constructeur portait `type_avis="appel-offres"` et `cpv=["60000000"]`.
    Mesuré : 94 % des opportunités construites dans ces tests étaient donc en
    forme de marché public. Le moteur était théoriquement indépendant, mais son
    banc d'essai lui apprenait implicitement « opportunité = marché public » —
    et un défaut qui n'apparaît que sur une source privée serait passé inaperçu.

    Le défaut est maintenant un besoin commercial nu : pas de CPV, pas de type
    d'avis, pas de référence officielle. Les tests qui ont réellement besoin
    d'un marché public le disent avec `avis_public()`.
    """
    base = dict(source="entreprise", ref_source="R1", intitule="Transport de colis",
                texte="transport routier de marchandises et distribution",
                pays_livraison=["BE"], echeance_brute=OUVERT)
    base.update(kw)
    return Opportunite(**base)


def avis_public(**kw):
    """Un besoin publié par un acheteur public — une FORME parmi d'autres.

    Elle n'a aucun privilège : elle porte simplement des champs que le privé
    n'a pas (CPV, type d'avis, référence officielle).
    """
    base = dict(source="bda", type_avis="appel-offres", cpv=["60000000"],
                acheteur="Commune de Namur", secteur_acheteur="public")
    base.update(kw)
    return opp(**base)


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
        l = self._analyser("google.json", "recherche")[0]
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
        sources = {source for _, _, _, source, _, _ in r.capter}
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
        cfg = yaml.safe_load((RACINE / "sources" / "recherche.yaml").read_text(encoding="utf-8"))
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
        cfg = yaml.safe_load((RACINE / "sources" / "recherche.yaml").read_text(encoding="utf-8"))
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


# ══════════════ L'ÉTAT DE LA PROCÉDURE — comprendre, pas reconnaître des mots
from radar.procedure import (  # noqa: E402
    Confiance as ConfProc, Etat as EtatProc, Vocabulaire, lire, reviser,
    vocabulaire_appris)


def etat(**kw):
    kw.setdefault("maintenant", MAINTENANT)
    return lire(**kw)


class EtatDeProcedure(unittest.TestCase):
    """Les quinze cas adversariaux. Chacun a une mauvaise réponse évidente."""

    def test_01_ouvert_est_postulable(self):
        self.assertIs(etat(texte="procédure ouverte").etat, EtatProc.POSTULABLE)

    def test_02_attribue_est_attribue(self):
        self.assertIs(etat(texte="marché attribué").etat, EtatProc.ATTRIBUE)

    def test_03_award_est_attribue(self):
        self.assertIs(etat(texte="contract awarded").etat, EtatProc.ATTRIBUE)

    def test_04_gunning_est_attribue(self):
        self.assertIs(etat(texte="gunning van de opdracht").etat, EtatProc.ATTRIBUE)

    def test_05_date_depassee_sans_attribution_est_ferme_pas_attribue(self):
        """Le piège central : une date passée ne prouve AUCUNE attribution."""
        l = etat(echeance=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertIs(l.etat, EtatProc.FERME)
        self.assertIsNot(l.etat, EtatProc.ATTRIBUE)
        self.assertIn("attribution", l.etat.libelle_long)

    def test_06_attribution_publiee_bat_une_ancienne_date_limite(self):
        l = etat(texte="marché attribué le 03/09/2026",
                 echeance=datetime(2099, 1, 1, tzinfo=timezone.utc))
        self.assertIs(l.etat, EtatProc.ATTRIBUE)
        self.assertTrue(l.contradictions, "la date contradictoire doit rester visible")

    def test_07_statut_inconnu_reste_inconnu(self):
        l = etat(statut_source="zorbliflé", source="portail")
        self.assertIs(l.etat, EtatProc.INCONNU)
        self.assertIn(("statut", "zorbliflé"), l.inconnues)

    def test_08_un_rectificatif_ne_rouvre_pas_un_marche_attribue(self):
        voc = Vocabulaire({"procedure": {"types_information": {
            "avis rectificatif": {"interpretation": "a_evaluer", "confiance": "nulle"}}}})
        l = etat(type_information="avis rectificatif",
                 titre="Rectificatif — transport de matériel",
                 evenements=[{"type": "avis d'attribution", "date": "2026-06-01"}],
                 vocabulaire=voc)
        self.assertIs(l.etat, EtatProc.ATTRIBUE)

    def test_09_un_lot_encore_ouvert_dans_un_marche_attribue(self):
        """Le marché est attribué ; le lot 3 ne l'est pas. Trois situations."""
        marche = opp(ref_source="M", statut_source="attribué",
                     intitule="Marché de services logistiques",
                     texte="transport et distribution",
                     lots=[LotBrut(numero="1", intitule="Transport de mobilier",
                                   statut_source="attribué"),
                           LotBrut(numero="2", intitule="Transport de palettes",
                                   statut_source="annulé"),
                           LotBrut(numero="3", intitule="Distribution urbaine",
                                   statut_source="en cours")])
        enfants = eclater(marche)
        self.assertEqual([e.statut_source for e in enfants],
                         ["attribué", "annulé", "en cours"])

    def test_10_un_lot_annule_dans_un_marche_ouvert(self):
        marche = opp(ref_source="M2", statut_source="en cours",
                     lots=[LotBrut(numero="1", intitule="Transport"),
                           LotBrut(numero="2", intitule="Manutention",
                                   statut_source="annulé")])
        enfants = eclater(marche)
        self.assertEqual(enfants[0].statut_source, "en cours",
                         "un lot sans statut hérite de celui du marché")
        self.assertEqual(enfants[1].statut_source, "annulé")

    def test_11_le_neerlandais_est_compris(self):
        self.assertIs(etat(texte="inschrijving mogelijk tot 15/10").etat,
                      EtatProc.POSTULABLE)
        self.assertIs(etat(texte="de opdracht is gegund").etat, EtatProc.ATTRIBUE)

    def test_12_le_francais_est_compris(self):
        self.assertIs(etat(texte="les offres sont recevables").etat, EtatProc.POSTULABLE)
        self.assertIs(etat(texte="le contrat a été octroyé").etat, EtatProc.ATTRIBUE)

    def test_13_l_anglais_et_l_allemand_sont_compris(self):
        self.assertIs(etat(titre="Open tenders").etat, EtatProc.POSTULABLE)
        self.assertIs(etat(texte="the contract has been awarded").etat, EtatProc.ATTRIBUE)
        self.assertIs(etat(texte="Angebote können eingereicht werden").etat,
                      EtatProc.POSTULABLE)
        self.assertIs(etat(texte="der Zuschlag wurde erteilt").etat, EtatProc.ATTRIBUE)

    def test_14_award_dans_un_document_annexe_ne_conclut_pas(self):
        """Le statut d'un DOCUMENT n'est pas celui de la PROCÉDURE."""
        l = etat(titre="Marché de transport de marchandises",
                 documents=["avis d'attribution.pdf", "cahier des charges.pdf"])
        self.assertIsNot(l.etat, EtatProc.ATTRIBUE)
        self.assertTrue(any("document" in v for v in l.a_verifier))

    def test_15_absence_totale_de_statut_donne_inconnu_jamais_postulable(self):
        l = etat(titre="Marché de transport", texte="")
        self.assertIs(l.etat, EtatProc.INCONNU)
        self.assertIsNone(l.postulable, "INCONNU n'est ni True ni False")
        self.assertIsNot(l.etat, EtatProc.POSTULABLE)


class FormulationsJamaisVues(unittest.TestCase):
    """Des tournures absentes des fixtures. Le moteur ne connaît pas « la phrase
    du portail X » : il connaît ce dont une phrase parle."""

    POSTULABLES = [
        "consultations ouvertes", "dépôt des offres en cours",
        "les soumissions sont recevables", "procédure active",
        "offres actuellement recevables", "appel à concurrence en cours",
        "inschrijvingen zijn mogelijk", "open procedure",
        "tender opportunities currently available",
        "Angebote können eingereicht werden",
    ]
    ATTRIBUES = [
        "contrat déjà octroyé", "fournisseur retenu", "soumissionnaire retenu",
        "décision d'attribution publiée", "marché conclu avec le prestataire",
        "award decision published", "awarded supplier", "de winnaar is bekend",
        "opdracht toegewezen", "der Auftragnehmer steht fest",
    ]
    FERMES = [
        "aucune offre ne peut désormais être déposée",
        "les offres ne sont plus acceptées", "la procédure est clôturée",
        "la date limite de remise des offres est dépassée",
        "de procedure is afgesloten", "submissions are closed",
    ]

    def test_les_formulations_ouvertes_sont_comprises(self):
        for phrase in self.POSTULABLES:
            with self.subTest(phrase=phrase):
                self.assertIs(etat(texte=phrase).etat, EtatProc.POSTULABLE)

    def test_les_formulations_d_attribution_sont_comprises(self):
        for phrase in self.ATTRIBUES:
            with self.subTest(phrase=phrase):
                self.assertIs(etat(texte=phrase).etat, EtatProc.ATTRIBUE)

    def test_les_formulations_de_fermeture_sont_comprises(self):
        for phrase in self.FERMES:
            with self.subTest(phrase=phrase):
                self.assertIs(etat(texte=phrase).etat, EtatProc.FERME)

    def test_les_negations_ne_sont_pas_ignorees(self):
        """« aucun soumissionnaire désigné » contient le vocabulaire de
        l'attribution et dit exactement l'inverse."""
        l = etat(texte="aucun soumissionnaire n'a encore été désigné")
        self.assertIsNot(l.etat, EtatProc.ATTRIBUE)
        self.assertIsNot(l.etat, EtatProc.POSTULABLE)

    def test_une_attribution_annoncee_n_est_pas_une_attribution(self):
        l = etat(texte="le marché sera attribué prochainement")
        self.assertIsNot(l.etat, EtatProc.ATTRIBUE)

    def test_aucune_attribution_annoncee_ne_rend_pas_postulable(self):
        l = etat(texte="aucune attribution annoncée")
        self.assertIsNot(l.etat, EtatProc.POSTULABLE)
        self.assertIsNot(l.etat, EtatProc.ATTRIBUE)

    def test_une_selection_en_cours_n_est_ni_ouverte_ni_attribuee(self):
        l = etat(texte="sélection en cours")
        self.assertIsNot(l.etat, EtatProc.POSTULABLE)
        self.assertIsNot(l.etat, EtatProc.ATTRIBUE)

    def test_un_resultat_publie_sans_titulaire_ne_dit_pas_attribue(self):
        l = etat(texte="résultat de la procédure")
        self.assertIsNot(l.etat, EtatProc.ATTRIBUE)

    def test_un_depot_logistique_n_est_pas_un_depot_d_offre(self):
        """« nous disposons d'un dépôt en Belgique » ne parle pas de procédure."""
        l = etat(titre="Devenir partenaire transporteur",
                 texte="Nous confions nos tournées à des partenaires disposant "
                       "d'un dépôt en Belgique.")
        self.assertFalse(l.procedure_detectee)

    def test_une_expression_non_interpretable_ne_devient_jamais_postulable(self):
        l = etat(statut_source="phase gamma", texte="Marché de transport", source="x")
        self.assertIs(l.etat, EtatProc.INCONNU)
        self.assertTrue(l.a_verifier)


class HierarchieDesPreuves(unittest.TestCase):
    def test_un_statut_declare_bat_la_rubrique_du_portail(self):
        voc = Vocabulaire({"procedure": {
            "statuts": {"gesloten": {"interpretation": "ferme", "confiance": "elevee"}},
            "types_information": {"Marchés en cours": {"interpretation": "postulable"}}}})
        l = etat(statut_source="gesloten", type_information="Marchés en cours",
                 vocabulaire=voc)
        self.assertIs(l.etat, EtatProc.FERME)
        self.assertTrue(l.contradictions)

    def test_un_etat_explicite_bat_la_rubrique_du_portail(self):
        """Une rubrique de listing est souvent en retard ; la phrase de
        l'annonce parle de CETTE procédure."""
        voc = Vocabulaire({"procedure": {"types_information": {
            "Marchés en cours": {"interpretation": "postulable", "confiance": "moyenne"}}}})
        l = etat(type_information="Marchés en cours",
                 texte="La procédure est clôturée. Les offres ne sont plus acceptées.",
                 vocabulaire=voc)
        self.assertIs(l.etat, EtatProc.FERME)
        self.assertTrue(any("Marchés en cours" in c for c in l.contradictions))

    def test_la_date_ne_bat_jamais_une_attribution(self):
        l = etat(texte="marché attribué",
                 echeance=datetime(2099, 1, 1, tzinfo=timezone.utc))
        self.assertIs(l.etat, EtatProc.ATTRIBUE)

    def test_deux_preuves_de_meme_rang_contradictoires_donnent_inconnu(self):
        voc = Vocabulaire({"procedure": {"types_information": {
            "A": {"interpretation": "postulable"}, "B": {"interpretation": "attribue"}}}})
        l1 = etat(type_information="A", vocabulaire=voc)
        l2 = etat(type_information="B", vocabulaire=voc)
        self.assertIs(l1.etat, EtatProc.POSTULABLE)
        self.assertIs(l2.etat, EtatProc.ATTRIBUE)
        # deux états terminaux différents, même rang : on ne tranche pas
        l3 = etat(texte="procédure annulée, marché attribué à XYZ")
        self.assertIs(l3.etat, EtatProc.INCONNU)

    def test_un_etat_plus_precis_absorbe_ferme_sans_contradiction_fausse(self):
        """ATTRIBUÉ dit « fermé » ET pourquoi. Ce n'est pas une contradiction."""
        l = etat(texte="procédure clôturée, marché attribué à XYZ Logistics")
        self.assertIs(l.etat, EtatProc.ATTRIBUE)

    def test_la_confiance_baisse_quand_une_preuve_contredit(self):
        seul = etat(texte="marché attribué")
        contredit = etat(texte="marché attribué",
                         echeance=datetime(2099, 1, 1, tzinfo=timezone.utc))
        self.assertIs(seul.confiance, ConfProc.ELEVEE)
        self.assertIs(contredit.confiance, ConfProc.MOYENNE)


class TaxonomieDunPortail(unittest.TestCase):
    """« Marchés en cours », « Avis de préinformation », « Appels à projets »
    ne veulent pas dire la même chose et ne doivent pas finir au même endroit."""

    def _traiter(self):
        from outils.radar_commercial import charger, _moteur
        cx = ouvrir(":memory:")
        traiter(cx, _moteur(), charger("portail.json", "portail"),
                maintenant_dt=MAINTENANT)
        return {l["intitule"]: l for l in cx.execute(
            "SELECT intitule, type, moteur, action, fiche FROM opportunites")}

    def _une(self, fragment):
        for titre, l in self._traiter().items():
            if fragment.lower() in (titre or "").lower():
                return l
        self.fail(f"aucune opportunité contenant « {fragment} »")

    def test_les_trois_rubriques_ne_finissent_pas_au_meme_endroit(self):
        lignes = self._traiter()
        moteurs = {t: l["moteur"] for t, l in lignes.items()}
        actions = {l["action"] for l in lignes.values()}
        self.assertIn("CAPTER", moteurs.values())
        self.assertIn("DEVELOPPER", moteurs.values())
        self.assertGreaterEqual(len(actions), 3,
                                f"trois rubriques, au moins trois actions : {actions}")

    def test_un_marche_en_cours_est_analyse_pour_sa_postulabilite(self):
        l = self._une("Distribution de fournitures")
        self.assertEqual(l["moteur"], "CAPTER")
        self.assertIn("POSTULABLE", l["fiche"])

    def test_une_preinformation_va_dans_developper_et_surveille(self):
        l = self._une("Préinformation")
        self.assertEqual(l["moteur"], "DEVELOPPER")
        self.assertEqual(l["action"], "SURVEILLER")
        self.assertIn("ANNONCÉ", l["fiche"])
        self.assertIn("futur marché", l["fiche"])

    def test_un_appel_a_projets_n_est_ni_postulable_ni_jete(self):
        l = self._une("Appel à projets")
        self.assertNotEqual(l["type"], "REJET", "un appel à projets n'est pas du bruit")
        self.assertIn("ÉTAT À VÉRIFIER", l["fiche"])
        self.assertIn("bénéficiaire", l["fiche"].lower())

    def test_une_rubrique_contredite_par_le_texte_suit_le_texte(self):
        l = self._une("ateliers communaux")
        self.assertEqual(l["moteur"], "DEVELOPPER")
        self.assertIn("FERMÉ", l["fiche"])
        self.assertIn("CONTRADICTION", l["fiche"])

    def test_une_rubrique_inconnue_ne_casse_pas_le_moteur(self):
        """« Phase de consultation active » n'est déclarée nulle part."""
        l = self._une("reprise des tournées")
        self.assertNotEqual(l["type"], "REJET")

    def test_l_acces_du_portail_reste_inconnu_tant_qu_il_n_est_pas_verifie(self):
        cfg = yaml.safe_load((RACINE / "sources" / "portail.yaml").read_text(
            encoding="utf-8"))
        self.assertEqual(cfg["acces"], "INCONNU")
        self.assertIn("absence d'opportunité", cfg["note_acces"])


class EtatEtAction(unittest.TestCase):
    """L'état change l'ACTION. Il ne change jamais la valeur économique."""

    def _avec(self, **kw):
        o = opp(intitule="Distribution urbaine de marchandises",
                texte="tournées quotidiennes de distribution urbaine",
                acheteur="Client", montant=240000, duree_mois=24,
                cadence="quotidienne", pays_livraison=["BE"], distance_depot_km=20,
                echeance_brute=OUVERT, **kw)
        return moteur().analyser(o, MAINTENANT)

    def test_ferme_va_dans_developper_et_dit_attribution_non_publiee(self):
        r = self._avec(texte_statut="la procédure est clôturée")
        self.assertEqual(r.classement.moteur.value, "DEVELOPPER")
        self.assertIn("NON PUBLIÉE", r.classement.motif)

    def test_un_marche_annule_reste_une_piste(self):
        r = self._avec(texte_statut="procédure annulée")
        self.assertIsNot(r.classement.type, Type.REJET)
        self.assertEqual(r.classement.action, Action.SURVEILLER)

    def test_un_marche_infructueux_est_une_occasion_d_etre_connu(self):
        r = self._avec(texte_statut="procédure déclarée sans suite")
        self.assertIsNot(r.classement.type, Type.REJET)
        self.assertEqual(r.classement.action, Action.CONTACTER_ACHETEUR)

    def test_un_etat_inconnu_donne_verifier_jamais_postuler(self):
        r = self._avec(statut_source="phase gamma")
        self.assertEqual(r.classement.action, Action.VERIFIER_ETAT)
        self.assertIsNot(r.classement.type, Type.REJET)

    def test_l_etat_ne_change_pas_le_score(self):
        """Un marché fermé vaut économiquement ce qu'il vaut. C'est l'action
        qui change, pas le chiffre d'affaires potentiel."""
        scores = {
            "postulable": self._avec(texte_statut="procédure ouverte").score.total,
            "ferme": self._avec(texte_statut="procédure clôturée").score.total,
            "attribue": self._avec(texte_statut="marché attribué").score.total,
            "inconnu": self._avec(statut_source="phase gamma").score.total,
        }
        self.assertEqual(len(set(scores.values())), 1,
                         f"l'état a influencé le score : {scores}")


class MemoireDuVocabulaire(unittest.TestCase):
    def test_une_expression_inconnue_est_conservee_avec_son_contexte(self):
        cx = ouvrir(":memory:")
        o = opp(source="portail", ref_source="P1", statut_source="phase gamma",
                intitule="Transport de matériel", echeance_brute=OUVERT)
        traiter(cx, moteur(), [o], maintenant_dt=MAINTENANT)
        l = cx.execute("SELECT * FROM vocabulaire").fetchone()
        self.assertEqual(l["expression"], "phase gamma")
        self.assertIsNone(l["interpretation"], "rien n'est tranché automatiquement")
        self.assertIn("Transport", l["contexte"])

    def test_trancher_une_expression_la_rend_lisible_ensuite(self):
        cx = ouvrir(":memory:")
        reviser(cx, "portail", "statut", "phase gamma", "ferme",
                motif="vérifié sur le portail", par="test")
        voc = vocabulaire_appris(cx, "portail")
        self.assertIs(lire(statut_source="phase gamma", vocabulaire=voc).etat,
                      EtatProc.FERME)

    def test_une_revision_archive_l_ancienne_lecture_sans_l_effacer(self):
        cx = ouvrir(":memory:")
        reviser(cx, "portail", "statut", "phase gamma", "postulable", par="a")
        reviser(cx, "portail", "statut", "phase gamma", "ferme",
                motif="première lecture erronée", par="b")
        hist = cx.execute("SELECT * FROM vocabulaire_historique").fetchall()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["interpretation"], "postulable")
        self.assertEqual(
            cx.execute("SELECT interpretation FROM vocabulaire").fetchone()[0], "ferme")

    def test_une_interpretation_inventee_est_refusee(self):
        cx = ouvrir(":memory:")
        with self.assertRaises(ValueError):
            reviser(cx, "portail", "statut", "x", "probablement-ouvert")

    def test_le_yaml_ecrit_a_la_main_prime_sur_la_memoire(self):
        from radar.procedure import fusionner_vocabulaires
        cx = ouvrir(":memory:")
        reviser(cx, "bda", "statut", "clôturé", "postulable", par="erreur")
        declare = Vocabulaire(yaml.safe_load(
            (RACINE / "sources" / "bda.yaml").read_text(encoding="utf-8")))
        fusion = fusionner_vocabulaires(vocabulaire_appris(cx, "bda"), declare)
        self.assertIs(lire(statut_source="clôturé", vocabulaire=fusion).etat,
                      EtatProc.FERME)


class InterpretationHorsAppelsDOffres(unittest.TestCase):
    """La couche d'interprétation est générique — elle n'est pas réservée aux
    portails de marchés publics."""

    def test_une_page_privee_qui_cherche_activement_est_lue(self):
        l = etat(texte="nous cherchons actuellement un partenaire logistique")
        self.assertIsNot(l.etat, EtatProc.ATTRIBUE)

    def test_une_bourse_de_fret_est_lue_par_le_meme_module(self):
        l = etat(texte="capacité recherchée sur la liaison Rotterdam-Bruxelles")
        self.assertIsNot(l.etat, EtatProc.POSTULABLE,
                         "rien ne prouve une procédure ouverte ici")

    def test_le_module_ne_connait_aucun_portail(self):
        source = (RACINE / "radar" / "procedure.py").read_text(encoding="utf-8")
        for nom in ("ted.europa", "publicprocurement", "tenderned", "api.ted"):
            self.assertNotIn(nom, source)


class IndependanceDesCapteurs(unittest.TestCase):
    """Le radar existe indépendamment de chacun de ses capteurs.

    Le projet ne doit jamais pouvoir être résumé à « un lecteur de TED
    amélioré » : le produit est le radar, TED n'en est qu'un capteur.
    """

    PUBLIQUES = {"ted", "bda", "portail"}
    PRIVEES = {"google", "entreprise", "signaux", "bourse_fret"}

    def _radar(self, exclues=()):
        from outils.radar_commercial import LOTS, charger, _moteur
        cx = ouvrir(":memory:")
        m = _moteur()
        for fichier, source in LOTS:
            if source in exclues:
                continue
            traiter(cx, m, charger(fichier, source), maintenant_dt=MAINTENANT)
        return cx.execute(
            "SELECT o.type, o.moteur, o.action, a.source FROM opportunites o"
            " JOIN avis a ON a.id = o.avis_id WHERE o.type <> 'REJET'").fetchall()

    def _coherent(self, lignes, contexte):
        self.assertGreater(len(lignes), 0, f"{contexte} : plus aucune opportunité")
        self.assertTrue(any(l["moteur"] == "CAPTER" for l in lignes),
                        f"{contexte} : plus rien à attaquer")
        self.assertTrue(all(l["action"] for l in lignes),
                        f"{contexte} : une opportunité sans action")

    def test_sans_ted_le_radar_produit_toujours_un_resultat_commercial(self):
        lignes = self._radar({"ted"})
        self._coherent(lignes, "sans TED")
        self.assertNotIn("ted", {l["source"] for l in lignes})

    def test_sans_google_le_radar_continue(self):
        self._coherent(self._radar({"google"}), "sans Google")

    def test_sans_aucune_source_publique_le_radar_continue(self):
        """Ni TED, ni BDA, ni portail : restent le privé, les entreprises et
        les signaux. C'est encore un radar commercial."""
        lignes = self._radar(self.PUBLIQUES)
        self._coherent(lignes, "sans aucune source publique")
        self.assertTrue(self.PRIVEES & {l["source"] for l in lignes})

    def test_sans_aucune_source_privee_le_radar_continue(self):
        self._coherent(self._radar(self.PRIVEES), "sans aucune source privée")

    def test_aucune_source_ne_represente_plus_de_la_moitie_des_occasions(self):
        """Un radar dont une source ferait tout le travail serait un lecteur
        de cette source, pas un radar."""
        lignes = self._radar()
        compte = {}
        for l in lignes:
            compte[l["source"]] = compte.get(l["source"], 0) + 1
        part = max(compte.values()) / len(lignes)
        self.assertLess(part, 0.5, f"une source domine le radar : {compte}")


# ══════════════ LE FIL DE VIE — une opportunité, plusieurs observations
from radar import transitions as tr  # noqa: E402
from radar.fiabilite import Niveau as NiveauFiab  # noqa: E402


class FilDeVie(unittest.TestCase):
    """03/09 POSTULABLE · 14/09 FERMÉ · 28/09 ATTRIBUÉ, ce n'est pas trois
    opportunités : c'est une opportunité, trois observations, deux transitions."""

    def setUp(self):
        self.cx = ouvrir(":memory:")
        self.m = moteur()

    def _collecter(self, **kw):
        o = opp(ref_source="M1", intitule="Distribution de colis",
                texte="tournées quotidiennes de distribution", acheteur="Ville",
                montant=240000, pays_livraison=["BE"], echeance_brute=OUVERT, **kw)
        return traiter(self.cx, self.m, [o], maintenant_dt=MAINTENANT)

    def _historique(self):
        return self.cx.execute(
            "SELECT ancien_etat, nouvel_etat, origine FROM etats_historique"
            " ORDER BY id").fetchall()

    def test_une_collecte_identique_ne_cree_aucun_evenement(self):
        self._collecter()
        avant = len(self._historique())
        b = self._collecter()
        self.assertEqual(b.transitions, 0)
        self.assertEqual(len(self._historique()), avant)

    def test_trois_observations_donnent_une_opportunite_et_deux_transitions(self):
        self._collecter()
        self._collecter(texte_statut="la procédure est clôturée")
        self._collecter(texte_statut="marché attribué à XYZ Logistics")
        n = self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        self.assertEqual(n, 1, "le fil de vie ne doit pas dupliquer l'opportunité")
        hist = self._historique()
        self.assertEqual([(h["ancien_etat"], h["nouvel_etat"]) for h in hist],
                         [(None, "POSTULABLE"), ("POSTULABLE", "FERMÉ"),
                          ("FERMÉ", "ATTRIBUÉ")])

    def test_chaque_transition_conserve_sa_preuve_et_son_origine(self):
        self._collecter()
        self._collecter(texte_statut="la procédure est clôturée")
        l = self._historique()[-1]
        self.assertEqual(l["origine"], tr.COLLECTE)
        preuve = self.cx.execute(
            "SELECT preuve FROM etats_historique ORDER BY id DESC").fetchone()["preuve"]
        self.assertIn("clotur", preuve)

    def test_moteur_et_action_sont_bien_recalcules(self):
        """Le bug : `moteur` et `action` n'étaient pas mis à jour. La fiche
        disait ATTRIBUÉ pendant que la ligne disait POSTULER."""
        self._collecter()
        avant = self.cx.execute(
            "SELECT moteur, action FROM opportunites").fetchone()
        self._collecter(texte_statut="marché attribué à XYZ Logistics")
        apres = self.cx.execute(
            "SELECT moteur, action, etat_procedure FROM opportunites").fetchone()
        self.assertEqual(avant["action"], "POSTULER")
        self.assertEqual(apres["moteur"], "DEVELOPPER")
        self.assertEqual(apres["action"], "CONTACTER LE TITULAIRE")
        self.assertEqual(apres["etat_procedure"], "ATTRIBUÉ")

    def test_la_fiche_montre_le_fil_de_vie(self):
        self._collecter()
        self._collecter(texte_statut="la procédure est clôturée")
        self._collecter(texte_statut="marché attribué à XYZ Logistics")
        fiche = self.cx.execute("SELECT fiche FROM opportunites").fetchone()["fiche"]
        self.assertIn("HISTORIQUE", fiche)
        self.assertIn("POSTULABLE → FERMÉ", fiche)


class TransitionsEtActions(unittest.TestCase):
    """Un changement d'état est un événement commercial, pas une mise à jour."""

    def setUp(self):
        self.cx = ouvrir(":memory:")
        self.m = moteur()

    def _passer(self, **kw):
        o = opp(ref_source="T1", intitule="Distribution urbaine",
                texte="tournées quotidiennes de distribution urbaine",
                acheteur="Ville", montant=240000, pays_livraison=["BE"],
                echeance_brute=OUVERT, **kw)
        return traiter(self.cx, self.m, [o], maintenant_dt=MAINTENANT)

    def _envois(self):
        return {l["motif"]: (l["etat"], l["intensite"]) for l in
                self.cx.execute("SELECT motif, etat, intensite FROM envois")}

    def test_postulable_vers_ferme_annule_les_alertes_postuler_en_attente(self):
        self._passer()
        self.assertEqual(self._envois()["decouverte"][0], "a_envoyer")
        self._passer(texte_statut="la procédure est clôturée")
        self.assertEqual(self._envois()["decouverte"][0], "perime")

    def test_ferme_vers_attribue_bascule_en_developper_et_alerte(self):
        self._passer()
        self._passer(texte_statut="la procédure est clôturée")
        self._passer(texte_statut="marché attribué à XYZ Logistics")
        self.assertIn("FERMÉ->ATTRIBUÉ", self._envois())

    def test_annonce_vers_postulable_est_une_alerte_forte(self):
        self._passer(type_avis="avis de préinformation",
                     texte_statut="avis de préinformation")
        b = self._passer(texte_statut="les offres peuvent encore être introduites")
        self.assertTrue(b.alertes)
        motif, (_, intensite) = next(
            (m, v) for m, v in self._envois().items() if "->" in m)
        self.assertEqual(intensite, "forte")
        corps = self.cx.execute(
            "SELECT corps FROM envois WHERE motif LIKE '%->%'").fetchone()["corps"]
        self.assertIn("MAINTENANT OUVERT", corps)

    def test_infructueux_vers_postulable_annonce_une_nouvelle_chance(self):
        self._passer(texte_statut="procédure déclarée sans suite")
        self._passer(texte_statut="les offres peuvent encore être introduites")
        corps = self.cx.execute(
            "SELECT corps FROM envois WHERE motif LIKE '%->%'").fetchone()["corps"]
        self.assertIn("NOUVELLE CHANCE DE POSTULER", corps)

    def test_annule_vers_postulable_alerte_aussi(self):
        self._passer(texte_statut="procédure annulée")
        self._passer(texte_statut="les offres peuvent encore être introduites")
        corps = self.cx.execute(
            "SELECT corps FROM envois WHERE motif LIKE '%->%'").fetchone()["corps"]
        self.assertIn("RELANCE", corps)

    def test_une_transition_vers_inconnu_n_alerte_jamais(self):
        self._passer()
        self._passer(statut_source="phase gamma")
        self.assertFalse([m for m in self._envois() if "->" in m],
                         "perdre la certitude n'est pas une occasion")

    def test_la_premiere_observation_n_est_pas_une_alerte_de_transition(self):
        self._passer()
        self.assertEqual([m for m in self._envois() if "->" in m], [])

    def test_une_correction_de_vocabulaire_ne_fait_pas_croire_a_un_changement(self):
        """« la source a changé » n'est pas « nous avons changé notre lecture »."""
        from radar.procedure import Etat as E, Lecture, Confiance as C
        self._passer()
        avis_id = self.cx.execute("SELECT id FROM avis").fetchone()["id"]
        lecture = Lecture(etat=E.FERME, confiance=C.ELEVEE)
        t = tr.constater(self.cx, avis_id, lecture, "ted",
                         origine=tr.REVISION, version_vocabulaire=3)
        self.assertFalse(t.alerte)
        self.assertEqual(t.origine, tr.REVISION)
        l = self.cx.execute("SELECT origine, version_vocabulaire FROM etats_historique"
                            " ORDER BY id DESC").fetchone()
        self.assertEqual(l["origine"], "revision_vocabulaire")
        self.assertEqual(l["version_vocabulaire"], 3)


class ContradictionsFortes(unittest.TestCase):
    """La hiérarchie départage des preuves NON contradictoires. Elle ne fait pas
    gagner un champ structuré périmé contre une phrase qui dit le contraire."""

    def _voc(self):
        return Vocabulaire({"procedure": {
            "statuts": {"open": {"interpretation": "postulable", "confiance": "elevee"}},
            "types_information": {
                "Marchés en cours": {"interpretation": "postulable", "confiance": "moyenne"},
                "Résultats": {"interpretation": "attribue", "confiance": "elevee"}}}})

    def test_statut_structuré_ouvert_contre_texte_ferme_donne_inconnu(self):
        l = lire(statut_source="open", texte="la procédure est clôturée",
                 vocabulaire=self._voc())
        self.assertIs(l.etat, EtatProc.INCONNU)
        self.assertTrue(any("CONTRADICTION À VÉRIFIER" in c for c in l.contradictions))

    def test_rubrique_ouverte_contre_texte_ferme_suit_le_texte(self):
        """Ici une seule preuve est de confiance élevée : elle tranche."""
        l = lire(type_information="Marchés en cours",
                 texte="La procédure est clôturée et les offres ne sont plus acceptées.",
                 vocabulaire=self._voc())
        self.assertIs(l.etat, EtatProc.FERME)
        self.assertTrue(l.contradictions)
        # La confiance BAISSE parce qu'une preuve dit autre chose. Elle reste
        # élevée seulement quand rien ne contredit.
        self.assertIs(l.confiance, ConfProc.MOYENNE)
        self.assertIs(lire(texte="la procédure est clôturée").confiance,
                      ConfProc.ELEVEE)

    def test_la_hierarchie_departage_quand_il_n_y_a_pas_de_conflit_fort(self):
        l = lire(type_information="Résultats",
                 echeance=datetime(2099, 1, 1, tzinfo=timezone.utc),
                 maintenant=MAINTENANT, vocabulaire=self._voc())
        self.assertIs(l.etat, EtatProc.ATTRIBUE)

    def test_la_hierarchie_est_configurable_par_source(self):
        """Un portail dont les rubriques sont en retard peut les rétrograder."""
        retard = Vocabulaire({"procedure": {
            "hierarchie": {"rubrique": 0},
            "types_information": {
                "Marchés en cours": {"interpretation": "postulable", "confiance": "moyenne"}}}})
        l = lire(type_information="Marchés en cours",
                 echeance=datetime(2020, 1, 1, tzinfo=timezone.utc),
                 maintenant=MAINTENANT, vocabulaire=retard)
        self.assertIs(l.etat, EtatProc.FERME, "la date passe devant la rubrique")

    def test_un_rang_inconnu_dans_la_configuration_est_refuse(self):
        with self.assertRaises(ValueError):
            Vocabulaire({"procedure": {"hierarchie": {"couleur_du_bouton": 9}}})


class EtatsParLot(unittest.TestCase):
    def test_un_marche_attribue_avec_quatre_lots_donne_quatre_etats(self):
        marche = avis_public(ref_source="P", statut_source="attribué",
                             intitule="Marché de services logistiques",
                             texte="transport et distribution", acheteur="Province",
                             pays_livraison=["BE"], echeance_brute=OUVERT,
                             lots=[LotBrut(numero="1", intitule="Transport de mobilier",
                                           statut_source="attribué"),
                                   LotBrut(numero="2", intitule="Transport de palettes",
                                           statut_source="clôturé"),
                                   LotBrut(numero="3", intitule="Distribution urbaine",
                                           statut_source="en cours"),
                                   LotBrut(numero="4", intitule="Manutention",
                                           statut_source="infructueux")])
        cx = ouvrir(":memory:")
        voc = Vocabulaire(yaml.safe_load(
            (RACINE / "sources" / "bda.yaml").read_text(encoding="utf-8")))
        voc.statuts.update(Vocabulaire({"procedure": {"statuts": {
            "infructueux": {"interpretation": "infructueux", "confiance": "elevee"}}}}).statuts)
        m = moteur()
        m.vocabulaires["bda"] = voc
        traiter(cx, m, [marche], maintenant_dt=MAINTENANT)
        etats = {l["lot_numero"]: l["etat_procedure"] for l in cx.execute(
            "SELECT lot_numero, etat_procedure FROM opportunites")}
        self.assertEqual(etats, {"1": "ATTRIBUÉ", "2": "FERMÉ",
                                 "3": "POSTULABLE", "4": "INFRUCTUEUX"})

    def test_un_lot_attribue_dans_un_marche_ouvert_reste_attribue(self):
        marche = avis_public(ref_source="Q", statut_source="en cours",
                             intitule="Marché de transport",
                             texte="transport de marchandises",
                             acheteur="Commune", pays_livraison=["BE"],
                             echeance_brute=OUVERT,
                             lots=[LotBrut(numero="1", intitule="Transport A"),
                                   LotBrut(numero="2", intitule="Transport B",
                                           statut_source="attribué")])
        cx = ouvrir(":memory:")
        m = moteur()
        m.vocabulaires["bda"] = Vocabulaire(yaml.safe_load(
            (RACINE / "sources" / "bda.yaml").read_text(encoding="utf-8")))
        traiter(cx, m, [marche], maintenant_dt=MAINTENANT)
        etats = {l["lot_numero"]: (l["etat_procedure"], l["moteur"]) for l in cx.execute(
            "SELECT lot_numero, etat_procedure, moteur FROM opportunites")}
        self.assertEqual(etats["1"][0], "POSTULABLE")
        self.assertEqual(etats["2"], ("ATTRIBUÉ", "DEVELOPPER"))


class FiabiliteSeparee(unittest.TestCase):
    """FIABILITÉ DE L'INFORMATION ≠ VALEUR ÉCONOMIQUE. Jamais mélangées."""

    def _analyser(self, **kw):
        o = opp(intitule="Distribution urbaine de marchandises",
                texte="tournées quotidiennes de distribution urbaine",
                montant=240000, duree_mois=24, cadence="quotidienne",
                pays_livraison=["BE"], distance_depot_km=20, **kw)
        return moteur().analyser(o, MAINTENANT)

    def test_une_information_peu_fiable_garde_toute_sa_valeur_economique(self):
        solide = self._analyser(ref_source="OK-1", acheteur="Ville de Namur",
                                echeance_brute=OUVERT, plateforme="https://ex.be/1")
        fragile = self._analyser(ref_source="SANS-REF-abc", acheteur=None,
                                 echeance_brute=None)
        self.assertEqual(solide.score.total, fragile.score.total,
                         "la fiabilité ne doit pas entrer dans le score")
        self.assertNotEqual(solide.fiabilite.niveau, fragile.fiabilite.niveau)

    def test_la_fiabilite_est_affichee_avec_son_motif(self):
        r = self._analyser(ref_source="OK-2", acheteur="Ville", echeance_brute=OUVERT)
        fiche = r.fiche.en_texte()
        self.assertIn("FIABILITÉ", fiche)
        self.assertIn(r.fiabilite.niveau.value, fiche)

    def test_une_contradiction_fait_baisser_la_fiabilite_pas_le_score(self):
        voc = Vocabulaire({"procedure": {"statuts": {
            "open": {"interpretation": "postulable", "confiance": "elevee"}}}})
        m = moteur()
        m.vocabulaires["bda"] = voc
        propre = m.analyser(avis_public(ref_source="C1", acheteur="Ville",
                                        echeance_brute=OUVERT), MAINTENANT)
        trouble = m.analyser(avis_public(ref_source="C2", acheteur="Ville",
                                         echeance_brute=OUVERT, statut_source="open",
                                         texte_statut="la procédure est clôturée"),
                             MAINTENANT)
        self.assertEqual(propre.score.total, trouble.score.total)
        self.assertIn("cohérence", trouble.fiabilite.motif())

    def test_le_module_de_fiabilite_ne_nomme_aucune_source(self):
        source = (RACINE / "radar" / "fiabilite.py").read_text(encoding="utf-8")
        for nom in ("ted", "google", "bda", "tenderned"):
            self.assertNotIn(f'"{nom}"', source)

    def test_le_rapport_croise_fiabilite_et_score_sans_les_confondre(self):
        from outils.radar_commercial import LOTS, charger, _moteur
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        m = _moteur()
        for fichier, source in LOTS:
            traiter(cx, m, charger(fichier, source), maintenant_dt=MAINTENANT)
        texte = construire(cx, Mode.DEMO).en_texte(avec_fiches=False)
        self.assertIn("FIABILITÉ DE L'INFORMATION ≠ VALEUR ÉCONOMIQUE", texte)
        self.assertIn("jamais", texte)


class VocabulaireVersionne(unittest.TestCase):
    def test_une_expression_apprise_ne_se_propage_pas_a_une_autre_source(self):
        from radar.procedure import reviser, vocabulaire_appris
        cx = ouvrir(":memory:")
        reviser(cx, "portail_a", "statut", "phase active", "postulable", par="t")
        a = vocabulaire_appris(cx, "portail_a")
        b = vocabulaire_appris(cx, "portail_b")
        self.assertIs(lire(statut_source="phase active", vocabulaire=a).etat,
                      EtatProc.POSTULABLE)
        self.assertIs(lire(statut_source="phase active", vocabulaire=b).etat,
                      EtatProc.INCONNU)

    def test_chaque_revision_incremente_la_version(self):
        from radar.procedure import reviser
        cx = ouvrir(":memory:")
        self.assertEqual(reviser(cx, "p", "statut", "x", "postulable", par="a"), 1)
        self.assertEqual(reviser(cx, "p", "statut", "x", "ferme", par="b"), 2)
        l = cx.execute("SELECT version FROM vocabulaire").fetchone()
        self.assertEqual(l["version"], 2)

    def test_la_langue_est_enregistree_jamais_devinee(self):
        cx = ouvrir(":memory:")
        o = opp(source="portail", ref_source="L1", statut_source="phase gamma",
                intitule="Transport", echeance_brute=OUVERT)
        traiter(cx, moteur(), [o], maintenant_dt=MAINTENANT)
        l = cx.execute("SELECT langue FROM vocabulaire").fetchone()
        self.assertEqual(l["langue"], "INCONNUE",
                         "une langue non déclarée n'est pas devinée")

    def test_on_sait_quelles_fiches_dependent_d_une_expression(self):
        from radar.procedure import concerne
        cx = ouvrir(":memory:")
        m = moteur()
        m.vocabulaires["portail"] = Vocabulaire({"procedure": {"types_information": {
            "Phase gamma": {"interpretation": "postulable", "confiance": "moyenne"}}}})
        o = opp(source="portail", ref_source="D1", type_information="Phase gamma",
                intitule="Transport de colis", texte="distribution",
                acheteur="Ville", pays_livraison=["BE"], echeance_brute=OUVERT)
        traiter(cx, m, [o], maintenant_dt=MAINTENANT)
        touchees = concerne(cx, "portail", "type_information", "Phase gamma")
        self.assertEqual(len(touchees), 1)
        self.assertEqual(touchees[0]["etat_procedure"], "POSTULABLE")


# ══════════════ §18 — LE MÊME BESOIN, INJECTÉ PAR SIX CAPTEURS DIFFÉRENTS
def besoin_neutre(source: str, **kw):
    """Un besoin économique décrit SANS vocabulaire de marché public.

    Le banc de test avait un biais : `opp()` porte par défaut
    `type_avis="appel-offres"` et `cpv=["60000000"]`. Presque tous les tests
    faisaient donc passer le moteur par un objet en forme d'appel d'offres.
    Ce constructeur-ci n'a ni CPV, ni type d'avis, ni référence officielle :
    c'est ce qu'une page d'entreprise ou une bourse de fret produit vraiment.
    """
    base = dict(source=source, ref_source=f"N-{source}",
                intitule="Distribution urbaine de marchandises",
                texte="tournées quotidiennes de distribution urbaine pour le "
                      "compte de tiers",
                acheteur="Client Exemple", montant=240000, duree_mois=24,
                cadence="quotidienne", pays_livraison=["BE"],
                distance_depot_km=20, echeance_brute=OUVERT,
                cpv=[], type_avis=None)
    base.update(kw)
    return Opportunite(**base)


CAPTEURS = ("ted", "bda", "tenderned", "recherche", "entreprise", "bourse_fret")


class MemeBesoinSixCapteurs(unittest.TestCase):
    """Seule la PROVENANCE change. Tout le reste doit être identique."""

    def setUp(self):
        self.m = moteur()
        self.resultats = {s: self.m.analyser(besoin_neutre(s), MAINTENANT)
                          for s in CAPTEURS}

    def test_meme_classification_economique(self):
        types = {s: r.classement.type.value for s, r in self.resultats.items()}
        self.assertEqual(len(set(types.values())), 1, types)

    def test_meme_moteur_et_meme_action(self):
        sorties = {s: (r.classement.moteur.value, r.classement.action.value)
                   for s, r in self.resultats.items()}
        self.assertEqual(len(set(sorties.values())), 1, sorties)

    def test_meme_bilan_de_capacite(self):
        bilans = {s: (tuple(r.bilan.atouts), tuple(r.bilan.bloquants),
                      tuple(r.bilan.mobilisations)) for s, r in self.resultats.items()}
        self.assertEqual(len(set(bilans.values())), 1, list(bilans)[:2])

    def test_meme_score(self):
        scores = {s: r.score.total for s, r in self.resultats.items()}
        self.assertEqual(len(set(scores.values())), 1, scores)

    def test_meme_role_et_meme_etat(self):
        lus = {s: (r.role.value, r.lecture.etat.value) for s, r in self.resultats.items()}
        self.assertEqual(len(set(lus.values())), 1, lus)

    def test_une_seule_opportunite_apres_deduplication(self):
        """Six capteurs, un besoin : une opportunité, six provenances."""
        cx = ouvrir(":memory:")
        entrees = [besoin_neutre(s, provenances=[{"source": s, "url": f"https://{s}.be/1"}])
                   for s in CAPTEURS]
        b = traiter(cx, moteur(), entrees, maintenant_dt=MAINTENANT)
        n = cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        self.assertEqual(n, 1, "le même besoin ne doit produire qu'une opportunité")
        self.assertEqual(b.doublons, len(CAPTEURS) - 1)
        fiche = cx.execute("SELECT fiche FROM opportunites").fetchone()["fiche"]
        for s in CAPTEURS:
            self.assertIn(s, fiche, f"la provenance « {s} » doit rester visible")

    def test_le_besoin_neutre_ne_porte_aucun_vocabulaire_de_marche_public(self):
        o = besoin_neutre("recherche")
        self.assertEqual(o.cpv, [])
        self.assertIsNone(o.type_avis)


class RetraitDeChaqueCapteur(unittest.TestCase):
    """Aucun capteur n'est indispensable — un par un, tous retirés tour à tour."""

    def _sans(self, exclu):
        cx = ouvrir(":memory:")
        m = moteur()
        entrees = [besoin_neutre(s, intitule=f"Besoin vu sur {s}",
                                 acheteur=f"Client {s}")
                   for s in CAPTEURS if s != exclu]
        traiter(cx, m, entrees, maintenant_dt=MAINTENANT)
        return cx.execute("SELECT count(*) c FROM opportunites"
                          " WHERE type <> 'REJET'").fetchone()["c"]

    def test_retirer_n_importe_quel_capteur_ne_casse_rien(self):
        for capteur in CAPTEURS:
            with self.subTest(retire=capteur):
                self.assertEqual(self._sans(capteur), len(CAPTEURS) - 1)

    def test_sans_aucun_moteur_de_recherche_le_radar_produit_encore(self):
        """Aucune clé d'API n'est fournie : la découverte web ne démarre pas."""
        from radar.decouverte import charger_connecteur
        self.assertFalse(charger_connecteur({}).disponible)
        cx = ouvrir(":memory:")
        entrees = [besoin_neutre(s, intitule=f"Besoin {s}", acheteur=f"Client {s}")
                   for s in ("entreprise", "bourse_fret", "signaux")]
        traiter(cx, moteur(), entrees, maintenant_dt=MAINTENANT)
        self.assertEqual(cx.execute("SELECT count(*) c FROM opportunites"
                                    " WHERE type <> 'REJET'").fetchone()["c"], 3)


class LeCoeurIgnoreLesCapteurs(unittest.TestCase):
    """Le cœur ne doit connaître ni portail, ni moteur de recherche."""

    COEUR = ("activite", "capacite", "chaine", "classification", "comptes",
             "construction", "deduplication", "fiabilite", "fiche", "geographie",
             "lots", "memoire", "modele", "nature", "procedure", "questions",
             "role", "score", "statut", "transitions")

    def test_aucun_module_du_coeur_n_importe_un_adaptateur(self):
        import ast
        interdits = ("moteurs_recherche", "adaptateur", "decouverte", "boucle", "cli")
        for nom in self.COEUR:
            arbre = ast.parse((RACINE / "radar" / f"{nom}.py").read_text(encoding="utf-8"))
            for n in ast.walk(arbre):
                cibles = ([n.module] if isinstance(n, ast.ImportFrom) and n.module
                          else [a.name for a in n.names] if isinstance(n, ast.Import)
                          else [])
                for c in cibles:
                    self.assertFalse(
                        any(i in c for i in interdits),
                        f"{nom} importe {c} — le cœur doit ignorer les capteurs")

    def test_aucun_nom_de_portail_dans_le_code_du_coeur(self):
        """Les commentaires peuvent citer TED en exemple. Le CODE, non."""
        import ast
        import io
        import re
        import tokenize
        motif = re.compile(r"\b(ted|bda|tenderned|publicprocurement)\b", re.I)
        for nom in self.COEUR:
            src = (RACINE / "radar" / f"{nom}.py").read_text(encoding="utf-8")
            arbre = ast.parse(src)
            ignorees = set()
            for n in ast.walk(arbre):
                if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                  ast.AsyncFunctionDef)) and ast.get_docstring(n):
                    ignorees.update(range(n.body[0].lineno, n.body[0].end_lineno + 1))
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                if tok.type == tokenize.COMMENT:
                    ignorees.add(tok.start[0])
            for i, ligne in enumerate(src.splitlines(), 1):
                if i in ignorees:
                    continue
                code = ligne.split("#", 1)[0]
                self.assertIsNone(motif.search(code),
                                  f"{nom}.py:{i} nomme un portail dans du code")


class SymetriePublicPrive(unittest.TestCase):
    """Trois asymétries trouvées à l'audit. Chacune donnait un avantage
    structurel aux sources publiques."""

    def _role(self, texte, cpv):
        import yaml as _y
        from radar.role import DetecteurDeRole
        d = DetecteurDeRole(_y.safe_load(
            (RACINE / "config" / "roles.yaml").read_text(encoding="utf-8")))
        return d.analyser(texte, cpv).role

    def test_le_prive_dit_prestation_avec_ses_propres_mots(self):
        """Le lexique était écrit en langue de marchés publics : « nous
        recherchons un transporteur » ressortait A_VERIFIER quand un avis
        équivalent ressortait PRESTATAIRE grâce à son CPV."""
        for phrase in ("Nous recherchons un transporteur partenaire pour nos livraisons",
                       "Devenir partenaire transporteur, nous confions nos tournées",
                       "Tournée régulière Rotterdam Bruxelles, 3 rotations par semaine",
                       "Capacité recherchée sur la liaison Anvers-Bruxelles"):
            with self.subTest(phrase=phrase[:40]):
                self.assertIs(self._role(phrase, []), Role.PRESTATAIRE)

    def test_le_lexique_elargi_ne_rachete_pas_une_fourniture(self):
        self.assertIs(self._role("Fourniture et livraison de poissons frais", []),
                      Role.FOURNISSEUR)

    def test_le_lexique_elargi_ne_ratisse_pas_les_metiers_etrangers(self):
        self.assertIs(self._role("Entretien des espaces verts et tonte des haies", []),
                      Role.A_VERIFIER)

    def test_un_cpv_absent_n_empeche_plus_la_fusion_certaine(self):
        """Le CPV est une nomenclature de marchés publics. L'inclure dans
        l'empreinte faisait que le même besoin, public d'un côté et privé de
        l'autre, ne se reconnaissait pas."""
        commun = dict(intitule="Distribution de colis pour la ville de Namur",
                      texte="tournées quotidiennes", acheteur="Ville de Namur",
                      montant=540000, echeance_brute=OUVERT, pays_livraison=["BE"])
        idx = Index()
        idx.ajouter(opp(source="ted", ref_source="T", cpv=["60000000"], **commun))
        r = idx.rapprocher(opp(source="recherche", ref_source="G", cpv=[], **commun))
        self.assertIs(r.confiance, Confiance.CERTAIN)

    def test_deux_cpv_de_familles_differentes_interdisent_encore_la_fusion(self):
        """Le garde-fou reste : ce n'est pas parce que le CPV sort de
        l'empreinte qu'on fusionne un marché de poissons avec un transport."""
        commun = dict(intitule="Marché de la ville de Namur", texte="lot unique",
                      acheteur="Ville de Namur", montant=540000,
                      echeance_brute=OUVERT, pays_livraison=["BE"])
        idx = Index()
        idx.ajouter(opp(source="ted", ref_source="T", cpv=["60000000"], **commun))
        r = idx.rapprocher(opp(source="bda", ref_source="B", cpv=["15200000"], **commun))
        self.assertIs(r.confiance, Confiance.POSSIBLE)
        self.assertIn("CPV", r.motif)

    def test_un_resultat_brave_n_est_pas_etiquete_google(self):
        """Un seul adaptateur lit la forme d'un résultat web ; la provenance
        enregistrée reste celle du moteur qui a réellement répondu."""
        from radar.adaptateur import Adaptateur, vers_opportunite
        from radar.moteurs_recherche import Resultat
        cfg = yaml.safe_load(
            (RACINE / "sources" / "recherche.yaml").read_text(encoding="utf-8"))
        res = Resultat(titre="Transporteur recherché", url="https://ex.be/a",
                       extrait="", requete="q", fournisseur="brave")
        charge = res.en_charge()
        o = vers_opportunite(Adaptateur.depuis_config(cfg), charge,
                             charge["fournisseur"], {})
        self.assertEqual(o.source, "brave")

    def test_l_adaptateur_de_recherche_ne_nomme_aucun_moteur(self):
        cfg = yaml.safe_load(
            (RACINE / "sources" / "recherche.yaml").read_text(encoding="utf-8"))
        self.assertEqual(cfg["source"], "recherche")


class QuatreDimensionsJamaisMelangees(unittest.TestCase):
    """Le défaut trouvé en construisant la section SIGNAUX : elle sélectionnait
    sur l'ÉTAT (dimension B) au lieu de la NATURE (dimension C). Une page
    d'entreprise qui dit ce qu'elle cherche est HORS PROCÉDURE sur B et un FAIT
    sur C — la ranger parmi les signaux présentait un fait comme une inférence."""

    def _n(self, titre, texte="", **kw):
        from radar.nature import qualifier
        return qualifier(Opportunite(source="x", ref_source="r", intitule=titre,
                                     texte=texte, **kw))

    def test_un_besoin_exprime_directement_est_un_fait(self):
        from radar.nature import Nature
        self.assertIs(self._n("Nous recherchons un partenaire transport",
                              "pour nos livraisons"), Nature.FAIT)
        self.assertIs(self._n("Devenir partenaire transporteur",
                              "nous confions nos tournées"), Nature.FAIT)

    def test_un_evenement_observable_est_un_signal(self):
        from radar.nature import Nature
        self.assertIs(self._n("Recrutement de 15 chauffeurs", "distribution",
                              est_signal=True), Nature.SIGNAL)
        self.assertIs(self._n("Marché attribué", "distribution", attribue=True),
                      Nature.SIGNAL)

    def test_une_page_qui_ne_dit_rien_reste_une_hypothese(self):
        from radar.nature import Nature
        self.assertIs(self._n("Page", "du transport quelque part"), Nature.HYPOTHESE)

    def test_hors_procedure_n_est_pas_un_signal(self):
        """B et C sont indépendantes : une page sans procédure peut être un
        fait, et un marché public en cours peut être un signal (attribution)."""
        r = moteur().analyser(
            opp(source="entreprise", ref_source="E9", cpv=[], type_avis=None,
                intitule="Devenir partenaire transporteur",
                texte="nous confions nos tournées à des transporteurs partenaires",
                acheteur="PME Exemple", pays_livraison=["BE"],
                echeance_brute=None), MAINTENANT)
        self.assertEqual(r.lecture.etat_affiche, "HORS PROCÉDURE")
        self.assertEqual(r.nature.value, "FAIT")

    def test_le_rapport_range_les_signaux_par_nature_pas_par_etat(self):
        from outils.radar_commercial import LOTS, charger, _moteur
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        m = _moteur()
        for fichier, source in LOTS:
            traiter(cx, m, charger(fichier, source), maintenant_dt=MAINTENANT)
        r = construire(cx, Mode.DEMO)
        natures = {n for _, _, _, n in r.signaux}
        self.assertTrue(natures <= {"SIGNAL", "HYPOTHÈSE"},
                        f"un FAIT ne doit pas figurer parmi les signaux : {natures}")

    def test_le_rapport_porte_les_cinq_blocs_du_produit(self):
        from outils.radar_commercial import LOTS, charger, _moteur
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        m = _moteur()
        for fichier, source in LOTS:
            traiter(cx, m, charger(fichier, source), maintenant_dt=MAINTENANT)
        texte = construire(cx, Mode.DEMO).en_texte(avec_fiches=False)
        for bloc in ("CAPTER", "DÉVELOPPER", "SIGNAUX", "À VÉRIFIER", "TOP ACTIONS"):
            self.assertIn(bloc, texte)
        self.assertLess(texte.index("TOP ACTIONS"), texte.index("COLLECTE"),
                        "les actions passent avant les statistiques de source")


# ══════════════ §10 — LE MÊME BESOIN ÉCONOMIQUE SOUS SIX FORMES
#
# Le besoin est identique : 180 000 € sur 24 mois, tournées quotidiennes en
# Belgique, à 20 km du dépôt. Seule la FORME de l'information change.
BESOIN = dict(montant=180000, duree_mois=24, cadence="quotidienne",
              pays_livraison=["BE"], distance_depot_km=20,
              intitule="Distribution urbaine de marchandises",
              texte="tournées quotidiennes de distribution urbaine pour le "
                    "compte de tiers")


def _forme(nom, **kw):
    base = dict(source=nom, ref_source=f"F-{nom}", acheteur="Client Exemple",
                echeance_brute=OUVERT, cpv=[], type_avis=None)
    base.update(BESOIN)
    base.update(kw)
    return Opportunite(**base)


FORMES = {
    # A · appel d'offres public : porte un CPV, un type d'avis, une référence
    "appel_offres": _forme("ted", ref_source="TED-9001", cpv=["60000000"],
                           type_avis="contract-notice", secteur_acheteur="public"),
    # B · page privée : rien de tout cela
    "page_privee": _forme("entreprise", secteur_acheteur="privé"),
    # C · résultat de moteur de recherche
    "recherche": _forme("brave", ref_source="https://ex.be/besoin",
                        secteur_acheteur="privé"),
    # D · bourse de fret
    "bourse_fret": _forme("bourse_fret", secteur_acheteur="privé"),
    # E · page d'entreprise avec contact
    "page_entreprise": _forme("entreprise", ref_source="F-ent2",
                              contact="logistique@ex.be", secteur_acheteur="privé"),
    # F · signal économique — même besoin, mais déduit d'un événement
    "signal": _forme("signaux", est_signal=True, signal_code="ouverture_site",
                     secteur_acheteur="privé"),
}


class MemeBesoinSixFormes(unittest.TestCase):
    """Capacité, économie et score IDENTIQUES. Seul change ce qui dépend
    réellement de la nature de l'information : action, fiabilité, état, nature,
    provenance."""

    def setUp(self):
        m = moteur()
        self.r = {nom: m.analyser(o, MAINTENANT) for nom, o in FORMES.items()}

    def _unique(self, extraire, quoi):
        valeurs = {nom: extraire(r) for nom, r in self.r.items()}
        self.assertEqual(len(set(valeurs.values())), 1, f"{quoi} diverge : {valeurs}")

    def test_capacite_identique(self):
        self._unique(lambda r: (tuple(r.bilan.atouts), tuple(r.bilan.bloquants),
                                tuple(r.bilan.mobilisations), tuple(r.bilan.remedes)),
                     "le bilan de capacité")

    def test_economie_identique(self):
        self._unique(lambda r: (r.score.marge_estimee,
                                tuple(l.split(" ")[0] for l in r.score.detail())),
                     "le détail économique")

    def test_score_identique(self):
        self._unique(lambda r: r.score.total, "le score")

    def test_classification_identique(self):
        """Sauf le signal, qui EST une catégorie d'information différente."""
        sans_signal = {n: r.classement.type.value
                       for n, r in self.r.items() if n != "signal"}
        self.assertEqual(len(set(sans_signal.values())), 1, sans_signal)

    def test_un_signal_reste_un_prospect_meme_a_economie_egale(self):
        """Ce n'est PAS un biais de source : c'est la dimension C qui parle.
        Une inférence ne se présente pas comme un contrat ouvert."""
        self.assertEqual(self.r["signal"].classement.type.value, "PROSPECT")
        self.assertEqual(self.r["signal"].nature.value, "SIGNAL")
        self.assertEqual(self.r["signal"].score.total,
                         self.r["appel_offres"].score.total,
                         "mais son économie reste la même")

    def test_l_action_a_LE_DROIT_de_changer(self):
        actions = {n: r.classement.action.value for n, r in self.r.items()}
        self.assertGreater(len(set(actions.values())), 1,
                           "l'action doit dépendre de la nature de l'information")

    def test_la_fiabilite_suit_les_PREUVES_pas_l_officialite(self):
        """Ces six formes portent les mêmes preuves : leur fiabilité est donc
        la même, y compris pour l'appel d'offres. Ce qui la fait bouger, c'est
        un lien, un contact, une référence — jamais le caractère officiel."""
        self.assertEqual(len({r.fiabilite.niveau for r in self.r.values()}), 1,
                         "à preuves égales, fiabilité égale")
        m = moteur()
        nu = m.analyser(_forme("ted", ref_source="SANS-REF-x", acheteur=None,
                               type_avis="contract-notice", cpv=["60000000"]),
                        MAINTENANT)
        etoffe = m.analyser(_forme("entreprise", ref_source="ENT-77",
                                   plateforme="https://ex.be/partenaires",
                                   contact="logistique@ex.be"), MAINTENANT)
        ordre = ["NULLE", "FAIBLE", "MOYENNE", "FORTE"]
        self.assertGreater(ordre.index(etoffe.fiabilite.niveau.value),
                           ordre.index(nu.fiabilite.niveau.value),
                           "une page privée bien documentée doit battre un avis "
                           "officiel qui ne prouve rien")
        self.assertEqual(nu.score.total, etoffe.score.total,
                         "et la fiabilité ne touche jamais le score")


class CentBesoinsPrivesSeuls(unittest.TestCase):
    """§12 — cent besoins privés, aucun appel d'offres. Le radar doit tout
    faire : analyser, classer, capacité, score, doublons, CAPTER/DÉVELOPPER,
    actions, rapport complet."""

    N = 100

    def _lot(self, prefixe, publique: bool):
        lot = []
        for i in range(self.N):
            commun = dict(intitule=f"Distribution urbaine — client {i}",
                          texte="tournées quotidiennes de distribution pour le "
                                "compte de tiers",
                          acheteur=f"Client {i}", montant=90000 + i * 900,
                          duree_mois=24, cadence="quotidienne",
                          pays_livraison=["BE"], distance_depot_km=15 + i % 40,
                          echeance_brute=OUVERT)
            if publique:
                lot.append(Opportunite(source="bda", ref_source=f"{prefixe}-{i}",
                                       cpv=["60000000"], type_avis="avis de marché",
                                       secteur_acheteur="public", **commun))
            else:
                lot.append(Opportunite(source="entreprise", ref_source=f"{prefixe}-{i}",
                                       cpv=[], type_avis=None,
                                       secteur_acheteur="privé", **commun))
        # deux doublons volontaires, pour éprouver la déduplication
        lot.append(Opportunite(source="brave", ref_source=f"{prefixe}-dup",
                               cpv=[], type_avis=None,
                               intitule="Distribution urbaine — client 3",
                               texte="tournées quotidiennes de distribution pour "
                                     "le compte de tiers",
                               acheteur="Client 3", montant=92700, duree_mois=24,
                               cadence="quotidienne", pays_livraison=["BE"],
                               distance_depot_km=18, echeance_brute=OUVERT))
        return lot

    def _passer(self, publique):
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        b = traiter(cx, moteur(), self._lot("P" if publique else "V", publique),
                    maintenant_dt=MAINTENANT)
        return cx, b, construire(cx, Mode.DEMO,
                                 cible={"montant_total_confortable_max": 1500000})

    def _verifier(self, cx, b, r, contexte):
        self.assertEqual(b.lus, self.N + 1, f"{contexte} : toutes les lignes lues")
        self.assertEqual(b.livre.ecart(), 0, f"{contexte} : réconciliation")
        self.assertEqual(b.doublons, 1, f"{contexte} : le doublon est détecté")
        n = cx.execute("SELECT count(*) c FROM opportunites"
                       " WHERE type <> 'REJET'").fetchone()["c"]
        self.assertEqual(n, self.N, f"{contexte} : {self.N} opportunités")
        # capacité, économie, actions
        sans_capacite = cx.execute(
            "SELECT count(*) c FROM opportunites WHERE fiche NOT LIKE '%CE QUE J''AI%'"
        ).fetchone()["c"]
        self.assertEqual(sans_capacite, 0, f"{contexte} : chaque fiche a sa capacité")
        self.assertTrue(all(l["score"] > 0 for l in cx.execute(
            "SELECT score FROM opportunites WHERE type <> 'REJET'")),
            f"{contexte} : chaque opportunité est notée")
        self.assertTrue(b.capter + b.developper > 0, f"{contexte} : CAPTER/DÉVELOPPER")
        self.assertTrue(r.actions, f"{contexte} : des actions sont produites")
        texte = r.en_texte(avec_fiches=False)
        for bloc in ("CAPTER", "DÉVELOPPER", "TOP ACTIONS", "COLLECTE",
                     "FIABILITÉ DE L'INFORMATION", "ÉCONOMIE"):
            self.assertIn(bloc, texte, f"{contexte} : le rapport porte {bloc}")

    def test_cent_besoins_prives_produisent_un_radar_complet(self):
        cx, b, r = self._passer(publique=False)
        self._verifier(cx, b, r, "100 % privé")
        etats = {l["etat_procedure"] for l in cx.execute(
            "SELECT etat_procedure FROM opportunites")}
        self.assertNotIn("INCONNU", etats,
                         "un besoin privé clair ne doit pas finir « à vérifier »")

    def test_cent_appels_d_offres_produisent_un_radar_complet(self):
        cx, b, r = self._passer(publique=True)
        self._verifier(cx, b, r, "100 % public")

    def test_les_deux_lots_donnent_les_memes_scores(self):
        """Cent besoins identiques, l'un public l'autre privé : mêmes scores."""
        cxv, _, _ = self._passer(publique=False)
        cxp, _, _ = self._passer(publique=True)
        prive = [l["score"] for l in cxv.execute(
            "SELECT score FROM opportunites ORDER BY intitule")]
        public = [l["score"] for l in cxp.execute(
            "SELECT score FROM opportunites ORDER BY intitule")]
        self.assertEqual(prive, public)


class LAbsenceNEstPasUnAvantage(unittest.TestCase):
    """Une source qui ne publie AUCUNE exigence produisait un bilan vide,
    indistinguable de « tout est couvert » — et gagnait les points pleins.
    Une annonce muette notait donc mieux qu'une annonce précise, et NON MESURÉ
    était traité comme un zéro favorable."""

    def _score(self, **kw):
        base = dict(intitule="Distribution urbaine de marchandises",
                    texte="tournées quotidiennes de distribution urbaine",
                    acheteur="Client", montant=180000, duree_mois=24,
                    cadence="quotidienne", pays_livraison=["BE"],
                    echeance_brute=OUVERT)
        base.update(kw)
        return moteur().analyser(opp(**base), MAINTENANT)

    def test_les_trois_cas_d_exigence_sont_distincts(self):
        """PUBLIÉE ET COUVERTE · PUBLIÉE ET NON COUVERTE · AUCUNE PUBLIÉE.
        Trois situations, trois libellés, trois niveaux de points."""
        muette = self._score(ref_source="M")
        couverte = self._score(ref_source="C",
                               exigences={"licence_transport": True})
        non_couverte = self._score(ref_source="N", exigences={"vehicules_min": 12})

        def ligne(r):
            return next(l for l in r.score.detail() if "accessibilité" in l)

        self.assertIn("AUCUNE EXIGENCE PUBLIÉE", ligne(muette))
        self.assertIn("NON MESURÉ", ligne(muette))
        self.assertIn("PUBLIÉE ET COUVERTE", ligne(couverte))
        self.assertIn("PUBLIÉE ET NON COUVERTE", ligne(non_couverte))

    def test_une_exigence_juridiquement_inaccessible_annule_l_accessibilite(self):
        r = self._score(ref_source="ADR", exigences={"adr": True})
        ligne = next(l for l in r.score.detail() if "accessibilité" in l)
        self.assertIn("+0", ligne)
        self.assertIn("PUBLIÉE ET NON COUVERTE", ligne)

    def test_une_annonce_muette_ne_bat_pas_une_annonce_couverte(self):
        muette = self._score(ref_source="M")
        couverte = self._score(ref_source="C", exigences={"licence_transport": True})
        self.assertGreater(couverte.score.total, muette.score.total,
                           "publier des exigences qu'on couvre doit valoir mieux "
                           "que ne rien publier")

    def test_le_demarrage_non_publie_n_est_pas_un_demarrage_immediat(self):
        lignes = " ".join(self._score().score.detail())
        self.assertIn("moyens nécessaires NON PUBLIÉS", lignes)


class RapportParFamilleDeBesoin(unittest.TestCase):
    """Le rapport s'organise par FAMILLE DE BESOIN, pas par portail."""

    def _rapport(self):
        from outils.familles import FAMILLES, charger, moteur as m_familles
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        m = m_familles()
        for nom, _, _, _ in FAMILLES:
            traiter(cx, m, charger(nom), maintenant_dt=MAINTENANT)
        return construire(cx, Mode.DEMO,
                          cible={"montant_total_confortable_max": 1500000})

    def test_les_sept_familles_sont_toujours_affichees(self):
        texte = self._rapport().en_texte(avec_fiches=False)
        for famille in ("BESOINS PRIVÉS", "MARCHÉS PUBLICS",
                        "SOUS-TRAITANCE ET PARTENARIAT", "ENTREPRISES À DÉMARCHER",
                        "SIGNAUX ÉCONOMIQUES", "RENOUVELLEMENTS À ANTICIPER",
                        "MÉTIERS À CONSTRUIRE"):
            self.assertIn(famille, texte)

    def test_les_marches_publics_ne_sont_pas_la_famille_majoritaire(self):
        r = self._rapport()
        total = sum(len(v) for v in r.familles.values())
        publics = len(r.familles.get("MARCHÉS PUBLICS", []))
        self.assertLess(publics / total, 0.5,
                        f"les marchés publics dominent le radar : {publics}/{total}")

    def test_la_famille_se_lit_sur_le_besoin_pas_sur_la_source(self):
        from radar.rapport import famille_de
        besoin_public_via_google = {"type": "DIRECT", "nature": "FAIT",
                                    "etat_procedure": "POSTULABLE", "action": "POSTULER",
                                    "secteur": "public", "echeance": "2099-01-01"}
        self.assertEqual(famille_de(besoin_public_via_google), "MARCHÉS PUBLICS")
        besoin_prive_via_ted = dict(besoin_public_via_google, secteur="privé")
        self.assertEqual(famille_de(besoin_prive_via_ted), "BESOINS PRIVÉS")

    def test_les_familles_passent_avant_les_sources(self):
        texte = self._rapport().en_texte(avec_fiches=False)
        self.assertLess(texte.index("PAR FAMILLE DE BESOIN"), texte.index("COLLECTE"))


class LesDouzeFamillesTraversentLeMoteur(unittest.TestCase):
    """§3 — douze familles de besoin, publiques et privées, un seul moteur."""

    def test_chaque_famille_produit_au_moins_une_opportunite(self):
        from outils.familles import FAMILLES, charger, moteur as m_familles
        m = m_familles()
        for nom, _, _, _ in FAMILLES:
            with self.subTest(famille=nom):
                cx = ouvrir(":memory:")
                b = traiter(cx, m, charger(nom), maintenant_dt=MAINTENANT)
                self.assertEqual(b.livre.ecart(), 0)
                retenues = cx.execute("SELECT count(*) c FROM opportunites"
                                      " WHERE type <> 'REJET'").fetchone()["c"]
                self.assertGreater(retenues, 0, f"« {nom} » ne produit rien")

    def test_le_radar_tourne_sans_aucune_famille_publique(self):
        from outils.familles import PRIVEES, passer
        cx, b = passer(sorted(PRIVEES))
        self.assertEqual(b.livre.ecart(), 0)
        self.assertGreater(b.capter + b.developper, 0)

    def test_le_radar_tourne_sans_aucune_famille_privee(self):
        from outils.familles import PUBLIQUES, passer
        cx, b = passer(sorted(PUBLIQUES))
        self.assertEqual(b.livre.ecart(), 0)
        self.assertGreater(b.capter + b.developper, 0)

    def test_retirer_n_importe_quelle_famille_ne_casse_rien(self):
        from outils.familles import FAMILLES, passer
        noms = [f[0] for f in FAMILLES]
        for exclue in noms:
            with self.subTest(sans=exclue):
                _, b = passer([n for n in noms if n != exclue])
                self.assertEqual(b.livre.ecart(), 0)
                self.assertGreater(b.capter + b.developper, 0)

    def test_le_banc_d_essai_n_est_plus_majoritairement_public(self):
        """Le biais mesuré : 94 % des opportunités construites portaient un CPV
        et un type d'avis. Le défaut du constructeur est maintenant un besoin nu."""
        o = opp()
        self.assertEqual(o.cpv, [])
        self.assertIsNone(o.type_avis)
        self.assertEqual(avis_public().cpv, ["60000000"])


# ══════════════ LE SCORE RÉAGIT À L'ÉCONOMIE, PAS À LA NATURE DE L'INFORMATION
#
# Deux tests réciproques. Le premier fige l'économie et fait varier la nature :
# rien ne doit bouger. Le second fige la nature et fait varier UNE seule
# variable économique : le score doit bouger, et dans le bon sens.
ECONOMIE_TEMOIN = dict(
    intitule="Distribution urbaine de marchandises",
    texte="tournées quotidiennes de distribution urbaine pour le compte de tiers",
    montant=180000, duree_mois=24, cadence="hebdomadaire",
    pays_livraison=["BE"], distance_depot_km=120, km_annuels=30000,
    exigences={"licence_transport": True}, acheteur="Client Exemple")
# Volontairement PAS au plafond : le score est borné à 0-100, et un témoin à
# 100 rendrait toute pénalité invisible. On mesure des variations, pas un idéal.


def _temoin(**kw):
    base = dict(source="entreprise", ref_source="T", cpv=[], type_avis=None,
                echeance_brute=OUVERT)
    base.update(ECONOMIE_TEMOIN)
    base.update(kw)
    return Opportunite(**base)


NATURES_TEMOIN = {
    "A_marche_public": _temoin(source="bda", ref_source="A", cpv=["60000000"],
                               type_avis="avis de marché", secteur_acheteur="public"),
    "B_contrat_prive": _temoin(source="entreprise", ref_source="B",
                               secteur_acheteur="privé"),
    "C_sous_traitance": _temoin(source="entreprise", ref_source="C",
                                texte=ECONOMIE_TEMOIN["texte"] + " en sous-traitance",
                                secteur_acheteur="privé"),
    "D_signal_recrutement": _temoin(source="signaux", ref_source="D", est_signal=True,
                                    signal_code="recrutement_massif",
                                    secteur_acheteur="privé"),
    "E_page_partenaire": _temoin(source="entreprise", ref_source="E",
                                 intitule="Devenir partenaire transporteur",
                                 secteur_acheteur="privé"),
    "F_attribution": _temoin(source="ted", ref_source="F", attribue=True,
                             titulaire="Transport National SA",
                             secteur_acheteur="public"),
}


class MemeEconomieNaturesDifferentes(unittest.TestCase):
    """A→F : même économie, six natures. Valeur économique, score et capacité
    identiques. Seuls nature, fiabilité, état, action et provenance changent."""

    def setUp(self):
        m = moteur()
        self.r = {n: m.analyser(o, MAINTENANT) for n, o in NATURES_TEMOIN.items()}

    def test_le_score_est_identique(self):
        scores = {n: r.score.total for n, r in self.r.items()}
        self.assertEqual(len(set(scores.values())), 1, scores)

    def test_la_valeur_economique_ligne_a_ligne_est_identique(self):
        """Pas seulement le total : chaque critère doit être au même niveau."""
        detail = {n: tuple(r.score.detail()) for n, r in self.r.items()}
        self.assertEqual(len(set(detail.values())), 1,
                         "\n".join(f"{n} : {d}" for n, d in list(detail.items())[:2]))

    def test_la_capacite_est_identique(self):
        bilans = {n: (tuple(r.bilan.atouts), tuple(r.bilan.bloquants),
                      tuple(r.bilan.mobilisations), tuple(r.bilan.a_verifier))
                  for n, r in self.r.items()}
        self.assertEqual(len(set(bilans.values())), 1)

    def test_le_signal_ne_gagne_rien_a_etre_muet(self):
        """Le piège inverse : un signal ne doit pas non plus profiter de son
        silence. Ici il porte les mêmes données que les autres, il note pareil."""
        self.assertEqual(self.r["D_signal_recrutement"].score.total,
                         self.r["A_marche_public"].score.total)

    def test_ce_qui_change_est_exactement_ce_qui_doit_changer(self):
        change = {
            "nature": {r.nature.value for r in self.r.values()},
            "état": {r.lecture.etat_affiche for r in self.r.values()},
            "action": {r.classement.action.value for r in self.r.values()},
            "provenance": {NATURES_TEMOIN[n].source for n in self.r},
        }
        for dimension, valeurs in change.items():
            self.assertGreater(len(valeurs), 1,
                               f"{dimension} devrait dépendre de la forme")
        fige = {
            "score": {r.score.total for r in self.r.values()},
            "capacité": {tuple(r.bilan.bloquants) for r in self.r.values()},
            "marge": {r.score.marge_estimee for r in self.r.values()},
        }
        for dimension, valeurs in fige.items():
            self.assertEqual(len(valeurs), 1,
                             f"{dimension} ne doit PAS dépendre de la forme")

    def test_une_attribution_garde_sa_valeur_economique(self):
        """Elle change de moteur, pas de valeur : le titulaire devra exécuter."""
        a = self.r["F_attribution"]
        self.assertEqual(a.classement.moteur.value, "DEVELOPPER")
        self.assertEqual(a.score.total, self.r["A_marche_public"].score.total)


class LeScoreReagitALEconomie(unittest.TestCase):
    """Le test réciproque. Même nature, même source, même besoin — une seule
    variable économique bouge. Sans lui, « score identique partout » pourrait
    simplement vouloir dire « le score ne mesure rien »."""

    def _score(self, **kw):
        return moteur().analyser(_temoin(**kw), MAINTENANT).score.total

    def setUp(self):
        self.reference = self._score()

    def test_un_montant_hors_cible_fait_baisser_le_score(self):
        self.assertLess(self._score(ref_source="gros", montant=8_000_000),
                        self.reference)

    def test_un_contrat_plus_court_fait_baisser_le_score(self):
        self.assertLess(self._score(ref_source="court", duree_mois=1,
                                    cadence="ponctuelle"), self.reference)

    def test_l_eloignement_fait_baisser_le_score(self):
        self.assertLess(self._score(ref_source="loin", distance_depot_km=400),
                        self.reference)

    def test_un_kilometrage_lourd_fait_baisser_le_score(self):
        self.assertLess(self._score(ref_source="km", km_annuels=95000),
                        self.reference)

    def test_une_exigence_hors_capacite_fait_baisser_le_score(self):
        self.assertLess(self._score(ref_source="gros_parc",
                                    exigences={"vehicules_min": 40}), self.reference)

    def test_le_travail_de_nuit_et_de_weekend_fait_baisser_le_score(self):
        self.assertLess(self._score(ref_source="nuit", travail_nuit=True,
                                    travail_weekend=True), self.reference)

    def test_la_proximite_fait_monter_le_score(self):
        loin = self._score(ref_source="l", distance_depot_km=400)
        pres = self._score(ref_source="p", distance_depot_km=10)
        self.assertGreater(pres, loin)

    def test_chaque_variable_economique_a_un_effet_mesurable(self):
        """Aucune ne doit être décorative : si l'une ne change rien, le critère
        ment sur ce qu'il prétend mesurer."""
        variations = {
            "montant": dict(montant=8_000_000),
            "durée": dict(duree_mois=1, cadence="ponctuelle"),
            "distance": dict(distance_depot_km=400),
            "kilométrage": dict(km_annuels=95000),
            "capacité": dict(exigences={"vehicules_min": 40}),
            "horaires": dict(travail_nuit=True, travail_weekend=True),
        }
        for nom, kw in variations.items():
            with self.subTest(variable=nom):
                self.assertNotEqual(self._score(ref_source=nom, **kw), self.reference,
                                    f"« {nom} » n'a aucun effet sur le score")


class LAdequationMesureLAptitudePasLaVerbosite(unittest.TestCase):
    """Défaut trouvé en décomposant le 77 d'un signal : l'adéquation donnait la
    moitié des points pour une famille reconnue et le plein pour deux. Un texte
    bavard battait donc un intitulé précis, à besoin égal — et les sources qui
    écrivent long (communiqués, pages web) y gagnaient mécaniquement."""

    def _adequation(self, texte):
        r = moteur().analyser(_temoin(ref_source="A", intitule=texte, texte=texte),
                              MAINTENANT)
        ligne = next(l for l in r.score.detail() if "adéquation" in l)
        return float(ligne.split("+")[1].split(" ")[0])

    def test_un_intitule_precis_vaut_autant_qu_un_texte_bavard(self):
        precis = self._adequation("distribution de colis")
        bavard = self._adequation("distribution urbaine de marchandises, logistique, "
                                  "entreposage, tri de colis et messagerie")
        self.assertEqual(precis, bavard)

    def test_un_domaine_sans_specialite_vaut_moins_qu_un_metier_reconnu(self):
        reconnu = self._adequation("distribution de colis")
        domaine = self._adequation("prestation de transport non détaillée")
        self.assertLess(domaine, reconnu)
        self.assertGreater(domaine, 0, "le domaine reconnu n'est pas zéro")

    def test_un_metier_etranger_ne_gagne_aucun_point_d_adequation(self):
        self.assertEqual(self._adequation("entretien des espaces verts et tonte"), 0)


class LePlafondDuScoreEstUneLimiteConnue(unittest.TestCase):
    """Le score est borné à 0-100. Deux opportunités excellentes mais inégales
    peuvent donc plafonner ensemble et devenir impossibles à départager.

    Ce test ne corrige rien : il DOCUMENTE la limite, pour qu'elle ne soit pas
    découverte le jour où deux vraies affaires arrivent à égalité.
    """

    def _tres_bon(self, **kw):
        base = dict(source="entreprise", ref_source="X", cpv=[], type_avis=None,
                    intitule="Distribution urbaine de marchandises",
                    texte="tournées quotidiennes de distribution urbaine",
                    acheteur="Client", montant=180000, duree_mois=24,
                    cadence="quotidienne", pays_livraison=["BE"],
                    distance_depot_km=10, km_annuels=15000,
                    exigences={"licence_transport": True}, echeance_brute=OUVERT)
        base.update(kw)
        return moteur().analyser(Opportunite(**base), MAINTENANT).score.total

    def test_deux_excellentes_opportunites_restent_departageables(self):
        """Limite LEVÉE. Le score coupait à 100 sur une somme atteignable
        d'environ 120 : les meilleures affaires arrivaient à égalité, exactement
        là où le radar doit trancher. Il normalise désormais au lieu de
        tronquer — l'ordre est conservé jusqu'en haut."""
        # 5 km et 45 km sont dans la MÊME bande « confortable » : ils valent
        # bien le même nombre de points, et c'est voulu. On compare donc deux
        # bandes différentes, ce qui est la vraie question économique.
        proche = self._tres_bon(ref_source="A", distance_depot_km=20)
        loin = self._tres_bon(ref_source="B", distance_depot_km=200)
        self.assertGreater(proche, loin)
        self.assertLessEqual(proche, 100)

    def test_le_plafond_ne_s_atteint_que_sur_un_cas_parfait(self):
        ordinaire = self._tres_bon(ref_source="C", distance_depot_km=45,
                                   cadence="hebdomadaire")
        self.assertLess(ordinaire, 100)

    def test_sous_le_plafond_les_variations_restent_visibles(self):
        loin = self._tres_bon(ref_source="C", distance_depot_km=400,
                              cadence="ponctuelle", km_annuels=70000,
                              exigences={"vehicules_min": 12})
        proche = self._tres_bon(ref_source="D", distance_depot_km=20,
                                cadence="ponctuelle", km_annuels=70000,
                                exigences={"vehicules_min": 12})
        self.assertLess(loin, proche)
        self.assertLess(proche, 100)


class AuditDeRealisme(unittest.TestCase):
    """Le corpus de formulations devient un filet de sécurité permanent.

    Il ne prouve pas que le moteur comprend le monde — il a été écrit puis le
    moteur corrigé contre lui. Il prouve qu'aucune régression ne repassera sur
    les 78 formulations dont on sait déjà qu'elles posaient problème.
    """

    def test_le_corpus_ne_declare_aucune_donnee_reelle(self):
        corpus = yaml.safe_load((RACINE / "validation" /
                                 "corpus_formulations.yaml").read_text(encoding="utf-8"))
        self.assertEqual(corpus["meta"]["pages_reelles_observees"], 0)
        self.assertEqual(corpus["meta"]["origine_par_defaut"], "invente")

    def test_aucune_formulation_du_corpus_n_est_mal_comprise(self):
        from outils.audit_realisme import _etat_lu
        corpus = yaml.safe_load((RACINE / "validation" /
                                 "corpus_formulations.yaml").read_text(encoding="utf-8"))
        fautes = []
        for f in corpus["formulations"]:
            if f.get("champ") == "statut":
                lecture = lire(statut_source=f["texte"], source="portail-test")
            else:
                lecture = lire(texte=f["texte"])
            obtenu = _etat_lu(lecture)
            if obtenu != f["attendu"] and obtenu not in ("INCONNU", "HORS_PROCEDURE"):
                fautes.append(f"« {f['texte']} » attendu {f['attendu']}, lu {obtenu}")
        self.assertEqual(fautes, [], "\n".join(fautes))

    def test_offres_non_recevables_n_est_jamais_postulable(self):
        """Le pire cas trouvé par l'audit : « non » manquait des négations, et
        « offres non recevables » ressortait POSTULABLE — inviter à monter un
        dossier sur un marché fermé."""
        self.assertIsNot(lire(texte="offres non recevables").etat,
                         EtatProc.POSTULABLE)

    def test_une_date_depassee_bat_la_rubrique_du_portail(self):
        voc = Vocabulaire({"procedure": {"types_information": {
            "Marchés en cours": {"interpretation": "postulable", "confiance": "moyenne"}}}})
        l = lire(type_information="Marchés en cours",
                 echeance=datetime(2026, 1, 1, tzinfo=timezone.utc),
                 maintenant=MAINTENANT, vocabulaire=voc)
        self.assertIs(l.etat, EtatProc.FERME,
                      "une échéance passée est un fait, la rubrique un classement")

    def test_une_attribution_annoncee_ne_laisse_pas_postuler(self):
        voc = Vocabulaire({"procedure": {"types_information": {
            "Marchés en cours": {"interpretation": "postulable", "confiance": "moyenne"}}}})
        l = lire(type_information="Marchés en cours",
                 texte="L'attribution sera prononcée prochainement.", vocabulaire=voc)
        self.assertIsNot(l.etat, EtatProc.POSTULABLE)

    def test_une_echeance_posterieure_au_demarrage_est_illisible(self):
        """Contradiction dans les données publiées : elle produisait un délai de
        -25 551 jours, traité comme « insuffisant » au lieu de « illisible »."""
        o = opp(ref_source="CONTRA", intitule="Installation de bornes",
                texte="véhicules utilitaires et personnel de terrain, formation "
                      "complète de trois semaines assurée",
                echeance_brute="2099-05-15T12:00:00+02:00",
                date_demarrage="2029-06-01", acheteur="Opérateur")
        r = moteur().analyser(o, MAINTENANT)
        manques = " ".join((r.construction.manques if r.construction else []))
        self.assertNotIn("-", manques, "aucun délai négatif ne doit être affiché")

    def test_les_quatre_lots_gardent_quatre_etats_distincts(self):
        from outils.audit_realisme import epreuve_lots, Matrice
        import io
        import contextlib
        m = Matrice()
        with contextlib.redirect_stdout(io.StringIO()):
            epreuve_lots(m, False)
        self.assertEqual(m.incorrects, 0)

    def test_les_cent_opportunites_melangees_retrouvent_leur_famille(self):
        from outils.audit_realisme import epreuve_cent, Matrice
        import io
        import contextlib
        m = Matrice()
        with contextlib.redirect_stdout(io.StringIO()):
            epreuve_cent(m, False)
        self.assertEqual(m.par_dimension["familles retrouvées"]["INCORRECT"], 0)


class LeRadarFonctionneSansMarchesPublics(unittest.TestCase):
    """Aucun marché public. Aucun CPV. Aucun publication-number. Aucune
    procédure. Le radar doit produire une chaîne COMPLÈTE.

    Si cette classe échoue, le projet n'est pas un radar commercial : c'est un
    moteur d'appels d'offres auquel on a ajouté des sources privées autour.
    """

    FAMILLES = ("besoin_prive", "sous_traitance", "partenariat",
                "entreprise_a_demarcher", "signal_economique", "emploi_signal",
                "metier_inconnu")

    def setUp(self):
        from outils.familles import charger, moteur as m_familles
        from radar.rapport import construire
        self.cx = ouvrir(":memory:")
        m = m_familles()
        self.entrees = []
        for f in self.FAMILLES:
            self.entrees += charger(f)
        self.bilan = traiter(self.cx, m, self.entrees, maintenant_dt=MAINTENANT)
        self.rapport = construire(self.cx, Mode.DEMO,
                                  cible={"montant_total_confortable_max": 1500000})

    def test_aucune_entree_ne_porte_de_marqueur_de_marche_public(self):
        for o in self.entrees:
            self.assertEqual(o.cpv, [], f"{o.ref_source} porte un CPV")
            self.assertFalse((o.ref_source or "").startswith("TED-"))
            self.assertNotEqual((o.secteur_acheteur or "").lower(), "public")

    def test_la_chaine_va_jusqu_au_bout(self):
        self.assertEqual(self.bilan.livre.ecart(), 0)
        for l in self.cx.execute("SELECT * FROM opportunites WHERE type <> 'REJET'"):
            ref = l["intitule"]
            self.assertTrue(l["type"], f"{ref} : pas de classification")
            self.assertTrue(l["moteur"], f"{ref} : pas de moteur")
            self.assertTrue(l["action"], f"{ref} : pas d'action")
            self.assertTrue(l["nature"], f"{ref} : pas de nature")
            self.assertTrue(l["fiabilite"], f"{ref} : pas de fiabilité")
            self.assertGreater(l["score"], 0, f"{ref} : score nul")
            self.assertIn("CE QUE J'AI", l["fiche"], f"{ref} : pas de capacité")
            self.assertTrue(l["zone"], f"{ref} : pas de zone")
            self.assertTrue(l["journal"], f"{ref} : pas de journal")

    def test_le_rapport_est_complet_sans_le_moindre_marche_public(self):
        texte = self.rapport.en_texte(avec_fiches=False)
        for bloc in ("CAPTER", "DÉVELOPPER", "SIGNAUX", "PAR FAMILLE DE BESOIN",
                     "TOP ACTIONS", "COMPLÉTUDE", "FIABILITÉ DE L'INFORMATION"):
            self.assertIn(bloc, texte)
        self.assertEqual(self.rapport.familles.get("MARCHÉS PUBLICS", []), [])

    def test_la_deduplication_fonctionne_sans_reference_officielle(self):
        besoin = dict(intitule="Nous recherchons un transporteur — site de Gand",
                      texte="livraisons quotidiennes pour le compte de tiers",
                      acheteur="Société Gand", cpv=[], type_avis=None,
                      pays_livraison=["BE"], montant=120000, secteur_acheteur="privé")
        cx = ouvrir(":memory:")
        b = traiter(cx, moteur(), [
            Opportunite(source="entreprise", ref_source="E1", **besoin),
            Opportunite(source="brave", ref_source="B1", **besoin)],
            maintenant_dt=MAINTENANT)
        self.assertEqual(b.doublons, 1)
        self.assertEqual(cx.execute("SELECT count(*) c FROM opportunites"
                                    ).fetchone()["c"], 1)

    def test_le_suivi_fonctionne_sans_procedure(self):
        """Un besoin privé qui disparaît puis revient garde son fil de vie."""
        cx = ouvrir(":memory:")
        m = moteur()
        o = lambda: Opportunite(  # noqa: E731
            source="entreprise", ref_source="S1", cpv=[], type_avis=None,
            intitule="Nous recherchons un transporteur", texte="livraisons",
            acheteur="Société", pays_livraison=["BE"], secteur_acheteur="privé")
        traiter(cx, m, [o()], maintenant_dt=MAINTENANT)
        traiter(cx, m, [o()], maintenant_dt=MAINTENANT)
        hist = cx.execute("SELECT count(*) c FROM etats_historique").fetchone()["c"]
        self.assertEqual(hist, 1, "une observation identique ne crée pas d'événement")

    def test_aucun_champ_de_marche_public_n_est_invente(self):
        for l in self.cx.execute("SELECT * FROM opportunites"):
            self.assertIsNone(l["echeance"] if l["nature"] == "SIGNAL" else None)
            self.assertNotIn("CPV", l["fiche"] or "",
                             "aucun CPV ne doit apparaître sur un besoin privé")


class LesMarchesPublicsNeSontQuUnCapteur(unittest.TestCase):
    """Ajouter ou retirer les marchés publics ne change RIEN à l'économie des
    besoins déjà détectés."""

    def _mesurer(self, avec_public: bool):
        from outils.familles import PRIVEES, PUBLIQUES, charger, moteur as m_familles
        cx = ouvrir(":memory:")
        m = m_familles()
        familles = sorted(PRIVEES) + (sorted(PUBLIQUES) if avec_public else [])
        for f in familles:
            traiter(cx, m, charger(f), maintenant_dt=MAINTENANT)
        return {l["intitule"]: (l["score"], l["type"], l["action"], l["nature"])
                for l in cx.execute(
                    "SELECT intitule, score, type, action, nature FROM opportunites")}

    def test_ajouter_les_marches_publics_ne_change_pas_les_besoins_prives(self):
        sans = self._mesurer(False)
        avec = self._mesurer(True)
        for titre, valeurs in sans.items():
            self.assertIn(titre, avec, f"« {titre} » a disparu")
            self.assertEqual(valeurs, avec[titre],
                             f"« {titre} » change quand on ajoute du public")

    def test_les_marches_publics_ne_prennent_pas_toute_la_place(self):
        avec = self._mesurer(True)
        from radar.rapport import famille_de
        self.assertGreater(len(avec), len(self._mesurer(False)),
                           "ajouter un capteur doit ajouter des observations")

    def test_retirer_les_adaptateurs_publics_laisse_un_radar_entier(self):
        """Les fichiers ted.yaml, bda.yaml, portail.yaml peuvent être supprimés
        du disque : le cœur ne les importe jamais."""
        import ast
        for module in ("chaine", "score", "classification", "capacite", "nature",
                       "fiabilite", "rapport"):
            src = (RACINE / "radar" / f"{module}.py").read_text(encoding="utf-8")
            for nom in ("ted", "bda", "portail", "tenderned"):
                self.assertNotIn(f'"{nom}"', src,
                                 f"{module}.py nomme l'adaptateur {nom}")


class ComplétudeAdapteeAuBesoin(unittest.TestCase):
    """La complétude d'un signal ne se mesure pas avec les champs d'un avis."""

    def _rapport(self, familles):
        from outils.familles import charger, moteur as m_familles
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        m = m_familles()
        for f in familles:
            traiter(cx, m, charger(f), maintenant_dt=MAINTENANT)
        return construire(cx, Mode.DEMO)

    def test_un_signal_n_est_pas_mesure_sur_lots_et_echeance(self):
        r = self._rapport(["signal_economique", "emploi_signal"])
        grille = r.completude_par_famille.get("SIGNAUX ÉCONOMIQUES", {})
        self.assertTrue(grille)
        self.assertNotIn("lots", grille)
        self.assertNotIn("échéance", grille)
        self.assertIn("nature du signal", grille)

    def test_un_marche_public_garde_sa_grille_complete(self):
        r = self._rapport(["appel_offres", "lot"])
        grille = r.completude_par_famille.get("MARCHÉS PUBLICS", {})
        for champ in ("acheteur", "échéance", "montant", "lots", "exigences"):
            self.assertIn(champ, grille)

    def test_un_besoin_prive_est_complet_sur_sa_propre_grille(self):
        r = self._rapport(["besoin_prive"])
        grille = r.completude_par_famille.get("BESOINS PRIVÉS", {})
        total = r.familles_effectif["BESOINS PRIVÉS"]
        manquants = [k for k, v in grille.items() if v is not None and v < total]
        self.assertEqual(manquants, [],
                         f"un besoin privé complet paraît incomplet : {manquants}")


# ══════════════ LE PRODUIT N'EST PAS UN RADAR D'APPELS D'OFFRES
#
# Dix formulations privées RÉELLES et imparfaites — pas la version propre
# « nous recherchons un transporteur pour nos livraisons ».
FORMULATIONS_PRIVEES = [
    ("Nous ouvrons un nouveau dépôt à Gand", "SIGNAL"),
    ("Nous cherchons à externaliser une partie de nos livraisons", "FAIT"),
    ("Besoin de partenaires régionaux pour accompagner notre croissance", "FAIT"),
    ("15 chauffeurs recherchés pour notre nouveau site", "SIGNAL"),
    ("Nous souhaitons référencer plusieurs transporteurs", "FAIT"),
    ("Notre activité logistique va doubler l'année prochaine", "SIGNAL"),
    ("Nous cherchons un partenaire pour les tournées Benelux", "FAIT"),
    ("Prestataire actuel : contrat arrivant à échéance prochainement", "SIGNAL"),
    ("Recherche fournisseur capable d'assurer la distribution quotidienne", "FAIT"),
    ("Nous étudions différentes solutions pour nos livraisons", "HYPOTHÈSE"),
]


class LeProduitNEstPasUnRadarDAppelsDOffres(unittest.TestCase):
    """Un corpus SANS le moindre marqueur de marché public.

    Aucun CPV, aucun publication-number, aucune procédure, aucune référence
    officielle, aucune date limite. Si cette classe échoue, le produit ne sait
    fonctionner qu'avec la structure d'un avis, et ce n'est pas un radar
    commercial.

    TESTÉ SUR FIXTURE — aucune de ces phrases n'a été observée sur une page
    réelle.
    """

    def _corpus(self):
        return [Opportunite(
            source="brave", ref_source=f"PRV-{i}", cpv=[], type_avis=None,
            statut_source=None, echeance_brute=None, intitule=t,
            texte=f"{t} — transport et distribution en Belgique",
            acheteur=f"Société {i}", secteur_acheteur="privé",
            pays_livraison=["BE"])
            for i, (t, _) in enumerate(FORMULATIONS_PRIVEES)]

    def test_aucune_entree_ne_porte_de_structure_d_avis_public(self):
        for o in self._corpus():
            self.assertEqual(o.cpv, [])
            self.assertIsNone(o.type_avis)
            self.assertIsNone(o.statut_source)
            self.assertIsNone(o.echeance_brute)
            self.assertFalse(o.lots)

    def test_la_chaine_complete_fonctionne_sur_ce_corpus(self):
        cx = ouvrir(":memory:")
        b = traiter(cx, moteur(), self._corpus(), maintenant_dt=MAINTENANT)
        self.assertEqual(b.livre.ecart(), 0)
        retenues = cx.execute("SELECT count(*) c FROM opportunites"
                              " WHERE type <> 'REJET'").fetchone()["c"]
        self.assertEqual(retenues, len(FORMULATIONS_PRIVEES))
        for l in cx.execute("SELECT * FROM opportunites"):
            for champ in ("type", "moteur", "action", "nature", "fiabilite",
                          "zone", "journal", "fiche"):
                self.assertTrue(l[champ], f"{l['intitule'][:30]} : {champ} vide")
            self.assertGreater(l["score"], 0)

    def test_chaque_formulation_recoit_la_bonne_nature(self):
        """FAIT, SIGNAL et HYPOTHÈSE ne se confondent pas — c'est ce qui évite
        de transformer un événement en contrat imaginaire."""
        from radar.nature import qualifier
        for texte, attendue in FORMULATIONS_PRIVEES:
            with self.subTest(texte=texte[:40]):
                o = Opportunite(source="brave", ref_source="x", intitule=texte,
                                texte=texte)
                self.assertEqual(qualifier(o).value, attendue)

    def test_aucune_de_ces_opportunites_n_invente_de_procedure(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), self._corpus(), maintenant_dt=MAINTENANT)
        etats = {l["etat_procedure"] for l in cx.execute(
            "SELECT etat_procedure FROM opportunites")}
        self.assertEqual(etats, {"HORS PROCÉDURE"},
                         "un besoin privé n'a pas d'état de procédure")

    def test_aucun_montant_n_est_fabrique(self):
        """Aucune de ces pages ne publie de montant. Le radar ne doit pas en
        inventer un — ni le déduire d'une moyenne."""
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), self._corpus(), maintenant_dt=MAINTENANT)
        for l in cx.execute("SELECT intitule, montant, marge FROM opportunites"):
            self.assertIsNone(l["montant"], f"{l['intitule'][:30]} : montant inventé")
            self.assertEqual(l["marge"], "NON MESURÉE")

    def test_un_signal_ne_devient_pas_un_contrat(self):
        """« Nous recrutons 15 chauffeurs » ne veut pas dire « ils cherchent un
        sous-traitant ». Les deux niveaux restent séparés."""
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), self._corpus(), maintenant_dt=MAINTENANT)
        for l in cx.execute("SELECT intitule, nature, action, type FROM opportunites"
                            " WHERE nature = 'SIGNAL'"):
            self.assertNotIn("POSTULER", l["action"])
            self.assertEqual(l["type"], "PROSPECT",
                             f"{l['intitule'][:30]} : un signal n'est pas un contrat")

    def test_le_rapport_produit_un_pipeline_commercial_complet(self):
        from radar.rapport import construire
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), self._corpus(), maintenant_dt=MAINTENANT)
        r = construire(cx, Mode.DEMO, cible={"montant_total_confortable_max": 1500000})
        texte = r.en_texte(avec_fiches=False)
        for bloc in ("CAPTER", "DÉVELOPPER", "SIGNAUX", "PAR FAMILLE DE BESOIN",
                     "TOP ACTIONS"):
            self.assertIn(bloc, texte)
        self.assertEqual(r.familles.get("MARCHÉS PUBLICS", []), [])
        self.assertTrue(r.actions, "le radar doit dire quoi faire demain matin")

    def test_les_objets_commerciaux_ne_sont_pas_confondus(self):
        """Un besoin explicite, un signal et une entreprise à prospecter sont
        trois objets différents, avec trois actions différentes."""
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), self._corpus(), maintenant_dt=MAINTENANT)
        par_nature = {}
        for l in cx.execute("SELECT nature, action FROM opportunites"):
            par_nature.setdefault(l["nature"], set()).add(l["action"])
        self.assertIn("FAIT", par_nature)
        self.assertIn("SIGNAL", par_nature)
        self.assertTrue(any("CONTACTER" in a for a in par_nature["FAIT"]))


class LeCPVNEstPasUneAutorite(unittest.TestCase):
    """Le CPV est une preuve, jamais un arbitre.

    Il tranchait tout : « Prestations de transport et distribution quotidienne »
    ressortait FOURNISSEUR parce qu'un CPV indiquait des fournitures de bureau.
    Une nomenclature propre aux marchés publics écrasait la description du
    besoin — et un besoin privé, qui n'a jamais de CPV, ne pouvait par
    construction jamais en bénéficier.
    """

    def _role(self, texte, cpv):
        import yaml as _y
        from radar.role import DetecteurDeRole
        d = DetecteurDeRole(_y.safe_load(
            (RACINE / "config" / "roles.yaml").read_text(encoding="utf-8")))
        return d.analyser(texte, cpv)

    PRESTATION = "Prestations de transport et distribution quotidienne pour compte de tiers"

    def test_un_cpv_de_fourniture_n_ecrase_pas_un_texte_de_prestation(self):
        a = self._role(self.PRESTATION, ["30190000"])
        self.assertIs(a.role, Role.A_VERIFIER)
        self.assertTrue(any("contradiction" in c for c in a.contre_preuves))

    def test_un_cpv_de_transport_n_ecrase_pas_un_texte_de_fourniture(self):
        a = self._role("Fourniture et livraison de mobilier de bureau", ["60000000"])
        self.assertIs(a.role, Role.A_VERIFIER)

    def test_un_cpv_de_travaux_n_ecrase_pas_un_texte_de_transport(self):
        a = self._role("Transport de marchandises, tournées quotidiennes", ["45000000"])
        self.assertIs(a.role, Role.A_VERIFIER)

    def test_sans_cpv_un_texte_clair_conclut_seul(self):
        self.assertIs(self._role(self.PRESTATION, []).role, Role.PRESTATAIRE)

    def test_le_prive_atteint_le_meme_niveau_de_reconnaissance_que_le_public(self):
        """Un besoin privé bien décrit doit valoir un besoin public bien décrit."""
        public = self._role("Transport de marchandises, tournées quotidiennes",
                            ["60000000"])
        prive = self._role("Nous cherchons un transporteur pour nos tournées "
                           "quotidiennes de distribution", [])
        self.assertIs(public.role, prive.role)

    def test_les_deux_preuves_concordantes_donnent_une_conclusion_nette(self):
        a = self._role("Transport de marchandises, tournées quotidiennes",
                       ["60000000"])
        self.assertIs(a.role, Role.PRESTATAIRE)
        self.assertEqual(a.cpv_decisif, "60000000")

    def test_un_texte_mixte_laisse_le_cpv_departager_sans_ecraser(self):
        """« Fourniture ET livraison » est réellement ambigu : là, le CPV
        éclaire au lieu d'écraser. C'est le seul cas où il départage."""
        a = self._role("Fourniture et livraison de poissons frais", ["15200000"])
        self.assertIs(a.role, Role.FOURNISSEUR)

    def test_une_contradiction_ne_produit_jamais_un_rejet(self):
        """A_VERIFIER n'est pas REJET : l'opportunité reste dans le radar."""
        o = opp(ref_source="CONTRA", cpv=["30190000"],
                intitule="Prestations de transport",
                texte=self.PRESTATION, acheteur="Client")
        r = moteur().analyser(o, MAINTENANT)
        self.assertIsNot(r.classement.type, Type.REJET)


# ══════════════ LE RADAR CHERCHE DU CHIFFRE D'AFFAIRES, PAS DES AVIS
def _besoin(ref, **kw):
    base = dict(source="entreprise", ref_source=ref, cpv=[], type_avis=None,
                statut_source=None, texte="tournées quotidiennes de distribution "
                "urbaine pour le compte de tiers", pays_livraison=["BE"],
                distance_depot_km=20, cadence="quotidienne", duree_mois=36,
                secteur_acheteur="privé", exigences={"licence_transport": True})
    base.update(kw)
    return Opportunite(**base)


class LeRadarNestPasUnMoteurDAppelsOffres(unittest.TestCase):
    """Un lot TOTALEMENT privé : contrat, sous-traitance, partenariat,
    recrutement, entreprise à contacter, renouvellement, signal d'expansion,
    besoin exprimé, nouveau métier. Aucun CPV, aucun publication-number,
    aucune procédure publique, aucun portail.

    TESTÉ SUR FIXTURE — données réelles observées : 0.
    """

    def _lot(self):
        return [
            _besoin("CONTRAT", intitule="Nous recherchons un transporteur régional",
                    acheteur="Industrie SA", montant=12000 * 36),
            _besoin("SST", intitule="Appel à sous-traitants pour nos tournées",
                    acheteur="Grand Opérateur", montant=15000 * 36),
            _besoin("PART", intitule="Devenir partenaire transporteur du réseau",
                    acheteur="Réseau Froid", montant=9000 * 36),
            _besoin("RECRUT", source="brave",
                    intitule="20 chauffeurs recherchés pour notre nouveau site",
                    acheteur="Messagerie SA", montant=None),
            _besoin("PROSPECT", source="brave",
                    intitule="Distributeur régional, trois sites en Belgique",
                    texte="livraisons quotidiennes, flotte interne saturée",
                    acheteur="Distributeur SA", montant=None),
            _besoin("RENOUV", source="brave",
                    intitule="Prestataire actuel : contrat arrivant à échéance",
                    acheteur="Groupe Alimentaire", montant=11000 * 36),
            _besoin("EXPANSION", source="brave",
                    intitule="Nous ouvrons un nouveau dépôt à Gand",
                    acheteur="Groupe Agro", montant=None),
            _besoin("METIER", intitule="Recherche de partenaires installation bornes",
                    texte="véhicules utilitaires et personnel de terrain, formation "
                          "complète de trois semaines assurée au démarrage",
                    acheteur="Opérateur Énergie", montant=8000 * 36,
                    echeance_brute="2028-03-01T12:00:00+01:00",
                    date_demarrage="2028-09-01"),
        ]

    def setUp(self):
        from radar.rapport import construire
        self.cx = ouvrir(":memory:")
        self.bilan = traiter(self.cx, moteur(), self._lot(), maintenant_dt=MAINTENANT)
        self.rapport = construire(self.cx, Mode.DEMO,
                                  cible={"montant_total_confortable_max": 1500000})

    def test_le_lot_ne_contient_aucun_marqueur_public(self):
        for o in self._lot():
            self.assertEqual(o.cpv, [])
            self.assertIsNone(o.type_avis)
            self.assertIsNone(o.statut_source)
            self.assertFalse((o.ref_source or "").startswith("TED"))

    def test_le_radar_produit_un_resultat_commercial_complet(self):
        self.assertEqual(self.bilan.livre.ecart(), 0)
        retenues = self.cx.execute("SELECT count(*) c FROM opportunites"
                                   " WHERE type <> 'REJET'").fetchone()["c"]
        self.assertEqual(retenues, 8)
        self.assertGreater(self.bilan.capter + self.bilan.developper, 0)

    def test_le_pipeline_commercial_est_alimente_sans_aucun_avis(self):
        """Les blocs qui comptent doivent être remplis par du privé seul."""
        pipeline = self.rapport.pipeline
        self.assertTrue(pipeline.get("contacter"), "personne à contacter")
        self.assertTrue(pipeline.get("surveiller"), "rien à surveiller")
        self.assertTrue(pipeline.get("metier"), "aucun métier à construire")

    def test_chaque_objet_commercial_a_son_action_propre(self):
        actions = {l["ref_source"]: l["action"] for l in self.cx.execute(
            "SELECT a.ref_source, o.action FROM opportunites o"
            " JOIN avis a ON a.id = o.avis_id")}
        self.assertIn("CONTACTER", actions["CONTRAT"])
        self.assertIn("CONTACTER", actions["SST"])
        self.assertNotIn("POSTULER", actions["RECRUT"])
        self.assertNotIn("POSTULER", actions["EXPANSION"])

    def test_les_signaux_ne_deviennent_pas_des_contrats(self):
        for ref in ("RECRUT", "EXPANSION"):
            l = self.cx.execute(
                "SELECT o.nature, o.type, o.etat_procedure FROM opportunites o"
                " JOIN avis a ON a.id = o.avis_id WHERE a.ref_source = ?",
                (ref,)).fetchone()
            self.assertEqual(l["nature"], "SIGNAL")
            self.assertEqual(l["type"], "PROSPECT")
            self.assertEqual(l["etat_procedure"], "HORS PROCÉDURE")

    def test_aucune_procedure_n_est_inventee(self):
        """Un état n'est fabriqué que lorsque RIEN ne le fonde.

        La fixture « nouveau métier » publie, elle, une date limite : son
        POSTULABLE est donc mérité, pas inventé. Ce qu'on vérifie, c'est
        qu'aucune opportunité sans le moindre élément de procédure n'en reçoit
        un — et qu'aucune ne finit en INCONNU, qui ferait vérifier un état
        inexistant.
        """
        lignes = {l["ref_source"]: l["etat_procedure"] for l in self.cx.execute(
            "SELECT a.ref_source, o.etat_procedure FROM opportunites o"
            " JOIN avis a ON a.id = o.avis_id")}
        self.assertNotIn("INCONNU", set(lignes.values()))
        for ref in ("CONTRAT", "SST", "PART", "RECRUT", "PROSPECT", "RENOUV",
                    "EXPANSION"):
            self.assertEqual(lignes[ref], "HORS PROCÉDURE",
                             f"{ref} n'a aucune procédure — aucun état ne doit "
                             f"lui être inventé")
        self.assertEqual(lignes["METIER"], "POSTULABLE",
                         "cette page publie une date limite : l'état est mérité")

    def test_aucun_montant_n_est_fabrique_quand_il_manque(self):
        for ref in ("RECRUT", "PROSPECT", "EXPANSION"):
            l = self.cx.execute(
                "SELECT o.montant, o.marge FROM opportunites o JOIN avis a"
                " ON a.id = o.avis_id WHERE a.ref_source = ?", (ref,)).fetchone()
            self.assertIsNone(l["montant"])
            self.assertEqual(l["marge"], "NON MESURÉE")

    def test_le_meilleur_score_va_a_la_meilleure_economie(self):
        scores = {l["ref_source"]: l["score"] for l in self.cx.execute(
            "SELECT a.ref_source, o.score FROM opportunites o"
            " JOIN avis a ON a.id = o.avis_id")}
        self.assertGreater(scores["SST"], scores["PART"],
                           "15 000 €/mois doit battre 9 000 €/mois")


class UnBesoinPriveFortBatUnMarchePublicFaible(unittest.TestCase):
    """§4 — le classement suit l'économie, jamais la provenance."""

    def _lot(self):
        return [
            Opportunite(source="bda", ref_source="PUB", cpv=["60000000"],
                        type_avis="avis de marché", secteur_acheteur="public",
                        intitule="Marché public de distribution", acheteur="Commune",
                        texte="tournées quotidiennes de distribution urbaine",
                        montant=8000 * 36, duree_mois=36, cadence="quotidienne",
                        pays_livraison=["BE"], distance_depot_km=20,
                        echeance_brute=OUVERT,
                        exigences={"licence_transport": True}),
            _besoin("PRV", intitule="Nous recherchons un transporteur régional",
                    acheteur="Industrie SA", montant=12000 * 36),
            _besoin("SST", intitule="Appel à sous-traitants pour nos tournées",
                    acheteur="Grand Opérateur", montant=15000 * 36),
            _besoin("SIG", source="brave", montant=None,
                    intitule="Nous ouvrons un nouveau dépôt à Gand",
                    acheteur="Groupe Agro"),
        ]

    def setUp(self):
        self.cx = ouvrir(":memory:")
        traiter(self.cx, moteur(), self._lot(), maintenant_dt=MAINTENANT)
        self.scores = {l["ref_source"]: l["score"] for l in self.cx.execute(
            "SELECT a.ref_source, o.score FROM opportunites o"
            " JOIN avis a ON a.id = o.avis_id")}

    def test_le_prive_a_12k_bat_le_public_a_8k(self):
        self.assertGreater(self.scores["PRV"], self.scores["PUB"])

    def test_la_sous_traitance_a_15k_bat_le_public_a_8k(self):
        self.assertGreater(self.scores["SST"], self.scores["PUB"])

    def test_le_signal_sans_economie_connue_passe_derriere(self):
        for ref in ("PUB", "PRV", "SST"):
            self.assertGreater(self.scores[ref], self.scores["SIG"],
                               "une économie inconnue ne doit pas dominer")

    def test_memes_donnees_economiques_sources_differentes_meme_score(self):
        commun = dict(intitule="Distribution urbaine de marchandises",
                      texte="tournées quotidiennes de distribution urbaine",
                      acheteur="Client", montant=12000 * 36, duree_mois=36,
                      cadence="quotidienne", pays_livraison=["BE"],
                      distance_depot_km=20, echeance_brute=OUVERT,
                      exigences={"licence_transport": True})
        m = moteur()
        scores = {}
        for src, extra in (("ted", dict(cpv=["60000000"], type_avis="contract-notice")),
                           ("bda", dict(cpv=["60000000"])),
                           ("brave", {}), ("entreprise", {}),
                           ("bourse_fret", {}), ("signaux", {})):
            o = Opportunite(source=src, ref_source=f"S-{src}",
                            **{**commun, **{"cpv": [], "type_avis": None}, **extra})
            scores[src] = m.analyser(o, MAINTENANT).score.total
        self.assertEqual(len(set(scores.values())), 1, scores)

    def test_source_identique_economies_differentes_scores_differents(self):
        m = moteur()
        petit = m.analyser(_besoin("A", intitule="Distribution urbaine",
                                   acheteur="C", montant=6000 * 36), MAINTENANT)
        gros = m.analyser(_besoin("B", intitule="Distribution urbaine",
                                  acheteur="C", montant=20000 * 36), MAINTENANT)
        self.assertNotEqual(petit.score.total, gros.score.total)
        self.assertGreater(gros.score.total, petit.score.total)


class RetirerTEDNeChangePasLeProduit(unittest.TestCase):
    def _mesurer(self, exclues=()):
        from outils.familles import FAMILLES, charger, moteur as m_familles
        cx = ouvrir(":memory:")
        m = m_familles()
        for nom, _, source, _ in FAMILLES:
            if source in exclues:
                continue
            traiter(cx, m, charger(nom), maintenant_dt=MAINTENANT)
        return {l["intitule"]: (l["score"], l["type"], l["action"], l["nature"])
                for l in cx.execute("SELECT intitule, score, type, action, nature"
                                    " FROM opportunites")}

    def test_retirer_ted_ne_change_rien_aux_autres(self):
        avec, sans = self._mesurer(), self._mesurer({"ted"})
        for titre, valeurs in sans.items():
            self.assertEqual(valeurs, avec[titre],
                             f"« {titre} » change quand on retire TED")

    def test_sans_ted_le_radar_produit_encore_un_pipeline(self):
        self.assertGreater(len(self._mesurer({"ted"})), 0)


class AucuneSourceNestIndispensable(unittest.TestCase):
    def test_chaque_adaptateur_peut_etre_retire(self):
        from outils.familles import FAMILLES, charger, moteur as m_familles
        sources = sorted({s for _, _, s, _ in FAMILLES})
        for exclue in sources:
            with self.subTest(sans=exclue):
                cx = ouvrir(":memory:")
                m = m_familles()
                for nom, _, source, _ in FAMILLES:
                    if source == exclue:
                        continue
                    traiter(cx, m, charger(nom), maintenant_dt=MAINTENANT)
                n = cx.execute("SELECT count(*) c FROM opportunites"
                               " WHERE type <> 'REJET'").fetchone()["c"]
                self.assertGreater(n, 0, f"le radar meurt sans « {exclue} »")

    def test_le_coeur_ne_nomme_aucun_adaptateur(self):
        for module in ("score", "capacite", "classification", "nature", "fiabilite",
                       "deduplication", "transitions", "questions"):
            src = (RACINE / "radar" / f"{module}.py").read_text(encoding="utf-8")
            for nom in ('"ted"', '"bda"', '"google"', '"brave"', '"portail"'):
                self.assertNotIn(nom, src, f"{module}.py nomme {nom}")


# ═══════════════════════════════════════════════════════════════════════════
#  §16 — CE QUE LA PREMIÈRE PAGE RÉELLE A RÉVÉLÉ
#
#  Ces tests ne sortent d'aucune imagination. Chacun verrouille un comportement
#  qu'une VRAIE page — https://pypi.org/project/requests/, 251 417 octets,
#  sha256 ef41f74e…, conservée dans validation/pages_reelles/ — a pris en
#  défaut le 4 septembre 2026. Le fichier est joint : chaque assertion est
#  recontrôlable sur les octets d'origine.
#
#  La page choisie n'a AUCUN rapport avec le transport. C'est le but : c'est
#  le seul cas que les fixtures ne contenaient pas — une page qu'on lit et qui
#  ne donne rien. Les douze familles de fixtures décrivaient toutes une
#  opportunité ; aucune ne décrivait une non-opportunité.
# ═══════════════════════════════════════════════════════════════════════════

PAGE_REELLE = RACINE / "validation" / "pages_reelles"


def _page_reelle():
    fichiers = sorted(PAGE_REELLE.glob("*.html"))
    return fichiers[0] if fichiers else None


class CeQueLaPremierePageReelleARevele(unittest.TestCase):
    """Défaut observé : le texte d'un <script> entrait dans l'analyse sémantique.

    Sur la page mesurée, le balisage pèse 95 % du fichier. Le lecteur ramassait
    le contenu des <script> comme du texte de page : le moteur sémantique
    analysait du JavaScript. Une fixture, elle, est du texte pur — le défaut
    était structurellement invisible.
    """

    def test_le_javascript_nest_pas_du_texte_de_page(self):
        from radar.extraction import analyser
        r = analyser('<body><h1>Partenaires</h1>'
                     '<script>var t="marché attribué le 12/03 au titulaire";</script>'
                     '<style>.a{content:"appel d\'offres clôturé"}</style>'
                     '<p>Nous cherchons un transporteur.</p></body>')
        texte = r.texte()
        self.assertIn("Nous cherchons un transporteur", texte)
        self.assertNotIn("marché attribué", texte)
        self.assertNotIn("clôturé", texte)

    def test_une_page_sans_aucun_fait_commercial_nest_pas_une_opportunite(self):
        """Défaut observé : 🔵 PROSPECT, score 24/100, action « SURVEILLER ».

        La page ne parlait que d'une bibliothèque HTTP. Les 24 points étaient
        entièrement composés de neutralités accordées à des absences — chacune
        juste isolément, toutes ensemble une note fabriquée à partir de rien.
        """
        # Fidèle à la page mesurée : ni échéance, ni pays, ni montant, ni
        # durée, ni cadence, ni exigence. Le banc d'essai en fournit deux par
        # défaut (`echeance_brute`, `pays_livraison`) — une vraie page
        # d'entreprise n'en offre aucun.
        r = moteur().analyser(opp(
            intitule="requests 2.34.2", texte="Python HTTP for Humans.",
            acheteur="PyPI", secteur_acheteur="prive",
            echeance_brute=None, pays_livraison=[]))
        self.assertIs(r.classement.type, Type.OBSERVATION)
        self.assertFalse(r.classement.type.notifiable,
                         "une observation ne doit pas réveiller le commercial")
        self.assertFalse(r.score.mesurable)
        self.assertIn("NON MESURABLE", r.fiche.score_affiche)

    def test_ce_nest_pas_un_rejet(self):
        """⚪ n'est pas 🔴. Rien ne dit que cette entreprise n'aura pas de besoin."""
        r = moteur().analyser(opp(intitule="Notre société change son logo",
                                  texte="Nouvelle identité visuelle.",
                                  acheteur="Bral SA", secteur_acheteur="prive",
                                  echeance_brute=None, pays_livraison=[]))
        self.assertIs(r.classement.type, Type.OBSERVATION)
        self.assertNotEqual(r.classement.type, Type.REJET)
        self.assertTrue(any("pas un rejet" in x for x in r.classement.raisons))

    def test_un_besoin_en_vocabulaire_inconnu_reste_une_opportunite(self):
        """⚪ ne doit JAMAIS devenir un rejet par absence de mot-clé.

        La règle regarde l'absence de TOUT fait — pas l'absence d'un mot connu.
        Un besoin écrit dans un métier inconnu, mais daté et chiffré, est ancré.
        """
        r = moteur().analyser(opp(
            intitule="Convoyage de mâts d'éoliennes",
            texte="Nous recherchons un prestataire pour du convoyage exceptionnel.",
            montant=180000, duree_mois=24, cadence="hebdomadaire",
            acheteur="Windco", secteur_acheteur="prive",
            pays_livraison=["BE"]))
        self.assertIsNot(r.classement.type, Type.OBSERVATION,
                         "un métier inconnu mais chiffré et daté reste une affaire")

    def test_une_absence_nest_jamais_un_argument_commercial(self):
        """Défaut observé : « POURQUOI C'EST INTÉRESSANT · aucun lieu publié ».

        Une zone A_VERIFIER produisait sa raison dans la rubrique des arguments.
        Le radar vendait une absence.
        """
        r = moteur().analyser(opp(intitule="Transport de palettes",
                                  texte="Distribution de palettes en Belgique."))
        for p in r.fiche.pourquoi:
            self.assertNotIn("aucun lieu publié", p)
            self.assertNotIn("à vérifier", p.lower())

    def test_ajouter_une_categorie_ne_casse_pas_la_chaine(self):
        """Défaut observé : un dict indexé par Type a levé KeyError en ajoutant ⚪.

        Toute la chaîne d'analyse tombait. Aucun test ne couvrait « une valeur
        d'énumération que ce dictionnaire ne connaît pas ».
        """
        from radar import questions
        for t in Type:
            with self.subTest(type=t):
                self.assertIn(t, {Type.DIRECT, Type.RENFORCEMENT, Type.A_CONSTRUIRE,
                                  Type.PROSPECT, Type.OBSERVATION, Type.REJET})
        src = (RACINE / "radar" / "questions.py").read_text(encoding="utf-8")
        self.assertIn("}.get(classement.type", src,
                      "l'accès par Type doit tolérer une catégorie ajoutée")


class LeNiveauObserveEstVerifieEtNonDeclare(unittest.TestCase):
    """Le journal de provenance doit pouvoir CONTREDIRE celui qui l'appelle."""

    def test_une_valeur_absente_de_la_page_ne_peut_pas_etre_observee(self):
        from radar.provenance import Journal, Niveau
        j = Journal("Nous cherchons un transporteur pour Gand.")
        c = j.observer("montant", "120 000 EUR")
        self.assertIs(c.niveau, Niveau.INTERPRETE)
        self.assertIn("refusé", c.retrograde)

    def test_une_valeur_presente_est_observee_avec_sa_position(self):
        from radar.provenance import Journal, Niveau
        j = Journal("Nous cherchons un transporteur pour Gand.")
        c = j.observer("intitulé", "transporteur")
        self.assertIs(c.niveau, Niveau.OBSERVE)
        self.assertIsNotNone(c.position)
        self.assertIn("transporteur", c.extrait)

    def test_le_balisage_est_distingue_du_texte_visible(self):
        """Défaut observé : « mailto:me@… ne figure pas dans la page » — c'était faux.

        L'adresse figurait bien dans le fichier, dans un attribut href. Le
        journal ne comparait qu'au texte visible et adressait donc un reproche
        inexact. Un lecteur humain ne voit pourtant pas cette valeur : les deux
        niveaux existent, et ils ne se valent pas.
        """
        from radar.provenance import Journal, Niveau
        j = Journal("Kenneth Reitz", '<a href="mailto:me@kennethreitz.org">Kenneth Reitz</a>')
        c = j.observer("contact", "me@kennethreitz.org")
        self.assertIs(c.niveau, Niveau.OBSERVE_BALISAGE)
        self.assertIn("invisible", c.ligne())

    def test_inconnu_porte_une_question_et_jamais_un_zero(self):
        from radar.provenance import Journal, Niveau
        j = Journal("page sans montant")
        c = j.inconnu("montant", question="Quel volume annuel ?")
        self.assertIs(c.niveau, Niveau.INCONNU)
        self.assertEqual(c.affichage, "INCONNU")
        self.assertNotEqual(c.affichage, "0")
        self.assertTrue(c.question)


class LeLecteurDePageGeneriqueNInventeRien(unittest.TestCase):
    def _profil(self):
        import yaml
        return yaml.safe_load((RACINE / "sources" / "page_web.yaml").read_text(
            encoding="utf-8"))

    def test_un_champ_introuvable_reste_absent(self):
        from radar.page import lire
        lec = lire("<html><body><p>rien</p></body></html>", self._profil())
        self.assertNotIn("contact_email", lec.champs)
        self.assertIn("contact_email", lec.non_trouves)

    def test_le_prefixe_mailto_est_retire(self):
        """Défaut observé : le contact sortait « mailto:me@kennethreitz.org »."""
        from radar.page import lire
        lec = lire('<html><body><a href="mailto:jan@transco.be?subject=Devis">'
                   'Nous écrire</a></body></html>', self._profil())
        self.assertEqual(lec.champs.get("contact_email"), "jan@transco.be")

    def test_deux_pistes_qui_se_contredisent_sont_signalees(self):
        """Observé : <h1> disait « requests 2.34.2 », <title> « requests »."""
        from radar.page import lire
        lec = lire("<html><head><title>Transco — accueil</title></head>"
                   "<body><h1>Devenir partenaire</h1></body></html>", self._profil())
        self.assertEqual(lec.champs["intitule"], "Devenir partenaire")
        self.assertIn("intitule", lec.variantes)

    def test_les_absences_attendues_deviennent_des_questions(self):
        from radar.page import lire
        lec = lire("<html><body><h1>Transco</h1></body></html>", self._profil())
        self.assertIn("montant", lec.questions)
        self.assertTrue(lec.questions["montant"].endswith("?"))


class LesDeuxCompteursNeSeMelangentJamais(unittest.TestCase):
    """« 373 tests » ne doit jamais pouvoir se lire comme une validation."""

    def test_le_compteur_reel_ne_sinvente_pas_dans_une_phrase(self):
        from radar import validation
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            vide = Path(d) / "mesures.json"
            e = validation.Etat(tests_coherence=validation.compter_tests(),
                                mesures=validation.lire_registre(vide))
            self.assertEqual(len(e.mesures), 0)
            self.assertGreater(e.tests_coherence, 0)
            rendu = e.rendu()
            # Les deux dimensions, chacune à zéro et affichée séparément.
            self.assertIn(f"{validation.DONNEE_OBSERVEE:<34} : 0", rendu)
            self.assertIn(f"{validation.OPPORTUNITE_TESTEE:<34} : 0", rendu)
            self.assertIn("ne mesurent AUCUNE capacité", rendu)

    def test_la_formule_interdite_napparait_dans_aucune_sortie(self):
        from radar import validation
        interdites = ("n'importe quelle source", "toutes les sources",
                      "toute source du web")
        for fichier in list((RACINE / "radar").glob("*.py")) + \
                list((RACINE / "outils").glob("*.py")) + [RACINE / "README.md"]:
            texte = fichier.read_text(encoding="utf-8")
            for phrase in interdites:
                self.assertNotIn(
                    f"opportunités provenant de {phrase}", texte,
                    f"{fichier.name} promet plus que ce qui a été mesuré")
        self.assertIn("différentes familles de sources prévues par l'architecture",
                      validation.FORMULE_AUTORISEE)

    def test_une_meme_page_relue_ne_compte_pas_deux_fois(self):
        from radar import validation
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "m.json"
            m = validation.Mesure(horodatage="2026-09-04T00:00:00+00:00",
                                  famille="page_web", origine="test",
                                  reference="http://x", empreinte="abc123")
            validation.inscrire(m, f)
            validation.inscrire(m, f)
            self.assertEqual(len(validation.lire_registre(f)), 1)


# ═══════════════════════════════════════════════════════════════════════════
#  §2026-09 — LE RADAR CHERCHE DU CHIFFRE D'AFFAIRES, PAS DES APPELS D'OFFRES
#
#  Ces tests viennent d'une vérification EXÉCUTÉE des points verrouillés, pas
#  d'une relecture. Trois ont trouvé un défaut réel ; deux ont trouvé une
#  erreur dans mon banc d'essai, ce qui est un défaut aussi.
# ═══════════════════════════════════════════════════════════════════════════

class LeSensDeLaFormulationPasLeMotClef(unittest.TestCase):
    """Point 4 : comprendre ce que la phrase VEUT DIRE, en quatre langues."""

    def _etat(self, texte=None, **kw):
        return moteur().analyser(
            avis_public(intitule="Distribution de colis", texte=texte or "", **kw),
            MAINTENANT).lecture.etat_affiche

    def test_les_formulations_de_cloture_sont_comprises(self):
        """« procédure achevée » ressortait POSTULABLE — le pire des faux sens,
        puisqu'il envoie préparer un dossier sur un marché fini. Mesuré, pas
        supposé : « achevée » n'était dans aucune liste de marqueurs."""
        for texte in ("procédure clôturée", "procédure achevée",
                      "les offres ne sont plus acceptées", "délai de remise dépassé",
                      "consultation terminée", "nous sommes hors délai",
                      "de procedure is voltooid", "procedure afgerond",
                      "the procedure is completed", "das Verfahren ist abgeschlossen"):
            with self.subTest(texte=texte):
                self.assertEqual(self._etat(texte), "FERMÉ")

    def test_les_formulations_douverture_ne_basculent_pas(self):
        for texte in ("Procédure ouverte", "Vous pouvez remettre votre offre",
                      "Les offres sont acceptées jusqu'au 30 novembre 2026",
                      "Angebote können eingereicht werden",
                      "Deadline for submissions: 30 November 2026"):
            with self.subTest(texte=texte):
                self.assertEqual(self._etat(texte), "POSTULABLE")

    def test_les_formulations_dattribution_sont_comprises(self):
        for texte in ("marché attribué", "contrat attribué à Transalux",
                      "Zuschlag erteilt", "Auftrag vergeben",
                      "contract awarded to Transalux"):
            with self.subTest(texte=texte):
                self.assertEqual(self._etat(texte), "ATTRIBUÉ")

    def test_une_attribution_annoncee_nest_pas_une_attribution(self):
        for texte in ("Le marché sera attribué prochainement.",
                      "La décision d'attribution est à venir.",
                      "Attribution prévue au premier trimestre.",
                      "Beslissing volgt later.", "Entscheidung steht noch aus."):
            with self.subTest(texte=texte):
                self.assertNotEqual(self._etat(texte), "ATTRIBUÉ")


class LeBancDEssaiDoitExercerLesPreuvesFortes(unittest.TestCase):
    """Le banc construisait le moteur SANS vocabulaire.

    Conséquence mesurée : `statut_source` et `type_information` — les rangs 5
    et 4, les deux preuves les plus fortes — ressortaient toujours INCONNU dans
    les 390 tests. Toute la partie haute de la hiérarchie n'était jamais
    exercée. Même défaut que le banc à 94 % en forme de marché public : le
    moteur était correct, son banc ne savait pas le mettre à l'épreuve.
    """

    def test_le_moteur_de_test_charge_bien_les_vocabulaires(self):
        self.assertTrue(VOCABULAIRES, "aucun vocabulaire chargé")
        self.assertIn("bda", VOCABULAIRES)
        self.assertTrue(VOCABULAIRES["bda"].statuts,
                        "le vocabulaire bda ne déclare aucun statut")

    def test_un_statut_declare_produit_bien_une_preuve_de_rang_5(self):
        r = moteur().analyser(avis_public(intitule="Distribution de colis",
                                          statut_source="attribué"), MAINTENANT)
        rangs = {p.rang for p in r.lecture.preuves}
        self.assertIn(5, rangs, "le statut déclaré n'a produit aucune preuve forte")
        self.assertEqual(r.lecture.etat_affiche, "ATTRIBUÉ")

    def test_deux_preuves_fortes_contradictoires_donnent_INCONNU(self):
        """Point 5 : le radar n'invente pas, il demande une vérification."""
        r = moteur().analyser(
            avis_public(intitule="Distribution de colis", statut_source="attribué",
                        evenements=[{"type": "procédure annulée", "date": None}]),
            MAINTENANT)
        self.assertEqual(r.lecture.etat_affiche, "INCONNU")
        self.assertEqual(r.classement.action, Action.VERIFIER_ETAT)
        self.assertIsNot(r.classement.type, Type.REJET)
        self.assertTrue(any("s'excluent" in a for a in r.lecture.a_verifier))

    def test_la_preuve_la_plus_precise_bat_la_rubrique(self):
        r = moteur().analyser(
            avis_public(intitule="Distribution de colis",
                        type_information="avis de marché",
                        texte="La procédure est clôturée."), MAINTENANT)
        self.assertEqual(r.lecture.etat_affiche, "FERMÉ")
        self.assertTrue(any("rubrique du portail" in c for c in r.lecture.contradictions),
                        "la contradiction doit être AFFICHÉE, pas absorbée")


class LaFiabiliteNeRecompensePasLOfficialite(unittest.TestCase):
    """« NE JAMAIS confondre source publique avec opportunité meilleure » —
    appliqué à la fiabilité.

    Le critère « état démontré / probable » ne pouvait être gagné que par une
    source publiant une rubrique normée. Une page d'entreprise n'en publie
    jamais. C'était une prime à l'officialité déguisée en mesure de fiabilité,
    invisible tant que le banc tournait sans vocabulaire.
    """

    def test_la_fiabilite_ne_lit_pas_letat_de_procedure(self):
        """Lu sur le CODE EXÉCUTABLE seul : les commentaires du module
        expliquent précisément pourquoi ce critère a été retiré, et les citer
        ferait échouer le test sur sa propre explication."""
        import io
        import tokenize
        src = (RACINE / "radar" / "fiabilite.py").read_text(encoding="utf-8")
        code = []
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type not in (tokenize.COMMENT, tokenize.STRING):
                code.append(tok.string)
        code = " ".join(code)
        for interdit in ("Confiance.ELEVEE", "Confiance.MOYENNE"):
            self.assertNotIn(interdit, code,
                             "la fiabilité recompte l'état de procédure")

    def test_meme_preuves_meme_fiabilite_quelle_que_soit_la_source(self):
        commun = dict(intitule="Transport de palettes",
                      texte="Transport de palettes en Belgique.",
                      acheteur="Client", plateforme="https://exemple.be/x",
                      pays_livraison=["BE"])
        niveaux = set()
        for source, secteur in (("entreprise", "prive"), ("bda", "public"),
                                ("recherche", "prive"), ("ted", "public"),
                                ("bourse_fret", "prive")):
            r = moteur().analyser(opp(source=source, ref_source="R-1",
                                      secteur_acheteur=secteur, **commun), MAINTENANT)
            niveaux.add(r.fiabilite.niveau)
        self.assertEqual(len(niveaux), 1,
                         "à preuves égales, la source ne doit rien changer")


class LeScoreEstAveugleALaSource(unittest.TestCase):
    """Point 7, vérifié à texte IDENTIQUE — sinon on mesure la rédaction."""

    def test_six_sources_meme_economie_meme_score(self):
        eco = dict(intitule="Livraisons régionales",
                   texte="Transport de marchandises et distribution régionale de colis.",
                   montant=180000, duree_mois=12, cadence="quotidienne",
                   pays_livraison=["BE"], km_annuels=60000, chauffeurs_requis=2,
                   vehicules_requis=2)
        notes = set()
        for source, secteur, extra in (
                ("entreprise", "prive", {}), ("recherche", "prive", {}),
                ("bourse_fret", "prive", {}),
                ("bda", "public", {"type_avis": "appel-offres", "cpv": ["60000000"]}),
                ("ted", "public", {"type_avis": "appel-offres", "cpv": ["60000000"]}),
                ("signaux", "prive", {"est_signal": True,
                                      "signal_code": "ouverture_site"})):
            r = moteur().analyser(opp(source=source, acheteur="X",
                                      secteur_acheteur=secteur, **extra, **eco),
                                  MAINTENANT)
            notes.add(r.score.total)
        self.assertEqual(len(notes), 1,
                         f"la source influe sur le score : {sorted(notes)}")

    def test_un_besoin_prive_de_15k_bat_un_marche_public_de_8k(self):
        commun = dict(texte="Transport de marchandises et distribution de colis.",
                      duree_mois=12, cadence="quotidienne", pays_livraison=["BE"])
        prive = moteur().analyser(opp(source="entreprise", acheteur="Delhaize",
                                      secteur_acheteur="prive", intitule="Livraisons",
                                      montant=180000, **commun), MAINTENANT)
        public = moteur().analyser(avis_public(intitule="Livraisons", montant=96000,
                                               **commun), MAINTENANT)
        self.assertGreater(prive.score.total, public.score.total)


class MaTailleNestJamaisUnFiltreDeRejet(unittest.TestCase):
    """Point 8 : 100 000 €/mois, 20 véhicules, j'en ai 10."""

    def _gros(self):
        return moteur().analyser(
            avis_public(intitule="Distribution nationale de colis",
                        texte="Marché de distribution de colis.", montant=1200000,
                        duree_mois=12, cadence="quotidienne", pays_livraison=["BE"],
                        exigences={"vehicules_min": 20}), MAINTENANT)

    def test_trop_gros_nest_pas_un_rejet(self):
        r = self._gros()
        self.assertIsNot(r.classement.type, Type.REJET)
        self.assertIn(r.classement.action, (Action.PROPOSER_GROUPEMENT,
                                            Action.PROPOSER_SOUS_TRAITANCE))

    def test_le_plan_de_faisabilite_est_chiffre(self):
        """« au-delà du maximum mobilisable » est vrai et inutile. Il faut
        dire combien il manque, et par quelles voies y arriver."""
        plan = self._gros().bilan.plan_de_faisabilite()
        self.assertTrue(plan, "aucun plan pour une affaire bloquée")
        self.assertTrue(any("il manque" in p for p in plan))
        self.assertTrue(any("groupement" in p or "sous-trait" in p for p in plan))
        self.assertTrue(any("lot" in p for p in plan))


class LeRapportRepondAuxDixQuestions(unittest.TestCase):
    def setUp(self):
        cx = ouvrir(":memory:")
        m = moteur()
        traiter(cx, m, [
            avis_public(ref_source="A", intitule="Tournée régionale de palettes",
                        texte="Transport de palettes en Wallonie.", montant=96000,
                        duree_mois=12, cadence="hebdomadaire", pays_livraison=["BE"]),
            avis_public(ref_source="B", intitule="Distribution nationale de colis",
                        texte="Marché de distribution de colis.", montant=1200000,
                        duree_mois=12, cadence="quotidienne", pays_livraison=["BE"],
                        exigences={"vehicules_min": 20}),
            opp(source="entreprise", ref_source="C", intitule="Changement de logo",
                texte="Nouvelle identité visuelle.", acheteur="Bral SA",
                secteur_acheteur="prive", echeance_brute=None, pays_livraison=[]),
            # Une affaire RETENUE dont la source ne publie aucun montant : le
            # cas normal du privé, et celui que la question 8 doit compter à
            # part au lieu de l'additionner comme un zéro.
            opp(source="entreprise", ref_source="D",
                intitule="Nous recherchons un transporteur pour nos livraisons",
                texte="Nous recherchons un transporteur pour nos livraisons "
                      "de palettes en Wallonie.",
                acheteur="Delhaize", secteur_acheteur="prive", pays_livraison=["BE"]),
        ], maintenant_dt=MAINTENANT)
        from radar.rapport import construire
        self.texte = "\n".join(construire(
            cx, Mode.DEMO, cible={}, proche_km=50)._decision())

    def test_les_dix_questions_sont_toutes_posees(self):
        for n, question in enumerate((
                "QUOI ATTAQUER MAINTENANT", "QUI CONTACTER", "QUOI SURVEILLER",
                "QUOI DÉVELOPPER", "QUOI IGNORER", "QUELLE CAPACITÉ ME MANQUE",
                "COMMENT LA COMBLER", "QUEL EST LE POTENTIEL ÉCONOMIQUE",
                "QUEL EST LE RISQUE", "QUELLE EST LA PROCHAINE ACTION CONCRÈTE"), 1):
            with self.subTest(question=question):
                self.assertIn(f"{n}. {question}", self.texte)

    def test_la_capacite_manquante_ne_contient_pas_de_points_a_verifier(self):
        """Défaut mesuré : la question 6 listait « TYPE D'INFORMATION INCONNU »
        comme s'il fallait acheter un camion pour le combler. Un manque se
        COMBLE ; un point à vérifier se LÈVE par un appel — il est en risque."""
        bloc = self.texte.split("6. QUELLE CAPACITÉ ME MANQUE")[1].split("7.")[0]
        for bruit in ("TYPE D'INFORMATION INCONNU", "à confirmer à la source",
                      "STATUT SOURCE INCONNU", "analyser objet"):
            self.assertNotIn(bruit, bloc)

    def test_le_potentiel_ne_compte_jamais_un_montant_absent_comme_zero(self):
        bloc = self.texte.split("8. QUEL EST LE POTENTIEL")[1].split("9.")[0]
        self.assertIn("NON CHIFFRÉES", bloc)
        self.assertIn("pas zéro", bloc)

    def test_ce_qui_est_ignore_nest_pas_melange_a_ce_qui_est_a_surveiller(self):
        ignorer = self.texte.split("5. QUOI IGNORER")[1].split("6.")[0]
        surveiller = self.texte.split("3. QUOI SURVEILLER")[1].split("4.")[0]
        self.assertIn("Changement de logo", ignorer)
        self.assertNotIn("Changement de logo", surveiller)


class LePlanDeMesureNaPasDeSourcePrincipale(unittest.TestCase):
    def test_les_huit_familles_sont_declarees(self):
        from radar import validation
        lettres = [l for l, _, _ in validation.FAMILLES_PREVUES]
        self.assertEqual(lettres, list("ABCDEFGH"))

    def test_les_deux_dimensions_ne_se_deduisent_pas_lune_de_lautre(self):
        """Une donnée réelle observée n'est PAS une opportunité testée."""
        from radar import validation
        e = validation.Etat(tests_coherence=1, mesures=[
            validation.Mesure(horodatage="2026-09-04T00:00:00+00:00",
                              famille="page_web", origine="test",
                              reference="http://x", empreinte="a1",
                              completude="page complète", porte_un_besoin=False)])
        self.assertEqual(e.donnees_observees(), 1)
        self.assertEqual(e.opportunites_testees(), 0)
        self.assertIn("OPPORTUNITÉ COMMERCIALE TESTÉE ✗", e.rendu())

    def test_une_famille_hors_plan_ne_couvre_aucune_des_huit(self):
        from radar import validation
        e = validation.Etat(tests_coherence=1, mesures=[
            validation.Mesure(horodatage="2026-09-04T00:00:00+00:00",
                              famille="page_web", origine="test",
                              reference="http://x", empreinte="a1",
                              porte_un_besoin=True)])
        self.assertEqual(len(e.hors_plan), 1)
        for *_, etat, _ in e.plan_de_mesure():
            self.assertEqual(etat, "NON MESURÉE")

    def test_la_prochaine_mesure_vise_une_famille_non_couverte(self):
        """Jamais une seconde page de la famille déjà mesurée : c'est ainsi
        qu'une source devient « la principale » sans que personne le décide."""
        from radar import validation
        e = validation.Etat(tests_coherence=1, mesures=[
            validation.Mesure(horodatage="2026-09-04T00:00:00+00:00",
                              famille="entreprise", origine="test",
                              reference="http://x", empreinte="a1",
                              porte_un_besoin=True)])
        suite = e.prochaine_mesure()
        self.assertIn("jamais mesurée", suite)
        self.assertNotIn("A. entreprise", suite)


# ═══════════════════════════════════════════════════════════════════════════
#  §CA — TROIS ÉTATS DU CHIFFRE D'AFFAIRES, ET L'UNITÉ QUI SE DÉCLARE
#
#  Un seul défaut réel derrière ces tests, mais il coûtait cher : le montant
#  était toujours traité comme un TOTAL réparti sur la durée. Une tournée de
#  bourse de fret à 4 200 € ressortait donc à 350 €/mois au lieu de 18 186.
#  L'erreur allait dans le sens qui fait RATER une bonne affaire.
# ═══════════════════════════════════════════════════════════════════════════

class LeChiffreDAffairesADroitATroisEtats(unittest.TestCase):
    def test_publie(self):
        from radar.chiffre_affaires import Etat, mesurer
        ca = mesurer(opp(montant=180000, duree_mois=12))
        self.assertIs(ca.etat, Etat.PUBLIE)
        self.assertEqual(round(ca.mensuel), 15000)
        self.assertIn("PUBLIÉ", ca.ligne())

    def test_inconnu_nest_ni_zero_ni_bonus(self):
        from radar.chiffre_affaires import Etat, mesurer
        ca = mesurer(opp())
        self.assertIs(ca.etat, Etat.INCONNU)
        self.assertIsNone(ca.mensuel)
        self.assertNotIn("0 €", ca.ligne())
        self.assertTrue(ca.detail(), "un CA inconnu doit dire ce qu'il faut demander")

    def test_aucune_estimation_sans_base_declaree_au_profil(self):
        """Une fourchette inventée est pire qu'un trou : un trou se voit."""
        from radar.chiffre_affaires import Etat, mesurer
        self.assertIs(mesurer(opp(vehicules_requis=4)).etat, Etat.INCONNU)
        ca = mesurer(opp(vehicules_requis=4),
                     {"references_economiques": {"ca_mensuel_par_vehicule": 3500}})
        self.assertIs(ca.etat, Etat.ESTIMABLE)
        self.assertLess(ca.bas, ca.mensuel)
        self.assertGreater(ca.haut, ca.mensuel)
        self.assertIn("MÉTHODE", ca.detail()[0])

    def test_la_fourchette_saffiche_sans_perdre_un_facteur_dix(self):
        """« 10.5 k€ » arrondi puis dépouillé de son zéro devenait « 1 k€ »."""
        from radar.chiffre_affaires import mesurer
        ligne = mesurer(opp(vehicules_requis=4),
                        {"references_economiques": {"ca_mensuel_par_vehicule": 3500}}).ligne()
        self.assertIn("10", ligne)
        self.assertIn("18", ligne)

    def test_un_prix_recurrent_nest_pas_un_total_annuel(self):
        from radar.chiffre_affaires import Etat, mesurer
        ca = mesurer(opp(montant=4200, cadence="hebdomadaire",
                         montant_unite="par_periode"))
        self.assertIs(ca.etat, Etat.PUBLIE)
        self.assertGreater(ca.mensuel, 15000)

    def test_un_prix_recurrent_sans_cadence_ne_se_devine_pas(self):
        from radar.chiffre_affaires import Etat, mesurer
        ca = mesurer(opp(montant=4200, montant_unite="par_periode", cadence=None))
        self.assertIs(ca.etat, Etat.INCONNU)
        self.assertIn("cadence", ca.manque)

    def test_le_score_note_le_meme_chiffre_que_la_fiche(self):
        """La fiche affichait 18 186 €/mois et le score notait 350."""
        r = moteur().analyser(opp(source="bourse_fret", intitule="Tournée régulière",
                                  texte="Transport de palettes, 3 rotations.",
                                  montant=4200, cadence="hebdomadaire",
                                  montant_unite="par_periode", pays_livraison=["BE"]),
                              MAINTENANT)
        taille = [l for l in r.score.lignes if l.critere == "taille adaptée"][0]
        self.assertIn("18", taille.raison)


class ZeroNestPasNonMesure(unittest.TestCase):
    """§11 : « 0 » veut dire « on a regardé, il n'y avait rien ».
    « NON MESURÉ » veut dire « personne n'y est allé ». Les confondre fait
    abandonner une famille sans l'avoir ouverte."""

    def test_une_famille_jamais_observee_affiche_un_tiret_pas_un_zero(self):
        from radar import validation
        tableau = validation.Etat(tests_coherence=1, mesures=[]).tableau_des_familles()
        self.assertIn("NON MESURÉE", tableau)
        for ligne in tableau.splitlines():
            if "NON MESURÉE" in ligne:
                self.assertNotIn(" 0 ", ligne, "une famille non mesurée affiche 0")

    def test_une_famille_observee_sans_opportunite_affiche_bien_zero(self):
        from radar import validation
        e = validation.Etat(tests_coherence=1, mesures=[
            validation.Mesure(horodatage="2026-09-04T00:00:00+00:00",
                              famille="entreprise", origine="test",
                              reference="http://x", empreinte="a1",
                              porte_un_besoin=False)])
        ligne = [l for l in e.tableau_des_familles().splitlines()
                 if "A. entreprise" in l][0]
        self.assertIn("observée, sans opportunité", ligne)
        self.assertNotIn("NON MESURÉE", ligne)

    def test_le_bulletin_dit_non_disponible_quand_rien_de_reel(self):
        from radar import validation
        b = validation.Etat(tests_coherence=999, mesures=[]).bulletin()
        self.assertIn("MESURE COMMERCIALE : NON DISPONIBLE", b)
        self.assertNotIn("999", b, "le nombre de tests n'a rien à faire ici")


class LeBulletinCommercialPasseAvantLaMachine(unittest.TestCase):
    def setUp(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [
            avis_public(ref_source="A", intitule="Tournée régionale de palettes",
                        texte="Transport de palettes en Wallonie.", montant=96000,
                        duree_mois=12, cadence="hebdomadaire", pays_livraison=["BE"]),
            opp(source="entreprise", ref_source="B",
                intitule="Nous recherchons un transporteur",
                texte="Nous recherchons un transporteur pour nos livraisons.",
                acheteur="Delhaize", secteur_acheteur="prive", pays_livraison=["BE"]),
        ], maintenant_dt=MAINTENANT)
        from radar.rapport import construire
        self.r = construire(cx, Mode.DEMO, cible={}, proche_km=50)
        self.texte = self.r.en_texte(avec_fiches=False)

    def test_le_bulletin_ouvre_le_rapport(self):
        entete = self.texte.split("=" * 72)[0]
        for ligne in ("DONNÉES RÉELLES OBSERVÉES", "OPPORTUNITÉS RÉELLES",
                      "CA RÉELLEMENT IDENTIFIÉ", "OPPORTUNITÉS POSTULABLES",
                      "OPPORTUNITÉS À CONTACTER", "SIGNAUX",
                      "OPPORTUNITÉS À SURVEILLER", "CAPACITÉS MANQUANTES",
                      "TOP 5 DES ACTIONS"):
            self.assertIn(ligne, entete)

    def test_chaque_affaire_porte_son_ca_et_son_action(self):
        bloc = self.texte.split("🔥 À ATTAQUER MAINTENANT")[1][:600]
        self.assertIn("CA         :", bloc)
        self.assertIn("Action     :", bloc)

    def test_le_tableau_des_sources_ne_classe_pas_par_volume(self):
        """VOLUME ≠ VALEUR : le tableau ne désigne aucune source principale."""
        self.assertIn("VOLUME ≠ VALEUR", self.texte)
        self.assertIn("aucune « source principale »", self.texte)
        bloc = self.texte.split("VOLUME ≠ VALEUR")[1].split("TOP ACTIONS")[0]
        sources = [l.split()[0] for l in bloc.splitlines()
                   if l.startswith("  ") and l.strip() and not l.strip().startswith(("source", "─", "Une", "qu'une", "tableau"))]
        self.assertEqual(sources, sorted(sources),
                         "les sources doivent être en ordre alphabétique, "
                         "jamais classées par volume")
