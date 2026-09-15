"""LA V1 EN LIGNE DE COMMANDE — ce qu'un exploitant voit vraiment.

Ces tests lancent les VRAIES commandes, sur le VRAI jeu de données du
14/09, et lisent ce qui s'affiche. Ils protègent trois choses :

    1. la CLI n'invente rien — aucune donnée absente n'est comblée ;
    2. la CLI ne décide rien — catégories, actions et scores viennent du
       moteur, et les emojis avec ;
    3. une source non consultée ne devient jamais « 0 résultat ».

Ils protègent aussi l'IDEMPOTENCE : deux analyses sur les mêmes données
ne doublent rien.
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from radar.cli import principal                                # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent
EXPORT = str(RACINE / "validation/exports-reels/2026-09-14-premier-export-reel.tsv")


class Socle(unittest.TestCase):
    """Une base neuve par classe, et une analyse réelle déjà jouée."""

    ANALYSE = True

    @classmethod
    def setUpClass(cls):
        cls.dossier = tempfile.mkdtemp()
        cls.base = str(pathlib.Path(cls.dossier) / "essai.sqlite3")
        if cls.ANALYSE:
            cls.lancer_classe("analyse-du-jour", "--import", EXPORT, "--top", "0")

    @classmethod
    def lancer_classe(cls, *args):
        sortie, erreur = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(sortie), contextlib.redirect_stderr(erreur):
            code = principal(["--base", cls.base, *args])
        return code, sortie.getvalue(), erreur.getvalue()

    def lancer(self, *args):
        return self.lancer_classe(*args)

    def json_de(self, *args):
        code, texte, _ = self.lancer(*args, "--json")
        self.assertEqual(code, 0, args)
        return json.loads(texte)


# ═══════════════════════════════════════ LANCEMENT ET AIDE
class A_LeRadarSeLance(unittest.TestCase):
    def test_1_l_aide_repond_et_liste_les_commandes_de_la_v1(self):
        sortie = io.StringIO()
        with self.assertRaises(SystemExit) as sortie_code:
            with contextlib.redirect_stdout(sortie):
                principal(["--help"])
        self.assertEqual(sortie_code.exception.code, 0)
        texte = sortie.getvalue()
        for commande in ("analyse-du-jour", "opportunites", "opportunite",
                         "entreprises", "entreprise", "signaux", "suivi",
                         "notifications", "sources", "tableau", "statut"):
            self.assertIn(commande, texte, commande)

    def test_2_sans_commande_le_radar_le_dit_et_sort_en_erreur(self):
        erreur = io.StringIO()
        with self.assertRaises(SystemExit) as code:
            with contextlib.redirect_stderr(erreur):
                principal([])
        self.assertNotEqual(code.exception.code, 0)

    def test_3_les_lanceurs_windows_et_unix_existent(self):
        """Je testerai d'abord depuis CMD : le lanceur doit être là."""
        self.assertTrue((RACINE / "radar.cmd").exists(), "lanceur Windows")
        self.assertTrue((RACINE / "radar.sh").exists(), "lanceur Unix")
        cmd = (RACINE / "radar.cmd").read_text(encoding="utf-8", errors="replace")
        self.assertIn("python -m radar.cli", cmd)
        self.assertIn("PYTHONIOENCODING", cmd,
                      "sans cela, les emojis cassent l'affichage sous CMD")

    def test_4_le_statut_repond_sur_une_base_neuve(self):
        dossier = tempfile.mkdtemp()
        base = str(pathlib.Path(dossier) / "neuve.sqlite3")
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            code = principal(["--base", base, "statut"])
        self.assertEqual(code, 0)
        texte = sortie.getvalue()
        self.assertIn("Moteur", texte)
        self.assertIn("OK", texte)
        self.assertIn("PROCHAINE COMMANDE UTILE", texte)


# ═══════════════════════════════════════ ANALYSE DU JOUR
class B_LAnalyseDuJour(Socle):
    ANALYSE = False

    def test_1_une_analyse_sur_le_jeu_reel_affiche_sa_synthese(self):
        code, texte, _ = self.lancer("analyse-du-jour", "--import", EXPORT,
                                     "--top", "0")
        self.assertEqual(code, 0)
        self.assertIn("RADAR COMMERCIAL — ANALYSE DU JOUR", texte)
        self.assertIn("IMPORT RÉEL", texte)
        self.assertIn("Résultats en base", texte)
        self.assertIn("OPPORTUNITÉS PAR CATÉGORIE", texte)
        self.assertIn("ACTIONS RECOMMANDÉES", texte)
        self.assertIn("SOURCES", texte)
        self.assertIn("Analyse terminée.", texte)

    def test_2_les_chiffres_viennent_du_moteur_pas_d_un_codage_en_dur(self):
        _, texte, _ = self.lancer("analyse-du-jour", "--import", EXPORT,
                                  "--top", "0")
        charge = self.json_de("opportunites", "--tout", "--limite", "999")
        self.assertEqual(len(charge), 27, "le jeu réel porte 27 opportunités")
        for ligne in ("Résultats en base", "URLs uniques"):
            self.assertIn(ligne, texte)
        self.assertIn("35", texte)
        self.assertIn("28", texte)

    def test_3_les_six_categories_sont_affichees_avec_leurs_emojis(self):
        from radar.classification import Type
        _, texte, _ = self.lancer("analyse-du-jour", "--import", EXPORT,
                                  "--top", "0")
        for t in Type:
            self.assertIn(t.value, texte, t.value)
            self.assertIn(t.emoji, texte, t.emoji)

    def test_4_une_source_sans_cle_dit_pourquoi_et_ne_rend_pas_zero(self):
        _, texte, _ = self.lancer("analyse-du-jour", "--import", EXPORT,
                                  "--top", "0")
        self.assertIn("NON DISPONIBLE", texte)
        self.assertIn("CLÉ ABSENTE", texte)
        self.assertNotIn("google                   CONSULTÉE", texte)

    def test_5_le_bot_dit_qu_il_n_a_rien_envoye(self):
        _, texte, _ = self.lancer("analyse-du-jour", "--import", EXPORT,
                                  "--top", "0")
        self.assertIn("n'a contacté personne", texte)

    def test_6_une_page_non_collectee_n_est_pas_une_page_vide(self):
        _, texte, _ = self.lancer("analyse-du-jour", "--import", EXPORT,
                                  "--top", "0")
        self.assertIn("AUCUNE PAGE N'A ÉTÉ LUE", texte)

    def test_7_la_sortie_json_existe_et_est_structuree(self):
        code, texte, _ = self.lancer("analyse-du-jour", "--import", EXPORT,
                                     "--json")
        self.assertEqual(code, 0)
        charge = json.loads(texte)
        self.assertIn("cycle", charge)
        self.assertIn("mode", charge)
        self.assertIn("opportunites", charge)
        self.assertEqual(
            set(charge["cycle"]["sources"]),
            {"demandees", "executees", "en_erreur", "non_disponibles",
             "non_mesurees"})

    def test_8_le_mode_est_lu_dans_ce_qui_a_ete_execute(self):
        """Une fixture ne peut pas se présenter comme une recherche réelle."""
        charge = json.loads(self.lancer("analyse-du-jour", "--json")[1])
        self.assertIn("AUCUNE SOURCE EXÉCUTÉE", charge["mode"])
        charge = json.loads(self.lancer("analyse-du-jour", "--import", EXPORT,
                                        "--json")[1])
        self.assertIn("HORS RADAR", charge["mode"])


# ═══════════════════════════════════════ IDEMPOTENCE
class C_DeuxAnalysesNeDoublentRien(Socle):
    ANALYSE = False

    def test_la_seconde_analyse_ne_cree_rien_de_neuf(self):
        self.lancer("analyse-du-jour", "--import", EXPORT, "--top", "0")
        avant = self.json_de("opportunites", "--tout", "--limite", "999")
        entreprises_avant = self.json_de("entreprises", "--limite", "999")
        notifs_avant = self.json_de("notifications", "--limite", "999")

        _, texte, _ = self.lancer("analyse-du-jour", "--import", EXPORT,
                                  "--top", "0")
        apres = self.json_de("opportunites", "--tout", "--limite", "999")
        entreprises_apres = self.json_de("entreprises", "--limite", "999")
        notifs_apres = self.json_de("notifications", "--limite", "999")

        self.assertEqual(len(apres), len(avant), "aucune opportunité dupliquée")
        self.assertEqual(len(entreprises_apres), len(entreprises_avant),
                         "aucune entreprise dupliquée")
        self.assertEqual(len(notifs_apres), len(notifs_avant),
                         "aucune notification répétée")
        self.assertIn("CE QUI EST NEUF", texte)
        self.assertIn("Déjà connues avant ce cycle", texte)

    def test_la_provenance_survit_a_la_seconde_analyse(self):
        self.lancer("analyse-du-jour", "--import", EXPORT, "--top", "0")
        self.lancer("analyse-du-jour", "--import", EXPORT, "--top", "0")
        for c in self.json_de("opportunites", "--tout", "--limite", "999"):
            self.assertTrue(c["sources"])
            for s in c["sources"]:
                self.assertTrue(s["source"])


# ═══════════════════════════════════════ LES VUES
class D_LesVuesSontLisibles(Socle):
    def test_1_opportunites_masque_le_blanc_et_sait_le_montrer(self):
        _, retenues, _ = self.lancer("opportunites")
        self.assertNotIn("⚪", retenues, "⚪ n'est pas une opportunité retenue")
        _, tout, _ = self.lancer("opportunites", "--tout")
        self.assertIn("⚪", tout, "…mais elle n'est jamais supprimée")

    def test_2_une_opportunite_dit_pourquoi_elle_est_retenue(self):
        _, texte, _ = self.lancer("opportunites")
        self.assertIn("Pourquoi elle est retenue", texte)
        self.assertIn("ACTION :", texte)
        self.assertIn("Niveau de preuve", texte)

    def test_3_la_fiche_complete_expose_les_quatre_dimensions(self):
        carte = self.json_de("opportunites", "--limite", "1")[0]
        code, texte, _ = self.lancer("opportunite", str(carte["avis_id"]))
        self.assertEqual(code, 0)
        for bloc in ("IDENTITÉ", "PROVENANCE", "LES QUATRE DIMENSIONS",
                     "COMMERCIAL", "EXÉCUTION", "VOIES COMMERCIALES",
                     "INFORMATIONS MANQUANTES", "SURVEILLANCE",
                     "SUIVI COMMERCIAL"):
            self.assertIn(bloc, texte, bloc)
        for champ in ("Type d'information", "Nature", "État de procédure",
                      "Action recommandée"):
            self.assertIn(champ, texte, champ)

    def test_4_la_fiche_n_invente_aucune_valeur_absente(self):
        carte = self.json_de("opportunites", "--limite", "1")[0]
        _, texte, _ = self.lancer("opportunite", str(carte["avis_id"]))
        formes = ("À CONFIRMER", "NON PUBLIÉ", "NON MESURÉ", "NON DISPONIBLE",
                  "NON CALCULABLE", "INCONNUE", "JAMAIS CONSULTÉE")
        self.assertTrue(any(f in texte for f in formes),
                        "une absence doit se dire, pas se taire")
        self.assertNotIn(": None", texte, "aucun None brut à l'écran")
        self.assertNotIn(": ,", texte)

    def test_5_les_entreprises_ne_sont_jamais_devinees(self):
        code, texte, _ = self.lancer("entreprises")
        self.assertEqual(code, 0)
        self.assertIn("IDENTITÉ", texte)
        self.assertIn("INCONNUE", texte)
        self.assertIn("n'est pas une raison sociale", texte)

    def test_6_une_fiche_entreprise_montre_pages_et_opportunites(self):
        e = self.json_de("entreprises", "--limite", "1")[0]
        code, texte, _ = self.lancer("entreprise", str(e["domaine"]))
        self.assertEqual(code, 0)
        for bloc in ("MOTIFS OBSERVÉS", "PAGES", "OPPORTUNITÉS ASSOCIÉES",
                     "SIGNAUX COMMERCIAUX", "PROCHAINE ACTION"):
            self.assertIn(bloc, texte, bloc)

    def test_7_un_signal_n_est_jamais_presente_comme_un_contrat(self):
        code, texte, _ = self.lancer("signaux", "--limite", "3")
        self.assertEqual(code, 0)
        self.assertIn("personne n'a rien demandé", texte)
        self.assertIn("Ce que nous savons", texte)
        self.assertIn("Ce que nous supposons", texte)
        self.assertIn("ne constitue pas la", texte)
        self.assertIn("preuve d'un contrat", texte)

    def test_8_le_signal_affiche_sa_nature_reelle(self):
        """Écrire « SIGNAL » sur une HYPOTHÈSE présenterait une déduction
        comme un fait observé."""
        liste = self.json_de("signaux", "--limite", "50")
        _, texte, _ = self.lancer("signaux", "--limite", "50")
        for s in liste:
            self.assertIn(s["nature"], ("SIGNAL", "HYPOTHÈSE"))
        if any(s["nature"] == "HYPOTHÈSE" for s in liste):
            self.assertIn("HYPOTHÈSE —", texte)

    def test_9_le_suivi_expose_les_huit_statuts_existants(self):
        from radar.suivi import Statut
        code, texte, _ = self.lancer("suivi")
        self.assertEqual(code, 0)
        for s in Statut:
            self.assertIn(s.value, texte, s.value)
        self.assertIn("posé par un humain", texte)

    def test_10_les_notifications_sont_preparees_jamais_envoyees(self):
        code, texte, _ = self.lancer("notifications")
        self.assertEqual(code, 0)
        self.assertIn("PRÉPARÉE N'EST PAS ENVOYÉE", texte)
        self.assertIn("aucune candidature", texte)
        for n in self.json_de("notifications", "--limite", "99"):
            self.assertFalse(n["envoyee"])

    def test_11_les_sources_distinguent_indisponible_et_zero(self):
        code, texte, _ = self.lancer("sources")
        self.assertEqual(code, 0)
        self.assertIn("NON DISPONIBLE", texte)
        self.assertIn("CONSULTÉE", texte)
        self.assertIn("n'est PAS « 0 résultat »", texte)
        par_nom = {s["nom"]: s for s in self.json_de("sources")}
        for nom in ("google", "brave"):
            self.assertIn(nom, par_nom, f"{nom} doit apparaître même sans clé")
            self.assertEqual(par_nom[nom]["etat"], "NON DISPONIBLE")
            self.assertNotEqual(par_nom[nom]["resultats"], 0,
                                "NON DISPONIBLE n'est pas 0 résultat")
            self.assertIn("CLÉ ABSENTE", par_nom[nom]["motif"])

    def test_12_le_tableau_reste_lisible_et_dit_ses_limites(self):
        code, texte, _ = self.lancer("tableau")
        self.assertEqual(code, 0)
        for bloc in ("DÉCOUVERTE", "QUALIFICATION", "QUALITÉ", "COMMERCIAL"):
            self.assertIn(bloc, texte, bloc)
        # ZÉRO verdict n'est pas « échantillon insuffisant » : c'est
        # l'absence totale de relecture, et le tableau le dit autrement.
        self.assertIn("NON MESURÉ", texte)
        self.assertIn("Ce n'est pas « zéro erreur »", texte)

    def test_12bis_sous_vingt_verdicts_aucun_taux_n_est_affiche(self):
        """La limite statistique reste visible — §12 de la V1."""
        carte = self.json_de("opportunites", "--limite", "1")[0]
        url = carte["sources"][0]["reference"]
        code, _, _ = self.lancer("verdict", url, "VP", "--par", "essai")
        self.assertEqual(code, 0)
        _, texte, _ = self.lancer("tableau")
        self.assertIn("ÉCHANTILLON INSUFFISANT", texte,
                      "sous 20 verdicts, aucun pourcentage n'est calculé")

    def test_13_le_statut_eprouve_les_composants(self):
        code, texte, _ = self.lancer("statut")
        self.assertEqual(code, 0)
        for composant in ("Moteur", "Base", "Sources", "Import", "Collecte",
                          "Notifications", "Surveillance"):
            self.assertIn(composant, texte, composant)
        self.assertIn("PARTIEL", texte, "deux moteurs sont sans clé")


# ═══════════════════════════════════════ JSON
class E_LaSortieStructuree(Socle):
    def test_chaque_vue_a_sa_sortie_json(self):
        for args in (["opportunites"], ["entreprises"], ["signaux"],
                     ["suivi"], ["notifications"], ["sources"], ["statut"]):
            charge = self.json_de(*args)
            self.assertIsInstance(charge, (list, dict), args)

    def test_json_et_humain_ne_sortent_jamais_ensemble(self):
        _, texte, _ = self.lancer("sources", "--json")
        self.assertNotIn("ÉTAT RÉEL DES SOURCES", texte)
        json.loads(texte)

    def test_une_fiche_json_porte_les_champs_du_contrat(self):
        carte = self.json_de("opportunites", "--limite", "1")[0]
        for champ in ("avis_id", "entreprise", "categorie", "nature",
                      "etat_procedure", "sources", "score", "score_mesurable",
                      "niveau_de_preuve", "action_recommandee",
                      "raison_principale", "surveillance", "suivi"):
            self.assertIn(champ, carte, champ)


# ═══════════════════════════════════════ ERREURS
class F_LesErreursSontHumaines(Socle):
    ANALYSE = False

    def test_1_un_fichier_introuvable_ne_montre_aucun_traceback(self):
        code, _, erreur = self.lancer("analyse-du-jour", "--import",
                                      "/chemin/qui/n/existe/pas.tsv")
        self.assertEqual(code, 2)
        self.assertIn("IMPOSSIBLE", erreur)
        self.assertIn("fichier introuvable", erreur)
        self.assertIn("Aucune donnée n'a été créée", erreur)
        self.assertNotIn("Traceback", erreur)

    def test_2_un_fichier_sans_provenance_est_refuse_et_le_dit(self):
        mauvais = pathlib.Path(self.dossier) / "sans-provenance.tsv"
        mauvais.write_text("colonne\tautre\n1\t2\n", encoding="utf-8")
        code, texte, _ = self.lancer("analyse-du-jour", "--import",
                                     str(mauvais), "--top", "0")
        self.assertEqual(code, 0, "le cycle aboutit, mais il dit son erreur")
        self.assertIn("ERREURS", texte)
        self.assertIn("EXÉCUTÉ HORS RADAR", texte)
        self.assertIn("Statut            : ERREUR", texte)

    def test_3_un_fichier_vide_ne_fabrique_aucune_donnee(self):
        vide = pathlib.Path(self.dossier) / "vide.tsv"
        vide.write_text("", encoding="utf-8")
        code, texte, _ = self.lancer("analyse-du-jour", "--import", str(vide),
                                     "--top", "0")
        self.assertEqual(code, 0)
        self.assertIn("ERREURS", texte)
        self.assertEqual(self.json_de("opportunites", "--tout"), [])

    def test_4_une_opportunite_inconnue_le_dit_sans_traceback(self):
        code, _, erreur = self.lancer("opportunite", "999999")
        self.assertEqual(code, 2)
        self.assertIn("aucune opportunité #999999", erreur)
        self.assertIn("radar opportunites", erreur)
        self.assertNotIn("Traceback", erreur)

    def test_5_une_entreprise_inconnue_le_dit_sans_traceback(self):
        code, _, erreur = self.lancer("entreprise", "nexistepas.invalid")
        self.assertEqual(code, 2)
        self.assertIn("aucune entreprise", erreur)
        self.assertNotIn("Traceback", erreur)

    def test_6_une_base_inaccessible_le_dit_sans_traceback(self):
        sortie, erreur = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(sortie), contextlib.redirect_stderr(erreur):
            code = principal(["--base", "/racine-interdite-xyz/x.sqlite3",
                              "statut"])
        self.assertEqual(code, 2)
        self.assertIn("IMPOSSIBLE", erreur.getvalue())
        self.assertNotIn("Traceback", erreur.getvalue())

    def test_7_une_categorie_inconnue_liste_les_six_vraies(self):
        code, _, erreur = self.lancer("opportunites", "--categorie", "VIOLET")
        self.assertEqual(code, 2)
        self.assertIn("n'est pas une catégorie", erreur)
        self.assertIn("DIRECT", erreur)


# ═══════════════════════════════════════ WINDOWS
class H_LeParcoursWindows(Socle):
    """Ce qui casse chez l'utilisateur, pas chez le développeur."""

    ANALYSE = False

    def test_1_une_console_qui_ne_sait_pas_ecrire_en_UTF8_ne_fait_pas_planter(self):
        """BUG MESURÉ, CORRIGÉ.

        Sous une console Windows en cp850 — la page de codes par défaut
        d'un CMD français — ou dès qu'on redirige la sortie vers un
        fichier pour la copier-coller, `sys.stdout` n'est plus en UTF-8.
        Le premier tiret cadratin du rapport levait alors
        UnicodeEncodeError, et l'utilisateur voyait un traceback et un
        code 1 : pour lui, le radar était cassé.

        `cli._sortie_lisible` repasse les flux en UTF-8 avec
        `errors="replace"` : si la console ne sait vraiment pas afficher
        un caractère, elle écrit « ? » et le texte reste lisible.
        """
        import os
        import subprocess
        chemin = str(pathlib.Path(self.dossier) / "cp850.sqlite3")
        r = subprocess.run(
            [sys.executable, "-m", "radar.cli", "--base", chemin, "statut"],
            capture_output=True, cwd=str(RACINE),
            env={**os.environ, "PYTHONIOENCODING": "cp850"})
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        self.assertNotIn(b"Traceback", r.stderr)
        self.assertNotIn(b"UnicodeEncodeError", r.stderr)
        self.assertIn("RADAR", r.stdout.decode("utf-8", "replace"))

    def test_2_la_sortie_redirigee_reste_lisible(self):
        """Le cas réel : `radar ... > sortie.txt` pour copier-coller."""
        import os
        import subprocess
        chemin = str(pathlib.Path(self.dossier) / "redirige.sqlite3")
        fichier = pathlib.Path(self.dossier) / "sortie.txt"
        with fichier.open("wb") as f:
            r = subprocess.run(
                [sys.executable, "-m", "radar.cli", "--base", chemin, "statut"],
                stdout=f, stderr=subprocess.PIPE, cwd=str(RACINE),
                env={**os.environ, "PYTHONIOENCODING": "cp850"})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, b"")
        self.assertIn("ÉTAT DU SYSTÈME",
                      fichier.read_text(encoding="utf-8", errors="replace"))

    def test_3_un_chemin_windows_introuvable_est_dit_proprement(self):
        code, _, erreur = self.lancer("analyse-du-jour", "--import",
                                      r"Z:\nexiste\pas.tsv")
        self.assertEqual(code, 2)
        self.assertIn("fichier introuvable", erreur)
        self.assertNotIn("Traceback", erreur)

    def test_4_le_lanceur_windows_regle_la_page_de_codes(self):
        """Deux réglages, et les deux sont nécessaires : l'un dit à Python
        quoi écrire, l'autre dit à la console quoi afficher."""
        cmd = (RACINE / "radar.cmd").read_text(encoding="utf-8",
                                               errors="replace")
        self.assertIn("PYTHONIOENCODING=utf-8", cmd)
        self.assertIn("chcp 65001", cmd)
        self.assertIn("python -m radar.cli", cmd)

    def test_5_les_identifiants_sont_reproductibles_sur_une_base_neuve(self):
        """La procédure de test donne `radar opportunite 8` : il faut que
        le 8 existe vraiment, et qu'il soit le même à chaque fois."""
        vus = []
        for n in range(2):
            base = str(pathlib.Path(self.dossier) / f"reproductible{n}.sqlite3")
            sortie = io.StringIO()
            with contextlib.redirect_stdout(sortie):
                principal(["--base", base, "analyse-du-jour",
                           "--import", EXPORT, "--top", "0"])
            sortie = io.StringIO()
            with contextlib.redirect_stdout(sortie):
                principal(["--base", base, "opportunites", "--json",
                           "--limite", "99"])
            vus.append([c["avis_id"] for c in json.loads(sortie.getvalue())])
        self.assertEqual(vus[0], vus[1], "mêmes données, mêmes identifiants")
        self.assertIn(8, vus[0], "l'identifiant 8 de la procédure existe bien")


# ═══════════════════════════════════════ L'INVARIANT
class G_LaCliNeDecideRien(unittest.TestCase):
    """Aucune règle métier concurrente dans la présentation."""

    def setUp(self):
        import ast
        self.arbre = ast.parse(
            (RACINE / "radar/vue.py").read_text(encoding="utf-8"))

    def test_1_aucun_nom_de_categorie_n_est_ecrit_dans_la_vue(self):
        import ast
        docs = {ast.get_docstring(n, clean=False) for n in ast.walk(self.arbre)
                if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))}
        litteraux = [n.value for n in ast.walk(self.arbre)
                     if isinstance(n, ast.Constant) and isinstance(n.value, str)
                     and n.value not in docs]
        for interdit in ("DIRECT", "RENFORCEMENT", "A_CONSTRUIRE", "PROSPECT",
                         "REJET", "POSTULABLE"):
            self.assertNotIn(interdit, litteraux,
                             f"« {interdit} » doit venir de classification.Type")

    def test_2_aucun_emoji_de_categorie_n_est_ecrit_dans_la_vue(self):
        """Les commentaires ont le droit de les NOMMER pour expliquer la
        règle ; le CODE, lui, ne doit en produire aucun."""
        import ast
        docs = {ast.get_docstring(n, clean=False) for n in ast.walk(self.arbre)
                if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))}
        litteraux = " ".join(
            n.value for n in ast.walk(self.arbre)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value not in docs)
        for emoji in ("🟢", "🟡", "🟣", "🔵", "🔴"):
            self.assertNotIn(emoji, litteraux,
                             "les emojis viennent du moteur, pas de la vue")

    def test_3_aucun_calcul_de_score_dans_la_vue(self):
        """« ─ » * 70 dessine un trait ; ce n'est pas de l'arithmétique.
        Ce qui est interdit, c'est un calcul SUR DES NOMBRES."""
        import ast

        def nombre(n):
            return isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
        calculs = [n for n in ast.walk(self.arbre)
                   if isinstance(n, ast.BinOp)
                   and isinstance(n.op, (ast.Mult, ast.Div, ast.Pow))
                   and (nombre(n.left) and nombre(n.right))]
        self.assertEqual(calculs, [], "un calcul ici serait un second score")

    def test_4_la_vue_ne_parle_jamais_a_la_base(self):
        import ast
        appels = {n.attr for n in ast.walk(self.arbre)
                  if isinstance(n, ast.Attribute)}
        for interdit in ("execute", "commit", "cursor"):
            self.assertNotIn(interdit, appels, interdit)

    def test_5_les_statuts_de_suivi_viennent_du_moteur(self):
        import ast
        docs = {ast.get_docstring(n, clean=False) for n in ast.walk(self.arbre)
                if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))}
        litteraux = [n.value for n in ast.walk(self.arbre)
                     if isinstance(n, ast.Constant) and isinstance(n.value, str)
                     and n.value not in docs]
        for interdit in ("CONTACT À FAIRE", "GAGNÉE", "PERDUE", "ABANDONNÉE"):
            self.assertNotIn(interdit, litteraux,
                             f"« {interdit} » doit venir de suivi.Statut")


if __name__ == "__main__":
    unittest.main()
