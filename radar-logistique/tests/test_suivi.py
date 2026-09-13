"""LE SUIVI COMMERCIAL — tests du cycle, de l'identité et du non-écrasement.

Tous les scénarios de statut sont des TESTS SYNTHÉTIQUES : aucun contact réel
n'a été pris, aucune réponse n'a été reçue. Ils éprouvent le mécanisme, ils ne
comptent pour aucune donnée commerciale réelle.
"""

import unittest

from radar.base import ouvrir
from radar.chaine import RECALCULEES
from radar import suivi


COLONNES_DE_SUIVI = ("etat", "etat_maj", "prochaine_action_le",
                     "dernier_contact_le", "motif_commercial")


def _base_avec_opportunite(ref="https://exemple.be/partenaire", intitule="Besoin"):
    cx = ouvrir(":memory:")
    cx.execute("INSERT INTO avis(source, ref_source, empreinte, premiere_vue,"
               " derniere_vue) VALUES('entreprise', ?, 'e1', '2026-09-13', '2026-09-13')",
               (ref,))
    avis_id = cx.execute("SELECT id FROM avis WHERE ref_source=?", (ref,)).fetchone()["id"]
    cx.execute("INSERT INTO opportunites(avis_id, type, statut, intitule, action,"
               " etat_procedure, calcule_le) VALUES(?,'DIRECT','OUVERT',?,"
               "'CONTACTER L''ENTREPRISE','HORS PROCÉDURE','2026-09-13')",
               (avis_id, intitule))
    return cx, avis_id


class LeVocabulaireCommercial(unittest.TestCase):

    def test_il_accepte_les_huit_statuts_prevus(self):
        for s in suivi.Statut:
            self.assertIs(suivi.lire_statut(s.value), s)

    def test_il_tolere_la_casse_et_les_accents_du_clavier(self):
        self.assertIs(suivi.lire_statut("contactee"), suivi.Statut.CONTACTEE)
        self.assertIs(suivi.lire_statut("GAGNEE"), suivi.Statut.GAGNEE)

    def test_un_statut_hors_vocabulaire_est_refuse_pas_devine(self):
        with self.assertRaises(suivi.StatutInconnu):
            suivi.lire_statut("PEUT-ÊTRE")

    def test_le_contact_est_deduit_du_statut_jamais_stocke_deux_fois(self):
        self.assertFalse(suivi.Statut.NOUVELLE.contact_effectue)
        self.assertTrue(suivi.Statut.CONTACTEE.contact_effectue)
        self.assertTrue(suivi.Statut.RELANCE.contact_effectue)

    def test_une_date_inventee_est_refusee(self):
        with self.assertRaises(suivi.DateInvalide):
            suivi.lire_jour("dans 7 jours")
        with self.assertRaises(suivi.DateInvalide):
            suivi.lire_jour("2026-13-45")
        self.assertIsNone(suivi.lire_jour(None))
        self.assertEqual(suivi.lire_jour("2026-09-24"), "2026-09-24")


class LeCycleCommercial(unittest.TestCase):

    def test_1_une_opportunite_neuve_n_a_pas_encore_ete_regardee(self):
        cx, avis_id = _base_avec_opportunite()
        s = suivi.lire(cx, avis_id)
        self.assertTrue(s.jamais_regardee)
        self.assertIsNone(s.prochaine_action_le)
        self.assertEqual(suivi.fil(cx, avis_id), [])

    def test_3_un_changement_de_statut_ecrit_un_evenement(self):
        cx, avis_id = _base_avec_opportunite()
        s = suivi.marquer(cx, avis_id, "CONTACTÉE", dernier_contact_le="2026-09-13")
        self.assertIs(s.statut, suivi.Statut.CONTACTEE)
        self.assertTrue(s.statut_maj)
        self.assertEqual(len(suivi.historique(cx, avis_id)), 1)
        self.assertEqual(suivi.historique(cx, avis_id)[0]["ancien"], None)

    def test_le_parcours_complet_se_reconstitue(self):
        cx, avis_id = _base_avec_opportunite()
        for st in ("CONTACTÉE", "EN ATTENTE", "RELANCE", "GAGNÉE"):
            suivi.marquer(cx, avis_id, st)
        fil = suivi.fil(cx, avis_id)
        self.assertEqual(len(fil), 4)
        self.assertIn("détectée → CONTACTÉE", fil[0])
        self.assertIn("RELANCE → GAGNÉE", fil[3])

    def test_reposer_le_meme_statut_n_invente_aucun_evenement(self):
        cx, avis_id = _base_avec_opportunite()
        suivi.marquer(cx, avis_id, "CONTACTÉE")
        suivi.marquer(cx, avis_id, "CONTACTÉE")
        suivi.marquer(cx, avis_id, "CONTACTÉE")
        self.assertEqual(len(suivi.historique(cx, avis_id)), 1)

    def test_un_motif_de_perte_est_conserve(self):
        cx, avis_id = _base_avec_opportunite()
        suivi.marquer(cx, avis_id, "PERDUE", motif="flotte insuffisante")
        self.assertEqual(suivi.lire(cx, avis_id).motif, "flotte insuffisante")

    def test_sans_date_reelle_la_prochaine_action_n_est_pas_planifiee(self):
        cx, avis_id = _base_avec_opportunite()
        s = suivi.marquer(cx, avis_id, "CONTACTÉE")
        self.assertIsNone(s.prochaine_action_le)
        self.assertIn(suivi.NON_PLANIFIEE, "\n".join(s.en_lignes()))

    def test_une_opportunite_inexistante_est_refusee(self):
        cx, _ = _base_avec_opportunite()
        with self.assertRaises(suivi.OpportuniteIntrouvable):
            suivi.lire(cx, 9999)
        with self.assertRaises(suivi.OpportuniteIntrouvable):
            suivi.resoudre(cx, "jamais-vu.example")


class LeSuiviSurvitALaRecollecte(unittest.TestCase):

    def test_4_aucune_colonne_de_suivi_n_est_recalculee(self):
        """La garantie de non-écrasement, vérifiée et non supposée.

        Si quelqu'un ajoute un jour une de ces colonnes à RECALCULEES, une
        recollecte effacerait le travail du commercial. Ce test le refuse.
        """
        for colonne in COLONNES_DE_SUIVI:
            self.assertNotIn(colonne, RECALCULEES,
                             f"« {colonne} » serait écrasée à chaque recollecte")

    def test_le_statut_pose_reste_apres_une_reecriture_de_l_opportunite(self):
        cx, avis_id = _base_avec_opportunite()
        suivi.marquer(cx, avis_id, "CONTACTÉE", prochaine_action_le="2026-09-24")
        # Ce que fait une recollecte : réécrire les colonnes recalculées.
        maj = ", ".join(f"{c}=?" for c in ("type", "action", "calcule_le"))
        cx.execute(f"UPDATE opportunites SET {maj} WHERE avis_id=?",
                   ("PROSPECT", "SURVEILLER", "2026-09-20", avis_id))
        s = suivi.lire(cx, avis_id)
        self.assertIs(s.statut, suivi.Statut.CONTACTEE)
        self.assertEqual(s.prochaine_action_le, "2026-09-24")


class LesTroisDimensionsRestentSeparees(unittest.TestCase):

    def test_le_statut_commercial_ne_touche_ni_l_etat_ni_le_score(self):
        cx, avis_id = _base_avec_opportunite()
        cx.execute("UPDATE opportunites SET score=55, nature='FAIT' WHERE avis_id=?",
                   (avis_id,))
        avant = cx.execute("SELECT etat_procedure, action, score, nature FROM"
                           " opportunites WHERE avis_id=?", (avis_id,)).fetchone()
        suivi.marquer(cx, avis_id, "GAGNÉE")
        apres = cx.execute("SELECT etat_procedure, action, score, nature FROM"
                           " opportunites WHERE avis_id=?", (avis_id,)).fetchone()
        self.assertEqual(tuple(avant), tuple(apres))

    def test_un_besoin_prive_hors_procedure_est_suivable(self):
        """Colis Privé : HORS PROCÉDURE, action CONTACTER, statut NOUVELLE.
        Les trois sont vrais en même temps."""
        cx, avis_id = _base_avec_opportunite()
        ligne = cx.execute("SELECT etat_procedure, action FROM opportunites"
                           " WHERE avis_id=?", (avis_id,)).fetchone()
        self.assertEqual(ligne["etat_procedure"], "HORS PROCÉDURE")
        self.assertEqual(ligne["action"], "CONTACTER L'ENTREPRISE")
        s = suivi.marquer(cx, avis_id, "CONTACT À FAIRE")
        self.assertIs(s.statut, suivi.Statut.CONTACT_A_FAIRE)


class L_identiteCommerciale(unittest.TestCase):

    def test_6_deux_besoins_de_la_meme_entreprise_restent_distincts(self):
        cx, premier = _base_avec_opportunite(
            "https://colisprive.be/devenir-partenaire-livraison/", "Partenaire livraison")
        cx.execute("INSERT INTO avis(source, ref_source, empreinte, premiere_vue,"
                   " derniere_vue) VALUES('entreprise',"
                   " 'https://colisprive.be/devenir-relais/', 'e2', '2026-09-13', '2026-09-13')")
        second = cx.execute("SELECT id FROM avis WHERE ref_source LIKE '%relais%'"
                            ).fetchone()["id"]
        cx.execute("INSERT INTO opportunites(avis_id, type, statut, intitule, action,"
                   " calcule_le) VALUES(?,'DIRECT','OUVERT','Devenir relais','CONTACTER',"
                   "'2026-09-13')", (second,))
        suivi.marquer(cx, premier, "CONTACTÉE")
        self.assertIs(suivi.lire(cx, premier).statut, suivi.Statut.CONTACTEE)
        self.assertTrue(suivi.lire(cx, second).jamais_regardee)

    def test_une_reference_ambigue_est_refusee_pas_tranchee(self):
        cx, _ = _base_avec_opportunite("https://x.be/a", "A")
        cx.execute("INSERT INTO avis(source, ref_source, empreinte, premiere_vue,"
                   " derniere_vue) VALUES('entreprise','https://x.be/b','e2',"
                   "'2026-09-13','2026-09-13')")
        i = cx.execute("SELECT id FROM avis WHERE ref_source='https://x.be/b'").fetchone()["id"]
        cx.execute("INSERT INTO opportunites(avis_id, type, statut, intitule, calcule_le)"
                   " VALUES(?,'DIRECT','OUVERT','B','2026-09-13')", (i,))
        with self.assertRaises(suivi.OpportuniteIntrouvable):
            suivi.resoudre(cx, "https://x.be/")


if __name__ == "__main__":
    unittest.main()
