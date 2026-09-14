"""LES QUATRE DÉCISIONS MÉTIER, VERROUILLÉES UNE PAR UNE.

    1  veto d'ontologie à deux niveaux      radar/pertinence.py · radar/ancrage.py
    2  lexique + ancrage resserré           config/roles.yaml · radar/nature.py
                                            radar/chaine.py
    3  le corps lu porte la preuve          radar/nature.py
    4  une adresse, une fiche               radar/consolidation.py

Chaque classe ci-dessous porte le numéro de sa décision. Aucun vocabulaire
n'est redéfini ici : tous les tests interrogent l'ontologie, le détecteur de
rôle et les listes RÉELS du projet, chargés depuis la configuration.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import yaml                                                    # noqa: E402

from radar import ancrage as mod_ancrage, nature as nat        # noqa: E402
from radar import consolidation, pertinence                    # noqa: E402
from radar.activite import Ontologie                           # noqa: E402
from radar.pertinence import Confiance                         # noqa: E402
from radar.role import DetecteurDeRole, Role                   # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent


def _cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


def _mecanismes():
    prof = _cfg("profil.yaml")
    return (Ontologie(_cfg("config/capacites.yaml"), prof["familles_actives"],
                      prof.get("familles_exclues")),
            DetecteurDeRole(_cfg("config/roles.yaml")))


# ═══════════════════════════════════════════ DÉCISION 1 — LA PORTE
class D1_LaPorteEstADeuxNiveaux(unittest.TestCase):
    """Le vocabulaire est UN indice parmi six. Il n'est ni nécessaire, ni suffisant."""

    def setUp(self):
        self.onto, self.det = _mecanismes()

    def p(self, texte):
        return pertinence.evaluer(texte, self.onto, self.det)

    # ── 1 · vocabulaire métier SEUL → pas de promotion ──
    def test_1_le_vocabulaire_seul_ne_promeut_pas(self):
        for vitrine in (
                "Spécialiste du transport et de la logistique en Belgique depuis 1998.",
                "Prestations de logistique et gestion d'entrepôt",
                "Logistique en entrepôts Belgique — entreprises et fournisseurs"):
            p = self.p(vitrine)
            self.assertFalse(p.promouvoir, vitrine)
            self.assertIn(mod_ancrage.VOCABULAIRE, p.signaux,
                          "…mais il ancre toujours : la page reste lisible")

    def test_1bis_ce_qui_RESTE_du_defaut_de_lexique_A6(self):
        """A6 — RÉSOLUE POUR LA VITRINE QUI SE VEND, PAS POUR LA VITRINE NUE.

        Le lexique de PRESTATION nomme un service ; il ne dit pas qui
        l'achète et qui le vend. Une vitrine qui écrit « affrètement » sort
        PRESTATAIRE comme le client qui le cherche.

        Ce qui est corrigé (voir `D1bis_A6…`) : la page qui porte des
        marqueurs de VENTE — tarifs, devis, « nos services » — est arrêtée
        par la contre-preuve `nature.offre_de_service_dans`.

        Ce qui NE l'est PAS : la vitrine NUE, sans le moindre marqueur. Rien
        dans son texte ne dit qu'elle vend. Elle reste promue, et c'est
        assumé — depuis la décision 2 elle ressort ⚪ CLASSER SANS SUITE une
        fois collectée, donc elle ne coûte qu'une place de collecte.
        """
        p = self.p("Transport routier et affrètement — notre métier depuis 40 ans")
        self.assertIs(p.role, Role.PRESTATAIRE)
        self.assertTrue(p.promouvoir,
                        "si ce test échoue, le reste du défaut a été corrigé : "
                        "vérifier que c'était une décision et non un effet de bord")

    # ── 2 · besoin explicite SANS vocabulaire → promotion possible ──
    def test_2_un_besoin_sans_vocabulaire_metier_promeut(self):
        texte = ("Nous recherchons un partenaire pour acheminer chaque jour "
                 "nos commandes vers nos douze magasins.")
        self.assertFalse(self.onto.analyser(texte).correspond,
                         "prérequis du test : notre ontologie ne reconnaît rien ici")
        p = self.p(texte)
        self.assertIs(p.confiance, Confiance.FORTE)
        self.assertTrue(p.promouvoir,
                        "une entreprise a le droit d'employer ses propres mots")

    # ── 3 · une date pertinente sans vocabulaire → ancrage ──
    def test_3_une_date_ancre_sans_vocabulaire(self):
        p = self.p("Le nouveau contrat démarre le 15 mars 2026 "
                   "pour nos douze points de vente.")
        self.assertIsNot(p.confiance, Confiance.AUCUNE)
        self.assertIn(mod_ancrage.DATE, p.signaux)
        self.assertFalse(p.promouvoir, "ancrer n'est pas promouvoir")

    # ── 4 · un volume pertinent sans vocabulaire → ancrage ──
    def test_4_un_volume_ancre_sans_vocabulaire(self):
        p = self.p("Environ 1 200 expéditions par semaine depuis notre site de Gand.")
        self.assertIsNot(p.confiance, Confiance.AUCUNE)
        self.assertIn(mod_ancrage.CHIFFRE, p.signaux)
        self.assertFalse(p.promouvoir)

    # ── 5 · une exigence explicite sans vocabulaire → ancrage ──
    def test_5_une_exigence_ancre_sans_vocabulaire(self):
        p = self.p("Une assurance RC professionnelle est exigée "
                   "et la certification est obligatoire.")
        self.assertIsNot(p.confiance, Confiance.AUCUNE)
        self.assertIn(mod_ancrage.EXIGENCE, p.signaux)
        self.assertFalse(p.promouvoir)

    # ── 6 · page totalement éditoriale → rien ──
    def test_6_une_page_editoriale_ne_promeut_pas(self):
        for texte in ("Le commerce en ligne a beaucoup changé les habitudes "
                      "des Belges ces dernières années.",
                      "Mentions légales et politique de confidentialité.",
                      "Nos actualités · Qui sommes-nous ? · Contact"):
            self.assertFalse(self.p(texte).promouvoir, texte)

    # ── 7 · page générique d'entreprise → rien ──
    def test_7_une_page_generique_d_entreprise_ne_promeut_pas(self):
        p = self.p("Notre entreprise familiale accompagne ses clients "
                   "depuis trois générations.")
        self.assertIs(p.confiance, Confiance.AUCUNE)
        self.assertFalse(p.promouvoir)

    # ── 8 · besoin + vocabulaire → promotion ──
    def test_8_un_besoin_avec_vocabulaire_promeut(self):
        p = self.p("Nous recherchons un partenaire de livraison pour assurer "
                   "nos tournées régulières en Wallonie.")
        self.assertIs(p.confiance, Confiance.FORTE)
        self.assertTrue(p.promouvoir)

    # ── 9 · aucun ancrage → AUCUNE ──
    def test_9_sans_le_moindre_ancrage_c_est_AUCUNE(self):
        p = self.p("Bienvenue sur notre site. Politique de cookies. CGU.")
        self.assertIs(p.confiance, Confiance.AUCUNE)
        self.assertIn("aucun ancrage commercial", p.raison())

    # ── LE PIÈGE NOMMÉ : le recrutement ──
    def test_10_le_recrutement_ne_fait_pas_une_opportunite_de_transport(self):
        """« Rejoignez-nous », « Wanted », « Become part of our team ».

        N'importe quelle entreprise de n'importe quel secteur les écrit. Les
        promouvoir ferait entrer en surveillance toutes les pages de
        recrutement du web.
        """
        for texte in ("Rejoignez-nous ! Become part of our team.",
                      "Comptable expérimenté wanted pour notre cabinet.",
                      "Devenez client et profitez de nos offres."):
            self.assertFalse(self.p(texte).promouvoir, texte)

    def test_11_recruter_des_chauffeurs_reste_un_recrutement(self):
        """DÉCISION 7d, toujours en vigueur — vérifiée à la nouvelle porte.

        « Nous recrutons 20 chauffeurs » embauche des salariés ; ça n'achète
        aucune prestation de transport.
        """
        for emploi in ("Recrutement de chauffeurs",
                       "Nous recrutons 20 chauffeurs",
                       "Offre d'emploi chauffeur livreur CDI"):
            self.assertFalse(self.p(emploi).promouvoir, emploi)

    def test_12_mais_recruter_des_sous_traitants_est_une_demande(self):
        """Le pendant du test 11 : là, une prestation EST demandée."""
        p = self.p("Nous recrutons des sous-traitants pour nos tournées.")
        self.assertTrue(p.promouvoir)
        self.assertIs(p.role, Role.PRESTATAIRE)

    def test_13_la_contre_preuve_fournisseur_prime_toujours(self):
        p = self.p("Fourniture et livraison de repas en liaison froide "
                   "pour les écoles communales.")
        self.assertIs(p.role, Role.FOURNISSEUR)
        self.assertFalse(p.promouvoir)

    def test_14_le_module_d_ancrage_n_a_aucun_vocabulaire_metier(self):
        """Pas de deuxième ontologie cachée. Vérifié sur l'AST, pas sur le texte.

        Les mots du métier apparaissent LÉGITIMEMENT dans les commentaires de
        `radar/ancrage.py` — ils expliquent précisément ce qu'on refuse d'y
        mettre. Seules les chaînes de code sont donc inspectées.
        """
        import ast
        arbre = ast.parse((RACINE / "radar/ancrage.py").read_text(encoding="utf-8"))
        docstrings = set()
        for n in ast.walk(arbre):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)):
                d = ast.get_docstring(n, clean=False)
                if d:
                    docstrings.add(d)
        litteraux = " ".join(
            n.value.lower() for n in ast.walk(arbre)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value not in docstrings)
        for interdit in ("palette", "tournee", "tournée", "colis", "camion",
                         "fret", "messagerie", "entrepot", "entrepôt",
                         "transporteur", "chauffeur"):
            self.assertNotIn(interdit, litteraux,
                             f"« {interdit} » est du métier : sa place est en "
                             "configuration, pas dans radar/ancrage.py")


# ═══════════════════════════ A6 — LA PAGE QUI VEND NE DEMANDE PAS
class A6_UneVitrineQuiSeVendNEstPasUneDemande(unittest.TestCase):
    """La contre-preuve existante, LUE à la porte au lieu d'être réécrite."""

    def setUp(self):
        self.onto, self.det = _mecanismes()

    def p(self, texte):
        return pertinence.evaluer(texte, self.onto, self.det)

    def test_1_une_vitrine_qui_affiche_ses_tarifs_n_est_plus_promue(self):
        for vend in ("Affrètement et transport — nos services et nos tarifs. "
                     "Demandez un devis gratuit.",
                     "Livraison à domicile partout en Belgique. "
                     "Comparez nos prix, obtenez un devis.",
                     "Prestataire logistique : nos solutions, nos tarifs."):
            p = self.p(vend)
            self.assertFalse(p.promouvoir, vend)
            self.assertTrue(any("VEND" in x for x in p.preuves), p.preuves)

    def test_2_la_demande_l_emporte_toujours_sur_la_vente(self):
        """Une page qui vend ET qui cherche reste une demande.

        C'est le garde-fou d'origine de `est_une_offre`, et il est conservé
        mot pour mot : sans lui, un transporteur cherchant un sous-traitant
        serait écarté parce que son site affiche aussi ses tarifs.
        """
        mixte = ("Nos tarifs sont les moins chers. Demandez un devis. "
                 "Nous recherchons aussi un transporteur partenaire "
                 "pour la Wallonie.")
        self.assertFalse(nat.offre_de_service_dans(mixte))
        self.assertTrue(self.p(mixte).promouvoir)

    def test_3_aucun_vrai_positif_du_jeu_reel_n_est_perdu(self):
        """Les cinq adresses jugées du 14/09, avant et après la correction."""
        for nom, titre, attendu in (
                ("Colis Privé", "Devenir partenaire de livraison - Colis Privé BeLux", True),
                ("Bulbul", "Sous-traitance transport en Belgique | Partenaire DPD & DHL", True),
                ("Beeliv", "Devenir partenaire | Beeliv", False),
                ("PostNL", "Travailler comme partenaire de PostNL | PostNL", False),
                ("Shippr", "Devenir livreur indépendant en Belgique : guide complet", False)):
            self.assertIs(self.p(titre).promouvoir, attendu, nom)
            self.assertFalse(nat.offre_de_service_dans(titre),
                             f"{nom} ne vend rien")

    def test_4_la_contre_preuve_n_est_pas_reecrite_mais_lue(self):
        """Une seule implémentation : `est_une_offre` délègue au texte."""
        class Page:
            intitule = "Nos tarifs et nos services de transport"
            texte = ""
        self.assertTrue(nat.est_une_offre(Page()))
        self.assertTrue(nat.offre_de_service_dans(
            "Nos tarifs et nos services de transport "))
        import ast
        arbre = ast.parse((RACINE / "radar/pertinence.py").read_text(encoding="utf-8"))
        listes = {n.id for n in ast.walk(arbre) if isinstance(n, ast.Name)}
        self.assertNotIn("OFFRE_DE_SERVICE", listes,
                         "la porte LIT la contre-preuve, elle ne la recopie pas")


# ═══════════════════════════ A7 — RETENIR N'EST PAS PROMOUVOIR
class A7_UnLienExterneQuiNommeLeMetierEstRetenu(unittest.TestCase):
    """Une candidate n'est pas une opportunité. Elle entre dans l'analyse."""

    def setUp(self):
        self.onto, self.det = _mecanismes()
        from radar import liens
        self.liens = liens

    def _sel(self, bruts, base="https://client.be/page"):
        return self.liens.selectionner(bruts, base, self.onto, self.det)

    def test_1_un_lien_externe_nommant_une_FAMILLE_est_retenu(self):
        c = self._sel([{"href": "https://www.cevalogistics.com/fr",
                        "texte": "Logistique et entreposage"}])
        self.assertEqual(len(c), 1, "retenue comme candidate")
        self.assertFalse(c[0].promouvable, "et JAMAIS promue automatiquement")

    def test_2_le_DOMAINE_generique_ne_suffit_toujours_pas(self):
        """Mesuré : retenir sur le domaine faisait entrer 8 adresses de bruit
        sur les quatre pages réelles — dépôt de code, page de login, wiki."""
        for bruit in ("https://github.com/pypi/warehouse",
                      "https://depot.dev",
                      "https://www.colisprive.com/agence/Account/Login.aspx"):
            self.assertEqual(self._sel([{"href": bruit, "texte": ""}]), [], bruit)

    def test_3_une_candidate_retenue_ainsi_n_est_jamais_promue(self):
        c = self._sel([{"href": "https://www.cevalogistics.com/fr",
                        "texte": "Logistique et entreposage"},
                       {"href": "https://autre.be/devenir-transporteur",
                        "texte": "Devenir transporteur"}])
        self.assertEqual(len(c), 2)
        promues = self.liens.retenus(c)
        self.assertEqual(len(promues), 1)
        self.assertIn("devenir-transporteur", promues[0].url,
                      "seule la page qui DEMANDE est promue")


# ═══════════════════════════════════════════ DÉCISION 2 — LE LEXIQUE
class D2_LeLexiqueEnrichi(unittest.TestCase):
    """Chaque terme validé, testé individuellement, et chaque refus assumé."""

    def setUp(self):
        self.onto, self.det = _mecanismes()

    def role_de(self, texte):
        return self.det.analyser(texte).role

    # ── les désignations de PRESTATION ajoutées à config/roles.yaml ──
    def test_1_chaque_designation_de_prestation_est_reconnue(self):
        for terme in ("sous-traitant", "sous-traitants", "sous-traitance",
                      "sous-traitance transport", "sous-traitants transport",
                      "partenaire livreur", "partenaires livreurs",
                      "livreur partenaire"):
            self.assertIs(self.role_de(terme), Role.PRESTATAIRE, terme)

    def test_2_les_formes_anterieures_restent_reconnues(self):
        """L'ajout complète, il ne remplace pas."""
        for terme in ("sous-traitant transport", "sous-traitance de transport",
                      "partenaire de livraison", "transporteur",
                      "partenaire transport"):
            self.assertIs(self.role_de(terme), Role.PRESTATAIRE, terme)

    def test_3_livreur_independant_est_REFUSE_et_c_est_delibere(self):
        """C'est un STATUT D'EMPLOI, pas une prestation achetée.

        Même raison que « chauffeur », maintenu hors du lexique par la
        décision 7d. Si ce test échoue, c'est que le terme a été ajouté :
        refaire la mesure sur les guides administratifs du jeu réel.
        """
        self.assertIsNot(self.role_de("livreur indépendant"), Role.PRESTATAIRE)
        for guide in ("Devenir chauffeur indépendant en Belgique : permis et démarches",
                      "Comment Devenir Chauffeur Indépendant en Belgique"):
            self.assertFalse(
                pertinence.evaluer(guide, self.onto, self.det).promouvoir, guide)

    # ── le BESOIN ajouté à nature.BESOIN_DIRECT ──
    def test_4_travailler_comme_partenaire_est_un_besoin(self):
        """Le jumeau exact de « devenir partenaire », présent depuis l'origine."""
        self.assertTrue(nat.besoin_exprime_dans(
            "Travailler comme partenaire de PostNL | PostNL"))
        self.assertTrue(nat.besoin_exprime_dans(
            "Devenir partenaire de livraison - Colis Privé BeLux"))

    def test_5_les_formulations_ambigues_sont_des_SIGNAUX_pas_des_FAITS(self):
        """« sous traitance transport » et « devenir livreur » : refusées en FAIT.

        Une entreprise qui écrit « Sous-traitance transport en Belgique »
        DÉCRIT ce qu'elle fait. Personne ne demande rien. En faire un FAIT
        présenterait une auto-description comme un besoin publié.
        """
        for terme in ("Sous-traitance transport en Belgique | Partenaire DPD & DHL",
                      "Devenir livreur indépendant en Belgique : guide complet",
                      "Devenir sous-traitant : mode d'emploi"):
            self.assertFalse(nat.besoin_exprime_dans(terme),
                             f"« {terme} » ne doit pas être un FAIT")
            self.assertTrue(nat.evenement_observable_dans(terme),
                            f"« {terme} » doit rester un SIGNAL")

    def test_6_un_signal_dit_que_personne_n_a_rien_demande(self):
        class Page:
            intitule = "Sous-traitance transport en Belgique | Partenaire DPD & DHL"
            texte = ""
        self.assertIs(nat.qualifier(Page()), nat.Nature.SIGNAL)
        self.assertFalse(nat.Nature.SIGNAL.depot_attendu)

    # ── l'ANCRAGE resserré ──
    def test_7_une_famille_seule_n_est_plus_un_ancrage_commercial(self):
        a = mod_ancrage.depuis_opportunite(
            _Opp(), vocabulaire=True, nature=nat.Nature.HYPOTHESE)
        self.assertTrue(a.ancre, "elle ancre toujours — la porte reste ouverte")
        self.assertFalse(a.commercial, "…mais il n'y a aucune affaire ici")

    def test_8_un_seul_fait_suffit_a_ancrer_commercialement(self):
        """La liste des faits est INCHANGÉE : seule la famille en est sortie."""
        for champ, valeur in (("echeance_brute", "2026-12-01"),
                              ("date_demarrage", "2026-12-01"),
                              ("montant", 50000), ("cadence", "quotidienne"),
                              ("duree_mois", 24), ("km_annuels", 80000),
                              ("vehicules_requis", 3), ("chauffeurs_requis", 2),
                              ("exigences_texte", ["licence de transport"])):
            o = _Opp()
            setattr(o, champ, valeur)
            a = mod_ancrage.depuis_opportunite(
                o, vocabulaire=True, nature=nat.Nature.HYPOTHESE)
            self.assertTrue(a.commercial, champ)

    def test_9_un_besoin_ou_un_signal_ancre_commercialement(self):
        for nature in (nat.Nature.FAIT, nat.Nature.SIGNAL):
            a = mod_ancrage.depuis_opportunite(_Opp(), vocabulaire=False,
                                               nature=nature)
            self.assertTrue(a.commercial, nature.value)
        a = mod_ancrage.depuis_opportunite(_Opp(), vocabulaire=False,
                                           nature=nat.Nature.HYPOTHESE)
        self.assertFalse(a.commercial)

    def test_10_la_chaine_lit_des_CHAMPS_jamais_des_formes(self):
        """Un titre réel qui porte une date et un nombre — et aucun besoin.

        « Sous Traitant Transport : plus de 50 emplois (18 février 2026) »
        est une page d'offres d'emploi. La chaîne ne doit pas y voir un
        ancrage commercial parce qu'un nombre et un mois y figurent : elle
        lit les CHAMPS extraits par l'adaptateur, qui sont ici vides.
        """
        o = _Opp()
        o.intitule = ("Sous Traitant Transport : plus de 50 emplois "
                      "(18 février 2026) | Indeed")
        a = mod_ancrage.depuis_opportunite(o, vocabulaire=True,
                                           nature=nat.Nature.HYPOTHESE)
        self.assertFalse(a.commercial)


class _Opp:
    """Une opportunité NUE — aucun fait, aucun champ rempli."""
    intitule = ""
    texte = ""
    est_signal = False
    echeance_brute = None
    date_demarrage = None
    montant = None
    cadence = None
    duree_mois = None
    km_annuels = None
    vehicules_requis = None
    chauffeurs_requis = None
    lots: list = []
    exigences: dict = {}
    exigences_texte: list = []


# ═══════════════════════════════════════════ DÉCISION 3 — LE CORPS LU
class D3_LeCorpsLuPorteLaPreuve(unittest.TestCase):
    """Le titre n'est plus la condition d'existence d'un fait."""

    BESOIN = ("Nous recherchons un partenaire de livraison pour assurer "
              "nos tournées régulières en Wallonie.")
    VITRINE = ("Notre entreprise familiale accompagne ses clients "
               "depuis trois générations.")

    def nature_de(self, intitule, texte):
        class P:
            pass
        P.intitule, P.texte = intitule, texte
        return nat.qualifier(P())

    def test_1_avec_titre_pertinent_et_corps(self):
        self.assertIs(self.nature_de("Nos partenaires", self.BESOIN),
                      nat.Nature.FAIT)

    def test_2_sans_aucun_titre_declare_le_corps_suffit(self):
        for absent in ("", nat.SANS_INTITULE, None):
            self.assertIs(self.nature_de(absent, self.BESOIN), nat.Nature.FAIT,
                          repr(absent))

    def test_3_un_titre_sans_rapport_ne_change_rien_au_verdict(self):
        """LE DÉFAUT D'ORIGINE : « Actualités » valait « Nos partenaires ».

        Après correction, les trois donnent le même verdict — et c'est le
        CORPS qui le donne, ce qui est le point.
        """
        pertinent = self.nature_de("Nos partenaires", self.BESOIN)
        hors_sujet = self.nature_de("Actualités", self.BESOIN)
        absent = self.nature_de(nat.SANS_INTITULE, self.BESOIN)
        self.assertEqual({pertinent, hors_sujet, absent}, {nat.Nature.FAIT})

    def test_4_un_titre_sans_rapport_ne_prouve_rien_tout_seul(self):
        self.assertIs(self.nature_de("Actualités", ""), nat.Nature.HYPOTHESE)
        self.assertIs(self.nature_de("Nos partenaires", ""), nat.Nature.HYPOTHESE)

    def test_5_un_corps_sans_preuve_ne_promeut_rien(self):
        for titre in ("Nos partenaires", "", nat.SANS_INTITULE):
            self.assertIs(self.nature_de(titre, self.VITRINE),
                          nat.Nature.HYPOTHESE, repr(titre))

    def test_6_aucun_titre_n_est_jamais_fabrique(self):
        """Ni la première phrase, ni un h1 : l'absence se DIT."""
        class P:
            intitule, texte = nat.SANS_INTITULE, self.BESOIN
        self.assertFalse(nat.titre_declare(P()))
        self.assertIs(nat.qualifier(P()), nat.Nature.FAIT)

    def test_7_titre_declare_distingue_le_declare_du_fabrique(self):
        class Declare:
            intitule, texte = "Nos partenaires", ""

        class NonDeclare:
            intitule, texte = nat.SANS_INTITULE, ""
        self.assertTrue(nat.titre_declare(Declare()))
        self.assertFalse(nat.titre_declare(NonDeclare()))


# ═══════════════════════════════════════════ DÉCISION 4 — UNE ADRESSE
class D4_UneAdresseUneFiche(unittest.TestCase):
    """Les avis restent séparés ; l'affichage, lui, est consolidé."""

    @staticmethod
    def lecture(url, type_, fiabilite, score, source, vue="2026-09-14"):
        return {"ref_source": url, "type": type_, "fiabilite": fiabilite,
                "score": score, "source_avis": source, "derniere_vue": vue,
                "nature": "FAIT", "action": "CONTACTER L'ENTREPRISE"}

    def test_1_deux_lectures_d_une_meme_url_font_une_seule_adresse(self):
        lignes = [self.lecture("https://x.be/p", "DIRECT", "MOYENNE", 45, "collecte"),
                  self.lecture("https://x.be/p", "PAS ENCORE UNE OPPORTUNITÉ",
                               "FAIBLE", 24, "import:m")]
        ad = consolidation.grouper(lignes)
        self.assertEqual(len(ad), 1)
        self.assertEqual(len(ad[0].lectures), 2, "les deux lectures sont gardées")

    def test_2_la_lecture_la_mieux_etayee_ouvre_la_fiche(self):
        """L'ordre vient de l'axe NIVEAU DE PREUVE, déjà présent au projet."""
        lignes = [self.lecture("https://x.be/p", "PAS ENCORE UNE OPPORTUNITÉ",
                               "FAIBLE", 90, "import:m"),
                  self.lecture("https://x.be/p", "DIRECT", "FORTE", 10, "collecte")]
        ad = consolidation.grouper(lignes)[0]
        self.assertEqual(ad.principale["type"], "DIRECT")
        self.assertEqual(ad.principale["fiabilite"], "FORTE",
                         "la preuve prime sur le score")

    def test_3_a_preuve_egale_le_score_puis_la_date_departagent(self):
        lignes = [self.lecture("https://x.be/p", "A", "MOYENNE", 10, "s1"),
                  self.lecture("https://x.be/p", "B", "MOYENNE", 40, "s2")]
        self.assertEqual(consolidation.grouper(lignes)[0].principale["type"], "B")
        lignes = [self.lecture("https://x.be/p", "A", "MOYENNE", 10, "s1", "2026-01-01"),
                  self.lecture("https://x.be/p", "B", "MOYENNE", 10, "s2", "2026-09-14")]
        self.assertEqual(consolidation.grouper(lignes)[0].principale["type"], "B",
                         "à égalité, la lecture la plus récente")

    def test_4_la_contradiction_est_affichee_jamais_masquee(self):
        lignes = [self.lecture("https://x.be/p", "DIRECT", "MOYENNE", 45, "collecte"),
                  self.lecture("https://x.be/p", "PAS ENCORE UNE OPPORTUNITÉ",
                               "FAIBLE", 24, "import:m")]
        ad = consolidation.grouper(lignes)[0]
        self.assertTrue(ad.divergentes)
        bloc = "\n".join(consolidation.bloc_divergence(
            ad, fiche=lambda l: str(l["type"])))
        self.assertIn(consolidation.DIVERGENCE, bloc)
        self.assertIn("DIRECT", bloc)
        self.assertIn("PAS ENCORE UNE OPPORTUNITÉ", bloc)

    def test_5_la_provenance_de_chaque_lecture_est_conservee(self):
        lignes = [self.lecture("https://x.be/p", "DIRECT", "MOYENNE", 45,
                               "COLLECTÉ HORS RADAR"),
                  self.lecture("https://x.be/p", "PAS ENCORE UNE OPPORTUNITÉ",
                               "FAIBLE", 24, "import:websearch-assistant")]
        ad = consolidation.grouper(lignes)[0]
        bloc = "\n".join(consolidation.bloc_divergence(
            ad, fiche=lambda l: str(l["type"])))
        self.assertIn("import:websearch-assistant", bloc)
        sources = {l["source_avis"] for l in ad.lectures}
        self.assertEqual(len(sources), 2, "aucune provenance n'est perdue")

    def test_6_deux_lectures_concordantes_ne_crient_pas_a_la_divergence(self):
        lignes = [self.lecture("https://x.be/p", "DIRECT", "MOYENNE", 45, "s1"),
                  self.lecture("https://x.be/p", "DIRECT", "FAIBLE", 24, "s2")]
        ad = consolidation.grouper(lignes)[0]
        self.assertFalse(ad.divergentes)
        bloc = "\n".join(consolidation.bloc_divergence(
            ad, fiche=lambda l: str(l["type"])))
        self.assertNotIn(consolidation.DIVERGENCE, bloc)
        self.assertIn("AUTRE(S) LECTURE(S)", bloc)

    def test_7_une_adresse_seule_n_affiche_aucun_bloc(self):
        lignes = [self.lecture("https://x.be/p", "DIRECT", "MOYENNE", 45, "s1")]
        ad = consolidation.grouper(lignes)[0]
        self.assertEqual(consolidation.bloc_divergence(
            ad, fiche=lambda l: str(l["type"])), [])

    def test_8_l_ordre_des_adresses_suit_celui_d_arrivee(self):
        """Regrouper ne fait jamais remonter ni descendre une affaire."""
        lignes = [self.lecture("https://a.be/p", "DIRECT", "FORTE", 90, "s"),
                  self.lecture("https://b.be/p", "DIRECT", "FORTE", 50, "s"),
                  self.lecture("https://a.be/p", "DIRECT", "FAIBLE", 10, "s")]
        self.assertEqual([a.url for a in consolidation.grouper(lignes)],
                         ["https://a.be/p", "https://b.be/p"])

    def test_9_le_module_n_ecrit_rien(self):
        """Une VUE, et rien d'autre : ni INSERT, ni UPDATE, ni DELETE."""
        import ast
        arbre = ast.parse(
            (RACINE / "radar/consolidation.py").read_text(encoding="utf-8"))
        docstrings = set()
        for n in ast.walk(arbre):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)):
                d = ast.get_docstring(n, clean=False)
                if d:
                    docstrings.add(d)
        code = " ".join(
            n.value.upper() for n in ast.walk(arbre)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value not in docstrings)
        for interdit in ("INSERT", "UPDATE ", "DELETE", "COMMIT"):
            self.assertNotIn(interdit, code, interdit)
        appels = {n.attr for n in ast.walk(arbre) if isinstance(n, ast.Attribute)}
        self.assertNotIn("execute", appels, "ce module ne parle pas à la base")


# ═══════════════════════ LE SCHÉMA N'A PAS BOUGÉ — décision 4, contrainte
class D4_LeSchemaEstIntact(unittest.TestCase):
    def test_la_cle_d_un_avis_reste_source_plus_reference(self):
        """UNIQUE(source, ref_source) — la provenance ne se perd pas.

        Le regroupement est un affichage. Remplacer cette clé par
        UNIQUE(ref_source) supprimerait la mesure d'apport propre des
        moteurs, et la seconde lecture écraserait la première.
        """
        sql = (RACINE / "radar/schema.sql").read_text(encoding="utf-8")
        plat = " ".join(sql.split())
        self.assertIn("UNIQUE (source, ref_source)", plat)


if __name__ == "__main__":
    unittest.main()
