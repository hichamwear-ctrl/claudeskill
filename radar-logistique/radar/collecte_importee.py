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
    trace: object = None

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


def _en_page(contenu: str, ligne: dict) -> bytes:
    """Le contenu, sous une forme que le PROFIL DE LECTURE sait lire.

    Le profil de page extrait le titre et le corps d'un document HTML. Un
    texte brut n'en est pas un : mesuré, il ressortait « (sans intitulé) » et
    un corps vide, si bien que le contenu réellement collecté n'atteignait
    JAMAIS l'analyse commerciale. Une page dont le besoin était écrit noir sur
    blanc restait « aucun fait commercial observé ».

    Un contenu déjà balisé passe tel quel — on ne réencapsule pas ce qui l'est
    déjà. Un texte brut est enveloppé du strict minimum, et le titre déclaré
    par le collecteur devient le titre du document. Rien n'est ajouté au
    texte : l'enveloppe est une forme, pas un mot de plus.
    """
    brut = contenu or ""
    if "<" in brut[:2000] and ">" in brut[:2000]:
        return brut.encode("utf-8")
    from html import escape
    titre = str(ligne.get("titre") or ligne.get("title") or "").strip()
    corps = "".join(f"<p>{escape(bloc)}</p>"
                    for bloc in brut.split("\n") if bloc.strip())
    return (f"<html><head><title>{escape(titre)}</title></head>"
            f"<body>{corps}</body></html>").encode("utf-8")


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


class Depot:
    """Les pages lues AILLEURS, présentées comme une source de collecte.

    C'est la pièce qui manquait. `boucle.Veille` sait déjà tout faire —
    comparer les empreintes, distinguer INCHANGÉE / MODIFIÉE / MODIFIÉE
    TECHNIQUE / NON COMMERCIALE, qualifier, n'analyser que ce qui bouge et
    peut porter un besoin. Il lui fallait seulement un `recuperer(url)`.

    Ce dépôt en est un. La veille ne sait donc pas — et n'a pas besoin de
    savoir — que le réseau est fermé : elle reçoit des `Collecte`, comme
    toujours, avec leur provenance écrite dessus.

    L'ÉTAPE 8 AVAIT DUPLIQUÉ CE MÉCANISME. Une seconde comparaison
    d'empreintes vivait ici, à côté de `changement.observer`. Deux versions
    d'une même règle finissent toujours par diverger ; celle-ci est retirée
    au profit de la seule qui fait autorité.
    """

    def __init__(self, pages, *, provenance: str = PROVENANCE):
        self.provenance = provenance
        self.par_url: dict = {}
        self.non_declarees: list = []
        for brute in pages or []:
            l = brute if isinstance(brute, dict) else {}
            url = str(l.get("url") or "").strip()
            if url:
                self.par_url[mod_pages.normaliser(url)] = l

    def __contains__(self, url) -> bool:
        return mod_pages.normaliser(str(url)) in self.par_url

    def recuperer(self, url) -> "Collecte":
        """Rend toujours une Collecte, jamais une exception — comme la
        collecte directe. Une URL absente du dépôt n'est pas une page vide :
        c'est une page qu'on n'a PAS lue, et elle le dit."""
        from .collecte_directe import Collecte
        from .base import maintenant

        l = self.par_url.get(mod_pages.normaliser(str(url)))
        if l is None:
            self.non_declarees.append(str(url))
            return Collecte(url=str(url), acces=Acces.JAMAIS_CONSULTEE,
                            consulte_le=maintenant(), provenance=self.provenance,
                            motif="absente du dépôt — aucune lecture n'a eu lieu")

        contenu = l.get("contenu") or l.get("texte") or ""
        motif = str(l.get("erreur") or l.get("motif") or "").strip()
        acces = _etat(l.get("acces") or l.get("statut"), contenu)
        if acces is not Acces.CONSULTEE:
            return Collecte(url=str(url), acces=acces, consulte_le=maintenant(),
                            provenance=self.provenance,
                            motif=motif or "accès impossible")
        return Collecte(url=str(url), acces=Acces.CONSULTEE,
                        octets=_en_page(contenu, l),
                        consulte_le=str(l.get("lu_le") or maintenant()),
                        provenance=self.provenance,
                        motif=motif or f"{len(contenu)} caractères reçus")


def _profil_par_defaut():
    """Le profil de lecture de page déjà déclaré. Sans lui, la veille ne sait
    pas extraire le TEXTE LISIBLE : elle ne compare alors que des octets, et
    toute page devient CONTENU ILLISIBLE — ce qui ferait passer une preuve
    parfaitement lisible pour un contenu qu'on n'a pas su lire."""
    import yaml
    chemin = Path(__file__).resolve().parent.parent / "sources" / "page_web.yaml"
    if not chemin.exists():
        return None
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))


def _veille(cx, depot, moteur, *, analyser=None, profil=None):
    """La veille existante, alimentée par le dépôt. Aucune règle ajoutée."""
    from .boucle import Veille
    return Veille(cx, depot.recuperer, analyser=analyser,
                  profil=profil if profil is not None else _profil_par_defaut(),
                  ontologie=moteur.ontologie, detecteur=moteur.roles)


def appliquer(cx, pages, moteur, *, fichier=None, profil=None) -> Bilan:
    """Fait entrer le contenu réel et laisse 7b qualifier — SANS analyser.

    Qualifier une page n'est pas créer une opportunité. Cette porte-là sert
    à établir ce que la page DIT ; l'analyse commerciale a sa propre entrée,
    `surveiller()`, et il faut la demander.

    Ne visite QUE les pages déclarées dans le fichier : une page candidate
    absente du dépôt n'a pas été lue, et rien ne doit laisser croire qu'on a
    essayé.
    """
    depot = Depot(pages)
    bilan = Bilan(fichier=fichier)
    bilan.lues = len(pages or [])

    connues = []
    for position, brute in enumerate(pages or [], start=1):
        l = brute if isinstance(brute, dict) else {}
        url = str(l.get("url") or "").strip()
        if not url:
            bilan.refus.append((position, URL_ABSENTE, None))
            continue
        contenu = l.get("contenu") or l.get("texte") or ""
        if len(contenu) > CONTENU_MAX:
            bilan.refus.append((position, "CONTENU HORS LIMITE", url))
            continue
        page = mod_pages.lire(cx, url)
        if page is None:
            bilan.inconnues += 1
            bilan.refus.append((position, PAGE_INCONNUE, url))
            continue
        connues.append(page)

    if not connues:
        return bilan

    trace = _veille(cx, depot, moteur, profil=profil).passer(connues)
    for passage in trace.passages:
        page = mod_pages.lire(cx, passage.url)
        if page is None:
            continue
        if page.acces is Acces.CONSULTEE:
            bilan.collectees += 1
            v = page.qualification.value
            bilan.qualifications[v] = bilan.qualifications.get(v, 0) + 1
            if page.statut is mod_pages.Statut.SURVEILLEE:
                bilan.promues += 1
        elif page.acces is Acces.ERREUR:
            bilan.erreurs += 1
        elif page.acces is Acces.NON_DISPONIBLE:
            bilan.non_disponibles += 1
    bilan.trace = trace
    return bilan


def surveiller(cx, chemin, moteur, *, analyser=None, profil=None,
               entreprise=None, limite=None):
    """UN CYCLE DE VEILLE COMPLET sur des pages lues ailleurs.

        page inchangée        → rien
        page modifiée         → qualification, puis analyse si commercial
        modifiée techniquement→ rien de commercial, et c'est dit
        erreur / indisponible → l'état précédent est conservé

    Ce n'est pas une nouvelle veille : c'est LA veille, avec une autre porte
    d'entrée. Les verdicts, la comparaison d'empreintes et la porte
    commerciale sont ceux des étapes précédentes, inchangés.
    """
    pages, fichier = charger(chemin)
    depot = Depot(pages)
    liste = [p for p in mod_pages.a_surveiller(cx, entreprise=entreprise,
                                               limite=limite, toutes=True)
             if p.url in depot]
    trace = _veille(cx, depot, moteur, analyser=analyser,
                    profil=profil).passer(liste)
    return trace, fichier, len(liste)


def importer(cx, chemin, moteur, *, profil=None) -> Bilan:
    """Charge un fichier de collecte et le fait entrer, SANS analyse.

    La porte de la QUALIFICATION. Pour un cycle de veille complet — avec
    analyse commerciale de ce qui a changé — c'est `surveiller()`.
    """
    pages, fichier = charger(chemin)
    return appliquer(cx, pages, moteur, fichier=fichier, profil=profil)


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
