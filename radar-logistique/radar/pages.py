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


class Statut(Enum):
    """Où en est cette page dans son cycle de vie.

    CANDIDATE  elle a été RENCONTRÉE. Rien de plus. On sait qu'elle existe
               et par quoi on l'a vue ; on n'a pas décidé de la surveiller.
    SURVEILLÉE elle est dans la rotation des visites.
    ÉCARTÉE    on ne la visite plus, et le motif est écrit.

    Le passage de CANDIDATE à SURVEILLÉE est une DÉCISION, pas un effet de
    bord : `promouvoir()` l'écrit avec sa raison. Aucune règle automatique ne
    promeut une page dans ce module — ce serait une règle métier, et elle
    n'appartient pas à la plomberie.
    """
    CANDIDATE = "CANDIDATE"
    SURVEILLEE = "SURVEILLÉE"
    ECARTEE = "ÉCARTÉE"


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
    provenance: str = DECOUVERTE           # la PREMIÈRE rencontre
    statut: Statut = Statut.CANDIDATE
    raison: str | None = None              # pourquoi elle est passée surveillée
    acces: Acces = Acces.JAMAIS_CONSULTEE
    derniere_visite: str | None = None
    empreinte: str | None = None
    motif: str | None = None               # le détail du dernier accès
    libelle: str | None = None
    provenances: list = None               # toutes les rencontres, voir lire()

    @property
    def surveillee(self) -> bool:
        return self.statut is Statut.SURVEILLEE

    def ligne(self) -> str:
        quand = (self.derniere_visite or "jamais")[:19]
        return (f"{self.url[:48]:<50} {self.statut.value:<11} {self.acces.value:<17} "
                f"{quand:<21}{self.provenance}"
                + (f" · {self.motif[:36]}" if self.motif else ""))


def _acces(valeur) -> Acces:
    for a in Acces:
        if a.value == valeur:
            return a
    return Acces.JAMAIS_CONSULTEE


def _statut(valeur) -> Statut:
    """Un statut illisible ne devient pas SURVEILLÉE : on retombe sur
    CANDIDATE, qui n'engage à rien."""
    for st in Statut:
        if st.value == valeur:
            return st
    return Statut.CANDIDATE


# ─────────────────────────────────────────────────────────── base de données
def rencontrer(cx, url, *, entreprise=None, provenance=DECOUVERTE, source=None,
               circuit=None, raison=None, libelle=None,
               statut: Statut = Statut.CANDIDATE) -> PageSurveillee:
    """UNE page, autant de provenances qu'on l'a rencontrée.

    Rencontrer une page déjà connue n'en crée PAS une seconde et n'écrase
    rien : on ajoute une provenance. Google, le BDA et le site de l'entreprise
    qui montrent la même page produisent UNE page et TROIS provenances.

    Le statut par défaut est CANDIDATE : rencontrer n'est pas décider de
    surveiller. Seul `promouvoir()` fait passer une page en SURVEILLÉE.
    """
    if provenance not in PROVENANCES:
        raise ProvenanceInconnue(
            f"provenance « {provenance} » inconnue — une page ne s'inscrit pas "
            f"sans dire d'où elle vient ({', '.join(sorted(PROVENANCES))})")
    u = normaliser(url)
    if not u:
        raise ValueError("URL vide")
    cx.execute(
        "INSERT INTO pages_surveillees(url, entreprise, provenance, statut,"
        " raison, acces, libelle, declaree_le) VALUES(?,?,?,?,?,?,?,?)"
        " ON CONFLICT(url) DO UPDATE SET"
        "   entreprise=COALESCE(excluded.entreprise, pages_surveillees.entreprise),"
        "   libelle=COALESCE(excluded.libelle, pages_surveillees.libelle)",
        (u, entreprise, provenance, statut.value, raison,
         Acces.JAMAIS_CONSULTEE.value, libelle, _maintenant()))
    cx.execute(
        "INSERT OR IGNORE INTO provenances_pages(url, source, circuit, raison, vue_le)"
        " VALUES(?,?,?,?,?)",
        (u, source or provenance, circuit, raison, _maintenant()))
    return lire(cx, u)


# Nom historique conservé : une déclaration explicite est une rencontre dont
# l'exploitant est la source.
def declarer(cx, url, *, entreprise=None, provenance=DECOUVERTE, libelle=None,
             statut: Statut = Statut.CANDIDATE, raison=None) -> PageSurveillee:
    return rencontrer(cx, url, entreprise=entreprise, provenance=provenance,
                      libelle=libelle, statut=statut, raison=raison)


def promouvoir(cx, url, raison: str) -> PageSurveillee:
    """CANDIDATE → SURVEILLÉE. C'est une DÉCISION, et sa raison est écrite.

    Ce module ne promeut jamais tout seul : quelle page mérite d'être
    surveillée est une règle métier, pas de la plomberie.
    """
    if not raison:
        raise ValueError("une page ne devient surveillée sans raison écrite")
    u = normaliser(url)
    cx.execute("UPDATE pages_surveillees SET statut=?, raison=? WHERE url=?",
               (Statut.SURVEILLEE.value, raison, u))
    return lire(cx, u)


def ecarter(cx, url, raison: str) -> PageSurveillee:
    u = normaliser(url)
    cx.execute("UPDATE pages_surveillees SET statut=?, raison=? WHERE url=?",
               (Statut.ECARTEE.value, raison, u))
    return lire(cx, u)


def provenances_de(cx, url) -> list[dict]:
    """Toutes les façons dont cette page a été rencontrée."""
    return [dict(l) for l in cx.execute(
        "SELECT source, circuit, raison, vue_le FROM provenances_pages"
        " WHERE url=? ORDER BY id", (normaliser(url),)).fetchall()]


def lire(cx, url) -> PageSurveillee | None:
    l = cx.execute("SELECT * FROM pages_surveillees WHERE url=?",
                   (normaliser(url),)).fetchone()
    if l is None:
        return None
    cles = l.keys()
    return PageSurveillee(
        url=l["url"], entreprise=l["entreprise"], provenance=l["provenance"],
        statut=_statut(l["statut"] if "statut" in cles else None),
        raison=l["raison"] if "raison" in cles else None,
        acces=_acces(l["acces"]), derniere_visite=l["derniere_visite"],
        empreinte=l["empreinte"], motif=l["motif"], libelle=l["libelle"],
        provenances=provenances_de(cx, l["url"]))


def a_surveiller(cx, entreprise=None, limite=None, *, toutes=False) -> list[PageSurveillee]:
    """Les pages à revisiter, la plus anciennement vue d'abord.

    SEULES les pages SURVEILLÉES y figurent : une CANDIDATE a été rencontrée,
    elle n'a pas été retenue. Une page en ERREUR reste dans la liste — une
    erreur d'accès n'est pas un abandon.
    """
    sql = "SELECT * FROM pages_surveillees"
    conditions, args = [], []
    if not toutes:
        conditions.append("statut=?")
        args.append(Statut.SURVEILLEE.value)
    if entreprise:
        conditions.append("entreprise=?")
        args.append(entreprise)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
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


# ═════════════════════════════ ALIMENTATION AUTOMATIQUE
#
# Cinq objets, et ils ne se confondent JAMAIS :
#
#     ENTREPRISE IDENTIFIÉE   une raison sociale, au registre des entreprises
#     PAGE IDENTIFIÉE         une URL qui existe et qu'on a vue
#     PAGE CANDIDATE          retenue par le filtre, pas encore décidée
#     PAGE SURVEILLÉE         dans la rotation des visites, avec sa raison
#     OPPORTUNITÉ             un besoin, produit par la chaîne d'analyse
#
# Ce qui suit fabrique des PAGES. Jamais des entreprises, jamais des
# opportunités. Un domaine n'est pas une raison sociale.

def depuis_liens(cx, candidats, *, entreprise=None, source="page surveillée",
                 circuit=None) -> dict:
    """Inscrit des liens RETENUS comme pages candidates, et promeut celles qui
    portent un indice fort.

    Rend un décompte : {"candidates": n, "promues": n, "deja_connues": n}.
    Une page déjà connue n'est ni dupliquée ni rétrogradée : on lui ajoute
    seulement une provenance de plus.
    """
    bilan = {"candidates": 0, "promues": 0, "deja_connues": 0}
    for c in candidats or []:
        existante = lire(cx, c.url)
        if existante is not None:
            bilan["deja_connues"] += 1
        rencontrer(cx, c.url, entreprise=entreprise, provenance=DECOUVERTE,
                   source=source, circuit=circuit, raison=c.raison(),
                   libelle=c.libelle or None)
        if existante is None:
            bilan["candidates"] += 1
        # La promotion n'a lieu que sur indice FORT, et seulement si la page
        # n'est pas DÉJÀ surveillée ou écartée : on ne réveille pas une page
        # que l'exploitant a écartée à la main.
        if c.promouvable and (existante is None
                              or existante.statut is Statut.CANDIDATE):
            promouvoir(cx, c.url, c.pertinence.raison())
            bilan["promues"] += 1
    return bilan


def depuis_opportunite(cx, opp, *, entreprise=None, circuit=None) -> int:
    """Les URL OBSERVÉES dans un avis deviennent des pages CANDIDATES.

    Jamais surveillées automatiquement : l'URL d'un dossier sur un portail
    public n'est pas la page d'une entreprise, et la promouvoir remplirait la
    rotation de pages de procédure. Elle est retenue parce qu'elle a été vue,
    et c'est tout ce qu'on en sait.
    """
    n = 0
    for url in (getattr(opp, "lien_dossier", None), getattr(opp, "plateforme", None)):
        if not url or not str(url).startswith(("http://", "https://")):
            continue
        rencontrer(cx, url, entreprise=entreprise, provenance=OBSERVEE,
                   source=getattr(opp, "source", None) or "avis", circuit=circuit,
                   raison="URL observée dans un avis")
        n += 1
    return n
