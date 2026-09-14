"""LA COUCHE DE SERVICE — ce qu'un frontend reçoit, et ce qu'il ne peut pas faire.

Ces tests protègent une seule chose, et elle est architecturale :

    le moteur reste la source de vérité ; l'interface n'en devient jamais une.

Un écran qui recalculerait une couleur, un seuil ou une action referait le
radar une seconde fois, en moins testé. Les tests ci-dessous vérifient donc
que tout arrive DÉJÀ DÉCIDÉ, et qu'aucune règle métier n'a été recopiée dans
`radar/service.py`.
"""

from __future__ import annotations

import ast
import io
import json
import contextlib
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from radar import cli, service                                 # noqa: E402
from radar.base import ouvrir                                  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent
EXPORT = str(RACINE / "validation/exports-reels/2026-09-14-premier-export-reel.tsv")


class MoteurAbsent:
    nom = "moteur-sans-cle"
    disponible = False
    motif_indisponibilite = "CLÉ ABSENTE — clé API non fournie"


class MoteurPret:
    """Un moteur QUI POURRAIT chercher. Le cycle ne l'interroge pas."""
    nom = "moteur-pret"
    disponible = True
    motif_indisponibilite = None


class Socle(unittest.TestCase):
    """Un cycle réel, joué une fois, sur le jeu réel du 14/09."""

    @classmethod
    def setUpClass(cls):
        cls.chemin = tempfile.mktemp(suffix=".sqlite3")
        cls.cx = ouvrir(cls.chemin)
        adaptateur, _ = cli._source("recherche")
        with contextlib.redirect_stdout(io.StringIO()):
            cls.cycle = service.analyser(
                cls.cx, cli._moteur(cls.cx), adaptateur,
                moteurs_declares=[MoteurAbsent(), MoteurPret()],
                imports=[EXPORT])
        cls.cx.commit()

    @classmethod
    def tearDownClass(cls):
        cls.cx.close()
        pathlib.Path(cls.chemin).unlink(missing_ok=True)


# ═══════════════════════════════════════ POST /analyse
class A_LAnalyseDuJour(Socle):
    def test_1_un_cycle_rend_son_entonnoir_complet(self):
        e = self.cycle["entonnoir"]
        self.assertEqual(e["resultats_bruts"], 35)
        self.assertEqual(e["urls_uniques"], 28)
        self.assertEqual(e["doublons"], 7)
        self.assertEqual(e["opportunites"], 27)

    def test_2_les_cinq_etats_de_source_ne_sont_jamais_additionnes(self):
        s = self.cycle["sources"]
        self.assertEqual(
            set(s), {"demandees", "executees", "en_erreur",
                     "non_disponibles", "non_mesurees"})
        self.assertIn("moteur-sans-cle", s["non_disponibles"])
        self.assertIn("moteur-pret", s["non_mesurees"])
        self.assertIn("import:websearch-assistant", s["executees"])

    def test_3_une_source_indisponible_dit_pourquoi_et_ne_rend_pas_zero(self):
        """NON DISPONIBLE ≠ 0 résultat. Le confondre serait un faux résultat."""
        par_nom = {d["nom"]: d for d in self.cycle["detail_sources"]}
        absent = par_nom["moteur-sans-cle"]
        self.assertEqual(absent["etat"], "NON DISPONIBLE")
        self.assertEqual(absent["resultats"], "NON MESURÉE")
        self.assertIn("CLÉ ABSENTE", absent["motif"])
        self.assertEqual(absent["derniere_consultation"], "JAMAIS CONSULTÉE")

    def test_4_une_source_disponible_mais_non_interrogee_le_dit(self):
        par_nom = {d["nom"]: d for d in self.cycle["detail_sources"]}
        pret = par_nom["moteur-pret"]
        self.assertEqual(pret["etat"], "NON MESURÉE")
        self.assertIn("NON INTERROGÉ", pret["motif"])

    def test_5_la_source_reellement_executee_porte_ses_vrais_comptes(self):
        par_nom = {d["nom"]: d for d in self.cycle["detail_sources"]}
        imp = par_nom["import:websearch-assistant"]
        self.assertEqual(imp["etat"], "EXÉCUTÉE")
        self.assertEqual(imp["resultats"], 35)
        self.assertEqual(imp["opportunites"], 27)

    def test_6_un_cycle_partiel_le_dit(self):
        self.assertEqual(self.cycle["statut"], "PARTIEL")
        self.assertIn("NON MESURÉE n'est pas zéro", self.cycle["avertissement"])

    def test_7_le_cycle_est_serialisable_tel_quel(self):
        json.dumps(self.cycle, ensure_ascii=False)

    def test_8_GET_analyses_retrouve_le_cycle(self):
        liste = service.analyses(self.cx)
        self.assertTrue(liste)
        self.assertEqual(liste[0]["id"], self.cycle["id"])
        self.assertIn("moteur-pret", liste[0]["sources"]["non_mesurees"])


# ═══════════════════════════════════════ GET /opportunites
class B_LesOpportunites(Socle):
    def test_1_une_carte_porte_tous_les_champs_de_l_ecran(self):
        c = service.opportunites(self.cx, limite=1)[0]
        for champ in ("entreprise", "opportunite", "categorie", "nature",
                      "etat_procedure", "sources", "zone", "distance_km",
                      "montant", "duree_mois", "effort", "score",
                      "niveau_de_preuve", "action_recommandee",
                      "raison_principale", "decouverte_le", "echeance",
                      "surveillance"):
            self.assertIn(champ, c, champ)

    def test_2_la_couleur_arrive_decidee_jamais_a_recalculer(self):
        for c in service.opportunites(self.cx, limite=30):
            self.assertIn(c["categorie"]["emoji"],
                          {"🟢", "🟡", "🟣", "🔵", "⚪", "🔴"})
            self.assertTrue(c["categorie"]["code"])

    def test_3_le_score_est_rendu_avec_son_caractere_mesurable(self):
        """Un score affiché sans dire qu'il ne repose sur aucun fait
        économique se lit comme une évaluation."""
        for c in service.opportunites(self.cx, limite=30):
            self.assertIsInstance(c["score_mesurable"], bool)

    def test_4_ce_qu_on_ignore_s_ecrit_jamais_un_vide_silencieux(self):
        c = service.opportunites(self.cx, limite=1)[0]
        self.assertIn(c["effort"]["distance"], ("distance À CONFIRMER",)) \
            if c["distance_km"] is None else None
        self.assertNotEqual(c["echeance"], "")
        self.assertNotEqual(c["niveau_de_preuve"], "")

    def test_5_une_entreprise_n_est_jamais_inventee(self):
        for c in service.opportunites(self.cx, limite=30):
            ident = c["entreprise"]["identite"]
            self.assertIn("etat", ident)
            if ident["etat"] == "INCONNUE":
                self.assertIsNone(ident["raison_sociale"],
                                  "un domaine n'est pas une raison sociale")

    def test_6_les_opportunites_sont_consolidees_par_adresse(self):
        cartes = service.opportunites(self.cx, limite=100)
        urls = [c["sources"][0]["reference"] for c in cartes]
        self.assertEqual(len(urls), len(set(urls)), "une fiche par adresse")

    def test_7_chaque_carte_porte_toutes_ses_provenances(self):
        for c in service.opportunites(self.cx, limite=100):
            self.assertTrue(c["sources"])
            for s in c["sources"]:
                self.assertTrue(s["source"], "provenance conservée")

    def test_8_une_opportunite_se_lit_seule(self):
        c = service.opportunites(self.cx, limite=1)[0]
        seule = service.opportunite(self.cx, c["avis_id"])
        self.assertIsNotNone(seule)
        self.assertEqual(seule["avis_id"], c["avis_id"])
        self.assertIsNone(service.opportunite(self.cx, 999999))

    def test_9_le_filtre_par_categorie_ne_supprime_rien_ailleurs(self):
        toutes = service.opportunites(self.cx, limite=None)
        prospects = service.opportunites(self.cx, limite=None,
                                         categorie="PROSPECT")
        self.assertTrue(prospects)
        self.assertLess(len(prospects), len(toutes))
        for c in prospects:
            self.assertEqual(c["categorie"]["code"], "PROSPECT")

    def test_10_tout_est_serialisable(self):
        json.dumps(service.opportunites(self.cx, limite=100), ensure_ascii=False)


# ═══════════════════════════════════════ LA CONTRADICTION VISIBLE
class C_LesLecturesDivergentes(unittest.TestCase):
    """Deux lectures d'une même adresse : la contradiction sort de l'API."""

    def test_la_divergence_est_rendue_et_pas_masquee(self):
        import sqlite3
        from radar import consolidation

        def l(t, f, s, src):
            return {"ref_source": "https://x.be/p", "type": t, "fiabilite": f,
                    "score": s, "source_avis": src, "derniere_vue": "2026-09-14",
                    "nature": "FAIT", "action": "CONTACTER L'ENTREPRISE"}
        ad = consolidation.grouper([
            l("DIRECT", "MOYENNE", 45, "COLLECTÉ HORS RADAR"),
            l("PAS ENCORE UNE OPPORTUNITÉ", "FAIBLE", 24, "import:moteur")])[0]
        self.assertTrue(ad.divergentes)
        self.assertEqual(ad.principale["type"], "DIRECT",
                         "la lecture la mieux étayée ouvre la fiche")
        self.assertEqual(ad.autres[0]["source_avis"], "import:moteur",
                         "et l'autre garde sa provenance")


# ═══════════════════════════════════════ GET /sources · /signaux · /suivi
class D_LesAutresVues(Socle):
    def test_1_une_source_declare_son_etat_et_sa_derniere_consultation(self):
        for s in service.sources(self.cx):
            for champ in ("nom", "etat", "resultats", "opportunites",
                          "derniere_consultation", "motif"):
                self.assertIn(champ, s, champ)

    def test_2_un_import_n_est_pas_une_consultation_par_le_radar(self):
        par_nom = {s["nom"]: s for s in service.sources(self.cx)}
        imp = par_nom["import:websearch-assistant"]
        self.assertEqual(imp["execution"], "EXÉCUTÉ HORS RADAR")
        self.assertEqual(imp["resultats"], 35)

    def test_3_un_signal_dit_que_personne_n_a_rien_demande(self):
        for s in service.signaux(self.cx, limite=5):
            self.assertIn("AUCUN besoin", s["avertissement"])
            self.assertIn(s["nature"], ("SIGNAL", "HYPOTHÈSE"))

    def test_4_le_suivi_part_de_NOUVELLE_et_liste_ses_colonnes(self):
        for a in service.suivi(self.cx, limite=5):
            self.assertEqual(a["statut"], "NOUVELLE")
        self.assertEqual(
            service.statuts_possibles(),
            ["NOUVELLE", "CONTACT À FAIRE", "CONTACTÉE", "EN ATTENTE",
             "RELANCE", "GAGNÉE", "PERDUE", "ABANDONNÉE"])

    def test_5_les_six_categories_viennent_du_moteur(self):
        codes = {c["code"] for c in service.categories_possibles()}
        self.assertEqual(codes, {"DIRECT", "RENFORCEMENT", "A_CONSTRUIRE",
                                 "PROSPECT", "PAS ENCORE UNE OPPORTUNITÉ",
                                 "REJET"})

    def test_6_une_notification_dit_que_rien_n_a_ete_envoye(self):
        for n in service.notifications(self.cx, limite=3):
            self.assertFalse(n["envoyee"])
            self.assertIn("n'a contacté personne", n["avertissement"])

    def test_7_les_entreprises_sortent_avec_leur_identite(self):
        liste = service.entreprises(self.cx, limite=5)
        self.assertTrue(liste)
        for e in liste:
            self.assertIn(e["identite"]["etat"],
                          {"INCONNUE", "PROBABLE", "ÉTABLIE", "CONFIRMÉE"})

    def test_8_une_entreprise_se_lit_seule_avec_ses_pages(self):
        e = service.entreprises(self.cx, limite=1)[0]
        fiche = service.entreprise(self.cx, e["domaine"])
        self.assertIsNotNone(fiche)
        self.assertIn("pages", fiche)
        self.assertIn("opportunites", fiche)
        self.assertIsNone(service.entreprise(self.cx, "inexistant.invalid"))


# ═══════════════════════════════════════ POST /verdict · /action · /surveillance
class E_LesEcrituresHumaines(Socle):
    def test_1_un_verdict_humain_est_accepte(self):
        r = service.poser_verdict(
            self.cx, "https://colisprive.be/devenir-partenaire-livraison/",
            "VP", motif="page de partenariat réelle", juge_par="exploitant")
        self.assertEqual(r["verdict"], "VRAI POSITIF")
        self.assertEqual(r["emoji"], "🟢")

    def test_2_le_radar_ne_se_juge_jamais_lui_meme(self):
        from radar.verdicts import JugeInvalide
        with self.assertRaises(JugeInvalide):
            service.poser_verdict(self.cx, "https://x.be", "VP",
                                  juge_par="radar")

    def test_3_un_petit_echantillon_refuse_de_donner_un_taux(self):
        m = service.qualite(self.cx)
        self.assertEqual(m["precision"], "ÉCHANTILLON INSUFFISANT")
        self.assertEqual(m["rappel"], "ÉCHANTILLON INSUFFISANT")

    def test_4_une_action_commerciale_se_pose_et_se_relit(self):
        avis_id = service.opportunites(self.cx, limite=1)[0]["avis_id"]
        r = service.poser_action(self.cx, avis_id, "CONTACT À FAIRE",
                                 motif="piste à appeler")
        self.assertEqual(r["statut"], "CONTACT À FAIRE")
        relu = service.opportunite(self.cx, avis_id)
        self.assertEqual(relu["suivi"]["statut"], "CONTACT À FAIRE")

    def test_5_un_statut_hors_vocabulaire_est_refuse_jamais_devine(self):
        from radar.suivi import StatutInconnu
        avis_id = service.opportunites(self.cx, limite=1)[0]["avis_id"]
        with self.assertRaises(StatutInconnu):
            service.poser_action(self.cx, avis_id, "PRESQUE GAGNÉE")

    def test_6_la_surveillance_se_pose_et_se_retire(self):
        url = "https://exemple-surveillance.be/partenaires"
        r = service.poser_surveillance(self.cx, url, entreprise="exemple-surveillance.be",
                                       raison="demandée pour l'essai")
        self.assertEqual(r["statut"], "SURVEILLÉE")
        r = service.poser_surveillance(self.cx, url, surveiller=False,
                                       raison="finalement non")
        self.assertEqual(r["statut"], "ÉCARTÉE")

    def test_7_les_pages_a_collecter_sortent_avec_leur_raison(self):
        for p in service.a_collecter(self.cx, limite=5):
            self.assertTrue(p["url"])
            self.assertTrue(p["raison"])


# ═══════════════════════════════════════ L'INVARIANT ARCHITECTURAL
class F_LeServiceNeDecideRien(unittest.TestCase):
    """Aucune règle métier ne doit avoir été recopiée dans la couche."""

    def setUp(self):
        self.arbre = ast.parse(
            (RACINE / "radar/service.py").read_text(encoding="utf-8"))

    def test_1_aucun_score_n_est_calcule_ici(self):
        operateurs = [n for n in ast.walk(self.arbre)
                      if isinstance(n, ast.BinOp)
                      and isinstance(n.op, (ast.Mult, ast.Div, ast.Pow))]
        self.assertEqual(operateurs, [],
                         "un calcul arithmétique ici serait un second score")

    def test_2_aucune_categorie_n_est_decidee_ici(self):
        docs = {ast.get_docstring(n, clean=False) for n in ast.walk(self.arbre)
                if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))}
        litteraux = [n.value for n in ast.walk(self.arbre)
                     if isinstance(n, ast.Constant) and isinstance(n.value, str)
                     and n.value not in docs]
        for interdit in ("DIRECT", "RENFORCEMENT", "A_CONSTRUIRE", "REJET"):
            self.assertNotIn(interdit, litteraux,
                             f"« {interdit} » doit venir de classification.Type")

    def test_3_aucun_seuil_n_est_ecrit_ici(self):
        comparaisons = [n for n in ast.walk(self.arbre)
                        if isinstance(n, ast.Compare)
                        and any(isinstance(c, ast.Constant)
                                and isinstance(c.value, (int, float))
                                and c.value not in (0, 1)
                                for c in n.comparators)]
        self.assertEqual(comparaisons, [], "aucun seuil métier dans la couche")

    def test_4_le_service_delegue_aux_modules_du_moteur(self):
        modules = set()
        for n in ast.walk(self.arbre):
            if isinstance(n, ast.ImportFrom) and n.level:
                modules.update(a.name.split(".")[-1] for a in n.names)
        for attendu in ("orchestrateur", "consolidation", "classification",
                        "verdicts", "pages"):
            self.assertIn(attendu, modules, attendu)

    def test_5_le_service_n_ouvre_ni_ne_ferme_la_base(self):
        """La transaction appartient à l'appelant."""
        appels = {n.func.attr for n in ast.walk(self.arbre)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for interdit in ("commit", "rollback", "close"):
            self.assertNotIn(interdit, appels, interdit)


if __name__ == "__main__":
    unittest.main()
