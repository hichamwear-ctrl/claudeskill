"""CE QUE L'ADRESSE DIT — un INDICE, jamais une preuve.

    https://www.postnl.be/fr/offres-demploi-pour-sous-traitants/
                              └────────────────────────────┘
                              « offres emploi pour sous traitants »

Mesuré sur le premier jeu réel : trois des meilleures pistes portaient le
besoin DANS LEUR ADRESSE, et nulle part ailleurs dans ce qui avait été
importé. Le titre de l'une d'elles — « Travailler comme partenaire de
PostNL » — ne contenait pas le mot « sous-traitant ». Elle est ressortie
« aucun fait commercial observé ».

CE QUE CE MODULE FAIT, ET LA LIMITE QU'IL NE FRANCHIT PAS
=========================================================

Il rend l'adresse LISIBLE, et il dit si elle porte du vocabulaire du métier.
C'est tout.

    UN MOT DANS UNE URL N'EST PAS UNE PREUVE D'OPPORTUNITÉ.

Une adresse est écrite par celui qui tient le site, souvent des années avant
la page, parfois pour le référencement et pas pour dire la vérité. Elle ne
qualifie donc RIEN : elle sert à décider qu'on ira LIRE la page. La preuve
viendra du contenu, ou ne viendra pas.

Concrètement, un indice d'adresse peut :

    · rendre une piste visible dans la raison d'une page candidate ;
    · faire passer cette page EN TÊTE de la file de collecte.

Il ne peut pas :

    · créer une opportunité ;
    · qualifier une page ;
    · confirmer une identité ;
    · ajouter un point de score ;
    · écarter quoi que ce soit.

AUCUN NOM DE SITE N'EST ÉCRIT ICI
=================================

Pas de liste d'annuaires, pas de liste de concurrents, pas de liste de
journaux. Le vocabulaire vient de l'ontologie et du détecteur de rôle déjà
en place — les mêmes que pour le contenu. Une règle écrite pour un site
nommé ne vaudrait que pour lui.

L'ABSENCE D'INDICE NE REJETTE PERSONNE
======================================

Une adresse muette — « /fr/services/ », « /page/12 » — ne dit rien contre la
page. Elle dit seulement que l'adresse ne renseigne pas. La page reste
candidate exactement comme avant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlparse

# Ce qui n'est jamais un mot : les extensions de fichier, les marques de
# langue, et les segments techniques d'un site. Les retirer n'écarte aucune
# page — cela évite seulement de lire « html » comme un terme de métier.
BRUIT = {
    "html", "htm", "php", "asp", "aspx", "jsp", "cgi", "pdf", "xml", "json",
    "www", "index", "default", "page", "pages", "p", "id", "cat", "tag",
    "fr", "nl", "en", "de", "be", "com", "eu", "org", "net",
}

# Un mot d'une ou deux lettres ne porte pas de sens métier exploitable, et
# les identifiants numériques encore moins.
LONGUEUR_MINIMALE = 3

_DECOUPE = re.compile(r"[/\-_.+~,;:()\[\]%20\s]+")


@dataclass
class Indice:
    """Ce que l'adresse laisse voir. Un indice, et il se dit comme tel."""
    url: str
    mots: list = field(default_factory=list)
    pertinence: object = None          # la lecture de l'ontologie SUR L'ADRESSE
    familles: list = field(default_factory=list)
    role: object = None

    @property
    def texte(self) -> str:
        return " ".join(self.mots)

    @property
    def porteuse(self) -> bool:
        """L'adresse porte-t-elle du vocabulaire du métier ?

        Vrai ne veut pas dire « opportunité ». Vrai veut dire « il vaut la
        peine d'aller lire cette page », et rien d'autre.
        """
        return bool(self.familles) or self.role is not None

    def raison(self) -> str | None:
        """La phrase qui ira dans la raison de la page candidate.

        Elle dit d'où vient l'indice, pour qu'on ne le confonde jamais avec
        une lecture de contenu.
        """
        if not self.porteuse:
            return None
        quoi = ", ".join(self.familles) if self.familles else str(
            getattr(self.role, "value", self.role))
        return (f"INDICE D'ADRESSE — l'adresse contient « {self.texte[:60]} » "
                f"({quoi}). Ce n'est pas une preuve : la page n'a pas été lue.")


def mots(url) -> list[str]:
    """Les mots lisibles du CHEMIN. Le domaine n'en fait pas partie.

    Le domaine désigne l'entité qui sert la page — c'est le travail de
    `entreprises.domaine_de`, et le mêler au vocabulaire ferait lire
    « transport » dans « transport-exemple.be » comme si la page parlait de
    transport. Le chemin, lui, décrit la page.
    """
    chemin = urlparse(str(url or "")).path
    if not chemin:
        return []
    sortie = []
    for brut in _DECOUPE.split(unquote(chemin)):
        mot = brut.strip().lower()
        if (len(mot) < LONGUEUR_MINIMALE or mot in BRUIT or mot.isdigit()
                or mot in sortie):
            continue
        sortie.append(mot)
    return sortie


def lire(url, ontologie, detecteur) -> Indice:
    """Lit l'adresse avec LES MÊMES mécanismes que le contenu.

    Pas de vocabulaire parallèle : si l'ontologie ne reconnaît pas un terme
    dans une page, elle ne doit pas le reconnaître dans une adresse non plus.
    Deux lexiques finiraient par diverger, et l'on ne saurait plus lequel a
    décidé.
    """
    from .pertinence import Confiance, evaluer
    trouves = mots(url)
    indice = Indice(url=str(url or ""), mots=trouves)
    if not trouves:
        return indice
    p = evaluer(indice.texte, ontologie, detecteur)
    indice.pertinence = p
    if p.confiance is not Confiance.AUCUNE:
        indice.familles = list(getattr(p, "familles", []) or [])
        # Le rôle n'est retenu que s'il est POSITIF. Une contre-preuve lue
        # dans une adresse n'écarte rien : on ne refuse pas d'aller lire une
        # page parce que son adresse contient un mot qui nous déplaît.
        from .role import Role
        if getattr(p, "role", None) is Role.PRESTATAIRE:
            indice.role = p.role
    return indice


def porteuses(urls, ontologie, detecteur) -> list[Indice]:
    """Les adresses qui valent qu'on aille lire la page, dans l'ordre reçu.

    L'ordre n'est pas un classement de valeur : c'est l'ordre dans lequel on
    a rencontré les pages. Deux indices d'adresse ne se comparent pas.
    """
    return [i for i in (lire(u, ontologie, detecteur) for u in urls or [])
            if i.porteuse]


def rapport(indices) -> str:
    L = ["INDICES D'ADRESSE — ce que l'adresse laisse voir", "=" * 80, ""]
    porte = [i for i in indices if i.porteuse]
    L.append(f"  adresses lues            {len(list(indices))}")
    L.append(f"  adresses PORTEUSES       {len(porte)}")
    L.append("")
    for i in porte:
        L.append(f"  {i.url[:70]}")
        L.append(f"      « {i.texte[:64]} »")
        quoi = ", ".join(i.familles) if i.familles else getattr(
            i.role, "value", "")
        L.append(f"      {quoi}")
    L.append("")
    L.append("  UN MOT DANS UNE ADRESSE N'EST PAS UNE PREUVE. Ces indices")
    L.append("  servent à décider qu'on ira LIRE la page — jamais à la")
    L.append("  qualifier, jamais à créer une opportunité, jamais à noter.")
    return "\n".join(L)
