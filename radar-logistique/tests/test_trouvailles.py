"""8a — LE JOURNAL DES TROUVAILLES.

    URL DÉCOUVERTE ≠ PAGE COLLECTÉE ≠ CONTENU ANALYSÉ ≠ OPPORTUNITÉ

Tous les scénarios sont SYNTHÉTIQUES. Aucun moteur de recherche n'a été
interrogé, aucun réseau n'a été touché : les résultats sont fabriqués en
mémoire pour éprouver le mécanisme. Ils ne mesurent AUCUN marché.
"""

import pathlib
import unittest

from radar.base import ouvrir
from radar.mode import Mode
from radar.moteurs_recherche import Resultat
from radar.pages import Acces
from radar import circuit, trouvailles as tr


def resultat(url, source="fixture", requete="une requête", rang=None,
             titre="Un titre", extrait="Un extrait"):
    return Resultat(titre=titre, url=url, extrait=extrait, requete=requete,
                    fournisseur=source, rang=rang)


class UneUrlTrouveeNEstPasUnePageLue(unittest.TestCase):
    """La frontière que 8a existe pour tenir."""

    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_1_une_trouvaille_nait_NON_COLLECTEE(self):
        t = tr.inscrire(self.cx, resultat("https://exemple.be/a"), mode=Mode.DEMO)
        self.assertIs(t.collecte, Acces.JAMAIS_CONSULTEE)
        self.assertFalse(t.lue)
        self.assertIsNone(t.collecte_le)

    def test_2_aucun_appelant_ne_peut_la_declarer_lue_a_l_inscription(self):
        """Même si le résultat prétend le contraire, l'inscription pose
        JAMAIS CONSULTÉE. Seule une collecte réelle change cet état."""
        r = resultat("https://exemple.be/a")
        r.consulte_le = "2026-09-13T10:00:00+00:00"   # le MOTEUR l'a vue, pas nous
        t = tr.inscrire(self.cx, r, mode=Mode.DEMO)
        self.assertIs(t.collecte, Acces.JAMAIS_CONSULTEE)

    def test_3_une_collecte_reussie_change_l_etat(self):
        tr.inscrire(self.cx, resultat("https://exemple.be/a"), mode=Mode.DEMO)
        tr.collectee(self.cx, "https://exemple.be/a", Acces.CONSULTEE,
                     motif="1200 octets reçus")
        t = tr.lire(self.cx, "https://exemple.be/a")
        self.assertIs(t.collecte, Acces.CONSULTEE)
        self.assertTrue(t.lue)
        self.assertTrue(t.collecte_le)

    def test_4_une_erreur_ne_dit_rien_du_contenu(self):
        tr.inscrire(self.cx, resultat("https://exemple.be/a"), mode=Mode.DEMO)
        tr.collectee(self.cx, "https://exemple.be/a", Acces.ERREUR,
                     motif="accès impossible")
        t = tr.lire(self.cx, "https://exemple.be/a")
        self.assertIs(t.collecte, Acces.ERREUR)
        self.assertFalse(t.lue)
        # Le rapport n'a PAS le droit de conclure « rien trouvé » sur une
        # erreur d'accès. Il a en revanche le droit — et le devoir — de dire
        # qu'une URL non lue ne prouve aucune opportunité.
        texte = tr.rapport(self.cx).lower()
        for interdit in ("aucune opportunité trouvée", "pas d'opportunité",
                         "page inexistante", "rien trouvé"):
            self.assertNotIn(interdit, texte, interdit)
        self.assertIn("erreur", t.collecte.value.lower())

    def test_5_le_rapport_dit_combien_n_ont_jamais_ete_lues(self):
        for i in range(3):
            tr.inscrire(self.cx, resultat(f"https://exemple.be/{i}"), mode=Mode.DEMO)
        texte = tr.rapport(self.cx)
        self.assertIn("3 URL sur 3 n'ont JAMAIS été collectées", texte)
        self.assertIn("INCONNU", texte)


class FixtureEtReelNeSeComptentJamaisEnsemble(unittest.TestCase):
    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_1_sans_moteur_reel_la_decouverte_est_NON_MESUREE(self):
        tr.inscrire(self.cx, resultat("https://exemple.be/a"), mode=Mode.DEMO)
        texte = tr.rapport(self.cx)
        self.assertIn("DÉCOUVERTE RÉELLE", texte)
        self.assertIn("NON MESURÉE", texte)
        self.assertIn("Ce n'est pas zéro", texte)

    def test_2_une_fixture_ne_se_presente_jamais_comme_une_mesure(self):
        tr.inscrire(self.cx, resultat("https://exemple.be/a"), mode=Mode.DEMO)
        texte = tr.rapport(self.cx)
        self.assertIn("FIXTURE", texte)
        self.assertIn("ne mesure AUCUN marché", texte)

    def test_3_les_metriques_separent_les_deux_modes(self):
        tr.inscrire(self.cx, resultat("https://exemple.be/a", source="fixture"),
                    mode=Mode.DEMO)
        tr.inscrire(self.cx, resultat("https://exemple.be/b", source="moteur"),
                    mode=Mode.REEL)
        m = tr.metriques(self.cx)
        self.assertEqual(m[Mode.DEMO.value]["trouvailles"], 1)
        self.assertEqual(m[Mode.REEL.value]["trouvailles"], 1)
        self.assertEqual(len(tr.toutes(self.cx, mode=Mode.DEMO)), 1)
        self.assertEqual(len(tr.toutes(self.cx, mode=Mode.REEL)), 1)

    def test_4_un_mode_illisible_retombe_sur_DEMO_jamais_sur_REEL(self):
        self.cx.execute(
            "INSERT INTO trouvailles(url, source, mode, collecte, decouverte_le)"
            " VALUES('https://x.be/a','s','n_importe_quoi','JAMAIS CONSULTÉE','2026')")
        t = tr.lire(self.cx, "https://x.be/a")
        self.assertIs(t.mode, Mode.DEMO, "on ne promeut jamais une fixture en réel")

    def test_5_le_rapport_reel_apparait_des_qu_un_moteur_reel_a_tourne(self):
        tr.inscrire(self.cx, resultat("https://exemple.be/a", source="moteur"),
                    mode=Mode.REEL)
        texte = tr.rapport(self.cx)
        self.assertNotIn("NON MESURÉE", texte)
        self.assertIn("URL uniques", texte)


class LaProvenanceEstConservee(unittest.TestCase):
    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_1_les_huit_champs_demandes_sont_conserves(self):
        r = resultat("https://exemple.be/partenaires", source="fixture",
                     requete='"recherche transporteur" Bruxelles', rang=3)
        t = tr.inscrire(self.cx, r, mode=Mode.DEMO,
                        page_source="https://exemple.be/accueil")
        self.assertEqual(t.requete, '"recherche transporteur" Bruxelles')
        self.assertEqual(t.source, "fixture")
        self.assertEqual(t.url, "https://exemple.be/partenaires")
        self.assertEqual(t.rang, 3)
        self.assertTrue(t.decouverte_le)
        self.assertEqual(t.page_source, "https://exemple.be/accueil")
        self.assertEqual(t.circuit, circuit.DECOUVERTE)
        self.assertIs(t.collecte, Acces.JAMAIS_CONSULTEE)

    def test_2_le_titre_et_l_extrait_sont_conserves_mot_pour_mot(self):
        r = resultat("https://exemple.be/a", titre="Devenir  partenaire — 2026",
                     extrait="Nous  recherchons   des transporteurs.")
        t = tr.inscrire(self.cx, r, mode=Mode.DEMO)
        self.assertEqual(t.titre, "Devenir  partenaire — 2026")
        self.assertEqual(t.extrait, "Nous  recherchons   des transporteurs.")

    def test_3_le_rang_est_pose_dans_l_ordre_rendu_s_il_manque(self):
        lot = [resultat(f"https://exemple.be/{i}") for i in range(3)]
        inscrits = tr.inscrire_lot(self.cx, lot, mode=Mode.DEMO)
        self.assertEqual([t.rang for t in inscrits], [1, 2, 3])

    def test_4_un_rang_deja_fourni_par_le_moteur_est_respecte(self):
        lot = [resultat("https://exemple.be/a", rang=7)]
        self.assertEqual(tr.inscrire_lot(self.cx, lot, mode=Mode.DEMO)[0].rang, 7)

    def test_5_une_url_sans_adresse_est_refusee(self):
        with self.assertRaises(ValueError):
            tr.inscrire(self.cx, resultat(""), mode=Mode.DEMO)

    def test_6_le_circuit_par_defaut_est_la_decouverte(self):
        t = tr.inscrire(self.cx, resultat("https://exemple.be/a"), mode=Mode.DEMO)
        self.assertEqual(t.circuit, circuit.DECOUVERTE)

    def test_7_un_lien_lu_sur_une_page_connue_porte_le_circuit_connu(self):
        t = tr.inscrire(self.cx, resultat("https://exemple.be/a", source="page"),
                        mode=Mode.DEMO, circuit=circuit.CONNUE,
                        page_source="https://exemple.be/accueil")
        self.assertEqual(t.circuit, circuit.CONNUE)
        self.assertEqual(t.page_source, "https://exemple.be/accueil")


class DeuxMoteursDeuxObservationsUneAdresse(unittest.TestCase):
    def setUp(self):
        self.cx = ouvrir(":memory:")
        for source in ("moteur_a", "moteur_b"):
            tr.inscrire(self.cx, resultat("https://exemple.be/besoin", source=source),
                        mode=Mode.DEMO)

    def test_1_deux_moteurs_font_deux_trouvailles(self):
        self.assertEqual(len(tr.toutes(self.cx)), 2)

    def test_2_mais_une_seule_adresse_unique(self):
        self.assertEqual(tr.urls_uniques(self.cx), ["https://exemple.be/besoin"])

    def test_3_le_recouvrement_dit_ce_que_chaque_source_apporte_seule(self):
        tr.inscrire(self.cx, resultat("https://autre.be/x", source="moteur_a"),
                    mode=Mode.DEMO)
        rec = tr.recouvrement(self.cx)
        self.assertEqual(rec["moteur_a"], {"trouvees": 2, "uniques": 1, "partagees": 1})
        self.assertEqual(rec["moteur_b"], {"trouvees": 1, "uniques": 0, "partagees": 1})

    def test_4_une_collecte_met_a_jour_toutes_les_trouvailles_de_l_adresse(self):
        tr.collectee(self.cx, "https://exemple.be/besoin", Acces.CONSULTEE)
        for t in tr.toutes(self.cx):
            self.assertIs(t.collecte, Acces.CONSULTEE)

    def test_5_la_meme_source_et_la_meme_requete_ne_dupliquent_pas(self):
        tr.inscrire(self.cx, resultat("https://exemple.be/besoin", source="moteur_a"),
                    mode=Mode.DEMO)
        self.assertEqual(len(tr.toutes(self.cx)), 2, "toujours deux observations")

    def test_6_les_urls_equivalentes_sont_normalisees(self):
        tr.inscrire(self.cx, resultat("https://EXEMPLE.be/besoin#bas",
                                      source="moteur_c"), mode=Mode.DEMO)
        self.assertEqual(len(tr.urls_uniques(self.cx)), 1)


class LeRangEtLaSourceNeNotentRien(unittest.TestCase):
    """La garde anti-biais de 8a."""

    def test_1_le_module_ne_calcule_aucun_score(self):
        import ast
        arbre = ast.parse(pathlib.Path("radar/trouvailles.py")
                          .read_text(encoding="utf-8"))
        noms = {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)}
        noms |= {n.attr for n in ast.walk(arbre) if isinstance(n, ast.Attribute)}
        for interdit in ("score", "Classement", "Opportunite", "classification",
                         "ponderation", "bareme"):
            self.assertNotIn(interdit, noms, interdit)

    def test_2_aucune_source_n_est_nommee_dans_le_code(self):
        import ast
        arbre = ast.parse(pathlib.Path("radar/trouvailles.py")
                          .read_text(encoding="utf-8"))
        docs = set()
        for n in ast.walk(arbre):
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                d = ast.get_docstring(n, clean=False)
                if d:
                    docs.add(d)
        litterales = [n.value.lower() for n in ast.walk(arbre)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str)
                      and n.value not in docs]
        for nom in ("google", "brave", "bing", "exa", "tavily", "serpapi"):
            for t in litterales:
                self.assertNotIn(nom, t, nom)

    def test_3_le_score_d_une_opportunite_ignore_le_rang(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        a, b = opp(ref_source="R1"), opp(ref_source="R2")
        a.provenances = [{"source": "moteur_a", "circuit": circuit.DECOUVERTE}]
        b.provenances = [{"source": "moteur_b", "circuit": circuit.DECOUVERTE}]
        self.assertEqual(moteur().analyser(a, MAINTENANT).score.total,
                         moteur().analyser(b, MAINTENANT).score.total)

    def test_4_aucune_opportunite_n_est_creee_par_une_trouvaille(self):
        cx = ouvrir(":memory:")
        tr.inscrire_lot(cx, [resultat(f"https://exemple.be/{i}") for i in range(5)],
                        mode=Mode.DEMO)
        self.assertEqual(
            cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"], 0)
        self.assertEqual(
            cx.execute("SELECT count(*) c FROM entreprises").fetchone()["c"], 0)
        self.assertEqual(
            cx.execute("SELECT count(*) c FROM pages_surveillees").fetchone()["c"], 0)

    def test_5_le_module_ne_touche_a_aucun_reseau(self):
        source = pathlib.Path("radar/trouvailles.py").read_text(encoding="utf-8")
        for interdit in ("urllib", "requests", "socket", "urlopen",
                         "collecte_directe", "moteurs_recherche"):
            self.assertNotIn(interdit, source, interdit)
