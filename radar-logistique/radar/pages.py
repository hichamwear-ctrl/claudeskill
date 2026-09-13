"""Les pages surveillées — ce qu'on connaît déjà, et qu'on peut revisiter.

Une entreprise n'a pas « un domaine ». Elle a des PAGES : une page partenaires,
une page transporteurs, une page fournisseurs, une page recrutement. Ce sont
ces pages qu'on surveille, pas un domaine abstrait.

TROIS RÈGLES, et elles ne se négocient pas :

1. UNE PAGE N'EST JAMAIS SUPPOSÉE. Posséder « exemple.be » ne donne AUCUN droit
   d'affirmer que « exemple.be/partenaires » existe. Une page entre ici parce
   qu'elle a été découverte, configurée, observée dans une source, ou désignée
   par une règle — et sa PROVENANCE dit laquelle. Il n'y a pas d'URL devinée.

2. LES PAGES SONT INDÉPENDANTES. Une page en erreur n'empêche aucune autre
   d'être consultée. Un domaine injoignable ne condamne pas l'entreprise.

3. UNE ERREUR RÉSEAU N'EST PAS UNE ABSENCE DE CONTENU. `ERREUR` et
   `NON DISPONIBLE` disent que nous n'avons pas pu lire. Ils ne disent RIEN
   sur ce que la page contient, et n'effacent jamais ce qu'on en savait.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from urllib.parse import urlparse, urlunparse


class Acces(Enum):
    """L'état de CONSULTATION d'une page. Jamais son contenu, jamais sa valeur."""
    JAMAIS_CONSULTEE = "JAMAIS CONSULTÉE"
    CONSULTEE = "CONSULTÉE"
    ERREUR = "ERREUR"
    NON_DISPONIBLE = "NON DISPONIBLE"

    @property
    def lue(self) -> bool:
        return self is Acces.CONSULTEE


# Pourquoi cette page est surveillée. Jamais « parce qu'elle pourrait exister ».
DECOUVERTE = "DÉCOUVERTE"          # un moteur ou une source l'a fait apparaître
CONFIGUREE = "CONFIGURÉE"          # l'exploitant l'a désignée
OBSERVEE = "OBSERVÉE DANS UNE SOURCE"   # un lien lu dans une page ou un avis
REGLE = "IDENTIFIÉE PAR RÈGLE"     # une règle existante l'a retenue

PROVENANCES = frozenset({DECOUVERTE, CONFIGUREE, OBSERVEE, REGLE})


class ProvenanceInconnue(ValueError):
    """Une page sans provenance est une page supposée. On refuse."""


def normaliser(url: str) -> str:
    """Compare deux URL sans les réécrire : schéma et hôte en minuscules, le
    fragment retiré. Le chemin est laissé TEL QUEL — « /Partenaires » et
    « /partenaires » ne sont pas la même ressource sur tous les serveurs."""
    p = urlparse((url or "").strip())
    if not p.scheme or not p.netloc:
        return (url or "").strip()
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path or "/",
                       p.params, p.query, ""))


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PageSurveillee:
    url: str
    entreprise: str | None = None          # clé de l'entreprise au registre
    provenance: str = DECOUVERTE
    acces: Acces = Acces.JAMAIS_CONSULTEE
    derniere_visite: str | None = None
    empreinte: str | None = None
    motif: str | None = None               # le détail du dernier accès
    libelle: str | None = None

    def ligne(self) -> str:
        quand = (self.derniere_visite or "jamais")[:19]
        return (f"{self.url[:52]:<54} {self.acces.value:<17} {quand:<21}"
                f"{self.provenance}"
                + (f" · {self.motif[:40]}" if self.motif else ""))


def _acces(valeur) -> Acces:
    for a in Acces:
        if a.value == valeur:
            return a
    return Acces.JAMAIS_CONSULTEE


# ─────────────────────────────────────────────────────────── base de données
def declarer(cx, url, *, entreprise=None, provenance=DECOUVERTE,
             libelle=None) -> PageSurveillee:
    """Inscrit une page. Redéclarer une page connue ne l'écrase pas : elle
    garde son état d'accès, sa dernière visite et son empreinte."""
    if provenance not in PROVENANCES:
        raise ProvenanceInconnue(
            f"provenance « {provenance} » inconnue — une page ne s'inscrit pas "
            f"sans dire d'où elle vient ({', '.join(sorted(PROVENANCES))})")
    u = normaliser(url)
    if not u:
        raise ValueError("URL vide")
    cx.execute(
        "INSERT INTO pages_surveillees(url, entreprise, provenance, acces,"
        " libelle, declaree_le) VALUES(?,?,?,?,?,?)"
        " ON CONFLICT(url) DO UPDATE SET"
        "   entreprise=COALESCE(excluded.entreprise, pages_surveillees.entreprise),"
        "   libelle=COALESCE(excluded.libelle, pages_surveillees.libelle)",
        (u, entreprise, provenance, Acces.JAMAIS_CONSULTEE.value, libelle,
         _maintenant()))
    return lire(cx, u)


def lire(cx, url) -> PageSurveillee | None:
    l = cx.execute("SELECT * FROM pages_surveillees WHERE url=?",
                   (normaliser(url),)).fetchone()
    if l is None:
        return None
    return PageSurveillee(url=l["url"], entreprise=l["entreprise"],
                          provenance=l["provenance"], acces=_acces(l["acces"]),
                          derniere_visite=l["derniere_visite"],
                          empreinte=l["empreinte"], motif=l["motif"],
                          libelle=l["libelle"])


def a_surveiller(cx, entreprise=None, limite=None) -> list[PageSurveillee]:
    """Les pages à revisiter, la plus anciennement vue d'abord. Une page en
    ERREUR reste dans la liste : une erreur n'est pas un abandon."""
    sql = "SELECT * FROM pages_surveillees"
    args = []
    if entreprise:
        sql += " WHERE entreprise=?"
        args.append(entreprise)
    sql += " ORDER BY derniere_visite IS NOT NULL, derniere_visite, id"
    if limite:
        sql += f" LIMIT {int(limite)}"
    return [lire(cx, l["url"]) for l in cx.execute(sql, args).fetchall()]


def marquer(cx, url, acces: Acces, *, motif=None, empreinte=None) -> PageSurveillee:
    """Enregistre le RÉSULTAT D'ACCÈS d'une visite.

    L'empreinte n'est écrite que si une lecture a réellement eu lieu. Une
    erreur réseau n'écrase JAMAIS l'empreinte valide de la dernière lecture
    réussie : sinon la visite suivante croirait la page modifiée alors que
    c'est notre accès qui a échoué.
    """
    u = normaliser(url)
    if acces is Acces.CONSULTEE and empreinte:
        cx.execute("UPDATE pages_surveillees SET acces=?, derniere_visite=?,"
                   " motif=?, empreinte=? WHERE url=?",
                   (acces.value, _maintenant(), motif, empreinte, u))
    else:
        cx.execute("UPDATE pages_surveillees SET acces=?, derniere_visite=?,"
                   " motif=? WHERE url=?",
                   (acces.value, _maintenant(), motif, u))
    return lire(cx, u)


def rapport(cx) -> str:
    pages = a_surveiller(cx)
    L = ["PAGES SURVEILLÉES", "=" * 100, ""]
    if not pages:
        return "\n".join(L + ["  aucune page surveillée — aucune n'a été déclarée.",
                              "  Une page n'est jamais supposée à partir d'un domaine."])
    for p in pages:
        L.append("  " + p.ligne())
    compte = {a: sum(1 for p in pages if p.acces is a) for a in Acces}
    L.append("")
    L.append(f"  {len(pages)} page(s) · "
             + " · ".join(f"{a.value} {compte[a]}" for a in Acces if compte[a]))
    if compte[Acces.JAMAIS_CONSULTEE]:
        L.append(f"  {compte[Acces.JAMAIS_CONSULTEE]} page(s) n'ont JAMAIS été "
                 "consultées : on ne sait rien de leur contenu.")
    return "\n".join(L)
