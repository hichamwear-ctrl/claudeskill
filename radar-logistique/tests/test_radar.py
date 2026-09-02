"""Tests de COMPORTEMENT.

Un test qui vérifie qu'une ligne de code est présente ne prouve rien : sur le
projet précédent, le seuil contourné vivait sous un test vert. Chaque test ici
pose une question à laquelle l'exploitant tient : « est-ce que ça peut
disparaître de mes opportunités ? », « est-ce que ça peut partir deux fois ? ».
"""

import json
import sqlite3
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radar import actionnabilite as act, eligibilite as eli, envoi
from radar.base import ouvrir
from radar.chaine import traiter
from radar.correspondance import Correspondance
from radar.fiche import Fiche

MAINTENANT = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
RACINE = Path(__file__).resolve().parent.parent
PROFIL = yaml.safe_load((RACINE / "profil.yaml").read_text(encoding="utf-8"))


class CritereActionnable(unittest.TestCase):
    """« Est-ce que je peux encore postuler aujourd'hui ? »"""

    def test_marche_cloture_hier_nest_pas_actionnable(self):
        v = act.evaluer(type_avis="appel-offres", echeance="2026-09-01T11:00:00+02:00",
                        maintenant=MAINTENANT)
        self.assertFalse(v.actionnable)
        self.assertIs(v.statut, act.Statut.CLOTURE)

    def test_marche_ouvert_demain_est_actionnable(self):
        v = act.evaluer(type_avis="appel-offres", echeance="2026-09-03T11:00:00+02:00",
                        maintenant=MAINTENANT)
        self.assertTrue(v.actionnable)
        self.assertTrue(v.urgent, "un délai de 1 jour doit être signalé comme tendu")

    def test_attribution_nest_jamais_actionnable_meme_avec_date_future(self):
        """L'ordre des règles compte : un marché attribué reste fermé."""
        v = act.evaluer(type_avis="attribution", echeance="2027-01-01T11:00:00+01:00",
                        maintenant=MAINTENANT)
        self.assertFalse(v.actionnable)
        self.assertIs(v.statut, act.Statut.ATTRIBUE)

    def test_avis_informatif_nest_pas_actionnable(self):
        v = act.evaluer(type_avis="information-prealable", echeance="2026-12-01T11:00:00+01:00",
                        maintenant=MAINTENANT)
        self.assertFalse(v.actionnable)

    def test_echeance_illisible_est_livree_et_signalee(self):
        """Le cas dangereux : ne JAMAIS faire disparaître un marché peut-être ouvert."""
        for valeur in (None, "", "prochainement", "31/02/2026"):
            with self.subTest(valeur=valeur):
                v = act.evaluer(type_avis="appel-offres", echeance=valeur, maintenant=MAINTENANT)
                self.assertTrue(v.actionnable, f"{valeur!r} ne doit pas écarter l'annonce")
                self.assertTrue(v.signalements, "l'incertitude doit être signalée")

    def test_aucune_date_de_repli_nest_inventee(self):
        dt, echec = act.parse_echeance("n'importe quoi")
        self.assertIsNone(dt)
        self.assertIsNotNone(echec)

    def test_heure_sans_fuseau_est_lue_en_heure_belge(self):
        dt, _ = act.parse_echeance("2026-10-15 11:00")
        self.assertEqual(dt.utcoffset().total_seconds(), 2 * 3600)


class Eligibilite(unittest.TestCase):

    def test_exigence_structuree_bloque(self):
        r = eli.evaluer([eli.Exigence("surface_min_m2", 2000, structuree=True)], PROFIL)
        self.assertFalse(r.peut_deposer)

    def test_meme_exigence_en_texte_libre_ne_bloque_pas(self):
        """Une lecture de texte libre est faillible : elle ne peut pas fermer la porte."""
        r = eli.evaluer([eli.Exigence("surface_min_m2", 2000, structuree=False)], PROFIL)
        self.assertTrue(r.peut_deposer)
        self.assertTrue(r.reserves)

    def test_capacite_non_verifiee_ne_bloque_pas(self):
        """froid_positif vaut « À CONFIRMER » au profil : inconnu n'est pas impossible."""
        r = eli.evaluer([eli.Exigence("froid_requis", True)], PROFIL)
        self.assertTrue(r.peut_deposer)
        self.assertTrue(r.reserves)

    def test_flotte_insuffisante_devient_reserve_car_location_possible(self):
        r = eli.evaluer([eli.Exigence("vehicules_min", 12)], PROFIL)
        self.assertTrue(r.peut_deposer)

    def test_atouts_expliquent_pourquoi_ca_correspond(self):
        r = eli.evaluer([eli.Exigence("afsca_requis", True)], PROFIL)
        self.assertTrue(any("AFSCA" in a for a in r.atouts))


class FicheAction(unittest.TestCase):

    def _fiche(self, **kw):
        base = dict(reference="X", intitule="Lot", acheteur=None, contact=None, objet=None,
                    montant=None, devise="EUR", echeance_texte="ouvert", jours_restants=20,
                    plateforme=None, lien_depot=None, lien_documents=None)
        base.update(kw)
        return Fiche(**base)

    def test_montant_absent_nest_jamais_invente(self):
        t = self._fiche().en_texte()
        self.assertIn("NON PUBLIÉ", t)
        self.assertNotIn("0 EUR", t)

    def test_les_sept_champs_demandes_sont_presents(self):
        t = self._fiche(acheteur="CHU", montant=610000, objet="Distribution",
                        plateforme="e-Tendering").en_texte()
        for attendu in ("CLÔTURE", "MONTANT", "ACHETEUR", "CE QUI EST DEMANDÉ",
                        "CONDITIONS POUR RÉPONDRE", "OÙ DÉPOSER", "POURQUOI TU CORRESPONDS"):
            self.assertIn(attendu, t)


class FileDEnvoi(unittest.TestCase):

    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_une_annonce_ne_part_pas_deux_fois(self):
        self.assertTrue(envoi.mettre_en_file(self.cx, "ted", "REF-1", "corps"))
        self.assertFalse(envoi.mettre_en_file(self.cx, "ted", "REF-1", "corps"))

    def test_envoi_interrompu_devient_ambigu_et_nest_pas_reemis(self):
        envoi.mettre_en_file(self.cx, "ted", "REF-1", "corps")
        self.cx.execute("UPDATE envois SET etat='en_cours'")
        self.assertEqual(envoi.reprendre_interrompus(self.cx), 1)
        self.assertEqual(len(envoi.a_envoyer(self.cx)), 0)

    def test_echec_de_transport_ne_marque_pas_delivre(self):
        envoi.mettre_en_file(self.cx, "ted", "REF-1", "corps")
        def transport_casse(_):
            raise ConnectionError("réseau")
        self.assertEqual(envoi.vider(self.cx, transport_casse)["echec"], 1)
        etat = self.cx.execute("SELECT etat FROM envois").fetchone()["etat"]
        self.assertEqual(etat, "echec")

    def test_timeout_est_ambigu_pas_un_echec_reessayable(self):
        envoi.mettre_en_file(self.cx, "ted", "REF-1", "corps")
        def transport_timeout(_):
            raise TimeoutError("issue inconnue")
        self.assertEqual(envoi.vider(self.cx, transport_timeout)["ambigu"], 1)
        self.assertEqual(len(envoi.a_envoyer(self.cx)), 0)


class ChaineComplete(unittest.TestCase):
    """Le test qui compte : ce que l'exploitant reçoit réellement."""

    LOT = [
        {"publication-number": "OUVERT-1", "notice-type": "appel-offres",
         "title": {"fra": "Distribution pharma sous température dirigée"},
         "buyer": {"name": {"fra": "Réseau hospitalier"}},
         "estimated-value": {"amount": 610000, "currency": "EUR"},
         "deadline-receipt-tender": "2026-10-15T11:00:00+02:00",
         "submission-url": "https://exemple/e-tendering/OUVERT-1",
         "exige_afsca": True, "exige_licence": True},
        {"publication-number": "CLOS-1", "notice-type": "appel-offres",
         "title": {"fra": "Tournée déjà clôturée"},
         "deadline-receipt-tender": "2026-08-01T11:00:00+02:00"},
        {"publication-number": "ATTRIB-1", "notice-type": "attribution",
         "title": {"fra": "Marché attribué à un tiers"},
         "deadline-receipt-tender": "2026-12-01T11:00:00+01:00"},
        {"publication-number": "INFO-1", "notice-type": "information-prealable",
         "title": {"fra": "Avis de préinformation"}},
        {"publication-number": "SANSDATE-1", "notice-type": "appel-offres",
         "title": {"fra": "Échéance non publiée"}},
        {"publication-number": "TROPGROS-1", "notice-type": "appel-offres",
         "title": {"fra": "Plateforme régionale 2000 m2"},
         "deadline-receipt-tender": "2026-11-01T11:00:00+01:00",
         "surface_min_m2": 2000},
    ]

    def setUp(self):
        self.cx = ouvrir(":memory:")
        cfg = yaml.safe_load((RACINE / "sources" / "ted.yaml").read_text(encoding="utf-8"))
        self.corr = Correspondance.depuis_config(cfg)
        self.bilan = traiter(self.cx, "ted", self.LOT, self.corr, PROFIL,
                             maintenant_dt=MAINTENANT)

    def _refs_notifiees(self):
        return {l["ref_source"] for l in self.cx.execute("SELECT ref_source FROM envois")}

    def test_seuls_les_marches_encore_deposables_sont_notifies(self):
        self.assertEqual(self._refs_notifiees(), {"OUVERT-1", "SANSDATE-1"})

    def test_le_cloture_lattribue_et_linformatif_ne_sont_pas_notifies(self):
        for ref in ("CLOS-1", "ATTRIB-1", "INFO-1"):
            self.assertNotIn(ref, self._refs_notifiees())

    def test_le_lot_hors_gabarit_nest_pas_notifie_mais_est_trace(self):
        self.assertNotIn("TROPGROS-1", self._refs_notifiees())
        l = self.cx.execute(
            "SELECT statut_elig FROM opportunites o JOIN avis a ON a.id=o.avis_id "
            "WHERE a.ref_source='TROPGROS-1'").fetchone()
        self.assertEqual(l["statut_elig"], "non éligible")

    def test_tout_est_stocke_meme_ce_qui_nest_pas_notifie(self):
        """Les attributions alimentent le calendrier : elles ne sont pas jetées."""
        self.assertEqual(self.cx.execute("SELECT count(*) c FROM avis").fetchone()["c"], 6)

    def test_la_reponse_brute_est_conservee_telle_quelle(self):
        brut = self.cx.execute(
            "SELECT r.charge FROM reponses r JOIN avis a ON a.id=r.avis_id "
            "WHERE a.ref_source='OUVERT-1'").fetchone()["charge"]
        self.assertEqual(json.loads(brut)["estimated-value"]["amount"], 610000)

    def test_la_fiche_notifiee_dit_pourquoi_il_correspond(self):
        corps = self.cx.execute(
            "SELECT corps FROM envois WHERE ref_source='OUVERT-1'").fetchone()["corps"]
        self.assertIn("POURQUOI TU CORRESPONDS", corps)
        self.assertIn("AFSCA", corps)
        self.assertIn("OÙ DÉPOSER", corps)

    def test_relancer_le_traitement_ne_renotifie_rien(self):
        traiter(self.cx, "ted", self.LOT, self.corr, PROFIL, maintenant_dt=MAINTENANT)
        n = self.cx.execute("SELECT count(*) c FROM envois").fetchone()["c"]
        self.assertEqual(n, 2)


class BaseEnLectureSeule(unittest.TestCase):

    def test_un_outil_de_lecture_est_incapable_decrire(self):
        """Promettre de ne rien écrire ne suffit pas : 298 lignes en double l'ont prouvé."""
        chemin = Path(RACINE / "tests" / "_tmp.sqlite3")
        chemin.unlink(missing_ok=True)
        ouvrir(chemin).close()
        cx = ouvrir(chemin, lecture_seule=True)
        with self.assertRaises(sqlite3.OperationalError):
            cx.execute("INSERT INTO avis(source, ref_source, premiere_vue, derniere_vue) "
                       "VALUES('x','y','z','z')")
        cx.close(); chemin.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
