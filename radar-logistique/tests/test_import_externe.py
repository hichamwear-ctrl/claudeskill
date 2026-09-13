"""8e-4 — LE MOTEUR DE DÉCOUVERTE EST UN ADAPTATEUR INTERCHANGEABLE.

    MOTEUR RÉEL ─┐
    EXPORT EXTERNE ─┼─► TROUVAILLES ─► COLLECTE ─► ENTREPRISE ─► PAGE
    FIXTURE ─────┘        CANDIDATE ─► QUALIFICATION ─► SURVEILLANCE
                                                      ─► OPPORTUNITÉ

Aucun fournisseur n'est choisi ici, aucune clé n'est utilisée, aucun réseau
n'est touché. Tous les fichiers d'import sont FABRIQUÉS en mémoire ou dans un
répertoire temporaire : ils n'ont été produits par aucun moteur et ne mesurent
AUCUN marché.

Ce que ces tests éprouvent, c'est le MÉCANISME — et les quatre états qui ne
doivent jamais se confondre :

    RECHERCHE RÉELLE PAR LE RADAR
    RÉSULTAT IMPORTÉ — RECHERCHE EXTERNE
    FIXTURE / DEMO
    NON MESURÉ
"""

import ast
import json
import pathlib
import tempfile
import unittest

from radar import (chainage, circuit, execution as ex, fixtures_recherche as fx,
                   import_externe as imp, pages as mod_pages, recoupement,
                   trouvailles as tr)
from radar.base import ouvrir
from radar.entreprises import Registre as RegistreEntreprises
from radar.identite import Etat
from radar.mode import Mode
from radar.moteurs_recherche import MoteurRecherche, Registre, Resultat

RAPPEL = "fixtures/recherche-rappel.yaml"
HORS = imp.PROVENANCE


def ligne(url, *, moteur="moteur-a", requete="une requête", titre="Un titre",
          extrait="Un extrait", rang=1, date="2026-09-12T09:00:00+00:00"):
    return {"provenance": HORS, "moteur": moteur, "date_execution": date,
            "requete": requete, "url": url, "titre": titre,
            "extrait": extrait, "rang": rang}


def charger(lignes, **entete):
    return imp.depuis_lignes(lignes, entete={"provenance": HORS, **entete})


def fichier(contenu, suffixe=".json"):
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / ("export" + suffixe)
    p.write_text(contenu if isinstance(contenu, str)
                 else json.dumps(contenu, ensure_ascii=False), encoding="utf-8")
    return str(p)


# ════════════════════════════════════════════════════════════════ 8e-4A
class A_LInterfaceDeMoteurReel(unittest.TestCase):
    """Ce que l'interface doit PORTER — et ce qu'elle ne doit jamais SAVOIR."""

    ELEMENTS = ("requête", "URL", "titre", "extrait", "rang", "moteur/source",
                "date", "provenance", "mode RÉEL", "statut de collecte")

    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_1_les_dix_elements_sont_portes_de_bout_en_bout(self):
        """Un seul aller-retour, et les dix éléments sont relisibles."""
        a, = charger([ligne("https://exemple.be/a", rang=4)])
        imp.inscrire(self.cx, a)
        t = tr.lire(self.cx, "https://exemple.be/a")

        self.assertEqual(t.requete, "une requête")            # requête
        self.assertEqual(t.url, "https://exemple.be/a")       # URL
        self.assertEqual(t.titre, "Un titre")                 # titre
        self.assertEqual(t.extrait, "Un extrait")             # extrait
        self.assertEqual(t.rang, 4)                           # rang
        self.assertEqual(t.source, "import:moteur-a")         # moteur/source
        self.assertTrue(t.decouverte_le)                      # date
        self.assertIs(ex.de_trouvaille(t),
                      ex.Execution.IMPORT_EXTERNE)            # provenance
        self.assertIs(t.mode, Mode.REEL)                      # mode RÉEL
        self.assertIs(t.collecte, tr.NON_COLLECTEE)           # statut ultérieur

    def test_2_la_date_declaree_est_conservee_telle_quelle(self):
        a, = charger([ligne("https://exemple.be/a")])
        self.assertEqual(a.resultats_importes[0].consulte_le,
                         "2026-09-12T09:00:00+00:00")
        self.assertEqual(a.date_execution, "2026-09-12T09:00:00+00:00")

    def test_3_le_statut_de_collecte_reste_modifiable_ensuite(self):
        from radar.pages import Acces
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        tr.collectee(self.cx, "https://exemple.be/a", Acces.CONSULTEE,
                     motif="900 octets reçus")
        self.assertIs(tr.lire(self.cx, "https://exemple.be/a").collecte,
                      Acces.CONSULTEE)

    def test_4_le_moteur_ignore_le_score_les_categories_et_le_registre(self):
        """Vérifié sur les IMPORTS et les IDENTIFIANTS, pas sur la prose.

        Les commentaires de ces modules ont le droit d'expliquer qu'un score
        existe : c'est en expliquant la règle qu'on la tient. Ce qu'ils n'ont
        pas le droit de faire, c'est de l'IMPORTER ou de la NOMMER.
        """
        interdits = ("score", "classification", "capacite", "nature", "fiche",
                     "portee", "procedure", "priorite", "profil", "entreprises",
                     "chainage", "pertinence", "suivi", "ponderations")
        for chemin in ("radar/moteurs_recherche.py", "radar/import_externe.py",
                       "radar/execution.py"):
            arbre = ast.parse(pathlib.Path(chemin).read_text(encoding="utf-8"))
            modules = set()
            for n in ast.walk(arbre):
                if isinstance(n, ast.Import):
                    modules.update(a.name.split(".")[-1] for a in n.names)
                elif isinstance(n, ast.ImportFrom):
                    modules.update(a.name.split(".")[-1] for a in n.names)
                    if n.module:
                        modules.update(n.module.split("."))
            for mot in interdits:
                self.assertNotIn(mot, modules, f"{chemin} importe {mot}")

    def test_5_aucun_attribut_metier_sur_les_objets_de_l_interface(self):
        a, = charger([ligne("https://exemple.be/a")])
        noms = set(dir(Resultat)) | set(dir(MoteurRecherche)) | set(dir(a))
        for interdit in ("score", "categorie", "classification", "profil",
                         "registre", "adequation", "potentiel", "ponderation"):
            for n in noms:
                self.assertNotIn(interdit, n.lower(), n)

    def test_6_aucun_nom_de_fournisseur_dans_le_code(self):
        """Les noms de moteurs viennent des FICHIERS, jamais du code."""
        for chemin in ("radar/import_externe.py", "radar/execution.py"):
            arbre = ast.parse(pathlib.Path(chemin).read_text(encoding="utf-8"))
            docs = set()
            for n in ast.walk(arbre):
                if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                    d = ast.get_docstring(n, clean=False)
                    if d:
                        docs.add(d)
            litterales = [n.value.lower() for n in ast.walk(arbre)
                          if isinstance(n, ast.Constant)
                          and isinstance(n.value, str) and n.value not in docs]
            for nom in ("google", "brave", "bing", "serpapi", "serper",
                        "duckduckgo", "yandex"):
                for t in litterales:
                    self.assertNotIn(nom, t, f"{chemin} : {nom}")

    def test_7_aucun_reseau_dans_les_modules_de_cette_etape(self):
        """Aucune CONNEXION possible. `urllib.parse` analyse une adresse et
        n'ouvre rien : c'est l'ouverture de connexion qui est interdite ici."""
        for chemin in ("radar/import_externe.py", "radar/execution.py"):
            source = pathlib.Path(chemin).read_text(encoding="utf-8")
            for interdit in ("urllib.request", "urlopen", "requests",
                             "socket", "http.client", "ssl"):
                self.assertNotIn(interdit, source, f"{chemin} : {interdit}")


# ════════════════════════════════════════════════════════════════ 8e-4B
class B_UnImportNEstJamaisUneRechercheDuRadar(unittest.TestCase):
    """La règle absolue de 8e-4B, tenue par la structure et non par un usage."""

    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_1_import_valide(self):                            # démonstration 1
        b = imp.importer(self.cx, fichier(
            {"provenance": HORS, "moteur": "moteur-a",
             "date_execution": "2026-09-12T09:00:00+00:00",
             "resultats": [{"requete": "q", "url": "https://exemple.be/a",
                            "titre": "T", "extrait": "E", "rang": 1}]}))
        self.assertEqual(b.inscrites, 1)
        self.assertEqual(b.refusees, 0)
        self.assertEqual(len(tr.toutes(self.cx)), 1)

    def test_2_un_import_refuse_d_executer_une_recherche(self):
        a, = charger([ligne("https://exemple.be/a")])
        with self.assertRaises(imp.RechercheNonExecutee):
            a.rechercher("une requête")

    def test_3_une_liste_vide_ne_se_confondrait_pas_avec_un_refus(self):
        """Un import ne rend pas [] : il LÈVE. Une liste vide voudrait dire
        « interrogé, rien trouvé », ce qui serait faux."""
        a, = charger([ligne("https://exemple.be/a")])
        try:
            a.rechercher("q")
        except imp.RechercheNonExecutee as e:
            self.assertIn(HORS, str(e))
        else:
            self.fail("un import a prétendu chercher")

    def test_4_un_import_n_est_jamais_le_moteur_disponible_d_un_registre(self):
        a, = charger([ligne("https://exemple.be/a")])
        self.assertFalse(a.disponible)
        self.assertIsNone(Registre([a]).disponible())
        self.assertIn(HORS, a.motif_indisponibilite)

    def test_5_le_fichier_doit_declarer_sa_provenance(self):
        """Ni en-tête, ni colonne : on ne sait pas qui a exécuté la recherche."""
        nue = dict(ligne("https://exemple.be/a"))
        nue.pop("provenance")
        with self.assertRaises(imp.ImportInvalide):
            imp.depuis_lignes([nue], entete={})

    def test_6_une_provenance_differente_est_refusee(self):
        with self.assertRaises(imp.ImportInvalide) as c:
            imp.depuis_lignes([{"url": "https://exemple.be/a", "moteur": "m"}],
                              entete={"provenance": "RECHERCHE DU RADAR"})
        self.assertIn(HORS, str(c.exception))

    def test_7_une_seule_ligne_non_declaree_refuse_le_fichier_csv(self):
        texte = ("provenance,moteur,date_execution,requete,url,titre,extrait,rang\n"
                 f"{HORS},m,2026-09-12T09:00:00+00:00,q,https://exemple.be/a,T,E,1\n"
                 ",m,2026-09-12T09:00:00+00:00,q,https://exemple.be/b,T,E,2\n")
        with self.assertRaises(imp.ImportInvalide):
            imp.charger(fichier(texte, ".csv"))

    def test_8_la_source_porte_la_marque_en_tete_du_nom(self):
        """En tête, parce que les rapports tronquent les noms À DROITE."""
        a, = charger([ligne("https://exemple.be/a", moteur="un-nom-tres-long-de-moteur")])
        self.assertTrue(a.nom.startswith(ex.PREFIXE))
        self.assertTrue(a.nom[:16].startswith(ex.PREFIXE))

    def test_9_un_nom_deja_qualifie_est_refuse(self):
        a = charger([ligne("https://exemple.be/a", moteur="import:moteur-a")])
        self.assertEqual(a, [])

    def test_10_les_quatre_etats_sont_nommes_et_distincts(self):
        valeurs = [e.value for e in ex.Execution]
        self.assertEqual(len(set(valeurs)), 4)
        self.assertIn("RECHERCHE RÉELLE PAR LE RADAR", valeurs)
        self.assertIn("RÉSULTAT IMPORTÉ — RECHERCHE EXTERNE", valeurs)
        self.assertIn("FIXTURE / DEMO", valeurs)
        self.assertIn("NON MESURÉ", valeurs)

    def test_11_la_provenance_est_conservee_en_base(self):     # démonstration 7
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        l, = ex.executions(self.cx)
        self.assertEqual(l.execution_par, HORS)
        self.assertEqual(l.moteur_declare, "moteur-a")
        self.assertIs(l.nature, ex.Execution.IMPORT_EXTERNE)

    def test_12_le_mode_externe_est_conserve(self):            # démonstration 8
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        for t in tr.toutes(self.cx):
            self.assertIs(ex.de_trouvaille(t), ex.Execution.IMPORT_EXTERNE)
        self.assertIn(HORS, ex.rapport(self.cx))

    def test_13_le_rapport_dit_que_le_radar_n_a_rien_interroge(self):
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        texte = ex.rapport(self.cx)
        self.assertIn("NON MESURÉ", texte)
        self.assertIn("Le radar n'a interrogé aucun moteur", texte)

    def test_14_le_csv_et_le_json_donnent_le_meme_resultat(self):
        cjson = imp.charger(fichier(
            {"provenance": HORS, "moteur": "m", "date_execution": "2026-09-12T09:00:00+00:00",
             "resultats": [{"requete": "q", "url": "https://exemple.be/a",
                            "titre": "T", "extrait": "E", "rang": 2}]}))
        ccsv = imp.charger(fichier(
            "provenance,moteur,date_execution,requete,url,titre,extrait,rang\n"
            f"{HORS},m,2026-09-12T09:00:00+00:00,q,https://exemple.be/a,T,E,2\n",
            ".csv"))
        for x, y in zip(cjson, ccsv):
            self.assertEqual(x.nom, y.nom)
            self.assertEqual([(r.url, r.titre, r.rang) for r in x.resultats_importes],
                             [(r.url, r.titre, r.rang) for r in y.resultats_importes])


# ════════════════════════════════════════════════════════════════ 8e-4C
class C_LeFichierEstUneEntreeNonFiable(unittest.TestCase):
    """Il n'a pas été produit par le radar. On ne lui fait aucune confiance."""

    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_1_url_manquante(self):
        a = charger([{"moteur": "m", "requete": "q", "url": ""}])
        self.assertEqual(a, [])

    def test_2_url_invalide_schema_non_consultable(self):
        for mauvaise in ("javascript:alert(1)", "data:text/html,<b>x",
                         "file:///etc/passwd", "pas une url", "https://",
                         "https://exemple.be/a b"):
            a = charger([{"moteur": "m", "requete": "q", "url": mauvaise}])
            self.assertEqual(a, [], mauvaise)

    def test_3_url_trop_longue(self):
        a = charger([ligne("https://exemple.be/" + "a" * imp.URL_MAX)])
        self.assertEqual(a, [])

    def test_4_titre_enorme_refuse_sans_reecrire_les_mots_du_moteur(self):
        lignes = [ligne("https://exemple.be/a", titre="T" * (imp.TITRE_MAX + 1))]
        a = charger(lignes)
        self.assertEqual(a, [])

    def test_5_extrait_enorme(self):
        a = charger([ligne("https://exemple.be/a",
                           extrait="E" * (imp.EXTRAIT_MAX + 1))])
        self.assertEqual(a, [])

    def test_6_rang_invalide_conserve_la_ligne_sans_inventer_de_rang(self):
        for mauvais in ("abc", -3, 0, imp.RANG_MAX + 1, "1.5"):
            a, = charger([ligne("https://exemple.be/a", rang=mauvais)])
            self.assertIsNone(a.resultats_importes[0].rang, mauvais)
        imp.inscrire(self.cx, a)
        self.assertIsNone(tr.lire(self.cx, "https://exemple.be/a").rang,
                          "un rang illisible ne doit pas être renuméroté")

    def test_7_moteur_absent(self):
        a = charger([{"url": "https://exemple.be/a", "requete": "q"}])
        self.assertEqual(a, [])

    def test_8_date_invalide_reste_inconnue_jamais_la_date_du_jour(self):
        a, = charger([ligne("https://exemple.be/a", date="hier matin")])
        self.assertEqual(a.date_execution, ex.DATE_INCONNUE)
        self.assertEqual(a.bilan.dates_inconnues, 1)

    def test_9_doublons(self):                                 # démonstration 4
        a, = charger([ligne("https://exemple.be/a", rang=1),
                      ligne("https://exemple.be/a/", rang=9),
                      ligne("https://www.exemple.be/a", rang=9)])
        self.assertEqual(len(a.resultats_importes), 1)
        self.assertEqual(a.bilan.doublons, 2)
        self.assertEqual(a.resultats_importes[0].rang, 1,
                         "la première occurrence garde son rang")

    def test_10_caracteres_inhabituels_nettoyes_et_comptes(self):
        """Octet nul, marque de direction, espace de largeur nulle.

        Ils sont RETIRÉS, pas tronqués : un caractère de contrôle n'est pas un
        mot, et le retirer ne réécrit pas ce que le moteur a dit. Les retraits
        sont comptés — la promesse « mot pour mot » porte sur les mots.
        """
        titre = "Un\u202etitre\u0000 net"
        a, = charger([ligne("https://exemple.be/a", titre=titre,
                            extrait="E\u200bx")])
        r = a.resultats_importes[0]
        for interdit in ("\u202e", "\u0000", "\u200b"):
            self.assertNotIn(interdit, r.titre)
            self.assertNotIn(interdit, r.extrait)
        self.assertIn("titre", r.titre)
        self.assertEqual(r.extrait, "Ex")
        self.assertEqual(a.bilan.caracteres_retires, 3)

    def test_11_contenu_vide(self):                            # démonstration 2
        with self.assertRaises(imp.ImportInvalide):
            imp.charger(fichier("", ".json"))
        with self.assertRaises(imp.ImportInvalide):
            imp.charger(fichier("   \n", ".csv"))

    def test_12_import_malforme(self):                         # démonstration 3
        with self.assertRaises(imp.ImportInvalide):
            imp.charger(fichier("{ceci n'est pas du JSON", ".json"))
        with self.assertRaises(imp.ImportInvalide):
            imp.charger(fichier(json.dumps({"provenance": HORS}), ".json"))
        with self.assertRaises(imp.ImportInvalide):
            imp.charger(fichier(json.dumps({"provenance": HORS,
                                            "resultats": "pas une liste"})))

    def test_13_aucun_refus_ne_disparait_en_silence(self):
        a, = charger([ligne("https://exemple.be/ok"),
                      {"moteur": "m", "url": "javascript:x"},
                      {"url": "https://exemple.be/b"}])
        self.assertEqual(a.bilan.refusees, 2)
        resume = a.bilan.resume()
        self.assertIn(imp.URL_INVALIDE, resume)
        self.assertIn(imp.MOTEUR_ABSENT, resume)
        self.assertIn("LIGNES REFUSÉES", resume)

    def test_14_aucune_donnee_malformee_ne_cree_quoi_que_ce_soit(self):
        """Le cœur de 8e-4C : une entrée abîmée ne produit RIEN."""
        mauvaises = [{"moteur": "m", "url": "javascript:x"},
                     {"url": "https://exemple.be/b"},
                     {"moteur": "m", "url": ""},
                     {"moteur": "m", "url": "https://exemple.be/c",
                      "titre": "T" * 5000}]
        a = charger(mauvaises)
        imp.inscrire(self.cx, a)
        for table in ("opportunites", "avis", "entreprises",
                      "pages_surveillees", "trouvailles"):
            self.assertEqual(
                self.cx.execute(f"SELECT count(*) c FROM {table}").fetchone()["c"],
                0, table)

    def test_15_le_fichier_introuvable_est_refuse_sans_rien_supposer(self):
        with self.assertRaises(imp.ImportInvalide):
            imp.charger("/chemin/qui/n/existe/pas.json")


# ════════════════════════════════════════════════════════════════ 8e-4D
class D_AucunRaccourciDansLaChaine(unittest.TestCase):
    """IMPORT ≠ OPPORTUNITÉ. Sept maillons, et aucun ne se saute."""

    def setUp(self):
        self.cx = ouvrir(":memory:")
        a, = charger([ligne("https://transporteur.example/partenaires"),
                      ligne("https://presse.example/actu",
                            titre="Fictif SA ouvre un dépôt")])
        imp.inscrire(self.cx, a)

    def test_1_aucune_opportunite_creee_directement(self):     # démonstration 9
        for table in ("opportunites", "avis"):
            self.assertEqual(
                self.cx.execute(f"SELECT count(*) c FROM {table}").fetchone()["c"],
                0, table)

    def test_2_aucune_entreprise_confirmee(self):              # démonstration 10
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM entreprises").fetchone()["c"], 0)

    def test_3_aucune_page_surveillee_d_office(self):
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM pages_surveillees")
            .fetchone()["c"], 0)

    def test_4_le_chainage_reste_celui_d_un_resultat_ordinaire(self):
        registre = RegistreEntreprises()
        bilan = chainage.chainer(self.cx, tr.toutes(self.cx), registre)
        self.assertEqual(bilan.pages_candidates, 2)
        for p in mod_pages.a_surveiller(self.cx, toutes=True):
            self.assertIs(p.statut, mod_pages.Statut.CANDIDATE)
            self.assertIs(p.acces, mod_pages.Acces.JAMAIS_CONSULTEE)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"], 0)

    def test_5_l_identite_reste_inconnue_apres_chainage(self):
        from radar import entreprises as ent, identite
        registre = RegistreEntreprises()
        chainage.chainer(self.cx, tr.toutes(self.cx), registre)
        ent.enregistrer(self.cx, registre)
        chainage.marquer_identites(self.cx, registre)
        for cle in registre.entreprises:
            self.assertIsNot(identite.lire(self.cx, cle).etat, Etat.CONFIRMEE)

    def test_6_7b_et_7c_ne_sont_pas_contournes(self):
        """Une page importée n'est pas qualifiée : rien n'a été collecté."""
        registre = RegistreEntreprises()
        chainage.chainer(self.cx, tr.toutes(self.cx), registre)
        for p in mod_pages.a_surveiller(self.cx, toutes=True):
            self.assertIs(p.qualification, mod_pages.Qualification.NON_QUALIFIEE)
        self.assertEqual(mod_pages.a_surveiller(self.cx), [])

    def test_7_une_societe_citee_ne_devient_pas_l_entreprise_du_domaine(self):
        registre = RegistreEntreprises()
        chainage.chainer(self.cx, tr.toutes(self.cx), registre)
        for cle in registre.entreprises:
            self.assertNotIn("Fictif", cle)

    def test_8_aucune_influence_sur_le_score(self):            # démonstration 11
        from tests.test_radar import MAINTENANT, moteur, opp
        a, b = opp(ref_source="I1"), opp(ref_source="I2")
        a.provenances = [{"source": "moteur-a", "circuit": circuit.DECOUVERTE}]
        b.provenances = [{"source": ex.qualifier("moteur-a"),
                          "circuit": circuit.DECOUVERTE}]
        self.assertEqual(moteur().analyser(a, MAINTENANT).score.total,
                         moteur().analyser(b, MAINTENANT).score.total,
                         "la nature de l'exécution ne vaut pas un point")


# ════════════════════════════════════════════════════════════════ 8e-4E
class E_LesMetriquesNeSeMelangentPas(unittest.TestCase):
    """Un import ne gonfle jamais les chiffres d'un moteur interrogé par nous."""

    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_1_plusieurs_moteurs_dans_un_meme_fichier(self):   # démonstration 5
        a = charger([ligne("https://exemple.be/a", moteur="moteur-a"),
                     ligne("https://exemple.be/b", moteur="moteur-b")])
        self.assertEqual(sorted(x.nom for x in a),
                         ["import:moteur-a", "import:moteur-b"])

    def test_2_meme_url_par_plusieurs_moteurs(self):           # démonstration 6
        a = charger([ligne("https://exemple.be/a", moteur="moteur-a", rang=1),
                     ligne("https://exemple.be/a", moteur="moteur-b", rang=7)])
        imp.inscrire(self.cx, a)
        self.assertEqual(len(tr.toutes(self.cx)), 2, "deux observations")
        g, = recoupement.grouper(tr.toutes(self.cx))
        self.assertTrue(g.multi_source)
        self.assertEqual(sorted(g.sources), ["import:moteur-a", "import:moteur-b"])

    def test_3_historique_conserve(self):                      # démonstration 14
        a = charger([ligne("https://exemple.be/a", moteur="moteur-a",
                           requete="q1", rang=1),
                     ligne("https://exemple.be/a", moteur="moteur-b",
                           requete="q2", rang=7)])
        imp.inscrire(self.cx, a)
        g, = recoupement.grouper(tr.toutes(self.cx))
        h = " ".join(g.historique())
        for attendu in ("import:moteur-a", "import:moteur-b", "rang 1",
                        "rang 7", "q1", "q2"):
            self.assertIn(attendu, h, attendu)
        self.assertEqual(sorted(g.requetes), ["q1", "q2"])

    def test_4_un_import_ne_gonfle_pas_un_moteur_reellement_interroge(self):
        """Le même nom déclaré, deux sources distinctes — par construction."""
        a, = charger([ligne("https://exemple.be/a", moteur="moteur-a")])
        imp.inscrire(self.cx, a)
        # Une recherche que le radar aurait réellement exécutée, même moteur.
        tr.inscrire(self.cx, Resultat(titre="T", url="https://exemple.be/b",
                                      extrait="E", requete="q",
                                      fournisseur="moteur-a", rang=1),
                    mode=Mode.REEL, source="moteur-a")
        m = recoupement.metriques_moteurs(self.cx)
        self.assertEqual(sorted(m), ["import:moteur-a", "moteur-a"])
        self.assertEqual(m["moteur-a"]["resultats"], 1)
        self.assertEqual(m["import:moteur-a"]["resultats"], 1)
        self.assertEqual(m["moteur-a"]["nature"], ex.Execution.RADAR.value)
        self.assertEqual(m["import:moteur-a"]["nature"],
                         ex.Execution.IMPORT_EXTERNE.value)

    def test_5_les_deux_compteurs_demandes(self):
        a = charger([ligne("https://exemple.be/a", requete="q1"),
                     ligne("https://exemple.be/b", requete="q2"),
                     ligne("https://exemple.be/c", requete="q2")])
        imp.inscrire(self.cx, a)
        m = ex.metriques(self.cx)
        self.assertEqual(m["resultats_importes_externes"], 3)
        self.assertEqual(m["requetes_importees_externes"], 2)

    def test_6_non_mesure_n_est_pas_zero_resultat(self):       # démonstration 13
        vide = ex.metriques(self.cx)
        self.assertTrue(vide[ex.Execution.NON_MESUREE.value],
                        "aucune recherche : NON MESURÉ")
        self.assertEqual(vide["requetes_importees_externes"], 0)

        imp.declarer_muette(self.cx, moteur="moteur-a", requete="q sans réponse")
        apres = ex.metriques(self.cx)
        self.assertFalse(apres[ex.Execution.NON_MESUREE.value])
        self.assertEqual(apres["executions_externes_muettes"], 1)
        self.assertEqual(apres["requetes_importees_externes"], 1)
        self.assertEqual(apres["resultats_importes_externes"], 0,
                         "0 résultat — et c'est une mesure")

    def test_7_un_export_vide_qui_declare_sa_requete_inscrit_un_zero(self):
        imp.importer(self.cx, fichier(
            {"provenance": HORS, "moteur": "moteur-a", "requete": "q",
             "date_execution": "2026-09-12T09:00:00+00:00", "resultats": []}))
        l, = ex.executions(self.cx)
        self.assertEqual(l.resultats, 0)
        self.assertTrue(l.muette)
        self.assertFalse(ex.metriques(self.cx)[ex.Execution.NON_MESUREE.value])

    def test_8_les_refus_ne_sont_pas_comptes_une_fois_par_requete(self):
        imp.importer(self.cx, fichier(
            {"provenance": HORS, "moteur": "moteur-a",
             "date_execution": "2026-09-12T09:00:00+00:00",
             "resultats": [{"requete": "q1", "url": "https://exemple.be/a"},
                           {"requete": "q2", "url": "https://exemple.be/b"},
                           {"requete": "q2", "url": "javascript:x"}]}))
        self.assertEqual(ex.metriques(self.cx)["refuses_a_l_import"], 1)

    def test_9_les_quatre_etats_dans_le_rapport(self):
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        for m in fx.depuis_fichier(RAPPEL):
            tr.depuis_moteur(self.cx, m, m.rechercher('"recherche transporteur" Belgique'))
        texte = ex.rapport(self.cx)
        for etat in ex.Execution:
            self.assertIn(etat.value, texte, etat.value)

    def test_10_la_marque_reste_lisible_dans_les_rapports_existants(self):
        a, = charger([ligne("https://exemple.be/a",
                            moteur="un-nom-de-moteur-vraiment-tres-long")])
        imp.inscrire(self.cx, a)
        self.assertIn(ex.PREFIXE, tr.rapport(self.cx))
        self.assertIn(ex.PREFIXE, recoupement.rapport(self.cx))

    def test_11_le_rapport_de_recoupement_nomme_la_nature(self):
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        texte = recoupement.rapport(self.cx)
        self.assertIn("NATURE", texte)
        self.assertIn(ex.Execution.IMPORT_EXTERNE.value, texte)


# ════════════════════════════════════════════════════════════════ 8e-4F
class F_CompatibiliteAvecLesEtapes8aA8d(unittest.TestCase):
    """Démonstration 12 — l'import se pose sur les rails existants."""

    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_1_8a_le_journal_des_trouvailles_lit_un_import(self):
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        t = tr.lire(self.cx, "https://exemple.be/a")
        self.assertFalse(t.lue)
        self.assertEqual(tr.urls_uniques(self.cx), ["https://exemple.be/a"])
        self.assertEqual(tr.metriques(self.cx)[Mode.REEL.value]["trouvailles"], 1)

    def test_2_8b_une_fixture_reste_une_fixture_a_cote_d_un_import(self):
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        for m in fx.depuis_fichier(RAPPEL):
            tr.depuis_moteur(self.cx, m, m.rechercher('"recherche transporteur" Belgique'))
        r = ex.repartition(self.cx)
        self.assertEqual(r[ex.Execution.IMPORT_EXTERNE.value], 1)
        self.assertGreater(r[ex.Execution.FIXTURE.value], 0)
        self.assertEqual(r[ex.Execution.RADAR.value], 0,
                         "le radar n'a interrogé personne")

    def test_3_8b_une_fixture_ne_peut_pas_se_faire_passer_pour_un_import(self):
        m = fx.depuis_fichier(RAPPEL)[0]
        self.assertIs(ex.de_moteur(m), ex.Execution.FIXTURE)
        self.assertIs(m.mode, Mode.DEMO)

    def test_4_8c_le_chainage_traite_un_import_comme_le_reste(self):
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        bilan = chainage.chainer(self.cx, tr.toutes(self.cx),
                                 RegistreEntreprises())
        self.assertEqual(bilan.trouvailles_lues, 1)
        self.assertEqual(bilan.entreprises_nouvelles, 1)
        self.assertEqual(bilan.pages_candidates, 1)

    def test_5_8d_le_recoupement_mesure_un_import(self):
        a = charger([ligne("https://exemple.be/a", moteur="moteur-a"),
                     ligne("https://exemple.be/a", moteur="moteur-b"),
                     ligne("https://exemple.be/c", moteur="moteur-b")])
        imp.inscrire(self.cx, a)
        r = recoupement.metriques_rappel(self.cx)
        self.assertEqual(r["resultats_bruts"], 3)
        self.assertEqual(r["urls_uniques"], 2)
        self.assertEqual(r["groupes_multi_sources"], 1)

    def test_6_8d_un_moteur_declare_non_interroge_reste_non_mesure(self):
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        m = recoupement.metriques_moteurs(
            self.cx, declares={"moteur-jamais-interroge": "clé absente"})
        case = m["moteur-jamais-interroge"]
        self.assertFalse(case["mesure"])
        self.assertEqual(case["resultats"], recoupement.NON_MESURE)
        self.assertEqual(case["nature"], ex.Execution.NON_MESUREE.value)

    def test_7_le_circuit_est_celui_de_la_decouverte(self):
        a, = charger([ligne("https://exemple.be/a")])
        imp.inscrire(self.cx, a)
        self.assertEqual(tr.lire(self.cx, "https://exemple.be/a").circuit,
                         circuit.DECOUVERTE)

    def test_8_reimporter_le_meme_fichier_ne_duplique_rien(self):
        chemin = fichier({"provenance": HORS, "moteur": "moteur-a",
                          "date_execution": "2026-09-12T09:00:00+00:00",
                          "resultats": [{"requete": "q",
                                         "url": "https://exemple.be/a",
                                         "titre": "T", "extrait": "E",
                                         "rang": 1}]})
        imp.importer(self.cx, chemin)
        imp.importer(self.cx, chemin)
        self.assertEqual(len(tr.toutes(self.cx)), 1)
        self.assertEqual(len(ex.executions(self.cx)), 1)


# ═════════════════════════════════════════════════ 8e-4-CORRECTION
class G_AucunRapportNePresenteUnImportCommeUneRechercheDuRadar(unittest.TestCase):
    """NON-RÉGRESSION — l'intitulé ambigu ne peut pas revenir.

    `trouvailles.rapport()` écrivait « DÉCOUVERTE RÉELLE » au-dessus d'un
    compte qui additionne deux choses différentes : ce que le radar a trouvé
    lui-même et ce qu'on lui a remis. Le chiffre était juste ; l'intitulé,
    lui, se lisait « le radar a cherché » — alors que le radar pouvait
    n'avoir interrogé personne.

    Le mode répond à « fabriqué ou réel ». Il ne répond pas à « qui est allé
    chercher ». L'intitulé est donc neutre, et la réponse à la seconde
    question vit dans `execution.rapport()`.
    """

    # Des affirmations, pas des mots isolés : ces rapports ont le DROIT de
    # parler du radar pour expliquer une règle. Ce qu'ils n'ont pas le droit
    # de faire, c'est d'AFFIRMER que le radar a exécuté la recherche.
    AFFIRMATIONS = ("découverte réelle", "recherche réelle par le radar",
                    "recherche exécutée par le radar", "trouvé par le radar",
                    "interrogé par le radar", "le radar a cherché")

    def setUp(self):
        self.cx = ouvrir(":memory:")
        a = charger([ligne("https://exemple.be/a", moteur="moteur-a"),
                     ligne("https://exemple.be/b", moteur="moteur-b")])
        imp.inscrire(self.cx, a)

    def test_1_l_intitule_ambigu_a_disparu_du_rapport(self):
        self.assertNotIn("DÉCOUVERTE RÉELLE", tr.rapport(self.cx))
        self.assertIn("TROUVAILLES EN MODE RÉEL", tr.rapport(self.cx))

    def test_2_l_intitule_ambigu_a_disparu_du_code(self):
        """Pour qu'il ne puisse pas revenir par un autre rapport."""
        for chemin in sorted(pathlib.Path("radar").glob("*.py")):
            source = chemin.read_text(encoding="utf-8")
            self.assertNotIn("DÉCOUVERTE RÉELLE", source, str(chemin))

    def test_3_aucun_rapport_n_affirme_que_le_radar_a_cherche(self):
        for nom, texte in (("trouvailles", tr.rapport(self.cx)),
                           ("recoupement", recoupement.rapport(self.cx))):
            for affirmation in self.AFFIRMATIONS:
                self.assertNotIn(affirmation, texte.lower(),
                                 f"{nom} : « {affirmation} »")

    def test_4_l_import_reste_visible_il_n_est_pas_masque(self):
        """Corriger l'intitulé ne doit pas faire disparaître l'information.

        « pas de disparition silencieuse » vaut aussi pour une correction de
        rapport : l'origine importée doit rester lisible.
        """
        for texte in (tr.rapport(self.cx), recoupement.rapport(self.cx)):
            self.assertIn(ex.PREFIXE, texte)

    def test_5_le_rapport_renvoie_a_celui_qui_tranche_la_question(self):
        self.assertIn("execution.rapport()", tr.rapport(self.cx))

    def test_6_execution_conserve_les_quatre_etats(self):
        texte = ex.rapport(self.cx)
        for etat in ex.Execution:
            self.assertIn(etat.value, texte, etat.value)

    def test_7_execution_dit_que_le_radar_n_a_rien_interroge(self):
        m = ex.metriques(self.cx)
        self.assertEqual(m[ex.Execution.RADAR.value], 0)
        self.assertEqual(m[ex.Execution.IMPORT_EXTERNE.value], 2)
        self.assertIn("Le radar n'a interrogé aucun moteur", ex.rapport(self.cx))

    def test_8_symetrie_une_vraie_recherche_du_radar_est_bien_comptee(self):
        """La correction ne doit pas rendre la recherche réelle invisible."""
        tr.inscrire(self.cx, Resultat(titre="T", url="https://exemple.be/c",
                                      extrait="E", requete="q",
                                      fournisseur="moteur-c", rang=1),
                    mode=Mode.REEL, source="moteur-c")
        m = ex.metriques(self.cx)
        self.assertEqual(m[ex.Execution.RADAR.value], 1)
        self.assertNotIn("Le radar n'a interrogé aucun moteur",
                         ex.rapport(self.cx))

    def test_9_aucun_calcul_n_a_bouge(self):
        """La correction est un INTITULÉ. Les chiffres sont inchangés."""
        m = tr.metriques(self.cx)
        self.assertEqual(m[Mode.REEL.value]["trouvailles"], 2)
        self.assertEqual(m[Mode.REEL.value]["urls_uniques"], 2)
        self.assertEqual(m[Mode.DEMO.value]["trouvailles"], 0)
        self.assertEqual(recoupement.metriques_rappel(self.cx)["resultats_bruts"], 2)


if __name__ == "__main__":
    unittest.main()
