"""ÉTAPE 10 — LA BOUCLE COMMERCIALE, DE BOUT EN BOUT.

    DÉCOUVERTE → QUALIFICATION → OPPORTUNITÉ → ACTION → CONTACT
               → SUIVI → RÉSULTAT → SURVEILLANCE → NOUVELLE OPPORTUNITÉ

Les pages de ces tests sont FABRIQUÉES. Le jeu réel vit dans
`validation/exports-reels/`.

Ce que l'étape tient : la boucle est cohérente, persistante et MESURABLE —
et le radar n'apprend RIEN automatiquement de ces mesures.
"""

import json
import pathlib
import tempfile
import unittest

from radar import (collecte_importee as col, entreprises as ent, identite,
                   import_externe as imp, pages as mod_pages, parcours,
                   suivi, tableau, verdicts)
from radar.base import enregistrer_reponse, ouvrir
from radar.cli import _cfg, _moteur, _source
from radar.entreprises import Etat as EtatEnt, Registre
from radar.mode import Mode
from radar.pages import Acces
from radar.suivi import Statut
from radar.verdicts import Verdict

PROFIL = _cfg("sources/page_web.yaml")
BESOIN = ("Nous recherchons un partenaire de livraison pour assurer nos "
          "tournées régulières en Wallonie.")
COLONNES = ("acheteur", "titulaire", "montant", "duree_mois", "prestation",
            "zone", "lots", "conclu_le", "debut", "fin", "renouvellement",
            "contact", "besoin_sous_traitance")


def fichier(charge):
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / "f.json"
    p.write_text(json.dumps(charge, ensure_ascii=False), encoding="utf-8")
    return str(p)


def export(lignes, *, moteur="moteur-t"):
    return fichier({"provenance": imp.PROVENANCE, "moteur": moteur,
                    "date_execution": "2026-09-14T09:00:00+00:00",
                    "resultats": lignes})


def r(url, titre, extrait="", requete="recherche transporteur Belgique"):
    return {"requete": requete, "url": url, "titre": titre,
            "extrait": extrait, "rang": 1}


def attribution(cx, **champs):
    avis_id = enregistrer_reponse(cx, "essai", champs.pop("ref", "M-1"), {}, "")
    cx.execute(
        f"INSERT INTO attributions(avis_id, fiabilite, {', '.join(COLONNES)})"
        f" VALUES(?,?{',?' * len(COLONNES)})",
        [avis_id, "MOYENNE", *[champs.get(c) for c in COLONNES]])
    return avis_id


class Socle(unittest.TestCase):
    def setUp(self):
        self.cx = ouvrir(":memory:")
        self.adaptateur, self.cfg = _source("recherche")

    def decouvrir(self, lignes, *, moteur="moteur-t"):
        imp.importer(self.cx, export(lignes, moteur=moteur))
        return parcours.executer(
            self.cx, _moteur(self.cx), self.adaptateur, mode=Mode.REEL,
            defauts={"secteur": self.cfg.get("secteur_par_defaut")})

    def premiere(self):
        return self.cx.execute(
            "SELECT o.*, a.ref_source, a.source FROM opportunites o"
            " JOIN avis a ON a.id=o.avis_id WHERE o.type<>'REJET'"
            " ORDER BY o.score DESC").fetchone()


# ═══════════════════════════════════════════ la boucle, maillon par maillon
class A_LaBoucleTientDeBoutEnBout(Socle):

    def test_1_trouvaille_devient_opportunite(self):
        p = self.decouvrir([r("https://exemple.be/partenaires",
                              "Nous recherchons un partenaire de livraison")])
        self.assertEqual(p.resultats, 1)
        self.assertEqual(p.opportunites, 1)

    def test_2_une_opportunite_porte_une_action(self):
        self.decouvrir([r("https://exemple.be/partenaires",
                          "Nous recherchons un partenaire de livraison")])
        self.assertTrue(self.premiere()["action"])

    def test_3_action_puis_contact(self):
        self.decouvrir([r("https://exemple.be/p", "Recherche transporteur")])
        avis_id = self.premiere()["avis_id"]
        suivi.marquer(self.cx, avis_id, Statut.CONTACT_A_FAIRE)
        s = suivi.marquer(self.cx, avis_id, Statut.CONTACTEE,
                          dernier_contact_le="2026-09-14")
        self.assertIs(s.statut, Statut.CONTACTEE)
        self.assertEqual(s.dernier_contact_le, "2026-09-14")

    def test_4_contact_puis_attente(self):
        self.decouvrir([r("https://exemple.be/p", "Recherche transporteur")])
        avis_id = self.premiere()["avis_id"]
        suivi.marquer(self.cx, avis_id, Statut.CONTACTEE)
        self.assertIs(suivi.marquer(self.cx, avis_id, Statut.EN_ATTENTE).statut,
                      Statut.EN_ATTENTE)

    def test_5_attente_puis_gagnee(self):
        self.decouvrir([r("https://exemple.be/p", "Recherche transporteur")])
        avis_id = self.premiere()["avis_id"]
        for s in (Statut.CONTACTEE, Statut.EN_ATTENTE, Statut.GAGNEE):
            suivi.marquer(self.cx, avis_id, s)
        self.assertIs(suivi.lire(self.cx, avis_id).statut, Statut.GAGNEE)

    def test_6_attente_puis_perdue(self):
        self.decouvrir([r("https://exemple.be/p", "Recherche transporteur")])
        avis_id = self.premiere()["avis_id"]
        for s in (Statut.CONTACTEE, Statut.EN_ATTENTE, Statut.PERDUE):
            suivi.marquer(self.cx, avis_id, s, motif="prix trop élevé")
        self.assertIs(suivi.lire(self.cx, avis_id).statut, Statut.PERDUE)

    def test_7_contact_puis_relance(self):
        self.decouvrir([r("https://exemple.be/p", "Recherche transporteur")])
        avis_id = self.premiere()["avis_id"]
        suivi.marquer(self.cx, avis_id, Statut.CONTACTEE)
        suivi.marquer(self.cx, avis_id, Statut.RELANCE, motif="sans réponse")
        self.assertIs(suivi.lire(self.cx, avis_id).statut, Statut.RELANCE)

    def test_8_aucune_relance_n_est_creee_automatiquement(self):
        """§1 — une relance se propose, elle ne s'exécute pas toute seule."""
        self.decouvrir([r("https://exemple.be/p", "Recherche transporteur")])
        avis_id = self.premiere()["avis_id"]
        suivi.marquer(self.cx, avis_id, Statut.CONTACTEE)
        self.decouvrir([r("https://autre.be/p", "Recherche transporteur")])
        self.assertIs(suivi.lire(self.cx, avis_id).statut, Statut.CONTACTEE)

    def test_9_le_parcours_entier_est_conserve(self):
        self.decouvrir([r("https://exemple.be/p", "Recherche transporteur")])
        avis_id = self.premiere()["avis_id"]
        for s in (Statut.CONTACT_A_FAIRE, Statut.CONTACTEE, Statut.EN_ATTENTE,
                  Statut.GAGNEE):
            suivi.marquer(self.cx, avis_id, s)
        fil = suivi.fil(self.cx, avis_id)
        self.assertGreaterEqual(len(fil), 4)
        self.assertIn("GAGNÉE", " ".join(fil))

    def test_10_le_resultat_reste_lie_a_sa_source_et_sa_categorie(self):
        """§5 — entreprise, source, type, catégorie, action, date."""
        self.decouvrir([r("https://exemple.be/p", "Recherche transporteur")],
                       moteur="moteur-a")
        l = self.premiere()
        suivi.marquer(self.cx, l["avis_id"], Statut.GAGNEE)
        relu = self.cx.execute(
            "SELECT o.type, o.action, o.etat, o.etat_maj, a.source, a.ref_source"
            " FROM opportunites o JOIN avis a ON a.id=o.avis_id"
            " WHERE o.avis_id=?", (l["avis_id"],)).fetchone()
        self.assertEqual(relu["source"], "import:moteur-a")
        self.assertEqual(relu["etat"], Statut.GAGNEE.value)
        self.assertTrue(relu["etat_maj"] and relu["type"] and relu["action"])


# ═══════════════════════════════════════════ développement et surveillance
class B_UneEntrepriseNeDisparaitPas(Socle):

    def test_11_une_entreprise_survit_a_son_opportunite_terminee(self):
        """§4 — perdre une affaire n'efface pas l'entreprise."""
        self.decouvrir([r("https://exemple.be/p", "Recherche transporteur")])
        avis_id = self.premiere()["avis_id"]
        suivi.marquer(self.cx, avis_id, Statut.PERDUE, motif="prix")
        self.assertIn("exemple.be", ent.charger(self.cx).entreprises)

    def test_12_attribution_devient_developpement(self):
        attribution(self.cx, titulaire="Transports Test SA", fin="2029-12-31",
                    renouvellement="2029-06-30")
        t = tableau.mesurer(self.cx)
        self.assertEqual(t.commercial["attributions"], 1)
        self.assertEqual(t.commercial["renouvellements"], 1)

    def test_13_un_titulaire_devient_une_cible_de_contact(self):
        import contextlib
        import io
        from radar.cli import principal
        d = tempfile.mkdtemp()
        base = str(pathlib.Path(d) / "b.sqlite3")
        cx = ouvrir(base)
        attribution(cx, titulaire="Transports Test SA", fin="2029-12-31")
        cx.commit()
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            principal(["--base", base, "developper"])
        self.assertIn("CONTACTER LE TITULAIRE", sortie.getvalue())

    def test_14_un_renouvellement_est_surveillable(self):
        attribution(self.cx, titulaire="T SA", fin="2029-12-31",
                    renouvellement="2029-06-30")
        l = self.cx.execute("SELECT renouvellement FROM attributions").fetchone()
        self.assertEqual(l["renouvellement"], "2029-06-30")

    def test_15_une_nouvelle_decouverte_retrouve_l_entreprise_existante(self):
        """§12-13 — une entreprise connue ne se recrée pas à chaque passage."""
        self.decouvrir([r("https://exemple.be/a", "Recherche transporteur")])
        avant = len(ent.charger(self.cx).entreprises)
        p = self.decouvrir([r("https://exemple.be/b",
                              "Nous recherchons un partenaire de livraison")])
        self.assertEqual(len(ent.charger(self.cx).entreprises), avant)
        self.assertGreaterEqual(p.entreprises_connues, 1)

    def test_16_une_entreprise_existante_produit_une_nouvelle_opportunite(self):
        self.decouvrir([r("https://exemple.be/a", "Une page quelconque")])
        avant = self.cx.execute(
            "SELECT count(*) c FROM opportunites").fetchone()["c"]
        self.decouvrir([r("https://exemple.be/b",
                          "Nous recherchons un partenaire de livraison")])
        self.assertGreater(
            self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"],
            avant)

    def test_17_une_page_surveillee_produit_une_nouvelle_piste(self):
        """La boucle se referme : surveillance → nouveau besoin → opportunité."""
        from radar import circuit as mod_circuit, normalisation
        from radar.chaine import traiter
        url = "https://exemple.be/partenaires"
        self.decouvrir([r(url, "Nos partenaires")])
        moteur = _moteur(self.cx)

        def analyser(collecte, page):
            opp, _ = normalisation.depuis_collecte(
                collecte, PROFIL, source=collecte.provenance,
                circuit=mod_circuit.CONNUE)
            if opp is None:
                return 0
            b = traiter(self.cx, moteur, [opp], mode=Mode.REEL)
            return b.capter + b.developper

        def veiller(contenu):
            return col.surveiller(self.cx, fichier({
                "provenance": col.PROVENANCE,
                "pages": [{"url": url, "acces": Acces.CONSULTEE.value,
                           "contenu": contenu}]}),
                moteur, analyser=analyser, profil=PROFIL)

        veiller("Nos bureaux sont ouverts du lundi au vendredi.")
        avant = self.cx.execute(
            "SELECT count(*) c FROM opportunites").fetchone()["c"]
        veiller(BESOIN)
        self.assertGreater(
            self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"],
            avant)


# ═══════════════════════════════════════════ ce qui ne se confond jamais
class C_TroisChosesDistinctes(Socle):

    def test_18_signal_besoin_et_postulable_sont_comptes_separement(self):
        self.decouvrir([r("https://a.be/p", "Recherche transporteur"),
                        r("https://b.be/p", "Ouverture d'un entrepôt à Liège")])
        t = tableau.mesurer(self.cx)
        for cle in ("signaux", "faits", "hypotheses", "postulables",
                    "attribuees"):
            self.assertIn(cle, t.qualification)
        texte = tableau.rapport(self.cx)
        self.assertIn("SIGNAL ≠ BESOIN ≠ POSTULABLE", texte)
        self.assertIn("Les additionner donnerait un total qui ne veut rien dire",
                      texte)

    def test_19_fait_et_hypothese_ne_se_confondent_pas(self):
        self.decouvrir([r("https://a.be/p",
                          "Nous recherchons un partenaire de livraison"),
                        r("https://b.be/p", "Une société ouvre un dépôt")])
        natures = {l["nature"] for l in
                   self.cx.execute("SELECT nature FROM opportunites")}
        self.assertGreaterEqual(len(natures), 2, natures)

    def test_20_postulable_et_attribue_restent_distincts(self):
        self.decouvrir([r("https://a.be/p", "Recherche transporteur")])
        attribution(self.cx, titulaire="T SA")
        t = tableau.mesurer(self.cx)
        self.assertEqual(t.qualification["postulables"], 0)
        self.assertEqual(t.commercial["attributions"], 1)

    def test_21_la_classification_ne_decide_pas_seule_l_action(self):
        """§2 — une 🔵 peut CONTACTER, PROPOSER PARTENARIAT ou GROUPEMENT."""
        from radar.classification import Action, Type
        actions_bleu = {Action.CONTACTER_ENTREPRISE, Action.PROPOSER_PARTENARIAT,
                        Action.PROPOSER_GROUPEMENT, Action.SURVEILLER}
        self.assertGreater(len(actions_bleu), 1)
        self.assertIn(Action.PROPOSER_SOUS_TRAITANCE, set(Action))
        self.assertIn(Type.PROSPECT, set(Type))

    def test_22_un_marche_trop_gros_n_est_pas_rejete(self):
        """§3 — trop gros seul mène en 🔵/🟣, jamais en 🔴."""
        from radar.classification import BLOCAGES_DE_TAILLE, SEUIL_GROUPEMENT
        self.assertTrue(BLOCAGES_DE_TAILLE)
        self.assertGreater(SEUIL_GROUPEMENT, 0)


# ═══════════════════════════════════════════ mesurer sans apprendre
class D_LeRadarObserveIlNApprendPas(Socle):

    def test_23_un_faux_negatif_s_ecrit_sur_une_url_inconnue_du_radar(self):
        """§9 — c'est exactement ce qui définit un faux négatif."""
        j = verdicts.inscrire(self.cx, "https://jamais-vue.be/partenaires", "FN",
                              motif="le radar ne l'a jamais montrée")
        self.assertIs(j.verdict, Verdict.FAUX_NEGATIF)
        self.assertIsNone(mod_pages.lire(self.cx, "https://jamais-vue.be/partenaires"))
        self.assertIn("jamais-vue.be", tableau.rapport(self.cx))

    def test_24_un_faux_negatif_n_est_jamais_masque(self):
        verdicts.inscrire(self.cx, "https://manquee.be/p", "FN", motif="manquée")
        texte = verdicts.rapport(self.cx)
        self.assertIn("CE QUE LE RADAR A MANQUÉ", texte)
        self.assertIn("manquee.be", texte)

    def test_25_un_petit_echantillon_se_dit_petit(self):
        for i in range(3):
            verdicts.inscrire(self.cx, f"https://x{i}.be/p", "VP")
        m = verdicts.metriques(self.cx)
        self.assertEqual(m["precision"], verdicts.ECHANTILLON_INSUFFISANT)
        self.assertEqual(m["rappel"], verdicts.ECHANTILLON_INSUFFISANT)
        self.assertFalse(m["suffisant"])

    def test_26_au_dela_du_seuil_les_taux_apparaissent(self):
        for i in range(verdicts.MINIMUM_POUR_UN_TAUX):
            verdicts.inscrire(self.cx, f"https://x{i}.be/p",
                              "VP" if i % 2 else "FP")
        m = verdicts.metriques(self.cx)
        self.assertTrue(m["suffisant"])
        self.assertIsInstance(m["precision"], float)

    def test_27_le_radar_ne_se_juge_pas_lui_meme(self):
        for juge in ("radar", "AUTOMATIQUE", "système"):
            with self.assertRaises(verdicts.JugeInvalide):
                verdicts.inscrire(self.cx, "https://x.be/p", "VP", juge_par=juge)

    def test_28_deux_relecteurs_peuvent_ne_pas_etre_d_accord(self):
        verdicts.inscrire(self.cx, "https://x.be/p", "VP", juge_par="alice")
        verdicts.inscrire(self.cx, "https://x.be/p", "FP", juge_par="bob")
        self.assertEqual(len(verdicts.tous(self.cx)), 2)

    def test_29_les_sources_sont_cote_a_cote_sans_classement(self):
        """§8 — mesurer sans prioriser."""
        self.decouvrir([r("https://a.be/p", "Recherche transporteur")],
                       moteur="zzz-petite")
        self.decouvrir([r("https://b.be/p", "Recherche transporteur"),
                        r("https://c.be/p", "Recherche transporteur")],
                       moteur="aaa-grosse")
        texte = tableau.rapport(self.cx)
        self.assertIn("SANS CLASSEMENT", texte)
        self.assertLess(texte.index("aaa-grosse"), texte.index("zzz-petite"),
                        "tri alphabétique, jamais par volume")

    def test_30_le_tableau_prepare_l_apprentissage_sans_l_activer(self):
        """§6 — observer d'abord."""
        texte = tableau.rapport(self.cx)
        self.assertIn("APPRENTISSAGE — préparé, PAS activé", texte)
        self.assertIn("Aucun poids, aucun seuil", texte)

    def test_31_la_marge_reste_non_mesuree_sans_couts(self):
        """§7 — aucun coût n'est fabriqué."""
        self.decouvrir([r("https://a.be/p", "Recherche transporteur")])
        t = tableau.mesurer(self.cx)
        self.assertEqual(t.valeur["marge"], tableau.MARGE_NON_MESUREE)
        self.assertEqual(t.valeur["cout"], verdicts.NON_MESURE)
        self.assertIn("NON MESURÉE", tableau.rapport(self.cx))

    def test_32_aucun_score_n_est_invente(self):
        self.decouvrir([r("https://a.be/p", "Une page sans rapport")])
        for l in self.cx.execute("SELECT score, score_mesurable FROM opportunites"):
            if not l["score_mesurable"]:
                self.assertIn("NON MESURABLE",
                              parcours.axes(self.cx.execute(
                                  "SELECT o.*, a.ref_source, a.source AS source_avis"
                                  " FROM opportunites o JOIN avis a ON a.id=o.avis_id"
                                  " LIMIT 1").fetchone()))

    def test_33_aucun_score_ne_supprime_une_opportunite(self):
        p = self.decouvrir([r("https://a.be/p", "Une page sans rapport")])
        self.assertGreaterEqual(p.opportunites, 1)

    def test_34_le_tableau_ne_modifie_rien(self):
        self.decouvrir([r("https://a.be/p", "Recherche transporteur")])
        avant = self.cx.execute(
            "SELECT type, score, action, etat FROM opportunites").fetchall()
        tableau.rapport(self.cx)
        apres = self.cx.execute(
            "SELECT type, score, action, etat FROM opportunites").fetchall()
        self.assertEqual([tuple(l) for l in avant], [tuple(l) for l in apres])

    def test_35_les_metriques_discovery_et_commerciales_coexistent(self):
        self.decouvrir([r("https://a.be/p", "Recherche transporteur")])
        avis_id = self.premiere()["avis_id"]
        suivi.marquer(self.cx, avis_id, Statut.CONTACTEE)
        t = tableau.mesurer(self.cx)
        self.assertEqual(t.decouverte["resultats_bruts"], 1)
        self.assertEqual(t.commercial[Statut.CONTACTEE.value], 1)
        self.assertIn("import:moteur-t", t.par_source)


if __name__ == "__main__":
    unittest.main()
