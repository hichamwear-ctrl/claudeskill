"""QUI a exécuté la recherche — quatre états, et ils ne se confondent jamais.

    RECHERCHE RÉELLE PAR LE RADAR     nous avons interrogé un moteur nous-mêmes
    RÉSULTAT IMPORTÉ — RECHERCHE EXTERNE  quelqu'un d'autre l'a interrogé, hors
                                          du radar, et nous a remis le fichier
    FIXTURE / DEMO                    personne n'a rien interrogé ; les
                                      résultats sont fabriqués
    NON MESURÉ                        rien n'a été tenté — et ce n'est PAS zéro

POURQUOI CE MODULE EXISTE
=========================

`mode.Mode` répond à « cette donnée est-elle réelle ou fabriquée ? » — deux
états, et c'est la question qui décide de la BASE où la donnée atterrit.

Il ne répond pas à « qui a exécuté la recherche ? ». Un export remis par un
poste externe contient de vrais résultats rendus par un vrai moteur : les
appeler « fabriqués » serait faux. Mais le radar n'a interrogé personne :
les présenter comme une recherche qu'il a exécutée serait faux aussi.

Ce sont DEUX questions, et une seule valeur booléenne ne peut pas porter les
deux réponses. Ce module porte la seconde, sans toucher à la première.

CE QUE CE MODULE NE FAIT PAS
============================

Il ne note rien. La nature d'une exécution n'entre dans AUCUN score : un
besoin trouvé par un export externe vaut exactement celui trouvé par une
requête que nous aurions lancée nous-mêmes. C'est le BESOIN qui a une valeur,
jamais le chemin qui nous y a menés — la même règle que pour le circuit.

Il ne classe aucun moteur, il ne privilégie aucune provenance, et il
n'autorise ni n'interdit aucune collecte ultérieure.

LA MARQUE EST UN PRÉFIXE, ET CE N'EST PAS UN DÉTAIL
===================================================

Un résultat importé est inscrit au journal des trouvailles sous un nom de
source QUALIFIÉ — le nom du moteur déclaré, précédé de la marque d'import.
Les deux ne peuvent donc pas se confondre dans les métriques : un moteur
réellement interrogé et un export du même moteur sont deux sources distinctes,
et aucune ne gonfle les chiffres de l'autre.

Le préfixe est en TÊTE parce que les rapports tronquent les noms de source à
droite : une marque en fin de nom disparaîtrait au premier alignement de
colonne. Une garantie qui saute à l'affichage n'est pas une garantie.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .mode import Mode

# Le mot qui marque une source importée. Ce n'est le nom d'aucun fournisseur :
# aucun moteur ne s'appelle ainsi, et ce module n'en connaît aucun.
MARQUE = "import"
SEPARATEUR = ":"
PREFIXE = MARQUE + SEPARATEUR

# Ce qu'on écrit au journal des exécutions, mot pour mot.
PAR_LE_RADAR = "RADAR"
HORS_RADAR = "EXÉCUTÉ HORS RADAR"

# Une date d'exécution illisible ne devient pas la date du jour : elle reste
# inconnue. Dater une recherche qu'on n'a pas datée serait inventer.
DATE_INCONNUE = "INCONNUE"


class Execution(Enum):
    RADAR = "RECHERCHE RÉELLE PAR LE RADAR"
    IMPORT_EXTERNE = "RÉSULTAT IMPORTÉ — RECHERCHE EXTERNE"
    FIXTURE = "FIXTURE / DEMO"
    NON_MESUREE = "NON MESURÉ"

    @property
    def mesuree(self) -> bool:
        """NON MESURÉ n'est pas un résultat : c'est l'absence de mesure."""
        return self is not Execution.NON_MESUREE


class NomDeSourceInvalide(ValueError):
    """Un nom de moteur qui porterait déjà la marque, ou qui serait vide."""


# ═══════════════════════════════════════════════════ le nom qualifié
def qualifier(moteur_declare: str) -> str:
    """« un moteur » → « import:un moteur ».

    Refuse un nom qui contient déjà le séparateur : sans cela, un fichier
    pourrait se déclarer sous un nom déjà qualifié et brouiller la lecture.
    """
    nom = str(moteur_declare or "").strip()
    if not nom:
        raise NomDeSourceInvalide(
            "un import sans nom de moteur n'est pas attribuable : on ne sait "
            "pas qui a produit ces résultats")
    if SEPARATEUR in nom:
        raise NomDeSourceInvalide(
            f"« {nom} » contient « {SEPARATEUR} » — un nom de moteur déclaré "
            "ne peut pas porter le séparateur de marque")
    return PREFIXE + nom


def est_import(source) -> bool:
    return str(source or "").startswith(PREFIXE)


def moteur_declare(source) -> str:
    """Le nom que le fichier a DÉCLARÉ, sans la marque. Ce nom n'est pas une
    preuve : c'est ce que l'exploitant a écrit dans son export."""
    s = str(source or "")
    return s[len(PREFIXE):] if est_import(s) else s


# ═══════════════════════════════════════════════════ la nature d'une ligne
def de_source(source, mode: Mode | None = None) -> Execution:
    """La nature d'une observation, à partir de sa source et de son mode.

    L'ordre compte : la marque d'import l'emporte, parce qu'un import porte le
    mode RÉEL (ses résultats viennent d'un vrai moteur) et serait sinon compté
    comme une recherche que le radar aurait exécutée.
    """
    if est_import(source):
        return Execution.IMPORT_EXTERNE
    if mode is Mode.REEL:
        return Execution.RADAR
    return Execution.FIXTURE


def de_trouvaille(trouvaille) -> Execution:
    return de_source(getattr(trouvaille, "source", None),
                     getattr(trouvaille, "mode", None))


def de_moteur(moteur) -> Execution:
    return de_source(getattr(moteur, "nom", None), getattr(moteur, "mode", None))


# ═══════════════════════════════════════════════════ le journal
@dataclass
class LigneExecution:
    """UNE recherche déclarée exécutée — par nous ou par un poste externe.

    Une ligne à zéro résultat est une MESURE : la requête a été passée et rien
    n'est revenu. L'absence de ligne, elle, n'est pas zéro : c'est NON MESURÉ.
    """
    moteur_declare: str
    source: str
    requete: str | None
    execution_par: str
    date_execution: str | None = None
    fichier: str | None = None
    empreinte: str | None = None
    resultats: int = 0
    refuses: int = 0
    importe_le: str | None = None

    @property
    def nature(self) -> Execution:
        return (Execution.IMPORT_EXTERNE if self.execution_par == HORS_RADAR
                else Execution.RADAR)

    @property
    def muette(self) -> bool:
        return self.resultats == 0

    def ligne(self) -> str:
        return (f"{self.execution_par:<18} {self.moteur_declare[:14]:<16} "
                f"{self.resultats:>4} rés. {self.refuses:>4} ref. "
                f"{(self.date_execution or DATE_INCONNUE)[:19]:<21}"
                f"{(self.requete or '—')[:34]}")


def journaliser(cx, *, moteur_declare: str, source: str, requete,
                execution_par: str, date_execution=None, fichier=None,
                empreinte=None, resultats: int = 0,
                refuses: int = 0) -> LigneExecution:
    """Inscrit ce qui a été exécuté, et par qui. N'inscrit aucun résultat.

    Le journal des exécutions et le journal des trouvailles répondent à deux
    questions différentes : « quelles recherches ont eu lieu » et « quelles
    adresses ont été montrées ». Une recherche sans résultat n'apparaît que
    dans le premier — et c'est exactement pourquoi il existe.
    """
    from .base import maintenant
    cx.execute(
        "INSERT INTO executions_recherche(moteur_declare, source, requete,"
        " execution_par, date_execution, fichier, empreinte, resultats,"
        " refuses, importe_le) VALUES(?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(source, requete, empreinte) DO UPDATE SET"
        "   resultats=excluded.resultats, refuses=excluded.refuses,"
        "   importe_le=excluded.importe_le",
        (moteur_declare, source, requete, execution_par, date_execution,
         fichier, empreinte, int(resultats), int(refuses), maintenant()))
    return LigneExecution(
        moteur_declare=moteur_declare, source=source, requete=requete,
        execution_par=execution_par, date_execution=date_execution,
        fichier=fichier, empreinte=empreinte, resultats=int(resultats),
        refuses=int(refuses))


def _depuis(l) -> LigneExecution:
    return LigneExecution(
        moteur_declare=l["moteur_declare"], source=l["source"],
        requete=l["requete"], execution_par=l["execution_par"],
        date_execution=l["date_execution"], fichier=l["fichier"],
        empreinte=l["empreinte"], resultats=l["resultats"],
        refuses=l["refuses"], importe_le=l["importe_le"])


def executions(cx, *, execution_par=None, source=None) -> list[LigneExecution]:
    sql, args, conditions = "SELECT * FROM executions_recherche", [], []
    if execution_par:
        conditions.append("execution_par=?")
        args.append(execution_par)
    if source:
        conditions.append("source=?")
        args.append(source)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    return [_depuis(l) for l in cx.execute(sql + " ORDER BY id", args).fetchall()]


# ═══════════════════════════════════════════════════ métriques
def repartition(cx) -> dict[str, int]:
    """Combien de TROUVAILLES pour chacun des trois états observables.

    NON MESURÉ n'y figure pas : c'est l'absence de ligne, pas une ligne. Il
    est rendu par `metriques()`, qui sait ce qui n'a jamais été tenté.
    """
    from .trouvailles import toutes as toutes_trouvailles
    compte = {e.value: 0 for e in Execution if e.mesuree}
    for t in toutes_trouvailles(cx):
        compte[de_trouvaille(t).value] += 1
    return compte


def metriques(cx) -> dict:
    """Les quatre états, avec les deux compteurs d'import demandés.

    `requetes_importees_externes` compte les requêtes DÉCLARÉES exécutées hors
    radar, y compris celles qui n'ont rien rendu. Une requête muette a bien
    été passée : ne pas la compter reviendrait à effacer une mesure.
    """
    r = repartition(cx)
    lignes = executions(cx, execution_par=HORS_RADAR)
    radar = executions(cx, execution_par=PAR_LE_RADAR)
    requetes = {l.requete for l in lignes if l.requete}
    sortie = {
        Execution.RADAR.value: r[Execution.RADAR.value],
        Execution.IMPORT_EXTERNE.value: r[Execution.IMPORT_EXTERNE.value],
        Execution.FIXTURE.value: r[Execution.FIXTURE.value],
        "resultats_importes_externes": r[Execution.IMPORT_EXTERNE.value],
        "requetes_importees_externes": len(requetes),
        "executions_externes": len(lignes),
        "executions_externes_muettes": sum(1 for l in lignes if l.muette),
        "refuses_a_l_import": sum(l.refuses for l in lignes),
        "executions_radar": len(radar),
        "moteurs_importes": sorted({l.moteur_declare for l in lignes}),
    }
    # NON MESURÉ : aucune recherche du tout, ni par nous, ni hors radar.
    sortie[Execution.NON_MESUREE.value] = (
        not lignes and not radar
        and r[Execution.RADAR.value] == 0
        and r[Execution.IMPORT_EXTERNE.value] == 0)
    return sortie


def rapport(cx) -> str:
    """Les quatre états côte à côte — c'est le seul rapport qui les sépare.

    `trouvailles.rapport()` sépare fabriqué et réel, ce qui est sa question.
    Celui-ci sépare en plus ce que le radar a interrogé de ce qu'on lui a
    remis. Les deux sont nécessaires ; aucun ne remplace l'autre.
    """
    m = metriques(cx)
    L = ["NATURE DES EXÉCUTIONS DE RECHERCHE", "=" * 80, ""]

    for etat in (Execution.RADAR, Execution.IMPORT_EXTERNE, Execution.FIXTURE):
        L.append(f"  {etat.value:<40} {m[etat.value]:>6} trouvaille(s)")

    L.append("")
    if m[Execution.RADAR.value] == 0:
        L.append(f"  {Execution.RADAR.value} : {Execution.NON_MESUREE.value}")
        L.append("  Le radar n'a interrogé aucun moteur. Ce n'est pas zéro")
        L.append("  résultat : c'est l'absence de recherche.")

    if m["executions_externes"]:
        L.append("")
        L.append(f"IMPORTS — {HORS_RADAR}")
        L.append(f"  résultats importés   {m['resultats_importes_externes']}")
        L.append(f"  requêtes importées   {m['requetes_importees_externes']}")
        L.append(f"  exécutions déclarées {m['executions_externes']}")
        L.append(f"  dont muettes         {m['executions_externes_muettes']}"
                 "  — la requête a été passée, rien n'est revenu : c'est 0,")
        L.append("                         pas NON MESURÉ")
        L.append(f"  refusés à l'import   {m['refuses_a_l_import']}")
        if m["moteurs_importes"]:
            L.append("  moteurs déclarés     " + ", ".join(m["moteurs_importes"]))
        L.append("")
        L.append("  Ces résultats N'ONT PAS été obtenus par le radar. Un moteur")
        L.append("  externe les a rendus ; le fichier a été produit ailleurs et")
        L.append("  remis au radar. Le radar n'a interrogé personne pour eux.")

    L.append("")
    L.append("  La nature d'une exécution n'entre dans AUCUN score. Un besoin")
    L.append("  importé vaut exactement un besoin trouvé par nous : c'est le")
    L.append("  besoin qui a une valeur, jamais le chemin qui y mène.")
    return "\n".join(L)
