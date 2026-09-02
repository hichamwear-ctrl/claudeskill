"""Ce que le radar apprend du marché, à partir de ce qu'il a réellement vu.

Aucune de ces mesures n'est estimée : elles se calculent sur la base. Quand il
n'y a pas assez d'observations, la réponse est « NON MESURÉ » et non une
tendance inventée.

Sert deux décisions concrètes :
  · quelles sources méritent d'être lues en priorité (§24) ;
  · quels types de contrats ont le plus de chances d'être décrochés (§21).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .modele import NON_MESURE

MINIMUM_POUR_CONCLURE = 10


@dataclass
class Rendement:
    source: str
    lues: int
    exploitables: int
    directes: int

    @property
    def taux(self) -> float:
        return self.exploitables / self.lues if self.lues else 0.0


@dataclass
class Apprentissage:
    rendements: list[Rendement] = field(default_factory=list)
    acheteurs_recurrents: list[tuple] = field(default_factory=list)
    familles_porteuses: list[tuple] = field(default_factory=list)
    titulaires_actifs: list[tuple] = field(default_factory=list)
    montants_accessibles: list[float] = field(default_factory=list)
    observations: int = 0

    def rapport(self) -> str:
        L = ["CE QUE LE RADAR A APPRIS", "=" * 60, ""]
        if self.observations < MINIMUM_POUR_CONCLURE:
            L.append(f"{self.observations} opportunité(s) en base — moins de "
                     f"{MINIMUM_POUR_CONCLURE}.")
            L.append("Aucune conclusion n'est tirée : ce serait du bruit, pas un apprentissage.")
            return "\n".join(L)

        L.append("RENDEMENT DES SOURCES — priorité à recalculer sur ces chiffres")
        for r in sorted(self.rendements, key=lambda x: -x.taux):
            L.append(f"  {r.taux:6.0%}  {r.source:<14} {r.exploitables:>4} exploitables "
                     f"sur {r.lues:>4} lues  (dont {r.directes} à postuler)")
        L.append("")
        L.append("ACHETEURS QUI REVIENNENT — ils rachèteront")
        if self.acheteurs_recurrents:
            for nom, n in self.acheteurs_recurrents:
                L.append(f"  {n:>3}×  {nom[:56]}")
        else:
            L.append(f"  {NON_MESURE} — aucun acheteur vu plus d'une fois")
        L.append("")
        L.append("TYPES DE CONTRATS LES PLUS ACCESSIBLES")
        if self.familles_porteuses:
            for famille, n in self.familles_porteuses:
                L.append(f"  {n:>3}  {famille}")
        else:
            L.append(f"  {NON_MESURE}")
        L.append("")
        L.append("TITULAIRES À DÉMARCHER — ils gagnent et devront sous-traiter")
        if self.titulaires_actifs:
            for nom, n in self.titulaires_actifs:
                L.append(f"  {n:>3} marché(s)  {nom[:50]}")
        else:
            L.append(f"  {NON_MESURE}")
        L.append("")
        L.append("TAILLE DES CONTRATS RÉELLEMENT ACCESSIBLES")
        if self.montants_accessibles:
            t = sorted(self.montants_accessibles)
            L.append(f"  médiane {t[len(t)//2]:,.0f} EUR sur {len(t)} observés".replace(",", " "))
            L.append(f"  de {t[0]:,.0f} à {t[-1]:,.0f}".replace(",", " "))
        else:
            L.append(f"  {NON_MESURE}")
        return "\n".join(L)


def apprendre(cx) -> Apprentissage:
    a = Apprentissage()
    a.observations = cx.execute("SELECT count(*) c FROM opportunites").fetchone()["c"]

    for l in cx.execute(
            "SELECT av.source AS s, count(*) AS lues,"
            " sum(o.type IN ('DIRECT','SOUS_TRAITANCE')) AS utiles,"
            " sum(o.type = 'DIRECT') AS directes"
            " FROM opportunites o JOIN avis av ON av.id = o.avis_id GROUP BY av.source"):
        a.rendements.append(Rendement(l["s"], l["lues"], l["utiles"] or 0, l["directes"] or 0))

    a.acheteurs_recurrents = [
        (l["acheteur"], l["n"]) for l in cx.execute(
            "SELECT acheteur, count(*) n FROM opportunites WHERE acheteur IS NOT NULL"
            " AND acheteur <> '' GROUP BY acheteur HAVING n > 1 ORDER BY n DESC LIMIT 10")]

    compte: dict[str, int] = {}
    for l in cx.execute("SELECT familles FROM opportunites WHERE type IN ('DIRECT','SOUS_TRAITANCE')"):
        for f in (l["familles"] or "").split(","):
            if f:
                compte[f] = compte.get(f, 0) + 1
    a.familles_porteuses = sorted(compte.items(), key=lambda x: -x[1])[:10]

    a.titulaires_actifs = [
        (l["titulaire"], l["n"]) for l in cx.execute(
            "SELECT titulaire, count(*) n FROM attributions WHERE titulaire IS NOT NULL"
            " GROUP BY titulaire ORDER BY n DESC LIMIT 10")]

    a.montants_accessibles = [
        l["montant"] for l in cx.execute(
            "SELECT montant FROM opportunites WHERE montant IS NOT NULL"
            " AND type IN ('DIRECT','SOUS_TRAITANCE')")]
    return a
