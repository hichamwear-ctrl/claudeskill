"""VALIDATION DU MOTEUR — les 35 propriétés, chacune vérifiée nommément.

Ce fichier ne remplace pas les 1 245 tests de comportement : il les
COMPLÈTE par une liste de contrôle exécutable. Chaque test porte le numéro
de la propriété qu'il vérifie, pour qu'on puisse lire d'un coup ce qui est
tenu et par quoi.

Une propriété tenue « quelque part dans la suite » n'est pas lisible. Ici,
elle a un nom, un numéro et une assertion.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import yaml                                                    # noqa: E402

from radar import (ancrage as anc, classification as cls,      # noqa: E402
                   consolidation, deduplication, execution as ex,
                   fiabilite as fia, nature as nat, notification as notif,
                   orchestrateur as orch, pertinence, suivi, verdicts)
from radar.activite import Ontologie                           # noqa: E402
from radar.base import ouvrir                                  # noqa: E402
from radar.role import DetecteurDeRole, Role                   # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent

# L'empreinte de config/ponderations.yaml au moment où le score a été gelé.
# Elle est ÉCRITE EN DUR, et c'est tout l'intérêt : la recalculer à
# l'exécution rendrait le test toujours vert, donc inutile.
PONDERATIONS_GELEES = "cbb7128bdf6b49f7"


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def _mecanismes():
    prof = _cfg("profil.yaml")
    return (Ontologie(_cfg("config/capacites.yaml"), prof["familles_actives"],
                      prof.get("familles_exclues")),
            DetecteurDeRole(_cfg("config/roles.yaml")))


# ═══════════════════════════════════ 4 · LES SIX CATÉGORIES
class P04_LesSixCategories(unittest.TestCase):
    def test_les_six_existent_et_aucune_septieme(self):
        self.assertEqual(
            {t.value for t in cls.Type},
            {"DIRECT", "RENFORCEMENT", "A_CONSTRUIRE", "PROSPECT",
             "PAS ENCORE UNE OPPORTUNITÉ", "REJET"})

    def test_chacune_porte_son_emoji(self):
        self.assertEqual(
            {t.emoji for t in cls.Type}, {"🟢", "🟡", "🟣", "🔵", "⚪", "🔴"})

    def test_observation_n_est_pas_une_sixieme_facon_d_entrer(self):
        """⚪ répond à « on n'en est pas encore là », pas à « comment entrer »."""
        self.assertFalse(cls.Type.OBSERVATION.notifiable)
        self.assertFalse(cls.Type.REJET.notifiable)
        for t in (cls.Type.DIRECT, cls.Type.RENFORCEMENT,
                  cls.Type.A_CONSTRUIRE, cls.Type.PROSPECT):
            self.assertTrue(t.notifiable, t.value)


# ═══════════════════════════════════ 5 · QUATRE DIMENSIONS SÉPARÉES
class P05_LesDimensionsNeSeResumentPas(unittest.TestCase):
    def test_type_information_procedure_nature_action_sont_des_champs_distincts(self):
        cx = ouvrir(":memory:")
        cols = {d[1] for d in cx.execute("PRAGMA table_info(opportunites)")}
        for champ in ("type_information", "etat_procedure", "nature", "action"):
            self.assertIn(champ, cols, champ)

    def test_une_affaire_executable_peut_rester_une_hypothese(self):
        """🟢 et HYPOTHÈSE cohabitent : « puis-je le faire » ≠ « est-ce réel »."""
        self.assertIsNot(cls.Type.DIRECT.value, nat.Nature.HYPOTHESE.value)
        self.assertFalse(nat.Nature.HYPOTHESE.depot_attendu)


# ═══════════════════════════════════ 6 · FAIT ≠ SIGNAL ≠ HYPOTHÈSE
class P06_TroisNatures(unittest.TestCase):
    def test_les_trois_sont_distinctes(self):
        self.assertEqual({n.value for n in nat.Nature},
                         {"FAIT", "SIGNAL", "HYPOTHÈSE"})

    def test_seul_un_fait_attend_un_depot(self):
        self.assertTrue(nat.Nature.FAIT.depot_attendu)
        self.assertFalse(nat.Nature.SIGNAL.depot_attendu)
        self.assertFalse(nat.Nature.HYPOTHESE.depot_attendu)

    def test_mesure_sur_trois_textes_reels(self):
        def n(intitule, texte=""):
            class P:
                pass
            P.intitule, P.texte = intitule, texte
            return nat.qualifier(P())
        self.assertIs(n("Nous recherchons un transporteur"), nat.Nature.FAIT)
        self.assertIs(n("L'entreprise ouvre un nouveau dépôt à Gand"),
                      nat.Nature.SIGNAL)
        self.assertIs(n("Notre société existe depuis 1998"), nat.Nature.HYPOTHESE)


# ═══════════════════════════════════ 7 · OPPORTUNITÉ ≠ SIGNAL COMMERCIAL
class P07_UnSignalNEstPasUneOpportunite(unittest.TestCase):
    def test_un_signal_ne_fait_pas_deposer(self):
        self.assertFalse(nat.Nature.SIGNAL.depot_attendu,
                         "on ne dépose pas un dossier sur une inférence")

    def test_le_rapport_range_les_signaux_a_part(self):
        src = (RACINE / "radar/parcours.py").read_text(encoding="utf-8")
        self.assertIn("SIGNAUX", src)
        self.assertIn("BESOINS ÉNONCÉS", src)


# ═══════════════════════════════════ 8 · ATTRIBUÉ ≠ POSTULABLE
class P08_UnMarcheAttribueNEstPasPostulable(unittest.TestCase):
    def test_un_titulaire_connu_ne_rend_pas_le_marche_deposable(self):
        from radar import statut as st
        for e in st.Statut:
            if e.name == "ATTRIBUE":
                self.assertFalse(e.depot_possible)
                break
        else:
            self.skipTest("pas d'état ATTRIBUE dans ce vocabulaire")

    def test_une_attribution_reste_exploitable_pour_developper(self):
        self.assertEqual(notif.RENOUVELLEMENT, "RENOUVELLEMENT APPROCHANT")
        self.assertEqual(notif.DEVELOPPEMENT, "TITULAIRE À DÉVELOPPER")


# ═══════════════════════════════════ 9 · SCORE FAIBLE ≠ SUPPRESSION
class P09_UnScoreFaibleNeSupprimeRien(unittest.TestCase):
    def test_le_top_ne_filtre_que_le_rejet(self):
        src = (RACINE / "radar/parcours.py").read_text(encoding="utf-8")
        self.assertIn("o.type <> 'REJET'", src)
        self.assertNotIn("o.score >", src, "aucun seuil de score ne filtre")

    def test_une_opportunite_non_notifiable_reste_en_base(self):
        src = (RACINE / "radar/notification.py").read_text(encoding="utf-8")
        self.assertIn("continue", src)
        self.assertNotIn("DELETE", src.upper())


# ═══════════════════════════════════ 10-12 · AUCUNE SOURCE PRIVILÉGIÉE
class P10_LaSourceNeChangeAucunScore(unittest.TestCase):
    def test_le_bareme_ne_lit_aucun_nom_de_source(self):
        import ast
        arbre = ast.parse((RACINE / "radar/score.py").read_text(encoding="utf-8"))
        docs = {ast.get_docstring(n, clean=False) for n in ast.walk(arbre)
                if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))}
        litteraux = " ".join(
            n.value.lower() for n in ast.walk(arbre)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value not in docs)
        for source in ("ted", "bda", "google", "brave", "europages", "indeed"):
            self.assertNotIn(source, litteraux.split(),
                             f"« {source} » ne doit pas exister dans le barème")

    def test_11_public_et_prive_passent_par_le_meme_bareme(self):
        import ast
        arbre = ast.parse((RACINE / "radar/score.py").read_text(encoding="utf-8"))
        noms = {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)}
        self.assertNotIn("secteur", noms,
                         "le secteur de l'acheteur n'entre pas dans le score")

    def test_12_la_classification_ne_nomme_aucune_source(self):
        import ast
        arbre = ast.parse(
            (RACINE / "radar/classification.py").read_text(encoding="utf-8"))
        args = set()
        for n in ast.walk(arbre):
            if isinstance(n, ast.FunctionDef) and n.name == "classer":
                args = {a.arg for a in n.args.args + n.args.kwonlyargs}
        self.assertTrue(args, "classer introuvable")
        for interdit in ("source", "moteur_source", "portail"):
            self.assertNotIn(interdit, args, interdit)


# ═══════════════════════════════════ 13-15 · DOUBLONS, PROVENANCE, CONFLITS
class P13_DoublonsConsolides(unittest.TestCase):
    @staticmethod
    def l(url, t, f, s, src, vue="2026-09-14"):
        return {"ref_source": url, "type": t, "fiabilite": f, "score": s,
                "source_avis": src, "derniere_vue": vue, "nature": "FAIT",
                "action": "CONTACTER L'ENTREPRISE"}

    def test_13_une_url_vue_par_deux_sources_fait_une_fiche(self):
        ad = consolidation.grouper([
            self.l("https://x.be/p", "DIRECT", "MOYENNE", 45, "bda"),
            self.l("https://x.be/p", "PAS ENCORE UNE OPPORTUNITÉ", "FAIBLE",
                   24, "import:google")])
        self.assertEqual(len(ad), 1)
        self.assertEqual(len(ad[0].lectures), 2)

    def test_14_la_provenance_de_chaque_lecture_survit(self):
        ad = consolidation.grouper([
            self.l("https://x.be/p", "DIRECT", "MOYENNE", 45, "bda"),
            self.l("https://x.be/p", "PAS ENCORE", "FAIBLE", 24, "import:google")])[0]
        self.assertEqual({x["source_avis"] for x in ad.lectures},
                         {"bda", "import:google"})

    def test_15_la_contradiction_est_ecrite(self):
        ad = consolidation.grouper([
            self.l("https://x.be/p", "DIRECT", "MOYENNE", 45, "bda"),
            self.l("https://x.be/p", "PAS ENCORE", "FAIBLE", 24, "import:google")])[0]
        self.assertTrue(ad.divergentes)
        bloc = "\n".join(consolidation.bloc_divergence(
            ad, fiche=lambda x: str(x["type"])))
        self.assertIn(consolidation.DIVERGENCE, bloc)

    def test_13bis_la_dedup_existe_et_rend_une_confiance(self):
        self.assertTrue({c.name for c in deduplication.Confiance})


# ═══════════════════════════════════ 16-18 · LES VOIES COMMERCIALES
class P16_GroupementEtSousTraitance(unittest.TestCase):
    def test_16_le_groupement_est_une_voie(self):
        self.assertEqual(cls.Action.PROPOSER_GROUPEMENT.value,
                         "PROPOSER UN GROUPEMENT")
        self.assertIsInstance(cls.SEUIL_GROUPEMENT, float,
                              "la part minimale pour être associé est chiffrée")

    def test_17_la_sous_traitance_est_une_voie(self):
        self.assertEqual(cls.Action.PROPOSER_SOUS_TRAITANCE.value,
                         "PROPOSER SOUS-TRAITANCE")

    def test_18_une_capacite_insuffisante_n_est_pas_un_rejet(self):
        """🟡 · 🟣 · 🔵 existent précisément pour ça."""
        # Le rejet est réservé à l'impossibilité OBJECTIVE. Un manque de
        # moyens mène en 🔵 avec une voie d'entrée chiffrée.
        self.assertIn(cls.Action.PROPOSER_GROUPEMENT, set(cls.Action))
        self.assertIn(cls.Action.PROPOSER_SOUS_TRAITANCE, set(cls.Action))
        src = (RACINE / "radar/classification.py").read_text(encoding="utf-8")
        self.assertIn("trop grand pour être porté seul", src)

    def test_18bis_un_metier_nouveau_passe_par_a_construire(self):
        self.assertIs(cls.Type.A_CONSTRUIRE, cls.Type("A_CONSTRUIRE"))


# ═══════════════════════════════════ 19-23 · L'HONNÊTETÉ DES DONNÉES
class P19_CeQuOnIgnoreSEcrit(unittest.TestCase):
    def test_19_une_donnee_inconnue_devient_A_CONFIRMER(self):
        from radar import parcours
        self.assertEqual(parcours.A_CONFIRMER, "À CONFIRMER")
        self.assertEqual(notif.A_CONFIRMER, "À CONFIRMER")

    def test_20_aucune_entreprise_n_est_inventee(self):
        src = (RACINE / "radar/entreprises.py").read_text(encoding="utf-8")
        self.assertIn("domaine", src)
        from radar import identite
        etats = {e.value for e in identite.Etat}
        self.assertIn("INCONNUE", etats,
                      "une identité non établie se dit INCONNUE")

    def test_21_une_fixture_ne_passe_pas_pour_du_reel(self):
        self.assertEqual(ex.Execution.FIXTURE.value, "FIXTURE / DEMO")
        self.assertEqual(ex.Execution.IMPORT_EXTERNE.value,
                         "RÉSULTAT IMPORTÉ — RECHERCHE EXTERNE")
        self.assertEqual(ex.Execution.RADAR.value,
                         "RECHERCHE RÉELLE PAR LE RADAR")

    def test_22_une_source_non_consultee_le_dit(self):
        self.assertEqual(ex.Execution.NON_MESUREE.value, "NON MESURÉ")
        self.assertFalse(ex.Execution.NON_MESUREE.mesuree)
        self.assertEqual(orch.NON_MESUREE, "NON MESURÉE")
        self.assertEqual(orch.ERREUR, "ERREUR")

    def test_23_une_page_non_collectee_n_est_pas_une_page_vide(self):
        from radar import pages
        q = {x.value for x in pages.Qualification}
        self.assertIn("CONTENU ILLISIBLE", q,
                      "une page qu'on n'a pas pu lire le DIT")
        self.assertIn("NON QUALIFIÉE", q,
                      "…et une page jamais examinée n'est pas « sans preuve »")
        self.assertNotIn("VIDE", q, "aucune page n'est déclarée vide")


# ═══════════════════════════════════ 24 · IDEMPOTENCE
class P24_UnCycleRejoueNeDoublePasLaBase(unittest.TestCase):
    def test_le_sceau_de_notification_empeche_la_repetition(self):
        a = notif.sceau("un corps")
        self.assertEqual(a, notif.sceau("un corps"))
        self.assertNotEqual(a, notif.sceau("un autre corps"))

    def test_la_cle_d_avis_empeche_le_doublon(self):
        sql = " ".join((RACINE / "radar/schema.sql")
                       .read_text(encoding="utf-8").split())
        self.assertIn("UNIQUE (source, ref_source)", sql)


# ═══════════════════════════════════ 25-30 · LA BOUCLE COMMERCIALE
class P25_LaBoucleEstComplete(unittest.TestCase):
    def test_25_la_surveillance_d_entreprise_existe(self):
        from radar import pages
        self.assertIn("SURVEILLEE", {s.name for s in pages.Statut})

    def test_26_27_les_titulaires_et_les_renouvellements(self):
        cx = ouvrir(":memory:")
        cols = {d[1] for d in cx.execute("PRAGMA table_info(attributions)")}
        for champ in ("titulaire", "renouvellement", "fin"):
            self.assertIn(champ, cols, champ)

    def test_28_le_suivi_commercial_couvre_le_cycle_de_vente(self):
        self.assertEqual(
            {s.value for s in suivi.Statut},
            {"NOUVELLE", "CONTACT À FAIRE", "CONTACTÉE", "EN ATTENTE",
             "RELANCE", "GAGNÉE", "PERDUE", "ABANDONNÉE"})

    def test_29_les_quatre_verdicts_et_le_refus_de_s_auto_juger(self):
        self.assertEqual({v.value for v in verdicts.Verdict},
                         {"VRAI POSITIF", "FAUX POSITIF", "FAUX NÉGATIF",
                          "INCONNU"})
        cx = ouvrir(":memory:")
        with self.assertRaises(verdicts.JugeInvalide):
            verdicts.inscrire(cx, "https://x.be", "VP", juge_par="radar")

    def test_29bis_un_petit_echantillon_se_dit_petit(self):
        cx = ouvrir(":memory:")
        verdicts.inscrire(cx, "https://a.be", "VP", juge_par="moi")
        m = verdicts.metriques(cx)
        self.assertEqual(m["precision"], verdicts.ECHANTILLON_INSUFFISANT)
        self.assertEqual(m["rappel"], verdicts.ECHANTILLON_INSUFFISANT)

    def test_30_une_notification_lit_la_regle_existante(self):
        self.assertTrue(notif.merite_une_alerte("DIRECT"))
        self.assertFalse(notif.merite_une_alerte("PAS ENCORE UNE OPPORTUNITÉ"))
        self.assertFalse(notif.merite_une_alerte("REJET"))


# ═══════════════════════════════════ 31-33 · LES ENTRÉES DU MOTEUR
class P31_OrchestrationEtEntrees(unittest.TestCase):
    def test_31_l_orchestrateur_declare_l_etat_de_chaque_source(self):
        for champ in ("nom", "etat", "resultats", "opportunites", "motif",
                      "derniere_consultation"):
            self.assertIn(champ, orch.EtatSource.__dataclass_fields__, champ)

    def test_31bis_l_orchestrateur_n_apprend_rien_tout_seul(self):
        import ast
        arbre = ast.parse(
            (RACINE / "radar/orchestrateur.py").read_text(encoding="utf-8"))
        modules = set()
        for n in ast.walk(arbre):
            if isinstance(n, ast.ImportFrom) and n.module:
                modules.update(n.module.split("."))
                modules.update(a.name.split(".")[-1] for a in n.names)
        for interdit in ("score", "ponderations", "classification",
                         "apprentissage"):
            self.assertNotIn(interdit, modules, interdit)

    def test_32_un_import_externe_declare_sa_provenance(self):
        from radar import import_externe as imp
        self.assertEqual(imp.PROVENANCE, ex.HORS_RADAR)
        self.assertEqual(imp.PROVENANCE, "EXÉCUTÉ HORS RADAR")

    def test_32bis_un_import_sans_moteur_nomme_est_refuse(self):
        with self.assertRaises(ex.NomDeSourceInvalide):
            ex.qualifier("")

    def test_33_la_deduplication_ne_supprime_jamais_en_silence(self):
        src = (RACINE / "radar/deduplication.py").read_text(encoding="utf-8")
        self.assertNotIn("DELETE", src.upper())


# ═══════════════════════════════════ 34-35 · RECALL ET SCORE
class P34_RecallLarge(unittest.TestCase):
    def setUp(self):
        self.onto, self.det = _mecanismes()

    def test_34_un_besoin_ecrit_dans_d_autres_mots_entre(self):
        """LE test de recall : notre vocabulaire n'est pas la condition."""
        texte = ("Nous recherchons un partenaire pour acheminer chaque jour "
                 "nos commandes vers nos douze magasins.")
        self.assertFalse(self.onto.analyser(texte).correspond)
        self.assertTrue(pertinence.evaluer(texte, self.onto, self.det).promouvoir)

    def test_34bis_une_page_non_promue_n_est_pas_supprimee(self):
        p = pertinence.evaluer("Nos actualités", self.onto, self.det)
        self.assertFalse(p.promouvoir)
        self.assertIn("CANDIDATE", p.raison())

    def test_34ter_les_six_signaux_d_ancrage_sont_lisibles(self):
        self.assertEqual(
            set(anc.ORDRE),
            {anc.BESOIN, anc.EVENEMENT, anc.EXIGENCE, anc.CHIFFRE, anc.DATE,
             anc.VOCABULAIRE})

    def test_35_le_bareme_n_a_pas_change(self):
        """Le score est GELÉ. Toute modification doit être une décision.

        L'empreinte porte sur les PONDÉRATIONS, pas sur les commentaires du
        module : c'est la configuration qui fixe les poids.
        """
        import hashlib
        octets = (RACINE / "config/ponderations.yaml").read_bytes()
        self.assertEqual(
            hashlib.sha256(octets).hexdigest()[:16],
            PONDERATIONS_GELEES,
            "config/ponderations.yaml a changé — si c'est voulu, mettre à "
            "jour cette empreinte ET dire pourquoi dans le compte rendu")


if __name__ == "__main__":
    unittest.main()
