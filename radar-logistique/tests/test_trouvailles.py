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
        self.assertIn("TROUVAILLES EN MODE RÉEL", texte)
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


# ══════════════════════════ 8b — LE MOTEUR DE FIXTURE
#
# Rappel : TOUT ce qui suit est fabriqué. Aucun moteur de recherche n'a été
# interrogé, aucune de ces adresses n'existe, aucun marché n'est mesuré.

FIXTURE = "fixtures/recherche-exemple.yaml"


class UneFixtureRespecteLeContratDUnMoteur(unittest.TestCase):
    def setUp(self):
        from radar import fixtures_recherche as fx
        self.fx = fx
        self.moteurs = fx.depuis_fichier(FIXTURE)

    def test_1_elle_implemente_exactement_l_interface(self):
        from radar.moteurs_recherche import MoteurRecherche
        for m in self.moteurs:
            self.assertIsInstance(m, MoteurRecherche)
            self.assertTrue(m.disponible)
            self.assertIsNone(m.motif_indisponibilite)
            self.assertTrue(callable(m.rechercher))
            self.assertTrue(m.nom)

    def test_2_elle_rend_des_Resultat_conformes(self):
        from radar.moteurs_recherche import Resultat
        for r in self.moteurs[0].rechercher('"recherche transporteur" Bruxelles'):
            self.assertIsInstance(r, Resultat)
            self.assertTrue(r.url)
            self.assertEqual(r.fournisseur, self.moteurs[0].nom)
            self.assertIsNotNone(r.rang)

    def test_3_elle_entre_dans_un_Registre_comme_un_moteur_normal(self):
        reg = self.fx.registre(FIXTURE)
        self.assertIsNotNone(reg.disponible())
        self.assertEqual(len(reg.moteurs), 2)
        self.assertIn("FIXTURE", reg.rapport())

    def test_4_plusieurs_moteurs_de_fixture_pour_eprouver_le_multi_sources(self):
        self.assertGreaterEqual(len(self.moteurs), 2)
        self.assertNotEqual(self.moteurs[0].nom, self.moteurs[1].nom)


class UneFixtureNePeutPasSeFairePasserPourReelle(unittest.TestCase):
    """LE VERROU CENTRAL DE 8b."""

    def setUp(self):
        from radar import fixtures_recherche as fx
        self.fx = fx
        self.moteurs = fx.depuis_fichier(FIXTURE)
        self.cx = ouvrir(":memory:")

    def test_1_son_mode_est_DEMO_et_n_est_pas_un_parametre(self):
        for m in self.moteurs:
            self.assertIs(m.mode, Mode.DEMO)

    def test_2_un_moteur_reel_declare_RÉEL(self):
        from radar.moteurs_recherche import depuis_environnement
        for m in depuis_environnement({}).moteurs:
            self.assertIs(m.mode, Mode.REEL)

    def test_3_elle_REFUSE_de_tourner_en_mode_reel(self):
        with self.assertRaises(self.fx.FixtureEnModeReel):
            self.moteurs[0].rechercher("une requête", mode=Mode.REEL)

    def test_4_le_mode_FIXTURE_traverse_jusqu_a_la_persistance(self):
        r = self.moteurs[0].rechercher('"recherche transporteur" Bruxelles')
        tr.depuis_moteur(self.cx, self.moteurs[0], r)
        for t in tr.toutes(self.cx):
            self.assertIs(t.mode, Mode.DEMO)
            self.assertFalse(t.reelle)

    def test_5_elle_n_est_jamais_comptee_dans_les_metriques_reelles(self):
        r = self.moteurs[0].rechercher('"recherche transporteur" Bruxelles')
        tr.depuis_moteur(self.cx, self.moteurs[0], r)
        m = tr.metriques(self.cx)
        self.assertEqual(m[Mode.REEL.value]["trouvailles"], 0)
        self.assertGreater(m[Mode.DEMO.value]["trouvailles"], 0)
        texte = tr.rapport(self.cx)
        self.assertIn("TROUVAILLES EN MODE RÉEL", texte)
        self.assertIn("NON MESURÉE", texte)

    def test_6_elle_ne_cree_aucune_fausse_consultation(self):
        r = self.moteurs[0].rechercher('"recherche transporteur" Bruxelles')
        tr.depuis_moteur(self.cx, self.moteurs[0], r)
        for t in tr.toutes(self.cx):
            self.assertIs(t.collecte, Acces.JAMAIS_CONSULTEE)
            self.assertFalse(t.lue)
            self.assertIsNone(t.collecte_le)

    def test_7_un_fichier_non_marque_n_est_pas_charge(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        chemin = os.path.join(d, "faux.yaml")
        with open(chemin, "w", encoding="utf-8") as f:
            f.write("moteurs:\n  - nom: x\n    resultats: []\n")
        with self.assertRaises(self.fx.FixtureInvalide):
            self.fx.depuis_fichier(chemin)
        import shutil; shutil.rmtree(d)

    def test_8_le_fichier_de_fixture_se_declare_comme_tel(self):
        import yaml
        d = yaml.safe_load(pathlib.Path(FIXTURE).read_text(encoding="utf-8"))
        self.assertEqual(d["mode"], "FIXTURE")
        entete = pathlib.Path(FIXTURE).read_text(encoding="utf-8")[:1200]
        self.assertIn("N'ONT JAMAIS ÉTÉ RENDUS PAR UN MOTEUR", entete)
        self.assertIn("ne mesure AUCUN marché", entete)


class AucunResultatNEstRejeteALaDecouverte(unittest.TestCase):
    """« Une absence de mot-clé n'est jamais une preuve d'absence. »"""

    def setUp(self):
        from radar import fixtures_recherche as fx
        self.moteurs = fx.depuis_fichier(FIXTURE)
        self.cx = ouvrir(":memory:")
        for m in self.moteurs:
            for q in ('"recherche transporteur" Bruxelles',
                      '"recherche sous-traitant" Belgique',
                      '"nouveau dépôt" Gand',
                      '"référencement fournisseur" transport',
                      '"capacité recherchée" transport',
                      '"partenariat logistique" Belgique'):
                tr.depuis_moteur(self.cx, m, m.rechercher(q))

    def test_1_un_titre_vide_reste_une_decouverte(self):
        t = tr.lire(self.cx, "https://sans-titre-fictif.example/page")
        self.assertIsNotNone(t, "une découverte sans titre reste une découverte")
        self.assertEqual(t.titre, "")

    def test_2_un_titre_vague_reste_une_decouverte(self):
        t = tr.lire(self.cx, "https://entreprise-fictive.example/nous-rejoindre")
        self.assertIsNotNone(t)
        self.assertEqual(t.titre, "Nous rejoindre")

    def test_3_un_resultat_non_pertinent_reste_une_decouverte(self):
        t = tr.lire(self.cx, "https://boulangerie-fictive.example/nos-pains")
        self.assertIsNotNone(t, "le tri vient APRÈS, jamais à la découverte")

    def test_4_un_signal_indirect_reste_une_decouverte_pas_un_contrat(self):
        t = tr.lire(self.cx, "https://presse-fictive.example/ouverture-depot-gand")
        self.assertIsNotNone(t)
        self.assertIs(t.collecte, Acces.JAMAIS_CONSULTEE)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"], 0)

    def test_5_les_dix_resultats_declares_sont_tous_inscrits(self):
        self.assertEqual(len(tr.toutes(self.cx)), 10)

    def test_6_une_meme_url_vue_par_deux_moteurs_fait_deux_observations(self):
        url = "https://logistique-fictive.example/sous-traitance"
        vues = [t for t in tr.toutes(self.cx) if t.url == url]
        self.assertEqual(len(vues), 2)
        self.assertEqual({t.source for t in vues}, {"fixture_alpha", "fixture_beta"})
        self.assertEqual(len([u for u in tr.urls_uniques(self.cx) if u == url]), 1)

    def test_7_le_recouvrement_distingue_l_apport_de_chaque_fixture(self):
        rec = tr.recouvrement(self.cx)
        self.assertEqual(rec["fixture_alpha"]["partagees"], 1)
        self.assertEqual(rec["fixture_beta"]["partagees"], 1)
        self.assertGreater(rec["fixture_alpha"]["uniques"], 0)
        self.assertGreater(rec["fixture_beta"]["uniques"], 0)

    def test_8_une_page_injoignable_est_une_erreur_d_acces_pas_un_vide(self):
        url = "https://injoignable-fictif.example/partenaires"
        tr.collectee(self.cx, url, Acces.ERREUR, motif="accès impossible")
        t = tr.lire(self.cx, url)
        self.assertIs(t.collecte, Acces.ERREUR)
        self.assertFalse(t.lue)

    def test_9_une_decouverte_jamais_collectee_le_reste(self):
        t = tr.lire(self.cx, "https://jamais-lue-fictive.example/offre")
        self.assertIs(t.collecte, Acces.JAMAIS_CONSULTEE)

    def test_10_le_rang_reste_informatif_et_la_provenance_intacte(self):
        for t in tr.toutes(self.cx):
            self.assertIsNotNone(t.rang)
            self.assertGreaterEqual(t.rang, 1)
            self.assertIn(t.source, {"fixture_alpha", "fixture_beta"})
            self.assertTrue(t.requete)

    def test_11_une_requete_sans_resultat_declare_ne_rejette_rien(self):
        vide = self.moteurs[0].rechercher("une requête que personne n'a déclarée")
        self.assertEqual(vide, [], "liste vide : absence de résultat, pas rejet")


class LaFixtureNeTouchePasAuScore(unittest.TestCase):
    def test_1_le_module_ignore_le_scoring(self):
        import ast
        arbre = ast.parse(pathlib.Path("radar/fixtures_recherche.py")
                          .read_text(encoding="utf-8"))
        noms = {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)}
        noms |= {n.attr for n in ast.walk(arbre) if isinstance(n, ast.Attribute)}
        for interdit in ("score", "Classement", "Opportunite", "classification",
                         "bareme", "ponderation"):
            self.assertNotIn(interdit, noms, interdit)

    def test_2_aucun_nom_de_fournisseur_reel_dans_le_code(self):
        """On inspecte le CODE — littéraux et identifiants — pas la prose, qui
        a le droit de dire « ce module ne connaît ni l'un ni l'autre »."""
        import ast
        arbre = ast.parse(pathlib.Path("radar/fixtures_recherche.py")
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
        noms_code = {n.id.lower() for n in ast.walk(arbre) if isinstance(n, ast.Name)}
        for nom in ("google", "brave", "bing", "exa", "tavily", "serpapi",
                    "duckduckgo", "mojeek"):
            for t in litterales:
                self.assertNotIn(nom, t, f"littéral « {nom} »")
            self.assertNotIn(nom, noms_code, f"identifiant « {nom} »")

    def test_3_aucun_acces_reseau(self):
        source = pathlib.Path("radar/fixtures_recherche.py").read_text(encoding="utf-8")
        for interdit in ("urllib", "requests", "socket", "urlopen", "http"):
            self.assertNotIn(interdit, source, interdit)

    def test_4_une_fixture_ne_change_aucun_score(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        a, b = opp(ref_source="F1"), opp(ref_source="F2")
        a.provenances = [{"source": "fixture_alpha", "circuit": circuit.DECOUVERTE}]
        b.provenances = [{"source": "ted", "circuit": circuit.CONNUE}]
        self.assertEqual(moteur().analyser(a, MAINTENANT).score.total,
                         moteur().analyser(b, MAINTENANT).score.total)


# ══════════════════════════ 8c — LE CHAÎNAGE
#
# Rappel : tout ce qui suit part de FIXTURES. Aucun moteur interrogé, aucune
# page consultée, aucun marché mesuré.

class S8c_UneTrouvailleNeConfirmeRien(unittest.TestCase):
    def setUp(self):
        from radar import chainage, entreprises as ent_mod, fixtures_recherche as fx
        from radar import identite as mod_id
        self.chainage, self.ent, self.id = chainage, ent_mod, mod_id
        self.cx = ouvrir(":memory:")
        self.moteurs = fx.depuis_fichier(FIXTURE)
        for m in self.moteurs:
            for q in ('"recherche transporteur" Bruxelles',
                      '"recherche sous-traitant" Belgique', '"nouveau dépôt" Gand',
                      '"référencement fournisseur" transport',
                      '"capacité recherchée" transport',
                      '"partenariat logistique" Belgique'):
                tr.depuis_moteur(self.cx, m, m.rechercher(q))
        self.registre = self.ent.charger(self.cx)
        self.bilan = self.chainage.chainer(self.cx, tr.toutes(self.cx), self.registre)
        self.ent.enregistrer(self.cx, self.registre)
        self.chainage.marquer_identites(self.cx, self.registre)
        self.cx.commit()

    # ── trouvaille → entreprise INCONNUE, jamais confirmée ──
    def test_1_toutes_les_entreprises_creees_sont_INCONNUES(self):
        entreprises = self.ent.charger(self.cx).entreprises
        self.assertGreater(len(entreprises), 0)
        for cle in entreprises:
            self.assertIs(self.id.lire(self.cx, cle).etat, self.id.Etat.INCONNUE, cle)

    def test_2_la_provenance_de_la_decouverte_est_conservee(self):
        for cle, e in self.ent.charger(self.cx).entreprises.items():
            i = self.id.lire(self.cx, cle)
            self.assertEqual(i.source, self.id.DECOUVERTE)
            self.assertIn("aucune identification", i.preuve)
            self.assertTrue(e.origine.endswith("/découverte"), e.origine)

    def test_3_une_identite_confirmee_n_est_jamais_degradee_par_une_decouverte(self):
        cle = next(iter(self.ent.charger(self.cx).entreprises))
        self.id.confirmer(self.cx, cle, source=self.id.EXPLOITANT,
                          preuve="FIXTURE de test")
        self.id.depuis_decouverte(self.cx, cle, "https://x.example/y")
        self.assertIs(self.id.lire(self.cx, cle).etat, self.id.Etat.CONFIRMEE)

    def test_4_seule_une_preuve_confirme_une_identite(self):
        cle = next(iter(self.ent.charger(self.cx).entreprises))
        with self.assertRaises(self.id.IdentiteIncertaine):
            self.id.confirmer(self.cx, cle, source="", preuve="")
        i = self.id.confirmer(self.cx, cle, source=self.id.EXPLOITANT,
                              preuve="domaine relevé sur l'extrait Kbis — FIXTURE")
        self.assertIs(i.etat, self.id.Etat.CONFIRMEE)

    # ── aucune opportunité, aucun score ──
    def test_5_aucune_opportunite_n_est_creee(self):
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"], 0)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM avis").fetchone()["c"], 0)

    def test_6_aucune_metrique_reelle_n_est_creee_par_les_fixtures(self):
        m = tr.metriques(self.cx)
        self.assertEqual(m[Mode.REEL.value]["trouvailles"], 0)
        self.assertIn("NON MESURÉE", tr.rapport(self.cx))

    def test_7_le_bilan_dit_ce_qu_il_n_a_PAS_fait(self):
        texte = self.bilan.resume()
        self.assertIn("Aucune opportunité n'a été créée", texte)
        self.assertIn("Aucune identité n'a été", texte)
        self.assertIn("Aucune page n'est surveillée d'office", texte)


class S8c_UneUrlDecouverteNEstPasUnePageSurveillee(unittest.TestCase):
    def setUp(self):
        from radar import chainage, entreprises as ent_mod, fixtures_recherche as fx
        from radar import pages as mod_pages
        self.chainage, self.ent, self.pages = chainage, ent_mod, mod_pages
        self.cx = ouvrir(":memory:")
        m = fx.depuis_fichier(FIXTURE)[0]
        tr.depuis_moteur(self.cx, m,
                         m.rechercher('"recherche transporteur" Bruxelles'))
        reg = self.ent.charger(self.cx)
        self.chainage.chainer(self.cx, tr.toutes(self.cx), reg)
        self.ent.enregistrer(self.cx, reg)

    def test_1_toutes_les_pages_sont_CANDIDATES(self):
        toutes = self.pages.a_surveiller(self.cx, toutes=True)
        self.assertGreater(len(toutes), 0)
        for p in toutes:
            self.assertIs(p.statut, self.pages.Statut.CANDIDATE)
        self.assertEqual(self.pages.a_surveiller(self.cx), [],
                         "aucune n'est surveillée d'office")

    def test_2_aucune_n_est_collectee_ni_qualifiee(self):
        for p in self.pages.a_surveiller(self.cx, toutes=True):
            self.assertIs(p.acces, self.pages.Acces.JAMAIS_CONSULTEE)
            self.assertIs(p.qualification, self.pages.Qualification.NON_QUALIFIEE)

    def test_3_la_qualification_de_7b_reste_la_seule_porte(self):
        """CANDIDATE → SURVEILLÉE exige une PREUVE DE CONTENU, donc une collecte."""
        from radar import pertinence
        onto, det = _mecanismes_8c()
        url = "https://transports-fictifs.example/devenir-partenaire"
        verdict = pertinence.evaluer(
            "Nous recherchons des transporteurs partenaires pour assurer nos "
            "tournees quotidiennes en Belgique.", onto, det)
        p = self.pages.qualifier(self.cx, url, verdict)
        self.assertIs(p.qualification, self.pages.Qualification.PREUVE)
        self.assertIs(p.statut, self.pages.Statut.SURVEILLEE)
        self.assertIn("PROMUE APRÈS COLLECTE", p.raison)

    def test_4_une_url_jamais_collectee_reste_candidate(self):
        url = "https://boulangerie-fictive.example/nos-pains"
        p = self.pages.lire(self.cx, url)
        self.assertIs(p.statut, self.pages.Statut.CANDIDATE)
        self.assertIs(p.acces, self.pages.Acces.JAMAIS_CONSULTEE)

    def test_5_une_collecte_qui_echoue_laisse_la_page_candidate(self):
        url = "https://transports-fictifs.example/devenir-partenaire"
        self.pages.marquer(self.cx, url, self.pages.Acces.ERREUR,
                           motif="accès impossible")
        tr.collectee(self.cx, url, self.pages.Acces.ERREUR, motif="accès impossible")
        p = self.pages.lire(self.cx, url)
        self.assertIs(p.statut, self.pages.Statut.CANDIDATE)
        self.assertIs(p.acces, self.pages.Acces.ERREUR)
        self.assertIs(p.qualification, self.pages.Qualification.NON_QUALIFIEE)

    def test_6_une_collecte_reussie_ouvre_la_qualification(self):
        url = "https://transports-fictifs.example/devenir-partenaire"
        self.pages.marquer(self.cx, url, self.pages.Acces.CONSULTEE,
                           motif="1 200 octets", empreinte="abc")
        p = self.pages.lire(self.cx, url)
        self.assertIs(p.acces, self.pages.Acces.CONSULTEE)
        self.assertIs(p.statut, self.pages.Statut.CANDIDATE,
                      "collectée n'est pas surveillée")


class S8c_LeRattachementNEstJamaisDevine(unittest.TestCase):
    """La règle 16, verrouillée."""

    def setUp(self):
        from radar import chainage, entreprises as ent_mod, pages as mod_pages
        self.chainage, self.ent, self.pages = chainage, ent_mod, mod_pages
        self.cx = ouvrir(":memory:")

    def _chainer(self, *trouvailles):
        for t in trouvailles:
            tr.inscrire(self.cx, t, mode=Mode.DEMO)
        reg = self.ent.charger(self.cx)
        b = self.chainage.chainer(self.cx, tr.toutes(self.cx), reg)
        self.ent.enregistrer(self.cx, reg)
        return b, reg

    def test_1_un_site_de_presse_n_est_pas_l_entreprise_dont_il_parle(self):
        """LE DÉFAUT CORRIGÉ AVANT LIVRAISON.

        « Fictif SA ouvre un dépôt » publié sur presse-fictive.example : deux
        entités, aucune relation prouvée. Créer « Fictif SA » avec la clé du
        site de presse serait rattacher une page à une entreprise parce que
        son nom y figure.
        """
        self._chainer(resultat("https://presse-fictive.example/depot-gand",
                               source="fixture_alpha",
                               titre="Fictif SA ouvre un nouveau dépôt à Gand"))
        noms = {e.nom for e in self.ent.charger(self.cx).entreprises.values()}
        self.assertEqual(noms, {"presse-fictive.example"})
        self.assertNotIn("Fictif SA", noms,
                         "une société CITÉE n'est pas celle qui tient le domaine")

    def test_1bis_la_societe_citee_n_est_pas_perdue_pour_autant(self):
        from radar.chainage import societe_citee
        t = resultat("https://presse-fictive.example/depot-gand",
                     titre="Fictif SA ouvre un nouveau dépôt à Gand")
        self.assertEqual(societe_citee(t), "Fictif SA")

    def test_2_le_rattachement_par_domaine_est_un_fait_observe(self):
        self._chainer(resultat("https://exemple.example/partenaires"))
        p = self.pages.lire(self.cx, "https://exemple.example/partenaires")
        self.assertEqual(p.rattachement, self.pages.PAR_DOMAINE)
        self.assertEqual(p.entreprise, "exemple.example")

    def test_3_deux_noms_voisins_ne_fusionnent_jamais(self):
        self._chainer(resultat("https://transport-belgium.example/a"),
                      resultat("https://transports-belgium.example/b"))
        entreprises = self.ent.charger(self.cx).entreprises
        self.assertEqual(len(entreprises), 2,
                         "deux domaines voisins restent deux entreprises")

    def test_4_une_url_sans_hote_ne_cree_aucune_entreprise(self):
        b, reg = self._chainer(resultat("https://exemple.example/a"))
        avant = len(reg.entreprises)
        # Une trouvaille inscrite à la main, sans hôte exploitable.
        from radar.chainage import _entreprise_de
        class Fausse:
            url, titre, extrait = "pas-une-url", "", ""
        nom, domaine = _entreprise_de(reg, Fausse())
        self.assertIsNone(nom)
        self.assertIsNone(domaine)

    def test_5_le_module_ne_compare_aucun_nom_pour_rattacher(self):
        import ast
        arbre = ast.parse(pathlib.Path("radar/chainage.py").read_text(encoding="utf-8"))
        noms = {n.attr for n in ast.walk(arbre) if isinstance(n, ast.Attribute)}
        noms |= {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)}
        for interdit in ("SequenceMatcher", "difflib", "levenshtein",
                         "ratio", "similarite"):
            self.assertNotIn(interdit, noms, interdit)


class S8c_PlusieursTrouvaillesPourUneMemePage(unittest.TestCase):
    def setUp(self):
        from radar import chainage, entreprises as ent_mod, pages as mod_pages
        self.cx = ouvrir(":memory:")
        self.pages = mod_pages
        url = "https://partagee.example/besoin"
        for source in ("fixture_alpha", "fixture_beta"):
            tr.inscrire(self.cx, resultat(url, source=source), mode=Mode.DEMO)
        reg = ent_mod.charger(self.cx)
        self.bilan = chainage.chainer(self.cx, tr.toutes(self.cx), reg)
        ent_mod.enregistrer(self.cx, reg)
        self.ent = ent_mod

    def test_1_deux_trouvailles_une_seule_page(self):
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM pages_surveillees").fetchone()["c"], 1)
        self.assertEqual(self.bilan.pages_candidates, 1)
        self.assertEqual(self.bilan.pages_deja_connues, 1)

    def test_2_une_seule_entreprise(self):
        self.assertEqual(len(self.ent.charger(self.cx).entreprises), 1)
        self.assertEqual(self.bilan.entreprises_nouvelles, 1)
        self.assertEqual(self.bilan.entreprises_connues, 1)

    def test_3_les_deux_provenances_sont_conservees_sur_la_page(self):
        p = self.pages.lire(self.cx, "https://partagee.example/besoin")
        self.assertEqual({x["source"] for x in p.provenances},
                         {"fixture_alpha", "fixture_beta"})

    def test_4_les_deux_observations_restent_dans_les_trouvailles(self):
        self.assertEqual(len(tr.toutes(self.cx)), 2)
        self.assertEqual(len(tr.urls_uniques(self.cx)), 1)


def _mecanismes_8c():
    import yaml
    from radar.activite import Ontologie
    from radar.role import DetecteurDeRole
    cap = yaml.safe_load(pathlib.Path("config/capacites.yaml").read_text(encoding="utf-8"))
    prof = yaml.safe_load(pathlib.Path("profil.yaml").read_text(encoding="utf-8"))
    roles = yaml.safe_load(pathlib.Path("config/roles.yaml").read_text(encoding="utf-8"))
    return (Ontologie(cap, prof["familles_actives"], prof.get("familles_exclues")),
            DetecteurDeRole(roles))


# ══════════════════════════ 8d — RECOUPEMENT ENTRE MOTEURS
#
# Rappel : fixtures. Aucun moteur interrogé, aucun marché mesuré.

RAPPEL = "fixtures/recherche-rappel.yaml"


class S8d_DeduplicationDesURL(unittest.TestCase):
    """NIVEAU A — la même page vue plusieurs fois."""

    def setUp(self):
        from radar import recoupement
        self.rec = recoupement
        self.cx = ouvrir(":memory:")

    def _inscrire(self, *paires):
        for url, source in paires:
            tr.inscrire(self.cx, resultat(url, source=source), mode=Mode.DEMO)
        return self.rec.grouper(tr.toutes(self.cx))

    def test_1_meme_url_deux_moteurs_un_groupe_deux_sources(self):
        g = self._inscrire(("https://entreprise.be/partenaire", "fixture_alpha"),
                           ("https://entreprise.be/partenaire", "fixture_beta"))
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0].sources, ["fixture_alpha", "fixture_beta"])
        self.assertTrue(g[0].multi_source)
        self.assertEqual(len(g[0].observations), 2,
                         "les deux observations restent traçables")

    def test_2_les_variations_raisonnables_se_rejoignent(self):
        """www., barre finale, paramètres de suivi — canoniser_url, réutilisé."""
        g = self._inscrire(("https://entreprise.be/partenaire", "a"),
                           ("https://www.entreprise.be/partenaire/", "b"),
                           ("https://entreprise.be/partenaire?utm_source=x", "c"))
        self.assertEqual(len(g), 1, [x.cle for x in g])
        self.assertEqual(len(g[0].urls_vues), 3,
                         "les formes d'origine sont conservées")

    def test_3_deux_chemins_differents_ne_fusionnent_jamais(self):
        g = self._inscrire(("https://entreprise.be/partenaire", "a"),
                           ("https://entreprise.be/partenaires", "b"))
        self.assertEqual(len(g), 2, "la ressemblance n'est pas une preuve")

    def test_4_le_module_ne_reecrit_pas_la_canonisation(self):
        source = pathlib.Path("radar/recoupement.py").read_text(encoding="utf-8")
        self.assertIn("from .deduplication import canoniser_url", source)

    def test_5_un_refus_de_rapprochement_est_compte(self):
        self._inscrire(("https://entreprise.be/a", "x"),
                       ("https://entreprise.be/b", "x"))
        refuses = self.rec.rapprochements_refuses(tr.toutes(self.cx))
        self.assertEqual(len(refuses), 1,
                         "deux pages du même hôte, regardées et non fusionnées")


class S8d_DeduplicationDuBesoin(unittest.TestCase):
    """NIVEAU B — le même besoin sur des pages différentes.

    Ce niveau N'EST PAS refait en 8d : il existe déjà dans
    radar/deduplication.py, et il exige LA MÊME ORGANISATION avant toute
    comparaison. Ces tests prouvent qu'il tient, et qu'il ne fusionne pas
    deux villes.
    """

    def _opp(self, **kw):
        from tests.test_radar import opp
        return opp(**kw)

    def test_1_le_meme_besoin_de_la_meme_organisation_se_rapproche(self):
        from radar.deduplication import meme_besoin
        a = self._opp(acheteur="Ville de Namur",
                      intitule="Transport et distribution de colis",
                      texte="transport et distribution de colis pour la ville")
        b = self._opp(acheteur="Ville de Namur",
                      intitule="Distribution de colis — consultation",
                      texte="distribution de colis, transport, consultation")
        meme, score = meme_besoin(a, b)
        self.assertTrue(meme, f"similarité {score}")

    def test_2_deux_VILLES_differentes_ne_fusionnent_JAMAIS(self):
        """Namur ≠ Liège, quel que soit le vocabulaire commun."""
        from radar.deduplication import meme_besoin
        a = self._opp(acheteur="Ville de Namur",
                      intitule="Transport et distribution de colis",
                      texte="transport et distribution de colis")
        b = self._opp(acheteur="Ville de Liège",
                      intitule="Transport et distribution de colis",
                      texte="transport et distribution de colis")
        meme, _ = meme_besoin(a, b)
        self.assertFalse(meme, "l'organisation doit correspondre AVANT le texte")

    def test_3_deux_METIERS_differents_ne_fusionnent_pas(self):
        from radar.deduplication import meme_besoin
        a = self._opp(acheteur="Ville de Namur",
                      intitule="Distribution de colis",
                      texte="distribution de colis et transport")
        b = self._opp(acheteur="Ville de Namur",
                      intitule="Nettoyage industriel des locaux",
                      texte="nettoyage industriel, entretien des sols, vitrerie")
        meme, score = meme_besoin(a, b)
        self.assertFalse(meme, f"vocabulaires sans rapport, similarité {score}")

    def test_4_une_meme_entreprise_avec_deux_besoins_reste_deux_besoins(self):
        from radar.deduplication import meme_besoin
        a = self._opp(acheteur="Transports Exemple",
                      intitule="Recherche sous-traitant distribution colis",
                      texte="sous-traitant pour la distribution de colis")
        b = self._opp(acheteur="Transports Exemple",
                      intitule="Location d'entrepôt frigorifique",
                      texte="location entrepot frigorifique stockage froid")
        meme, _ = meme_besoin(a, b)
        self.assertFalse(meme)

    def test_5_le_besoin_ne_se_dedoublonne_PAS_a_la_decouverte(self):
        """Une trouvaille n'a ni organisation ni objet structuré. Fusionner
        là-dessus serait fusionner sur quelques mots."""
        import ast
        source = pathlib.Path("radar/recoupement.py").read_text(encoding="utf-8")
        arbre = ast.parse(source)
        # On inspecte ce que le module IMPORTE et APPELLE, pas sa prose — qui a
        # le droit d'expliquer pourquoi elle ne fait pas cette déduplication.
        importes = set()
        for n in ast.walk(arbre):
            if isinstance(n, ast.ImportFrom):
                importes |= {a.name for a in n.names}
            elif isinstance(n, ast.Import):
                importes |= {a.name for a in n.names}
        appeles = {n.func.id for n in ast.walk(arbre)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        for interdit in ("meme_besoin", "similarite", "mots_besoin",
                         "signature_objet", "organisation"):
            self.assertNotIn(interdit, importes, f"import « {interdit} »")
            self.assertNotIn(interdit, appeles, f"appel « {interdit} »")
        # Le seul emprunt à deduplication est la canonisation d'URL.
        self.assertEqual(importes & {"canoniser_url", "meme_besoin"},
                         {"canoniser_url"})
        self.assertIn("LA MÊME ORGANISATION", source,
                      "la raison doit rester écrite")


class S8d_DeduplicationDesEntreprises(unittest.TestCase):
    """NIVEAU C — la même organisation. Le domaine, et rien d'autre."""

    def setUp(self):
        from radar import chainage, entreprises as ent_mod
        self.chainage, self.ent = chainage, ent_mod
        self.cx = ouvrir(":memory:")

    def _chainer(self, *urls):
        for u in urls:
            tr.inscrire(self.cx, resultat(u), mode=Mode.DEMO)
        reg = self.ent.charger(self.cx)
        self.chainage.chainer(self.cx, tr.toutes(self.cx), reg)
        self.ent.enregistrer(self.cx, reg)
        return self.ent.charger(self.cx).entreprises

    def test_1_deux_pages_du_meme_domaine_une_entreprise(self):
        e = self._chainer("https://exemple.be/a", "https://exemple.be/b")
        self.assertEqual(len(e), 1)

    def test_2_deux_domaines_voisins_restent_deux_entreprises(self):
        e = self._chainer("https://transport-belgium.be/a",
                          "https://transports-belgium.be/a")
        self.assertEqual(len(e), 2, "la ressemblance de nom ne fusionne pas")

    def test_3_www_et_sans_www_sont_la_meme_entreprise(self):
        e = self._chainer("https://exemple.be/a", "https://www.exemple.be/b")
        self.assertEqual(len(e), 1)


class S8d_LeRappelSeMesureSansClasserAuVolume(unittest.TestCase):
    """LE POINT CENTRAL : peu de volume et beaucoup d'inédit peut valoir
    davantage que beaucoup de volume et rien d'inédit."""

    def setUp(self):
        from radar import fixtures_recherche as fx, recoupement
        self.rec = recoupement
        self.cx = ouvrir(":memory:")
        self.moteurs = fx.depuis_fichier(RAPPEL)
        for m in self.moteurs:
            tr.depuis_moteur(self.cx, m,
                             m.rechercher('"recherche transporteur" Belgique'))
        self.m = self.rec.metriques_moteurs(
            self.cx, interroges=[x.nom for x in self.moteurs],
            declares={"jamais_interroge": "CLÉ ABSENTE"})

    def test_1_volume_eleve_et_redondance_totale(self):
        self.assertEqual(self.m["redondant"]["resultats"], 10)
        self.assertEqual(self.m["redondant"]["uniques"], 0)
        self.assertEqual(self.m["redondant"]["apport_propre"], 0.0)

    def test_2_meme_volume_mais_forte_unicite(self):
        self.assertEqual(self.m["rare"]["resultats"], 10)
        self.assertEqual(self.m["rare"]["uniques"], 8)
        self.assertAlmostEqual(self.m["rare"]["apport_propre"], 0.8)

    def test_3_a_volume_egal_l_apport_differe_du_tout_au_tout(self):
        self.assertEqual(self.m["rare"]["resultats"],
                         self.m["redondant"]["resultats"])
        self.assertGreater(self.m["rare"]["apport_propre"],
                           self.m["redondant"]["apport_propre"])

    def test_4_le_rapport_refuse_explicitement_de_classer_au_volume(self):
        texte = self.rec.rapport(self.cx,
                                 interroges=[x.nom for x in self.moteurs])
        self.assertIn("AUCUN MOTEUR N'EST CLASSÉ AU VOLUME", texte)
        self.assertIn("APPORT", texte)

    def test_5_un_moteur_interroge_sans_resultat_affiche_ZERO(self):
        """« muet » a répondu. Son silence est une mesure."""
        self.assertEqual(self.m["muet"]["resultats"], 0)
        self.assertTrue(self.m["muet"]["mesure"])
        self.assertTrue(self.m["muet"].get("muet"))

    def test_6_un_moteur_non_interroge_affiche_NON_MESURE_jamais_zero(self):
        c = self.m["jamais_interroge"]
        self.assertEqual(c["resultats"], self.rec.NON_MESURE)
        self.assertFalse(c["mesure"])
        self.assertNotEqual(c["resultats"], 0)

    def test_7_le_radar_continue_quand_un_moteur_manque(self):
        texte = self.rec.rapport(
            self.cx, interroges=[x.nom for x in self.moteurs],
            declares={"absent": "CLÉ ABSENTE — aucune clé fournie"})
        self.assertIn("NON DISPONIBLE", texte)
        self.assertIn("abondant", texte, "les autres moteurs restent mesurés")

    def test_8_la_chaine_de_rappel_est_complete(self):
        r = self.rec.metriques_rappel(self.cx)
        for cle in ("resultats_bruts", "urls_uniques", "observations_partagees",
                    "groupes", "groupes_multi_sources", "doublons_regroupes",
                    "rapprochements_refuses"):
            self.assertIn(cle, r)
        self.assertEqual(r["resultats_bruts"], 120)
        self.assertEqual(r["urls_uniques"], 108)
        self.assertEqual(r["doublons_regroupes"], 12)


class S8d_LHistoriqueNEstJamaisDetruit(unittest.TestCase):
    def setUp(self):
        from radar import recoupement
        self.rec = recoupement
        self.cx = ouvrir(":memory:")
        url = "https://partagee.example/besoin"
        for source, q in (("fixture_alpha", "requête A"),
                          ("fixture_beta", "requête B")):
            tr.inscrire(self.cx, resultat(url, source=source, requete=q, rang=2),
                        mode=Mode.DEMO)
        self.groupe = self.rec.grouper(tr.toutes(self.cx))[0]

    def test_1_par_quels_moteurs_et_a_quelles_dates(self):
        lignes = self.groupe.historique()
        self.assertEqual(len(lignes), 2)
        self.assertTrue(any("fixture_alpha" in l for l in lignes))
        self.assertTrue(any("fixture_beta" in l for l in lignes))
        for l in lignes:
            self.assertIn("20", l, "chaque observation porte sa date")

    def test_2_les_requetes_sont_conservees(self):
        self.assertEqual(sorted(self.groupe.requetes), ["requête A", "requête B"])

    def test_3_les_rangs_sont_conserves(self):
        self.assertEqual([o.rang for o in self.groupe.observations], [2, 2])

    def test_4_les_dates_extremes_sont_disponibles(self):
        self.assertIsNotNone(self.groupe.premiere_vue)
        self.assertIsNotNone(self.groupe.derniere_vue)

    def test_5_le_regroupement_ne_supprime_aucune_trouvaille(self):
        self.assertEqual(len(tr.toutes(self.cx)), 2)


class S8d_LeRecoupementNeTouchePasAuCommercial(unittest.TestCase):
    def test_1_le_module_ignore_le_scoring_et_la_classification(self):
        import ast
        arbre = ast.parse(pathlib.Path("radar/recoupement.py")
                          .read_text(encoding="utf-8"))
        noms = {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)}
        noms |= {n.attr for n in ast.walk(arbre) if isinstance(n, ast.Attribute)}
        for interdit in ("score", "Classement", "Opportunite", "classification",
                         "Type", "bareme", "ponderation"):
            self.assertNotIn(interdit, noms, interdit)

    def test_2_aucun_nom_de_moteur_reel_dans_le_code(self):
        import ast
        arbre = ast.parse(pathlib.Path("radar/recoupement.py")
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
        for nom in ("google", "brave", "bing", "ted", "bda"):
            for t in litterales:
                self.assertNotIn(nom, t, nom)

    def test_3_aucun_reseau(self):
        source = pathlib.Path("radar/recoupement.py").read_text(encoding="utf-8")
        for interdit in ("urllib", "requests", "socket", "urlopen"):
            self.assertNotIn(interdit, source, interdit)

    def test_4_aucune_opportunite_creee_par_le_recoupement(self):
        from radar import fixtures_recherche as fx, recoupement
        cx = ouvrir(":memory:")
        for m in fx.depuis_fichier(RAPPEL):
            tr.depuis_moteur(cx, m, m.rechercher('"recherche transporteur" Belgique'))
        recoupement.rapport(cx)
        for table in ("opportunites", "avis", "entreprises", "pages_surveillees"):
            self.assertEqual(
                cx.execute(f"SELECT count(*) c FROM {table}").fetchone()["c"], 0,
                table)

    def test_5_le_score_reste_independant_du_moteur_et_du_recouvrement(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        a, b = opp(ref_source="D1"), opp(ref_source="D2")
        a.provenances = [{"source": "abondant", "circuit": circuit.DECOUVERTE}]
        b.provenances = [{"source": "rare", "circuit": circuit.DECOUVERTE},
                         {"source": "redondant", "circuit": circuit.DECOUVERTE}]
        self.assertEqual(moteur().analyser(a, MAINTENANT).score.total,
                         moteur().analyser(b, MAINTENANT).score.total,
                         "être trouvée deux fois ne vaut pas un point de plus")

    def test_6_les_metriques_reelles_restent_vides(self):
        from radar import fixtures_recherche as fx
        cx = ouvrir(":memory:")
        for m in fx.depuis_fichier(RAPPEL):
            tr.depuis_moteur(cx, m, m.rechercher('"recherche transporteur" Belgique'))
        self.assertEqual(tr.metriques(cx)[Mode.REEL.value]["trouvailles"], 0)
        self.assertIn("NON MESURÉE", tr.rapport(cx))


class S8d_LesAgregateursNeSontPasTranches(unittest.TestCase):
    """§8 — on MESURE un indicateur, on ne conclut RIEN."""

    def setUp(self):
        from radar import recoupement
        self.rec = recoupement
        self.cx = ouvrir(":memory:")
        # Un domaine qui revient sous quatre sujets sans rapport.
        for i, q in enumerate(("transport", "boulangerie", "coiffure", "informatique")):
            tr.inscrire(self.cx, resultat(f"https://presse.example/article-{i}",
                                          source="fixture_alpha", requete=q),
                        mode=Mode.DEMO)
        # Une entreprise, un seul sujet.
        tr.inscrire(self.cx, resultat("https://transporteur.example/partenaire",
                                      source="fixture_alpha", requete="transport"),
                    mode=Mode.DEMO)

    def test_1_l_indicateur_repere_bien_le_domaine_transversal(self):
        t = self.rec.domaines_transversaux(self.cx, seuil=3)
        self.assertIn("presse.example", t)
        self.assertEqual(t["presse.example"], 4)
        self.assertNotIn("transporteur.example", t)

    def test_2_mais_AUCUNE_identite_n_est_modifiee(self):
        from radar import chainage, entreprises as ent_mod, identite as mod_id
        reg = ent_mod.charger(self.cx)
        chainage.chainer(self.cx, tr.toutes(self.cx), reg)
        ent_mod.enregistrer(self.cx, reg)
        chainage.marquer_identites(self.cx, reg)
        for cle in ent_mod.charger(self.cx).entreprises:
            self.assertIs(mod_id.lire(self.cx, cle).etat, mod_id.Etat.INCONNUE)

    def test_3_aucune_entreprise_n_est_ecartee(self):
        from radar import chainage, entreprises as ent_mod
        from radar.entreprises import Etat as EtatEnt
        reg = ent_mod.charger(self.cx)
        chainage.chainer(self.cx, tr.toutes(self.cx), reg)
        ent_mod.enregistrer(self.cx, reg)
        for e in ent_mod.charger(self.cx).entreprises.values():
            self.assertIsNot(e.etat, EtatEnt.ECARTEE)

    def test_4_aucune_liste_en_dur_de_domaines(self):
        import ast
        arbre = ast.parse(pathlib.Path("radar/recoupement.py")
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
        for t in litterales:
            self.assertNotIn(".example", t)
            self.assertNotIn(".com", t)
            self.assertNotIn("presse", t)

    def test_5_le_rapport_dit_que_ce_n_est_pas_une_preuve(self):
        texte = self.rec.rapport(self.cx)
        self.assertIn("INDICATEUR", texte)
        self.assertIn("PAS une preuve", texte)
        self.assertIn("Aucune identité", texte)
