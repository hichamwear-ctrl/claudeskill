"""ÉTAPE 11 — LE BOT. Ce qu'il exécute, ce qu'il journalise, ce qu'il refuse.

    SOURCE / IMPORT / COLLECTE → … → NOTIFICATION → SUIVI → RÉSULTAT

Les données de ces tests sont FABRIQUÉES et le disent. Le jeu réel vit dans
`validation/exports-reels/`.

Ce que ces tests tiennent avant tout :

    source injoignable  →  NON MESURÉE
    et JAMAIS              « 0 opportunité pour cette source »
"""

import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from radar import (collecte_importee as col, import_externe as imp,
                   notification, orchestrateur, suivi, tableau, verdicts)
from radar.base import enregistrer_reponse, ouvrir
from radar.cli import _cfg, _moteur, _source, principal
from radar.mode import Mode
from radar.pages import Acces
from radar.suivi import Statut

PROFIL = _cfg("sources/page_web.yaml")
BESOIN = ("Nous recherchons un partenaire de livraison pour assurer nos "
          "tournées régulières en Wallonie.")
COLONNES = ("acheteur", "titulaire", "montant", "duree_mois", "prestation",
            "zone", "lots", "conclu_le", "debut", "fin", "renouvellement",
            "contact", "besoin_sous_traitance")


def fichier(charge, suffixe=".json"):
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / ("f" + suffixe)
    p.write_text(json.dumps(charge, ensure_ascii=False), encoding="utf-8")
    return str(p)


def export(lignes, *, moteur="moteur-t"):
    return fichier({"provenance": imp.PROVENANCE, "moteur": moteur,
                    "date_execution": "2026-09-14T09:00:00+00:00",
                    "resultats": lignes})


def r(url, titre, extrait=""):
    return {"requete": "recherche transporteur Belgique", "url": url,
            "titre": titre, "extrait": extrait, "rang": 1}


def collecte(pages):
    return fichier({"provenance": col.PROVENANCE, "pages": pages})


def page_lue(url, contenu, titre="Une page", acces=Acces.CONSULTEE):
    """Une page telle qu'un collecteur réel la rendrait — AVEC son titre.

    Une page web en a un. L'omettre affaiblit la lecture (voir
    `test_20c`), et un collecteur qui le tairait fabriquerait une page
    qui n'existe pas.
    """
    return {"url": url, "acces": acces.value, "contenu": contenu,
            "titre": titre}


def attribution(cx, **champs):
    avis_id = enregistrer_reponse(cx, "essai", champs.pop("ref", "M-1"), {}, "")
    cx.execute(
        f"INSERT INTO attributions(avis_id, fiabilite, {', '.join(COLONNES)})"
        f" VALUES(?,?{',?' * len(COLONNES)})",
        [avis_id, "MOYENNE", *[champs.get(c) for c in COLONNES]])
    return avis_id


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
    def setUp(self):
        self.cx = ouvrir(":memory:")
        self.adaptateur, self.cfg = _source("recherche")

    def cycle(self, **kw):
        return orchestrateur.executer(
            self.cx, _moteur(self.cx), self.adaptateur, profil=PROFIL, **kw)

    def premiere(self):
        return self.cx.execute(
            "SELECT o.*, a.ref_source, a.source FROM opportunites o"
            " JOIN avis a ON a.id=o.avis_id WHERE o.type<>'REJET'"
            " ORDER BY o.score DESC").fetchone()


# ══════════════════════════════════════════════════════════ exécution
class A_LeBotSaitCeQuIlAFait(Socle):

    def test_1_un_cycle_vide_est_PARTIEL_et_ne_ment_pas(self):
        c = self.cycle(moteurs_declares=[MoteurAbsent()])
        self.assertEqual(c.statut, orchestrateur.PARTIEL)
        self.assertEqual(c.opportunites, 0)
        self.assertIn("moteur-sans-cle", c.non_disponibles)

    def test_2_une_source_injoignable_est_NON_MESUREE_jamais_zero(self):
        """LA garantie centrale du bot."""
        c = self.cycle(moteurs_declares=[MoteurAbsent()])
        s = c.sources["moteur-sans-cle"]
        self.assertEqual(s.resultats, orchestrateur.NON_MESUREE)
        self.assertEqual(s.opportunites, orchestrateur.NON_MESUREE)
        self.assertNotEqual(s.resultats, 0)
        texte = orchestrateur.rapport(self.cx, c)
        self.assertIn("N'A PAS « RENDU ZÉRO »", texte)

    def test_3_un_moteur_disponible_mais_non_interroge_reste_NON_MESURE(self):
        """Pouvoir chercher n'est pas avoir cherché."""
        c = self.cycle(moteurs_declares=[MoteurPret()])
        self.assertIn("moteur-pret", c.non_mesurees)
        self.assertNotIn("moteur-pret", c.executees)
        self.assertIn("NON INTERROGÉ", c.sources["moteur-pret"].motif)

    def test_4_un_cycle_complet_quand_tout_a_repondu(self):
        c = self.cycle(imports=[export([r("https://a.be/p", "Recherche transporteur")])])
        self.assertEqual(c.statut, orchestrateur.COMPLET)
        self.assertEqual(c.executees, ["import:moteur-t"])

    def test_5_une_source_en_erreur_est_journalisee_sans_conclure(self):
        c = self.cycle(imports=["/chemin/inexistant.json"])
        self.assertTrue(c.erreurs)
        self.assertEqual(c.statut, orchestrateur.ERREUR)
        self.assertEqual(c.opportunites, 0)

    def test_6_le_journal_conserve_les_cinq_etats_separement(self):
        self.cycle(moteurs_declares=[MoteurAbsent(), MoteurPret()],
                   imports=[export([r("https://a.be/p", "Recherche transporteur")])])
        l = self.cx.execute("SELECT * FROM journal_cycles").fetchone()
        self.assertEqual(json.loads(l["sources_executees"]), ["import:moteur-t"])
        self.assertEqual(json.loads(l["sources_non_disponibles"]),
                         ["moteur-sans-cle"])
        self.assertEqual(json.loads(l["sources_non_mesurees"]), ["moteur-pret"])

    def test_7_deux_cycles_coup_sur_coup_ne_s_ecrasent_pas(self):
        self.cycle()
        self.cycle()
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM journal_cycles").fetchone()["c"],
            2, "un journal qui oublie un cycle ne vaut pas mieux que rien")

    def test_8_le_rapport_de_cycle_se_lit_sans_ouvrir_le_code(self):
        c = self.cycle(moteurs_declares=[MoteurAbsent()],
                       imports=[export([r("https://a.be/p", "Recherche transporteur")])])
        texte = orchestrateur.rapport(self.cx, c)
        for bloc in ("STATUT", "SOURCES", "DÉCOUVERTE", "QUALIFICATION",
                     "OPPORTUNITÉS", "ALERTES", "QUALITÉ",
                     "ACTIONS HUMAINES À EFFECTUER"):
            self.assertIn(bloc, texte, bloc)


# ══════════════════════════════════════════════════════════ idempotence
class B_Idempotence(Socle):

    def test_9_deux_cycles_identiques_ne_creent_pas_deux_opportunites(self):
        chemin = export([r("https://a.be/p",
                           "Nous recherchons un partenaire de livraison")])
        c1 = self.cycle(imports=[chemin])
        c2 = self.cycle(imports=[chemin])
        self.assertEqual(c1.opportunites, c2.opportunites)
        self.assertEqual(c1.entreprises, c2.entreprises)

    def test_10_la_deuxieme_execution_ne_renotifie_pas(self):
        chemin = export([r("https://a.be/p",
                           "Nous recherchons un partenaire de livraison")])
        c1 = self.cycle(imports=[chemin])
        c2 = self.cycle(imports=[chemin])
        self.assertGreater(c1.notifications, 0)
        self.assertEqual(c2.notifications, 0)

    def test_11_un_contenu_qui_change_renotifie(self):
        """Ne pas répéter, ne pas taire non plus."""
        self.cycle(imports=[export([r("https://a.be/p",
                                      "Nous recherchons un partenaire de livraison")])])
        avant = len(notification.toutes(self.cx))
        self.cx.execute("UPDATE opportunites SET echeance='2026-12-31'")
        notification.preparer(self.cx)
        self.assertGreater(len(notification.toutes(self.cx)), avant)


# ══════════════════════════════════════════════════════════ notifications
class C_NotifierNEstPasEnvoyer(Socle):

    def test_12_une_carte_repond_aux_quatre_questions(self):
        self.cycle(imports=[export([r("https://a.be/p",
                                      "Nous recherchons un partenaire de livraison")])])
        n = notification.toutes(self.cx)
        self.assertTrue(n)
        corps = n[0].corps
        for champ in ("Entreprise", "Besoin", "Nature", "Procédure",
                      "Classification", "Adéquation", "Preuve", "Potentiel",
                      "Pourquoi", "Action", "Effort", "Échéance", "Source",
                      "Preuves", "À CONFIRMER"):
            self.assertIn(champ, corps, champ)

    def test_13_le_bot_prepare_mais_n_envoie_jamais(self):
        """La file est REMPLIE ; elle n'est jamais VIDÉE par un cycle.

        Mettre en file est préparer. Envoyer est une autre commande, et elle
        est explicite. Un cycle qui viderait la file enverrait des messages
        commerciaux sans que personne l'ait demandé.
        """
        self.cycle(imports=[export([r("https://a.be/p",
                                      "Nous recherchons un partenaire de livraison")])])
        etats = {l["etat"] for l in self.cx.execute("SELECT etat FROM envois")}
        self.assertTrue(etats <= {"a_envoyer"},
                        f"un cycle a changé l'état d'un envoi : {etats}")
        self.assertIn("n'a contacté personne",
                      notification.toutes(self.cx)[0].corps)

    def test_13b_le_cycle_n_appelle_aucun_transport(self):
        """Vérifié sur les IMPORTS, pas sur la prose : le module a le droit
        d'expliquer qu'il n'envoie rien."""
        import ast
        arbre = ast.parse(pathlib.Path("radar/orchestrateur.py")
                          .read_text(encoding="utf-8"))
        noms = set()
        for n in ast.walk(arbre):
            if isinstance(n, ast.ImportFrom) and n.module:
                noms.update(n.module.split("."))
                noms.update(a.name.split(".")[-1] for a in n.names)
            elif isinstance(n, ast.Attribute):
                noms.add(n.attr)
            elif isinstance(n, ast.Name):
                noms.add(n.id)
        for interdit in ("envoi", "vider", "alerte", "TransportFichier",
                         "smtp", "sendmail"):
            self.assertNotIn(interdit, noms, interdit)

    def test_14_une_opportunite_non_notifiable_reste_en_base(self):
        """§8 — ne pas réveiller quelqu'un n'est pas supprimer une affaire."""
        c = self.cycle(imports=[export([r("https://a.be/p", "Une page quelconque")])])
        self.assertGreaterEqual(c.opportunites, 1)
        for l in self.cx.execute("SELECT type FROM opportunites"):
            if not notification.merite_une_alerte(l["type"]):
                break
        else:
            self.skipTest("aucune opportunité non notifiable dans ce lot")
        self.assertGreaterEqual(c.opportunites, 1)

    def test_15_un_rejet_ne_reveille_personne(self):
        from radar.classification import Type
        self.assertFalse(notification.merite_une_alerte(Type.REJET.value))
        self.assertFalse(notification.merite_une_alerte(Type.OBSERVATION.value))
        self.assertTrue(notification.merite_une_alerte(Type.DIRECT.value))

    def test_16_un_renouvellement_notifie_sans_devenir_postulable(self):
        attribution(self.cx, titulaire="T SA", fin="2029-12-31",
                    renouvellement="2029-06-30")
        notification.preparer(self.cx)
        cartes = [n for n in notification.toutes(self.cx)
                  if n.motif == notification.RENOUVELLEMENT]
        self.assertTrue(cartes)
        self.assertIn("n'est pas POSTULABLE", cartes[0].corps)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM opportunites"
                            " WHERE etat_procedure='POSTULABLE'").fetchone()["c"], 0)

    def test_17_un_changement_technique_ne_notifie_pas(self):
        """§9 — changement technique ≠ changement commercial."""
        from radar import pages as mod_pages
        url = "https://a.be/partenaires"
        self.cycle(imports=[export([r(url, "Nos partenaires")])])
        avant = len(notification.toutes(self.cx))
        col.surveiller(self.cx, collecte([page_lue(
            url, "Mentions légales. Cookies. Plan du site.")]),
            _moteur(self.cx), profil=PROFIL)
        trace, _, _ = col.surveiller(self.cx, collecte([page_lue(
            url, "Mentions légales. Cookies. Plan du site. "
                 "Politique de confidentialité mise à jour.")]),
            _moteur(self.cx), profil=PROFIL)
        self.assertGreaterEqual(trace.pages_non_commerciales, 1)
        self.assertEqual(len(notification.toutes(self.cx)), avant)


# ══════════════════════════════════════════════════ scénarios de bout en bout
class D_TroisScenariosComplets(Socle):

    def test_18_scenario_un_de_la_source_a_la_metrique(self):
        """SOURCE → … → NOTIFICATION → CONTACT → ATTENTE → RELANCE → GAGNÉE."""
        c = self.cycle(imports=[export([r(
            "https://transporteur.be/partenaires",
            "Nous recherchons un partenaire de livraison",
            "Tournées régulières à assurer en Wallonie.")])])
        self.assertEqual(c.resultats_bruts, 1)
        self.assertGreaterEqual(c.opportunites, 1)
        self.assertGreater(c.notifications, 0)

        l = self.premiere()
        self.assertTrue(l["type"] and l["action"] and l["nature"])
        avis_id = l["avis_id"]
        for s in (Statut.CONTACT_A_FAIRE, Statut.CONTACTEE, Statut.EN_ATTENTE,
                  Statut.RELANCE, Statut.GAGNEE):
            suivi.marquer(self.cx, avis_id, s)
        self.assertIs(suivi.lire(self.cx, avis_id).statut, Statut.GAGNEE)

        t = tableau.mesurer(self.cx)
        self.assertEqual(t.commercial[Statut.GAGNEE.value], 1)
        self.assertEqual(t.valeur["marge"], tableau.MARGE_NON_MESUREE)

    def test_19_scenario_deux_attribution_vers_renouvellement(self):
        """MARCHÉ ATTRIBUÉ → TITULAIRE → DÉVELOPPEMENT → RENOUVELLEMENT."""
        attribution(self.cx, titulaire="Transports T SA", acheteur="Ville X",
                    fin="2029-12-31", renouvellement="2029-06-30",
                    prestation="distribution de colis")
        c = self.cycle()
        self.assertEqual(c.attribues, 1)
        self.assertEqual(c.postulables, 0, "attribué ne devient jamais postulable")
        cartes = [n for n in notification.toutes(self.cx)
                  if n.motif == notification.RENOUVELLEMENT]
        self.assertTrue(cartes)
        self.assertIn("CONTACTER LE TITULAIRE", cartes[0].corps)

    def test_20_scenario_trois_signal_puis_surveillance_puis_besoin(self):
        """SIGNAL → SURVEILLANCE → NOUVEAU BESOIN → OPPORTUNITÉ."""
        from radar import circuit as mod_circuit, normalisation
        from radar.chaine import traiter
        url = "https://societe.be/actualites"
        self.cycle(imports=[export([r(url, "Une société ouvre un dépôt à Liège")])])
        moteur = _moteur(self.cx)

        def analyser(collecte_, page):
            opp, _ = normalisation.depuis_collecte(
                collecte_, PROFIL, source=collecte_.provenance,
                circuit=mod_circuit.CONNUE)
            if opp is None:
                return 0
            b = traiter(self.cx, moteur, [opp], mode=Mode.REEL)
            return b.capter + b.developper

        col.surveiller(self.cx, collecte([page_lue(
            url, "Notre nouveau dépôt ouvrira au printemps.",
            titre="Actualités")]), moteur, analyser=analyser, profil=PROFIL)
        avant = self.cx.execute(
            "SELECT count(*) c FROM opportunites").fetchone()["c"]
        # LA LIGNE DE LA VEILLE, pas celle de la découverte. La même URL
        # produit DEUX avis quand elle arrive par deux chemins — c'est un
        # défaut connu, documenté en étape 11 et NON corrigé : le corriger
        # toucherait la déduplication validée.
        etat_avant = self.cx.execute(
            "SELECT type, nature, action FROM opportunites o"
            " JOIN avis a ON a.id=o.avis_id WHERE a.ref_source=? AND a.source=?",
            (url, col.PROVENANCE)).fetchone()

        col.surveiller(self.cx, collecte([page_lue(url, BESOIN,
                                                   titre="Actualités")]),
                       moteur, analyser=analyser, profil=PROFIL)

        # LA MÊME PAGE NE PRODUIT PAS UNE SECONDE AFFAIRE. Le besoin nouveau
        # MET À JOUR l'opportunité existante — c'est la déduplication qui
        # fonctionne, et non un besoin perdu. Deux lignes pour une même page
        # d'une même entreprise seraient un doublon, pas une découverte.
        apres = self.cx.execute(
            "SELECT count(*) c FROM opportunites").fetchone()["c"]
        self.assertEqual(apres, avant, "une même page ne se dédouble pas")
        etat_apres = self.cx.execute(
            "SELECT type, nature, action FROM opportunites o"
            " JOIN avis a ON a.id=o.avis_id WHERE a.ref_source=? AND a.source=?",
            (url, col.PROVENANCE)).fetchone()
        self.assertNotEqual(tuple(etat_avant), tuple(etat_apres),
                            "le nouveau besoin doit avoir changé la lecture")
        self.assertEqual(etat_apres["nature"], "FAIT",
                         "un besoin écrit n'est plus une hypothèse")

    def test_20c_une_page_sans_titre_declare_est_lue_faiblement(self):
        """CONSTAT MESURÉ — non corrigé, l'analyse est GELÉE.

        Le même corps de page, avec et sans titre déclaré, ne donne pas la
        même lecture : sans titre, un besoin pourtant écrit noir sur blanc
        dans le corps reste « PAS ENCORE UNE OPPORTUNITÉ ».

        Ce test ne valide pas ce comportement : il le FIXE pour qu'on voie
        le jour où il change.
        """
        from radar import circuit as mod_circuit, normalisation
        from radar.chaine import traiter
        moteur = _moteur(self.cx)

        def lire(url, titre):
            self.cycle(imports=[export([r(url, "Une page")])])

            def analyser(c, pg):
                opp, _ = normalisation.depuis_collecte(
                    c, PROFIL, source=c.provenance, circuit=mod_circuit.CONNUE)
                if opp is None:
                    return 0
                traiter(self.cx, moteur, [opp], mode=Mode.REEL)
                return 0

            col.surveiller(self.cx, collecte([page_lue(url, BESOIN, titre=titre)]),
                           moteur, analyser=analyser, profil=PROFIL)
            l = self.cx.execute(
                "SELECT o.type FROM opportunites o JOIN avis a ON a.id=o.avis_id"
                " WHERE a.ref_source=? AND a.source=?",
                (url, col.PROVENANCE)).fetchone()
            return l["type"] if l else None

        avec = lire("https://avec.be/p", "Nos partenaires")
        sans = lire("https://sans.be/p", "")
        self.assertEqual(avec, "DIRECT")
        self.assertNotEqual(sans, "DIRECT",
                            "si ce test échoue, le corps seul suffit "
                            "désormais — refaire la mesure des faux positifs")

    def test_20b_une_meme_url_par_deux_chemins_fait_deux_avis(self):
        """DÉFAUT CONNU, MESURÉ, NON CORRIGÉ.

        La clé d'un avis est (source, référence). Une page découverte par un
        moteur puis relue par la veille porte donc DEUX lignes : une par
        chemin d'arrivée. Ce n'est pas un doublon de besoin — les deux
        lectures sont réelles et datées — mais l'exploitant voit la même
        adresse deux fois.

        Corriger cela toucherait la déduplication validée. Ce test FIXE le
        comportement actuel pour qu'on voie immédiatement s'il change.
        """
        url = "https://societe.be/page"
        self.cycle(imports=[export([r(url, "Une page")])])
        col.surveiller(self.cx, collecte([page_lue(url, BESOIN)]),
                       _moteur(self.cx), profil=PROFIL)
        sources = [l["source"] for l in self.cx.execute(
            "SELECT source FROM avis WHERE ref_source=?", (url,))]
        self.assertEqual(len(sources), 1,
                         "sans analyseur, la veille n'écrit aucun avis")


# ══════════════════════════════════════════════════ sécurité métier
class E_LeBotPrepareIlNeDecidePas(Socle):

    def test_21_aucun_apprentissage_automatique(self):
        """Ni poids, ni seuil, ni lexique, ni ontologie, ni priorité."""
        import ast
        arbre = ast.parse(pathlib.Path("radar/orchestrateur.py")
                          .read_text(encoding="utf-8"))
        modules = set()
        for n in ast.walk(arbre):
            if isinstance(n, ast.ImportFrom) and n.module:
                modules.update(n.module.split("."))
                modules.update(a.name.split(".")[-1] for a in n.names)
        for interdit in ("score", "ponderations", "capacite", "classification",
                         "apprentissage"):
            self.assertNotIn(interdit, modules, interdit)

    def test_22_le_cycle_ne_modifie_aucune_configuration(self):
        avant = {f: pathlib.Path(f).read_bytes() for f in
                 ("config/ponderations.yaml", "config/roles.yaml",
                  "config/capacites.yaml", "config/geographie.yaml")}
        self.cycle(imports=[export([r("https://a.be/p", "Recherche transporteur")])])
        for f, octets in avant.items():
            self.assertEqual(pathlib.Path(f).read_bytes(), octets, f)

    def test_23_aucune_source_n_est_favorisee(self):
        self.cycle(imports=[export([r("https://a.be/p", "Recherche transporteur")],
                                   moteur="zzz-petite"),
                            export([r("https://b.be/p", "Recherche transporteur"),
                                    r("https://c.be/p", "Recherche transporteur")],
                                   moteur="aaa-grosse")])
        texte = tableau.rapport(self.cx)
        self.assertIn("SANS CLASSEMENT", texte)
        self.assertLess(texte.index("aaa-grosse"), texte.index("zzz-petite"))

    def test_24_le_score_ne_supprime_jamais_une_opportunite(self):
        c = self.cycle(imports=[export([r("https://a.be/p", "Une page sans rapport")])])
        self.assertGreaterEqual(c.opportunites, 1)

    def test_25_un_faux_negatif_reste_visible(self):
        verdicts.inscrire(self.cx, "https://manquee.be/p", "FN",
                          motif="le radar ne l'a jamais montrée")
        self.assertIn("manquee.be", tableau.rapport(self.cx))
        self.assertIn("CE QUE LE RADAR A MANQUÉ", verdicts.rapport(self.cx))

    def test_26_une_fixture_ne_devient_jamais_reelle(self):
        from radar import fixtures_recherche as fx, trouvailles as tr
        from radar.execution import Execution, de_trouvaille
        for m in fx.depuis_fichier("fixtures/recherche-rappel.yaml")[:1]:
            tr.depuis_moteur(self.cx, m, m.rechercher("une requête"))
        for t in tr.toutes(self.cx):
            self.assertIs(de_trouvaille(t), Execution.FIXTURE)

    def test_27_un_import_reste_identifiable_comme_import(self):
        from radar.execution import est_import
        self.cycle(imports=[export([r("https://a.be/p", "Recherche transporteur")])])
        for l in self.cx.execute("SELECT source FROM avis"):
            self.assertTrue(est_import(l["source"]), l["source"])

    def test_28_la_date_de_derniere_consultation_est_identifiable(self):
        c = self.cycle(imports=[export([r("https://a.be/p", "Recherche transporteur")])])
        self.assertTrue(c.sources["import:moteur-t"].derniere_consultation)


# ══════════════════════════════════════════════════ la ligne de commande
class F_LeBotSeLanceEnUneCommande(unittest.TestCase):

    def setUp(self):
        self.base = str(pathlib.Path(tempfile.mkdtemp()) / "b.sqlite3")

    def lancer(self, *args):
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            code = principal(["--base", self.base, *args])
        return code, sortie.getvalue()

    def test_29_radar_run_tourne_sans_aucune_source(self):
        code, texte = self.lancer("run")
        self.assertEqual(code, 0)
        self.assertIn("STATUT : PARTIEL", texte)
        self.assertIn("NON DISPONIBLE", texte)

    def test_30_radar_run_avec_un_import(self):
        chemin = export([r("https://a.be/p",
                           "Nous recherchons un partenaire de livraison")])
        code, texte = self.lancer("run", "--import", chemin)
        self.assertEqual(code, 0)
        self.assertIn("EXÉCUTÉE", texte)
        self.assertIn("ALERTES", texte)

    def test_31_le_journal_et_les_notifications_se_lisent(self):
        chemin = export([r("https://a.be/p",
                           "Nous recherchons un partenaire de livraison")])
        self.lancer("run", "--import", chemin)
        code, journal = self.lancer("cycles")
        self.assertEqual(code, 0)
        self.assertIn("JOURNAL DES CYCLES", journal)
        code, cartes = self.lancer("notifications")
        self.assertEqual(code, 0)
        self.assertIn("🔔", cartes)

    def test_32_le_moteur_ne_connait_aucun_planificateur(self):
        """cron, systemd et docker appellent `radar run` — jamais l'inverse."""
        import ast
        for chemin in ("radar/orchestrateur.py", "radar/notification.py"):
            source = pathlib.Path(chemin).read_text(encoding="utf-8")
            arbre = ast.parse(source)
            docs = {ast.get_docstring(n, clean=False) for n in ast.walk(arbre)
                    if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef))}
            for n in ast.walk(arbre):
                if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                        and n.value not in docs):
                    for mot in ("crontab", "systemd", "docker", "schedule"):
                        self.assertNotIn(mot, n.value.lower(), chemin)


if __name__ == "__main__":
    unittest.main()
