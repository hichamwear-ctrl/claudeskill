"""ÉTAPE 9 — SURVEILLANCE ET DÉVELOPPEMENT COMMERCIAL.

    ENTREPRISE → PAGE SURVEILLÉE → OBSERVATION → CHANGEMENT
               → QUALIFICATION → BESOIN/SIGNAL → OPPORTUNITÉ → ACTION

    MARCHÉ ATTRIBUÉ → TITULAIRE → DÉVELOPPER → CONTACTER LE TITULAIRE
                    → DATE DE FIN → SURVEILLER LE RENOUVELLEMENT

Les pages de ces tests sont FABRIQUÉES et le disent. Le jeu réel du projet
vit dans `validation/exports-reels/`.

La surveillance fonctionne SANS moteur de recherche : une entreprise déjà
connue n'a aucune raison de repasser par un moteur pour être suivie.
"""

import json
import pathlib
import tempfile
import unittest

from radar import (changement, collecte_importee as col, entreprises as ent,
                   identite, import_externe as imp, pages as mod_pages, parcours)
from radar.base import ouvrir
from radar.cli import _cfg, _moteur, _source
from radar.entreprises import Etat as EtatEnt, Motif, Registre
from radar.mode import Mode
from radar.pages import Acces, Qualification, Statut

PROFIL = _cfg("sources/page_web.yaml")
BESOIN = ("Nous recherchons un partenaire de livraison pour assurer nos "
          "tournées régulières en Wallonie.")
NEUTRE = "Nos bureaux sont ouverts du lundi au vendredi de 9h à 17h."


def collecte(pages, provenance=col.PROVENANCE):
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / "collecte.json"
    p.write_text(json.dumps({"provenance": provenance, "pages": pages},
                            ensure_ascii=False), encoding="utf-8")
    return str(p)


COLONNES_ATTRIBUTION = ("acheteur", "titulaire", "montant", "duree_mois",
                        "prestation", "zone", "lots", "conclu_le", "debut",
                        "fin", "renouvellement", "contact",
                        "besoin_sous_traitance")


def _inserer(cx, avis_id, **champs):
    """Une attribution, telle qu'une source la donnerait. Les champs absents
    restent ABSENTS : c'est précisément ce qu'on veut éprouver."""
    valeurs = [champs.get(c) for c in COLONNES_ATTRIBUTION]
    cx.execute(
        f"INSERT INTO attributions(avis_id, fiabilite, {', '.join(COLONNES_ATTRIBUTION)})"
        f" VALUES(?,?{',?' * len(COLONNES_ATTRIBUTION)})",
        [avis_id, champs.get("fiabilite", "MOYENNE"), *valeurs])
    return avis_id


def lue(url, contenu, acces=Acces.CONSULTEE, erreur=None):
    return {"url": url, "acces": acces.value, "contenu": contenu,
            "erreur": erreur}


class Socle(unittest.TestCase):
    def setUp(self):
        self.cx = ouvrir(":memory:")
        self.moteur = _moteur(self.cx)

    def connaitre(self, url, *, entreprise=None, libelle="Une page"):
        """Une page candidate, SANS passer par un moteur de recherche."""
        mod_pages.declarer(self.cx, url, entreprise=entreprise, libelle=libelle)
        return mod_pages.lire(self.cx, url)

    def veiller(self, pages, *, analyser=None):
        return col.surveiller(self.cx, collecte(pages), self.moteur,
                              analyser=analyser, profil=PROFIL)

    def page(self, url):
        return mod_pages.lire(self.cx, url)


# ════════════════════════════════════════════ entreprise, page, besoin
class A_TroisObjetsDistincts(Socle):
    """§3 — ENTREPRISE ≠ PAGE ≠ BESOIN ≠ OPPORTUNITÉ."""

    def test_1_une_entreprise_connue_entre_en_surveillance(self):
        r = Registre()
        e = r.decouvrir("Transports Exemple", domaine="exemple.be",
                        motif=Motif.CHERCHE_PARTENAIRE, origine="essai")
        self.assertIs(e.etat, EtatEnt.DECOUVERTE)
        r.surveiller("Transports Exemple", domaine="exemple.be")
        ent.enregistrer(self.cx, r)
        self.assertIs(ent.charger(self.cx).entreprises["exemple.be"].etat,
                      EtatEnt.SURVEILLEE)

    def test_2_decouverte_candidate_et_surveillee_ne_se_confondent_pas(self):
        """§4 — une entreprise trouvée n'est pas une entreprise surveillée."""
        r = Registre()
        r.decouvrir("A", domaine="a.be", motif=Motif.CHERCHE_PARTENAIRE,
                    origine="essai")
        r.surveiller("B", domaine="b.be")
        ent.enregistrer(self.cx, r)
        relu = ent.charger(self.cx).entreprises
        self.assertIs(relu["a.be"].etat, EtatEnt.DECOUVERTE)
        self.assertIs(relu["b.be"].etat, EtatEnt.SURVEILLEE)

    def test_3_une_entreprise_peut_avoir_plusieurs_pages(self):
        for chemin in ("partenaires", "fournisseurs", "actualites"):
            self.connaitre(f"https://exemple.be/{chemin}", entreprise="exemple.be")
        pages = mod_pages.a_surveiller(self.cx, entreprise="exemple.be",
                                       toutes=True)
        self.assertEqual(len(pages), 3)

    def test_4_une_page_change_sans_que_l_entreprise_change_d_identite(self):
        url = "https://exemple.be/partenaires"
        self.connaitre(url, entreprise="exemple.be")
        avant = identite.lire(self.cx, "exemple.be").etat
        self.veiller([lue(url, NEUTRE)])
        self.veiller([lue(url, BESOIN)])
        self.assertIs(identite.lire(self.cx, "exemple.be").etat, avant)

    def test_5_une_entreprise_reste_surveillee_sans_opportunite(self):
        r = Registre()
        r.surveiller("Exemple", domaine="exemple.be")
        ent.enregistrer(self.cx, r)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"], 0)
        self.assertIs(ent.charger(self.cx).entreprises["exemple.be"].etat,
                      EtatEnt.SURVEILLEE)


# ════════════════════════════════════════════ le cycle de veille
class B_LaVeilleDetecteCeQuiBouge(Socle):
    """§6 et §11 — et elle ne conclut jamais d'une erreur à une absence."""

    URL = "https://exemple.be/partenaires"

    def setUp(self):
        super().setUp()
        self.connaitre(self.URL, entreprise="exemple.be")

    def test_6_page_inchangee_aucune_analyse(self):
        self.veiller([lue(self.URL, BESOIN)])
        vus = []
        self.veiller([lue(self.URL, BESOIN)],
                     analyser=lambda c, p: vus.append(p.url) or 0)
        self.assertEqual(vus, [], "une page inchangée ne se réanalyse pas")

    def test_7_page_modifiee_declenche_l_analyse(self):
        self.veiller([lue(self.URL, NEUTRE)])
        vus = []
        self.veiller([lue(self.URL, BESOIN)],
                     analyser=lambda c, p: vus.append(p.url) or 1)
        self.assertEqual(vus, [self.URL])

    def test_8_un_changement_non_commercial_ne_produit_pas_d_opportunite(self):
        """§7 — un pied de page qui change n'est pas une affaire."""
        self.veiller([lue(self.URL, "Mentions légales. Cookies. Plan du site.")])
        vus = []
        trace, _, _ = self.veiller(
            [lue(self.URL, "Mentions légales. Cookies. Plan du site. "
                           "Politique de confidentialité mise à jour.")],
            analyser=lambda c, p: vus.append(p.url) or 1)
        self.assertEqual(vus, [], "aucune analyse sur un changement non commercial")
        self.assertGreaterEqual(trace.pages_non_commerciales, 1)

    def test_9_un_changement_commercial_est_qualifie(self):
        self.veiller([lue(self.URL, NEUTRE)])
        self.veiller([lue(self.URL, BESOIN)])
        page = self.page(self.URL)
        self.assertIs(page.qualification, Qualification.PREUVE)
        self.assertIs(page.statut, Statut.SURVEILLEE)

    def test_10_une_erreur_conserve_l_historique(self):
        self.veiller([lue(self.URL, BESOIN)])
        empreinte = self.page(self.URL).empreinte
        statut = self.page(self.URL).statut
        self.veiller([lue(self.URL, "", acces=Acces.ERREUR, erreur="HTTP 503")])
        page = self.page(self.URL)
        self.assertIs(page.acces, Acces.ERREUR)
        self.assertEqual(page.empreinte, empreinte, "une erreur n'efface rien")
        self.assertIs(page.statut, statut, "jamais rétrogradée sur une erreur")

    def test_11_robots_bloque_donne_NON_DISPONIBLE(self):
        self.veiller([lue(self.URL, "", acces=Acces.NON_DISPONIBLE,
                          erreur="robots.txt interdit")])
        page = self.page(self.URL)
        self.assertIs(page.acces, Acces.NON_DISPONIBLE)
        self.assertIs(page.statut, Statut.CANDIDATE, "pas de besoin inexistant")

    def test_12_une_page_inaccessible_ne_conclut_a_aucune_absence(self):
        self.veiller([lue(self.URL, BESOIN)])
        avant = self.page(self.URL).qualification
        self.veiller([lue(self.URL, "", acces=Acces.ERREUR, erreur="timeout")])
        self.assertIs(self.page(self.URL).qualification, avant)

    def test_13_l_historique_des_empreintes_est_conserve(self):
        self.veiller([lue(self.URL, "Version un.")])
        e1 = changement.connue_lisible(self.cx, self.URL)
        self.veiller([lue(self.URL, "Version deux, le texte a changé.")])
        e2 = changement.connue_lisible(self.cx, self.URL)
        self.assertTrue(e1 and e2)
        self.assertNotEqual(e1, e2)

    def test_14_une_page_absente_du_depot_n_est_pas_visitee(self):
        autre = "https://exemple.be/autre"
        self.connaitre(autre, entreprise="exemple.be")
        _, _, visitees = self.veiller([lue(self.URL, BESOIN)])
        self.assertEqual(visitees, 1)
        self.assertIs(self.page(autre).acces, Acces.JAMAIS_CONSULTEE)

    def test_15_un_nouveau_besoin_cree_une_piste(self):
        """§11 — nouveau besoin sur une page connue → opportunité potentielle."""
        from radar import circuit as mod_circuit, normalisation
        from radar.chaine import traiter
        self.veiller([lue(self.URL, NEUTRE)])

        def analyser(collecte, page):
            opp, _ = normalisation.depuis_collecte(
                collecte, PROFIL, source=collecte.provenance,
                circuit=mod_circuit.CONNUE)
            if opp is None:
                return 0
            b = traiter(self.cx, self.moteur, [opp], mode=Mode.REEL)
            return b.capter + b.developper

        avant = self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        self.veiller([lue(self.URL, BESOIN)], analyser=analyser)
        apres = self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        self.assertGreater(apres, avant)


# ════════════════════════════════════════════ indépendance et provenance
class C_LaSurveillanceNeDependDAucunMoteur(Socle):

    def test_16_veiller_sans_jamais_toucher_un_moteur_de_recherche(self):
        """§2 — une entreprise connue se surveille sans repasser par un moteur."""
        url = "https://exemple.be/partenaires"
        self.connaitre(url, entreprise="exemple.be")
        self.veiller([lue(url, BESOIN)])
        self.assertIs(self.page(url).qualification, Qualification.PREUVE)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM trouvailles").fetchone()["c"],
            0, "aucune trouvaille : aucun moteur n'a été interrogé")

    def test_17_la_provenance_de_decouverte_survit_a_la_veille(self):
        """§12 — la surveillance n'écrase jamais l'origine initiale."""
        url = "https://exemple.be/partenaires"
        d = tempfile.mkdtemp()
        p = pathlib.Path(d) / "export.json"
        p.write_text(json.dumps({
            "provenance": imp.PROVENANCE, "moteur": "moteur-a",
            "date_execution": "2026-09-14T09:00:00+00:00",
            "resultats": [{"requete": "q", "url": url, "titre": "Nos partenaires",
                           "rang": 1}]}, ensure_ascii=False), encoding="utf-8")
        imp.importer(self.cx, str(p))
        adaptateur, cfg = _source("recherche")
        parcours.executer(self.cx, _moteur(self.cx), adaptateur, mode=Mode.REEL,
                          defauts={"secteur": cfg.get("secteur_par_defaut")})
        self.veiller([lue(url, BESOIN)])
        sources = {str(x.get("source", "")) for x in
                   mod_pages.provenances_de(self.cx, url)}
        self.assertTrue(any("import:moteur-a" in s for s in sources),
                        f"origine perdue : {sources}")

    def test_18_plusieurs_sources_pour_une_meme_page_sont_conservees(self):
        url = "https://exemple.be/partenaires"
        self.connaitre(url, entreprise="exemple.be")
        mod_pages.rencontrer(self.cx, url, entreprise="exemple.be",
                             source="source-b", raison="vue ailleurs")
        sources = {str(x.get("source", "")) for x in
                   mod_pages.provenances_de(self.cx, url)}
        self.assertGreaterEqual(len(sources), 2, sources)

    def test_19_un_fichier_de_veille_sans_provenance_est_refuse(self):
        with self.assertRaises(col.CollecteInvalide):
            col.surveiller(self.cx, collecte([], provenance="LU PAR LE RADAR"),
                           self.moteur)

    def test_20_la_veille_ne_cree_aucune_entreprise(self):
        url = "https://exemple.be/partenaires"
        self.connaitre(url, entreprise="exemple.be")
        avant = self.cx.execute("SELECT count(*) c FROM entreprises").fetchone()["c"]
        self.veiller([lue(url, BESOIN)])
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM entreprises").fetchone()["c"],
            avant)


# ════════════════════════════════════════════ développement commercial
class D_UnMarcheAttribueEstUnePiste(Socle):
    """§8, §9, §10 — attribué n'est pas perdu, et n'est pas postulable non plus."""

    def attribuer(self, **champs):
        from radar.base import enregistrer_reponse
        avis_id = enregistrer_reponse(
            self.cx, "essai", champs.get("ref", "MARCHE-1"), {}, "")
        return _inserer(self.cx, avis_id, **champs)

    def test_21_une_attribution_conserve_ses_champs_sans_rien_inventer(self):
        self.attribuer(acheteur="Ville de Test", titulaire="Transports Test SA",
                       montant=300000, duree_mois=48, zone="Brabant",
                       fin="2029-12-31", renouvellement="2029-06-30")
        l = self.cx.execute("SELECT * FROM attributions").fetchone()
        self.assertEqual(l["titulaire"], "Transports Test SA")
        self.assertEqual(l["acheteur"], "Ville de Test")
        self.assertEqual(l["renouvellement"], "2029-06-30")
        self.assertIsNone(l["contact"], "un champ absent reste absent")
        self.assertIsNone(l["besoin_sous_traitance"])

    def test_22_une_attribution_ne_devient_jamais_postulable(self):
        self.attribuer(titulaire="Transports Test SA", fin="2029-12-31")
        postulables = self.cx.execute(
            "SELECT count(*) c FROM opportunites WHERE etat_procedure='POSTULABLE'"
        ).fetchone()["c"]
        self.assertEqual(postulables, 0)

    def test_23_un_titulaire_n_est_pas_une_entreprise_confirmee(self):
        """§10 — un nom lu dans un avis n'est pas un domaine identifié."""
        self.attribuer(titulaire="Transports Test SA")
        for cle in ent.charger(self.cx).entreprises:
            self.assertIsNot(identite.lire(self.cx, cle).etat,
                             identite.Etat.CONFIRMEE)

    def test_24_un_groupement_reste_plusieurs_entites(self):
        """§10 — trois titulaires restent trois entités, jamais fondues."""
        from radar.base import enregistrer_reponse
        from radar.identite import enregistrer_titulaires, groupement
        avis_id = enregistrer_reponse(self.cx, "essai", "M-G", {}, "")
        membres = enregistrer_titulaires(
            self.cx, avis_id,
            ["Transports A SA", "Logistique B SRL", "Express C NV"])
        self.assertEqual(len(membres), 3)
        etat = groupement(self.cx, avis_id)
        self.assertIn("3", etat)
        self.assertIn("INCONNUE", etat.upper())

    def test_24b_une_chaine_libre_n_est_jamais_decoupee(self):
        """Deviner des membres dans un texte libre fabriquerait des
        entreprises qui n'existent pas."""
        from radar.base import enregistrer_reponse
        from radar.identite import enregistrer_titulaires
        avis_id = enregistrer_reponse(self.cx, "essai", "M-L", {}, "")
        membres = enregistrer_titulaires(
            self.cx, avis_id, "Transports A SA - Logistique B SRL")
        self.assertEqual(len(membres), 1, membres)

    def test_25_le_developpement_s_affiche_sans_inventer_les_manques(self):
        import contextlib
        import io
        from radar.cli import principal
        d = tempfile.mkdtemp()
        base = str(pathlib.Path(d) / "b.sqlite3")
        cx = ouvrir(base)
        from radar.base import enregistrer_reponse
        avis_id = enregistrer_reponse(cx, "essai", "M-1", {}, "")
        _inserer(cx, avis_id, titulaire="Transports Test SA", fin="2029-12-31")
        cx.commit()
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            code = principal(["--base", base, "developper"])
        texte = sortie.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("Transports Test SA", texte)
        self.assertIn("CONTACTER LE TITULAIRE", texte)
        self.assertIn("À CONFIRMER", texte, "les manques s'écrivent")
        self.assertIn("n'est PAS une opportunité postulable", texte)

    def test_26_sans_date_de_fin_le_renouvellement_n_est_pas_calcule(self):
        import contextlib
        import io
        from radar.cli import principal
        d = tempfile.mkdtemp()
        base = str(pathlib.Path(d) / "b.sqlite3")
        cx = ouvrir(base)
        from radar.base import enregistrer_reponse
        avis_id = enregistrer_reponse(cx, "essai", "M-2", {}, "")
        _inserer(cx, avis_id, titulaire="Sans Date SA")
        cx.commit()
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            principal(["--base", base, "developper"])
        self.assertIn("NON CALCULABLE", sortie.getvalue())


# ════════════════════════════════════════════ ce que l'étape 9 ne casse pas
class E_NonRegression(Socle):

    def test_27_aucun_score_ne_supprime_une_opportunite(self):
        from radar.chaine import traiter
        from tests.test_radar import MAINTENANT, opp
        a = opp(ref_source="S-1")
        b = traiter(self.cx, self.moteur, [a], mode=Mode.DEMO)
        self.assertGreaterEqual(
            self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"], 1)

    def test_28_la_veille_n_a_pas_de_vocabulaire_propre(self):
        """Elle interroge l'ontologie et le détecteur existants, pas d'autres."""
        import ast
        arbre = ast.parse(pathlib.Path("radar/collecte_importee.py")
                          .read_text(encoding="utf-8"))
        modules = set()
        for n in ast.walk(arbre):
            if isinstance(n, ast.ImportFrom) and n.module:
                modules.update(n.module.split("."))
                modules.update(a.name.split(".")[-1] for a in n.names)
        for interdit in ("score", "classification", "capacite", "ponderations"):
            self.assertNotIn(interdit, modules)

    def test_29_aucun_nom_de_site_dans_le_code_de_veille(self):
        import ast
        for chemin in ("radar/collecte_importee.py", "radar/adresse.py"):
            arbre = ast.parse(pathlib.Path(chemin).read_text(encoding="utf-8"))
            docs = {ast.get_docstring(n, clean=False) for n in ast.walk(arbre)
                    if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef))}
            for n in ast.walk(arbre):
                if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                        and n.value not in docs):
                    for nom in ("postnl", "colisprive", "europages", "shippr",
                                "bulbul", "indeed"):
                        self.assertNotIn(nom, n.value.lower(), chemin)

    def test_30_une_page_ecartee_n_est_pas_reveillee_par_la_veille(self):
        url = "https://exemple.be/partenaires"
        self.connaitre(url, entreprise="exemple.be")
        mod_pages.ecarter(self.cx, url, "sans intérêt — décidé à la main")
        self.veiller([lue(url, BESOIN)])
        self.assertIs(self.page(url).statut, Statut.ECARTEE)


if __name__ == "__main__":
    unittest.main()
