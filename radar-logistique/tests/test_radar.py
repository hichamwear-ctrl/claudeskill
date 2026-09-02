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

from radar.activite import Ontologie
from radar.base import ouvrir
from radar.capacite import Capacites, Niveau
from radar.chaine import Moteur, traiter
from radar.classification import Type
from radar.geographie import Geographie, Zone
from radar.lots import lots_de
from radar.modele import LotBrut, Opportunite
from radar.role import DetecteurDeRole, Role
from radar.sondage import sonder

MAINTENANT = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
DEMAIN = "2026-11-15T11:00:00+01:00"


def cfg(n):
    return yaml.safe_load((RACINE / n).read_text(encoding="utf-8"))


PROFIL, CAPACITES = cfg("profil.yaml"), cfg("config/capacites.yaml")
GEO, PONDS, ROLES = cfg("config/geographie.yaml"), cfg("config/ponderations.yaml"), cfg("config/roles.yaml")


def moteur():
    return Moteur(PROFIL, CAPACITES, GEO, PONDS, ROLES)


def opp(**kw):
    base = dict(source="bda", ref_source="R1", intitule="Marché",
                texte="transport routier de marchandises", type_avis="appel-offres",
                cpv=["60000000"], pays_livraison=["BE"], echeance_brute=DEMAIN)
    base.update(kw)
    return Opportunite(**base)


# ═══════════════════════ §13 — fourniture contre prestation logistique
class FournitureOuPrestation(unittest.TestCase):
    def setUp(self):
        self.d = DetecteurDeRole(ROLES)

    def test_fourniture_et_livraison_de_poissons_n_est_pas_du_transport(self):
        a = self.d.analyser("Fourniture et livraison de poissons frais", ["15200000"])
        self.assertIs(a.role, Role.FOURNISSEUR)

    def test_le_mot_livraison_ne_suffit_pas_a_faire_un_marche_de_transport(self):
        a = self.d.analyser("Fourniture et livraison de mobilier de bureau", ["39130000"])
        self.assertIs(a.role, Role.FOURNISSEUR)

    def test_transport_pour_le_compte_de_est_une_prestation(self):
        a = self.d.analyser("Transport de produits pour le compte de l'hôpital", ["60000000"])
        self.assertIs(a.role, Role.PRESTATAIRE)

    def test_un_marche_de_travaux_est_rejete(self):
        self.assertIs(self.d.analyser("Construction d'un entrepôt", ["45210000"]).role,
                      Role.FOURNISSEUR)

    def test_sans_signal_on_ne_tranche_pas(self):
        self.assertIs(self.d.analyser("Marché divers", None).role, Role.A_VERIFIER)

    def test_un_marche_de_fourniture_n_est_jamais_notifie(self):
        cx = ouvrir(":memory:")
        o = opp(ref_source="POISSON", intitule="Fourniture et livraison de poissons",
                texte="fourniture et livraison de poissons frais", cpv=["15200000"])
        traiter(cx, moteur(), [o], maintenant_dt=MAINTENANT)
        self.assertEqual(cx.execute("SELECT count(*) c FROM envois").fetchone()["c"], 0)


# ═══════════════════════ §10 — analyse lot par lot
class AnalyseParLot(unittest.TestCase):
    MARCHE = dict(
        ref_source="MULTILOT",
        intitule="Fourniture, livraison et installation d'équipements",
        texte="fourniture et installation d'équipements techniques",
        cpv=["42000000"],
        lots=[LotBrut(numero="1", intitule="Fourniture de machines",
                      texte="fourniture de machines-outils", cpv=["42600000"]),
              LotBrut(numero="15", intitule="Déménagement de postes de soudure",
                      texte="déménagement et manutention de postes de soudure",
                      cpv=["98392000"])])

    def test_un_marche_a_plusieurs_lots_est_bien_decoupe(self):
        self.assertEqual(len(lots_de(opp(**self.MARCHE))), 2)

    def test_un_marche_sans_lot_en_a_un_lui_meme(self):
        self.assertEqual(len(lots_de(opp())), 1)

    def test_un_seul_lot_compatible_sauve_le_marche(self):
        """Le titre général dit « fourniture » ; le lot 15 est un déménagement."""
        r = moteur().analyser(opp(**self.MARCHE), MAINTENANT)
        self.assertIs(r.classement.type, Type.DIRECT)
        self.assertTrue(any("LOT 15" in l for l in r.lots_retenus))

    def test_le_lot_incompatible_n_est_pas_retenu(self):
        r = moteur().analyser(opp(**self.MARCHE), MAINTENANT)
        self.assertFalse(any("LOT 1 " in l for l in r.lots_retenus))

    def test_un_lot_herite_de_la_geographie_du_marche(self):
        lots = lots_de(opp(pays_collecte=["NL"], pays_livraison=["BE"],
                           lots=[LotBrut(numero="1", intitule="Transport")]))
        self.assertEqual(lots[0].pays_collecte, ["NL"])


# ═══════════════════════ §1 — les trois niveaux de capacité
class TroisNiveauxDeCapacite(unittest.TestCase):
    def setUp(self):
        self.c = Capacites(PROFIL, CAPACITES["exigences"])

    def test_dans_la_flotte_actuelle(self):
        self.assertIs(self.c.vehicules(4).niveau, Niveau.ACTUELLE)

    def test_au_dela_de_la_flotte_mais_louable(self):
        r = self.c.vehicules(12)
        self.assertIs(r.niveau, Niveau.MOBILISABLE)
        self.assertIn("louer", r.message)

    def test_au_dela_du_mobilisable_est_bloquant(self):
        self.assertIs(self.c.vehicules(25).niveau, Niveau.NON_DISPONIBLE)

    def test_une_qualification_ne_se_loue_pas(self):
        """ADR est déclaré absent : la mobilisation ne couvre pas les agréments."""
        self.assertIs(self.c.qualification("adr").niveau, Niveau.NON_DISPONIBLE)

    def test_une_qualification_inconnue_n_est_jamais_presumee(self):
        r = self.c.qualification("gdp")
        self.assertIs(r.niveau, Niveau.A_VERIFIER)
        self.assertIn("non confirmé", r.message)

    def test_anciennete_insuffisante_ne_bloque_pas_seule(self):
        self.assertIs(self.c.anciennete(3).niveau, Niveau.A_VERIFIER)

    def test_chiffre_affaires_inconnu_ne_bloque_pas(self):
        self.assertIs(self.c.chiffre_affaires(500000).niveau, Niveau.A_VERIFIER)


# ═══════════════════════ §11 — les quatre catégories
class QuatreCategories(unittest.TestCase):
    def test_marche_normal_est_direct(self):
        r = moteur().analyser(opp(), MAINTENANT)
        self.assertIs(r.classement.type, Type.DIRECT)

    def test_trop_gros_pour_moi_devient_sous_traitance(self):
        """Ce que je ne peux pas porter seul, un autre le portera — avec des bras."""
        r = moteur().analyser(opp(exigences={"vehicules_min": 30}), MAINTENANT)
        self.assertIs(r.classement.type, Type.SOUS_TRAITANCE)

    def test_qualification_manquante_est_un_rejet_pas_une_sous_traitance(self):
        """Ce que je ne sais pas faire, personne ne me le sous-traitera."""
        r = moteur().analyser(opp(exigences={"adr": True}), MAINTENANT)
        self.assertIs(r.classement.type, Type.REJET)

    def test_un_marche_attribue_devient_une_piste_de_sous_traitance(self):
        r = moteur().analyser(opp(attribue=True, titulaire="Grand opérateur"), MAINTENANT)
        self.assertIs(r.classement.type, Type.SOUS_TRAITANCE)

    def test_un_signal_est_un_prospect(self):
        r = moteur().analyser(opp(est_signal=True, signal_code="recrutement_massif"),
                              MAINTENANT)
        self.assertIs(r.classement.type, Type.PROSPECT)

    def test_les_rejets_ne_sont_jamais_notifies(self):
        cx = ouvrir(":memory:")
        lot = [opp(ref_source="OK", intitule="Transport de colis"),
               opp(ref_source="ADR", intitule="Transport de produits chimiques",
                   exigences={"adr": True}),
               opp(ref_source="CLOS", intitule="Transport de palettes",
                   echeance_brute="2026-08-01T11:00:00+02:00"),
               opp(ref_source="FR", intitule="Transport Lyon Marseille",
                   pays_collecte=["FR"], pays_livraison=["FR"])]
        b = traiter(cx, moteur(), lot, maintenant_dt=MAINTENANT)
        refs = {l["ref_source"] for l in cx.execute("SELECT ref_source FROM envois")}
        self.assertEqual(refs, {"OK"})
        self.assertEqual(b.rejet, 3)


# ═══════════════════════ §9 — géographie
class Geographie_(unittest.TestCase):
    def setUp(self):
        self.g = Geographie(GEO)

    def test_pays_bas_vers_belgique_est_le_modele(self):
        r = self.g.evaluer(["NL"], ["BE"])
        self.assertIs(r.zone, Zone.CORRIDOR)
        self.assertTrue(r.corridor_eprouve)

    def test_france_vers_france_est_rejete(self):
        self.assertFalse(self.g.evaluer(["FR"], ["FR"]).compatible)

    def test_madrid_vers_madrid_est_rejete(self):
        self.assertFalse(self.g.evaluer(["ES"], ["ES"]).compatible)

    def test_toute_l_europe_vers_la_belgique_reste_ouvert(self):
        for pays in ("FR", "DE", "LU", "ES", "IT", "PL"):
            with self.subTest(pays=pays):
                self.assertIs(self.g.evaluer([pays], ["BE"]).zone, Zone.CORRIDOR)

    def test_lieu_absent_ne_fait_pas_disparaitre_l_opportunite(self):
        self.assertTrue(self.g.evaluer([], []).compatible)


# ═══════════════════════ §7 et §15 — le score sert la PME
class ScorePME(unittest.TestCase):
    def _score(self, **kw):
        return moteur().analyser(opp(**kw), MAINTENANT).score.total

    def test_un_petit_contrat_recurrent_bat_un_tres_gros_marche(self):
        petit = self._score(montant=192000, duree_mois=24, cadence="quotidienne")
        gros = self._score(montant=5000000, duree_mois=48, cadence="quotidienne",
                           exigences={"chiffre_affaires_min": 2000000})
        self.assertGreater(petit, gros)

    def test_la_recurrence_vaut_mieux_qu_une_prestation_ponctuelle(self):
        self.assertGreater(self._score(cadence="quotidienne"), self._score(cadence="ponctuelle"))

    def test_un_montant_non_publie_ne_penalise_pas(self):
        self.assertGreater(self._score(montant=None), 0)

    def test_le_score_ne_supprime_jamais_une_opportunite(self):
        cx = ouvrir(":memory:")
        b = traiter(cx, moteur(), [opp(ref_source="FAIBLE", cadence="ponctuelle",
                                       montant=900)], maintenant_dt=MAINTENANT)
        self.assertEqual(b.notifies, 1)

    def test_chaque_point_est_justifie(self):
        for ligne in moteur().analyser(opp(montant=250000, duree_mois=24), MAINTENANT).score.lignes:
            self.assertTrue(ligne.raison, f"« {ligne.critere} » n'explique pas ses points")

    def test_les_ponderations_viennent_de_la_configuration(self):
        modifie = yaml.safe_load(yaml.safe_dump(PONDS))
        modifie["criteres"]["adequation_operationnelle"] = 0
        autre = Moteur(PROFIL, CAPACITES, GEO, modifie, ROLES)
        self.assertGreater(moteur().analyser(opp(), MAINTENANT).score.total,
                           autre.analyser(opp(), MAINTENANT).score.total)


# ═══════════════════════ §14 et §9 — ne jamais inventer
class NeJamaisInventer(unittest.TestCase):
    def test_aucune_date_n_est_forgee(self):
        from radar.statut import parse_date
        self.assertIsNone(parse_date("prochainement")[0])
        self.assertIsNone(parse_date(None)[0])

    def test_une_echeance_illisible_ne_fait_pas_disparaitre_le_marche(self):
        cx = ouvrir(":memory:")
        b = traiter(cx, moteur(), [opp(ref_source="SANSDATE", echeance_brute=None)],
                    maintenant_dt=MAINTENANT)
        self.assertEqual(b.notifies, 1)

    def test_une_certification_non_confirmee_n_est_pas_affirmee(self):
        r = moteur().analyser(opp(exigences={"gdp": True}), MAINTENANT)
        self.assertTrue(any("GDP" in v or "gdp" in v for v in r.bilan.a_verifier))
        self.assertFalse(r.bilan.bloquants)

    def test_un_montant_absent_s_affiche_non_publie(self):
        texte = moteur().analyser(opp(montant=None), MAINTENANT).fiche.en_texte()
        self.assertIn("NON PUBLIÉ", texte)
        self.assertNotIn("0 EUR", texte)


# ═══════════════════════ §26 — les seize questions
class SeizeQuestions(unittest.TestCase):
    def test_le_journal_repond_aux_seize_questions(self):
        j = moteur().analyser(opp(acheteur="Commune", montant=120000, duree_mois=24),
                              MAINTENANT).journal
        numerotees = [q for q in j.reponses if q[0].isdigit()]
        self.assertEqual(len(numerotees), 16)

    def test_ce_qui_ne_peut_pas_etre_repondu_vaut_a_verifier(self):
        j = moteur().analyser(opp(acheteur=None, montant=None), MAINTENANT).journal
        self.assertIn("1. qui achète ?", j.sans_reponse())


# ═══════════════════════ §17 à §19 — les trois formats
class TroisFormats(unittest.TestCase):
    def test_le_format_direct_donne_l_essentiel(self):
        t = moteur().analyser(opp(montant=300000, duree_mois=24), MAINTENANT).fiche.en_texte()
        for attendu in ("OPPORTUNITÉ À POSTULER", "Deadline", "Valeur estimée",
                        "Pourquoi c'est compatible", "Score", "Action"):
            self.assertIn(attendu, t)

    def test_le_format_sous_traitance_nomme_le_titulaire(self):
        t = moteur().analyser(opp(attribue=True, titulaire="Grand opérateur"),
                              MAINTENANT).fiche.en_texte()
        self.assertIn("SOUS-TRAITANCE", t)
        self.assertIn("Grand opérateur", t)

    def test_le_format_prospect_propose_une_prise_de_contact(self):
        t = moteur().analyser(opp(est_signal=True, acheteur="Réseau colis",
                                  signal_code="recrutement_massif"),
                              MAINTENANT).fiche.en_texte()
        self.assertIn("PROSPECT COMMERCIAL", t)
        self.assertIn("responsable logistique", t)

    def test_les_moyens_a_mobiliser_sont_annonces(self):
        t = moteur().analyser(opp(exigences={"vehicules_min": 12}), MAINTENANT).fiche.en_texte()
        self.assertIn("À mobiliser", t)


# ═══════════════════════ §20 — mémoire des marchés
class MemoireDesMarches(unittest.TestCase):
    def test_une_attribution_est_conservee_avec_sa_date_de_renouvellement(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(ref_source="ATTR", attribue=True, duree_mois=36,
                                   attribue_le="2026-09-01", titulaire="X")],
                maintenant_dt=MAINTENANT)
        l = cx.execute("SELECT * FROM attributions").fetchone()
        self.assertTrue(l["renouvellement"].startswith("2029"))

    def test_sans_duree_la_date_n_est_pas_inventee(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(ref_source="A2", attribue=True, duree_mois=None)],
                maintenant_dt=MAINTENANT)
        l = cx.execute("SELECT * FROM attributions").fetchone()
        self.assertIsNone(l["renouvellement"])
        self.assertEqual(l["fiabilite"], "A_VERIFIER")


# ═══════════════════════ §5 — le vocabulaire de l'acheteur
class VocabulaireDeLAcheteur(unittest.TestCase):
    def setUp(self):
        self.o = Ontologie(CAPACITES, PROFIL["familles_actives"], PROFIL["familles_exclues"])

    def test_distribution_urbaine_est_du_dernier_kilometre(self):
        self.assertIn("dernier_kilometre",
                      self.o.analyser("Distribution urbaine de marchandises").familles)

    def test_le_neerlandais_est_compris(self):
        self.assertIn("dernier_kilometre", self.o.analyser("Stadsdistributie").familles)

    def test_l_anglais_est_compris(self):
        self.assertIn("dernier_kilometre", self.o.analyser("Last mile delivery").familles)


# ═══════════════════════ §22 — mesurer sans inventer
class Sondage(unittest.TestCase):
    def test_sous_trente_opportunites_aucun_pourcentage(self):
        s = sonder(moteur(), [opp()], "bda", MAINTENANT)
        self.assertIn("aucun pourcentage n'est publié", s.rapport())

    def test_une_grandeur_non_observee_sort_en_non_mesure(self):
        s = sonder(moteur(), [opp(montant=None, cadence=None)], "bda", MAINTENANT)
        self.assertIn("NON MESURÉ", s.rapport())

    def test_le_sondage_juge_la_source_sur_ce_qu_elle_produit_d_utile(self):
        s = sonder(moteur(), [opp(), opp(ref_source="R2", exigences={"adr": True})],
                   "bda", MAINTENANT)
        self.assertIn("opportunité(s) exploitable(s)", s.rapport())


# ═══════════════════════ déduplication et envoi
class Garanties(unittest.TestCase):
    def test_le_meme_marche_vu_deux_fois_ne_notifie_qu_une_fois(self):
        cx = ouvrir(":memory:")
        a = opp(source="ted", ref_source="T1", acheteur="CHU", intitule="Transport de colis")
        b = opp(source="bda", ref_source="B1", acheteur="CHU", intitule="Transport de colis")
        bilan = traiter(cx, moteur(), [a, b], maintenant_dt=MAINTENANT)
        self.assertEqual(bilan.doublons, 1)
        self.assertEqual(cx.execute("SELECT count(*) c FROM envois").fetchone()["c"], 1)

    def test_un_envoi_interrompu_n_est_jamais_reemis(self):
        from radar import envoi
        cx = ouvrir(":memory:")
        envoi.mettre_en_file(cx, "bda", "R1", "corps")
        cx.execute("UPDATE envois SET etat='en_cours'")
        self.assertEqual(envoi.reprendre_interrompus(cx), 1)
        self.assertEqual(len(envoi.a_envoyer(cx)), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ═══════════════════════ non-régression : CPV générique
class CpvGenerique(unittest.TestCase):
    def setUp(self):
        self.o = Ontologie(CAPACITES, PROFIL["familles_actives"], PROFIL["familles_exclues"])

    def test_un_cpv_generique_ne_designe_pas_une_specialite(self):
        """« 60000000 » est déclaré par presque toutes les familles : il confirme
        le domaine, il ne dit pas qu'un marché de colis est pharmaceutique."""
        r = self.o.analyser("Distribution régionale de marchandises", ["60000000"])
        self.assertNotIn("pharmaceutique", r.familles)
        self.assertNotIn("alimentaire", r.familles)

    def test_mais_il_empeche_un_rejet_pour_activite_inconnue(self):
        r = self.o.analyser("Marché sans vocabulaire reconnaissable", ["60000000"])
        self.assertTrue(r.correspond)
        self.assertTrue(r.domaine_transport)

    def test_un_cpv_specifique_designe_bien_sa_famille(self):
        self.assertIn("dernier_kilometre",
                      self.o.analyser("Intitulé neutre", ["64120000"]).familles)


# ═══════════════════════ §21 et §24 — apprentissage
class Apprentissage(unittest.TestCase):
    def test_aucune_conclusion_sous_dix_observations(self):
        from radar.apprentissage import apprendre
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp()], maintenant_dt=MAINTENANT)
        self.assertIn("Aucune conclusion", apprendre(cx).rapport())

    def test_le_rendement_par_source_est_calcule(self):
        from radar.apprentissage import apprendre
        cx = ouvrir(":memory:")
        lot = [opp(ref_source=f"R{i}", intitule=f"Transport de colis lot {i}")
               for i in range(12)]
        traiter(cx, moteur(), lot, maintenant_dt=MAINTENANT)
        a = apprendre(cx)
        self.assertTrue(a.rendements)
        self.assertEqual(a.rendements[0].source, "bda")
