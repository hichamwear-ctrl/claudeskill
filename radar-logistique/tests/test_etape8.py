"""ÉTAPE 8 — DÉCOUVERTE WEB RÉELLE : l'adresse, la collecte, la qualification.

    RECHERCHE → TROUVAILLE → URL → ENTREPRISE → CANDIDATE → COLLECTE
              → QUALIFICATION → OPPORTUNITÉ → CLASSIFICATION → ACTION

Les pages de ces tests sont FABRIQUÉES et le disent. Le seul jeu réel du
projet vit dans `validation/exports-reels/` ; il n'est pas rejoué ici.

Ce que ces tests tiennent, c'est la frontière la plus fragile de l'étape :

    UN MOT DANS UNE ADRESSE N'EST PAS UNE PREUVE D'OPPORTUNITÉ.
"""

import json
import pathlib
import tempfile
import unittest

from radar import (adresse, collecte_importee as col, import_externe as imp,
                   pages as mod_pages, parcours)
from radar.base import ouvrir
from radar.cli import _moteur, _source
from radar.mode import Mode
from radar.pages import Acces, Qualification, Statut

HORS = imp.PROVENANCE


def export(lignes, *, moteur="moteur-t"):
    charge = {"provenance": HORS, "moteur": moteur,
              "date_execution": "2026-09-14T09:00:00+00:00", "resultats": lignes}
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / "export.json"
    p.write_text(json.dumps(charge, ensure_ascii=False), encoding="utf-8")
    return str(p)


def r(url, titre="", extrait="", requete="recherche transporteur Belgique", rang=1):
    return {"requete": requete, "url": url, "titre": titre, "extrait": extrait,
            "rang": rang}


def collecte(pages, provenance=col.PROVENANCE):
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / "collecte.json"
    p.write_text(json.dumps({"provenance": provenance, "pages": pages},
                            ensure_ascii=False), encoding="utf-8")
    return str(p)


class Socle(unittest.TestCase):
    def setUp(self):
        self.cx = ouvrir(":memory:")
        self.moteur = _moteur(self.cx)
        self.adaptateur, self.cfg = _source("recherche")

    def decouvrir(self, lignes):
        imp.importer(self.cx, export(lignes))
        return parcours.executer(
            self.cx, _moteur(self.cx), self.adaptateur, mode=Mode.REEL,
            defauts={"secteur": self.cfg.get("secteur_par_defaut")})

    def page(self, url):
        return mod_pages.lire(self.cx, url)


# ══════════════════════════════════════════════════ l'adresse comme INDICE
class A_LAdresseEstUnIndiceJamaisUnePreuve(Socle):

    def test_1_une_url_porteuse_d_un_besoin_est_lue(self):
        i = adresse.lire("https://exemple.be/fr/devenir-partenaire-livraison/",
                         self.moteur.ontologie, self.moteur.roles)
        self.assertIn("devenir", i.mots)
        self.assertIn("partenaire", i.mots)
        self.assertTrue(i.porteuse)
        self.assertIn("INDICE D'ADRESSE", i.raison())
        self.assertIn("pas une preuve", i.raison())

    def test_2_une_url_sans_information_commerciale_ne_dit_rien(self):
        i = adresse.lire("https://exemple.be/fr/page/12/index.html",
                         self.moteur.ontologie, self.moteur.roles)
        self.assertFalse(i.porteuse)
        self.assertIsNone(i.raison())
        self.assertEqual(i.mots, [], "ni langue, ni extension, ni identifiant")

    def test_3_titre_pertinent_et_url_neutre(self):
        p = self.decouvrir([r("https://exemple.be/p/1",
                              "Nous recherchons un partenaire de livraison")])
        self.assertEqual(p.opportunites, 1)
        self.assertNotIn("INDICE D'ADRESSE",
                         self.page("https://exemple.be/p/1").raison or "")

    def test_4_titre_neutre_et_url_pertinente(self):
        """L'indice apparaît dans la raison — il n'accorde AUCUN statut."""
        self.decouvrir([r("https://exemple.be/devenir-partenaire-livraison/",
                          "Bienvenue")])
        page = self.page("https://exemple.be/devenir-partenaire-livraison/")
        self.assertIn("INDICE D'ADRESSE", page.raison)
        self.assertIs(page.statut, Statut.CANDIDATE, "un indice ne promeut pas")
        self.assertIs(page.qualification, Qualification.NON_QUALIFIEE)
        self.assertIs(page.acces, Acces.JAMAIS_CONSULTEE)

    def test_5_une_url_porteuse_dont_la_page_n_est_pas_commerciale(self):
        """L'adresse promet, le contenu dément : c'est le CONTENU qui décide."""
        url = "https://exemple.be/devenir-partenaire-livraison/"
        self.decouvrir([r(url, "Bienvenue")])
        col.importer(self.cx, collecte([{
            "url": url, "acces": Acces.CONSULTEE.value,
            "contenu": "Nous avons changé notre logo cette année. "
                       "Découvrez notre nouvelle charte graphique."}]),
            self.moteur)
        page = self.page(url)
        self.assertIsNot(page.qualification, Qualification.PREUVE)
        self.assertIs(page.statut, Statut.CANDIDATE,
                      "une adresse porteuse ne sauve pas un contenu muet")

    def test_6_l_adresse_n_entre_dans_aucun_score(self):
        a = self.decouvrir([r("https://a.example/x",
                              "Nous recherchons un partenaire de livraison")])
        cxb = ouvrir(":memory:")
        imp.importer(cxb, export([r(
            "https://b.example/devenir-partenaire-livraison/sous-traitance/",
            "Nous recherchons un partenaire de livraison")]))
        parcours.executer(cxb, _moteur(cxb), self.adaptateur, mode=Mode.REEL,
                          defauts={"secteur": self.cfg.get("secteur_par_defaut")})
        sa = self.cx.execute("SELECT score FROM opportunites").fetchone()["score"]
        sb = cxb.execute("SELECT score FROM opportunites").fetchone()["score"]
        self.assertEqual(sa, sb, "l'adresse ne vaut pas un point")


# ══════════════════════════════════════════════════ la collecte importée
class B_LaCollecteReelleAlimenteLaQualification(Socle):

    URL = "https://exemple.be/partenaires/"

    def setUp(self):
        super().setUp()
        self.decouvrir([r(self.URL, "Nos partenaires")])

    def test_7_une_page_collectee_avec_preuve_commerciale_promeut(self):
        b = col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.CONSULTEE.value,
            "contenu": "Nous recherchons un partenaire de livraison pour "
                       "assurer nos tournées régulières en Wallonie."}]),
            self.moteur)
        page = self.page(self.URL)
        self.assertEqual(b.collectees, 1)
        self.assertIs(page.acces, Acces.CONSULTEE)
        self.assertIs(page.qualification, Qualification.PREUVE)
        self.assertIs(page.statut, Statut.SURVEILLEE)
        self.assertTrue(page.empreinte, "une lecture réussie laisse une empreinte")

    def test_8_une_page_collectee_sans_preuve_ne_promeut_pas(self):
        col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.CONSULTEE.value,
            "contenu": "Nos bureaux sont ouverts du lundi au vendredi."}]),
            self.moteur)
        page = self.page(self.URL)
        self.assertIs(page.acces, Acces.CONSULTEE)
        self.assertIsNot(page.qualification, Qualification.PREUVE)
        self.assertIs(page.statut, Statut.CANDIDATE)

    def test_9_une_erreur_de_collecte_n_est_pas_une_absence_de_besoin(self):
        b = col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.ERREUR.value,
            "erreur": "HTTP 503"}]), self.moteur)
        page = self.page(self.URL)
        self.assertEqual(b.erreurs, 1)
        self.assertIs(page.acces, Acces.ERREUR)
        self.assertIs(page.qualification, Qualification.NON_QUALIFIEE,
                      "aucune qualification ne s'écrit sans lecture")
        self.assertIs(page.statut, Statut.CANDIDATE, "jamais écartée sur un 503")

    def test_10_une_page_inaccessible_reste_candidate(self):
        col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.NON_DISPONIBLE.value,
            "erreur": "robots.txt interdit"}]), self.moteur)
        page = self.page(self.URL)
        self.assertIs(page.acces, Acces.NON_DISPONIBLE)
        self.assertIs(page.statut, Statut.CANDIDATE)

    def test_11_une_lecture_annoncee_sans_contenu_n_est_pas_une_lecture(self):
        col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.CONSULTEE.value, "contenu": ""}]),
            self.moteur)
        self.assertIsNot(self.page(self.URL).acces, Acces.CONSULTEE)

    def test_12_une_page_modifiee_change_d_empreinte(self):
        col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.CONSULTEE.value,
            "contenu": "Première version de la page."}]), self.moteur)
        avant = self.page(self.URL).empreinte
        col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.CONSULTEE.value,
            "contenu": "Seconde version, le texte a changé."}]), self.moteur)
        self.assertNotEqual(avant, self.page(self.URL).empreinte)

    def test_13_une_erreur_n_efface_pas_l_empreinte_d_une_lecture_reussie(self):
        col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.CONSULTEE.value,
            "contenu": "Une page lue."}]), self.moteur)
        empreinte = self.page(self.URL).empreinte
        col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.ERREUR.value, "erreur": "timeout"}]),
            self.moteur)
        self.assertEqual(self.page(self.URL).empreinte, empreinte)

    def test_14_aucune_page_n_est_creee_par_une_collecte(self):
        b = col.importer(self.cx, collecte([{
            "url": "https://jamais-vue.example/x",
            "acces": Acces.CONSULTEE.value, "contenu": "Recherche transporteur."}]),
            self.moteur)
        self.assertEqual(b.inconnues, 1)
        self.assertIsNone(self.page("https://jamais-vue.example/x"))

    def test_15_un_fichier_sans_provenance_est_refuse(self):
        with self.assertRaises(col.CollecteInvalide):
            col.importer(self.cx, collecte([], provenance="LU PAR LE RADAR"),
                         self.moteur)

    def test_16_la_collecte_ne_cree_aucune_opportunite(self):
        avant = self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]
        col.importer(self.cx, collecte([{
            "url": self.URL, "acces": Acces.CONSULTEE.value,
            "contenu": "Nous recherchons un partenaire de livraison."}]),
            self.moteur)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"],
            avant, "qualifier une page n'est pas créer une opportunité")


# ══════════════════════════════════════ les familles du premier jeu réel
class C_LesFamillesQuiOntProduitLesFauxPositifs(Socle):
    """Annuaire, presse, blog, concurrent — SANS liste de sites.

    Ces tests mesurent le comportement ACTUEL sur des pages fabriquées qui
    imitent les familles rencontrées dans le jeu réel. Aucune règle nouvelle
    n'est écrite : ils constatent, et servent de témoin si une règle est un
    jour validée.
    """

    def verdict(self, url, titre, contenu):
        self.decouvrir([r(url, titre)])
        col.importer(self.cx, collecte([{
            "url": url, "acces": Acces.CONSULTEE.value, "contenu": contenu}]),
            self.moteur)
        return self.page(url)

    def test_17_un_annuaire_est_collecte_et_qualifie_comme_les_autres(self):
        page = self.verdict(
            "https://annuaire.example/entreprises/belgique/transport.html",
            "Transport Belgique | Entreprises et fournisseurs B2B",
            "Trouvez 124 entreprises de transport en Belgique. "
            "Comparez les fournisseurs et demandez un devis.")
        self.assertIs(page.acces, Acces.CONSULTEE)
        self.assertIsNotNone(page.qualification)

    def test_18_un_article_de_presse_est_traite_sans_regle_speciale(self):
        page = self.verdict(
            "https://journal.example/article/le-dernier-kilometre-en-ville",
            "Dernier kilomètre : comment rendre les livraisons plus durables ?",
            "Chaque jour des milliers de colis sont livrés. Le dernier "
            "kilomètre pèse le plus lourd dans le bilan environnemental.")
        self.assertIs(page.acces, Acces.CONSULTEE)

    def test_19_aucune_liste_de_sites_n_est_ecrite_dans_le_code(self):
        """Pas de blacklist. La logique doit rester générique."""
        import ast
        for chemin in ("radar/adresse.py", "radar/collecte_importee.py"):
            arbre = ast.parse(pathlib.Path(chemin).read_text(encoding="utf-8"))
            docs = {ast.get_docstring(n, clean=False) for n in ast.walk(arbre)
                    if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef))}
            litterales = [n.value.lower() for n in ast.walk(arbre)
                          if isinstance(n, ast.Constant)
                          and isinstance(n.value, str) and n.value not in docs]
            for nom in ("europages", "indeed", "postnl", "bulbul", "shippr",
                        "colisprive", "mecalux", "rtbf", "beci", "vpd",
                        "recordexpress", "2ememain"):
                for t in litterales:
                    self.assertNotIn(nom, t, f"{chemin} nomme {nom}")

    def test_20_une_page_de_recrutement_n_est_pas_promue(self):
        page = self.verdict(
            "https://emplois.example/offres/chauffeur-poids-lourd",
            "Offre d'emploi : chauffeur poids lourd (CDI)",
            "Nous engageons un chauffeur en contrat à durée indéterminée. "
            "Envoyez votre CV et votre lettre de motivation.")
        self.assertIsNot(page.qualification, Qualification.PREUVE)
        self.assertIs(page.statut, Statut.CANDIDATE)


# ══════════════════════════════════════════ provenance, dédup, non-régression
class D_CeQueLEtape8NeDoitPasCasser(Socle):

    def test_21_la_provenance_traverse_la_collecte(self):
        url = "https://exemple.be/partenaires/"
        self.decouvrir([r(url, "Nos partenaires")])
        col.importer(self.cx, collecte([{
            "url": url, "acces": Acces.CONSULTEE.value,
            "contenu": "Nous recherchons un partenaire de livraison."}]),
            self.moteur)
        prov = mod_pages.provenances_de(self.cx, url)
        self.assertTrue(prov)
        self.assertTrue(any("import:" in str(p.get("source", "")) for p in prov))

    def test_22_la_deduplication_d_url_tient_apres_la_collecte(self):
        p = self.decouvrir([r("https://exemple.be/a", "Recherche transporteur"),
                            r("https://exemple.be/a/", "Recherche transporteur"),
                            r("https://www.exemple.be/a", "Recherche transporteur")])
        self.assertEqual(p.urls_uniques, 1)

    def test_23_le_meme_besoin_sur_plusieurs_sources_garde_ses_observations(self):
        from radar import recoupement, trouvailles as tr
        url = "https://exemple.be/partenaires"
        imp.importer(self.cx, export([r(url, "Recherche transporteur")],
                                     moteur="moteur-a"))
        imp.importer(self.cx, export([r(url, "Recherche transporteur")],
                                     moteur="moteur-b"))
        g, = recoupement.grouper(tr.toutes(self.cx))
        self.assertTrue(g.multi_source)
        self.assertEqual(len(g.observations), 2)
        self.assertEqual(sorted(g.sources), ["import:moteur-a", "import:moteur-b"])

    def test_24_le_score_ne_decide_jamais_qu_une_opportunite_n_existe_pas(self):
        """Un score faible ou non mesurable laisse l'opportunité en base."""
        p = self.decouvrir([r("https://exemple.be/x", "Une page quelconque")])
        self.assertGreaterEqual(p.opportunites, 1)
        l = self.cx.execute("SELECT score, score_mesurable, type FROM opportunites"
                            ).fetchone()
        self.assertIsNotNone(l["type"], "elle existe, quel que soit son score")

    def test_25_une_entreprise_reste_INCONNUE_apres_collecte(self):
        from radar import identite
        from radar.entreprises import charger, domaine_de
        url = "https://exemple.be/partenaires/"
        self.decouvrir([r(url, "Fictif SA recherche des partenaires")])
        col.importer(self.cx, collecte([{
            "url": url, "acces": Acces.CONSULTEE.value,
            "contenu": "Nous recherchons un partenaire de livraison."}]),
            self.moteur)
        for cle in charger(self.cx).entreprises:
            self.assertNotIn("Fictif", cle)
            self.assertIsNot(identite.lire(self.cx, cle).etat,
                             identite.Etat.CONFIRMEE)

    def test_26_les_pages_a_collecter_sont_ordonnees_sans_exclure_personne(self):
        self.decouvrir([r("https://a.example/page/1", "Une page"),
                        r("https://b.example/devenir-partenaire-livraison/", "Autre")])
        liste = col.a_collecter(self.cx, self.moteur)
        self.assertEqual(len(liste), 2, "aucune page n'est exclue de la file")
        self.assertTrue(liste[0][0].porteuse, "l'indice passe en tête")


class E_LeLexiqueEstAuSingulier(Socle):
    """CONSTAT MESURÉ — non corrigé, `roles.yaml` est GELÉ.

    « partenaire de livraison » est reconnu ; « partenaireS de livraison »
    ne l'est pas. Or une entreprise qui en cherche plusieurs écrit le
    pluriel — c'est même la formulation la plus naturelle.

    Ce test ne valide pas ce comportement : il le FIXE pour qu'on voie
    immédiatement le jour où il change, dans un sens ou dans l'autre.
    """

    def lecture(self, texte):
        from radar.pertinence import Confiance, evaluer
        return evaluer(texte, self.moteur.ontologie,
                       self.moteur.roles).confiance is Confiance.FORTE

    def test_27_le_singulier_est_reconnu(self):
        self.assertTrue(self.lecture("Nous recherchons un partenaire de livraison"))

    def test_28_le_pluriel_passe_desormais_par_le_BESOIN_pas_par_le_lexique(self):
        """RÈGLE CHANGÉE — décision métier 1.

        « Nous recherchons DES partenaires de livraison » ressortait MOYENNE :
        le lexique de rôle ne connaît que le singulier, et le rôle était la
        seule preuve positive possible. Le pluriel était donc un défaut réel,
        et ce test le figeait.

        Il n'est plus atteignable par là : « nous recherchons » est un BESOIN
        ÉNONCÉ, et un besoin énoncé promeut maintenant par lui-même. Le
        défaut du lexique, lui, N'EST PAS corrigé — la deuxième assertion le
        vérifie explicitement, pour qu'il ne passe pas pour réglé.
        """
        self.assertTrue(
            self.lecture("Nous recherchons des partenaires de livraison"),
            "le besoin énoncé doit suffire, sans passer par le lexique de rôle")
        from radar.role import Role
        self.assertIsNot(
            self.moteur.roles.analyser("des partenaires de livraison").role,
            Role.PRESTATAIRE,
            "le lexique de rôle reste au singulier — défaut non corrigé")


if __name__ == "__main__":
    unittest.main()
