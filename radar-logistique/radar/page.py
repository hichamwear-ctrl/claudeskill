"""Lire une page dont on ne connaît pas la structure.

Tout le reste du radar lit des sources DÉCLARÉES : on sait où est le titre,
où est le montant, où est le statut. Une page d'entreprise n'offre pas ça.
C'est la zone la plus incertaine du produit, et donc celle qu'il faut mesurer
en premier.

Ce module ne devine rien. Il applique les pistes déclarées dans
`sources/page_web.yaml`, note pour CHAQUE champ quelle piste a répondu, et
laisse vide tout ce qu'aucune piste n'a trouvé. Un champ vide sort en INCONNU
avec la question à poser — pas en zéro, pas en « non ».

Ce qu'il rend :
    Lecture.champs        ce qui a été trouvé, avec la piste qui l'a trouvé
    Lecture.non_trouves   ce qui a été cherché sans succès
    Lecture.texte         le texte visible, scripts et styles exclus
    Lecture.variantes     quand deux pistes répondent différemment
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .extraction import analyser as analyser_html


@dataclass
class Piste:
    """D'où vient une valeur : quelle règle, appliquée à quoi."""
    champ: str
    valeur: str
    regle: str


@dataclass
class Lecture:
    texte: str = ""
    titre_document: str = ""
    champs: dict = field(default_factory=dict)          # champ -> valeur
    pistes: dict = field(default_factory=dict)          # champ -> Piste
    variantes: dict = field(default_factory=dict)       # champ -> [valeurs]
    non_trouves: list = field(default_factory=list)
    questions: dict = field(default_factory=dict)       # champ -> question
    liens: list = field(default_factory=list)
    longueur_html: int = 0
    longueur_texte: int = 0

    @property
    def densite(self) -> float:
        """Part du fichier qui est du texte lisible. Sur une page réelle
        moderne, elle tombe souvent sous 10 % : c'est mesurable, pas supposé."""
        return (self.longueur_texte / self.longueur_html) if self.longueur_html else 0.0


def _decrire(spec: dict) -> str:
    if spec.get("motif_texte"):
        return f"motif dans le texte : {spec['motif_texte'][:40]}"
    balise = spec.get("balise", "?")
    attrs = spec.get("attrs") or {}
    detail = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    quoi = spec.get("attribut", "texte")
    return f"<{balise}{' ' + detail if detail else ''}> → {quoi}"


def _appliquer(spec: dict, racine, texte: str):
    """Une piste, appliquée. Rend la valeur ou None. N'invente jamais."""
    motif = spec.get("motif_texte")
    if motif:
        m = re.search(motif, texte)
        return (m.group(0).strip() if m else None)

    balise = spec.get("balise")
    attrs = spec.get("attrs") or {}
    noeuds = ([racine] if spec.get("soi_meme") and balise == "html"
              else racine.trouver(balise, attrs))
    if spec.get("soi_meme") and balise:
        noeuds = [n for n in racine.trouver(balise)] or noeuds
    for n in noeuds:
        attribut = spec.get("attribut", "texte")
        v = n.texte() if attribut == "texte" else n.attrs.get(attribut)
        if not (v and str(v).strip()):
            continue
        v = str(v).strip()
        # Un href « mailto:contact@… » n'est pas une adresse : c'est un lien
        # vers une adresse. Le préfixe se déclare dans la source, il ne se
        # code pas ici — mesuré sur une vraie page, où le contact sortait
        # « mailto:me@kennethreitz.org » et arrivait tel quel sur la fiche.
        prefixe = spec.get("retirer_prefixe")
        if prefixe and v.lower().startswith(prefixe.lower()):
            v = v[len(prefixe):].strip()
        if spec.get("couper_a"):
            v = v.split(spec["couper_a"])[0].strip()
        if v:
            return v
    return None


def lire(html: str, profil: dict) -> Lecture:
    """Applique le profil de lecture générique à une page HTML brute."""
    racine = analyser_html(html or "")
    texte = racine.texte()
    lec = Lecture(texte=texte, longueur_html=len(html or ""), longueur_texte=len(texte))

    titres = racine.trouver("title")
    lec.titre_document = titres[0].texte() if titres else ""

    for a in racine.trouver("a"):
        href = a.attrs.get("href")
        if href:
            lec.liens.append({"href": href, "texte": a.texte()[:80]})

    for champ, pistes in (profil.get("lecture_generique") or {}).items():
        trouvees = []
        for spec in pistes or []:
            v = _appliquer(spec, racine, texte)
            if v:
                trouvees.append(Piste(champ, v, _decrire(spec)))
        if not trouvees:
            lec.non_trouves.append(champ)
            continue
        lec.champs[champ] = trouvees[0].valeur
        lec.pistes[champ] = trouvees[0]
        distinctes = []
        for p in trouvees[1:]:
            if p.valeur != trouvees[0].valeur and p.valeur not in distinctes:
                distinctes.append(p.valeur)
        if distinctes:
            lec.variantes[champ] = distinctes

    for champ, question in (profil.get("absences_attendues") or {}).items():
        if champ not in lec.champs and question != "—":
            lec.questions[champ] = question

    return lec
