"""Le même besoin vu par plusieurs moteurs — une entité, toutes les observations.

    MOTEUR A ─┐
    MOTEUR B ─┼──► DÉCOUVERTES ──► REGROUPEMENT ──► UNE ENTITÉ
    MOTEUR C ─┘                         │
                                        └── et TOUTES les provenances

TROIS DÉDUPLICATIONS, ET CE MODULE N'EN FAIT QU'UNE
===================================================

    A · URL         la même page vue plusieurs fois.        ← ICI
    B · BESOIN      le même besoin sur des pages distinctes. ← radar/deduplication.py
    C · ENTREPRISE  la même organisation.                    ← le domaine, 8c

Ce module regroupe au niveau A, et il MESURE. Il n'écrit aucune nouvelle règle
de fusion : la canonisation d'URL et la comparaison de besoin existent déjà, et
en écrire une seconde version ferait diverger deux définitions du même fait.

POURQUOI LE BESOIN NE SE DÉDOUBLONNE PAS ICI
============================================

Une trouvaille ne porte qu'un titre et un extrait — écrits par le moteur. Pas
d'organisation, pas d'objet structuré, pas d'échéance. Rapprocher deux besoins
là-dessus reviendrait à fusionner sur quelques mots, et une opportunité
fusionnée à tort ne revient jamais.

`deduplication.meme_besoin` exige LA MÊME ORGANISATION avant de comparer quoi
que ce soit. C'est ce qui empêche « distribution de colis à Namur » de
fusionner avec « distribution de colis à Liège ». Cette garantie n'existe
qu'après collecte, sur des opportunités réelles. Le besoin s'y dédoublonne, et
mieux qu'ici.

CE QUE LE RECOUPEMENT NE FAIT JAMAIS
====================================

Il ne touche à rien de commercial. Ni score, ni catégorie, ni suppression
d'une opportunité faible, ni avantage à un moteur. Il compte des observations.

Et il ne classe JAMAIS un moteur au seul volume : un moteur qui rend dix
résultats dont huit que personne d'autre n'a vus vaut plus qu'un moteur qui en
rend cent déjà connus. Le rapport affiche les deux chiffres côte à côte.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .deduplication import canoniser_url
from .execution import Execution, de_source
from .mode import Mode
from .trouvailles import toutes as toutes_trouvailles

NON_MESURE = "NON MESURÉ"


@dataclass
class Observation:
    """UNE fois où UN moteur a montré cette page. Rien n'est fusionné ici."""
    source: str
    requete: str | None
    rang: int | None
    titre: str | None
    url_vue: str                    # l'URL telle que CE moteur l'a rendue
    vue_le: str | None
    mode: Mode = Mode.DEMO


@dataclass
class Groupe:
    """Une page, et toutes les fois où on l'a vue.

    Le groupe ne remplace pas les observations : il les rassemble. On doit
    pouvoir répondre ensuite « par quels moteurs, à quelles dates, avec quelles
    requêtes ? » — et la réponse est dans `observations`, intacte.
    """
    cle: str                        # l'URL canonique
    observations: list = field(default_factory=list)

    @property
    def sources(self) -> list[str]:
        vues = []
        for o in self.observations:
            if o.source not in vues:
                vues.append(o.source)
        return vues

    @property
    def urls_vues(self) -> list[str]:
        """Les formes sous lesquelles l'adresse a été rendue. Deux moteurs
        peuvent écrire la même page différemment."""
        vues = []
        for o in self.observations:
            if o.url_vue not in vues:
                vues.append(o.url_vue)
        return vues

    @property
    def multi_source(self) -> bool:
        return len(self.sources) > 1

    @property
    def premiere_vue(self) -> str | None:
        dates = sorted(o.vue_le for o in self.observations if o.vue_le)
        return dates[0] if dates else None

    @property
    def derniere_vue(self) -> str | None:
        dates = sorted(o.vue_le for o in self.observations if o.vue_le)
        return dates[-1] if dates else None

    @property
    def requetes(self) -> list[str]:
        vues = []
        for o in self.observations:
            if o.requete and o.requete not in vues:
                vues.append(o.requete)
        return vues

    def historique(self) -> list[str]:
        """« Découverte par quels moteurs, à quelles dates ? » — la réponse."""
        return [f"{(o.vue_le or '?')[:19]} · {o.source}"
                + (f" · rang {o.rang}" if o.rang else "")
                + (f" · {o.requete}" if o.requete else "")
                for o in sorted(self.observations, key=lambda x: x.vue_le or "")]


def grouper(trouvailles) -> list[Groupe]:
    """Regroupe par URL CANONIQUE — et par rien d'autre.

    La canonisation vient de `deduplication.canoniser_url` : www., barre
    finale, paramètres de suivi. Deux adresses qui ne se réduisent pas à la
    même clé restent DEUX groupes, même si elles se ressemblent. La
    ressemblance n'est pas une preuve.
    """
    groupes: dict[str, Groupe] = {}
    for t in trouvailles or []:
        cle = canoniser_url(t.url) or t.url
        g = groupes.setdefault(cle, Groupe(cle=cle))
        g.observations.append(Observation(
            source=t.source, requete=t.requete, rang=t.rang, titre=t.titre,
            url_vue=t.url, vue_le=t.decouverte_le, mode=t.mode))
    return list(groupes.values())


def rapprochements_refuses(trouvailles) -> list[tuple[str, str]]:
    """Les paires QUI SE RESSEMBLENT et qu'on a refusé de fusionner.

    Même hôte, chemins différents : on les a regardées ensemble et on a
    conclu que ce sont deux pages. Les compter rend le refus visible — sans
    cela, on ne saurait jamais ce que la déduplication a décidé de ne pas
    faire.
    """
    par_hote: dict[str, set] = {}
    for t in trouvailles or []:
        cle = canoniser_url(t.url)
        if not cle:
            continue
        par_hote.setdefault(cle.split("/")[0], set()).add(cle)
    refuses = []
    for cles in par_hote.values():
        rangees = sorted(cles)
        for i, a in enumerate(rangees):
            for b in rangees[i + 1:]:
                refuses.append((a, b))
    return refuses


# ═══════════════════════════════════════════ métriques de rappel
def metriques_moteurs(cx, *, mode: Mode | None = None, declares=None,
                      interroges=()) -> dict[str, dict]:
    """Ce que chaque moteur apporte — volume ET apport propre.

    TROIS ÉTATS, ET ILS NE SE CONFONDENT PAS :

      · il a rendu des résultats        → les chiffres
      · il a été INTERROGÉ sans rien rendre → 0, et c'est une mesure
      · il n'a PAS été interrogé        → NON MESURÉ, et ce n'est pas 0

    `interroges` : les moteurs qu'on a réellement interrogés. Ceux qui n'ont
    rien rendu affichent 0 — ils ont répondu, leur silence est un fait.
    `declares` : les moteurs connus mais non interrogés, avec leur motif.

    Chaque ligne porte en plus sa NATURE D'EXÉCUTION : ce que le radar a
    interrogé lui-même, ce qu'on lui a remis, ce qui est fabriqué. Sans elle,
    un export remis de l'extérieur se lirait comme une performance du radar —
    et les deux se compteraient ensemble.
    """
    groupes = grouper(toutes_trouvailles(cx, mode=mode))
    par_source: dict[str, dict] = {}
    for g in groupes:
        for source in g.sources:
            c = par_source.setdefault(source, {
                "resultats": 0, "urls": 0, "uniques": 0, "partagees": 0,
                "requetes": set(), "mesure": True})
            c["urls"] += 1
            if g.multi_source:
                c["partagees"] += 1
            else:
                c["uniques"] += 1
        for o in g.observations:
            c = par_source[o.source]
            c["resultats"] += 1
            c.setdefault("modes", set()).add(o.mode)
            if o.requete:
                c["requetes"].add(o.requete)

    for source, c in par_source.items():
        c["requetes"] = len(c["requetes"])
        modes = c.pop("modes", set())
        c["nature"] = de_source(source,
                                Mode.REEL if Mode.REEL in modes else None).value
        # Part de ce que ce moteur a montré que PERSONNE d'autre n'a montré.
        c["apport_propre"] = (c["uniques"] / c["urls"]) if c["urls"] else 0.0
        c["recouvrement"] = (c["partagees"] / c["urls"]) if c["urls"] else 0.0

    # Interrogé et muet : zéro est une MESURE. Il a répondu.
    for nom in interroges or ():
        if nom in par_source:
            continue
        par_source[nom] = {"resultats": 0, "urls": 0, "uniques": 0,
                           "partagees": 0, "requetes": 0, "apport_propre": 0.0,
                           "recouvrement": 0.0, "mesure": True, "muet": True,
                           "nature": de_source(nom, mode).value}

    for nom, motif in (declares or {}).items():
        if nom in par_source:
            continue
        # Déclaré mais sans trouvaille : on ne sait pas ce qu'il aurait rendu.
        par_source[nom] = {"resultats": NON_MESURE, "urls": NON_MESURE,
                           "uniques": NON_MESURE, "partagees": NON_MESURE,
                           "requetes": NON_MESURE, "apport_propre": None,
                           "recouvrement": None, "mesure": False,
                           "nature": Execution.NON_MESUREE.value,
                           "motif": motif}
    return par_source


def metriques_rappel(cx, *, mode: Mode | None = None) -> dict:
    """La chaîne demandée, de bout en bout."""
    trouvailles = toutes_trouvailles(cx, mode=mode)
    groupes = grouper(trouvailles)
    return {
        "resultats_bruts": len(trouvailles),
        "urls_uniques": len(groupes),
        "observations_partagees": sum(len(g.observations) for g in groupes
                                      if g.multi_source),
        "groupes": len(groupes),
        "groupes_multi_sources": sum(1 for g in groupes if g.multi_source),
        "doublons_regroupes": len(trouvailles) - len(groupes),
        "rapprochements_refuses": len(rapprochements_refuses(trouvailles)),
    }


def domaines_transversaux(cx, *, mode: Mode | None = None,
                          seuil: int = 3) -> dict[str, int]:
    """INDICATEUR SEULEMENT — un domaine qui revient sous des requêtes sans
    rapport entre elles.

    Un site de presse ou un agrégateur se comporte ainsi : il parle de tout.
    Une entreprise opérationnelle, non.

    MAIS CE N'EST PAS UNE PREUVE, ET RIEN N'EN EST DÉDUIT ICI. Un grand
    transporteur peut apparaître sous beaucoup de requêtes différentes sans
    cesser d'être une entreprise. L'identité reste INCONNUE ; aucune liste
    n'est écrite ; aucune entreprise n'est écartée.
    """
    par_domaine: dict[str, set] = {}
    for t in toutes_trouvailles(cx, mode=mode):
        cle = canoniser_url(t.url)
        if not cle or not t.requete:
            continue
        par_domaine.setdefault(cle.split("/")[0], set()).add(t.requete)
    return {d: len(qs) for d, qs in par_domaine.items() if len(qs) >= seuil}


def rapport(cx, *, mode: Mode | None = None, declares=None,
            interroges=()) -> str:
    r = metriques_rappel(cx, mode=mode)
    L = ["RECOUPEMENT ENTRE MOTEURS", "=" * 88, ""]
    L.append("CHAÎNE DE RAPPEL")
    for cle, libelle in (("resultats_bruts", "résultats bruts"),
                         ("urls_uniques", "URL uniques"),
                         ("observations_partagees", "observations partagées"),
                         ("groupes", "groupes de page"),
                         ("groupes_multi_sources", "groupes multi-sources"),
                         ("doublons_regroupes", "doublons regroupés"),
                         ("rapprochements_refuses", "rapprochements refusés")):
        L.append(f"  {libelle:<26} {r[cle]}")

    m = metriques_moteurs(cx, mode=mode, declares=declares,
                          interroges=interroges)
    L.append("")
    L.append("PAR MOTEUR — le volume ET l'apport propre, côte à côte")
    L.append(f"  {'MOTEUR':<20} {'RÉSULTATS':>10} {'URL':>7} {'UNIQUES':>8} "
             f"{'PARTAGÉES':>10} {'APPORT':>8}   NATURE")
    for source, c in sorted(m.items()):
        if not c["mesure"]:
            L.append(f"  {source[:20]:<20} {NON_MESURE:>10}   "
                     f"NON DISPONIBLE — {c.get('motif') or 'motif non précisé'}")
            continue
        ligne = (f"  {source[:20]:<20} {c['resultats']:>10} {c['urls']:>7} "
                 f"{c['uniques']:>8} {c['partagees']:>10} "
                 f"{c['apport_propre']:>7.0%}   {c.get('nature', NON_MESURE)}")
        if c.get("muet"):
            ligne += "   interrogé, aucun résultat — c'est une mesure"
        L.append(ligne)
    L.append("")
    L.append("  « NATURE » dit QUI a exécuté la recherche. Un export remis au")
    L.append("  radar n'est pas une performance du radar : les deux ne se")
    L.append("  comptent jamais ensemble, et portent des noms de source")
    L.append("  distincts pour que ce soit impossible.")
    L.append("  « APPORT » = part des pages que ce moteur a montrées et que")
    L.append("  personne d'autre n'a montrées. Un moteur qui rend dix pages")
    L.append("  dont huit inédites vaut plus qu'un moteur qui en rend cent")
    L.append("  déjà connues. AUCUN MOTEUR N'EST CLASSÉ AU VOLUME.")
    L.append("")
    L.append("  NON MESURÉ n'est pas 0 : un moteur qu'on n'a pas interrogé")
    L.append("  n'a pas « rendu zéro résultat ».")

    transversaux = domaines_transversaux(cx, mode=mode)
    if transversaux:
        L.append("")
        L.append("DOMAINES VUS SOUS PLUSIEURS SUJETS SANS RAPPORT — INDICATEUR")
        for d, n in sorted(transversaux.items(), key=lambda x: -x[1]):
            L.append(f"  {d[:40]:<42} {n} requêtes distinctes")
        L.append("  Ce n'est PAS une preuve qu'il s'agit d'un agrégateur : un")
        L.append("  grand transporteur se comporterait pareil. Aucune identité")
        L.append("  n'est modifiée, aucune entreprise n'est écartée.")
    return "\n".join(L)
