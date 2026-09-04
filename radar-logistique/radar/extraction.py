"""Extraction depuis une page HTML, avec des sélecteurs DÉCLARÉS en YAML.

Beaucoup de portails de marchés publics — le BDA belge en fait partie — ne
publient pas d'API : il faut lire la page. Les sélecteurs vivent donc dans le
fichier de source, jamais dans le code, exactement comme les chemins JSON.

Bibliothèque standard uniquement : `html.parser`, pas de dépendance ajoutée.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

AUTO_FERMANTES = {"br", "img", "input", "meta", "link", "hr", "source"}

# Le contenu de ces balises n'est PAS du texte de page. Sur une vraie page, un
# bloc <script> de suivi publicitaire pèse dix fois le texte visible : le
# ramasser revient à faire analyser du JavaScript au moteur sémantique.
NON_TEXTUELLES = {"script", "style", "noscript", "template", "svg"}


@dataclass
class Noeud:
    balise: str
    attrs: dict = field(default_factory=dict)
    enfants: list = field(default_factory=list)
    parent: object = None
    texte_direct: str = ""

    def texte(self) -> str:
        morceaux = [self.texte_direct] + [e.texte() for e in self.enfants]
        return re.sub(r"\s+", " ", " ".join(m for m in morceaux if m)).strip()

    def descendants(self):
        for e in self.enfants:
            yield e
            yield from e.descendants()

    def trouver(self, balise=None, attrs=None) -> list:
        """Tous les descendants correspondant à la balise et aux attributs."""
        sortie = []
        for n in self.descendants():
            if balise and n.balise != balise:
                continue
            if attrs and not all(
                    v.lower() in (n.attrs.get(k) or "").lower() for k, v in attrs.items()):
                continue
            sortie.append(n)
        return sortie


class _Constructeur(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.racine = Noeud("#racine")
        self.pile = [self.racine]

    def handle_starttag(self, tag, attrs):
        n = Noeud(tag, dict(attrs), parent=self.pile[-1])
        self.pile[-1].enfants.append(n)
        if tag not in AUTO_FERMANTES:
            self.pile.append(n)

    def handle_startendtag(self, tag, attrs):
        self.pile[-1].enfants.append(Noeud(tag, dict(attrs), parent=self.pile[-1]))

    def handle_endtag(self, tag):
        for i in range(len(self.pile) - 1, 0, -1):
            if self.pile[i].balise == tag:
                del self.pile[i:]
                return

    def handle_data(self, data):
        if not data.strip():
            return
        if any(n.balise in NON_TEXTUELLES for n in self.pile):
            return
        self.pile[-1].texte_direct += " " + data.strip()


def analyser(html: str) -> Noeud:
    c = _Constructeur()
    c.feed(html)
    return c.racine


def _valeur(noeud: Noeud, spec: dict, base_url: str | None = None):
    """Lit un champ dans un nœud selon sa déclaration."""
    if noeud is None:
        return None
    cibles = ([noeud] if spec.get("soi_meme") else
              noeud.trouver(spec.get("balise"), spec.get("attrs")))
    indice = spec.get("indice", 0)
    if len(cibles) <= indice:
        return None
    cible = cibles[indice]
    attribut = spec.get("attribut", "texte")
    if attribut == "texte":
        valeur = cible.texte()
    else:
        valeur = cible.attrs.get(attribut)
    if valeur and spec.get("motif"):
        m = re.search(spec["motif"], valeur)
        valeur = m.group(1) if m and m.groups() else (m.group(0) if m else None)
    if valeur and attribut == "href" and base_url and valeur.startswith("/"):
        from urllib.parse import urljoin
        valeur = urljoin(base_url, valeur)
    return valeur or None


def extraire(html: str, config: dict, base_url: str | None = None) -> list[dict]:
    """Applique la déclaration `navigation` d'un fichier de source.

    Aucun champ n'est fabriqué : un sélecteur qui ne trouve rien laisse le champ
    absent, et c'est `recenser` qui mesurera ensuite lesquels répondent vraiment.
    """
    nav = config.get("navigation") or {}
    racine = analyser(html)

    conteneur = racine
    spec_c = nav.get("conteneur")
    if spec_c:
        trouves = racine.trouver(spec_c.get("balise"), spec_c.get("attrs"))
        if not trouves:
            return []
        conteneur = trouves[0]

    spec_l = nav.get("ligne") or {}
    lignes = conteneur.trouver(spec_l.get("balise"), spec_l.get("attrs"))

    sortie = []
    for ligne in lignes:
        enregistrement = {}
        for nom, spec in (nav.get("champs") or {}).items():
            v = _valeur(ligne, spec, base_url)
            if v not in (None, ""):
                enregistrement[nom] = v
        if enregistrement:
            sortie.append(enregistrement)
    return sortie
