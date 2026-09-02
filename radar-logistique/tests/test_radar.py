"""Tests de COMPORTEMENT — un par règle du cahier des charges.

Aucun ne vérifie qu'une ligne de code existe. Chacun pose une question dont la
réponse coûte un contrat si elle est fausse.
"""

import json
import sqlite3
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from radar import eligibilite as eli, envoi, memoire, statut as st
from radar.activite import Ontologie
from radar.adaptateur import Adaptateur, vers_opportunite
from radar.base import ouvrir
from radar.chaine import Moteur, traiter
from radar.deduplication import empreinte
from radar.geographie import Geographie, Zone
from radar.modele import Nature, Opportunite
from radar.sondage import sonder

MAINTENANT = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)


def cfg(nom):
    return yaml.safe_load((RACINE / nom).read_text(encoding="utf-8"))


PROFIL = cfg("profil.yaml")
CAPACITES = cfg("config/capacites.yaml")
GEO = cfg("config/geographie.yaml")
PONDERATIONS = cfg("config/ponderations.yaml")
EXIGENCES = CAPACITES["exigences"]


def moteur():
    return Moteur(PROFIL, CAPACITES, GEO, PONDERATIONS)


def opp(**kw):
    base = dict(source="ted", ref_source="R1", intitule="Marché", texte="",
                type_avis="appel-offres", pays_livraison=["BE"])
    base.update(kw)
    return Opportunite(**base)


# ------------------------------------------------- §5 : vocabulaire de l'acheteur --
class VocabulaireDeLAcheteur(unittest.TestCase):
    def setUp(self):
        self.o = Ontologie(CAPACITES, PROFIL["familles_actives"], PROFIL["familles_exclues"])

    def test_distribution_urbaine_est_reconnue_comme_dernier_kilometre(self):
        """L'acheteur ne dit pas « dernier kilomètre »."""
        r = self.o.analyser("Distribution urbaine de marchandises en Région bruxelloise")
        self.assertIn("dernier_kilometre", r.familles)

    def test_le_neerlandais_est_reconnu(self):
        r = self.o.analyser("Stadsdistributie en pakketlevering voor de stad")
        self.assertIn("dernier_kilometre", r.familles)

    def test_l_anglais_est_reconnu(self):
        r = self.o.analyser("Last mile parcel delivery services")
        self.assertIn("dernier_kilometre", r.familles)

    def test_une_activite_hors_metier_est_exclue(self):
        r = self.o.analyser("Transport de matières dangereuses ADR")
        self.assertFalse(r.correspond)

    def test_le_cpv_seul_suffit_a_reconnaitre_une_famille(self):
        r = self.o.analyser("Intitulé sans vocabulaire utile", cpv=["64120000"])
        self.assertIn("dernier_kilometre", r.familles)


# ------------------------------------------------------------ §4 : géographie --
class LogiqueDeCorridor(unittest.TestCase):
    def setUp(self):
        self.g = Geographie(GEO)

    def test_collecte_nl_livraison_be_est_le_coeur_du_modele(self):
        r = self.g.evaluer(["NL"], ["BE"])
        self.assertIs(r.zone, Zone.CORRIDOR)
        self.assertTrue(r.corridor_eprouve, "le corridor NL→BE a déjà été exécuté")

    def test_deux_villes_francaises_sont_hors_zone(self):
        r = self.g.evaluer(["FR"], ["FR"])
        self.assertIs(r.zone, Zone.HORS_ZONE)
        self.assertFalse(r.compatible)

    def test_collecte_europeenne_lointaine_reste_dans_le_modele(self):
        """Je peux aller chercher partout en Europe."""
        self.assertIs(self.g.evaluer(["PL"], ["BE"]).zone, Zone.CORRIDOR)

    def test_lieu_absent_ne_fait_pas_disparaitre_l_opportunite(self):
        r = self.g.evaluer([], [])
        self.assertIs(r.zone, Zone.A_VERIFIER)
        self.assertTrue(r.compatible)


# ------------------------------------------------------- §9 : dates, §7 statut --
class StatutEtDates(unittest.TestCase):
    def test_marche_ouvert_est_postulable(self):
        v = st.evaluer(opp(echeance_brute="2026-10-15T11:00:00+02:00"), maintenant=MAINTENANT)
        self.assertIs(v.statut, st.Statut.POSTULABLE)

    def test_date_depassee_est_non_postulable(self):
        v = st.evaluer(opp(echeance_brute="2026-08-01T11:00:00+02:00"), maintenant=MAINTENANT)
        self.assertIs(v.statut, st.Statut.NON_POSTULABLE)

    def test_attribution_reste_fermee_meme_avec_date_future(self):
        v = st.evaluer(opp(type_avis="attribution", echeance_brute="2027-01-01T11:00:00+01:00"),
                       maintenant=MAINTENANT)
        self.assertIs(v.statut, st.Statut.NON_POSTULABLE)

    def test_date_absente_donne_a_verifier_jamais_postulable(self):
        v = st.evaluer(opp(echeance_brute=None), maintenant=MAINTENANT)
        self.assertIs(v.statut, st.Statut.A_VERIFIER)

    def test_date_illisible_donne_a_verifier_jamais_non_postulable(self):
        v = st.evaluer(opp(echeance_brute="prochainement"), maintenant=MAINTENANT)
        self.assertIs(v.statut, st.Statut.A_VERIFIER)
        self.assertTrue(v.statut.notifiable)

    def test_dates_contradictoires_donnent_a_verifier(self):
        v = st.evaluer(opp(echeance_brute="2026-10-01T11:00:00+02:00",
                           publie_le="2026-11-01T11:00:00+01:00"), maintenant=MAINTENANT)
        self.assertIs(v.statut, st.Statut.A_VERIFIER)

    def test_aucune_date_n_est_jamais_inventee(self):
        self.assertIsNone(st.parse_date("n'importe quoi")[0])
        self.assertIsNone(st.parse_date(None)[0])

    def test_zone_incompatible_rend_non_postulable(self):
        v = st.evaluer(opp(echeance_brute="2026-10-15T11:00:00+02:00"),
                       zone_compatible=False, zone_raison="hors modèle", maintenant=MAINTENANT)
        self.assertIs(v.statut, st.Statut.NON_POSTULABLE)


# --------------------------------------------------------- §10 : éligibilité --
class Eligibilite(unittest.TestCase):
    def ev(self, exigences):
        return eli.evaluer(exigences, PROFIL, EXIGENCES)

    def test_exigence_structuree_impossible_bloque(self):
        r = self.ev([eli.Exigence("surface_min_m2", 2500, structuree=True)])
        self.assertIs(r.statut, eli.Statut.NON_ELIGIBLE)

    def test_la_meme_exigence_en_texte_libre_ne_bloque_pas(self):
        r = self.ev([eli.Exigence("surface_min_m2", 2500, structuree=False)])
        self.assertIs(r.statut, eli.Statut.A_VERIFIER)

    def test_a_verifier_dans_le_profil_ne_vaut_jamais_non_eligible(self):
        """froid_positif vaut A_VERIFIER : ne pas savoir n'est pas ne pas pouvoir."""
        r = self.ev([eli.Exigence("froid")])
        self.assertIs(r.statut, eli.Statut.A_VERIFIER)

    def test_certification_pharma_jamais_supposee_acquise(self):
        r = self.ev([eli.Exigence("gdp")])
        self.assertIs(r.statut, eli.Statut.A_VERIFIER)
        self.assertTrue(any("GDP" in v for v in r.a_verifier))

    def test_capacite_actuelle_n_est_pas_capacite_maximale(self):
        """6 véhicules en propre, 20 mobilisables : 12 exigés n'est pas un blocage."""
        r = self.ev([eli.Exigence("vehicules_min", 12)])
        self.assertIs(r.statut, eli.Statut.A_VERIFIER)
        self.assertFalse(r.bloquants)

    def test_au_dela_du_maximum_mobilisable_bloque(self):
        r = self.ev([eli.Exigence("vehicules_min", 40)])
        self.assertIs(r.statut, eli.Statut.NON_ELIGIBLE)

    def test_anciennete_insuffisante_ne_bloque_pas_seule(self):
        """1 an d'existence contre 3 exigés : souvent contournable par références."""
        r = self.ev([eli.Exigence("anciennete_min_annees", 3)])
        self.assertIs(r.statut, eli.Statut.A_VERIFIER)

    def test_tout_couvert_donne_eligible(self):
        r = self.ev([eli.Exigence("afsca"), eli.Exigence("licence")])
        self.assertIs(r.statut, eli.Statut.ELIGIBLE)


# ------------------------------------------------------------- §11 : score --
class Score(unittest.TestCase):
    def test_le_score_ne_fait_jamais_disparaitre_une_opportunite(self):
        cx = ouvrir(":memory:")
        faible = opp(ref_source="FAIBLE", intitule="Transport routier de marchandises",
                     texte="transport routier", echeance_brute="2026-09-04T11:00:00+02:00")
        b = traiter(cx, moteur(), [faible], maintenant_dt=MAINTENANT)
        self.assertEqual(b.notifies, 1, "un score faible ne supprime pas la notification")
        ligne = cx.execute("SELECT score FROM opportunites").fetchone()
        self.assertLess(ligne["score"], 100)

    def test_chaque_point_est_justifie(self):
        m = moteur()
        o = opp(intitule="Distribution urbaine", texte="distribution urbaine de marchandises",
                pays_collecte=["NL"], pays_livraison=["BE"], montant=250000, duree_mois=36,
                echeance_brute="2026-10-15T11:00:00+02:00")
        _, _, note, _, _, _ = m.analyser(o, MAINTENANT)
        self.assertTrue(note.lignes)
        for l in note.lignes:
            self.assertTrue(l.raison, f"le critère « {l.critere} » n'explique pas ses points")

    def test_les_ponderations_viennent_de_la_configuration(self):
        modifiee = json.loads(json.dumps(PONDERATIONS))
        modifiee["criteres"]["activite"] = 0
        m1, m2 = moteur(), Moteur(PROFIL, CAPACITES, GEO, modifiee)
        o = opp(intitule="Distribution urbaine de marchandises",
                texte="distribution urbaine", echeance_brute="2026-10-15T11:00:00+02:00")
        s1 = m1.analyser(o, MAINTENANT)[2].total
        s2 = m2.analyser(o, MAINTENANT)[2].total
        self.assertGreater(s1, s2, "changer une pondération doit changer le score")

    def test_un_signal_est_pondere_sous_une_opportunite_directe(self):
        m = moteur()
        commun = dict(intitule="Distribution urbaine de marchandises",
                      texte="distribution urbaine", pays_livraison=["BE"],
                      echeance_brute="2026-10-15T11:00:00+02:00")
        direct = m.analyser(opp(**commun), MAINTENANT)[2].total
        signal = m.analyser(opp(nature=Nature.SIGNAL_COMMERCIAL, **commun), MAINTENANT)[2].total
        self.assertLess(signal, direct)


# ------------------------------------------------------- §8 : attributions --
class MemoireDesAttributions(unittest.TestCase):
    def test_une_attribution_n_est_jamais_notifiee(self):
        cx = ouvrir(":memory:")
        a = opp(ref_source="ATTR", type_avis="attribution", attribue=True,
                intitule="Distribution urbaine", texte="distribution urbaine",
                montant=2400000, duree_mois=36, attribue_le="2026-09-01")
        traiter(cx, moteur(), [a], maintenant_dt=MAINTENANT)
        self.assertEqual(cx.execute("SELECT count(*) c FROM envois").fetchone()["c"], 0)

    def test_mais_elle_est_conservee_en_memoire(self):
        cx = ouvrir(":memory:")
        a = opp(ref_source="ATTR", type_avis="attribution", attribue=True,
                intitule="Distribution urbaine", texte="distribution urbaine",
                montant=2400000, duree_mois=36, attribue_le="2026-09-01")
        traiter(cx, moteur(), [a], maintenant_dt=MAINTENANT)
        l = cx.execute("SELECT * FROM attributions").fetchone()
        self.assertEqual(l["fiabilite"], "calculée")
        self.assertTrue(l["renouvellement"].startswith("2029"),
                        "36 mois après septembre 2026 → 2029")

    def test_sans_duree_l_echeance_n_est_pas_inventee(self):
        r = memoire.memoriser(opp(attribue=True, attribue_le="2026-09-01", duree_mois=None))
        self.assertIsNone(r.remise_en_concurrence)
        self.assertEqual(r.fiabilite, "A_VERIFIER")


# ------------------------------------------------------ §15 : déduplication --
class Deduplication(unittest.TestCase):
    def test_le_meme_marche_vu_sur_deux_sources_ne_compte_qu_une_fois(self):
        a = opp(source="ted", ref_source="T1", acheteur="CHU", intitule="Distribution urbaine",
                texte="distribution urbaine", echeance_brute="2026-10-15T11:00:00+02:00")
        b = opp(source="bda", ref_source="B1", acheteur="CHU", intitule="Distribution urbaine",
                texte="distribution urbaine", echeance_brute="2026-10-15T11:00:00+02:00")
        self.assertEqual(empreinte(a), empreinte(b))
        cx = ouvrir(":memory:")
        bilan = traiter(cx, moteur(), [a, b], maintenant_dt=MAINTENANT)
        self.assertEqual(bilan.doublons, 1)
        self.assertEqual(cx.execute("SELECT count(*) c FROM envois").fetchone()["c"], 1)


# ---------------------------------------------------------- §12 : la fiche --
class Fiche(unittest.TestCase):
    def setUp(self):
        self.cx = ouvrir(":memory:")
        o = opp(ref_source="F1", intitule="Livraison dernier kilomètre",
                texte="distribution urbaine de marchandises et livraison à domicile",
                acheteur="Grand distributeur", secteur_acheteur="privé",
                pays_collecte=["NL"], pays_livraison=["BE"], montant=250000, duree_mois=36,
                echeance_brute="2026-10-15T11:00:00+02:00",
                plateforme="https://exemple.be/depot/F1")
        traiter(self.cx, moteur(), [o], maintenant_dt=MAINTENANT)
        self.corps = self.cx.execute("SELECT corps FROM envois").fetchone()["corps"]

    def test_la_fiche_porte_tous_les_champs_demandes(self):
        for attendu in ("Acheteur", "Date limite", "Valeur estimée",
                        "Pourquoi c'est intéressant pour moi", "Score", "Action"):
            self.assertIn(attendu, self.corps)

    def test_la_fiche_montre_le_corridor(self):
        self.assertIn("Collecte", self.corps)
        self.assertIn("NL", self.corps)

    def test_un_montant_absent_n_est_jamais_invente(self):
        cx = ouvrir(":memory:")
        traiter(cx, moteur(), [opp(ref_source="SANS", intitule="Distribution urbaine",
                                   texte="distribution urbaine", montant=None,
                                   echeance_brute="2026-10-15T11:00:00+02:00")],
                maintenant_dt=MAINTENANT)
        corps = cx.execute("SELECT corps FROM envois").fetchone()["corps"]
        self.assertIn("NON PUBLIÉ", corps)
        self.assertNotIn("0 EUR", corps)


# ------------------------------------------------------------ §7 : livraison --
class CeQuiEstNotifie(unittest.TestCase):
    LOT = None

    def setUp(self):
        self.cx = ouvrir(":memory:")
        commun = dict(texte="distribution urbaine de marchandises", pays_livraison=["BE"])
        lot = [
            opp(ref_source="VERT", intitule="Distribution urbaine BE",
                echeance_brute="2026-10-15T11:00:00+02:00", **commun),
            opp(ref_source="ORANGE", intitule="Distribution urbaine sans date",
                echeance_brute=None, **commun),
            opp(ref_source="ROUGE-DATE", intitule="Distribution urbaine passée",
                echeance_brute="2026-08-01T11:00:00+02:00", **commun),
            opp(ref_source="ROUGE-ZONE", intitule="Distribution urbaine Lyon Marseille",
                texte="distribution urbaine de marchandises", pays_collecte=["FR"],
                pays_livraison=["FR"], echeance_brute="2026-10-15T11:00:00+02:00"),
            opp(ref_source="ROUGE-METIER", intitule="Transport de matières dangereuses",
                texte="transport de matieres dangereuses ADR", pays_livraison=["BE"],
                echeance_brute="2026-10-15T11:00:00+02:00"),
            opp(ref_source="ROUGE-CAPA", intitule="Distribution urbaine grosse plateforme",
                exigences={"surface_min_m2": 4000},
                echeance_brute="2026-10-15T11:00:00+02:00", **commun),
        ]
        self.bilan = traiter(self.cx, moteur(), lot, maintenant_dt=MAINTENANT)

    def _notifies(self):
        return {l["ref_source"] for l in self.cx.execute("SELECT ref_source FROM envois")}

    def test_seuls_le_vert_et_l_orange_sont_notifies(self):
        self.assertEqual(self._notifies(), {"VERT", "ORANGE"})

    def test_aucun_rouge_n_est_notifie(self):
        for ref in ("ROUGE-DATE", "ROUGE-ZONE", "ROUGE-METIER", "ROUGE-CAPA"):
            self.assertNotIn(ref, self._notifies())

    def test_les_rouges_restent_traces_en_base(self):
        n = self.cx.execute(
            "SELECT count(*) c FROM opportunites WHERE statut='NON_POSTULABLE'").fetchone()["c"]
        self.assertEqual(n, 4)

    def test_le_bilan_dit_pourquoi_chaque_rejet(self):
        self.assertEqual(self.bilan.non_postulables, 4)
        self.assertTrue(self.bilan.motifs_rejet)


# -------------------------------------------------------------- §16 : sondage --
class SondageDuMarche(unittest.TestCase):
    def test_le_sondage_refuse_de_publier_des_pourcentages_sur_trop_peu(self):
        s = sonder(moteur(), [opp(intitule="Distribution urbaine", texte="distribution urbaine")],
                   "ted", MAINTENANT)
        self.assertIn("échantillon trop petit", s.rapport())

    def test_une_grandeur_non_observable_sort_en_non_mesure(self):
        s = sonder(moteur(), [opp(montant=None, intitule="X", texte="")], "ted", MAINTENANT)
        self.assertIn("NON MESURÉ", s.rapport())


# ---------------------------------------------------------- garanties d'envoi --
class FileDEnvoi(unittest.TestCase):
    def setUp(self):
        self.cx = ouvrir(":memory:")

    def test_une_opportunite_ne_part_pas_deux_fois(self):
        self.assertTrue(envoi.mettre_en_file(self.cx, "ted", "R1", "corps"))
        self.assertFalse(envoi.mettre_en_file(self.cx, "ted", "R1", "corps"))

    def test_envoi_interrompu_devient_ambigu_et_n_est_pas_reemis(self):
        envoi.mettre_en_file(self.cx, "ted", "R1", "corps")
        self.cx.execute("UPDATE envois SET etat='en_cours'")
        self.assertEqual(envoi.reprendre_interrompus(self.cx), 1)
        self.assertEqual(len(envoi.a_envoyer(self.cx)), 0)


class OutilDeLecture(unittest.TestCase):
    def test_un_outil_de_lecture_est_incapable_d_ecrire(self):
        chemin = RACINE / "tests" / "_tmp.sqlite3"
        chemin.unlink(missing_ok=True)
        ouvrir(chemin).close()
        cx = ouvrir(chemin, lecture_seule=True)
        with self.assertRaises(sqlite3.OperationalError):
            cx.execute("INSERT INTO avis(source, ref_source, empreinte, premiere_vue, "
                       "derniere_vue) VALUES('x','y','z','t','t')")
        cx.close(); chemin.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
