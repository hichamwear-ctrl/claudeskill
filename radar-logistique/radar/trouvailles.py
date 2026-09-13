"""Le journal de ce qu'un moteur a MONTRÉ — avant toute décision.

    URL DÉCOUVERTE ≠ PAGE COLLECTÉE ≠ CONTENU ANALYSÉ ≠ OPPORTUNITÉ

Une URL rendue par un moteur de recherche n'a PAS été lue par le radar. Le
moteur a rendu un titre, une adresse et un extrait qu'il a écrits lui-même.
Tant que la page n'a pas été récupérée, son contenu reste INCONNU — et une
trouvaille non collectée ne prouve rien du tout.

Ce module tient ce journal, et rien d'autre. Il ne collecte pas, il ne
qualifie pas, il ne crée aucune opportunité.

FIXTURE ET RÉEL NE SE COMPTENT JAMAIS ENSEMBLE
==============================================

Une fixture éprouve le mécanisme ; elle ne mesure AUCUN marché. Le mode est
porté par chaque trouvaille et les rapports les séparent toujours. Tant
qu'aucun moteur réel n'a fonctionné, le rapport écrit :

    DÉCOUVERTE RÉELLE : NON MESURÉE

et ce n'est pas un zéro : c'est l'absence de mesure.

LE RANG NE NOTE RIEN
====================

La place d'un résultat dans la liste d'un moteur sert au diagnostic de capteur
et aux métriques de rappel. Elle n'entre dans aucun score : un besoin trouvé au
dixième rang vaut exactement celui trouvé au premier.

LA MÊME URL VUE DEUX FOIS EST DEUX OBSERVATIONS
===============================================

Deux moteurs qui rendent la même adresse produisent DEUX trouvailles. C'est
ainsi qu'on mesure leur recouvrement — et donc ce que chacun apporte seul. La
déduplication se fait à la lecture, jamais en écrasant une observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .circuit import DECOUVERTE as CIRCUIT_DECOUVERTE, lire as lire_circuit
from .mode import Mode
from .pages import Acces, normaliser

# « JAMAIS CONSULTÉE » est l'état d'une URL qu'un moteur a montrée et que
# personne n'a lue. C'est le vocabulaire d'accès déjà en vigueur pour les
# pages : en créer un second ferait diverger deux définitions du même fait.
NON_COLLECTEE = Acces.JAMAIS_CONSULTEE


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _acces(valeur) -> Acces:
    for a in Acces:
        if a.value == valeur:
            return a
    return NON_COLLECTEE


def _mode(valeur) -> Mode:
    """Un mode illisible retombe sur DEMO. Jamais sur RÉEL : on ne promeut pas
    une fixture au rang de donnée réelle par accident."""
    for m in Mode:
        if m.value == valeur:
            return m
    return Mode.DEMO


@dataclass
class Trouvaille:
    url: str
    source: str
    requete: str | None = None
    rang: int | None = None
    titre: str | None = None
    extrait: str | None = None
    page_source: str | None = None
    circuit: str = CIRCUIT_DECOUVERTE
    mode: Mode = Mode.DEMO
    collecte: Acces = NON_COLLECTEE
    collecte_le: str | None = None
    motif: str | None = None
    decouverte_le: str | None = None

    @property
    def lue(self) -> bool:
        """A-t-on RÉELLEMENT lu cette page ? Presque toujours non."""
        return self.collecte is Acces.CONSULTEE

    @property
    def reelle(self) -> bool:
        return self.mode is Mode.REEL

    def ligne(self) -> str:
        marque = "RÉEL   " if self.reelle else "FIXTURE"
        rang = f"#{self.rang}" if self.rang is not None else "  —"
        return (f"{marque} {self.source[:12]:<14} {rang:>4} "
                f"{self.collecte.value:<17} {self.url[:52]}")


# ═══════════════════════════════════════════════════ écriture
def inscrire(cx, resultat, *, mode: Mode, source=None, circuit=None,
             page_source=None) -> Trouvaille:
    """Inscrit UNE trouvaille, telle que la source l'a rendue.

    Le titre et l'extrait sont conservés MOT POUR MOT : ce sont les mots du
    moteur, pas les nôtres, et ils devront pouvoir être relus tels quels.

    L'état de collecte est posé à JAMAIS CONSULTÉE, sans exception. Aucun
    appelant ne peut déclarer une page lue à l'inscription : seule une
    collecte réelle le fait, par `collectee()`.
    """
    url = normaliser(getattr(resultat, "url", "") or "")
    if not url:
        raise ValueError("une trouvaille sans URL n'est pas une trouvaille")
    nom = source or getattr(resultat, "fournisseur", None) or "?"
    cx.execute(
        "INSERT INTO trouvailles(url, source, requete, rang, titre, extrait,"
        " page_source, circuit, mode, collecte, decouverte_le)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(url, source, requete) DO UPDATE SET"
        "   rang=COALESCE(excluded.rang, trouvailles.rang),"
        "   titre=COALESCE(excluded.titre, trouvailles.titre),"
        "   extrait=COALESCE(excluded.extrait, trouvailles.extrait)",
        (url, nom, getattr(resultat, "requete", None),
         getattr(resultat, "rang", None), getattr(resultat, "titre", None),
         getattr(resultat, "extrait", None),
         page_source or getattr(resultat, "page_source", None),
         lire_circuit(circuit) if circuit else CIRCUIT_DECOUVERTE,
         mode.value, NON_COLLECTEE.value, _maintenant()))
    return lire(cx, url, nom, getattr(resultat, "requete", None))


def inscrire_lot(cx, resultats, *, mode: Mode, source=None, circuit=None,
                 page_source=None) -> list[Trouvaille]:
    """Un lot de résultats, avec leur RANG posé dans l'ordre rendu s'il manque.

    Le rang vient de la position dans la liste : c'est une observation sur le
    moteur, pas un jugement sur le résultat.
    """
    sortie = []
    for position, r in enumerate(resultats or [], start=1):
        if getattr(r, "rang", None) is None:
            try:
                r.rang = position
            except Exception:                                    # noqa: BLE001
                pass
        sortie.append(inscrire(cx, r, mode=mode, source=source, circuit=circuit,
                               page_source=page_source))
    return sortie


def collectee(cx, url, acces: Acces, *, source=None, motif=None) -> int:
    """Enregistre le RÉSULTAT D'UNE TENTATIVE de collecte sur une URL trouvée.

    Toutes les trouvailles portant cette URL sont mises à jour : la page est
    la même, quel que soit le moteur qui l'a montrée.

    Une erreur reste une erreur d'ACCÈS. Elle ne dit rien du contenu, et
    surtout pas qu'il n'y a pas d'opportunité.
    """
    u = normaliser(url)
    sql = ("UPDATE trouvailles SET collecte=?, collecte_le=?, motif=?"
           " WHERE url=?")
    args = [acces.value, _maintenant(), motif, u]
    if source:
        sql += " AND source=?"
        args.append(source)
    return cx.execute(sql, args).rowcount


# ═══════════════════════════════════════════════════ lecture
def _depuis(l) -> Trouvaille:
    return Trouvaille(
        url=l["url"], source=l["source"], requete=l["requete"], rang=l["rang"],
        titre=l["titre"], extrait=l["extrait"], page_source=l["page_source"],
        circuit=l["circuit"], mode=_mode(l["mode"]), collecte=_acces(l["collecte"]),
        collecte_le=l["collecte_le"], motif=l["motif"],
        decouverte_le=l["decouverte_le"])


def lire(cx, url, source=None, requete=None) -> Trouvaille | None:
    sql = "SELECT * FROM trouvailles WHERE url=?"
    args = [normaliser(url)]
    if source:
        sql += " AND source=?"
        args.append(source)
    if requete is not None:
        sql += " AND requete IS ?"
        args.append(requete)
    l = cx.execute(sql + " ORDER BY id DESC LIMIT 1", args).fetchone()
    return _depuis(l) if l else None


def toutes(cx, *, mode: Mode | None = None, source=None,
           limite=None) -> list[Trouvaille]:
    sql, args = "SELECT * FROM trouvailles", []
    conditions = []
    if mode is not None:
        conditions.append("mode=?")
        args.append(mode.value)
    if source:
        conditions.append("source=?")
        args.append(source)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id"
    if limite:
        sql += f" LIMIT {int(limite)}"
    return [_depuis(l) for l in cx.execute(sql, args).fetchall()]


def urls_uniques(cx, *, mode: Mode | None = None) -> list[str]:
    """Les adresses distinctes. Deux moteurs qui montrent la même page ne
    comptent qu'une adresse — mais bien deux observations."""
    sql, args = "SELECT DISTINCT url FROM trouvailles", []
    if mode is not None:
        sql += " WHERE mode=?"
        args.append(mode.value)
    return [l["url"] for l in cx.execute(sql + " ORDER BY url", args).fetchall()]


def recouvrement(cx, *, mode: Mode | None = None) -> dict:
    """Ce que chaque source apporte SEULE, et ce qu'elle partage.

    C'est la mesure qui répond à « ce moteur vaut-il son abonnement ». Elle ne
    change aucun score : elle juge la SOURCE, jamais l'affaire.
    """
    par_url: dict[str, set] = {}
    for t in toutes(cx, mode=mode):
        par_url.setdefault(t.url, set()).add(t.source)
    sortie: dict[str, dict] = {}
    for url, sources in par_url.items():
        for s in sources:
            case = sortie.setdefault(s, {"trouvees": 0, "uniques": 0, "partagees": 0})
            case["trouvees"] += 1
            if len(sources) == 1:
                case["uniques"] += 1
            else:
                case["partagees"] += 1
    return sortie


def metriques(cx) -> dict:
    """Les chiffres de la DÉCOUVERTE, fixture et réel SÉPARÉS."""
    def compte(sql, args=()):
        return cx.execute(sql, args).fetchone()[0]

    sortie = {}
    for mode in Mode:
        m = mode.value
        sortie[m] = {
            "trouvailles": compte("SELECT count(*) FROM trouvailles WHERE mode=?", (m,)),
            "urls_uniques": compte(
                "SELECT count(DISTINCT url) FROM trouvailles WHERE mode=?", (m,)),
            "sources": compte(
                "SELECT count(DISTINCT source) FROM trouvailles WHERE mode=?", (m,)),
            "requetes": compte(
                "SELECT count(DISTINCT requete) FROM trouvailles"
                " WHERE mode=? AND requete IS NOT NULL", (m,)),
            "non_collectees": compte(
                "SELECT count(*) FROM trouvailles WHERE mode=? AND collecte=?",
                (m, Acces.JAMAIS_CONSULTEE.value)),
            "collectees": compte(
                "SELECT count(*) FROM trouvailles WHERE mode=? AND collecte=?",
                (m, Acces.CONSULTEE.value)),
            "erreurs": compte(
                "SELECT count(*) FROM trouvailles WHERE mode=? AND collecte=?",
                (m, Acces.ERREUR.value)),
            "non_disponibles": compte(
                "SELECT count(*) FROM trouvailles WHERE mode=? AND collecte=?",
                (m, Acces.NON_DISPONIBLE.value)),
        }
    return sortie


def rapport(cx) -> str:
    m = metriques(cx)
    reel, demo = m[Mode.REEL.value], m[Mode.DEMO.value]
    L = ["TROUVAILLES — ce qu'un moteur a MONTRÉ", "=" * 84, ""]

    L.append("DÉCOUVERTE RÉELLE")
    if reel["trouvailles"] == 0:
        L.append("  NON MESURÉE — aucun moteur externe n'a fonctionné.")
        L.append("  Ce n'est pas zéro trouvaille : c'est l'absence de mesure.")
    else:
        for cle, libelle in (("trouvailles", "trouvailles"),
                             ("urls_uniques", "URL uniques"),
                             ("sources", "sources"), ("requetes", "requêtes"),
                             ("non_collectees", "NON COLLECTÉES"),
                             ("collectees", "collectées"),
                             ("erreurs", "erreurs"),
                             ("non_disponibles", "non disponibles")):
            L.append(f"  {libelle:<22} {reel[cle]}")

    L.append("")
    L.append("FIXTURE — éprouve le mécanisme, ne mesure AUCUN marché")
    if demo["trouvailles"] == 0:
        L.append("  aucune")
    else:
        L.append(f"  {demo['trouvailles']} trouvaille(s) · "
                 f"{demo['urls_uniques']} URL unique(s) · "
                 f"{demo['non_collectees']} NON COLLECTÉE(S) · "
                 f"{demo['collectees']} collectée(s)")
        L.append("  Ces chiffres ne disent RIEN du marché belge.")

    rec = recouvrement(cx)
    if rec:
        L.append("")
        L.append("APPORT PROPRE DE CHAQUE SOURCE")
        L.append(f"  {'SOURCE':<16} {'TROUVÉES':>9} {'UNIQUES':>9} {'PARTAGÉES':>10}")
        for s, c in sorted(rec.items()):
            L.append(f"  {s[:16]:<16} {c['trouvees']:>9} {c['uniques']:>9} "
                     f"{c['partagees']:>10}")
        L.append("  « Uniques » = trouvées par cette source SEULE. Cela juge la")
        L.append("  source, jamais l'affaire : le rang et l'origine n'entrent")
        L.append("  dans aucun score.")

    total = reel["trouvailles"] + demo["trouvailles"]
    non_lues = reel["non_collectees"] + demo["non_collectees"]
    if total and non_lues:
        L.append("")
        L.append(f"  {non_lues} URL sur {total} n'ont JAMAIS été collectées.")
        L.append("  Leur contenu est INCONNU : un titre de résultat n'est pas")
        L.append("  une page lue, et ne prouve aucune opportunité.")
    return "\n".join(L)


def depuis_moteur(cx, moteur, resultats, *, circuit=None,
                  page_source=None) -> list[Trouvaille]:
    """Inscrit ce QU'UN MOTEUR a rendu, avec LE MODE DU MOTEUR.

    C'est la porte d'entrée à privilégier. `inscrire()` et `inscrire_lot()`
    acceptent encore un mode explicite — un appelant peut donc, en théorie,
    inscrire une fixture comme une mesure réelle. En lisant `moteur.mode`,
    cette fonction rend ce mensonge impossible par simple usage normal.

    Une fixture reste une fixture jusqu'en base, et jusqu'au rapport.
    """
    return inscrire_lot(cx, resultats, mode=moteur.mode,
                        source=getattr(moteur, "nom", None), circuit=circuit,
                        page_source=page_source)
