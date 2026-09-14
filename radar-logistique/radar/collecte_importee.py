"""UNE PAGE LUE AILLEURS — son contenu entre, la qualification 7b décide.

    PAGE COLLECTÉE HORS RADAR ─► CE MODULE ─► pages.marquer()
                                           ─► pertinence.evaluer()
                                           ─► pages.qualifier()   (7b)

POURQUOI CE MODULE EXISTE
=========================

`WebFetch` est bloqué par le même mur d'egress que tout le reste : mesuré,
`EGRESS_BLOCKED` sur chaque domaine essayé. Le radar ne peut donc PAS lire
une page lui-même.

Ce qu'un poste extérieur peut faire, lui. Ce module reçoit ce qu'il a lu, et
le fait entrer par les rails existants — exactement comme `import_externe`
reçoit une recherche exécutée ailleurs. La symétrie est voulue : deux
maillons manquants, deux imports, une seule discipline.

CE QUI EST ENREGISTRÉ, ET CE QUI NE L'EST JAMAIS
================================================

Enregistré : l'URL, la date, l'état d'accès, le contenu, l'erreur s'il y en a
une, l'empreinte du contenu lu, et qui a lu.

Jamais enregistré : une lecture qui n'a pas eu lieu. Une page annoncée sans
contenu et sans erreur n'est pas « collectée » — elle reste
JAMAIS CONSULTÉE, parce que rien ne prouve qu'on l'ait ouverte.

UNE ERREUR D'ACCÈS N'EST PAS UNE ABSENCE DE BESOIN
==================================================

C'est la règle que ce module doit tenir plus fermement qu'aucune autre. Un
404, un 403, un délai dépassé : ce sont des faits sur NOTRE ACCÈS. Ils ne
disent rien du contenu, et surtout pas qu'il n'y a pas d'affaire derrière.
L'état devient ERREUR ou NON DISPONIBLE, la qualification reste ce qu'elle
était, et la page n'est ni écartée ni rétrogradée.

LA QUALIFICATION N'EST PAS RÉÉCRITE ICI
=======================================

Ce module ne décide d'aucun verdict. Il appelle `pertinence.evaluer` — le
même que partout — et passe sa réponse à `pages.qualifier`, qui range. Les
cinq verdicts existants ne bougent pas :

    NON QUALIFIÉE · PREUVE DE CONTENU · CONTRE-PREUVE · SANS PREUVE
    · CONTENU ILLISIBLE
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import pages as mod_pages
from .pages import Acces

PROVENANCE = "COLLECTÉ HORS RADAR"

# Bornes de lecture, comme pour l'import de recherche : au-delà, ce n'est plus
# une page, c'est un fichier abîmé. Généreuse — une vraie page de site peut
# être longue, et tronquer ferait perdre la preuve qui se trouve en bas.
CONTENU_MAX = 2_000_000

CONTENU_ABSENT = "CONTENU ABSENT"
URL_ABSENTE = "URL ABSENTE"
PAGE_INCONNUE = "PAGE NON CANDIDATE — jamais rencontrée"

# Les états d'accès qu'un fichier peut déclarer, sous leur nom exact.
ETATS = {a.value: a for a in Acces}


class CollecteInvalide(ValueError):
    """Le fichier entier est refusé : illisible, ou sans provenance déclarée."""


@dataclass
class Bilan:
    """Ce que la collecte importée a réellement changé."""
    fichier: str | None = None
    lues: int = 0
    collectees: int = 0
    erreurs: int = 0
    non_disponibles: int = 0
    inconnues: int = 0
    refus: list = field(default_factory=list)
    qualifications: dict = field(default_factory=dict)
    promues: int = 0

    def resume(self) -> str:
        L = [f"COLLECTE IMPORTÉE — {PROVENANCE}", "=" * 72, ""]
        L.append(f"  fichier                {self.fichier or '—'}")
        L.append(f"  lignes lues            {self.lues}")
        L.append(f"  pages COLLECTÉES       {self.collectees}")
        L.append(f"  erreurs d'accès        {self.erreurs}")
        L.append(f"  non disponibles        {self.non_disponibles}")
        L.append(f"  URL jamais rencontrées {self.inconnues}")
        if self.qualifications:
            L.append("")
            L.append("QUALIFICATION SUR CONTENU RÉEL (7b)")
            for v, n in sorted(self.qualifications.items(), key=lambda x: -x[1]):
                L.append(f"  {v:<28} {n:>4}")
        L.append(f"  pages PROMUES en surveillance   {self.promues}")
        if self.refus:
            L.append("")
            L.append("LIGNES REFUSÉES — aucune ne disparaît en silence")
            for position, motif, url in self.refus:
                L.append(f"  ligne {position:>4}  {motif:<26} {(url or '—')[:44]}")
        L.append("")
        L.append("  Une erreur d'accès n'est PAS une absence de besoin : elle dit")
        L.append("  que NOTRE lecture a échoué, et rien du contenu.")
        L.append("  Le radar n'a lu aucune de ces pages lui-même.")
        return "\n".join(L)


def _empreinte(contenu: str) -> str:
    return hashlib.sha256(contenu.encode("utf-8", "replace")).hexdigest()[:32]


def _etat(valeur, contenu) -> Acces:
    """L'état déclaré, ou celui que le contenu impose.

    Un état illisible ne devient jamais CONSULTÉE : on ne promeut pas une
    lecture douteuse au rang de lecture réussie. Et une ligne qui annonce
    CONSULTÉE sans contenu ne l'est pas — rien ne prouve qu'on ait ouvert
    quoi que ce soit.
    """
    declare = ETATS.get(str(valeur or "").strip().upper())
    if declare is Acces.CONSULTEE and not (contenu or "").strip():
        return Acces.ERREUR
    if declare is not None:
        return declare
    return Acces.CONSULTEE if (contenu or "").strip() else Acces.JAMAIS_CONSULTEE


def charger(chemin) -> tuple[list, str]:
    """Lit un fichier de collecte. Même discipline que l'import de recherche :
    un fichier qui ne déclare pas sa provenance n'entre pas."""
    p = Path(chemin)
    if not p.exists():
        raise CollecteInvalide(f"collecte introuvable : {p}")
    octets = p.read_bytes()
    if not octets.strip():
        raise CollecteInvalide(f"{p} est vide : aucune provenance déclarée")
    try:
        charge = json.loads(octets.decode("utf-8-sig", "replace"))
    except json.JSONDecodeError as e:
        raise CollecteInvalide(f"{p} illisible comme JSON : {e}") from e
    if not isinstance(charge, dict):
        raise CollecteInvalide(f"{p} : un objet est attendu, avec « pages »")
    declaree = str(charge.get("provenance") or "").strip()
    if declaree != PROVENANCE:
        raise CollecteInvalide(
            f"{p} ne déclare pas « {PROVENANCE} » (lu : « {declaree or 'rien'} »). "
            "On ne charge pas un contenu dont on ne sait pas qui l'a lu.")
    pages = charge.get("pages")
    if not isinstance(pages, list):
        raise CollecteInvalide(f"{p} ne déclare aucune liste « pages »")
    return pages, str(p)


def appliquer(cx, pages, moteur, *, fichier=None) -> Bilan:
    """Fait entrer le contenu réel, puis laisse 7b qualifier.

    `moteur` est le moteur commercial : on y lit l'ontologie et le détecteur
    de rôle, les MÊMES que partout. Aucun vocabulaire parallèle.

    Ne crée AUCUNE page : une URL jamais rencontrée est comptée et signalée,
    pas inventée. Une page n'apparaît que si une découverte l'a montrée.
    """
    from .pertinence import evaluer

    bilan = Bilan(fichier=fichier)
    for position, brute in enumerate(pages or [], start=1):
        bilan.lues += 1
        l = brute if isinstance(brute, dict) else {}
        url = str(l.get("url") or "").strip()
        if not url:
            bilan.refus.append((position, URL_ABSENTE, None))
            continue
        if mod_pages.lire(cx, url) is None:
            bilan.inconnues += 1
            bilan.refus.append((position, PAGE_INCONNUE, url))
            continue

        contenu = l.get("contenu") or l.get("texte") or ""
        if len(contenu) > CONTENU_MAX:
            bilan.refus.append((position, "CONTENU HORS LIMITE", url))
            continue
        acces = _etat(l.get("acces") or l.get("statut"), contenu)
        motif = str(l.get("erreur") or l.get("motif") or "").strip() or None

        if acces is Acces.CONSULTEE:
            bilan.collectees += 1
            mod_pages.marquer(cx, url, acces, motif=motif or f"{len(contenu)} caractères reçus",
                              empreinte=l.get("empreinte") or _empreinte(contenu))
            # LA QUALIFICATION — sur le contenu RÉEL, par le mécanisme 7b.
            p = evaluer(contenu, moteur.ontologie, moteur.roles)
            avant = mod_pages.lire(cx, url)
            apres = mod_pages.qualifier(cx, url, p, texte_lu=True)
            if apres is not None:
                v = apres.qualification.value
                bilan.qualifications[v] = bilan.qualifications.get(v, 0) + 1
                if (avant.statut is not mod_pages.Statut.SURVEILLEE
                        and apres.statut is mod_pages.Statut.SURVEILLEE):
                    bilan.promues += 1
            continue

        # ── ERREUR / NON DISPONIBLE : un fait sur NOTRE accès, rien de plus ──
        if acces is Acces.ERREUR:
            bilan.erreurs += 1
        elif acces is Acces.NON_DISPONIBLE:
            bilan.non_disponibles += 1
        mod_pages.marquer(cx, url, acces, motif=motif or "accès impossible")
        # Aucune qualification n'est écrite : on n'a rien lu. L'ancienne reste.
    return bilan


def importer(cx, chemin, moteur) -> Bilan:
    pages, fichier = charger(chemin)
    return appliquer(cx, pages, moteur, fichier=fichier)


def a_collecter(cx, moteur, *, limite=None) -> list:
    """Les pages candidates jamais lues, INDICE D'ADRESSE D'ABORD.

    L'ordre est un ordre de LECTURE, pas un jugement : une page sans indice
    d'adresse reste dans la liste, simplement plus bas. L'indice ne promeut
    rien, il ne fait que dire par où commencer quand on ne peut pas tout lire.
    """
    from . import adresse
    sortie = []
    for page in mod_pages.a_surveiller(cx, toutes=True):
        if page.acces is not Acces.JAMAIS_CONSULTEE:
            continue
        indice = adresse.lire(page.url, moteur.ontologie, moteur.roles)
        sortie.append((indice, page))
    sortie.sort(key=lambda x: (not x[0].porteuse, x[1].url))
    return sortie[:limite] if limite else sortie


def rapport_a_collecter(cx, moteur, *, limite=None) -> str:
    liste = a_collecter(cx, moteur, limite=limite)
    porteuses = sum(1 for i, _ in liste if i.porteuse)
    L = ["PAGES À COLLECTER — jamais lues", "=" * 88, ""]
    L.append(f"  {len(liste)} page(s) candidate(s) jamais consultée(s)")
    L.append(f"  dont {porteuses} avec un INDICE D'ADRESSE")
    L.append("")
    for indice, page in liste:
        marque = "INDICE" if indice.porteuse else "      "
        L.append(f"  {marque}  {page.url}")
        if indice.porteuse:
            L.append(f"          « {indice.texte[:68]} »")
    L.append("")
    L.append("  Un indice d'adresse dit par où COMMENCER, jamais ce que la page")
    L.append("  contient. Une adresse muette n'écarte aucune page : elle ne")
    L.append("  renseigne pas, c'est tout.")
    L.append("")
    L.append("  Le radar NE PEUT PAS lire ces pages lui-même : l'accès réseau")
    L.append("  est fermé. Un poste extérieur les lit et dépose un fichier :")
    L.append("     { \"provenance\": \"" + PROVENANCE + "\",")
    L.append("       \"pages\": [ {\"url\": \"…\", \"acces\": \"CONSULTÉE\",")
    L.append("                    \"contenu\": \"…\"} ] }")
    return "\n".join(L)
