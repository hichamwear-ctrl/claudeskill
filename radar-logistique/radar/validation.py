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

    def prochaine_mesure(self) -> str:
        """Ce que la prochaine mesure doit lever, en une phrase."""
        if not self.mesures:
            return ("UNE vraie page d'entreprise, conservée en brut. C'est la "
                    "zone qui porte le plus d'incertitude technique : ni champ "
                    "normé, ni statut, ni référence, ni montant.")
        if not self.pages_portant_un_besoin:
            return ("UNE page réelle qui PORTE UN BESOIN. Les pages mesurées "
                    "jusqu'ici n'en contenaient aucun : elles ont éprouvé "
                    "l'extraction et le tri, pas le score, ni les capacités, "
                    "ni l'action commerciale.")
        if not self.pages_completes:
            return ("UNE page d'entreprise COMPLÈTE. Les mesures faites portent "
                    "sur des extraits, pas sur une page entière : la structure "
                    "HTML réelle n'a pas encore été confrontée à l'extracteur.")
        manquantes = [f for f in ("entreprise", "marche_public", "bourse_fret",
                                  "recherche", "signaux")
                      if f not in self.familles_mesurees]
        if manquantes:
            return (f"une source réelle de la famille « {manquantes[0] } » — "
                    f"famille prévue par l'architecture, jamais mesurée.")
        return "une seconde page par famille, pour distinguer l'accident de la règle."

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
        A(f"  COMPORTEMENTS OBSERVÉS SUR DONNÉES RÉELLES : {len(self.mesures)}")
        A(f"  PAGES RÉELLES COMPLÈTES CONSERVÉES         : {self.pages_completes}")
        A(f"  DONT PORTANT UN BESOIN COMMERCIAL          : "
          f"{self.pages_portant_un_besoin}")
        familles = ", ".join(self.familles_mesurees) or "aucune"
        A(f"  FAMILLES RÉELLEMENT MESURÉES               : {familles}")
        A(f"  ADAPTATEURS VALIDÉS SUR DU RÉEL            : "
          f"{len([m for m in self.mesures if m.completude == 'page complète'])}")
        if not self.mesures:
            A("  Aucune donnée non fabriquée n'est encore entrée dans la chaîne.")
        else:
            for m in self.mesures:
                A(f"   · {m.horodatage[:10]}  {m.famille:<12} {m.completude}")
                A(f"     origine : {m.origine}")
                A(f"     {m.reference[:64]}")
                if m.verdict:
                    A(f"     verdict : {m.verdict}")
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
