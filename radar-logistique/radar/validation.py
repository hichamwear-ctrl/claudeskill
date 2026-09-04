"""ÉTAT DE VALIDATION — ce qui est prouvé, et par quoi.

Un nombre de tests n'est pas une validation commerciale. 400 tests écrits par
moi contre des fixtures écrites par moi mesurent la cohérence interne du
moteur : ils ne disent rien de ce que le moteur comprendra d'une vraie page.

D'où DEUX compteurs, qui ne se mélangent jamais :

    TESTS DE COHÉRENCE        combien de comportements sont verrouillés contre
                              des données FABRIQUÉES. Protège des régressions.
                              Ne prouve aucune capacité réelle.

    COMPORTEMENTS OBSERVÉS    combien de fois le moteur a été confronté à une
    SUR DONNÉES RÉELLES       donnée qu'il n'a pas fabriquée. Seul compteur qui
                              autorise à parler de capacité réelle.

Le second ne peut pas être écrit à la main : il se lit dans le registre de
mesures, alimenté par le seul outil qui collecte pour de vrai. Une phrase de
documentation ne peut donc pas le faire monter.

Et la formule qui borne ce que le produit a le droit d'affirmer :

    le radar détecte des opportunités provenant de DIFFÉRENTES FAMILLES DE
    SOURCES PRÉVUES PAR L'ARCHITECTURE — pas « de n'importe quelle source »,
    tant que ces familles n'ont pas été mesurées sur du réel.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
REGISTRE = RACINE / "validation" / "mesures_reelles.json"

FORMULE_AUTORISEE = ("des opportunités provenant de différentes familles de "
                     "sources prévues par l'architecture")
FORMULE_INTERDITE = "de n'importe quelle source"

# ═══ LES HUIT FAMILLES DE SOURCES PRÉVUES PAR L'ARCHITECTURE ═══
#
# Le plan de mesure s'organise autour d'elles, et AUCUNE n'est la principale.
# Le premier flux réellement disponible ne doit pas devenir « la source » : ce
# serait refaire, avec un autre nom, l'obsession qu'on a mis des mois à défaire.
#
# Chacune alimente le MÊME pipeline :
#   SOURCE → COLLECTE → PREUVE → EXTRACTION → NORMALISATION → NATURE
#          → ÉTAT (si applicable) → CAPACITÉ → ÉCONOMIE → SCORE → ACTION
#          → FIL DE VIE
# et aucune étape métier n'a le droit de demander « est-ce TED ? ».
FAMILLES_PREVUES = [
    ("A", "entreprise",    "entreprise privée exprimant un besoin"),
    ("B", "bourse_fret",   "bourse de fret"),
    ("C", "recherche",     "moteur de recherche"),
    ("D", "marche_public", "portail de marchés publics"),
    ("E", "attribution",   "attribution de marché"),
    ("F", "signal",        "signal économique"),
    ("G", "renouvellement", "renouvellement de contrat"),
    ("H", "partenariat",   "partenariat / sous-traitance"),
]

# LES DEUX DIMENSIONS, QUI NE SE CONFONDENT JAMAIS.
#
# Une page réelle sans besoin — la page PyPI mesurée le 4/9/2026 — prouve
# UNIQUEMENT que le système sait rencontrer une vraie page sans inventer un
# besoin. Ce n'est pas une validation commerciale, et elle ne doit plus jamais
# être présentée comme telle.
DONNEE_OBSERVEE = "DONNÉE RÉELLE OBSERVÉE"
OPPORTUNITE_TESTEE = "OPPORTUNITÉ COMMERCIALE TESTÉE"


@dataclass
class Mesure:
    """Une confrontation à une donnée non fabriquée."""
    horodatage: str
    famille: str            # entreprise, recherche, marche_public, bourse_fret…
    origine: str            # comment la donnée a été obtenue, exactement
    reference: str          # URL ou identifiant réel
    empreinte: str
    page_conservee: str = ""
    completude: str = ""    # ex. « page complète » ou « extrait de listing »
    ca_identifie: float = 0.0       # €/mois réellement identifiés sur cette mesure
    verdict: str = ""       # ce que le radar a conclu de cette page
    porte_un_besoin: bool = False   # la page contenait-elle une opportunité ?
    constats: dict = field(default_factory=dict)   # niveau -> nombre
    enseignements: list = field(default_factory=list)

    @classmethod
    def de_dict(cls, d: dict) -> "Mesure":
        connus = {c: d.get(c) for c in cls.__dataclass_fields__ if c in d}
        connus.setdefault("horodatage", "")
        connus.setdefault("famille", "INCONNUE")
        connus.setdefault("origine", "INCONNUE")
        connus.setdefault("reference", "")
        connus.setdefault("empreinte", "")
        return cls(**connus)


def lire_registre(chemin: Path | None = None) -> list[Mesure]:
    fichier = Path(chemin) if chemin else REGISTRE
    if not fichier.exists():
        return []
    try:
        brut = json.loads(fichier.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [Mesure.de_dict(d) for d in brut.get("mesures", []) if isinstance(d, dict)]


def inscrire(mesure: Mesure, chemin: Path | None = None) -> None:
    """Le SEUL chemin d'écriture du compteur réel. Appelé par un collecteur."""
    fichier = Path(chemin) if chemin else REGISTRE
    fichier.parent.mkdir(parents=True, exist_ok=True)
    existantes = []
    if fichier.exists():
        try:
            existantes = json.loads(fichier.read_text(encoding="utf-8")).get("mesures", [])
        except (json.JSONDecodeError, OSError):
            existantes = []
    # Une même empreinte relue n'est pas une seconde mesure.
    if any(m.get("empreinte") == mesure.empreinte for m in existantes if isinstance(m, dict)):
        return
    existantes.append(mesure.__dict__)
    fichier.write_text(json.dumps(
        {"avertissement": "Écrit UNIQUEMENT par un collecteur réel. "
                          "Ne pas remplir à la main.",
         "mesures": existantes}, ensure_ascii=False, indent=2), encoding="utf-8")


def compter_tests(racine: Path | None = None) -> int:
    """Compte les méthodes de test. C'est un compteur de COHÉRENCE."""
    import ast
    base = Path(racine) if racine else RACINE / "tests"
    total = 0
    for fichier in sorted(base.glob("test_*.py")):
        try:
            arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for noeud in ast.walk(arbre):
            if isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and noeud.name.startswith("test"):
                total += 1
    return total


@dataclass
class Etat:
    tests_coherence: int
    mesures: list

    @property
    def familles_mesurees(self) -> list[str]:
        return sorted({m.famille for m in self.mesures})

    @property
    def pages_completes(self) -> int:
        return sum(1 for m in self.mesures if m.completude == "page complète")

    @property
    def pages_portant_un_besoin(self) -> int:
        """Une page réelle SANS besoin éprouve l'extraction et le tri ; elle
        n'éprouve ni le score, ni les capacités, ni l'action commerciale."""
        return sum(1 for m in self.mesures if m.porte_un_besoin)

    # ── LES DEUX DIMENSIONS, SÉPARÉES ────────────────────────────────────
    def donnees_observees(self) -> int:
        """Dimension 1 : combien de fois une donnée non fabriquée est entrée."""
        return len(self.mesures)

    def opportunites_testees(self) -> int:
        """Dimension 2 : combien portaient réellement un besoin économique.

        Ne se déduit JAMAIS de la première. Une page réelle peut être une
        information générale, un ancien contrat, une entreprise sans besoin.
        """
        return self.pages_portant_un_besoin

    @property
    def hors_plan(self) -> list:
        """Mesures qui n'appartiennent à AUCUNE des huit familles.

        Elles comptent comme DONNÉE RÉELLE OBSERVÉE — elles éprouvent la
        chaîne — et jamais comme couverture d'une famille commerciale. La page
        PyPI est de celles-là : réelle, et hors sujet.
        """
        connues = {cle for _, cle, _ in FAMILLES_PREVUES}
        return [m for m in self.mesures if m.famille not in connues]

    def plan_de_mesure(self) -> list:
        """L'état de chacune des huit familles. Aucune n'est la principale."""
        par_famille = {}
        for m in self.mesures:
            par_famille.setdefault(m.famille, []).append(m)
        plan = []
        for lettre, cle, libelle in FAMILLES_PREVUES:
            faites = par_famille.get(cle, [])
            avec_besoin = [m for m in faites if m.porte_un_besoin]
            if avec_besoin:
                etat, marque = "OPPORTUNITÉ COMMERCIALE TESTÉE", "✓"
            elif faites:
                etat, marque = "donnée observée, opportunité NON TESTÉE", "~"
            else:
                etat, marque = "NON MESURÉE", "✗"
            plan.append((lettre, cle, libelle, marque, etat, len(faites)))
        return plan

    def tableau_des_familles(self) -> str:
        """Le tableau des huit. ZÉRO N'EST PAS « NON MESURÉ ».

        « 0 opportunité » veut dire : on a regardé, il n'y avait rien.
        « NON MESURÉ » veut dire : on n'a pas regardé. Confondre les deux fait
        croire qu'une famille a été explorée et qu'elle est stérile, alors que
        personne n'y est jamais allé. C'est la porte d'entrée pour abandonner
        une famille sans l'avoir ouverte.
        """
        L = ["  {:<30} {:>8} {:>14} {:>12}   {}".format(
            "FAMILLE", "DONNÉES", "OPPORTUNITÉS", "CA €/mois", "MESURE")]
        L.append("  " + "─" * 84)
        par_famille = {}
        for m in self.mesures:
            par_famille.setdefault(m.famille, []).append(m)
        for lettre, cle, libelle in FAMILLES_PREVUES:
            faites = par_famille.get(cle, [])
            if not faites:
                # Jamais observée : tout est NON MESURÉ, pas zéro.
                L.append("  {:<30} {:>8} {:>14} {:>12}   {}".format(
                    f"{lettre}. {libelle}"[:30], "—", "—", "—", "NON MESURÉE"))
                continue
            opportunites = sum(1 for m in faites if m.porte_un_besoin)
            ca = sum(m.ca_identifie for m in faites)
            L.append("  {:<30} {:>8} {:>14} {:>12}   {}".format(
                f"{lettre}. {libelle}"[:30], len(faites), opportunites,
                f"{ca:,.0f}".replace(",", " ") if ca else "0",
                "MESURÉE" if opportunites else "observée, sans opportunité"))
        L.append("  " + "─" * 84)
        L.append("  « — » = NON MESURÉ : personne n'y est allé.")
        L.append("  « 0 »  = on a regardé, il n'y avait rien. Ce n'est pas la même chose.")
        return "\n".join(L)

    def ca_identifie(self) -> float:
        return sum(m.ca_identifie for m in self.mesures)

    def bulletin(self) -> str:
        """LE STATUT COMMERCIAL DU PROJET — la première chose à lire.

        Pas « combien de tests ». Ce que le radar a réellement trouvé.
        """
        L = []
        A = L.append
        reel = self.opportunites_testees()
        A("╔" + "═" * 68 + "╗")
        A("║  " + "RADAR COMMERCIAL — STATUT RÉEL".ljust(66) + "║")
        A("╚" + "═" * 68 + "╝")
        A("")
        A(f"  DONNÉES RÉELLES OBSERVÉES        : {self.donnees_observees()}")
        A(f"  OPPORTUNITÉS RÉELLES             : {reel}")
        A(f"  CA POTENTIEL IDENTIFIÉ           : "
          f"{self.ca_identifie():,.0f} €/mois".replace(",", " "))
        A("")
        if not reel:
            A("  ─────────────────────────────────────────────────────────────")
            A("  MESURE COMMERCIALE : NON DISPONIBLE")
            A("  ─────────────────────────────────────────────────────────────")
            A("  Aucune donnée réelle portant un besoin n'est encore entrée.")
            A("  Le radar n'est PAS validé commercialement. Les tests de")
            A("  cohérence ne changent rien à cette ligne, et ne le doivent pas.")
            A("")
        A("  COUVERTURE DES HUIT FAMILLES")
        A("")
        A(self.tableau_des_familles())
        return "\n".join(L)

    def prochaine_mesure(self) -> str:
        """Ce que la prochaine mesure doit lever, en une phrase.

        Elle vise TOUJOURS une famille non couverte, jamais une seconde page
        de celle déjà mesurée : c'est ainsi qu'une source devient « la source
        principale » sans que personne ne l'ait décidé.
        """
        plan = self.plan_de_mesure()
        jamais = [(l, lib) for l, _, lib, _, etat, _ in plan if etat == "NON MESURÉE"]
        sans_besoin = [(l, lib) for l, _, lib, _, etat, _ in plan
                       if etat.startswith("donnée observée")]
        if jamais:
            liste = " · ".join(f"{l}. {lib}" for l, lib in jamais[:3])
            return (f"une donnée réelle PORTANT UN BESOIN, dans une famille encore "
                    f"jamais mesurée. {len(jamais)} des huit sont à zéro — "
                    f"au choix : {liste}.")
        if sans_besoin:
            l, lib = sans_besoin[0]
            return (f"une donnée de la famille {l}. {lib} qui porte un besoin : "
                    "cette famille a été rencontrée, mais jamais avec une "
                    "opportunité commerciale dedans.")
        return "une seconde par famille, pour distinguer l'accident de la règle."

    def rendu(self) -> str:
        L = []
        A = L.append
        titre = "RADAR COMMERCIAL — ÉTAT DE VALIDATION"
        A("╔" + "═" * 68 + "╗")
        A("║  " + titre.ljust(66) + "║")
        A("╚" + "═" * 68 + "╝")
        A("")
        A("Ce que le produit a le droit d'affirmer aujourd'hui :")
        phrase = (f"« Le radar détecte {FORMULE_AUTORISEE}, les qualifie "
                  "économiquement, distingue les faits des signaux et des "
                  "hypothèses, puis indique comment les attaquer, les "
                  "développer, les surveiller ou les convertir. »")
        for ligne in _plier(phrase, 66):
            A("  " + ligne)
        A("")
        A(f"Ce qu'il n'a PAS le droit d'affirmer : « {FORMULE_INTERDITE} ».")
        A("Une famille prévue par l'architecture n'est pas une famille validée.")
        A("")
        A("─" * 70)
        A("  ARCHITECTURE                                                    ✓")
        A("─" * 70)
        A("  Quatre dimensions séparées (type · état · nature · action),")
        A("  score aveugle à la source, aucun capteur indispensable.")
        A(f"  TESTS DE COHÉRENCE : {self.tests_coherence}")
        A("  ⚠ Ces tests protègent des régressions sur des données FABRIQUÉES.")
        A("    Ils ne mesurent AUCUNE capacité sur le monde réel.")
        A("")
        A("─" * 70)
        A("  FIXTURES                                                        ⚠")
        A("─" * 70)
        A("  Douze familles de besoin traversent le même moteur. Toutes ont été")
        A("  écrites par le développeur : elles décrivent ce qu'il a SU prévoir.")
        A("")
        A("─" * 70)
        # ✓ exige une page réelle qui PORTE UN BESOIN. Une page réelle sans
        # besoin prouve que la chaîne tient debout et sait dire non ; elle ne
        # prouve rien de la qualification commerciale.
        etat_reel = ("✓" if self.pages_portant_un_besoin
                     else ("~" if self.mesures else "✗"))
        A(f"  RÉEL                                                            {etat_reel}")
        A("─" * 70)
        A("  DEUX DIMENSIONS, JAMAIS CONFONDUES :")
        A(f"    {DONNEE_OBSERVEE:<34} : {self.donnees_observees()}")
        A(f"    {OPPORTUNITE_TESTEE:<34} : {self.opportunites_testees()}")
        A("    Une page réelle sans besoin prouve que le radar sait rencontrer")
        A("    le monde sans inventer une affaire. Elle ne prouve RIEN de sa")
        A("    capacité commerciale : la seconde ligne seule en parle.")
        A("")
        A("  PLAN DE MESURE — huit familles, aucune n'est la principale")
        for lettre, _, libelle, marque, etat, n in self.plan_de_mesure():
            suffixe = f" ({n} mesure{'s' if n > 1 else ''})" if n else ""
            A(f"    {marque} {lettre}. {libelle:<44} {etat}{suffixe}")
        couvertes = sum(1 for *_, etat, _ in self.plan_de_mesure()
                        if etat == "OPPORTUNITÉ COMMERCIALE TESTÉE")
        A(f"    → {couvertes}/8 familles ont vu une opportunité réelle.")
        A("")
        if self.hors_plan:
            A("  MESURES HORS PLAN — réelles, mais d'aucune des huit familles")
            for m in self.hors_plan:
                A(f"    · {m.famille} — {m.reference[:52]}")
            A("    Elles éprouvent la chaîne. Elles ne couvrent aucune famille.")
            A("")
        if not self.mesures:
            A("  Aucune donnée non fabriquée n'est encore entrée dans la chaîne.")
        else:
            A("  MESURES INSCRITES")
            for m in self.mesures:
                A(f"   · {m.horodatage[:10]}  {m.famille:<14} {m.completude}")
                A(f"     origine : {m.origine}")
                A(f"     {m.reference[:64]}")
                if m.verdict:
                    A(f"     verdict : {m.verdict}")
                A(f"     {DONNEE_OBSERVEE} ✓  ·  {OPPORTUNITE_TESTEE} "
                  f"{'✓' if m.porte_un_besoin else '✗ — cette page ne portait aucun besoin'}")
        A("")
        A("─" * 70)
        A("  PROCHAINE MESURE")
        A("─" * 70)
        for ligne in _plier(self.prochaine_mesure(), 66):
            A("  " + ligne)
        return "\n".join(L)


def _plier(texte: str, largeur: int) -> list[str]:
    mots, lignes, courante = texte.split(), [], ""
    for mot in mots:
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = f"{courante} {mot}".strip()
    if courante:
        lignes.append(courante)
    return lignes


def etat(chemin: Path | None = None) -> Etat:
    return Etat(tests_coherence=compter_tests(), mesures=lire_registre(chemin))
