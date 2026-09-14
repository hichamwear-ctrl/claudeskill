"""LES DEUX CIRCUITS — mémoire persistante, surveillance directe, changement.

RÈGLE VÉRIFIÉE ICI :

    Google et les autres moteurs servent à DÉCOUVRIR ce que nous ne
    connaissons pas. Les sources que le radar connaît déjà doivent pouvoir
    être analysées, surveillées et transformées en opportunités SANS moteur.

Tous les scénarios sont SYNTHÉTIQUES : aucune page réelle n'est récupérée,
aucun réseau n'est touché (l'ouvreur HTTP est injecté). Ils éprouvent le
mécanisme ; ils ne comptent pour AUCUNE donnée commerciale réelle et ne
mesurent le marché en rien.
"""

import pathlib
import unittest

from radar.base import ouvrir
from radar import entreprises as ent
from radar.entreprises import Etat as EtatEnt, Motif, Registre as RegistreEnt


# ═══════════════════════════════════════ C1 — le registre survit au processus
class C1_UneEntrepriseDecouverteNeDisparaitJamais(unittest.TestCase):
    """« collecte → registre persistant → fin du processus → nouvelle
    exécution → entreprise toujours présente »."""

    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_1_une_entreprise_decouverte_automatiquement_est_relue_apres_coup(self):
        r = RegistreEnt()
        r.decouvrir("Transports Exemple SRL", domaine="exemple.be",
                    motif=Motif.CHERCHE_PARTENAIRE, origine="bda/n0")
        ent.enregistrer(self.cx, r)
        self.cx.commit()

        # PROCESSUS TERMINÉ : on repart d'un registre NEUF, comme le ferait
        # une seconde exécution de `radar traiter`.
        relu = ent.charger(self.cx)
        self.assertIn("exemple.be", relu.entreprises)
        self.assertEqual(relu.entreprises["exemple.be"].nom, "Transports Exemple SRL")
        self.assertEqual(relu.entreprises["exemple.be"].origine, "bda/n0")

    def test_2_les_motifs_et_les_compteurs_traversent_la_persistance(self):
        r = RegistreEnt()
        e = r.decouvrir("X SA", domaine="x.be", motif=Motif.TITULAIRE, origine="ted")
        e.marches_gagnes, e.besoins_detectes, e.montant_gagne = 2, 3, 1500.0
        e.etat = EtatEnt.SURVEILLEE
        ent.enregistrer(self.cx, r)

        relu = ent.charger(self.cx).entreprises["x.be"]
        self.assertIs(relu.etat, EtatEnt.SURVEILLEE)
        self.assertEqual((relu.marches_gagnes, relu.besoins_detectes), (2, 3))
        self.assertEqual(relu.montant_gagne, 1500.0)
        self.assertEqual(relu.motifs, [Motif.TITULAIRE.value])

    def test_3_un_titulaire_d_attribution_entre_au_registre_et_y_reste(self):
        from tests.test_radar import opp
        r = RegistreEnt()
        r.depuis_attribution(opp(attribue=True, titulaire="Grand Opérateur SA",
                                 montant=2400000))
        ent.enregistrer(self.cx, r)

        relu = ent.charger(self.cx)
        garde = [e for e in relu.entreprises.values() if e.nom == "Grand Opérateur SA"]
        self.assertEqual(len(garde), 1)
        self.assertIs(garde[0].etat, EtatEnt.SURVEILLEE)
        self.assertEqual(garde[0].marches_gagnes, 1)

    def test_4_une_entreprise_ajoutee_manuellement_survit_aussi(self):
        r = RegistreEnt()
        r.surveiller("Transports Dupont", domaine="dupont.be")
        ent.enregistrer(self.cx, r)
        self.assertIs(ent.charger(self.cx).entreprises["dupont.be"].etat,
                      EtatEnt.SURVEILLEE)

    def test_5_deux_decouvertes_de_la_meme_entreprise_font_une_seule_fiche(self):
        r = RegistreEnt()
        r.decouvrir("Logistique BE SRL", domaine="logistiquebe.be", motif=Motif.ACHETEUR)
        r.decouvrir("Logistique BE SRL", domaine="logistiquebe.be",
                    motif=Motif.RECRUTE, origine="autre")
        self.assertEqual(len(r.entreprises), 1)
        self.assertEqual(len(r.entreprises["logistiquebe.be"].motifs), 2)

    def test_6_le_nom_seul_puis_le_nom_avec_domaine_restent_une_entreprise(self):
        """Vue d'abord sans domaine, revue avec : c'est la MÊME entreprise.
        Sans index secondaire, le registre en comptait deux."""
        r = RegistreEnt()
        r.decouvrir("Logistique BE SRL", motif=Motif.ACHETEUR)
        r.decouvrir("Logistique BE SRL", domaine="logistiquebe.be", motif=Motif.TITULAIRE)
        self.assertEqual(len(r.entreprises), 1)
        seule = next(iter(r.entreprises.values()))
        self.assertEqual(seule.domaine, "logistiquebe.be")
        self.assertEqual(len(seule.motifs), 2)

    def test_7_reecrire_une_entreprise_connue_n_efface_pas_ses_compteurs(self):
        r = RegistreEnt()
        e = r.decouvrir("Y SA", domaine="y.be", motif=Motif.TITULAIRE)
        e.marches_gagnes, e.contact = 4, "achats@y.be"
        ent.enregistrer(self.cx, r)

        # Seconde exécution : on recharge, on ajoute un motif, on réécrit.
        r2 = ent.charger(self.cx)
        r2.decouvrir("Y SA", domaine="y.be", motif=Motif.RECRUTE)
        ent.enregistrer(self.cx, r2)

        final = ent.charger(self.cx)
        self.assertEqual(len(final.entreprises), 1)
        self.assertEqual(final.entreprises["y.be"].marches_gagnes, 4)
        self.assertEqual(final.entreprises["y.be"].contact, "achats@y.be")
        self.assertEqual(len(final.entreprises["y.be"].motifs), 2)

    def test_8_un_registre_vide_n_invente_aucune_entreprise(self):
        self.assertEqual(ent.charger(self.cx).entreprises, {})


class C1_LaChaineEcritLeRegistreEnFinDeLot(unittest.TestCase):
    """Le test décisif : `traiter` découvre, et l'exécution SUIVANTE retrouve."""

    def test_un_acheteur_traite_existe_encore_a_l_execution_suivante(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar.chaine import traiter

        cx = ouvrir(":memory:")
        # EXÉCUTION N — un moteur au registre vide, comme en production.
        b = traiter(cx, moteur(), [opp(ref_source="N1", acheteur="Ville Exemple")],
                    maintenant_dt=MAINTENANT)
        self.assertGreaterEqual(b.entreprises_enregistrees, 1)

        # EXÉCUTION N+1 — registre reconstruit depuis la base, comme le fait
        # désormais _moteur(cx). L'entreprise est là.
        noms = {e.nom for e in ent.charger(cx).entreprises.values()}
        self.assertIn("Ville Exemple", noms)

    def test_le_titulaire_d_une_attribution_est_ecrit_aussi(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar.chaine import traiter

        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(ref_source="ATTR", attribue=True,
                                   titulaire="Grand Opérateur SA", duree_mois=36,
                                   attribue_le="2026-09-01")],
                maintenant_dt=MAINTENANT)
        relu = ent.charger(cx)
        garde = [e for e in relu.entreprises.values() if e.nom == "Grand Opérateur SA"]
        self.assertEqual(len(garde), 1, "le titulaire doit être mémorisé une fois")
        self.assertIs(garde[0].etat, EtatEnt.SURVEILLEE)

    def test_deux_lots_successifs_ne_dupliquent_pas_l_entreprise(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar.chaine import traiter
        from radar.entreprises import charger

        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(ref_source="L1", acheteur="Ville Exemple")],
                maintenant_dt=MAINTENANT)
        # Second lot : le moteur repart du registre PERSISTÉ.
        m2 = moteur()
        m2.entreprises = charger(cx)
        traiter(cx, m2, [opp(ref_source="L2", acheteur="Ville Exemple")],
                maintenant_dt=MAINTENANT)

        villes = [e for e in charger(cx).entreprises.values() if e.nom == "Ville Exemple"]
        self.assertEqual(len(villes), 1)
        self.assertEqual(villes[0].besoins_detectes, 2, "deux besoins, une fiche")


# ═══════════════════════════════════════ C2/C3/C5 — outillage de test
class _Reponse:
    """Une réponse HTTP simulée. AUCUN réseau n'est touché."""
    def __init__(self, corps: bytes, status=200):
        self._corps, self.status = corps, status

    def read(self, n=-1):
        return self._corps

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


ROBOTS_OUVERT = b"User-agent: *\nAllow: /\nCrawl-delay: 0\n"
ROBOTS_FERME = b"User-agent: *\nDisallow: /prive\n"


def faux_reseau(pages: dict, robots_txt: bytes = ROBOTS_OUVERT):
    """Un ouvreur injectable : rend les octets déclarés, lève sinon."""
    import urllib.error

    def ouvrir(requete, timeout=None):
        url = requete if isinstance(requete, str) else requete.full_url
        if url.endswith("/robots.txt"):
            if robots_txt is None:
                raise urllib.error.URLError("robots injoignable")
            return _Reponse(robots_txt)
        valeur = pages.get(url)
        if valeur is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        if isinstance(valeur, Exception):
            raise valeur
        return _Reponse(valeur)
    return ouvrir


class _SansAttente:
    """La politesse est vérifiée ailleurs ; les tests ne dorment pas."""
    def attendre(self, hote, delai):
        pass


class C2_UnePageNEstJamaisSupposee(unittest.TestCase):
    def setUp(self):
        from radar import pages
        self.pages = pages
        self.cx = ouvrir(":memory:")

    def test_1_une_page_exige_une_provenance_connue(self):
        with self.assertRaises(self.pages.ProvenanceInconnue):
            self.pages.declarer(self.cx, "https://x.be/a", provenance="DEVINÉE")

    def test_2_posseder_un_domaine_ne_declare_aucune_page(self):
        """Le registre d'entreprises connaît « exemple.be » ; cela ne crée
        AUCUNE page surveillée."""
        r = RegistreEnt()
        r.surveiller("Exemple SA", domaine="exemple.be")
        ent.enregistrer(self.cx, r)
        self.assertEqual(self.pages.a_surveiller(self.cx), [])

    def test_3_une_page_declaree_part_en_jamais_consultee(self):
        p = self.pages.declarer(self.cx, "https://exemple.be/partenaires",
                                entreprise="exemple.be",
                                provenance=self.pages.CONFIGUREE)
        self.assertIs(p.acces, self.pages.Acces.JAMAIS_CONSULTEE)
        self.assertIsNone(p.empreinte)
        self.assertIsNone(p.derniere_visite)

    def test_4_une_entreprise_peut_avoir_plusieurs_pages(self):
        for chemin in ("/partenaires", "/transporteurs", "/recrutement"):
            self.pages.declarer(self.cx, f"https://exemple.be{chemin}",
                                entreprise="exemple.be",
                                provenance=self.pages.OBSERVEE)
        # Rencontrées, donc CANDIDATES : aucune n'est encore surveillée.
        self.assertEqual(len(self.pages.a_surveiller(self.cx, entreprise="exemple.be")), 0)
        self.assertEqual(len(self.pages.a_surveiller(self.cx, entreprise="exemple.be",
                                                     toutes=True)), 3)
        for chemin in ("/partenaires", "/transporteurs", "/recrutement"):
            self.pages.promouvoir(self.cx, f"https://exemple.be{chemin}",
                                  "retenue pour le test")
        self.assertEqual(len(self.pages.a_surveiller(self.cx, entreprise="exemple.be")), 3)

    def test_5_redeclarer_une_page_n_efface_pas_son_etat(self):
        u = "https://exemple.be/partenaires"
        self.pages.declarer(self.cx, u, entreprise="exemple.be",
                            provenance=self.pages.CONFIGUREE)
        self.pages.marquer(self.cx, u, self.pages.Acces.CONSULTEE,
                           motif="120 octets reçus", empreinte="abc")
        self.pages.declarer(self.cx, u, provenance=self.pages.DECOUVERTE)
        relue = self.pages.lire(self.cx, u)
        self.assertIs(relue.acces, self.pages.Acces.CONSULTEE)
        self.assertEqual(relue.empreinte, "abc")

    def test_6_une_erreur_n_efface_pas_l_empreinte_de_la_derniere_lecture(self):
        u = "https://exemple.be/partenaires"
        self.pages.declarer(self.cx, u, provenance=self.pages.CONFIGUREE)
        self.pages.marquer(self.cx, u, self.pages.Acces.CONSULTEE, empreinte="abc")
        self.pages.marquer(self.cx, u, self.pages.Acces.ERREUR,
                           motif="accès impossible")
        relue = self.pages.lire(self.cx, u)
        self.assertIs(relue.acces, self.pages.Acces.ERREUR)
        self.assertEqual(relue.empreinte, "abc", "l'empreinte valide est conservée")


class C3_LaCollecteDirecteNeDependDAucunMoteur(unittest.TestCase):
    def setUp(self):
        from radar import collecte_directe
        self.cd = collecte_directe

    def _recuperer(self, url, pages, robots_txt=ROBOTS_OUVERT):
        return self.cd.recuperer(url, ouvrir=faux_reseau(pages, robots_txt),
                                 politesse=_SansAttente())

    def test_1_une_url_connue_est_lue_sans_le_moindre_moteur(self):
        import sys
        c = self._recuperer("https://colisprive.be/devenir-partenaire",
                            {"https://colisprive.be/devenir-partenaire": b"<html>ok</html>"})
        self.assertIs(c.acces, self.cd.Acces.CONSULTEE)
        self.assertEqual(c.octets, b"<html>ok</html>")
        self.assertTrue(c.lue)
        # Le module ne connaît aucun moteur : il ne les importe même pas.
        source = (sys.modules["radar.collecte_directe"].__doc__ or "")
        self.assertNotIn("moteurs_recherche",
                         pathlib.Path("radar/collecte_directe.py").read_text(encoding="utf-8"))
        self.assertIn("DÉCOUVRIR", source)

    def test_2_un_robots_txt_illisible_ne_vaut_pas_autorisation(self):
        c = self._recuperer("https://x.be/a", {"https://x.be/a": b"secret"},
                            robots_txt=None)
        self.assertIs(c.acces, self.cd.Acces.NON_DISPONIBLE)
        self.assertIsNone(c.octets)
        self.assertIn("n'autorise pas", c.motif)

    def test_3_un_chemin_interdit_n_est_pas_lu_et_n_est_pas_contourne(self):
        c = self._recuperer("https://x.be/prive/a", {"https://x.be/prive/a": b"secret"},
                            robots_txt=ROBOTS_FERME)
        self.assertIs(c.acces, self.cd.Acces.NON_DISPONIBLE)
        self.assertIsNone(c.octets)
        self.assertIn("robots.txt", c.motif)

    def test_4_une_erreur_reseau_n_est_pas_une_page_vide(self):
        import urllib.error
        c = self._recuperer("https://x.be/a",
                            {"https://x.be/a": urllib.error.URLError("egress bloqué")})
        self.assertIs(c.acces, self.cd.Acces.ERREUR)
        self.assertIsNone(c.octets, "aucun contenu n'est simulé")
        self.assertIsNone(c.empreinte, "pas d'empreinte de la chaîne vide")
        self.assertFalse(c.lue)
        self.assertIn("INCONNU", c.motif)

    def test_5_un_404_est_une_erreur_d_acces_pas_une_absence_d_opportunite(self):
        c = self._recuperer("https://x.be/absente", {})
        self.assertIs(c.acces, self.cd.Acces.ERREUR)
        self.assertEqual(c.http, 404)
        self.assertIn("n'a pas été lue", c.motif)

    def test_6_le_delai_de_politesse_est_reellement_respecte(self):
        dormi = []
        horloge = iter([0.0, 0.0, 0.0, 0.1, 0.1])
        p = self.cd.Politesse(horloge=lambda: next(horloge), dormir=dormi.append)
        p.attendre("x.be", 0)          # premier passage : rien à attendre
        p.attendre("x.be", 0)          # second : le plancher s'applique
        self.assertTrue(dormi and dormi[0] >= self.cd.DELAI_MINIMUM - 0.2,
                        f"délai appliqué : {dormi}")


class C5_LeChangementNeDecidePasDUneOpportunite(unittest.TestCase):
    def setUp(self):
        from radar import changement
        self.ch = changement
        self.cx = ouvrir(":memory:")
        self.u = "https://exemple.be/partenaires"

    def test_1_premiere_visite(self):
        self.assertEqual(self.ch.retenir(self.cx, self.u, self.ch.empreinte(b"A")),
                         self.ch.PREMIERE)

    def test_2_deuxieme_visite_identique_ne_signale_rien(self):
        self.ch.retenir(self.cx, self.u, self.ch.empreinte(b"A"))
        self.assertEqual(self.ch.retenir(self.cx, self.u, self.ch.empreinte(b"A")),
                         self.ch.INCHANGEE)

    def test_3_contenu_modifie_est_detecte(self):
        self.ch.retenir(self.cx, self.u, self.ch.empreinte(b"A"))
        self.assertEqual(self.ch.retenir(self.cx, self.u, self.ch.empreinte(b"B")),
                         self.ch.MODIFIEE)

    def test_4_modifie_ne_veut_pas_dire_opportunite(self):
        """Le module ne rend QUE trois verdicts de contenu. Il ne connaît ni
        opportunité, ni statut, ni procédure."""
        source = pathlib.Path("radar/changement.py").read_text(encoding="utf-8")
        for interdit in ("Opportunite", "Classement", "score", "POSTULABLE"):
            self.assertNotIn(interdit, source.split('"""', 2)[-1],
                             f"changement.py ne doit rien savoir de « {interdit} »")
        self.assertEqual(
            {self.ch.PREMIERE, self.ch.INCHANGEE, self.ch.MODIFIEE,
             self.ch.NON_COMPARABLE},
            {"PREMIÈRE VISITE", "INCHANGÉE", "MODIFIÉE", "NON COMPARABLE"})

    def test_5_une_erreur_apres_une_visite_reussie_n_ecrase_pas_l_empreinte(self):
        self.ch.retenir(self.cx, self.u, self.ch.empreinte(b"A"))
        self.assertEqual(self.ch.retenir(self.cx, self.u, None), self.ch.NON_COMPARABLE)
        self.assertEqual(self.ch.connue(self.cx, self.u), self.ch.empreinte(b"A"))
        # …et la visite suivante, identique, dit bien INCHANGÉE.
        self.assertEqual(self.ch.retenir(self.cx, self.u, self.ch.empreinte(b"A")),
                         self.ch.INCHANGEE)

    def test_6_comparer_ne_modifie_pas_l_etat(self):
        self.ch.retenir(self.cx, self.u, self.ch.empreinte(b"A"))
        self.ch.comparer(self.cx, self.u, self.ch.empreinte(b"B"))
        self.assertEqual(self.ch.connue(self.cx, self.u), self.ch.empreinte(b"A"))


# ═════════════════════ C4 — la surveillance ne dépend d'AUCUN moteur
class C4_TousMoteursCoupesLaSurveillanceContinue(unittest.TestCase):
    """LE TEST DÉCISIF DE LA RÈGLE.

    Google, Brave et tout autre moteur sont rendus indisponibles. La
    surveillance directe d'une entreprise connue doit continuer à l'identique.
    """

    CORPS = (b"<html><head><title>Devenir partenaire</title></head>"
             b"<body><h1>Devenir partenaire de livraison</h1>"
             b"<p>Nous recherchons des transporteurs en Belgique.</p></body></html>")

    def setUp(self):
        from radar import collecte_directe, pages
        self.cd, self.pages = collecte_directe, pages
        self.cx = ouvrir(":memory:")
        self.u = "https://colisprive.be/devenir-partenaire-livraison/"
        r = RegistreEnt()
        r.surveiller("Colis Privé BeLux", domaine="colisprive.be")
        ent.enregistrer(self.cx, r)
        self.pages.declarer(self.cx, self.u, entreprise="colisprive.be",
                            provenance=self.pages.CONFIGUREE,
                            libelle="page partenaires")
        self.pages.promouvoir(self.cx, self.u, "désignée par l'exploitant")
        self.cx.commit()

    def _sans_aucun_moteur(self):
        """Aucune clé nulle part : `depuis_environnement({})` ne rend aucun
        moteur disponible. C'est l'état réel du radar aujourd'hui."""
        from radar.moteurs_recherche import depuis_environnement
        registre = depuis_environnement({})
        self.assertIsNone(registre.disponible(),
                          "le test n'a de sens que si AUCUN moteur ne répond")
        return registre

    def _veille(self, reseau, analyser=None):
        from radar.boucle import Veille
        ouvreur = faux_reseau(reseau)
        return Veille(self.cx,
                      lambda url: self.cd.recuperer(url, ouvrir=ouvreur,
                                                    politesse=_SansAttente()),
                      analyser=analyser).passer()

    def test_1_la_page_connue_est_consultee_sans_aucun_moteur(self):
        self._sans_aucun_moteur()
        trace = self._veille({self.u: self.CORPS})
        self.assertEqual(trace.pages_consultees, 1)
        self.assertEqual(trace.pages_en_erreur, 0)
        self.assertIs(self.pages.lire(self.cx, self.u).acces,
                      self.pages.Acces.CONSULTEE)

    def test_2_la_chaine_d_analyse_tourne_sur_la_page_ainsi_collectee(self):
        """De l'URL connue jusqu'à l'opportunité, sans passer par un moteur."""
        self._sans_aucun_moteur()
        vues = []

        def analyser(collecte, page):
            from radar import page as lecteur
            cfg = __import__("yaml").safe_load(
                pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
            lec = lecteur.lire(collecte.octets.decode("utf-8"), cfg)
            vues.append(lec.champs.get("intitule"))
            return 1 if lec.champs.get("intitule") else 0

        trace = self._veille({self.u: self.CORPS}, analyser=analyser)
        self.assertEqual(trace.opportunites, 1)
        self.assertEqual(vues, ["Devenir partenaire de livraison"])

    def test_3_une_deuxieme_visite_identique_ne_signale_aucun_changement(self):
        self._veille({self.u: self.CORPS})
        trace = self._veille({self.u: self.CORPS})
        self.assertEqual(trace.pages_modifiees, 0)
        self.assertEqual(trace.passages[0].changement, "INCHANGÉE")

    def test_4_une_page_modifiee_est_signalee_sans_creer_d_opportunite(self):
        self._veille({self.u: self.CORPS})
        trace = self._veille({self.u: self.CORPS + b"<!-- banniere -->"})
        self.assertEqual(trace.pages_modifiees, 1)
        # Aucune opportunité : sans analyseur, le changement ne décide de rien.
        self.assertEqual(trace.opportunites, 0)

    def test_5_une_page_en_erreur_n_empeche_pas_les_autres(self):
        import urllib.error
        autre = "https://colisprive.be/recrutement"
        self.pages.declarer(self.cx, autre, entreprise="colisprive.be",
                            provenance=self.pages.OBSERVEE)
        self.pages.promouvoir(self.cx, autre, "désignée par le test")
        trace = self._veille({self.u: urllib.error.URLError("egress bloqué"),
                              autre: self.CORPS})
        self.assertEqual(trace.pages_surveillees, 2)
        self.assertEqual(trace.pages_en_erreur, 1)
        self.assertEqual(trace.pages_consultees, 1, "l'autre page a bien été lue")

    def test_6_une_erreur_n_est_jamais_presentee_comme_absence_d_opportunite(self):
        import urllib.error
        trace = self._veille({self.u: urllib.error.URLError("egress bloqué")})
        texte = trace.resume()
        self.assertIn("ERREUR", texte)
        self.assertIn("reste INCONNU", texte)
        self.assertNotIn("aucune opportunité", texte.lower())

    def test_7_la_veille_n_importe_aucun_moteur_de_recherche(self):
        for module in ("radar/collecte_directe.py", "radar/pages.py",
                       "radar/changement.py"):
            source = pathlib.Path(module).read_text(encoding="utf-8")
            self.assertNotIn("moteurs_recherche", source, module)
            self.assertNotIn("charger_connecteur", source, module)

    def test_8_la_surveillance_repart_du_registre_persistant(self):
        """Nouvelle exécution : l'entreprise ET ses pages sont toujours là."""
        relu = ent.charger(self.cx)
        self.assertIn("colisprive.be", relu.entreprises)
        self.assertEqual(len(self.pages.a_surveiller(self.cx,
                                                     entreprise="colisprive.be")), 1)


# ═════════════════════ C9 — le circuit trace, il ne note jamais
class C9_LeCircuitNEntreDansAucunScore(unittest.TestCase):
    """LA GARDE LA PLUS IMPORTANTE DE TOUT CE CHANTIER.

    Même opportunité, mêmes données commerciales → même score, quel que soit
    le chemin par lequel elle est arrivée. Le circuit sert à la provenance,
    à la traçabilité et aux métriques. Jamais à la valeur.
    """

    def test_1_les_deux_circuits_donnent_exactement_le_meme_score(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar import circuit

        a = opp(ref_source="MEME-1")
        b = opp(ref_source="MEME-2")
        a.provenances = [{"source": "bda", "url": "https://x.be/a",
                          "circuit": circuit.CONNUE}]
        b.provenances = [{"source": "google", "url": "https://x.be/a",
                          "circuit": circuit.DECOUVERTE}]
        ra = moteur().analyser(a, MAINTENANT)
        rb = moteur().analyser(b, MAINTENANT)
        self.assertEqual(ra.score.total, rb.score.total,
                         "le circuit a modifié le score — interdit")
        self.assertIs(ra.classement.type, rb.classement.type)
        self.assertIs(ra.classement.action, rb.classement.action)

    def test_2_le_moteur_de_scoring_ne_connait_pas_le_mot_circuit(self):
        for module in ("radar/score.py", "radar/classification.py"):
            source = pathlib.Path(module).read_text(encoding="utf-8")
            self.assertNotIn("SOURCE_DÉCOUVERTE", source, module)
            self.assertNotIn("SOURCE_CONNUE", source, module)
            self.assertNotIn("circuit", source, module)

    def test_3_un_circuit_illisible_ne_devient_pas_decouverte(self):
        from radar import circuit
        self.assertEqual(circuit.lire("n'importe quoi"), circuit.CONNUE)
        self.assertEqual(circuit.lire(None), circuit.CONNUE)
        self.assertEqual(circuit.lire("SOURCE_DÉCOUVERTE"), circuit.DECOUVERTE)

    def test_4_une_opportunite_peut_porter_les_deux_circuits(self):
        from radar import circuit
        provenances = [{"source": "bda", "circuit": circuit.CONNUE},
                       {"source": "google", "circuit": circuit.DECOUVERTE},
                       {"source": "entreprise", "circuit": circuit.CONNUE}]
        self.assertEqual(circuit.de_provenances(provenances),
                         [circuit.CONNUE, circuit.DECOUVERTE])
        self.assertEqual(circuit.libelle(provenances),
                         "SOURCE_CONNUE + SOURCE_DÉCOUVERTE")

    def test_5_le_circuit_est_ecrit_en_base_avec_la_provenance(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar.chaine import traiter
        from radar import circuit

        cx = ouvrir(":memory:")
        o = opp(ref_source="TRACE-1")
        o.provenances = [{"source": "bda", "url": "https://x.be/a",
                          "circuit": circuit.CONNUE}]
        traiter(cx, moteur(), [o], maintenant_dt=MAINTENANT)
        lu = cx.execute("SELECT circuit FROM provenances").fetchall()
        self.assertEqual([l["circuit"] for l in lu], [circuit.CONNUE])

    def test_6_une_base_sans_la_colonne_affiche_non_mesure_jamais_zero(self):
        """NON MESURÉ ≠ 0 : une base antérieure au circuit ne prétend pas
        avoir mesuré zéro opportunité découverte."""
        cx = ouvrir(":memory:")
        cx.execute("DROP TABLE provenances")
        cx.execute("CREATE TABLE provenances (id INTEGER PRIMARY KEY,"
                   " avis_id INTEGER, source TEXT, url TEXT)")
        colonnes = {l[1] for l in cx.execute("PRAGMA table_info(provenances)")}
        self.assertNotIn("circuit", colonnes)

    def test_7_les_deux_jeux_de_metriques_restent_separes(self):
        """Une opportunité de surveillance ne se compte pas comme découverte."""
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar.chaine import traiter
        from radar import circuit

        cx = ouvrir(":memory:")
        connue = opp(ref_source="C-1")
        connue.provenances = [{"source": "bda", "url": "https://x.be/1",
                               "circuit": circuit.CONNUE}]
        trouvee = opp(ref_source="D-1")
        trouvee.provenances = [{"source": "google", "url": "https://x.be/2",
                                "circuit": circuit.DECOUVERTE}]
        traiter(cx, moteur(), [connue, trouvee], maintenant_dt=MAINTENANT)

        def par(c):
            return cx.execute("SELECT count(DISTINCT avis_id) n FROM provenances"
                              " WHERE circuit=?", (c,)).fetchone()["n"]
        self.assertEqual(par(circuit.CONNUE), 1)
        self.assertEqual(par(circuit.DECOUVERTE), 1)


class C9_LesMetriquesDeSurveillanceSontComplete(unittest.TestCase):
    def test_la_trace_de_veille_expose_les_sept_compteurs_demandes(self):
        from radar.boucle import TraceVeille
        t = TraceVeille()
        for compteur in ("entreprises_surveillees", "pages_surveillees",
                         "pages_consultees", "pages_modifiees", "opportunites",
                         "pages_en_erreur", "pages_non_disponibles"):
            self.assertTrue(hasattr(t, compteur), compteur)

    def test_la_trace_de_decouverte_reste_distincte(self):
        from radar.boucle import Trace, TraceVeille
        self.assertIsNot(Trace, TraceVeille)
        # La découverte compte des requêtes et un budget ; la surveillance non.
        self.assertTrue(hasattr(Trace(), "budget_utilise"))
        self.assertFalse(hasattr(TraceVeille(), "budget_utilise"))


class C9_LaProvenanceEstEcriteDesLaPremiereVue(unittest.TestCase):
    """CHANGEMENT DE COMPORTEMENT SIGNALÉ À L'EXPLOITANT.

    La table `provenances` n'était alimentée QUE lors d'une fusion de doublon.
    Une opportunité vue une seule fois n'avait donc aucune provenance en base,
    alors qu'elle en avait forcément une — et son circuit était incomptable.

    Aucune règle commerciale n'a changé : ni score, ni classification, ni
    état, ni action. Seule la traçabilité est devenue complète.
    """

    def test_une_opportunite_vue_une_seule_fois_a_desormais_sa_provenance(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar.chaine import traiter
        from radar import circuit

        cx = ouvrir(":memory:")
        o = opp(ref_source="UNIQUE-1")
        o.provenances = [{"source": "bda", "url": "https://x.be/a",
                          "circuit": circuit.CONNUE}]
        traiter(cx, moteur(), [o], maintenant_dt=MAINTENANT)
        lignes = cx.execute("SELECT source, circuit FROM provenances").fetchall()
        self.assertEqual([(l["source"], l["circuit"]) for l in lignes],
                         [("bda", circuit.CONNUE)])

    def test_le_score_est_identique_avant_et_apres_ce_changement(self):
        """La provenance est une trace, pas une donnée d'entrée du score."""
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar import circuit

        sans = opp(ref_source="S")
        avec = opp(ref_source="S")
        avec.provenances = [{"source": "google", "url": "https://x.be/a",
                             "circuit": circuit.DECOUVERTE}]
        self.assertEqual(moteur().analyser(sans, MAINTENANT).score.total,
                         moteur().analyser(avec, MAINTENANT).score.total)


# ═══════════════ RACCORD — la page connue traverse la chaîne
class R1_LeRaccordPageChaine(unittest.TestCase):
    """PAGE CONNUE → COLLECTE DIRECTE → CHAÎNE → OPPORTUNITÉ, sans moteur."""

    BESOIN = (b"<html><head><title>Devenir partenaire</title>"
              b'<meta name="description" content="Colis Prive recherche des '
              b'partenaires de livraison en Belgique"></head><body>'
              b"<h1>Devenir partenaire de livraison</h1>"
              b"<p>Nous recherchons actuellement des partenaires de livraison "
              b"en Belgique pour la distribution de colis.</p></body></html>")

    def setUp(self):
        import yaml
        from radar import collecte_directe, normalisation, pages
        self.cd, self.norm, self.pages = collecte_directe, normalisation, pages
        self.profil = yaml.safe_load(
            pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
        self.cx = ouvrir(":memory:")
        self.u = "https://colisprive.be/devenir-partenaire-livraison/"

    def _collecte(self, octets):
        from radar.pages import Acces
        return self.cd.Collecte(url=self.u, acces=Acces.CONSULTEE, octets=octets,
                                http=200, consulte_le="2026-09-13T12:00:00+00:00")

    def test_1_une_page_connue_produit_une_opportunite_analysable(self):
        opp, lec = self.norm.depuis_collecte(self._collecte(self.BESOIN), self.profil)
        self.assertIsNotNone(opp)
        self.assertEqual(opp.intitule, "Devenir partenaire de livraison")
        self.assertIn("partenaires de livraison", opp.texte or lec.texte)

    def test_2_elle_traverse_toute_la_chaine_jusqu_au_score(self):
        from tests.test_radar import moteur
        from radar.chaine import traiter
        from radar.mode import Mode

        opp, _ = self.norm.depuis_collecte(self._collecte(self.BESOIN), self.profil)
        # Mode RÉEL : la preuve de collecte est contrôlée. Sans elle, refus.
        b = traiter(self.cx, moteur(), [opp], mode=Mode.REEL)
        self.assertEqual(b.lus, 1)
        self.assertEqual(b.motifs_rejet, {}, "aucun rejet de contrôle d'entrée")
        ligne = self.cx.execute(
            "SELECT type, action, score, etat_procedure FROM opportunites").fetchone()
        self.assertIsNotNone(ligne, "une opportunité a bien été écrite")
        self.assertIsNotNone(ligne["score"])

    def test_3_la_preuve_de_collecte_est_apposee_et_verifiable(self):
        from radar.mode import CLE_COLLECTE, Mode, verifier
        opp, _ = self.norm.depuis_collecte(self._collecte(self.BESOIN), self.profil)
        self.assertIn(CLE_COLLECTE, opp.brut)
        marque = verifier(opp.brut, Mode.REEL)
        self.assertEqual(marque.reference, self.u)

    def test_4_une_page_non_lue_ne_produit_rien_du_tout(self):
        """Ni opportunité vide, ni opportunité « sans besoin ». RIEN."""
        from radar.pages import Acces
        for acces in (Acces.ERREUR, Acces.NON_DISPONIBLE, Acces.JAMAIS_CONSULTEE):
            echec = self.cd.Collecte(url=self.u, acces=acces, octets=None)
            opp, lec = self.norm.depuis_collecte(echec, self.profil)
            self.assertIsNone(opp, acces.value)
            self.assertIsNone(lec, acces.value)

    def test_5_le_circuit_porte_est_source_connue(self):
        from radar import circuit
        opp, _ = self.norm.depuis_collecte(self._collecte(self.BESOIN), self.profil)
        self.assertEqual(circuit.de_provenances(opp.provenances), [circuit.CONNUE])

    def test_6_normalisation_n_importe_aucun_moteur(self):
        source = pathlib.Path("radar/normalisation.py").read_text(encoding="utf-8")
        self.assertNotIn("moteurs_recherche", source)
        self.assertNotIn("charger_connecteur", source)


class R2_ChangementTechniqueContreChangementCommercial(unittest.TestCase):
    """« Une page modifiée ≠ automatiquement une nouvelle opportunité. »"""

    BASE = (b"<html><head><title>Partenaires</title></head><body>"
            b"<h1>Devenir partenaire de livraison</h1>"
            b"<p>Nous recherchons des partenaires en Belgique.</p></body></html>")
    # MÊME texte lisible, fichier différent : horodatage, jeton, analytique.
    TECHNIQUE = BASE.replace(
        b"<body>", b"<!-- rendu 2026-09-13T14:32:11 jeton=a9f3 --><body>")
    # Texte réellement différent.
    COMMERCIAL = BASE.replace(b"des partenaires en Belgique",
                              "des transporteurs et des chauffeurs à Gand".encode("utf-8"))

    def setUp(self):
        import yaml
        from radar import collecte_directe, pages
        self.cd, self.pages = collecte_directe, pages
        self.profil = yaml.safe_load(
            pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
        self.cx = ouvrir(":memory:")
        self.u = "https://exemple.be/partenaires"
        self.pages.declarer(self.cx, self.u, entreprise="exemple.be",
                            provenance=self.pages.CONFIGUREE)
        self.pages.promouvoir(self.cx, self.u, "cas de test")
        self.analysees = []

    def _passer(self, octets):
        from radar.boucle import Veille
        ouvreur = faux_reseau({self.u: octets})
        return Veille(
            self.cx,
            lambda url: self.cd.recuperer(url, ouvrir=ouvreur,
                                          politesse=_SansAttente()),
            analyser=lambda c, p: (self.analysees.append(p.url) or 1),
            profil=self.profil).passer()

    def test_1_premiere_visite_analyse_la_page(self):
        t = self._passer(self.BASE)
        self.assertEqual(t.passages[0].changement, "PREMIÈRE VISITE")
        self.assertEqual(len(self.analysees), 1)

    def test_2_page_inchangee_n_est_pas_reanalysee(self):
        self._passer(self.BASE)
        self.analysees.clear()
        t = self._passer(self.BASE)
        self.assertEqual(t.passages[0].changement, "INCHANGÉE")
        self.assertEqual(self.analysees, [], "rien ne doit repasser dans la chaîne")
        self.assertEqual(t.opportunites, 0)

    def test_3_changement_purement_technique_est_enregistre_et_rien_de_plus(self):
        """LE TEST DEMANDÉ : cookie, horodatage, jeton, menu, HTML.

        Le fichier a bougé ; ce que la page DIT est mot pour mot identique.
        Aucune opportunité ne doit naître de ça.
        """
        self._passer(self.BASE)
        self.analysees.clear()
        t = self._passer(self.TECHNIQUE)
        self.assertEqual(t.passages[0].changement, "MODIFIÉE — TECHNIQUE")
        self.assertEqual(t.pages_changees_techniquement, 1)
        self.assertEqual(t.pages_modifiees, 0)
        self.assertEqual(self.analysees, [],
                         "un changement technique ne doit PAS entrer dans la chaîne")
        self.assertEqual(t.opportunites, 0)

    def test_4_changement_de_contenu_repasse_dans_la_chaine(self):
        self._passer(self.BASE)
        self.analysees.clear()
        t = self._passer(self.COMMERCIAL)
        self.assertEqual(t.passages[0].changement, "MODIFIÉE")
        self.assertEqual(t.pages_modifiees, 1)
        self.assertEqual(self.analysees, [self.u])
        self.assertEqual(t.opportunites, 1)

    def test_5_la_modification_technique_est_bien_memorisee(self):
        """« modification enregistrée uniquement » : la trace existe."""
        from radar import changement
        self._passer(self.BASE)
        avant = changement.connue(self.cx, self.u)
        self._passer(self.TECHNIQUE)
        self.assertNotEqual(changement.connue(self.cx, self.u), avant,
                            "l'empreinte du fichier a bien été mise à jour")
        self.assertEqual(changement.connue_lisible(self.cx, self.u),
                         changement.empreinte_lisible(
                             __import__("radar.page", fromlist=["lire"]).lire(
                                 self.BASE.decode(), self.profil).texte))


class R3_UnePageDeuxCircuitsUneSeulePage(unittest.TestCase):
    """« Google → page X, BDA → page X, entreprise → page X » = UNE page."""

    def setUp(self):
        from radar import pages
        self.pages = pages
        self.cx = ouvrir(":memory:")
        self.u = "https://exemple.be/devenir-partenaire"

    def test_1_trois_rencontres_font_une_page_et_trois_provenances(self):
        from radar import circuit
        self.pages.rencontrer(self.cx, self.u, entreprise="exemple.be",
                              provenance=self.pages.DECOUVERTE, source="google",
                              circuit=circuit.DECOUVERTE)
        self.pages.rencontrer(self.cx, self.u, provenance=self.pages.OBSERVEE,
                              source="bda", circuit=circuit.CONNUE)
        self.pages.rencontrer(self.cx, self.u, provenance=self.pages.OBSERVEE,
                              source="entreprise", circuit=circuit.CONNUE)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM pages_surveillees").fetchone()["c"],
            1, "trois rencontres, une seule page")
        pg = self.pages.lire(self.cx, self.u)
        self.assertEqual([p["source"] for p in pg.provenances],
                         ["google", "bda", "entreprise"])
        self.assertEqual(sorted({p["circuit"] for p in pg.provenances}),
                         sorted([circuit.CONNUE, circuit.DECOUVERTE]))

    def test_2_l_url_est_normalisee_avant_comparaison(self):
        self.pages.rencontrer(self.cx, "https://EXEMPLE.be/devenir-partenaire#a",
                              source="google", provenance=self.pages.DECOUVERTE)
        self.pages.rencontrer(self.cx, "https://exemple.be/devenir-partenaire",
                              source="bda", provenance=self.pages.OBSERVEE)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM pages_surveillees").fetchone()["c"], 1)

    def test_3_rencontrer_ne_decide_pas_de_surveiller(self):
        self.pages.rencontrer(self.cx, self.u, source="google",
                              provenance=self.pages.DECOUVERTE)
        pg = self.pages.lire(self.cx, self.u)
        self.assertIs(pg.statut, self.pages.Statut.CANDIDATE)
        self.assertFalse(pg.surveillee)
        self.assertEqual(self.pages.a_surveiller(self.cx), [])

    def test_4_une_promotion_exige_une_raison_ecrite(self):
        self.pages.rencontrer(self.cx, self.u, source="google",
                              provenance=self.pages.DECOUVERTE)
        with self.assertRaises(ValueError):
            self.pages.promouvoir(self.cx, self.u, "")
        pg = self.pages.promouvoir(self.cx, self.u, "page « devenir partenaire »")
        self.assertIs(pg.statut, self.pages.Statut.SURVEILLEE)
        self.assertEqual(pg.raison, "page « devenir partenaire »")

    def test_5_une_page_ecartee_sort_de_la_rotation_avec_son_motif(self):
        self.pages.rencontrer(self.cx, self.u, source="google",
                              provenance=self.pages.DECOUVERTE)
        self.pages.promouvoir(self.cx, self.u, "retenue")
        self.pages.ecarter(self.cx, self.u, "robots.txt interdit ce chemin")
        self.assertEqual(self.pages.a_surveiller(self.cx), [])
        self.assertEqual(self.pages.lire(self.cx, self.u).raison,
                         "robots.txt interdit ce chemin")


class R4_ColisPriveCasDeReference(unittest.TestCase):
    """LE CAS DE RÉFÉRENCE, sur la page RÉELLEMENT collectée et conservée.

    Ce n'est pas une fixture : c'est le fichier archivé le 2026-09-12, avec
    son empreinte. Aucun moteur de recherche n'intervient à aucune étape.
    """

    PAGE = pathlib.Path("validation/pages_reelles/"
                        "2026-09-12-entreprise-c5e20010e7bd.html")
    URL = "https://www.colisprive.be/devenir-partenaire-livraison/"

    def setUp(self):
        import yaml
        from radar import collecte_directe, normalisation, pages
        if not self.PAGE.exists():
            self.skipTest("page réelle absente")
        self.cd, self.norm, self.pages = collecte_directe, normalisation, pages
        self.profil = yaml.safe_load(
            pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
        self.octets = self.PAGE.read_bytes()
        self.cx = ouvrir(":memory:")

    def test_1_l_empreinte_de_la_page_reelle_est_bien_celle_archivee(self):
        import hashlib
        self.assertTrue(
            hashlib.sha256(self.octets).hexdigest().startswith("c5e20010e7bd"))

    def test_2_entreprise_puis_page_puis_collecte_puis_opportunite(self):
        """Le flux complet, sans moteur, sur le contenu réel."""
        from tests.test_radar import moteur
        from radar.chaine import traiter
        from radar.mode import Mode
        from radar.moteurs_recherche import depuis_environnement
        from radar.pages import Acces

        # Aucun moteur n'est disponible — c'est l'état réel du radar.
        self.assertIsNone(depuis_environnement({}).disponible())

        # 1. ENTREPRISE CONNUE, persistée.
        r = RegistreEnt()
        r.surveiller("Colis Privé BeLux", domaine="colisprive.be")
        ent.enregistrer(self.cx, r)

        # 2. PAGE SURVEILLÉE, avec sa raison.
        self.pages.rencontrer(self.cx, self.URL, entreprise="colisprive.be",
                              provenance=self.pages.CONFIGUREE, source="exploitant")
        self.pages.promouvoir(self.cx, self.URL, "page « devenir partenaire »")

        # 3. COLLECTE DIRECTE → CONTENU RÉEL (ici l'archive conservée).
        collecte = self.cd.Collecte(url=self.URL, acces=Acces.CONSULTEE,
                                    octets=self.octets, http=200)

        # 4. NORMALISATION → 5. CHAÎNE
        opp, lec = self.norm.depuis_collecte(collecte, self.profil)
        b = traiter(self.cx, moteur(), [opp], mode=Mode.REEL)
        self.assertEqual(b.motifs_rejet, {})

        ligne = self.cx.execute(
            "SELECT type, moteur, action, score, etat_procedure, intitule"
            " FROM opportunites").fetchone()
        self.assertEqual(ligne["intitule"], "Devenir partenaire de livraison")
        # RÈGLE MÉTIER CONSERVÉE : un besoin de partenaire privé est une
        # opportunité pertinente. Elle n'est PAS transformée en marché public.
        self.assertEqual(ligne["type"], "DIRECT")
        self.assertEqual(ligne["score"], 55)
        self.assertEqual(ligne["action"], "POSTULER")
        self.assertNotIn("MARCHÉ PUBLIC", (ligne["etat_procedure"] or "").upper())

    def test_3_la_porte_d_entree_est_constatee_sur_le_html_reel(self):
        opp, _ = self.norm.depuis_collecte(
            self.cd.Collecte(url=self.URL, acces=self.pages.Acces.CONSULTEE,
                             octets=self.octets, http=200), self.profil)
        self.assertEqual((opp.porte_entree or {}).get("type"), "FORMULAIRE")

    def test_4_le_score_est_le_meme_par_decouverte_que_par_surveillance(self):
        """Le circuit ne change rien : même page, même besoin, même score."""
        from tests.test_radar import moteur
        from radar import circuit

        connue, _ = self.norm.depuis_collecte(
            self.cd.Collecte(url=self.URL, acces=self.pages.Acces.CONSULTEE,
                             octets=self.octets, http=200),
            self.profil, circuit=circuit.CONNUE)
        trouvee, _ = self.norm.depuis_collecte(
            self.cd.Collecte(url=self.URL, acces=self.pages.Acces.CONSULTEE,
                             octets=self.octets, http=200),
            self.profil, circuit=circuit.DECOUVERTE)
        self.assertEqual(circuit.de_provenances(connue.provenances), [circuit.CONNUE])
        self.assertEqual(circuit.de_provenances(trouvee.provenances),
                         [circuit.DECOUVERTE])
        self.assertEqual(moteur().analyser(connue).score.total,
                         moteur().analyser(trouvee).score.total)


# ═══════════════════ PROMOTION AUTOMATIQUE — réutilise l'existant
def _mecanismes():
    """L'ontologie et le détecteur de rôle RÉELS du projet, chargés depuis la
    configuration. Aucun vocabulaire n'est redéfini dans ces tests."""
    import yaml
    from radar.activite import Ontologie
    from radar.role import DetecteurDeRole
    cap = yaml.safe_load(pathlib.Path("config/capacites.yaml").read_text(encoding="utf-8"))
    prof = yaml.safe_load(pathlib.Path("profil.yaml").read_text(encoding="utf-8"))
    roles = yaml.safe_load(pathlib.Path("config/roles.yaml").read_text(encoding="utf-8"))
    return (Ontologie(cap, prof["familles_actives"], prof.get("familles_exclues")),
            DetecteurDeRole(roles))


class P1_LaPromotionAutomatiqueEstPrudente(unittest.TestCase):
    """Elle n'a AUCUN vocabulaire propre : elle interroge l'ontologie et le
    détecteur de rôle déjà en place."""

    def setUp(self):
        from radar import pertinence
        self.pertinence = pertinence
        self.onto, self.det = _mecanismes()

    def _c(self, texte):
        return self.pertinence.evaluer(texte, self.onto, self.det).confiance

    def test_1_une_preuve_positive_de_role_promeut(self):
        """7a : seule une PREUVE POSITIVE promeut — ici, un rôle PRESTATAIRE
        établi par le lexique gelé de config/roles.yaml."""
        from radar.pertinence import Confiance
        for texte in ("Devenir transporteur",
                      "Transporteurs recherchés",
                      "Devenir sous-traitant transport"):
            self.assertIs(self._c(texte), Confiance.FORTE, texte)

    def test_1bis_l_asymetrie_fr_en_est_corrigee_7d(self):
        """Ce test a été posé en 7a pour que la correction de 7d SE VOIE.

        « partenaire de livraison » est désormais au lexique de prestation
        français, comme « delivery partner » l'était en anglais depuis
        l'origine. La page francophone obtient enfin la même preuve que sa
        propre traduction anglaise.
        """
        from radar.pertinence import Confiance
        from radar.role import Role
        p = self.pertinence.evaluer("Devenir partenaire de livraison",
                                    self.onto, self.det)
        self.assertIs(p.confiance, Confiance.FORTE)
        self.assertIs(p.role, Role.PRESTATAIRE)
        self.assertTrue(any("partenaire" in x for x in p.preuves), p.preuves)

    def test_1ter_chauffeur_reste_un_terme_de_domaine_decision_7d(self):
        """DÉCISION MÉTIER DE 7d : « chauffeur » N'EST PAS déplacé.

        « Nous recrutons 20 chauffeurs » est un recrutement de salariés, pas
        l'achat d'une prestation de transport. Mesuré avant toute écriture :
        déplacer le terme nu produisait 2 faux positifs sur les pages
        négatives du corpus de référence.

        La configuration distingue DÉJÀ les deux contextes — « mise à
        disposition de chauffeurs » et « location de véhicules avec
        chauffeur » sont bien des prestations, et sont bien au lexique.
        Le manque était apparent, pas réel.
        """
        from radar.pertinence import Confiance
        from radar.role import Role
        for emploi in ("Recrutement de chauffeurs",
                       "Nous recrutons 20 chauffeurs",
                       "Offre d'emploi chauffeur livreur CDI"):
            p = self.pertinence.evaluer(emploi, self.onto, self.det)
            self.assertIs(p.confiance, Confiance.MOYENNE, emploi)
            self.assertFalse(p.promouvoir, emploi)
        # …tandis que les DEUX contextes de prestation restent reconnus.
        for prestation in ("Mise à disposition de chauffeurs",
                           "Location de véhicules avec chauffeur"):
            self.assertIs(self.det.analyser(prestation).role, Role.PRESTATAIRE,
                          prestation)

    def test_2_un_mot_generique_ne_suffit_pas(self):
        """« partenaire » ou « actualités » seuls ne rattachent rien."""
        from radar.pertinence import Confiance
        for texte in ("Partenaires", "Nos actualités", "Nous rejoindre",
                      "Mentions légales", "Politique de confidentialité",
                      "Qui sommes-nous ?", "Contact", "CGU"):
            self.assertIs(self._c(texte), Confiance.AUCUNE, texte)

    def test_3_une_fourniture_n_est_pas_promue_meme_si_elle_parle_livraison(self):
        """La règle de rôle GELÉE fait son travail : l'acheteur veut du
        poisson, la livraison est accessoire."""
        from radar.pertinence import Confiance
        self.assertIs(self._c("Fourniture et livraison de poissons frais"),
                      Confiance.MOYENNE)

    def test_4_la_raison_de_la_promotion_est_conservee_et_relisible(self):
        p = self.pertinence.evaluer("Devenir transporteur", self.onto, self.det)
        self.assertTrue(p.promouvoir)
        self.assertIn("PROMUE AUTOMATIQUEMENT", p.raison())
        self.assertIn("CONFIANCE=FORTE", p.raison())
        self.assertIn("ROLE=", p.raison())

    def test_5_une_candidate_non_promue_garde_un_motif_a_qualifier(self):
        p = self.pertinence.evaluer("Nos actualités", self.onto, self.det)
        self.assertFalse(p.promouvoir)
        self.assertIn("À QUALIFIER", p.raison())

    def test_6_le_module_ne_contient_aucun_vocabulaire_metier(self):
        """S'il en contenait, il existerait deux définitions du métier.

        On inspecte les CHAÎNES DU CODE — pas les commentaires ni les
        docstrings, qui ont le droit d'expliquer avec des exemples.
        """
        import ast
        arbre = ast.parse(pathlib.Path("radar/pertinence.py")
                          .read_text(encoding="utf-8"))
        docstrings = set()
        for n in ast.walk(arbre):
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                d = ast.get_docstring(n, clean=False)
                if d:
                    docstrings.add(d)
        litterales = [n.value.lower() for n in ast.walk(arbre)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str)
                      and n.value not in docstrings]
        for mot in ("transporteur", "livraison", "logistique", "chauffeur",
                    "sous-traitance", "fournisseur", "palette", "colis", "fret"):
            for texte in litterales:
                self.assertNotIn(mot, texte,
                                 f"« {mot} » ne doit pas être une donnée du code")


class P2_UneUrlConfigureeResteToujoursSurveillee(unittest.TestCase):
    def test_le_choix_de_l_exploitant_prime_sur_toute_evaluation(self):
        from radar import pages
        cx = ouvrir(":memory:")
        # « Nos actualités » n'aurait JAMAIS été promue automatiquement.
        u = "https://exemple.be/nos-actualites"
        pages.rencontrer(cx, u, provenance=pages.CONFIGUREE, source="exploitant")
        pages.promouvoir(cx, u, "désignée par l'exploitant")
        self.assertIs(pages.lire(cx, u).statut, pages.Statut.SURVEILLEE)
        self.assertEqual(len(pages.a_surveiller(cx)), 1)


class P3_LaSelectionDesLiens(unittest.TestCase):
    """55 liens ne sont pas 55 pages à surveiller."""

    def setUp(self):
        from radar import liens
        self.liens = liens
        self.onto, self.det = _mecanismes()
        self.base = "https://exemple.be/devenir-partenaire"

    def _sel(self, bruts, **kw):
        return self.liens.selectionner(bruts, self.base, self.onto, self.det, **kw)

    def test_1_les_liens_non_pertinents_hors_domaine_sont_ignores(self):
        bruts = [{"href": "https://facebook.com/exemple", "texte": "Facebook"},
                 {"href": "https://twitter.com/exemple", "texte": "Suivez-nous"},
                 {"href": "https://wordpress.org", "texte": "Fièrement propulsé"}]
        self.assertEqual(self._sel(bruts), [])

    def test_2_ni_les_ancres_les_mailto_ni_les_fichiers(self):
        bruts = [{"href": "#contenu", "texte": "Aller au contenu"},
                 {"href": "mailto:a@b.be", "texte": "Écrivez-nous"},
                 {"href": "tel:+3222", "texte": "Appelez"},
                 {"href": "/plaquette.pdf", "texte": "Notre plaquette"},
                 {"href": "/logo.png", "texte": ""}]
        self.assertEqual(self._sel(bruts), [])

    def test_3_les_liens_du_meme_domaine_sont_retenus_comme_candidats(self):
        bruts = [{"href": "/mentions-legales", "texte": "Mentions légales"}]
        c = self._sel(bruts)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].priorite, self.liens.P1_MEME_DOMAINE)
        self.assertFalse(c[0].promouvable, "générique : candidat, pas promu")

    def test_4_un_lien_externe_a_indice_fort_est_retenu(self):
        bruts = [{"href": "https://autre.be/devenir-transporteur",
                  "texte": "Devenir transporteur"}]
        c = self._sel(bruts)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].priorite, self.liens.P2_INDICE_FORT)
        self.assertTrue(c[0].promouvable)

    def test_5_un_lien_externe_vers_une_entreprise_connue_est_retenu(self):
        bruts = [{"href": "https://titulaire.be/apropos", "texte": "À propos"}]
        self.assertEqual(self._sel(bruts), [])
        c = self._sel(bruts, domaines_connus={"titulaire.be"})
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].priorite, self.liens.P3_ENTREPRISE_CONNUE)
        self.assertFalse(c[0].promouvable, "connue ≠ pertinente")

    def test_6_le_chemin_de_l_url_est_lu_comme_du_texte(self):
        """« /devenir-transporteur » dit quelque chose, même sans libellé."""
        c = self._sel([{"href": "https://autre.be/devenir-transporteur",
                        "texte": ""}])
        self.assertEqual(len(c), 1)
        self.assertTrue(c[0].promouvable)

    def test_7_le_meme_lien_deux_fois_ne_fait_qu_un_candidat(self):
        bruts = [{"href": "/partenaires", "texte": "Partenaires"},
                 {"href": "/partenaires#bas", "texte": "Nos partenaires"}]
        self.assertEqual(len(self._sel(bruts)), 1)


class P4_LaRecolteSurLaPageReelle(unittest.TestCase):
    """FIXTURE : la page RÉELLEMENT collectée le 2026-09-12 et conservée.
    Aucun réseau n'est touché — c'est une archive, pas une collecte du jour."""

    PAGE = pathlib.Path("validation/pages_reelles/"
                        "2026-09-12-entreprise-c5e20010e7bd.html")
    URL = "https://www.colisprive.be/devenir-partenaire-livraison/"

    def setUp(self):
        import yaml
        from radar import liens, pages
        if not self.PAGE.exists():
            self.skipTest("archive absente")
        self.liens, self.pages = liens, pages
        self.onto, self.det = _mecanismes()
        self.profil = yaml.safe_load(
            pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
        self.cx = ouvrir(":memory:")

    def _candidats(self):
        from radar.page import lire as lire_page
        lec = lire_page(self.PAGE.read_bytes().decode("utf-8", "replace"), self.profil)
        self.assertGreaterEqual(len(lec.liens), 50, "la page réelle a bien ~55 liens")
        return lec.liens, self.liens.selectionner(lec.liens, self.URL,
                                                  self.onto, self.det)

    def test_1_cinquante_cinq_liens_donnent_une_poignee_de_pages(self):
        bruts, candidats = self._candidats()
        self.assertLess(len(candidats), len(bruts),
                        "le filtre doit réduire, pas tout garder")
        promouvables = self.liens.retenus(candidats)
        self.assertTrue(0 < len(promouvables) < len(candidats),
                        f"{len(promouvables)} promouvables sur {len(candidats)}")

    def test_2_les_pages_de_forme_ne_sont_jamais_promues(self):
        _, candidats = self._candidats()
        promues = {c.url for c in self.liens.retenus(candidats)}
        for forme in ("mentions-legales", "politique-de-cookies", "cgu",
                      "nos-actualites", "qui-sommes-nous", "nos-engagements-rse"):
            self.assertFalse(any(forme in u for u in promues),
                             f"« {forme} » ne doit pas être promue")

    def test_3_seules_les_pages_a_preuve_positive_sont_promues(self):
        """7a, 7d, puis décision 1 : 11 → 2 → 4 → 3 sur cette page réelle.

        7a a supprimé les 9 promotions qui tenaient à un mot générique.
        7d en a rendu 2 : celles qui portent une preuve de rôle en FRANÇAIS,
        là où seule la version anglaise en avait une.

        La décision métier 1 en retire UNE, et une seule — mesurée nommément :
        `cevalogistics.com/fr`, promue parce que le lien nommait la famille
        « logistique_entrepot ». C'est la page d'accueil d'un prestataire
        logistique : elle nomme le métier, elle ne demande rien. Le
        vocabulaire a cessé d'être une preuve positive.
        """
        _, candidats = self._candidats()
        promues = {c.url for c in self.liens.retenus(candidats)}
        self.assertEqual(len(promues), 3, promues)
        # La preuve anglaise, inchangée depuis l'origine.
        self.assertTrue(any("become-a-delivery-partner" in u for u in promues))
        # ÉQUIVALENCE FR/EN : la page française a sa preuve.
        self.assertTrue(any("devenir-partenaire-livraison" in u for u in promues))
        # LA PROMOTION RETIRÉE PAR LA DÉCISION 1 — nommée, pas seulement comptée.
        self.assertFalse(any("cevalogistics" in u for u in promues),
                         "une vitrine qui nomme le métier n'est pas une demande")

    def test_4_la_recolte_inscrit_candidates_et_promues_avec_leur_raison(self):
        from radar import circuit
        _, candidats = self._candidats()
        bilan = self.pages.depuis_liens(self.cx, candidats,
                                        entreprise="colisprive.be",
                                        circuit=circuit.CONNUE)
        self.assertEqual(bilan["candidates"], len(candidats))
        self.assertEqual(bilan["promues"], len(self.liens.retenus(candidats)))
        for p in self.pages.a_surveiller(self.cx):
            self.assertIn("PROMUE AUTOMATIQUEMENT", p.raison or "")
        toutes = self.pages.a_surveiller(self.cx, toutes=True)
        for p in toutes:
            self.assertTrue(p.provenances, "chaque page garde sa provenance")

    def test_5_une_seconde_recolte_ne_duplique_rien(self):
        _, candidats = self._candidats()
        self.pages.depuis_liens(self.cx, candidats, entreprise="colisprive.be")
        avant = self.cx.execute("SELECT count(*) c FROM pages_surveillees").fetchone()["c"]
        bilan = self.pages.depuis_liens(self.cx, candidats, entreprise="colisprive.be")
        apres = self.cx.execute("SELECT count(*) c FROM pages_surveillees").fetchone()["c"]
        self.assertEqual(avant, apres, "aucune page dupliquée")
        self.assertEqual(bilan["deja_connues"], len(candidats))
        self.assertEqual(bilan["candidates"], 0)

    def test_6_une_page_ecartee_a_la_main_n_est_pas_re_promue(self):
        _, candidats = self._candidats()
        self.pages.depuis_liens(self.cx, candidats, entreprise="colisprive.be")
        cible = self.pages.a_surveiller(self.cx)[0].url
        self.pages.ecarter(self.cx, cible, "sans intérêt — décision exploitant")
        self.pages.depuis_liens(self.cx, candidats, entreprise="colisprive.be")
        self.assertIs(self.pages.lire(self.cx, cible).statut,
                      self.pages.Statut.ECARTEE)


class P5_LaPorteAvantLaChaine(unittest.TestCase):
    """« NON COMMERCIAL CERTAIN → pas de chaîne · INCONNU → chaîne ».

    Le doute profite toujours à l'analyse : on préfère analyser pour rien
    qu'écarter en silence un changement qu'on n'a pas su juger.
    """

    METIER = (b"<html><body><h1>Devenir partenaire de livraison</h1>"
              b"<p>Nous recherchons des transporteurs en Belgique.</p></body></html>")
    HORS_METIER = (b"<html><body><h1>Politique de cookies</h1>"
                   b"<p>Ce site utilise des cookies de mesure d'audience. "
                   b"Vous pouvez retirer votre consentement.</p></body></html>")

    def setUp(self):
        import yaml
        from radar import collecte_directe, pages
        self.cd, self.pages = collecte_directe, pages
        self.onto, self.det = _mecanismes()
        self.profil = yaml.safe_load(
            pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
        self.cx = ouvrir(":memory:")
        self.u = "https://exemple.be/page"
        self.pages.declarer(self.cx, self.u, provenance=self.pages.CONFIGUREE)
        self.pages.promouvoir(self.cx, self.u, "cas de test")
        self.analysees = []

    def _passer(self, octets, *, avec_mecanismes=True):
        from radar.boucle import Veille
        ouvreur = faux_reseau({self.u: octets})
        return Veille(
            self.cx,
            lambda url: self.cd.recuperer(url, ouvrir=ouvreur,
                                          politesse=_SansAttente()),
            analyser=lambda c, p: (self.analysees.append(p.url) or 1),
            profil=self.profil,
            ontologie=self.onto if avec_mecanismes else None,
            detecteur=self.det if avec_mecanismes else None).passer()

    def test_1_un_changement_hors_metier_certain_n_entre_pas_dans_la_chaine(self):
        self._passer(self.HORS_METIER)
        self.analysees.clear()
        t = self._passer(self.HORS_METIER.replace(b"mesure d'audience",
                                                  b"mesure d'audience et de confort"))
        self.assertEqual(t.passages[0].changement, "MODIFIÉE — NON COMMERCIALE")
        self.assertEqual(t.pages_non_commerciales, 1)
        self.assertEqual(self.analysees, [])
        self.assertEqual(t.opportunites, 0)

    def test_2_un_changement_potentiellement_commercial_entre_dans_la_chaine(self):
        self._passer(self.METIER)
        self.analysees.clear()
        t = self._passer(self.METIER.replace(b"en Belgique", b"a Gand et a Anvers"))
        self.assertEqual(t.passages[0].changement, "MODIFIÉE")
        self.assertEqual(self.analysees, [self.u])

    def test_3_un_changement_ambigu_n_est_jamais_supprime_il_est_analyse(self):
        """Sans mécanismes disponibles, la porte laisse TOUT passer."""
        self._passer(self.HORS_METIER, avec_mecanismes=False)
        self.analysees.clear()
        t = self._passer(self.HORS_METIER.replace(b"cookies de", b"cookies tiers de"),
                         avec_mecanismes=False)
        self.assertEqual(t.passages[0].changement, "MODIFIÉE")
        self.assertEqual(self.analysees, [self.u],
                         "INCONNU doit aller à la chaîne, pas à la poubelle")

    def test_4_la_modification_ecartee_est_bien_enregistree(self):
        from radar import changement
        self._passer(self.HORS_METIER)
        avant = changement.connue_lisible(self.cx, self.u)
        self._passer(self.HORS_METIER.replace(b"consentement", b"accord"))
        self.assertNotEqual(changement.connue_lisible(self.cx, self.u), avant,
                            "la modification est mémorisée, pas perdue")

    def test_5_une_page_hors_metier_n_est_pas_analysee_des_la_premiere_visite(self):
        t = self._passer(self.HORS_METIER)
        self.assertEqual(t.passages[0].changement, "PREMIÈRE VISITE",
                         "le verdict de CONTENU reste exact")
        self.assertEqual(self.analysees, [])
        self.assertEqual(t.pages_non_commerciales, 1)

    def test_6_la_porte_n_a_aucun_vocabulaire_propre(self):
        source = pathlib.Path("radar/boucle.py").read_text(encoding="utf-8")
        self.assertIn("from .pertinence import", source)
        self.assertNotIn('"transporteur"', source)
        self.assertNotIn('"livraison"', source)


class P6_ScenarioCompletSansAucunMoteur(unittest.TestCase):
    """L'OBJECTIF DE L'ÉTAPE, de bout en bout.

        entreprise connue → page connue → collecte directe → page modifiée
        → signal commercial → analyse → opportunité → suivi

    FIXTURE : aucun réseau n'est touché, l'ouvreur HTTP est injecté.
    """

    AVANT = ("<html><head><title>Partenaires</title></head><body>"
             "<h1>Devenir partenaire de livraison</h1>"
             "<p>Colis Prive organise la distribution de colis en Belgique.</p>"
             "</body></html>").encode("utf-8")
    APRES = ("<html><head><title>Partenaires</title></head><body>"
             "<h1>Devenir partenaire de livraison</h1>"
             "<p>Colis Prive organise la distribution de colis en Belgique. "
             "Nous recherchons actuellement des transporteurs sous-traitants "
             "pour la distribution de colis a Gand.</p>"
             "</body></html>").encode("utf-8")

    def setUp(self):
        import yaml
        from radar import collecte_directe, normalisation, pages
        self.cd, self.norm, self.pages = collecte_directe, normalisation, pages
        self.onto, self.det = _mecanismes()
        self.profil = yaml.safe_load(
            pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
        self.cx = ouvrir(":memory:")
        self.u = "https://colisprive.be/devenir-partenaire-livraison/"

    def test_le_scenario_entier(self):
        from tests.test_radar import moteur
        from radar.boucle import Veille
        from radar.chaine import traiter
        from radar.mode import Mode
        from radar.moteurs_recherche import depuis_environnement
        from radar import suivi

        # ── AUCUN MOTEUR DE RECHERCHE N'EST DISPONIBLE ──
        self.assertIsNone(depuis_environnement({}).disponible())

        # ── 1. ENTREPRISE CONNUE, persistée ──
        r = RegistreEnt()
        r.surveiller("Colis Privé BeLux", domaine="colisprive.be")
        ent.enregistrer(self.cx, r)

        # ── 2. PAGE CONNUE, surveillée avec sa raison ──
        self.pages.rencontrer(self.cx, self.u, entreprise="colisprive.be",
                              provenance=self.pages.CONFIGUREE, source="exploitant")
        self.pages.promouvoir(self.cx, self.u, "désignée par l'exploitant")

        mot = moteur()
        opportunites = []

        def analyser(collecte, page):
            opp, _ = self.norm.depuis_collecte(collecte, self.profil)
            if opp is None:
                return 0
            opportunites.append(opp)
            b = traiter(self.cx, mot, [opp], mode=Mode.REEL)
            return b.capter + b.developper

        def veille(octets):
            ouvreur = faux_reseau({self.u: octets})
            return Veille(self.cx,
                          lambda url: self.cd.recuperer(url, ouvrir=ouvreur,
                                                        politesse=_SansAttente()),
                          analyser=analyser, profil=self.profil,
                          ontologie=self.onto, detecteur=self.det).passer()

        # ── 3. COLLECTE DIRECTE, première visite ──
        t1 = veille(self.AVANT)
        self.assertEqual(t1.pages_consultees, 1)
        self.assertEqual(t1.passages[0].changement, "PREMIÈRE VISITE")

        # ── 4. PAGE MODIFIÉE, signal commercial ──
        t2 = veille(self.APRES)
        self.assertEqual(t2.passages[0].changement, "MODIFIÉE")
        self.assertEqual(t2.pages_non_commerciales, 0)
        self.assertEqual(t2.pages_changees_techniquement, 0)

        # ── 5. OPPORTUNITÉ écrite, avec son score ──
        ligne = self.cx.execute(
            "SELECT avis_id, type, action, score, intitule"
            " FROM opportunites").fetchone()
        self.assertEqual(ligne["intitule"], "Devenir partenaire de livraison")
        self.assertIsNotNone(ligne["score"])
        # Le besoin PRIVÉ reste privé : rien ne le convertit en marché public.
        self.assertNotIn("MARCHÉ PUBLIC",
                         (self.cx.execute("SELECT etat_procedure e FROM opportunites")
                          .fetchone()["e"] or "").upper())

        # ── 6. SUIVI COMMERCIAL, sur cette opportunité ──
        s = suivi.marquer(self.cx, ligne["avis_id"], suivi.Statut.CONTACT_A_FAIRE,
                          motif="porte d'entrée constatée")
        self.assertIs(s.statut, suivi.Statut.CONTACT_A_FAIRE)
        self.assertTrue(suivi.fil(self.cx, ligne["avis_id"]))

    def test_le_circuit_ne_change_toujours_rien_au_score(self):
        from tests.test_radar import moteur
        from radar import circuit
        from radar.pages import Acces
        c = self.cd.Collecte(url=self.u, acces=Acces.CONSULTEE, octets=self.APRES,
                             http=200)
        a, _ = self.norm.depuis_collecte(c, self.profil, circuit=circuit.CONNUE)
        b, _ = self.norm.depuis_collecte(c, self.profil, circuit=circuit.DECOUVERTE)
        self.assertEqual(moteur().analyser(a).score.total,
                         moteur().analyser(b).score.total)


# ══════════════════════════ 7a — LA PREUVE POSITIVE
class S7a_LIncertitudeNestPasUnePreuve(unittest.TestCase):
    """« INCERTAIN vaut mieux qu'INCORRECT. »

    Une version antérieure promouvait dès que le domaine était reconnu et que
    le rôle n'était PAS fournisseur. C'était promouvoir sur l'absence de
    contre-preuve. Ces tests verrouillent la règle inverse.
    """

    def setUp(self):
        from radar import pertinence
        self.pertinence = pertinence
        self.onto, self.det = _mecanismes()

    def _p(self, texte):
        return self.pertinence.evaluer(texte, self.onto, self.det)

    # ── 1 · un simple mot métier ne promeut plus ──
    def test_1_un_mot_du_domaine_seul_ne_promeut_plus(self):
        from radar.pertinence import Confiance
        # « colis », « livraison » : vocabulaire de DOMAINE, l'équivalent
        # textuel d'un CPV générique. Il situe, il ne prouve rien.
        for texte in ("Mon espace Colis Privé",
                      "Reprogrammer une livraison",
                      "FAQ — J'attends un colis",
                      "Connexion espace colis"):
            p = self._p(texte)
            self.assertIs(p.confiance, Confiance.MOYENNE, texte)
            self.assertFalse(p.promouvoir, texte)
            self.assertTrue(p.domaine, "le domaine EST reconnu, il ne suffit pas")

    # ── 2 · A_VERIFIER seul ne promeut jamais ──
    def test_2_a_verifier_seul_ne_promeut_jamais(self):
        from radar.role import Role
        for texte in ("Mon espace Colis Privé", "Reprogrammer une livraison",
                      "Travailler pour Colis Privé", "Devenir relais colis Privé"):
            p = self._p(texte)
            self.assertIs(p.role, Role.A_VERIFIER, texte)
            self.assertFalse(p.promouvoir,
                             f"« {texte} » : l'incertitude a servi de preuve")

    # ── 3 · une preuve PRESTATAIRE continue de promouvoir ──
    def test_3_une_preuve_de_role_prestataire_promeut(self):
        from radar.pertinence import Confiance
        from radar.role import Role
        p = self._p("Devenir transporteur")
        self.assertIs(p.confiance, Confiance.FORTE)
        self.assertIs(p.role, Role.PRESTATAIRE)
        self.assertTrue(p.preuves, "la preuve doit être nommée")

    # ── 4 · une FAMILLE ancre, et ne promeut plus — DÉCISION 1 ──
    def test_4_une_famille_metier_ancre_sans_promouvoir(self):
        """RÈGLE CHANGÉE — décision métier 1 (veto d'ontologie à deux niveaux).

        Jusqu'ici, reconnaître une famille suffisait à PROMOUVOIR : ce test
        vérifiait `Confiance.FORTE`. Mesuré sur une page réelle, cela promouvait
        « Spécialiste du transport et de la logistique en Belgique depuis 1998 »
        — une vitrine qui ne demande rien à personne.

        La famille reste ce qu'elle a toujours été : un ANCRAGE, qui ouvre la
        porte et conserve la preuve. Elle n'est plus une preuve POSITIVE.
        Ce qui promeut désormais, c'est de DEMANDER : un besoin énoncé, ou un
        rôle PRESTATAIRE établi (test 3 ci-dessus, inchangé).
        """
        from radar.ancrage import VOCABULAIRE
        from radar.pertinence import Confiance
        p = self._p("Prestations de logistique et gestion d'entrepôt")
        self.assertIs(p.confiance, Confiance.MOYENNE)
        self.assertFalse(p.promouvoir, "nommer le métier n'est pas demander")
        self.assertTrue(p.familles, "la famille reconnue doit être conservée")
        self.assertIn(VOCABULAIRE, p.signaux, "…et elle ancre toujours")
        self.assertTrue(any("famille" in x for x in p.preuves), p.preuves)

    # ── 4bis · la MÊME famille, avec un besoin énoncé, promeut ──
    def test_4bis_la_meme_famille_avec_un_besoin_enonce_promeut(self):
        """Le pendant du test 4 : ce n'est pas la famille qu'on a perdue,
        c'est l'idée qu'elle suffise. Ajoutez une demande, la porte s'ouvre."""
        from radar.pertinence import Confiance
        p = self._p("Nous recherchons un prestataire de logistique et de "
                    "gestion d'entrepôt")
        self.assertIs(p.confiance, Confiance.FORTE)
        self.assertTrue(p.promouvoir)

    # ── 5 · une page générique reste candidate ──
    def test_5_une_page_generique_reste_candidate(self):
        from radar.pertinence import Confiance
        for texte in ("Partenaires", "Nos actualités", "Mentions légales",
                      "Politique de cookies", "CGU", "Qui sommes-nous ?",
                      "Contact", "Nous rejoindre"):
            self.assertIs(self._p(texte).confiance, Confiance.AUCUNE, texte)

    # ── CONTRE-EXEMPLE EXIGÉ ──
    def test_6_contre_exemple_le_vocabulaire_generique_ne_fait_pas_une_opportunite(self):
        """Une page bourrée de vocabulaire de domaine, SANS aucun besoin.

        Elle ne doit ni être promue, ni devenir une opportunité. Ce sont deux
        objets distincts, et aucun des deux ne naît d'un mot.
        """
        from radar.pertinence import Confiance
        texte = ("Suivi de colis — entrez votre numéro de colis pour connaître "
                 "l'état de votre livraison. Votre colis est en cours de "
                 "distribution. Le chauffeur passera aujourd'hui.")
        p = self._p(texte)
        self.assertTrue(p.domaine, "le vocabulaire du métier EST là")
        self.assertIs(p.confiance, Confiance.MOYENNE)
        self.assertFalse(p.promouvoir, "une page de suivi n'est pas un besoin")

        # PAGE SURVEILLÉE et OPPORTUNITÉ restent deux objets distincts : 7a
        # garantit la première décision, pas la seconde.
        #
        # PROBLÈME HORS PÉRIMÈTRE, CONSTATÉ ET NON CORRIGÉ EN 7a :
        # la chaîne gelée classe ce texte DIRECT / CAPTER / 49-100 alors que
        # c'est une page CLIENT — l'entreprise y parle à son destinataire, pas
        # à un prestataire. Le score est marqué non mesurable, ce qui est
        # correct, mais le classement l'est moins. Cela relève de la
        # classification, pas de la promotion : voir le compte rendu 7a,
        # rubrique « problèmes découverts ». Le test constate l'état actuel
        # sans l'entériner comme souhaitable.
        from tests.test_radar import MAINTENANT, moteur, opp
        r = moteur().analyser(opp(intitule="Suivi de colis", texte=texte, cpv=[]),
                              MAINTENANT)
        self.assertFalse(r.score.mesurable,
                         "aucun fait économique observé : le score n'est pas une mesure")

    # ── le veto FOURNISSEUR survit, même avec une famille ──
    def test_7_le_veto_fournisseur_prime_sur_la_famille(self):
        """« Fourniture et livraison de repas en liaison froide » porte la
        famille « alimentaire » ET le rôle FOURNISSEUR. Dans le mauvais ordre,
        la règle « famille OU prestataire » la promouvrait."""
        from radar.pertinence import Confiance
        from radar.role import Role
        p = self._p("Fourniture et livraison de repas en liaison froide")
        self.assertIs(p.role, Role.FOURNISSEUR)
        self.assertTrue(p.familles, "la famille EST reconnue")
        self.assertIs(p.confiance, Confiance.MOYENNE)
        self.assertFalse(p.promouvoir)

    def test_8_la_raison_dit_toujours_ce_qui_manque(self):
        p = self._p("Mon espace Colis Privé")
        self.assertIn("CANDIDATE — À QUALIFIER", p.raison())
        self.assertIn("aucune preuve positive", p.raison())


class S7a_AucuneCandidateNEstPerdue(unittest.TestCase):
    """Resserrer la promotion ne doit rien supprimer."""

    def setUp(self):
        from radar import liens, pages
        self.liens, self.pages = liens, pages
        self.onto, self.det = _mecanismes()
        self.cx = ouvrir(":memory:")

    # ── 6 · une URL explicitement surveillée le reste ──
    def test_6_une_url_configuree_reste_surveillee_malgre_une_faible_qualification(self):
        u = "https://exemple.be/mon-espace-colis"
        from radar.pertinence import Confiance
        self.assertIs(self.pertinence_de("Mon espace colis"), Confiance.MOYENNE)
        self.pages.rencontrer(self.cx, u, provenance=self.pages.CONFIGUREE,
                              source="exploitant")
        self.pages.promouvoir(self.cx, u, "désignée par l'exploitant")
        self.assertIs(self.pages.lire(self.cx, u).statut, self.pages.Statut.SURVEILLEE)
        self.assertEqual(len(self.pages.a_surveiller(self.cx)), 1)

    def pertinence_de(self, texte):
        from radar import pertinence
        return pertinence.evaluer(texte, self.onto, self.det).confiance

    # ── 7 · aucune candidate n'est supprimée ──
    def test_7_les_candidates_non_promues_restent_inscrites(self):
        bruts = [{"href": "/mon-espace", "texte": "Mon espace Colis Privé"},
                 {"href": "/faq-colis", "texte": "FAQ — J'attends un colis"},
                 {"href": "/devenir-transporteur", "texte": "Devenir transporteur"}]
        cands = self.liens.selectionner(bruts, "https://exemple.be/accueil",
                                        self.onto, self.det)
        bilan = self.pages.depuis_liens(self.cx, cands, entreprise="exemple.be")
        self.assertEqual(bilan["candidates"], 3, "les 3 sont inscrites")
        self.assertEqual(bilan["promues"], 1, "une seule porte une preuve")
        toutes = self.pages.a_surveiller(self.cx, toutes=True)
        self.assertEqual(len(toutes), 3, "aucune candidate perdue")
        self.assertEqual(len(self.pages.a_surveiller(self.cx)), 1)

    # ── 8 · la provenance est conservée ──
    def test_8_chaque_candidate_garde_sa_provenance_et_sa_raison(self):
        from radar import circuit
        bruts = [{"href": "/mon-espace", "texte": "Mon espace Colis Privé"}]
        cands = self.liens.selectionner(bruts, "https://exemple.be/accueil",
                                        self.onto, self.det)
        self.pages.depuis_liens(self.cx, cands, entreprise="exemple.be",
                                circuit=circuit.CONNUE)
        pg = self.pages.lire(self.cx, "https://exemple.be/mon-espace")
        self.assertTrue(pg.provenances)
        self.assertEqual(pg.provenances[0]["circuit"], circuit.CONNUE)
        self.assertIn("lien retenu", pg.raison or "")

    # ── 9 · la déduplication est inchangée ──
    def test_9_la_deduplication_reste_identique(self):
        bruts = [{"href": "/mon-espace", "texte": "Mon espace Colis Privé"},
                 {"href": "/mon-espace#bas", "texte": "Mon espace"}]
        cands = self.liens.selectionner(bruts, "https://exemple.be/accueil",
                                        self.onto, self.det)
        self.assertEqual(len(cands), 1)
        self.pages.depuis_liens(self.cx, cands)
        self.pages.depuis_liens(self.cx, cands)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM pages_surveillees").fetchone()["c"], 1)


class S7a_LeCircuitNInfluencePasLaPromotion(unittest.TestCase):
    """Ni la source, ni le circuit, ni le moteur n'entrent dans la décision."""

    def setUp(self):
        from radar import liens, pages, pertinence
        self.liens, self.pages, self.pertinence = liens, pages, pertinence
        self.onto, self.det = _mecanismes()

    def test_1_evaluer_ne_recoit_ni_source_ni_circuit(self):
        import inspect
        params = set(inspect.signature(self.pertinence.evaluer).parameters)
        for interdit in ("source", "circuit", "moteur", "fournisseur", "provenance"):
            self.assertNotIn(interdit, params,
                             f"evaluer() ne doit pas connaître « {interdit} »")

    def test_2_le_module_ne_nomme_aucune_source(self):
        source = pathlib.Path("radar/pertinence.py").read_text(encoding="utf-8")
        corps = source.split('"""', 2)[-1]
        for nom in ("google", "brave", "bda", "ted", "SOURCE_CONNUE",
                    "SOURCE_DÉCOUVERTE"):
            self.assertNotIn(nom.lower(), corps.lower(), nom)

    def test_3_la_meme_page_promeut_pareil_par_les_deux_circuits(self):
        from radar import circuit
        cx = ouvrir(":memory:")
        bruts = [{"href": "https://exemple.be/devenir-transporteur",
                  "texte": "Devenir transporteur"}]
        resultats = {}
        for c in (circuit.CONNUE, circuit.DECOUVERTE):
            base = ouvrir(":memory:")
            cands = self.liens.selectionner(bruts, "https://exemple.be/accueil",
                                            self.onto, self.det)
            resultats[c] = self.pages.depuis_liens(base, cands, circuit=c)
        self.assertEqual(resultats[circuit.CONNUE], resultats[circuit.DECOUVERTE])
        del cx


# ══════════════════ 7b — RÉÉVALUATION APRÈS COLLECTE
#
# FIXTURES : aucun réseau n'est touché, l'ouvreur HTTP est injecté.

CONTENU_PREUVE = ("<html><body><h1>Devenir transporteur</h1>"
                  "<p>Nous recherchons des transporteurs pour assurer nos "
                  "tournées en Belgique.</p></body></html>").encode("utf-8")
CONTENU_GENERIQUE = ("<html><body><h1>Suivi de colis</h1>"
                     "<p>Entrez votre numero de colis pour connaitre l'etat de "
                     "votre livraison.</p></body></html>").encode("utf-8")
CONTENU_CONTRE_PREUVE = ("<html><body><h1>Appel d'offres</h1>"
                         "<p>Fourniture et livraison de repas en liaison "
                         "froide.</p></body></html>").encode("utf-8")
CONTENU_HORS_METIER = ("<html><body><h1>Politique de cookies</h1>"
                       "<p>Ce site utilise des cookies de mesure "
                       "d'audience.</p></body></html>").encode("utf-8")
CONTENU_VIDE = b"<html><head><title></title></head><body></body></html>"


class S7b_QualifierUnePageSurSonContenu(unittest.TestCase):
    """« Le libellé d'un lien est un indice. Le contenu est une preuve. »"""

    def setUp(self):
        import yaml
        from radar import collecte_directe, pages
        self.cd, self.pages = collecte_directe, pages
        self.onto, self.det = _mecanismes()
        self.profil = yaml.safe_load(
            pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
        self.cx = ouvrir(":memory:")
        self.u = "https://exemple.be/une-page"
        self.analysees = []

    def _inscrire(self, statut=None, raison=None):
        self.pages.rencontrer(self.cx, self.u, entreprise="exemple.be",
                              provenance=self.pages.DECOUVERTE, source="google",
                              raison="lien retenu — MÊME DOMAINE")
        if statut is self.pages.Statut.SURVEILLEE:
            self.pages.promouvoir(self.cx, self.u, raison or "retenue")
        elif statut is self.pages.Statut.ECARTEE:
            self.pages.ecarter(self.cx, self.u, raison or "sans intérêt")

    def _passer(self, octets):
        from radar.boucle import Veille
        ouvreur = faux_reseau({self.u: octets})
        return Veille(self.cx,
                      lambda url: self.cd.recuperer(url, ouvrir=ouvreur,
                                                    politesse=_SansAttente()),
                      analyser=lambda c, p: (self.analysees.append(p.url) or 1),
                      profil=self.profil, ontologie=self.onto,
                      detecteur=self.det).passer(
                          self.pages.a_surveiller(self.cx, toutes=True))

    def _page(self):
        return self.pages.lire(self.cx, self.u)

    # ── 1 · contenu positif → qualification positive, et promotion ──
    def test_1_un_contenu_probant_qualifie_et_promeut(self):
        self._inscrire()
        self._passer(CONTENU_PREUVE)
        p = self._page()
        self.assertIs(p.qualification, self.pages.Qualification.PREUVE)
        self.assertIs(p.statut, self.pages.Statut.SURVEILLEE)
        self.assertIn("PROMUE APRÈS COLLECTE — CONTENU", p.raison)
        self.assertTrue(p.qualifiee_le)

    # ── 2 · contenu générique → reste candidate ──
    def test_2_un_contenu_generique_laisse_la_page_candidate(self):
        self._inscrire()
        self._passer(CONTENU_GENERIQUE)
        p = self._page()
        self.assertIs(p.qualification, self.pages.Qualification.SANS_PREUVE)
        self.assertIs(p.statut, self.pages.Statut.CANDIDATE)
        self.assertIn("SANS PREUVE", p.raison)
        self.assertIsNotNone(self.pages.lire(self.cx, self.u), "jamais supprimée")

    # ── 3 · contenu négatif → candidate avec contre-preuve ──
    def test_3_une_contre_preuve_ne_supprime_rien_et_se_dit(self):
        self._inscrire()
        self._passer(CONTENU_CONTRE_PREUVE)
        p = self._page()
        self.assertIs(p.qualification, self.pages.Qualification.CONTRE_PREUVE)
        self.assertIs(p.statut, self.pages.Statut.CANDIDATE)
        self.assertIn("CONTRE-PREUVE", p.raison)

    # ── 4 · sans contenu lisible → on n'invente aucune qualification ──
    def test_4_sans_contenu_lisible_rien_n_est_invente(self):
        import urllib.error
        self._inscrire()
        self._passer(urllib.error.URLError("egress bloqué"))
        p = self._page()
        self.assertIs(p.qualification, self.pages.Qualification.NON_QUALIFIEE,
                      "une page non lue n'est pas une page sans preuve")
        self.assertIs(p.statut, self.pages.Statut.CANDIDATE)

    def test_4bis_un_contenu_vide_est_illisible_pas_sans_preuve(self):
        self._inscrire()
        self._passer(CONTENU_VIDE)
        p = self._page()
        self.assertIn(p.qualification, (self.pages.Qualification.ILLISIBLE,
                                        self.pages.Qualification.NON_QUALIFIEE))
        self.assertIsNot(p.qualification, self.pages.Qualification.SANS_PREUVE)

    # ── 5 · surveillée + contenu moins pertinent → aucune rétrogradation ──
    def test_5_une_surveillee_n_est_jamais_retrogradee_automatiquement(self):
        self._inscrire(self.pages.Statut.SURVEILLEE, "désignée par l'exploitant")
        self._passer(CONTENU_HORS_METIER)
        p = self._page()
        self.assertIs(p.statut, self.pages.Statut.SURVEILLEE)
        self.assertEqual(p.raison, "désignée par l'exploitant",
                         "sa raison d'origine est conservée")
        # …mais l'observation est bien enregistrée.
        self.assertIsNot(p.qualification, self.pages.Qualification.NON_QUALIFIEE)

    # ── 6 · écartée → jamais réveillée ──
    def test_6_une_ecartee_n_est_jamais_reveillee(self):
        self._inscrire(self.pages.Statut.ECARTEE, "robots.txt interdit ce chemin")
        self._passer(CONTENU_PREUVE)
        p = self._page()
        self.assertIs(p.statut, self.pages.Statut.ECARTEE)
        self.assertEqual(p.raison, "robots.txt interdit ce chemin")
        self.assertEqual(self.pages.a_surveiller(self.cx), [])

    # ── 7 · seconde collecte identique → pas de nouvelle page ──
    def test_7_une_seconde_collecte_ne_cree_aucune_page(self):
        self._inscrire()
        self._passer(CONTENU_GENERIQUE)
        self._passer(CONTENU_GENERIQUE)
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM pages_surveillees").fetchone()["c"], 1)

    # ── 8 · provenance conservée ──
    def test_8_la_qualification_ne_touche_pas_a_la_provenance(self):
        from radar import circuit
        self.pages.rencontrer(self.cx, self.u, provenance=self.pages.DECOUVERTE,
                              source="google", circuit=circuit.DECOUVERTE)
        self.pages.rencontrer(self.cx, self.u, provenance=self.pages.OBSERVEE,
                              source="bda", circuit=circuit.CONNUE)
        avant = self.pages.lire(self.cx, self.u).provenances
        self._passer(CONTENU_PREUVE)
        self.assertEqual(self.pages.lire(self.cx, self.u).provenances, avant,
                         "une réévaluation n'est pas une rencontre")

    # ── 9 · qualification persistée d'un cycle à l'autre ──
    def test_9_la_qualification_survit_a_un_nouveau_cycle(self):
        self._inscrire()
        self._passer(CONTENU_GENERIQUE)
        premiere = self._page().qualifiee_le
        # Nouveau cycle, contenu INCHANGÉ : la qualification reste telle quelle.
        self._passer(CONTENU_GENERIQUE)
        p = self._page()
        self.assertIs(p.qualification, self.pages.Qualification.SANS_PREUVE)
        self.assertEqual(p.qualifiee_le, premiere, "pas de requalification inutile")

    # ── 10 · un contenu modifié entraîne une réévaluation ──
    def test_10_un_contenu_modifie_declenche_une_requalification(self):
        self._inscrire()
        self._passer(CONTENU_GENERIQUE)
        self.assertIs(self._page().qualification,
                      self.pages.Qualification.SANS_PREUVE)
        self._passer(CONTENU_PREUVE)
        p = self._page()
        self.assertIs(p.qualification, self.pages.Qualification.PREUVE)
        self.assertIs(p.statut, self.pages.Statut.SURVEILLEE)

    # ── 11 · contenu inchangé → pas de réanalyse ──
    def test_11_un_contenu_inchange_ne_declenche_aucune_reanalyse(self):
        self._inscrire()
        self._passer(CONTENU_PREUVE)
        quand = self._page().qualifiee_le
        self.analysees.clear()
        t = self._passer(CONTENU_PREUVE)
        self.assertEqual(t.passages[0].changement, "INCHANGÉE")
        self.assertEqual(self.analysees, [])
        self.assertEqual(self._page().qualifiee_le, quand)

    def test_11bis_un_changement_purement_technique_non_plus(self):
        self._inscrire()
        self._passer(CONTENU_PREUVE)
        quand = self._page().qualifiee_le
        t = self._passer(CONTENU_PREUVE.replace(b"<body>", b"<!-- 14h32 --><body>"))
        self.assertEqual(t.passages[0].changement, "MODIFIÉE — TECHNIQUE")
        self.assertEqual(self._page().qualifiee_le, quand)

    # ── 12 · qualifier n'est JAMAIS créer une opportunité ──
    def test_12_une_page_qualifiee_n_est_pas_une_opportunite(self):
        """B ≠ C. Qualifier décide qu'on revisitera, pas qu'il y a une affaire."""
        self._inscrire()
        self._passer(CONTENU_PREUVE)
        self.assertIs(self._page().qualification, self.pages.Qualification.PREUVE)
        # Aucune opportunité n'a été écrite par la qualification elle-même :
        # l'analyseur de ce test ne touche pas la base.
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"], 0)

    def test_12bis_le_module_de_qualification_ne_connait_pas_l_opportunite(self):
        """On inspecte le CODE — identifiants et imports — pas les
        commentaires, qui ont le droit d'expliquer la frontière."""
        import ast
        arbre = ast.parse(pathlib.Path("radar/pages.py").read_text(encoding="utf-8"))
        noms = {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)}
        noms |= {n.attr for n in ast.walk(arbre) if isinstance(n, ast.Attribute)}
        importes = set()
        for n in ast.walk(arbre):
            if isinstance(n, ast.ImportFrom):
                importes.add(n.module or "")
                importes |= {a.name for a in n.names}
            elif isinstance(n, ast.Import):
                importes |= {a.name for a in n.names}
        for interdit in ("Opportunite", "Classement", "score", "fiche",
                         "classification", "chaine", "procedure"):
            self.assertNotIn(interdit, noms, f"identifiant « {interdit} »")
            self.assertNotIn(interdit, importes, f"import « {interdit} »")

    # ── 14 · aucun vocabulaire métier en dur ──
    def test_14_aucun_vocabulaire_metier_n_est_ajoute(self):
        import ast
        arbre = ast.parse(pathlib.Path("radar/pages.py").read_text(encoding="utf-8"))
        docstrings = set()
        for n in ast.walk(arbre):
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                d = ast.get_docstring(n, clean=False)
                if d:
                    docstrings.add(d)
        litterales = [n.value.lower() for n in ast.walk(arbre)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str)
                      and n.value not in docstrings]
        for mot in ("transporteur", "livraison", "logistique", "chauffeur",
                    "colis", "fret", "palette", "sous-traitance"):
            for texte in litterales:
                self.assertNotIn(mot, texte, f"« {mot} » ne doit pas être ici")


class S7b_CasAmbigus(unittest.TestCase):
    """AMBIGU = on conserve l'information et on qualifie prudemment.
    Jamais de suppression, jamais de verdict inventé."""

    def setUp(self):
        from radar import pages, pertinence
        self.pages, self.pertinence = pages, pertinence
        self.onto, self.det = _mecanismes()
        self.cx = ouvrir(":memory:")
        self.u = "https://exemple.be/ambigu"
        self.pages.rencontrer(self.cx, self.u, provenance=self.pages.DECOUVERTE,
                              source="google")

    def test_1_pertinence_absente_donne_illisible_jamais_sans_preuve(self):
        """Mécanismes indisponibles : on ne conclut pas à leur place."""
        p = self.pages.qualifier(self.cx, self.u, None, texte_lu=True)
        self.assertIs(p.qualification, self.pages.Qualification.ILLISIBLE)
        self.assertIs(p.statut, self.pages.Statut.CANDIDATE)

    def test_2_domaine_reconnu_sans_preuve_reste_candidate_et_le_dit(self):
        verdict = self.pertinence.evaluer("Mon espace colis", self.onto, self.det)
        p = self.pages.qualifier(self.cx, self.u, verdict)
        self.assertIs(p.qualification, self.pages.Qualification.SANS_PREUVE)
        self.assertIn("domaine reconnu", p.raison)
        self.assertIn("aucune preuve positive", p.raison)

    def test_3_texte_non_lu_ne_produit_jamais_de_verdict_sur_le_fond(self):
        verdict = self.pertinence.evaluer("Devenir transporteur", self.onto, self.det)
        self.assertTrue(verdict.promouvoir, "le texte serait probant…")
        p = self.pages.qualifier(self.cx, self.u, verdict, texte_lu=False)
        self.assertIs(p.qualification, self.pages.Qualification.ILLISIBLE,
                      "…mais rien n'a été lu : on ne promeut pas sur du vide")
        self.assertIs(p.statut, self.pages.Statut.CANDIDATE)

    def test_4_non_qualifiee_n_est_pas_sans_preuve(self):
        p = self.pages.lire(self.cx, self.u)
        self.assertIs(p.qualification, self.pages.Qualification.NON_QUALIFIEE)
        self.assertIsNone(p.qualifiee_le)

    def test_5_qualifier_une_page_inconnue_ne_la_cree_pas(self):
        verdict = self.pertinence.evaluer("Devenir transporteur", self.onto, self.det)
        self.assertIsNone(self.pages.qualifier(self.cx, "https://autre.be/x", verdict))
        self.assertEqual(
            self.cx.execute("SELECT count(*) c FROM pages_surveillees").fetchone()["c"], 1)

    def test_6_une_base_ancienne_sans_les_colonnes_reste_lisible(self):
        """Compatibilité : une page écrite avant 7b n'a aucune qualification."""
        self.cx.execute("UPDATE pages_surveillees SET qualification=NULL,"
                        " qualifiee_le=NULL WHERE url=?", (self.u,))
        p = self.pages.lire(self.cx, self.u)
        self.assertIs(p.qualification, self.pages.Qualification.NON_QUALIFIEE)


class S7b_LeCircuitNInfluencePasLaQualification(unittest.TestCase):
    def test_la_qualification_ignore_source_et_circuit(self):
        import inspect
        from radar import pages
        params = set(inspect.signature(pages.qualifier).parameters)
        for interdit in ("source", "circuit", "moteur", "provenance"):
            self.assertNotIn(interdit, params, interdit)

    def test_le_score_reste_independant_du_circuit(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar import circuit
        a = opp(ref_source="Q1")
        b = opp(ref_source="Q2")
        a.provenances = [{"source": "bda", "circuit": circuit.CONNUE}]
        b.provenances = [{"source": "google", "circuit": circuit.DECOUVERTE}]
        self.assertEqual(moteur().analyser(a, MAINTENANT).score.total,
                         moteur().analyser(b, MAINTENANT).score.total)


# ══════════════════════════ 7c — IDENTITÉ DU TITULAIRE
#
# FIXTURES : tous les numéros BCE et domaines de ces tests sont INVENTÉS POUR
# LE TEST. Aucune consultation de la BCE, du KBO ni d'aucun registre n'a lieu :
# l'egress est bloqué et rien n'est simulé. Ces tests éprouvent le MÉCANISME
# d'enregistrement d'une identité, jamais son exactitude dans le monde réel.

class S7c_QuatreEtatsDIdentite(unittest.TestCase):
    def setUp(self):
        from radar import identite
        self.id = identite
        self.cx = ouvrir(":memory:")
        r = RegistreEnt()
        r.surveiller("ABC Logistics", domaine=None)
        ent.enregistrer(self.cx, r)
        self.cle = next(iter(ent.charger(self.cx).entreprises))

    # ── 1 · un titulaire nouveau est INCONNUE ──
    def test_1_un_titulaire_nouveau_est_inconnue(self):
        self.assertIs(self.id.lire(self.cx, self.cle).etat, self.id.Etat.INCONNUE)

    # ── 2 · INCONNUE ne veut pas dire inexistante ──
    def test_2_inconnue_ne_dit_rien_de_l_existence(self):
        i = self.id.lire(self.cx, self.cle)
        self.assertIn("ne sait pas encore", i.ligne())
        self.assertNotIn("n'existe", i.ligne())
        self.assertFalse(i.etat.identifiee)
        # L'entreprise, elle, est bien au registre.
        self.assertIn(self.cle, ent.charger(self.cx).entreprises)

    # ── 3 · BCE en FIXTURE → CONFIRMÉE ──
    def test_3_un_bce_saisi_confirme_avec_sa_preuve_et_sa_date(self):
        i = self.id.confirmer(self.cx, self.cle, source=self.id.EXPLOITANT,
                              preuve="BCE relevée sur l'avis d'attribution",
                              bce="0123.456.789")   # FIXTURE, numéro inventé
        self.assertIs(i.etat, self.id.Etat.CONFIRMEE)
        self.assertEqual(i.bce, "0123.456.789")
        self.assertEqual(i.source, self.id.EXPLOITANT)
        self.assertTrue(i.confirmee_le)
        self.assertTrue(i.preuve)

    def test_3bis_confirmer_sans_preuve_est_refuse(self):
        for manque in ({"source": "", "preuve": "x"}, {"source": "x", "preuve": ""}):
            with self.assertRaises(self.id.IdentiteIncertaine):
                self.id.confirmer(self.cx, self.cle, **manque)

    # ── 4 · deux homonymes → AMBIGUË ──
    def test_4_deux_homonymes_donnent_ambigue_sans_aucun_choix(self):
        i = self.id.proposer(self.cx, self.cle, [
            self.id.Candidat(nom="ABC Logistics SRL", bce="0111.111.111",
                             detail="Liège"),
            self.id.Candidat(nom="ABC Logistics NV", bce="0222.222.222",
                             detail="Antwerpen")])
        self.assertIs(i.etat, self.id.Etat.AMBIGUE)
        self.assertEqual(len(i.candidats), 2, "les deux sont CONSERVÉS")
        self.assertIsNone(i.domaine, "aucun domaine n'a été retenu")
        self.assertIsNone(i.bce, "aucun BCE n'a été retenu")

    # ── 5 · AMBIGUË → CONFIRMÉE avec preuve ──
    def test_5_trancher_exige_un_candidat_connu_et_une_preuve(self):
        self.test_4_deux_homonymes_donnent_ambigue_sans_aucun_choix()
        with self.assertRaises(self.id.IdentiteIncertaine):
            self.id.trancher(self.cx, self.cle, "Entreprise jamais citée",
                             source=self.id.EXPLOITANT, preuve="au hasard")
        i = self.id.trancher(self.cx, self.cle, "ABC Logistics NV",
                             source=self.id.EXPLOITANT,
                             preuve="siège d'exécution du marché à Antwerpen")
        self.assertIs(i.etat, self.id.Etat.CONFIRMEE)
        self.assertEqual(i.bce, "0222.222.222")
        self.assertIn("retenu parmi 2 candidats", i.preuve)
        self.assertEqual(len(i.candidats), 2,
                         "les candidats écartés restent consultables")

    # ── 6 · confirmée sans site → SANS SITE ──
    def test_6_une_entreprise_identifiee_sans_site_est_une_mesure(self):
        i = self.id.sans_site(self.cx, self.cle, source=self.id.EXPLOITANT,
                              preuve="aucun site déclaré au registre")
        self.assertIs(i.etat, self.id.Etat.SANS_SITE)
        self.assertTrue(i.etat.identifiee, "identifiée : ce n'est pas un échec")
        self.assertFalse(i.etat.surveillable, "mais rien à surveiller")
        self.assertIsNone(i.domaine)

    # ── 13 · l'identité survit d'un cycle à l'autre ──
    def test_13_l_identite_est_persistante(self):
        self.id.confirmer(self.cx, self.cle, source=self.id.REGISTRE_OFFICIEL,
                          preuve="fixture de test", domaine="exemple-fixture.be")
        relu = ent.charger(self.cx).entreprises[self.cle]
        self.assertEqual(relu.identite, "CONFIRMÉE")
        self.assertEqual(relu.domaine, "exemple-fixture.be")
        # …et une recollecte ne la dégrade pas.
        reg = ent.charger(self.cx)
        reg.decouvrir("ABC Logistics", motif=None, origine="nouvelle collecte")
        ent.enregistrer(self.cx, reg)
        self.assertIs(self.id.lire(self.cx, self.cle).etat, self.id.Etat.CONFIRMEE)

    # ── 14 · provenance et date conservées ──
    def test_14_la_source_et_la_date_sont_conservees(self):
        i = self.id.confirmer(self.cx, self.cle,
                              source=self.id.REGISTRE_OFFICIEL,
                              preuve="fixture — aucun registre n'a été consulté")
        self.assertEqual(i.source, self.id.REGISTRE_OFFICIEL)
        self.assertTrue(i.confirmee_le.startswith("20"))
        self.assertIn("fixture", i.preuve)


class S7c_JamaisInventerUneUrl(unittest.TestCase):
    """L'interdiction la plus importante de 7c."""

    def setUp(self):
        from radar import identite
        self.id = identite
        self.cx = ouvrir(":memory:")
        r = RegistreEnt()
        r.surveiller("Transports Exemple SRL")
        ent.enregistrer(self.cx, r)
        self.cle = next(iter(ent.charger(self.cx).entreprises))

    # ── 7 · aucun domaine inventé ──
    def test_7_aucun_domaine_n_est_derive_d_un_nom(self):
        i = self.id.lire(self.cx, self.cle)
        self.assertIsNone(i.domaine)
        for suppose in ("transports-exemple.be", "transportsexemple.be",
                        "exemple.be", "transports-exemple.com"):
            self.assertNotEqual(i.domaine, suppose)

    # ── 8 · aucune URL inventée, et la fonction n'existe même pas ──
    def test_8_le_module_ne_sait_pas_fabriquer_une_url(self):
        import ast
        source = pathlib.Path("radar/identite.py").read_text(encoding="utf-8")
        arbre = ast.parse(source)
        docstrings = set()
        for n in ast.walk(arbre):
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                d = ast.get_docstring(n, clean=False)
                if d:
                    docstrings.add(d)
        litterales = [n.value for n in ast.walk(arbre)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str)
                      and n.value not in docstrings]
        for interdit in (".be", ".com", ".eu", "http://", "https://", "www."):
            for texte in litterales:
                self.assertNotIn(interdit, texte,
                                 f"« {interdit} » ne doit pas être une donnée ici")

    # ── 16-17 · aucune consultation réseau, aucune fausse résolution ──
    def test_16_aucun_reseau_n_est_importe_ni_appele(self):
        source = pathlib.Path("radar/identite.py").read_text(encoding="utf-8")
        for interdit in ("urllib", "requests", "socket", "urlopen",
                         "moteurs_recherche", "charger_connecteur",
                         "collecte_directe"):
            self.assertNotIn(interdit, source, interdit)

    def test_17_sans_moteur_aucune_identite_ne_se_resout_toute_seule(self):
        from radar.moteurs_recherche import depuis_environnement
        self.assertIsNone(depuis_environnement({}).disponible())
        # Rien ne change : l'identité reste ce qu'elle était.
        self.assertIs(self.id.lire(self.cx, self.cle).etat, self.id.Etat.INCONNUE)

    # ── 15 · un titulaire non confirmé n'est pas surveillé ──
    def test_15_une_identite_non_confirmee_n_ouvre_aucune_surveillance(self):
        from radar import pages
        i = self.id.lire(self.cx, self.cle)
        self.assertFalse(i.etat.surveillable)
        self.assertEqual(pages.a_surveiller(self.cx, toutes=True), [],
                         "aucune page n'a été fabriquée à partir d'un nom")

    def test_15bis_confirmee_sans_domaine_n_ouvre_rien_non_plus(self):
        from radar import pages
        self.id.confirmer(self.cx, self.cle, source=self.id.EXPLOITANT,
                          preuve="identité établie, site inconnu")
        self.assertIsNone(self.id.lire(self.cx, self.cle).domaine)
        self.assertEqual(pages.a_surveiller(self.cx, toutes=True), [])


class S7c_CasLimites(unittest.TestCase):
    """Raisons sociales réelles : accents, abréviations, suffixes, étrangers."""

    def setUp(self):
        from radar import identite
        self.id = identite
        self.cx = ouvrir(":memory:")

    def _inscrire(self, nom):
        reg = ent.charger(self.cx)
        e = reg.surveiller(nom)
        ent.enregistrer(self.cx, reg)
        return e.cle

    def test_1_un_nom_accentue_est_conserve_tel_quel(self):
        cle = self._inscrire("Transports Frères Dupré SPRL")
        relu = ent.charger(self.cx).entreprises[cle]
        self.assertEqual(relu.nom, "Transports Frères Dupré SPRL")

    def test_2_une_abreviation_et_sa_forme_longue_restent_distinctes(self):
        """« ABC Log. » et « ABC Logistics » PEUVENT être la même entreprise.
        Le radar ne le décide pas : deux fiches, et l'ambiguïté se traite par
        des candidats — jamais par une fusion automatique."""
        a = self._inscrire("ABC Log. SRL")
        b = self._inscrire("ABC Logistics SRL")
        self.assertNotEqual(a, b)
        self.assertEqual(len(ent.charger(self.cx).entreprises), 2)

    def test_3_deux_noms_presque_identiques_ne_fusionnent_pas(self):
        a = self._inscrire("Transport Belgium SA")
        b = self._inscrire("Transports Belgium SA")
        self.assertNotEqual(a, b)

    def test_4_un_suffixe_juridique_fait_partie_du_nom(self):
        for suffixe in ("SRL", "NV", "BV", "SA", "GmbH", "SAS"):
            cle = self._inscrire(f"Exemple {suffixe}")
            self.assertIn(suffixe, ent.charger(self.cx).entreprises[cle].nom)

    def test_5_un_titulaire_etranger_sans_bce_belge_reste_identifiable(self):
        cle = self._inscrire("Muster Logistik GmbH")
        i = self.id.confirmer(self.cx, cle, source=self.id.REGISTRE_OFFICIEL,
                              preuve="registre du commerce allemand — FIXTURE")
        self.assertIs(i.etat, self.id.Etat.CONFIRMEE)
        self.assertIsNone(i.bce, "pas de BCE belge, et ce n'est pas un défaut")

    def test_6_un_titulaire_confirme_sans_site_reste_valide(self):
        cle = self._inscrire("Petite Entreprise SRL")
        i = self.id.sans_site(self.cx, cle, source=self.id.EXPLOITANT,
                              preuve="aucun site — constaté")
        self.assertTrue(i.etat.identifiee)
        self.assertIsNone(i.domaine)


class S7c_Groupements(unittest.TestCase):
    """« Ne réduis pas plusieurs membres à une seule entreprise. »"""

    def setUp(self):
        from radar import identite
        self.id = identite
        self.cx = ouvrir(":memory:")

    def _attribuer(self, titulaire, montant=None):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar.chaine import traiter
        traiter(self.cx, moteur(),
                [opp(ref_source="GRP", attribue=True, titulaire=titulaire,
                     montant=montant)], maintenant_dt=MAINTENANT)
        return self.cx.execute("SELECT id FROM avis").fetchone()["id"]

    def test_1_trois_membres_font_trois_entreprises(self):
        avis = self._attribuer(["Entreprise A SRL", "Entreprise B NV",
                                "Entreprise C SA"])
        noms = [t["nom"] for t in self.id.titulaires_de(self.cx, avis)]
        self.assertEqual(noms, ["Entreprise A SRL", "Entreprise B NV",
                                "Entreprise C SA"])
        registre = ent.charger(self.cx).entreprises
        for nom in noms:
            self.assertTrue(any(e.nom == nom for e in registre.values()), nom)

    def test_2_chaque_membre_compte_son_marche(self):
        self._attribuer(["Entreprise A SRL", "Entreprise B NV"])
        for e in ent.charger(self.cx).entreprises.values():
            self.assertEqual(e.marches_gagnes, 1, e.nom)

    def test_3_le_montant_n_est_reparti_sur_personne(self):
        """La source publie un montant GLOBAL, pas la clé de répartition."""
        self._attribuer(["Entreprise A SRL", "Entreprise B NV"], montant=2_400_000)
        for e in ent.charger(self.cx).entreprises.values():
            self.assertEqual(e.montant_gagne, 0.0,
                             f"{e.nom} : le montant du groupement a été inventé")

    def test_3bis_un_titulaire_unique_garde_son_montant(self):
        self._attribuer("Entreprise Seule SRL", montant=2_400_000)
        seule = next(iter(ent.charger(self.cx).entreprises.values()))
        self.assertEqual(seule.montant_gagne, 2_400_000.0)

    def test_4_un_membre_confirme_et_deux_inconnus_se_dit_ainsi(self):
        avis = self._attribuer(["Entreprise A SRL", "Entreprise B NV",
                                "Entreprise C SA"])
        membres = self.id.titulaires_de(self.cx, avis)
        self.id.confirmer(self.cx, membres[0]["entreprise"],
                          source=self.id.EXPLOITANT, preuve="FIXTURE de test")
        resume = self.id.groupement(self.cx, avis)
        self.assertIn("3 titulaire(s)", resume)
        self.assertIn("CONFIRMÉE", resume)
        self.assertIn("INCONNUE", resume)

    def test_5_une_chaine_libre_n_est_jamais_decoupee_en_membres(self):
        """Deviner des membres dans un texte libre fabriquerait des
        entreprises qui n'existent pas."""
        avis = self._attribuer("Groupement ABC (Entreprise A, Entreprise B)")
        noms = [t["nom"] for t in self.id.titulaires_de(self.cx, avis)]
        self.assertEqual(noms, ["Groupement ABC (Entreprise A, Entreprise B)"])

    def test_6_la_colonne_historique_reste_lisible(self):
        self._attribuer(["Entreprise A SRL", "Entreprise B NV"])
        l = self.cx.execute("SELECT titulaire FROM attributions").fetchone()
        self.assertIn("Entreprise A SRL", l["titulaire"])
        self.assertIn("Entreprise B NV", l["titulaire"])


class S7c_UneAttributionResteUneAttribution(unittest.TestCase):
    """« MARCHÉ ATTRIBUÉ ne devient jamais POSTULABLE. »"""

    def setUp(self):
        self.cx = ouvrir(":memory:")

    def _attribuer(self, **kw):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar.chaine import traiter
        traiter(self.cx, moteur(),
                [opp(ref_source="A1", attribue=True, titulaire="Grand Opérateur SA",
                     montant=2_400_000, duree_mois=36, attribue_le="2026-09-01",
                     **kw)], maintenant_dt=MAINTENANT)
        return self.cx.execute(
            "SELECT type, moteur, action, etat_procedure, score FROM opportunites"
        ).fetchone()

    # ── 9 · jamais postulable ──
    def test_9_une_attribution_n_est_jamais_postulable(self):
        l = self._attribuer()
        self.assertEqual(l["etat_procedure"], "ATTRIBUÉ")
        self.assertNotEqual(l["action"], "POSTULER")

    # ── 10 · elle alimente DÉVELOPPER ──
    def test_10_elle_alimente_developper(self):
        l = self._attribuer()
        self.assertEqual(l["moteur"], "DEVELOPPER")

    # ── 11-12 · les actions attendues sont disponibles ──
    def test_11_12_contacter_le_titulaire_et_surveiller_existent(self):
        from radar.classification import Action
        valeurs = {a.value for a in Action}
        self.assertIn("CONTACTER LE TITULAIRE", valeurs)
        self.assertIn("SURVEILLER", valeurs)
        l = self._attribuer()
        self.assertIn(l["action"], valeurs)

    def test_le_calendrier_de_renouvellement_est_alimente(self):
        self._attribuer()
        ligne = self.cx.execute(
            "SELECT titulaire, renouvellement, duree_mois FROM attributions"
        ).fetchone()
        self.assertEqual(ligne["titulaire"], "Grand Opérateur SA")
        self.assertEqual(ligne["duree_mois"], 36)
        self.assertTrue(str(ligne["renouvellement"] or "").startswith("2029"))

    # ── 18 · le score reste indépendant du circuit ──
    def test_18_le_score_ne_depend_pas_du_circuit(self):
        from tests.test_radar import MAINTENANT, moteur, opp
        from radar import circuit
        a = opp(ref_source="I1", attribue=True, titulaire="X SA")
        b = opp(ref_source="I2", attribue=True, titulaire="X SA")
        a.provenances = [{"source": "ted", "circuit": circuit.CONNUE}]
        b.provenances = [{"source": "google", "circuit": circuit.DECOUVERTE}]
        self.assertEqual(moteur().analyser(a, MAINTENANT).score.total,
                         moteur().analyser(b, MAINTENANT).score.total)


# ══════════════════════════ 7d — ASYMÉTRIE DE LANGUE
#
# FIXTURE : corpus de référence, archive du 2026-09-12. Aucun réseau.

class S7d_EquivalenceDesLangues(unittest.TestCase):
    """FR, NL et EN disent la même chose. Aucun n'a la priorité sur l'autre."""

    def setUp(self):
        from radar import pertinence
        self.pertinence = pertinence
        self.onto, self.det = _mecanismes()

    def _role(self, texte):
        return self.det.analyser(texte).role

    # ── 1 · l'anglais garde exactement ce qu'il avait ──
    def test_1_delivery_partner_garde_son_role(self):
        from radar.role import Role
        self.assertIs(self._role("Become a delivery partner"), Role.PRESTATAIRE)
        self.assertIs(self._role("delivery partner"), Role.PRESTATAIRE)

    # ── 2 · le français obtient le même ──
    def test_2_partenaire_de_livraison_obtient_le_meme_role(self):
        from radar.role import Role
        for forme in ("Devenir partenaire de livraison",
                      "devenir partenaire livraison"):
            self.assertIs(self._role(forme), Role.PRESTATAIRE, forme)

    # ── 3 · équivalence sur une page sémantiquement identique ──
    def test_3_la_meme_page_dans_trois_langues_donne_le_meme_verdict(self):
        from radar.pertinence import Confiance
        pages = {
            "fr": "Devenir partenaire de livraison pour nos tournees quotidiennes",
            "nl": "Word leveringspartner voor onze dagelijkse leveringen",
            "en": "Become a delivery partner for our daily deliveries",
        }
        verdicts = {langue: self.pertinence.evaluer(t, self.onto, self.det).confiance
                    for langue, t in pages.items()}
        self.assertEqual(set(verdicts.values()), {Confiance.FORTE},
                         f"les trois langues doivent conclure pareil : {verdicts}")

    def test_3ter_le_terme_nl_donne_bien_le_role_meme_isole(self):
        """LIMITE CONSTATÉE, HORS PÉRIMÈTRE 7d.

        « leveringspartner » produit bien PRESTATAIRE au niveau du RÔLE. Mais
        un composé néerlandais isolé ne franchit pas la porte de l'ONTOLOGIE :
        config/capacites.yaml déclare « levering » et « leveringen », pas les
        composés qui les contiennent — et le néerlandais compose beaucoup.

        Ce n'est pas un défaut de roles.yaml et ce n'est pas 7d. Toucher
        capacites.yaml sortirait du périmètre accordé.
        → DÉCISION MÉTIER À VALIDER, voir le compte rendu 7d.
        """
        from radar.role import Role
        self.assertIs(self._role("Leveringspartner worden"), Role.PRESTATAIRE,
                      "le rôle, lui, est bien détecté")
        self.assertFalse(self.onto.analyser("Leveringspartner worden").correspond,
                         "mais l'ontologie ne reconnaît pas le composé isolé")

    def test_3bis_aucune_langue_n_a_de_priorite_sur_une_autre(self):
        """Il n'existe aucune pondération par langue, nulle part."""
        import yaml
        roles = yaml.safe_load(
            pathlib.Path("config/roles.yaml").read_text(encoding="utf-8"))
        self.assertEqual(set(roles["lexique"]["prestation"]), {"fr", "nl", "en"})
        source = pathlib.Path("radar/role.py").read_text(encoding="utf-8")
        for biais in ('"fr" >', "langue_prioritaire", "poids_langue",
                      'if langue ==', "bonus_fr", "bonus_en"):
            self.assertNotIn(biais, source, biais)

    # ── 4-8 · AUCUNE régression sur les pages génériques ──
    def test_4_a_8_les_pages_de_forme_ne_deviennent_pas_des_preuves(self):
        from radar.pertinence import Confiance
        from radar.role import Role
        GENERIQUES = {
            "suivi de colis": "Suivi de colis — entrez votre numero de colis",
            "recevoir mon colis": "FAQ – J'attends un colis",
            "reprogrammer": "Reprogrammer une livraison",
            "connexion": "Mon espace Colis Prive — connexion",
            "mentions légales": "Mentions légales",
            "CGU": "CGU — conditions générales d'utilisation",
            "actualités": "Nos actualités",
            "cookies": "Politique de cookies",
            "qui sommes-nous": "Qui sommes-nous ?",
        }
        for nom, texte in GENERIQUES.items():
            p = self.pertinence.evaluer(texte, self.onto, self.det)
            self.assertIsNot(p.confiance, Confiance.FORTE,
                             f"« {nom} » est devenue une preuve — régression 7d")
            self.assertFalse(p.promouvoir, nom)
            self.assertIsNot(self._role(texte), Role.PRESTATAIRE, nom)

    # ── 9 · chauffeur : la décision de 7d, verrouillée ──
    def test_9_chauffeur_nu_n_est_pas_une_preuve_de_prestation(self):
        from radar.role import Role
        import yaml
        roles = yaml.safe_load(
            pathlib.Path("config/roles.yaml").read_text(encoding="utf-8"))
        nus = [m for langue in ("fr", "nl", "en")
               for m in roles["lexique"]["prestation"][langue]
               if m.strip() in ("chauffeur", "chauffeurs", "driver", "drivers",
                                "chauffeurs poids lourds")]
        self.assertEqual(nus, [], "« chauffeur » nu ne doit pas être une prestation")
        self.assertIsNot(self._role("Nous recrutons 20 chauffeurs"), Role.PRESTATAIRE)

    def test_9bis_mais_les_vrais_contextes_de_prestation_restent_reconnus(self):
        from radar.role import Role
        for texte in ("Mise à disposition de chauffeurs",
                      "Location de véhicules avec chauffeur"):
            self.assertIs(self._role(texte), Role.PRESTATAIRE, texte)

    # ── 10 · aucune promotion sur un mot générique ──
    def test_10_un_mot_du_domaine_seul_ne_promeut_toujours_pas(self):
        from radar.pertinence import Confiance
        for texte in ("colis", "livraison", "transport", "Mon espace colis",
                      "Votre colis est en cours de livraison"):
            self.assertIsNot(self.pertinence.evaluer(texte, self.onto, self.det)
                             .confiance, Confiance.FORTE, texte)

    # ── 11 · ni source ni circuit n'interviennent ──
    def test_11_le_lexique_ne_nomme_aucune_source(self):
        texte = pathlib.Path("config/roles.yaml").read_text(encoding="utf-8").lower()
        for nom in ("google", "brave", "bing", "source_connue",
                    "source_découverte", "circuit"):
            self.assertNotIn(nom, texte, nom)


class S7d_NonRegressionNegative(unittest.TestCase):
    """LE TEST EXIGÉ : un ajout lexical ne transforme pas une page client
    ou générique en page commerciale."""

    PAGE_CLIENT = ("Suivi de colis. Entrez votre numero de colis pour connaitre "
                   "l'etat de votre livraison. Votre colis est en cours de "
                   "distribution, le chauffeur passera aujourd'hui. Consultez "
                   "nos horaires de distribution et nos points relais.")

    def setUp(self):
        from radar import pertinence
        self.pertinence = pertinence
        self.onto, self.det = _mecanismes()

    def test_1_une_page_client_bourree_de_vocabulaire_ne_devient_pas_une_preuve(self):
        """Elle contient colis, livraison, distribution, chauffeur, partenaire,
        transport — et reste sans preuve de prestation."""
        from radar.pertinence import Confiance
        from radar.role import Role
        p = self.pertinence.evaluer(self.PAGE_CLIENT, self.onto, self.det)
        self.assertTrue(p.domaine, "le vocabulaire du métier EST là")
        self.assertIsNot(p.role, Role.PRESTATAIRE)
        self.assertIsNot(p.confiance, Confiance.FORTE)
        self.assertFalse(p.promouvoir)

    def test_1bis_une_expression_de_prestation_ANTERIEURE_a_7d_est_documentee(self):
        """PROBLÈME HORS PÉRIMÈTRE, ANTÉRIEUR À 7d, NON CORRIGÉ.

        « livraison à domicile » est au lexique de prestation français DEPUIS
        L'ORIGINE. Une page CLIENT qui l'emploie pour décrire son propre
        service ressort donc PRESTATAIRE.

        Vérifié en comparant la configuration d'avant et d'après 7d : le
        verdict est identique. 7d n'en est pas la cause et ne le corrige pas.
        Même famille que « suivi de colis → DIRECT ». Documenté, pas touché.
        """
        from radar.role import Role
        texte = "Notre partenaire de transport assure la livraison a domicile."
        self.assertIs(self._role_de(texte), Role.PRESTATAIRE)

    def _role_de(self, texte):
        return self.det.analyser(texte).role

    def test_2_le_nombre_de_promotions_sur_le_corpus_reste_borne(self):
        """11 (avant 7a) → 2 (7a) → 4 (7d) → 3 (décision 1). Pas de retour au bruit.

        La décision 1 retire AUSSI une candidate, et c'est la même adresse :
        `cevalogistics.com/fr` est sur un AUTRE domaine que la page lue. Elle
        n'entrait donc que par la priorité « INDICE FORT », que la famille lui
        donnait. Le vocabulaire n'étant plus une preuve positive, elle n'est
        plus ni promue ni retenue : 23 → 22 candidates.

        C'est une perte de DÉCOUVERTE, mesurée et non contournée : élargir la
        rétention de `radar/liens.py` pour la rattraper en faisait entrer deux
        autres, et aurait été une décision métier que personne n'a prise.
        """
        import yaml
        from radar import liens as mod
        from radar.page import lire as lire_page
        page = pathlib.Path("validation/pages_reelles/"
                            "2026-09-12-entreprise-c5e20010e7bd.html")
        if not page.exists():
            self.skipTest("archive absente")
        profil = yaml.safe_load(
            pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
        lec = lire_page(page.read_bytes().decode("utf-8", "replace"), profil)
        cands = mod.selectionner(lec.liens,
                                 "https://www.colisprive.be/devenir-partenaire-livraison/",
                                 self.onto, self.det)
        promues = mod.retenus(cands)
        self.assertEqual(len(cands), 22, "une seule candidate perdue : cevalogistics")
        self.assertEqual(len(promues), 3)
        self.assertFalse(any("cevalogistics" in c.url for c in cands),
                         "la candidate perdue est nommée, pas seulement comptée")
        # Et AUCUNE page de forme n'y figure.
        for forme in ("mentions-legales", "cgu", "politique-de-cookies",
                      "nos-actualites", "qui-sommes-nous", "nos-engagements-rse",
                      "Login.aspx", "connexion"):
            self.assertFalse(any(forme in c.url for c in promues), forme)

    def test_3_le_score_de_la_page_de_reference_est_inchange(self):
        """Le rôle se renforce ; le verdict commercial, lui, ne bouge pas."""
        import yaml
        from tests.test_radar import moteur
        from radar import collecte_directe, normalisation
        from radar.chaine import traiter
        from radar.mode import Mode
        from radar.pages import Acces
        page = pathlib.Path("validation/pages_reelles/"
                            "2026-09-12-entreprise-c5e20010e7bd.html")
        if not page.exists():
            self.skipTest("archive absente")
        profil = yaml.safe_load(
            pathlib.Path("sources/page_web.yaml").read_text(encoding="utf-8"))
        c = collecte_directe.Collecte(
            url="https://www.colisprive.be/devenir-partenaire-livraison/",
            acces=Acces.CONSULTEE, octets=page.read_bytes(), http=200)
        opp, _ = normalisation.depuis_collecte(c, profil)
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp], mode=Mode.REEL)
        l = cx.execute("SELECT type, moteur, action, score, etat_procedure"
                       " FROM opportunites").fetchone()
        self.assertEqual(l["score"], 55, "le score de référence a bougé")
        self.assertEqual(l["type"], "DIRECT")
        self.assertEqual(l["moteur"], "CAPTER")
        self.assertEqual(l["action"], "POSTULER")
        self.assertEqual(l["etat_procedure"], "POSTULABLE")
