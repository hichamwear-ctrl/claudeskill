"""QUATRE DÉFAUTS TROUVÉS PAR UN UTILISATEUR, SUR UN VRAI POSTE WINDOWS.

Aucun de ces quatre-là n'a été trouvé par les tests. Ils ont été trouvés par
quelqu'un qui a ouvert CMD et tapé la première commande du guide. C'est la
seule chose qu'ils ont en commun, et c'est pour cela qu'ils sont réunis ici.

    DÉFAUT 1   « ModuleNotFoundError: No module named 'tzdata' »
               La documentation annonçait « PyYAML, seule dépendance ».
               Windows ne livre aucune base de fuseaux horaires ; le radar
               ne démarrait pas du tout.

    DÉFAUT 2   radar.cmd appelait « python ». Windows 10 et 11 installent un
               FAUX python.exe qui renvoie vers le Microsoft Store. Le
               lanceur le trouvait avec « where » et croyait Python présent.

    DÉFAUT 8   La fiche affichait « aucun changement enregistré » juste après
               que `radar suivre` ait écrit le changement. Le service lisait
               un attribut nommé `depuis` ; `Suivi` l'expose sous le nom
               `statut_maj`. `getattr` avec un défaut ne levait rien.

    DÉFAUT 9   Une commande de lecture sur une base neuve affichait
               « unable to open database file ». Vrai, illisible, et sans
               aucune indication de quoi taper ensuite.

Ce qu'ils enseignent : un test qui n'exécute jamais ce qu'il affirme finit
par affirmer n'importe quoi. La liste des dépendances est donc exécutée, le
lanceur est lu, et le parcours de suivi est rejoué en entier.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from radar.base import BaseAbsente, DossierAbsent, ouvrir          # noqa: E402
from radar.cli import principal                                    # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent
EXPORT = str(RACINE / "validation/exports-reels/2026-09-14-premier-export-reel.tsv")
VERIFICATEUR = RACINE / "outils/verifier_environnement.py"
LANCEUR = RACINE / "radar.cmd"


def _lancer(base, *args):
    sortie, erreur = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(sortie), contextlib.redirect_stderr(erreur):
        code = principal(["--base", str(base), *args])
    return code, sortie.getvalue(), erreur.getvalue()


# ═══════════════════════════════════ DÉFAUT 1 — LES DÉPENDANCES
class Defaut1_LesDependancesSontVerifiees(unittest.TestCase):

    def test_1_requirements_declare_les_deux_paquets(self):
        """Une dépendance non déclarée est une dépendance que l'utilisateur
        découvre à sa place, bloqué, sur un message technique."""
        chemin = RACINE / "requirements.txt"
        self.assertTrue(chemin.exists(), "requirements.txt")
        texte = chemin.read_text(encoding="utf-8").lower()
        lignes = [l.strip() for l in texte.splitlines()
                  if l.strip() and not l.strip().startswith("#")]
        paquets = {l.split(">")[0].split("=")[0].split(";")[0].strip()
                   for l in lignes}
        self.assertIn("pyyaml", paquets)
        self.assertIn("tzdata", paquets)

    def test_2_aucune_documentation_ne_dit_plus_seule_dependance(self):
        """La phrase exacte qui a induit l'utilisateur en erreur."""
        for nom in ("DEMARRER.md", "RECEPTION-COLLECTE.md", "radar.sh"):
            texte = (RACINE / nom).read_text(encoding="utf-8")
            for mensonge in ("seule dépendance", "plus **PyYAML**.",
                             "plus PyYAML."):
                self.assertNotIn(mensonge, texte, f"{nom} : « {mensonge} »")

    def test_3_la_documentation_nomme_tzdata(self):
        texte = (RACINE / "DEMARRER.md").read_text(encoding="utf-8")
        self.assertIn("tzdata", texte)

    def test_4_le_verificateur_dit_oui_dans_cet_environnement(self):
        r = subprocess.run([sys.executable, str(VERIFICATEUR)],
                           capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        self.assertIn("ENVIRONNEMENT COMPLET",
                      r.stdout.decode("utf-8", "replace"))

    def test_5_le_verificateur_repere_un_fuseau_introuvable(self):
        """LA régression du défaut 1 : on rejoue la situation Windows — aucune
        base de fuseaux système, aucun paquet tzdata — et on exige un message
        nommant tzdata, pas un traceback."""
        amorce = (
            "import runpy, sys\n"
            "sys.modules['tzdata'] = None\n"      # importer tzdata lèvera ImportError
            f"runpy.run_path({str(VERIFICATEUR)!r}, run_name='__main__')\n")
        r = subprocess.run([sys.executable, "-c", amorce],
                           capture_output=True,
                           env={"PYTHONTZPATH": "", "PATH": "/usr/bin:/bin"})
        texte = (r.stdout + r.stderr).decode("utf-8", "replace")
        self.assertEqual(r.returncode, 1, texte)
        self.assertIn("tzdata", texte)
        self.assertIn("pip install tzdata", texte)
        self.assertNotIn("Traceback", texte)

    def test_6_le_fuseau_belge_est_un_besoin_reel_pas_un_reglage(self):
        """Interdit de « corriger » tzdata en gelant un décalage : la Belgique
        change d'heure deux fois par an. La preuve, mesurée."""
        from datetime import datetime
        from radar.statut import BRUXELLES
        hiver = datetime(2026, 1, 15, 12, 0, tzinfo=BRUXELLES)
        ete = datetime(2026, 7, 15, 12, 0, tzinfo=BRUXELLES)
        self.assertNotEqual(hiver.utcoffset(), ete.utcoffset(),
                            "un décalage fixe fausserait la moitié de l'année")


# ═══════════════════════════════════ DÉFAUT 2 — LE LANCEUR WINDOWS
class Defaut2_LeLanceurWindowsTrouveUnPython(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.octets = LANCEUR.read_bytes()
        cls.texte = cls.octets.decode("utf-8")
        # Les COMMANDES, pas les commentaires ni les messages affichés. Un
        # test qui cherche dans la prose finit par interdire d'expliquer le
        # défaut qu'on vient de corriger — la leçon a déjà été apprise sur
        # les tests qui lisaient du code source au lieu de le parcourir.
        cls.instructions = [
            l.strip() for l in cls.texte.splitlines()
            if l.strip() and not l.strip().upper().startswith("REM")
            and not l.strip().lower().startswith("echo")]

    def test_1_le_lanceur_nappelle_plus_python_en_dur(self):
        """Le défaut exact : « python -m radar.cli » sur un poste où seul
        « py » existe."""
        for ligne in self.instructions:
            self.assertNotIn("python -m radar.cli", ligne, ligne)
            self.assertNotIn("python3 -m radar.cli", ligne, ligne)

    def test_2_le_lanceur_essaie_py(self):
        self.assertIn("py -3", self.texte)

    def test_3_les_trois_candidats_sont_essayes_dans_cet_ordre(self):
        """« python » d'abord : un environnement virtuel actif doit rester
        celui qu'on utilise. « py » ensuite : il ignore le venv."""
        appels = [l.strip() for l in self.texte.splitlines()
                  if l.strip().lower().startswith(("call :essayer",
                                                   "if not defined radar_python call :essayer"))]
        candidats = [a.split("call :essayer", 1)[1].strip() for a in appels]
        self.assertEqual(candidats, ["python", "py -3", "python3"])

    def test_4_le_choix_se_fait_en_executant_pas_en_interrogeant_le_path(self):
        """« where python » trouve le faux python.exe du Microsoft Store :
        il EXISTE, il ne MARCHE pas. C'est toute la cause du défaut."""
        for ligne in self.instructions:
            self.assertNotIn("where ", ligne, ligne)
        self.assertTrue(any('-c "import sys"' in l for l in self.instructions),
                        "le lanceur doit EXÉCUTER le candidat")

    def test_5_la_sonde_est_reellement_concluante_sur_cette_machine(self):
        """La sonde du lanceur, jouée pour de vrai : un interpréteur valide
        doit la passer. Un test qui ne vérifie que du texte ne prouve rien."""
        r = subprocess.run([sys.executable, "-c", "import sys"],
                           capture_output=True)
        self.assertEqual(r.returncode, 0)

    def test_6_la_sonde_ne_contient_aucun_operateur_de_comparaison(self):
        """Sous CMD, « < » et « > » sont des redirections. Une sonde qui
        compare la version se ferait manger par le shell : la version est
        donc vérifiée en Python, pas dans le batch."""
        for ligne in self.instructions:
            if '-c "' in ligne:
                sonde = ligne.split('-c "', 1)[1].split('"', 1)[0]
                self.assertNotIn(">", sonde, ligne)
                self.assertNotIn("<", sonde, ligne)

    def test_7_le_lanceur_verifie_lenvironnement_avant_de_lancer(self):
        """L'ordre compte : diagnostiquer tzdata AVANT le premier import."""
        self.assertIn("verifier_environnement.py", self.texte)
        avant = self.texte.index("verifier_environnement.py")
        apres = self.texte.index("-m radar.cli %*")
        self.assertLess(avant, apres)

    def test_8_le_lanceur_garde_ses_fins_de_ligne_windows(self):
        """CMD relit un .bat par position d'octet : avec des fins de ligne
        LF, « goto » et « call :label » peuvent se perdre. Le lanceur utilise
        les deux, il lui faut donc des CRLF."""
        self.assertNotIn(b"\r\n", self.octets.replace(b"\r\n", b""))
        lf_nus = self.octets.count(b"\n") - self.octets.count(b"\r\n")
        self.assertEqual(lf_nus, 0, "une ligne du lanceur n'est pas en CRLF")

    def test_9_git_a_interdiction_de_normaliser_le_lanceur(self):
        """Sans cela, la correction précédente ne survit ni au clone ni au ZIP."""
        attributs = (RACINE / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("*.cmd -text", attributs)

    def test_10_le_reglage_dencodage_est_conserve(self):
        """Acquis du cycle précédent : ne pas le reperdre en corrigeant autre
        chose."""
        self.assertIn("PYTHONIOENCODING=utf-8", self.texte)
        self.assertIn("chcp 65001", self.texte)


# ═══════════════════════════════════ DÉFAUT 8 — LE SUIVI SE RELIT
class Defaut8_LaFicheMontreLeChangementDeSuivi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dossier = tempfile.mkdtemp()
        cls.base = str(pathlib.Path(cls.dossier) / "suivi.sqlite3")
        _lancer(cls.base, "analyse-du-jour", "--import", EXPORT, "--top", "0")

    def _fiche(self):
        code, texte, _ = _lancer(self.base, "opportunite", "8", "--json")
        self.assertEqual(code, 0)
        return json.loads(texte)

    def test_1_le_parcours_reel_de_bout_en_bout(self):
        """Exactement ce que l'utilisateur a tapé, et ce qu'il devait voir."""
        avant = self._fiche()
        self.assertEqual(avant["suivi"]["statut"], "NOUVELLE")
        self.assertIsNone(avant["suivi"]["depuis"],
                          "jamais touchée : « depuis » doit rester absent")

        code, _, erreur = _lancer(self.base, "suivre", "colisprive",
                                  "--statut", "CONTACT A FAIRE")
        self.assertEqual(code, 0, erreur)

        apres = self._fiche()
        self.assertEqual(apres["suivi"]["statut"], "CONTACT À FAIRE")
        self.assertIsNotNone(apres["suivi"]["depuis"],
                             "LE défaut 8 : le changement venait d'être écrit")
        self.assertRegex(apres["suivi"]["depuis"], r"^\d{4}-\d{2}-\d{2}")

    def test_2_la_fiche_lisible_ne_dit_plus_aucun_changement(self):
        _lancer(self.base, "suivre", "colisprive", "--statut", "CONTACTÉE")
        code, texte, _ = _lancer(self.base, "opportunite", "8")
        self.assertEqual(code, 0)
        bloc = texte.split("SUIVI COMMERCIAL", 1)[1][:400]
        self.assertIn("CONTACTÉE", bloc)
        self.assertNotIn("aucun changement enregistré", bloc)

    def test_3_une_affaire_jamais_touchee_dit_toujours_labsence(self):
        """La correction ne doit pas remplacer un vide par une date inventée :
        là où rien n'a été fait, le radar doit continuer à le dire."""
        cartes = json.loads(_lancer(self.base, "opportunites", "--tout",
                                    "--limite", "99", "--json")[1])
        intacte = next(c for c in cartes if c["avis_id"] != 8)
        code, texte, _ = _lancer(self.base, "opportunite",
                                 str(intacte["avis_id"]))
        self.assertEqual(code, 0)
        self.assertIn("aucun changement enregistré",
                      texte.split("SUIVI COMMERCIAL", 1)[1])

    def test_4_le_suivi_ne_touche_ni_le_score_ni_la_categorie(self):
        """La garantie métier du cycle précédent, revérifiée : poser un statut
        commercial ne rejuge pas l'affaire."""
        def carte():
            cartes = json.loads(_lancer(self.base, "opportunites", "--tout",
                                        "--limite", "99", "--json")[1])
            return next(c for c in cartes if c["avis_id"] == 8)
        avant = carte()
        _lancer(self.base, "suivre", "colisprive", "--statut", "EN ATTENTE")
        apres = carte()
        self.assertEqual(avant["score"], apres["score"])
        self.assertEqual(avant["categorie"], apres["categorie"])

    def test_5_le_service_lit_le_vrai_nom_de_lattribut(self):
        """La cause, pas seulement le symptôme : `Suivi` n'a pas d'attribut
        `depuis`, et personne ne doit le réintroduire par `getattr`."""
        from radar.suivi import Suivi
        self.assertFalse(hasattr(Suivi(avis_id=1), "depuis"))
        self.assertTrue(hasattr(Suivi(avis_id=1), "statut_maj"))
        # On parcourt l'arbre, on ne fouille pas le texte : un commentaire
        # qui raconte le défaut ne doit pas déclencher son propre test.
        arbre = ast.parse((RACINE / "radar/service.py").read_text(encoding="utf-8"))
        fautifs = [n for n in ast.walk(arbre)
                   if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name) and n.func.id == "getattr"
                   and len(n.args) >= 2
                   and isinstance(n.args[1], ast.Constant)
                   and n.args[1].value == "depuis"]
        self.assertEqual(fautifs, [],
                         "« depuis » n'est pas un attribut de Suivi ; "
                         "getattr avec un défaut masquerait de nouveau l'erreur")

    def test_6_nouvelle_est_une_reponse_calculee_pas_une_exception(self):
        """TROUVÉ EN CORRIGEANT LE DÉFAUT 8, et c'est la vraie leçon.

        `_suivi_de` était protégé par `except Exception`. En le resserrant,
        31 tests ont cassé d'un coup : « NOUVELLE » ne sortait pas d'une
        règle, il sortait d'un `AttributeError` — `s.statut.value` sur None,
        attrapé au vol. La bonne réponse, pour une mauvaise raison.

        Ce test exige que la réponse reste bonne SANS filet : on appelle
        directement, sur une opportunité jamais regardée.
        """
        from radar import service
        from radar.base import ouvrir
        cx = ouvrir(self.base, lecture_seule=True)
        jamais = cx.execute(
            "SELECT avis_id FROM opportunites WHERE etat IS NULL OR etat=''"
            " OR etat='non_vu' LIMIT 1").fetchone()
        self.assertIsNotNone(jamais, "il faut une affaire jamais regardée")
        vu = service._suivi_de(cx, jamais["avis_id"])
        self.assertEqual(vu["statut"], "NOUVELLE")
        self.assertIsNone(vu["depuis"])

    def test_7_le_filet_de_suivi_ne_rattrape_plus_tout(self):
        """Un `except Exception` transforme n'importe quelle faute en
        « NOUVELLE ». C'est ce qui a caché le défaut 8 pendant tout un cycle."""
        arbre = ast.parse((RACINE / "radar/service.py").read_text(encoding="utf-8"))
        fonction = next(n for n in ast.walk(arbre)
                        if isinstance(n, ast.FunctionDef)
                        and n.name == "_suivi_de")
        for garde in [n for n in ast.walk(fonction)
                      if isinstance(n, ast.ExceptHandler)]:
            noms = [d.id for d in ast.walk(garde.type or ast.Pass())
                    if isinstance(d, ast.Name)]
            self.assertNotIn("Exception", noms,
                             "trop large : une faute d'attribut y disparaîtrait")
            self.assertNotIn("BaseException", noms)


# ═══════════════════════════════════ DÉFAUT 9 — LA BASE ABSENTE
class Defaut9_UneBaseAbsenteSeDitEnClair(unittest.TestCase):

    LECTURES = ("signaux", "opportunites", "entreprises", "suivi",
                "notifications", "sources", "tableau")

    def setUp(self):
        self.dossier = pathlib.Path(tempfile.mkdtemp())
        self.base = self.dossier / "radar.sqlite3"

    def test_1_chaque_commande_de_lecture_dit_quoi_taper(self):
        """Le message que l'utilisateur a vu sept fois de suite, remplacé."""
        for commande in self.LECTURES:
            with self.subTest(commande=commande):
                code, _, erreur = _lancer(self.base, commande)
                self.assertEqual(code, 2, commande)
                self.assertNotIn("unable to open database file", erreur)
                self.assertNotIn("Traceback", erreur)
                self.assertIn("analyse-du-jour", erreur)
                self.assertIn("n'existe pas encore", erreur)

    def test_2_rien_nest_cree_en_douce(self):
        """Une base vide répondrait « 0 signal » là où la vérité est
        « aucune analyse ». C'est la confusion que le radar refuse partout."""
        _lancer(self.base, "signaux")
        self.assertFalse(self.base.exists(),
                         "une lecture ne crée pas de base, même vide")

    def test_3_un_dossier_absent_est_distingue_dune_base_absente(self):
        """Deux causes, deux messages : « unable to open database file » les
        confondait."""
        code, _, erreur = _lancer(self.dossier / "nulle-part" / "r.sqlite3",
                                  "statut")
        self.assertEqual(code, 2)
        self.assertIn("dossier", erreur)
        self.assertNotIn("unable to open database file", erreur)

    def test_4_apres_lanalyse_les_memes_commandes_repondent(self):
        """L'objectif de l'utilisateur : le parcours complet, sur base neuve."""
        code, _, erreur = _lancer(self.base, "analyse-du-jour",
                                  "--import", EXPORT, "--top", "0")
        self.assertEqual(code, 0, erreur)
        for commande in self.LECTURES:
            with self.subTest(commande=commande):
                self.assertEqual(_lancer(self.base, commande)[0], 0, commande)

    def test_5_une_commande_decriture_cree_la_base_complete(self):
        """Le comportement voulu, et il est déterministe : écrire crée et
        installe le schéma ; lire ne crée jamais."""
        code, _, _ = _lancer(self.base, "statut")
        self.assertEqual(code, 0)
        self.assertTrue(self.base.exists())
        cx = ouvrir(str(self.base), lecture_seule=True)
        tables = {l["name"] for l in cx.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for attendue in ("avis", "reponses", "opportunites", "entreprises"):
            self.assertIn(attendue, tables)

    def test_6_les_deux_causes_ont_des_exceptions_distinctes(self):
        with self.assertRaises(BaseAbsente):
            ouvrir(str(self.base), lecture_seule=True)
        with self.assertRaises(DossierAbsent):
            ouvrir(str(self.dossier / "nulle-part" / "r.sqlite3"))

    def test_7_les_bases_sans_fichier_restent_intactes(self):
        """`:memory:` est utilisé par les tests et par les outils d'audit :
        la vérification de présence n'a pas le droit de les casser."""
        cx = ouvrir(":memory:")
        self.assertEqual(cx.execute("SELECT 1").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
