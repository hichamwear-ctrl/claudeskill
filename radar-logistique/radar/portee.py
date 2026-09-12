"""LA PORTÉE D'UNE OBSERVATION — dans quelle unité de discours elle a été lue.

Le défaut que ce module corrige, mesuré sur une vraie page :

    « Une offre de livraison à domicile… »      position   934, bloc <h3> n°24
    « Lockers bientôt disponible »              position 2 109, bloc <p>  n°48

    → « « disponible » porte sur « offre » » → POSTULABLE

Deux phrases sans rapport, 1 175 caractères et 24 blocs l'une de l'autre, et
une preuve qui AFFIRME un lien syntaxique que personne n'a vérifié.

La cause n'est pas la règle qui les a combinées. C'est que la CO-OCCURRENCE
dans un texte aplati servait de substitut à la proximité syntaxique. Ce
substitut tient sur 150 caractères — la taille des textes du banc d'essai — et
ne vaut plus rien sur 3 500. Toute règle bâtie dessus se dégrade de la même
façon, y compris celles qu'on écrira demain : c'est pourquoi la réponse est un
mécanisme générique et non un correctif dans `procedure.py`.

────────────────────────────────────────────────────────────────────────────
LE PRINCIPE
────────────────────────────────────────────────────────────────────────────

  Deux fragments d'un même TEXTE LIBRE ne se combinent que s'ils partagent
  une unité de discours.

  Deux CHAMPS d'un même ENREGISTREMENT se combinent toujours : ce sont deux
  provenances d'un seul référent, pas deux fragments indépendants. C'est la
  corroboration du §7, et elle doit survivre intacte — « intitulé : marché en
  cours » et « corps : remise des offres » parlent bien du même marché.

  Une combinaison dont la portée n'est pas établie n'est pas une preuve :
  c'est une question. Elle s'affiche, elle ne conclut pas.

────────────────────────────────────────────────────────────────────────────
CE QU'EST UNE UNITÉ — mesurée, jamais décrétée
────────────────────────────────────────────────────────────────────────────

Trois niveaux, du plus fiable au plus grossier. On ne choisit pas : on prend
le meilleur que la source rende disponible.

  1. LE BLOC        quand la source sait le dire. Un <h3> et un <p> sont deux
                    blocs ; le DOM le sait déjà — la page Colis Privé en a 80.
  2. LA PHRASE      sinon. Une ponctuation forte ferme une unité.
  3. LA FENÊTRE     en dernier recours, quand le texte n'a ni bloc ni
                    ponctuation. `FENETRE` reprend la valeur que
                    `procedure._nie()` et `procedure._porte()` emploient déjà
                    depuis toujours pour juger qu'une négation « porte sur »
                    un mot. Ces deux fonctions sont la référence de ce module :
                    elles étaient déjà locales, elles ne changent pas.

Aucun seuil de longueur n'est introduit, et aucun mot n'est listé : ce module
ne sait pas ce qu'est un pied de page, ni ce qu'est « ADR ». Il ne sait dire
qu'une chose — « ces deux observations viennent-elles du même endroit ? »
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .activite import normaliser

# La même valeur que `procedure.FENETRE_NEGATION`, et pour la même raison :
# c'est la distance en deçà de laquelle deux mots d'un texte sans structure
# peuvent raisonnablement se rapporter l'un à l'autre. Elle n'est pas un
# seuil de défiance sur la longueur du document — elle ne sert que lorsque
# AUCUNE structure n'est disponible.
FENETRE = 60

# Une ponctuation forte, ou un passage à la ligne, ferme une unité.
_FIN_DE_PHRASE = re.compile(r"[.!?;:…]+[\s\"»)]*|\n+")


@dataclass(frozen=True)
class Unite:
    """Un morceau de discours, et ses bornes dans le texte normalisé."""
    rang: int
    debut: int
    fin: int
    brut: str = ""          # ce que la source a écrit, mot pour mot
    champ: str = ""         # le CHAMP d'où vient cette unité
    # LA ZONE de la page où ce morceau a été lu — « pied de page »,
    # « navigation »… Vide quand la source ne sait pas le dire : inconnue,
    # jamais présumée.
    zone: str = ""
    # QUEL NIVEAU a produit cette unité — bloc, phrase ou fenêtre. Une
    # relation plus large que l'unité (voir `meme_ensemble`) n'a de sens
    # qu'entre phrases : deux blocs voisins sont deux paragraphes.
    niveau: str = ""

    def contient(self, position: int) -> bool:
        return self.debut <= position < self.fin

    @property
    def extrait(self) -> str:
        t = " ".join(self.brut.split())
        return t if len(t) <= 160 else t[:157] + "…"


def _phrases(texte: str) -> list[str]:
    """Découpe en phrases SANS rien perdre : la ponctuation reste dans sa
    phrase, et la concaténation des morceaux redonne le texte d'origine."""
    morceaux, depart = [], 0
    for m in _FIN_DE_PHRASE.finditer(texte or ""):
        morceaux.append(texte[depart:m.end()])
        depart = m.end()
    if depart < len(texte or ""):
        morceaux.append(texte[depart:])
    return [m for m in morceaux if m.strip()]


def positions(plat: str, expression: str) -> list[int]:
    """Toutes les positions d'une expression dans un texte normalisé.

    `plat` est encadré d'espaces et ses mots séparés par un espace unique :
    chercher « espace + expression + espace » revient à chercher des mots
    entiers, exactement comme le font déjà les règles existantes.
    """
    sortie, depart = [], 0
    cible = f" {expression} "
    while True:
        i = plat.find(cible, depart)
        if i < 0:
            return sortie
        sortie.append(i + 1)
        depart = i + 1


@dataclass
class Portee:
    """Le texte normalisé, et la carte de ses unités de discours."""
    plat: str = " "
    unites: list = field(default_factory=list)
    structure: str = "fenêtre"      # blocs · phrases · fenêtre
    fenetre: int = FENETRE
    # `compatibles(champ_a, champ_b) -> bool`, FOURNI PAR L'APPELANT.
    #
    # La portée sait OÙ une preuve existe. Elle ne sait pas si deux
    # provenances décrivent le même objet — cela dépend du modèle, et le
    # modèle n'a pas sa place ici. Sans réponse, elle refuse : l'inconnu ne
    # corrobore pas.
    compatibles: object = None

    @classmethod
    def composer(cls, champs, fenetre: int = FENETRE, compatibles=None) -> "Portee":
        """Plusieurs CHAMPS d'un même enregistrement, concaténés.

        `champs` : [(nom, texte, blocs)]. Le texte analysé est leur
        concaténation — c'est ce que les appelants construisent déjà — mais
        chaque unité sait de quel champ elle vient, et deux champs se
        corroborent TOUJOURS : ce sont deux provenances d'un seul référent.
        C'est la distinction demandée, et elle vit ici.
        """
        entier = " ".join(str(t) for _, t, _ in champs if str(t or "").strip())
        plat = normaliser(entier)
        unites, curseur, rang = [], 1, 0
        for nom, texte, blocs in champs:
            if not str(texte or "").strip():
                continue
            partielle = cls.construire(texte, blocs, fenetre)
            noyau = normaliser(texte).strip()
            base = plat.find(noyau, curseur)
            if base < 0:
                continue
            for u in partielle.unites:
                unites.append(Unite(rang, base + u.debut - 1, base + u.fin - 1,
                                    u.brut, nom, u.zone, u.niveau))
                rang += 1
            curseur = base + len(noyau)
        if not unites:
            return cls.construire(entier, None, fenetre)
        structure = "champs"
        return cls(plat=plat, unites=unites, structure=structure, fenetre=fenetre,
                   compatibles=compatibles)

    @staticmethod
    def _denuder(morceaux):
        """Accepte des morceaux nus ou portés : « texte » ou (texte, zone)."""
        sortie = []
        for m in morceaux or []:
            if isinstance(m, (list, tuple)) and len(m) >= 2:
                sortie.append((str(m[0]), str(m[1] or "")))
            elif str(m).strip():
                sortie.append((str(m), ""))
        return sortie

    @classmethod
    def _apparier(cls, plat: str, morceaux) -> list:
        """Les morceaux qui se retrouvent RÉELLEMENT dans le texte, dans l'ordre.

        Le critère d'appariement est littéral : le noyau normalisé du morceau
        doit figurer tel quel dans le texte normalisé, à partir du curseur.
        Un morceau qui ne s'y retrouve pas décrit un AUTRE texte — il n'est
        pas une unité, et il ne doit pas non plus faire croire qu'on connaît
        le découpage.
        """
        apparies, curseur = [], 1
        for brut, zone in cls._denuder(morceaux):
            noyau = normaliser(brut).strip()
            if not noyau:
                continue
            i = plat.find(noyau, curseur)
            if i < 0:
                continue
            apparies.append((i, i + len(noyau), str(brut), zone))
            curseur = i + len(noyau)
        return apparies

    @classmethod
    def construire(cls, texte: str, blocs=None, fenetre: int = FENETRE) -> "Portee":
        plat = normaliser(texte)
        phrases = cls._apparier(plat, _phrases(texte or ""))
        blocs_apparies = cls._apparier(plat, cls._denuder(blocs))

        # DÉCLARER « blocs » SANS QU'AUCUN BLOC N'AIT ÉTÉ RETROUVÉ rendait le
        # texte entier opaque : une seule unité, et tout s'y corroborait — le
        # comportement d'avant ce module, silencieusement. Des blocs qui ne
        # correspondent pas au texte sont donc ignorés, et l'on retombe sur le
        # niveau suivant. Fournir de mauvais blocs ne doit jamais être PIRE
        # que n'en fournir aucun.
        if blocs_apparies:
            spans = cls._completer(plat, blocs_apparies, phrases)
            structure = "blocs"
            ancres = {(d, f) for d, f, _, _ in blocs_apparies}
            niveaux = ["bloc" if (d, f) in ancres else "phrase" for d, f, _, _ in spans]
        elif len(phrases) > 1:
            spans, structure = phrases, "phrases"
            niveaux = ["phrase"] * len(spans)
        else:
            spans, structure = phrases, "fenêtre"
            niveaux = ["fenêtre"] * len(spans)

        unites = [Unite(rang, d, f, brut, "", zone, niveaux[rang])
                  for rang, (d, f, brut, zone) in enumerate(spans)]
        if not unites:
            unites = [Unite(0, 0, len(plat), str(texte or ""))]
        return cls(plat=plat, unites=unites, structure=structure, fenetre=fenetre)

    @staticmethod
    def _completer(plat: str, spans: list, secours: list) -> list:
        """Aucune région ne reste opaque.

        Ce qu'aucun morceau ne revendique n'est pas laissé d'un seul tenant :
        le niveau suivant le découpe. Sans cela, un seul bloc apparié sur
        trois laissait 1 400 caractères dans une même unité, où deux mots
        sans rapport se corroboraient de nouveau.
        """
        complet, curseur = [], 1
        for d, f, brut, zone in list(spans) + [(len(plat) - 1, len(plat) - 1, "", "")]:
            if plat[curseur:d].strip():
                dedans = [(a, b, t, z) for a, b, t, z in secours if a >= curseur and b <= d]
                complet += dedans or [(curseur, d, "", "")]
            if brut:
                complet.append((d, f, brut, zone))
            curseur = max(curseur, f)
        return complet

    # ------------------------------------------------------------------ lire
    def unite_de(self, position: int):
        for u in self.unites:
            if u.contient(position):
                return u
        return None

    def meme_unite(self, a: int, b: int) -> bool:
        """Ces deux observations viennent-elles du même endroit ?

        Sans structure lisible, on retombe sur la fenêtre — la même que celle
        qui sert déjà à dire qu'une négation porte sur un mot.
        """
        ua, ub = self.unite_de(a), self.unite_de(b)
        # DEUX PROVENANCES DIFFÉRENTES : ce module NE TRANCHE PAS.
        #
        # « cohabiter dans un enregistrement » n'est pas « décrire le même
        # objet ». Le titre d'un lot et le corps de son marché cohabitent et
        # décrivent deux choses ; une méta-description décrit la page et non
        # le besoin. Seule la couche qui connaît le modèle peut le dire, et
        # c'est elle qui fournit `compatibles`. Sans elle : non.
        if ua is not None and ub is not None and ua.champ != ub.champ:
            return bool(self.compatibles) and bool(self.compatibles(ua.champ, ub.champ))
        if self.structure == "fenêtre":
            return abs(a - b) <= self.fenetre
        if ua is None or ub is None:
            return abs(a - b) <= self.fenetre
        return ua.rang == ub.rang

    def meme_ensemble(self, a: int, b: int) -> bool:
        """Une granularité plus LARGE que l'unité, pour les relations qui le
        sont aussi.

        Toutes les relations ne vivent pas dans la phrase. « Cette formation
        porte sur ces moyens-là » est une relation de PARAGRAPHE : mesuré sur
        une fixture réelle, « des véhicules utilitaires et du personnel de
        terrain » et « une formation complète de trois semaines est assurée »
        sont deux phrases consécutives d'un même paragraphe, et exiger la
        même phrase fermait un chemin légitime.

        Quand la source donne les blocs, le paragraphe EST le bloc. Quand
        elle n'a que des phrases, le paragraphe n'est pas représentable : la
        contiguïté en tient lieu — deux phrases voisines appartiennent au
        même paragraphe tant que rien ne dit le contraire. Ce n'est pas un
        seuil, c'est le niveau structurel immédiatement au-dessus.
        """
        if self.meme_unite(a, b):
            return True
        ua, ub = self.unite_de(a), self.unite_de(b)
        if ua is None or ub is None:
            return False
        # Deux BLOCS voisins sont deux paragraphes : ils ne se rejoignent pas.
        # Deux PHRASES voisines du même champ sont un paragraphe qu'aucune
        # source n'a su nous donner.
        if ua.champ != ub.champ or "phrase" not in (ua.niveau, ub.niveau):
            return False
        return abs(ua.rang - ub.rang) == 1

    def situer(self, position: int) -> str:
        """Où, en clair — pour que la preuve se relise."""
        u = self.unite_de(position)
        if u is None:
            return "position inconnue"
        if u.champ:
            return f"{u.champ}, unité {u.rang + 1}"
        return {"blocs": f"bloc {u.rang + 1}",
                "phrases": f"phrase {u.rang + 1}",
                "fenêtre": "texte sans structure"}[self.structure]

    def extrait(self, position: int) -> str:
        """Ce que la source a écrit là — jamais une reconstruction."""
        u = self.unite_de(position)
        if u is not None and u.brut:
            return u.extrait
        debut = max(0, position - self.fenetre)
        return self.plat[debut:position + self.fenetre].strip()


def appariees(portee: Portee, gauche: list[str], droite: list[str]):
    """La première paire d'expressions qui partagent une unité.

    Rend `(expr_gauche, pos_gauche, expr_droite, pos_droite)`, ou None si
    aucune paire ne se trouve au même endroit : les deux mots existent, mais
    rien ne permet de dire qu'ils parlent de la même chose.
    """
    for g in gauche:
        for pg in positions(portee.plat, g):
            for d in droite:
                for pd in positions(portee.plat, d):
                    if portee.meme_unite(pg, pd):
                        return g, pg, d, pd
    return None
