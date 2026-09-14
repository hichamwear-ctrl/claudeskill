"""LA CHAÎNE DE BOUT EN BOUT — d'un export externe jusqu'à une action.

    EXPORT EXTERNE → IMPORT → TROUVAILLES → DÉDUPLICATION → ENTREPRISE
                   → CANDIDATE → ANALYSE → OPPORTUNITÉ → 🟢🟡🟣🔵🔴 → ACTION

DONNÉES RÉELLES : NON MESURÉES. Tous les exports de ces tests sont FABRIQUÉS
en mémoire. Aucun moteur n'a été interrogé, aucun réseau n'a été touché,
aucune clé n'a été utilisée. Ces tests éprouvent un MÉCANISME ; ils ne disent
rien du marché belge.
"""

import json
import pathlib
import tempfile
import unittest

from radar import (execution as ex, import_externe as imp, pages as mod_pages,
                   parcours, trouvailles as tr)
from radar.base import ouvrir
from radar.cli import _cfg, _moteur, _source, principal
from radar.mode import Mode

HORS = imp.PROVENANCE
RACINE = pathlib.Path(__file__).resolve().parent.parent


def export(resultats, *, moteur="moteur-x", date="2026-09-13T09:00:00+00:00",
           provenance=HORS, suffixe=".json"):
    """Un export FABRIQUÉ. Aucun moteur ne l'a produit."""
    charge = {"provenance": provenance, "moteur": moteur,
              "date_execution": date, "resultats": resultats}
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / ("export" + suffixe)
    p.write_text(json.dumps(charge, ensure_ascii=False), encoding="utf-8")
    return str(p)


def besoin(url, titre, extrait, *, requete="recherche transporteur Belgique",
           rang=1):
    return {"requete": requete, "url": url, "titre": titre,
            "extrait": extrait, "rang": rang}


class Chaine(unittest.TestCase):
    """Le socle : un import, toute la chaîne, une base neuve à chaque fois."""

    def setUp(self):
        self.cx = ouvrir(":memory:")
        self.adaptateur, self.cfg = _source("recherche")

    def passer(self, chemin, *, mode=Mode.REEL):
        imp.importer(self.cx, chemin)
        return parcours.executer(
            self.cx, _moteur(self.cx), self.adaptateur, mode=mode,
            defauts={"signal": self.cfg.get("signal"),
                     "secteur": self.cfg.get("secteur_par_defaut")})


# ═══════════════════════════════════════════════ la chaîne complète
class A_DeLExportJusquALAction(Chaine):

    def test_1_un_export_traverse_toute_la_chaine(self):
        p = self.passer(export([
            besoin("https://transporteur.example/partenaires",
                   "Nous recherchons des partenaires de livraison",
                   "Réseau en Wallonie. Sous-traitants avec utilitaires.")]))
        self.assertEqual(p.resultats, 1)
        self.assertEqual(p.urls_uniques, 1)
        self.assertEqual(p.entreprises_decouvertes, 1)
        self.assertEqual(p.pages_candidates, 1)
        self.assertEqual(p.besoins, 1)
        self.assertEqual(p.opportunites, 1)
        self.assertGreaterEqual(p.retenues + p.rejet, 1)
        self.assertTrue(parcours.top_opportunites(self.cx) or p.rejet)

    def test_2_le_rapport_porte_les_comptes_demandes(self):
        p = self.passer(export([
            besoin("https://a.example/x", "Recherche transporteur", "…"),
            besoin("https://b.example/y", "Partenaire livraison", "…",
                   requete="partenaire livraison Belgique")]))
        texte = parcours.rapport(self.cx, p)
        for attendu in ("ENTONNOIR", "RAPPEL", "IDENTIFICATION", "PAGES",
                        "COMMERCIAL — catégories", "COMMERCIAL — actions",
                        "TOP OPPORTUNITÉS COMMERCIALES", "🟢", "🟡", "🟣",
                        "🔵", "🔴", "requêtes contributrices",
                        "vues par PLUSIEURS sources"):
            self.assertIn(attendu, texte, attendu)

    def test_3_les_douze_elements_de_chaque_fiche(self):
        self.passer(export([
            besoin("https://transporteur.example/partenaires",
                   "Nous recherchons un transporteur",
                   "Tournées quotidiennes à assurer en Brabant.")]))
        lignes = parcours.top_opportunites(self.cx)
        self.assertTrue(lignes, "aucune opportunité à décrire")
        fiche = "\n".join(parcours.fiche_courte(self.cx, lignes[0]))
        for element in ("ENTREPRISE", "BESOIN", "SOURCE", "PREUVE", "NATURE",
                        "ÉTAT", "CATÉGORIE", "ACTION", "ZONE", "EFFORT",
                        "MANQUE", "CLASSÉ AINSI", "TYPE D'INFO"):
            self.assertIn(element, fiche, element)

    def test_4_les_quatre_dimensions_restent_separees(self):
        """TYPE D'INFORMATION, NATURE, ÉTAT et ACTION ne se résument pas."""
        self.passer(export([
            besoin("https://x.example/a", "Recherche sous-traitant", "…")]))
        l = parcours.top_opportunites(self.cx)[0]
        self.assertIsNotNone(l["nature"])
        self.assertIsNotNone(l["etat_procedure"])
        self.assertIsNotNone(l["action"])
        self.assertIsNotNone(l["type"])
        # Aucune des quatre n'est recopiée d'une autre.
        self.assertNotEqual(l["nature"], l["etat_procedure"])
        self.assertNotEqual(l["action"], l["type"])


# ═══════════════════════════════════════════════ ce que l'import ne fait pas
class B_AucuneInventionAucunRaccourci(Chaine):

    def test_1_aucune_page_n_est_lue_ni_surveillee_d_office(self):
        p = self.passer(export([
            besoin("https://x.example/a", "Recherche transporteur", "…")]))
        self.assertEqual(p.pages_collectees, 0)
        self.assertEqual(p.pages_surveillees, 0)
        self.assertEqual(p.qualifications_positives, 0)
        for page in mod_pages.a_surveiller(self.cx, toutes=True):
            self.assertIs(page.acces, mod_pages.Acces.JAMAIS_CONSULTEE)
            self.assertIs(page.qualification,
                          mod_pages.Qualification.NON_QUALIFIEE)

    def test_2_le_rapport_dit_qu_aucune_page_n_a_ete_lue(self):
        p = self.passer(export([besoin("https://x.example/a", "T", "E")]))
        self.assertIn("AUCUNE PAGE N'A ÉTÉ LUE", parcours.rapport(self.cx, p))

    def test_3_aucune_identite_n_est_inventee(self):
        """Un article de presse n'est pas l'entreprise dont il parle."""
        from radar import identite
        self.passer(export([
            besoin("https://presse.example/actu/depot",
                   "Fictif SA ouvre un dépôt à Gand",
                   "L'entreprise annonce une plateforme de tri.")]))
        from radar.entreprises import charger
        for cle in charger(self.cx).entreprises:
            self.assertNotIn("Fictif", cle)
            self.assertIsNot(identite.lire(self.cx, cle).etat,
                             identite.Etat.CONFIRMEE)

    def test_4_aucun_chiffre_absent_n_est_fabrique(self):
        self.passer(export([
            besoin("https://x.example/a", "Recherche transporteur",
                   "Nous cherchons un partenaire.")]))
        l = parcours.top_opportunites(self.cx)[0]
        for colonne in ("montant", "duree_mois", "echeance", "ca_mensuel",
                        "ca_annuel", "contact"):
            self.assertIn(l[colonne], (None, "", 0, 0.0), colonne)
        self.assertIn("NON MESURÉE", str(l["marge"]))

    def test_5_le_rapport_ecrit_A_CONFIRMER_et_non_un_tiret(self):
        p = self.passer(export([besoin("https://x.example/a", "T", "E")]))
        texte = parcours.rapport(self.cx, p)
        self.assertIn(parcours.A_CONFIRMER, texte)
        self.assertIn("NON MESURÉE", texte)

    def test_6_une_liste_vide_se_dit_au_lieu_de_s_afficher_crument(self):
        self.assertEqual(parcours._liste("[]", "rien"), "rien")
        self.assertEqual(parcours._liste(None, "rien"), "rien")
        self.assertIn("a", parcours._liste('["a"]', "rien"))


# ═══════════════════════════════════════════════ déduplication et provenance
class C_PlusieursMoteursUnSeulBesoin(Chaine):

    def test_1_la_meme_url_par_deux_moteurs_fait_deux_observations(self):
        imp.importer(self.cx, export(
            [besoin("https://x.example/a", "Société X recherche transporteur",
                    "…", rang=1)], moteur="moteur-a"))
        p = self.passer(export(
            [besoin("https://x.example/a",
                    "Société X cherche sous-traitant livraison", "…", rang=4)],
            moteur="moteur-b"))
        self.assertEqual(p.resultats, 2)
        self.assertEqual(p.urls_uniques, 1)
        self.assertEqual(p.multi_sources, 1)
        self.assertEqual(len(p.sources), 2)

    def test_2_l_historique_de_decouverte_est_conserve(self):
        from radar import recoupement
        imp.importer(self.cx, export([besoin("https://x.example/a", "T", "E")],
                                     moteur="moteur-a"))
        imp.importer(self.cx, export([besoin("https://x.example/a", "T", "E")],
                                     moteur="moteur-b"))
        g, = recoupement.grouper(tr.toutes(self.cx))
        historique = " ".join(g.historique())
        self.assertIn("import:moteur-a", historique)
        self.assertIn("import:moteur-b", historique)

    def test_3_aucune_fusion_sur_simple_vocabulaire(self):
        """Deux pages différentes, mots voisins : DEUX affaires, pas une."""
        p = self.passer(export([
            besoin("https://a.example/1", "Distribution de colis à Namur",
                   "Recherche sous-traitant."),
            besoin("https://b.example/2", "Distribution de colis à Liège",
                   "Recherche sous-traitant.")]))
        self.assertEqual(p.urls_uniques, 2)
        self.assertGreaterEqual(p.opportunites, 2,
                                "deux besoins distincts n'ont pas à fusionner")

    def test_4_reimporter_le_meme_fichier_ne_duplique_rien(self):
        chemin = export([besoin("https://x.example/a", "T", "E")])
        self.passer(chemin)
        avant = self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        p = self.passer(chemin)
        self.assertEqual(p.opportunites, avant)


# ═══════════════════════════════════════════════ jamais une recherche du radar
class D_UnImportNEstJamaisUneRechercheDuRadar(Chaine):

    def test_1_la_provenance_survit_a_toute_la_chaine(self):
        self.passer(export([besoin("https://x.example/a", "T", "E")],
                           moteur="moteur-x"))
        l = parcours.top_opportunites(self.cx)[0]
        self.assertEqual(l["source_avis"], "import:moteur-x")
        self.assertTrue(ex.est_import(l["source_avis"]))

    def test_2_la_date_d_execution_declaree_est_conservee(self):
        self.passer(export([besoin("https://x.example/a", "T", "E")],
                           date="2026-09-01T08:00:00+00:00"))
        l, = ex.executions(self.cx)
        self.assertEqual(l.date_execution, "2026-09-01T08:00:00+00:00")
        self.assertEqual(l.execution_par, HORS)

    def test_3_le_radar_reste_a_zero_recherche_executee(self):
        p = self.passer(export([besoin("https://x.example/a", "T", "E")]))
        self.assertEqual(p.natures_execution[ex.Execution.RADAR.value], 0)
        self.assertIn("Le radar n'a interrogé aucun moteur", ex.rapport(self.cx))

    def test_4_le_rapport_n_affirme_jamais_que_le_radar_a_cherche(self):
        """L'étiquette d'état a le droit d'exister — suivie de 0.

        Ce qui est interdit, c'est l'AFFIRMATION. « RECHERCHE RÉELLE PAR LE
        RADAR   0 » dit exactement l'inverse de ce qu'on veut éviter : elle
        dit que le radar n'a rien cherché.
        """
        p = self.passer(export([besoin("https://x.example/a", "T", "E")]))
        texte = parcours.rapport(self.cx, p)
        for affirmation in ("DÉCOUVERTE RÉELLE", "recherche exécutée par le radar",
                            "interrogé par le radar", "trouvé par le radar"):
            self.assertNotIn(affirmation, texte, affirmation)
        self.assertRegex(texte, r"RECHERCHE RÉELLE PAR LE RADAR\s+0")

    def test_5_la_preuve_de_collecte_dit_ce_qu_elle_est(self):
        """Elle atteste l'ENTRÉE de la ligne, jamais la lecture de la page."""
        from radar.mode import lire_collecte
        t = tr.toutes(self.cx)
        imp.importer(self.cx, export([besoin("https://x.example/a", "T", "E")],
                                     moteur="moteur-x"))
        t, = tr.toutes(self.cx)
        marque = lire_collecte(parcours.charge_de(t, mode=Mode.REEL))
        self.assertEqual(marque.source, "import:moteur-x")
        self.assertEqual(marque.reference, "https://x.example/a")


# ═══════════════════════════════════════════════ score et source
class E_LeScoreIgnoreLaSource(Chaine):

    def test_1_meme_besoin_deux_moteurs_meme_score(self):
        a = ouvrir(":memory:")
        b = ouvrir(":memory:")
        resultat = besoin("https://x.example/a", "Recherche transporteur",
                          "Tournées à assurer.")
        for cx, nom in ((a, "moteur-a"), (b, "moteur-b")):
            imp.importer(cx, export([resultat], moteur=nom))
            parcours.executer(cx, _moteur(cx), self.adaptateur, mode=Mode.REEL,
                              defauts={"secteur": self.cfg.get("secteur_par_defaut")})
        sa = a.execute("SELECT score, type, action FROM opportunites").fetchone()
        sb = b.execute("SELECT score, type, action FROM opportunites").fetchone()
        self.assertEqual(sa["score"], sb["score"], "la source ne vaut pas un point")
        self.assertEqual(sa["type"], sb["type"])
        self.assertEqual(sa["action"], sb["action"])

    def test_2_le_nom_du_moteur_n_entre_dans_aucune_classification(self):
        self.passer(export([besoin("https://x.example/a", "T", "E")],
                           moteur="un-moteur-au-nom-tres-particulier"))
        l = parcours.top_opportunites(self.cx)[0]
        for colonne in ("type", "action", "moteur", "nature", "etat_procedure",
                        "zone", "role"):
            self.assertNotIn("un-moteur-au-nom", str(l[colonne]), colonne)

    def test_3_aucun_rejet_fonde_sur_le_seul_score(self):
        """🔴 est un rejet OBJECTIF motivé, jamais « score faible »."""
        p = self.passer(export([
            besoin("https://x.example/a", "Un titre sans rapport",
                   "Texte quelconque.")]))
        for motif in p.motifs_rejet:
            self.assertNotIn("score", motif.lower(), motif)
        texte = parcours.rapport(self.cx, p)
        self.assertIn("n'est pas « score faible »", texte)

    def test_4_la_distance_ne_supprime_jamais_une_opportunite(self):
        p = self.passer(export([
            besoin("https://lointain.example/a",
                   "Recherche transporteur en Roumanie",
                   "Tournées quotidiennes à Bucarest.")]))
        self.assertEqual(p.besoins, 1)
        self.assertEqual(p.opportunites, 1,
                         "une affaire lointaine reste écrite, jamais supprimée")


# ═══════════════════════════════════════════════ la commande utilisateur
class F_LaCommandeEstUtilisableTelleQuelle(unittest.TestCase):

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.base = str(pathlib.Path(self.dossier) / "essai.sqlite3")

    def lancer(self, *args):
        import contextlib
        import io
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            code = principal(["--base", self.base, *args])
        return code, sortie.getvalue()

    def test_1_import_recherche_va_jusqu_au_rapport_commercial(self):
        chemin = export([besoin("https://transporteur.example/partenaires",
                                "Nous recherchons des partenaires de livraison",
                                "Sous-traitants recherchés en Wallonie.")])
        code, texte = self.lancer("import-recherche", chemin)
        self.assertEqual(code, 0)
        self.assertIn(HORS, texte)
        self.assertIn("TOP OPPORTUNITÉS COMMERCIALES", texte)
        self.assertIn("ENTONNOIR", texte)

    def test_2_un_fichier_sans_provenance_est_refuse_proprement(self):
        chemin = export([besoin("https://x.example/a", "T", "E")],
                        provenance="RECHERCHE DU RADAR")
        code, _ = self.lancer("import-recherche", chemin)
        self.assertEqual(code, 2, "un refus doit sortir en code non nul")
        self.assertFalse(pathlib.Path(self.base).exists()
                         and tr.toutes(ouvrir(self.base)),
                         "rien ne doit être écrit")

    def test_3_sans_analyse_s_arrete_aux_trouvailles(self):
        chemin = export([besoin("https://x.example/a", "T", "E")])
        code, texte = self.lancer("import-recherche", chemin, "--sans-analyse")
        self.assertEqual(code, 0)
        self.assertNotIn("TOP OPPORTUNITÉS", texte)
        self.assertEqual(
            ouvrir(self.base).execute(
                "SELECT count(*) c FROM opportunites").fetchone()["c"], 0)

    def test_4_les_refus_restent_visibles_meme_si_tout_est_refuse(self):
        """Le cas où les refus comptent le plus est celui où rien ne passe."""
        chemin = export([{"requete": "q", "url": "", "titre": "T"},
                         {"requete": "q", "url": "javascript:x"}])
        code, texte = self.lancer("import-recherche", chemin)
        self.assertEqual(code, 0)
        self.assertIn("LIGNES REFUSÉES", texte)
        self.assertIn(imp.URL_ABSENTE, texte)
        self.assertIn(imp.URL_INVALIDE, texte)

    def test_5_la_commande_ecrit_dans_la_base_reelle_par_defaut(self):
        """Un import porte des résultats réels : aucun mode à choisir."""
        import inspect
        from radar import cli
        source = inspect.getsource(cli.cmd_import_recherche)
        self.assertIn("Mode.REEL", source)
        self.assertNotIn("_mode(a)", source)

    def test_6_les_requetes_prioritaires_sortent_sans_reseau(self):
        code, texte = self.lancer("requetes-prioritaires")
        self.assertEqual(code, 0)
        self.assertIn("recherche transporteur Belgique", texte)
        self.assertIn("Le radar n'en a exécuté AUCUNE", texte)
        for famille in ("A_besoin_explicite", "B_logistique_distribution",
                        "C_signaux_entreprises", "D_partenariats",
                        "E_metiers_a_construire"):
            self.assertIn(famille, texte, famille)

    def test_7_une_seule_requete_par_ligne_pour_copier(self):
        code, texte = self.lancer("requetes-prioritaires", "--brut")
        lignes = [l for l in texte.splitlines() if l.strip()]
        self.assertGreaterEqual(len(lignes), 40)
        for l in lignes:
            self.assertFalse(l.startswith(" "), l)


# ═══════════════════════════════════════════════ les requêtes
class G_LesRequetesPrioritaires(unittest.TestCase):

    def setUp(self):
        self.cfg = _cfg("config/requetes-prioritaires.yaml")

    def test_1_les_cinq_familles_demandees_existent(self):
        familles = self.cfg["familles"]
        for lettre in "ABCDE":
            self.assertTrue(any(c.startswith(lettre + "_") for c in familles),
                            lettre)

    def test_2_aucun_nom_de_moteur_dans_les_requetes(self):
        """Ce fichier dit QUOI chercher, jamais AVEC QUOI."""
        texte = (RACINE / "config/requetes-prioritaires.yaml").read_text(
            encoding="utf-8").lower()
        for nom in ("serpapi", "serper", "duckduckgo", "yandex", "brave.com"):
            self.assertNotIn(nom, texte, nom)

    def test_3_les_metiers_a_construire_n_affirment_aucune_eligibilite(self):
        f = self.cfg["familles"]["E_metiers_a_construire"]
        self.assertIn("À CONFIRMER", f.get("avertissement", ""))

    def test_4_la_geographie_est_un_ordre_d_exploration_pas_un_filtre(self):
        geo = self.cfg["geographie"]
        couches = [c["couche"] for c in geo["ordre_exploration"]]
        self.assertEqual(couches[:1], ["proximite_immediate"])
        self.assertIn("europe", couches)
        # Les couches locales sont VIDES : le radar ne devine pas une commune.
        for c in geo["ordre_exploration"][:2]:
            self.assertEqual(c.get("suffixes"), [])

    def test_5_aucune_requete_vide_ni_dupliquee(self):
        toutes = [r for f in self.cfg["familles"].values()
                  for r in f.get("requetes") or []]
        self.assertEqual(len(toutes), len(set(toutes)), "requête en double")
        for r in toutes:
            self.assertTrue(r.strip())


# ═══════════════════════════════════════════════ sécurité et non-régression
class H_SecuriteEtNonRegression(unittest.TestCase):
    """§18 — ce qui ne doit jamais arriver, quelle que soit l'entrée."""

    CLE_FACTICE = "CLE-FACTICE-SANS-VALEUR-0000"

    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.base = str(pathlib.Path(self.dossier) / "essai.sqlite3")
        self.cx = ouvrir(":memory:")
        self.adaptateur, self.cfg = _source("recherche")

    def passer(self, chemin):
        imp.importer(self.cx, chemin)
        return parcours.executer(
            self.cx, _moteur(self.cx), self.adaptateur, mode=Mode.REEL,
            defauts={"secteur": self.cfg.get("secteur_par_defaut")})

    def test_1_aucune_cle_ne_fuite_par_la_sortie_de_la_commande(self):
        """Une clé présente dans l'environnement ne doit pas être IMPRIMÉE."""
        import contextlib
        import io
        import os
        chemin = export([besoin("https://x.example/a", "T", "E")])
        anciennes = {c: os.environ.get(c) for c in
                     ("GOOGLE_API_KEY", "GOOGLE_CSE_ID", "BRAVE_API_KEY")}
        for c in anciennes:
            os.environ[c] = self.CLE_FACTICE
        try:
            sortie = io.StringIO()
            with contextlib.redirect_stdout(sortie):
                principal(["--base", self.base, "import-recherche", chemin])
            self.assertNotIn(self.CLE_FACTICE, sortie.getvalue())
        finally:
            for c, v in anciennes.items():
                if v is None:
                    os.environ.pop(c, None)
                else:
                    os.environ[c] = v

    def test_2_aucune_opportunite_n_est_inventee_sans_contenu(self):
        """Un export dont toutes les lignes sont refusées ne produit RIEN."""
        chemin = export([{"requete": "q", "url": ""},
                         {"requete": "q", "url": "javascript:x"}])
        p = self.passer(chemin)
        self.assertEqual(p.resultats, 0)
        self.assertEqual(p.opportunites, 0)
        for table in ("opportunites", "avis", "entreprises",
                      "pages_surveillees", "trouvailles"):
            self.assertEqual(
                self.cx.execute(f"SELECT count(*) c FROM {table}").fetchone()["c"],
                0, table)

    def test_3_une_affaire_difficile_n_est_jamais_supprimee(self):
        """Volume, recrutement, distance : des raisons d'effort, pas d'exclusion."""
        p = self.passer(export([
            besoin("https://gros.example/appel",
                   "Recherche transporteur — 40 véhicules, 60 chauffeurs",
                   "Marché national, service de nuit et week-end, "
                   "démarrage immédiat, recrutement massif nécessaire.")]))
        self.assertEqual(p.besoins, 1)
        self.assertEqual(p.opportunites, 1)
        l = self.cx.execute("SELECT type, motif FROM opportunites").fetchone()
        if l["type"] == "REJET":
            for mot in ("volume", "trop grand", "difficile", "recrutement",
                        "score"):
                self.assertNotIn(mot, (l["motif"] or "").lower(),
                                 "rejetée pour une raison d'EFFORT, pas objective")

    def test_4_un_marche_public_n_a_aucun_avantage_de_score(self):
        """Même besoin, deux provenances : le même score.

        « Comment entrer sur ce marché ? » — jamais « d'où vient l'avis ? ».
        """
        texte = ("Recherche transporteur pour tournées quotidiennes "
                 "en Brabant wallon.")
        scores = []
        for nom, url in (("moteur-portail-public", "https://portail.example/avis/1"),
                         ("moteur-generaliste", "https://societe.example/page")):
            cx = ouvrir(":memory:")
            imp.importer(cx, export([besoin(url, "Recherche transporteur", texte)],
                                    moteur=nom))
            parcours.executer(cx, _moteur(cx), self.adaptateur, mode=Mode.REEL,
                              defauts={"secteur": self.cfg.get("secteur_par_defaut")})
            scores.append(cx.execute("SELECT score FROM opportunites").fetchone()["score"])
        self.assertEqual(scores[0], scores[1],
                         "la provenance ne vaut pas un point")

    def test_5_le_rapport_ne_promet_jamais_de_donnees_reelles_qu_il_n_a_pas(self):
        p = parcours.Parcours(mode=Mode.DEMO)
        texte = parcours.rapport(self.cx, p)
        self.assertIn("DONNÉES RÉELLES : NON MESURÉES", texte)


# ═══════════════════════════════════════ ce que l'exploitant lira demain matin
class I_LeRapportRepondALaQuestionDeLExploitant(Chaine):
    """« Qu'est-ce que je fais demain matin ? » — et sans confondre les genres."""

    def test_1_un_signal_ne_se_melange_jamais_a_un_besoin_enonce(self):
        self.passer(export([
            besoin("https://a.example/partenaires",
                   "Nous recherchons des sous-traitants transport",
                   "Sociétés de transport partenaires avec véhicules propres."),
            besoin("https://presse.example/actu",
                   "Une société ouvre un dépôt à Gand",
                   "Ouverture d'une plateforme de tri.")]))
        texte = parcours.top_actions(self.cx)
        self.assertIn("BESOINS ÉNONCÉS", texte)
        self.assertIn("SIGNAUX", texte)
        avant, apres = texte.split("SIGNAUX", 1)
        self.assertIn("sous-traitants transport", avant)
        self.assertIn("AUCUN besoin n'a été exprimé ici", apres)

    def test_2_les_quatre_axes_sont_affiches_separement(self):
        """Le score ne porte pas la nature — parce que les quatre se lisent
        côte à côte. C'est la raison pour laquelle score.py n'a pas bougé."""
        self.passer(export([
            besoin("https://a.example/x", "Recherche transporteur", "Tournées.")]))
        l = parcours.top_opportunites(self.cx)[0]
        ligne = parcours.axes(l)
        for axe in ("ADÉQUATION", "PREUVE", "NATURE", "POTENTIEL"):
            self.assertIn(axe, ligne, axe)

    def test_3_une_hypothese_et_un_fait_se_distinguent_sans_toucher_au_score(self):
        """Même adéquation, preuve différente : lisible sans pondérer le score."""
        self.passer(export([
            besoin("https://a.example/appel", "Appel à partenaires logistiques",
                   "Nous cherchons des partenaires."),
            besoin("https://presse.example/actu",
                   "Une société ouvre un dépôt à Gand", "Plateforme de tri.")]))
        par_nature = {l["nature"]: l for l in parcours.top_opportunites(self.cx)}
        self.assertIn("FAIT", par_nature)
        self.assertIn("HYPOTHÈSE", par_nature)
        self.assertNotEqual(par_nature["FAIT"]["fiabilite"],
                            par_nature["HYPOTHÈSE"]["fiabilite"],
                            "la preuve doit les séparer, à défaut du score")

    def test_4_la_maturite_est_un_axe_a_part_pas_une_sixieme_categorie(self):
        p = self.passer(export([besoin("https://a.example/x", "T", "E")]))
        texte = parcours.rapport(self.cx, p)
        categories, maturite = texte.split("MATURITÉ", 1)
        self.assertNotIn(parcours.MATURITE_NON_QUALIFIEE,
                         categories.split("COMMERCIAL — catégories")[-1],
                         "⚪ ne doit pas être alignée avec les cinq catégories")
        self.assertIn("jamais une sixième catégorie", maturite)
        self.assertNotIn(parcours.MATURITE_NON_QUALIFIEE,
                         parcours.CATEGORIES_COMMERCIALES)

    def test_5_un_recrutement_de_salarie_n_est_pas_une_demande_adressee_a_nous(self):
        """RECRUTEMENT D'UN SALARIÉ ≠ RECHERCHE D'UN PRESTATAIRE.

        Mesuré : une offre d'emploi isolée ressort ⚪, et son action est de
        classer sans suite. Le cas du recrutement MASSIF, lui, n'est pas
        distingué aujourd'hui — c'est une observation documentée dans
        validation/mesures/, pas une règle écrite ici.
        """
        self.passer(export([
            besoin("https://a.example/jobs/chauffeur",
                   "Offre d'emploi : chauffeur poids lourd (CDI)",
                   "Nous engageons un chauffeur en contrat à durée "
                   "indéterminée. Envoyez votre CV.")]))
        l = parcours.top_opportunites(self.cx)
        if l:
            self.assertNotEqual(l[0]["type"], "DIRECT",
                                "une offre d'emploi isolée n'est pas une "
                                "opportunité directe")


# ═══════════════════════════════════════ ce qu'un tableur écrit réellement
class J_LImportSupporteCeQuUnTableurProduit(unittest.TestCase):
    """Deux défauts qui bloquaient un export réel, et rien d'inventé.

    Un tableur configuré en français ou en néerlandais écrit en
    POINT-VIRGULE et pose une marque d'ordre d'octets. Les deux faisaient
    refuser le fichier avec « PROVENANCE NON DÉCLARÉE », alors que la
    provenance ÉTAIT écrite — elle s'affichait simplement à l'identique.
    """

    def ecrire(self, contenu: bytes, suffixe=".csv"):
        d = tempfile.mkdtemp()
        p = pathlib.Path(d) / ("export" + suffixe)
        p.write_bytes(contenu)
        return str(p)

    def test_1_marque_d_ordre_d_octets(self):
        contenu = ("\ufeffprovenance,moteur,date_execution,requete,url,titre,"
                   "extrait,rang\n"
                   f"{HORS},m,2026-09-13T09:00:00Z,q,https://x.example/a,T,E,1\n")
        a, = imp.charger(self.ecrire(contenu.encode("utf-8")))
        self.assertEqual(len(a.resultats_importes), 1)

    def test_2_separateur_point_virgule(self):
        contenu = ("provenance;moteur;date_execution;requete;url;titre;"
                   "extrait;rang\n"
                   f"{HORS};m;2026-09-13T09:00:00Z;q;https://x.example/b;T;E;1\n")
        a, = imp.charger(self.ecrire(contenu.encode("utf-8")))
        self.assertEqual(a.resultats_importes[0].url, "https://x.example/b")

    def test_3_les_deux_a_la_fois(self):
        contenu = ("\ufeffprovenance;moteur;date_execution;requete;url;titre;"
                   "extrait;rang\n"
                   f"{HORS};m;2026-09-13T09:00:00Z;q;https://x.example/c;T;E;1\n")
        a, = imp.charger(self.ecrire(contenu.encode("utf-8")))
        self.assertEqual(a.resultats_importes[0].url, "https://x.example/c")

    def test_4_un_tableau_json_nu_aux_noms_anglais(self):
        contenu = json.dumps([{
            "provenance": HORS, "engine": "m", "date": "2026-09-13T09:00:00Z",
            "query": "q", "link": "https://x.example/d", "title": "T",
            "snippet": "E", "position": 3}], ensure_ascii=False)
        a, = imp.charger(self.ecrire(contenu.encode("utf-8"), ".json"))
        self.assertEqual(a.resultats_importes[0].url, "https://x.example/d")
        self.assertEqual(a.resultats_importes[0].rang, 3)

    def test_5_un_collage_de_navigateur_en_tabulations(self):
        """Le format se lit dans le CONTENU, pas dans l'extension.

        Un collage depuis un navigateur s'enregistre en .tsv, en .txt, ou sans
        extension. Choisir l'analyseur d'après le nom du fichier faisait lire
        un tableau tabulé comme du JSON, et l'exploitant recevait
        « Expecting value: line 1 column 1 » — un message qui ne lui dit rien.
        """
        contenu = ("provenance\tmoteur\trequete\turl\ttitre\n"
                   f"{HORS}\tnavigateur\trecherche transporteur Belgique\t"
                   "https://x.example/f\tNous recherchons des partenaires\n")
        a, = imp.charger(self.ecrire(contenu.encode("utf-8"), ".tsv"))
        r, = a.resultats_importes
        self.assertEqual(r.url, "https://x.example/f")
        # Sans extrait, sans rang, sans date : rien n'est inventé pour combler.
        self.assertEqual(r.extrait, "")
        self.assertIsNone(r.rang)
        self.assertEqual(a.date_execution, ex.DATE_INCONNUE)

    def test_6_les_espaces_d_un_tableur_ne_sont_pas_des_donnees(self):
        contenu = ("provenance; moteur ; date_execution ; requete ; url ;"
                   " titre ; extrait ; rang \n"
                   f"{HORS}; m ; 2026-09-13T09:00:00Z ; q ;"
                   " https://x.example/e ; T ; E ; 1 \n")
        a, = imp.charger(self.ecrire(contenu.encode("utf-8")))
        self.assertEqual(a.resultats_importes[0].url, "https://x.example/e")


if __name__ == "__main__":
    unittest.main()
