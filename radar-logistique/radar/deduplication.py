"""Fusionner le même besoin vu sur plusieurs sources.

Un besoin peut paraître au BDA, sur TED, sur Google et sur le site de
l'entreprise. C'est UNE opportunité — mais elle garde toutes ses provenances.

Trois empreintes, parce qu'une seule ne suffisait pas :

  · STRICTE  acheteur + objet + échéance + montant + CPV.
             Fusionne deux avis publics. Ne fusionne PAS une page privée, qui
             n'a ni CPV ni montant : c'était le point faible de la version
             précédente.
  · URL      la même page vue deux fois, quelle que soit la source qui l'a
             trouvée.
  · BESOIN   organisation + signature de l'objet, tolérante à la formulation.
             C'est elle qui rapproche « Transport de colis pour la commune X »
             trouvé sur Google et l'avis BDA correspondant.

Deux opportunités sont la même dès qu'UNE empreinte correspond.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class Confiance(Enum):
    """Trois niveaux, parce que fusionner à tort fait DISPARAÎTRE un contrat.

    Deux fiches en double coûtent trente secondes de lecture. Une opportunité
    fusionnée à tort ne revient jamais.
    """
    CERTAIN = "CERTAIN"      # identifiant, référence ou URL identiques
    PROBABLE = "PROBABLE"    # organisation + objet + date très proches
    POSSIBLE = "POSSIBLE"    # similarité sémantique seule
    AUCUN = "AUCUN"

    @property
    def fusionne(self) -> bool:
        """Un doublon POSSIBLE n'est jamais fusionné : il est seulement relié."""
        return self in (Confiance.CERTAIN, Confiance.PROBABLE)


@dataclass
class Rapprochement:
    opportunite: object
    confiance: Confiance
    motif: str
    score: float = 0.0

# Mots qui ne portent pas de sens distinctif dans un intitulé de marché.
VIDES = {
    "de", "du", "des", "la", "le", "les", "un", "une", "et", "ou", "pour", "par",
    "sur", "dans", "avec", "aux", "au", "en", "a", "l", "d", "marche", "public",
    "appel", "offres", "offre", "avis", "lot", "lots", "cahier", "charges",
    "services", "service", "prestation", "prestations", "van", "de", "het", "en",
    "voor", "the", "of", "and", "for",
}

# Paramètres d'URL qui ne changent pas la page visée.
PARAMS_INUTILES = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                   "utm_content", "fbclid", "gclid", "ref", "source"}


def _plat(t) -> str:
    t = unicodedata.normalize("NFKD", str(t or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _hacher(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:20]


# ------------------------------------------------------------------ stricte --
def empreinte_stricte(opp) -> str:
    return _hacher(
        _plat(opp.acheteur),
        _plat(opp.intitule)[:120],
        str(opp.echeance_brute or ""),
        f"{float(opp.montant):.0f}" if opp.montant else "",
        (sorted(str(c) for c in (opp.cpv or []))[:1] or [""])[0])


# ---------------------------------------------------------------------- URL --
def canoniser_url(url: str | None) -> str | None:
    """Réduit une URL à ce qui identifie vraiment la page."""
    if not url:
        return None
    p = urlparse(str(url).strip())
    if not p.netloc:
        return None
    hote = p.netloc.lower().removeprefix("www.")
    chemin = (p.path or "/").rstrip("/") or "/"
    params = sorted(
        kv for kv in (p.query or "").split("&")
        if kv and kv.split("=", 1)[0].lower() not in PARAMS_INUTILES)
    return f"{hote}{chemin}" + ("?" + "&".join(params) if params else "")


def empreinte_url(opp) -> str | None:
    """La même page vue deux fois.

    Le numéro de lot entre dans l'empreinte : les lots d'un même marché
    partagent la page du marché parent, et sans cela ils fusionneraient tous en
    une seule opportunité — ce qui reviendrait à perdre les lots.
    """
    lot = getattr(opp, "lot_numero", None) or ""
    for candidat in (opp.lien_depot, opp.lien_dossier, opp.plateforme):
        c = canoniser_url(candidat)
        if c:
            return _hacher("url", c, lot)
    for p in opp.provenances or []:
        c = canoniser_url((p or {}).get("url") if isinstance(p, dict) else getattr(p, "url", None))
        if c:
            return _hacher("url", c, lot)
    return None


# ------------------------------------------------------------------- besoin --
def signature_objet(texte: str, garder: int = 6) -> str:
    """Les mots significatifs de l'objet, triés — insensible à la formulation.

    « Transport et distribution de colis » et « Distribution, transport de
    colis » produisent la même signature.
    """
    mots = [m for m in _plat(texte).split() if len(m) > 3 and m not in VIDES]
    # Les plus longs portent le sens ; le tri rend l'ordre indifférent.
    retenus = sorted(sorted(set(mots), key=len, reverse=True)[:garder])
    return " ".join(retenus)


# Un hachage exige une égalité EXACTE : deux formulations du même besoin qui
# diffèrent d'un mot ne se rapprochent jamais. Le besoin se compare donc par
# SIMILARITÉ, à l'intérieur d'une même organisation.
#
# Deux seuils, pas un : au-dessus du premier on fusionne en le traçant, entre
# les deux on relie sans fusionner.
SIMILARITE_PROBABLE = 0.75
SIMILARITE_POSSIBLE = 0.50


def mots_besoin(opp) -> set:
    return set(signature_objet(f"{opp.intitule} {opp.texte}", garder=8).split())


def organisation(opp) -> str:
    return _plat(opp.acheteur or opp.titulaire)


def similarite(a: set, b: set) -> float:
    """Jaccard : part de vocabulaire commun."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def meme_date(x, y) -> bool:
    """Deux marchés du même acheteur publiés à la même échéance sont
    probablement le même. Sans date des deux côtés, on ne conclut pas."""
    a, b = str(x.echeance_brute or ""), str(y.echeance_brute or "")
    return bool(a) and bool(b) and a[:10] == b[:10]


def meme_besoin(x, y) -> tuple[bool, float]:
    """Même organisation ET vocabulaire d'objet largement commun.

    L'organisation doit correspondre : sans elle, rapprocher deux « transport
    de colis » fusionnerait deux marchés de communes différentes.
    """
    # Deux lots distincts d'un même marché sont deux opportunités, jamais une.
    lx, ly = getattr(x, "lot_numero", None), getattr(y, "lot_numero", None)
    if (lx or ly) and lx != ly:
        return False, 0.0
    ox, oy = organisation(x), organisation(y)
    if not ox or not oy or ox != oy:
        return False, 0.0
    s = similarite(mots_besoin(x), mots_besoin(y))
    return s >= SIMILARITE_POSSIBLE, s


# ------------------------------------------------------------------ index --
def empreintes(opp) -> dict[str, str]:
    """Empreintes exactes. Le besoin ne s'y trouve pas : il se compare par
    similarité, pas par égalité."""
    sortie = {"stricte": empreinte_stricte(opp)}
    u = empreinte_url(opp)
    if u:
        sortie["url"] = u
    return sortie


def empreinte(opp) -> str:
    """Empreinte principale, celle qui sert de clé en base."""
    return empreinte_stricte(opp)


class Index:
    """Reconnaît un besoin déjà vu, par n'importe laquelle de ses empreintes."""

    def __init__(self):
        self._par_empreinte: dict[str, object] = {}
        self._par_organisation: dict[str, list] = {}

    def rapprocher(self, opp) -> Rapprochement | None:
        """Cherche un doublon et dit avec QUELLE confiance."""
        # 1. CERTAIN — même identifiant officiel, ou même page.
        for nom, valeur in empreintes(opp).items():
            trouve = self._par_empreinte.get(valeur)
            if trouve is not None:
                motif = ("référence officielle identique" if nom == "stricte"
                         else "URL identique")
                return Rapprochement(trouve, Confiance.CERTAIN, motif, 1.0)

        # 2. PROBABLE ou POSSIBLE — même organisation, objet proche.
        meilleur, meilleur_score = None, 0.0
        for candidat in self._par_organisation.get(organisation(opp), []):
            ok, score = meme_besoin(candidat, opp)
            if ok and score > meilleur_score:
                meilleur, meilleur_score = candidat, score
        if meilleur is None:
            return None

        if meilleur_score >= SIMILARITE_PROBABLE and meme_date(meilleur, opp):
            return Rapprochement(
                meilleur, Confiance.PROBABLE,
                f"même acheteur, objet à {meilleur_score:.0%}, même échéance",
                meilleur_score)
        return Rapprochement(
            meilleur, Confiance.POSSIBLE,
            f"même acheteur, objet à {meilleur_score:.0%} — NON FUSIONNÉ, à vérifier",
            meilleur_score)

    def chercher(self, opp):
        """Compatibilité : ne renvoie que ce qui doit réellement être fusionné."""
        r = self.rapprocher(opp)
        return r.opportunite if r and r.confiance.fusionne else None

    def ajouter(self, opp):
        for valeur in empreintes(opp).values():
            self._par_empreinte.setdefault(valeur, opp)
        org = organisation(opp)
        if org:
            self._par_organisation.setdefault(org, []).append(opp)
        return opp


# ----------------------------------------------------------------- fusion --
def fusionner(existante, nouvelle):
    """Complète les trous et CUMULE les provenances.

    N'écrase jamais une valeur déjà présente : la première source qui a publié
    fait foi. Mais une source qui apporte un champ manquant l'ajoute — c'est
    souvent Google qui donne le contact quand l'avis public ne le publie pas.
    """
    for champ in ("acheteur", "contact", "montant", "duree_mois", "cadence",
                  "lien_dossier", "lien_depot", "plateforme", "texte",
                  "secteur_acheteur", "date_demarrage", "km_annuels",
                  "distance_depot_km", "titulaire", "lieu_texte"):
        if not getattr(existante, champ, None) and getattr(nouvelle, champ, None):
            setattr(existante, champ, getattr(nouvelle, champ))

    for champ in ("pays_collecte", "pays_livraison", "cpv", "exigences_texte"):
        fusion = list(dict.fromkeys(
            list(getattr(existante, champ, []) or []) + list(getattr(nouvelle, champ, []) or [])))
        setattr(existante, champ, fusion)

    exi = dict(getattr(nouvelle, "exigences", {}) or {})
    exi.update(getattr(existante, "exigences", {}) or {})
    existante.exigences = exi

    # Les provenances s'additionnent : SOURCES : GOOGLE + BDA + SITE ENTREPRISE.
    vues = {(p.get("source"), p.get("url")) for p in (existante.provenances or [])
            if isinstance(p, dict)}
    for p in (nouvelle.provenances or []):
        p = p if isinstance(p, dict) else p.__dict__
        if (p.get("source"), p.get("url")) not in vues:
            existante.provenances.append(p)
            vues.add((p.get("source"), p.get("url")))
    return existante


def libelle_provenances(opp) -> str:
    """« SOURCES : GOOGLE + BDA » — ce que la fiche affiche."""
    noms = []
    for p in (opp.provenances or []):
        p = p if isinstance(p, dict) else p.__dict__
        nom = (p.get("source") or "?").upper()
        if nom not in noms:
            noms.append(nom)
    return " + ".join(noms) or (opp.source or "?").upper()
