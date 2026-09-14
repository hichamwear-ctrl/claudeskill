"""Les 55 liens d'une page ne sont pas 55 pages à surveiller.

    PAGE CONSULTÉE → LIENS EXTRAITS → FILTRAGE → PAGES CANDIDATES

Ce module filtre. Il ne promeut rien, il ne surveille rien, il ne crée aucune
entreprise. Il dit seulement : « ce lien mérite d'être RETENU comme candidat ».

TROIS PRIORITÉS, ET AUCUNE N'OUVRE LE WEB ENTIER
================================================

    P1  même domaine que la page consultée
        On est chez l'entreprise qu'on surveille. C'est le périmètre naturel.

    P2  autre domaine, mais le lien porte un indice FORT selon les mécanismes
        existants (voir radar/pertinence.py, qui interroge l'ontologie et le
        détecteur de rôle — aucune taxonomie parallèle n'est créée ici).

    P3  autre domaine SANS indice fort, mais le domaine correspond à une
        entreprise DÉJÀ CONNUE du registre — un titulaire, un partenaire.

Tout le reste est ignoré. Un lien vers un réseau social, un CMS, une régie
publicitaire ou un site de presse n'entre pas : suivre les liens sans limite
reviendrait à explorer le web au hasard depuis une page, et le registre
deviendrait inexploitable.

CE QUE CE MODULE NE FAIT JAMAIS
===============================

Il ne transforme pas un lien en entreprise. Un domaine n'est pas une raison
sociale, et inventer un nom polluerait le registre pour toujours.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlparse

from .pertinence import Confiance, evaluer

# Ce qui ne pointe jamais vers un besoin : ni une page, ni un site d'entreprise.
SCHEMAS_IGNORES = ("mailto:", "tel:", "javascript:", "data:", "#")
EXTENSIONS_IGNOREES = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
                       ".zip", ".mp4", ".mp3", ".css", ".js", ".ico", ".xml")

P1_MEME_DOMAINE = "MÊME DOMAINE"
P2_INDICE_FORT = "INDICE FORT"
P3_ENTREPRISE_CONNUE = "ENTREPRISE CONNUE"


@dataclass
class Candidat:
    """Un lien retenu — et POURQUOI il l'a été."""
    url: str
    libelle: str = ""
    priorite: str = P1_MEME_DOMAINE
    pertinence: object = None       # Pertinence, si elle a été évaluée

    @property
    def promouvable(self) -> bool:
        return bool(self.pertinence and self.pertinence.promouvoir)

    def raison(self) -> str:
        base = f"lien retenu — {self.priorite}"
        if self.libelle:
            base += f" — « {self.libelle[:48]} »"
        return base


def _absolue(href: str, base: str) -> str | None:
    """Une URL utilisable, ou rien. Jamais une URL reconstruite au jugé."""
    h = (href or "").strip()
    if not h or h.startswith(SCHEMAS_IGNORES):
        return None
    url = urldefrag(urljoin(base, h))[0]
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        return None
    if p.path.lower().endswith(EXTENSIONS_IGNOREES):
        return None
    return url


def _hote(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _mots_de_l_url(url: str) -> str:
    """Le chemin d'une URL est du texte : « /devenir-partenaire-livraison »
    dit quelque chose. On le rend lisible pour que l'ontologie le lise, sans
    inventer de correspondance."""
    chemin = urlparse(url).path or ""
    return chemin.replace("-", " ").replace("_", " ").replace("/", " ").strip()


def selectionner(liens, base_url: str, ontologie, detecteur, *,
                 domaines_connus=(), limite: int | None = None) -> list[Candidat]:
    """Les liens RETENUS, sans doublon, dans l'ordre de la page.

    `liens` : [{"href": ..., "texte": ...}] tel que radar/page.py les rend.
    `domaines_connus` : les domaines des entreprises déjà au registre.
    """
    hote_base = _hote(base_url)
    connus = {str(d).lower().removeprefix("www.") for d in domaines_connus if d}
    vus, sortie = set(), []

    for lien in liens or []:
        href = lien.get("href") if isinstance(lien, dict) else getattr(lien, "href", None)
        libelle = (lien.get("texte") if isinstance(lien, dict)
                   else getattr(lien, "texte", "")) or ""
        url = _absolue(href, base_url)
        if not url or url in vus:
            continue
        vus.add(url)
        if url.rstrip("/") == base_url.rstrip("/"):
            continue                               # la page elle-même

        hote = _hote(url)
        # Le libellé du lien ET les mots du chemin : deux façons de dire la
        # même chose, lues par le MÊME mécanisme.
        texte = f"{libelle} {_mots_de_l_url(url)}".strip()
        pert = evaluer(texte, ontologie, detecteur)

        if hote == hote_base:
            sortie.append(Candidat(url, libelle, P1_MEME_DOMAINE, pert))
        elif pert.confiance is Confiance.FORTE or pert.familles:
            # ANOMALIE A7. RETENIR N'EST PAS PROMOUVOIR, et les deux décisions
            # se prennent à deux endroits : ici on GARDE une adresse, et
            # `promouvable` — qui lit la confiance, pas cette condition —
            # décide seul si elle passe en surveillance. Une candidate ajoutée
            # ici ne peut donc jamais être promue automatiquement.
            #
            # Depuis que le vocabulaire a cessé d'être une preuve positive, un
            # lien externe qui nomme une SPÉCIALITÉ du métier n'entrait plus du
            # tout. Mesuré sur les quatre pages réelles archivées :
            #     aujourd'hui                      230 candidates
            #     + toute reconnaissance de DOMAINE 240  (+10, dont 8 de bruit :
            #       github.com/pypi/warehouse, depot.dev, deux pages de login)
            #     + FAMILLE reconnue seulement      232  (+2, aucun bruit)
            #
            # C'est donc la FAMILLE qui est lue, et pas le domaine générique.
            # La distinction existe déjà : radar/activite.py documente le
            # domaine comme l'équivalent d'un CPV générique, qui confirme
            # qu'on parle de transport sans désigner de spécialité.
            sortie.append(Candidat(url, libelle, P2_INDICE_FORT, pert))
        elif hote in connus:
            sortie.append(Candidat(url, libelle, P3_ENTREPRISE_CONNUE, pert))
        # sinon : ignoré, et c'est le cas le plus fréquent.

        if limite and len(sortie) >= limite:
            break
    return sortie


def retenus(candidats) -> list[Candidat]:
    """Ceux qui portent un indice FORT — les seuls promouvables."""
    return [c for c in candidats if c.promouvable]
