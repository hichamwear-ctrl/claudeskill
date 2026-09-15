"""DÉFAUT 12 — LE TABLEAU PERDAIT 26 OPPORTUNITÉS SUR 27.

Trouvé par un utilisateur en comparant deux écrans du même radar :

    radar suivi      →  NOUVELLE (26)   ·  CONTACT À FAIRE (1)
    radar tableau    →  NOUVELLE  0     ·  jamais regardées 0

Le bloc COMMERCIAL totalisait UNE affaire là où la base en portait 27.

La cause : « jamais regardée » n'est pas `NULL` en base. Le schéma pose le
sentinelle `non_vu` par défaut, et `tableau.py` ne comptait que
`etat IS NULL`. Les 26 ne correspondaient donc ni à ce compteur, ni à aucun
des huit statuts commerciaux : elles tombaient entre les deux.

C'est la MÊME racine que le défaut 8 — le sentinelle `non_vu` mal lu.
`suivi.py` le gérait déjà ; `tableau.py` ne le gérait pas.

Le sentinelle n'a pas été remplacé par NULL pour faire passer le compteur :
son sens ne change pas, c'est le tableau qui apprend à lire ce qui est
réellement stocké.
"""

from __future__ import annotations

import ast
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from radar import tableau                                        # noqa: E402
from radar.base import enregistrer_reponse, maintenant, ouvrir     # noqa: E402
from radar.suivi import NON_VU, Statut                           # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent


def _base_avec(etats: list):
    """Une base neuve portant exactement ces états commerciaux, un par
    opportunité. On écrit l'état BRUT, tel que le schéma le stocke — c'est
    justement la lecture de cet état brut qui était fausse."""
    cx = ouvrir(str(pathlib.Path(tempfile.mkdtemp()) / "t.sqlite3"))
    for n, etat in enumerate(etats, start=1):
        avis = enregistrer_reponse(cx, "essai", f"https://exemple.be/{n}", {})
        cx.execute(
            "INSERT INTO opportunites(avis_id, type, statut, intitule, etat,"
            " calcule_le) VALUES(?,?,?,?,?,?)",
            (avis, "DIRECT", "INCONNUE", f"affaire {n}", etat, maintenant()))
    cx.commit()
    return cx


class A_LeCasExactDeLUtilisateur(unittest.TestCase):
    """26 jamais regardées + 1 CONTACT À FAIRE = 27. Pas 1."""

    ETATS = [NON_VU] * 26 + [Statut.CONTACT_A_FAIRE.value]

    def setUp(self):
        self.cx = _base_avec(self.ETATS)
        self.t = tableau.mesurer(self.cx)

    def test_1_les_jamais_regardees_sont_comptees(self):
        self.assertEqual(self.t.commercial["sans_statut"], 26)

    def test_2_le_statut_pose_par_un_humain_est_compte(self):
        self.assertEqual(self.t.commercial[Statut.CONTACT_A_FAIRE.value], 1)

    def test_3_le_total_est_celui_de_la_base(self):
        self.assertEqual(self.t.commercial["total"], 27)

    def test_4_rien_ne_tombe_entre_deux_compteurs(self):
        """L'invariant qui manquait : la somme des lignes affichées doit
        faire le total. C'est lui qui aurait montré le défaut tout seul."""
        somme = (sum(self.t.commercial[s.value] for s in Statut)
                 + self.t.commercial["sans_statut"])
        self.assertEqual(somme, self.t.commercial["total"])

    def test_5_le_tableau_lisible_affiche_les_deux_nombres(self):
        texte = tableau.rapport(self.cx)
        bloc = texte.split("COMMERCIAL", 1)[1].split("VALEUR", 1)[0]
        self.assertIn("jamais regardées", bloc)
        for attendu in ("26", "27"):
            self.assertIn(attendu, bloc, attendu)


class B_LesAutresStatutsNeCassentPas(unittest.TestCase):
    """Le correctif ne doit pas absorber les statuts réellement posés."""

    ETATS = ([NON_VU] * 3 + [""]
             + [Statut.NOUVELLE.value] * 2
             + [Statut.CONTACT_A_FAIRE.value]
             + [Statut.CONTACTEE.value] * 4
             + [Statut.EN_ATTENTE.value]
             + [Statut.RELANCE.value]
             + [Statut.GAGNEE.value] * 2
             + [Statut.PERDUE.value]
             + [Statut.ABANDONNEE.value])

    def setUp(self):
        self.t = tableau.mesurer(_base_avec(self.ETATS))

    def test_1_chaque_statut_garde_son_compte(self):
        attendus = {
            Statut.NOUVELLE: 2, Statut.CONTACT_A_FAIRE: 1,
            Statut.CONTACTEE: 4, Statut.EN_ATTENTE: 1, Statut.RELANCE: 1,
            Statut.GAGNEE: 2, Statut.PERDUE: 1, Statut.ABANDONNEE: 1,
        }
        for statut, n in attendus.items():
            with self.subTest(statut=statut.value):
                self.assertEqual(self.t.commercial[statut.value], n)

    def test_2_les_formes_dabsence_comptent_ensemble(self):
        """`non_vu` et la chaîne vide disent toutes deux « jamais regardée ».
        C'est le vocabulaire de `suivi.lire()`, pas une invention locale."""
        self.assertEqual(self.t.commercial["sans_statut"], 4)

    def test_3_NOUVELLE_pose_par_un_humain_nest_pas_jamais_regardee(self):
        """La distinction que le correctif NE DOIT PAS effacer : un humain
        qui pose NOUVELLE a regardé l'affaire ; `non_vu` veut dire que
        personne ne l'a jamais ouverte."""
        self.assertEqual(self.t.commercial[Statut.NOUVELLE.value], 2)
        self.assertNotEqual(self.t.commercial[Statut.NOUVELLE.value],
                            self.t.commercial["sans_statut"])

    def test_4_linvariant_tient_aussi_ici(self):
        somme = (sum(self.t.commercial[s.value] for s in Statut)
                 + self.t.commercial["sans_statut"])
        self.assertEqual(somme, self.t.commercial["total"])
        self.assertEqual(somme, len(self.ETATS))


class C_LaCauseNePeutPasRevenir(unittest.TestCase):

    def test_1_aucun_compteur_ne_lit_etat_is_null_tout_seul(self):
        """`WHERE etat IS NULL` seul est incompatible avec le modèle : le
        schéma pose `non_vu`, jamais NULL, sur une opportunité neuve."""
        source = (RACINE / "radar/tableau.py").read_text(encoding="utf-8")
        for n in ast.walk(ast.parse(source)):
            if not isinstance(n, ast.Constant) or not isinstance(n.value, str):
                continue
            if "etat IS NULL" in n.value:
                self.assertIn("etat=?", n.value,
                              "lire NULL sans lire le sentinelle refait "
                              "disparaître les affaires jamais regardées")

    def test_2_le_sentinelle_est_lu_chez_suivi_jamais_recopie(self):
        """Deux définitions de « jamais regardée » finiraient par diverger —
        c'est exactement comme cela que le défaut est né."""
        source = (RACINE / "radar/tableau.py").read_text(encoding="utf-8")
        litteraux = [n.value for n in ast.walk(ast.parse(source))
                     if isinstance(n, ast.Constant)
                     and isinstance(n.value, str)]
        self.assertNotIn(NON_VU, litteraux,
                         f"« {NON_VU} » est recopié en dur au lieu d'être "
                         "importé de radar.suivi")

    def test_3_une_base_neuve_pose_bien_le_sentinelle(self):
        """La prémisse du correctif, vérifiée plutôt que supposée."""
        cx = _base_avec([NON_VU])
        avis = enregistrer_reponse(cx, "essai", "https://exemple.be/defaut", {})
        cx.execute("INSERT INTO opportunites(avis_id, type, statut, intitule,"
                   " calcule_le) VALUES(?,?,?,?,?)",
                   (avis, "DIRECT", "INCONNUE", "sans etat", maintenant()))
        cx.commit()
        pose = cx.execute(
            "SELECT etat FROM opportunites WHERE avis_id=?", (avis,)
        ).fetchone()["etat"]
        self.assertEqual(pose, NON_VU, "le schéma pose le sentinelle, pas NULL")
        self.assertEqual(tableau.mesurer(cx).commercial["sans_statut"], 2)

    def test_4_la_colonne_ne_peut_meme_pas_etre_NULL(self):
        """Ce qui aggrave le défaut, et qu'il faut consigner : la colonne est
        `NOT NULL DEFAULT 'non_vu'`. `WHERE etat IS NULL` ne pouvait donc
        JAMAIS rien trouver — le compteur « jamais regardées » valait 0 sur
        toute base, depuis le jour où il a été écrit."""
        cx = _base_avec([NON_VU])
        colonne = next(l for l in cx.execute("PRAGMA table_info(opportunites)")
                       if l["name"] == "etat")
        self.assertEqual(colonne["notnull"], 1)
        self.assertEqual(colonne["dflt_value"], f"'{NON_VU}'")
        self.assertEqual(
            cx.execute("SELECT count(*) FROM opportunites"
                       " WHERE etat IS NULL").fetchone()[0], 0,
            "l'ancienne requête ne pouvait structurellement rien compter")


if __name__ == "__main__":
    unittest.main()
