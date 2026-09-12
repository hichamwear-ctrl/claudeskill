"""Correspondance d'ACTIVITÉ, pas de mots-clés.

L'acheteur ne dit pas « dernier kilomètre », il dit « distribution urbaine de
marchandises ». Le moteur cherche donc le vocabulaire des acheteurs, dans les
trois langues où paraissent les avis belges et européens, et le rattache à une
famille d'activité de l'entreprise.

Toute l'ontologie vit dans config/capacites.yaml : ajouter un synonyme ne
demande jamais de toucher au code.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def normaliser(texte: str) -> str:
    """Minuscule, sans accents, ponctuation réduite à des espaces."""
    if not texte:
        return ""
    plat = unicodedata.normalize("NFKD", str(texte))
    plat = "".join(c for c in plat if not unicodedata.combining(c)).lower()
    return " " + re.sub(r"[^a-z0-9]+", " ", plat).strip() + " "


# L'ORIGINE PAR DÉFAUT : quand une source ne dit pas où elle a lu un texte,
# ce texte décrit le besoin. L'inconnu est traité comme caractérisant — donc
# comme bloquant. Jamais l'inverse : une portée qu'on ignore ne doit pas
# servir à laisser passer une activité interdite.
ORIGINE_PAR_DEFAUT = "corps du document"

_MOT = re.compile(r"[^\W_]+", re.UNICODE)


def reperer(brut: str, terme: str):
    """Position exacte d'un terme dans le texte D'ORIGINE.

    On compare sans casse ni accents ; on restitue ce que la source a écrit,
    mot pour mot. Rend `(début, fin)` ou None.
    """
    jetons = [(normaliser(m.group(0)).strip(), m.start(), m.end())
              for m in _MOT.finditer(brut or "")]
    cible = [x for x in normaliser(terme).split() if x]
    if not cible or len(jetons) < len(cible):
        return None
    for i in range(len(jetons) - len(cible) + 1):
        if [j[0] for j in jetons[i:i + len(cible)]] == cible:
            return jetons[i][1], jetons[i + len(cible) - 1][2]
    return None


@dataclass
class Exclusion:
    """Une activité exclue, ET l'endroit où elle a été lue.

    Le terme seul ne décide de rien : « ADR » dans l'objet d'un marché est un
    empêchement juridique, « ADR » dans un lien de pied de page est le nom
    d'une page voisine. C'est la PORTÉE qui tranche, pas le mot.
    """
    terme: str
    origine: str
    extrait: str = ""
    bloquante: bool = True

    def __str__(self) -> str:
        etat = "bloquante" if self.bloquante else "écartée — ne caractérise pas le besoin"
        return f"« {self.terme} » [{self.origine}] {etat}"


@dataclass
class Correspondance:
    familles: list[str] = field(default_factory=list)
    preuves: dict[str, list[str]] = field(default_factory=dict)   # famille -> termes trouvés
    par_cpv: list[str] = field(default_factory=list)
    # Toutes les exclusions LUES, bloquantes ou non. Rien n'est effacé ici :
    # une exclusion écartée reste visible, elle change seulement de statut —
    # de verdict à question.
    exclusions_lues: list = field(default_factory=list)
    exigences_suggerees: list[str] = field(default_factory=list)
    # Un CPV générique de transport confirme le DOMAINE sans désigner de
    # spécialité. Il empêche un rejet pour « aucune prestation reconnue » sans
    # pour autant faire passer un marché de distribution pour du pharmaceutique.
    domaine_transport: bool = False
    preuve_domaine: str = ""

    @property
    def exclusions(self) -> list[str]:
        """Les seules qui condamnent : celles lues là où le besoin se décrit."""
        return [e.terme for e in self.exclusions_lues if e.bloquante]

    @property
    def reserves(self) -> list:
        """Observées, écartées, jamais supprimées."""
        return [e for e in self.exclusions_lues if not e.bloquante]

    @property
    def correspond(self) -> bool:
        return (bool(self.familles) or self.domaine_transport) and not self.exclusions


class Ontologie:
    def __init__(self, config: dict, familles_actives: list[str], familles_exclues=()):
        self.cfg = config
        self.actives = list(familles_actives)
        self.exclues = set(familles_exclues or ())
        self._termes = {}
        for nom, spec in config.get("familles", {}).items():
            mots = []
            for langue in ("fr", "nl", "en"):
                mots += [normaliser(m).strip() for m in spec.get("mots", {}).get(langue, [])]
            self._termes[nom] = [m for m in mots if m]
        # Un CPV déclaré par beaucoup de familles ne discrimine rien : « 60000000 »
        # confirme qu'on est dans le transport, il ne dit pas LEQUEL. Il ne peut
        # donc pas attribuer une famille à lui seul — sinon un simple marché de
        # distribution ressort comme pharmaceutique, alimentaire et volumineux.
        compte: dict[str, int] = {}
        for spec in config.get("familles", {}).values():
            for code in spec.get("cpv", []):
                compte[str(code)] = compte.get(str(code), 0) + 1
        self._cpv_generiques = {c for c, n in compte.items() if n > 2}

        # Le vocabulaire de DOMAINE : il confirme qu'on parle de transport ou
        # de logistique, sans nommer de spécialité — l'équivalent textuel d'un
        # CPV générique. Il existe pour que les sources sans CPV (une page
        # d'entreprise, un résultat de recherche, une bourse de fret) soient
        # traitées à égalité avec les marchés publics.
        self._domaine = []
        for langue in ("fr", "nl", "en"):
            self._domaine += [normaliser(m).strip()
                              for m in config.get("domaine", {}).get(langue, [])]
        self._domaine = [m for m in self._domaine if m]

        self._exclusions = []
        for langue in ("fr", "nl", "en"):
            self._exclusions += [normaliser(m).strip()
                                 for m in config.get("exclusions", {}).get(langue, [])]

        # Les EMPLACEMENTS qui ne caractérisent pas un besoin. Ce n'est pas une
        # liste de mots à ignorer — une liste de mots se tromperait au mot
        # suivant. C'est une liste de LIEUX : un menu, un pied de page et des
        # mentions légales décrivent le site, pas ce que l'acheteur demande.
        # Toute origine absente de cette liste caractérise et bloque.
        self._hors_besoin = {
            normaliser(o).strip()
            for o in (config.get("portee_exclusions", {}) or {}).get(
                "ne_caracterisent_pas", [])}

    def caracterise(self, origine: str) -> bool:
        """Un texte lu ICI décrit-il le besoin ? Par défaut : oui."""
        return normaliser(origine).strip() not in self._hors_besoin

    def analyser(self, texte: str, cpv: list[str] | None = None,
                 segments: list | None = None) -> Correspondance:
        plat = normaliser(texte)
        res = Correspondance()

        # ── Les exclusions, et ELLES SEULES, se lisent avec leur provenance ──
        #
        # `segments` est une VUE PORTÉE du même matériau, pas un matériau de
        # plus : les familles et le domaine continuent de lire exactement
        # `texte`, comme avant. Une source qui ne déclare aucun segment
        # retrouve le comportement d'avant, à l'octet près.
        vues = [(t, o) for t, o in (segments or []) if t] or [(texte, ORIGINE_PAR_DEFAUT)]
        deja = set()
        for brut, origine in vues:
            morceau = normaliser(brut)
            for terme in self._exclusions:
                if not terme or f" {terme} " not in morceau:
                    continue
                bloquante = self.caracterise(origine)
                # Le même terme vu bloquant ailleurs reste bloquant : on garde
                # les deux constats, et c'est le bloquant qui décide.
                if (terme, bloquante) in deja:
                    continue
                deja.add((terme, bloquante))
                bornes = reperer(brut, terme)
                extrait = ""
                if bornes:
                    d, f = bornes
                    extrait = ("…" if d > 70 else "") + brut[max(0, d - 70):f + 50].strip() \
                        + ("…" if f + 50 < len(brut) else "")
                res.exclusions_lues.append(Exclusion(
                    terme=terme, origine=origine, extrait=extrait, bloquante=bloquante))

        for famille in self.actives:
            if famille in self.exclues:
                continue
            trouves = [t for t in self._termes.get(famille, []) if t and f" {t} " in plat]
            spec = self.cfg["familles"].get(famille, {})
            declares = [str(c) for c in spec.get("cpv", [])]
            codes = [c for c in (cpv or []) if str(c) in declares]
            discriminants = [c for c in codes if str(c) not in self._cpv_generiques]
            # Un CPV générique ne suffit pas : il faut soit un terme du métier,
            # soit un code réellement spécifique à cette famille.
            if trouves or discriminants:
                res.familles.append(famille)
                res.preuves[famille] = trouves
                res.par_cpv += discriminants
                # Les exigences typiques d'une famille sont SUGGÉRÉES, jamais
                # présumées satisfaites : elles ressortiront en A_VERIFIER.
                res.exigences_suggerees += spec.get("exigences_typiques", [])

        # Deux chemins vers le domaine, strictement équivalents : un CPV
        # générique (marchés publics) OU le vocabulaire du métier (partout
        # ailleurs). Aucun des deux n'est meilleur que l'autre.
        if any(str(c) in self._cpv_generiques for c in (cpv or [])):
            res.domaine_transport = True
            res.preuve_domaine = "CPV générique de transport"
        else:
            mots = [t for t in self._domaine if f" {t} " in plat]
            if mots:
                res.domaine_transport = True
                res.preuve_domaine = f"vocabulaire du métier : « {mots[0]} »"

        res.exigences_suggerees = sorted(set(res.exigences_suggerees))
        return res
