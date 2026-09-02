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


@dataclass
class Correspondance:
    familles: list[str] = field(default_factory=list)
    preuves: dict[str, list[str]] = field(default_factory=dict)   # famille -> termes trouvés
    par_cpv: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    exigences_suggerees: list[str] = field(default_factory=list)

    @property
    def correspond(self) -> bool:
        return bool(self.familles) and not self.exclusions


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
        self._exclusions = []
        for langue in ("fr", "nl", "en"):
            self._exclusions += [normaliser(m).strip()
                                 for m in config.get("exclusions", {}).get(langue, [])]

    def analyser(self, texte: str, cpv: list[str] | None = None) -> Correspondance:
        plat = normaliser(texte)
        res = Correspondance()

        for terme in self._exclusions:
            if terme and f" {terme} " in plat:
                res.exclusions.append(terme)

        for famille in self.actives:
            if famille in self.exclues:
                continue
            trouves = [t for t in self._termes.get(famille, []) if t and f" {t} " in plat]
            spec = self.cfg["familles"].get(famille, {})
            codes = [c for c in (cpv or []) if c in spec.get("cpv", [])]
            if trouves or codes:
                res.familles.append(famille)
                res.preuves[famille] = trouves
                res.par_cpv += codes
                # Les exigences typiques d'une famille sont SUGGÉRÉES, jamais
                # présumées satisfaites : elles ressortiront en A_VERIFIER.
                res.exigences_suggerees += spec.get("exigences_typiques", [])

        res.exigences_suggerees = sorted(set(res.exigences_suggerees))
        return res
