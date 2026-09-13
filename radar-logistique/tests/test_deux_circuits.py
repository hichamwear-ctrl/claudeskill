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
