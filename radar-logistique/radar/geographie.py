"""Le corridor, pas un filtre « Belgique ».

    COLLECTE EUROPE -> TRANSPORT -> DÉPÔT BELGE -> TRI -> LIVRAISON BELGIQUE

« Collecte NL + livraison BE » est le cœur du modèle. « Lyon -> Marseille » est
hors modèle même si c'est du transport routier parfaitement exécutable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Zone(Enum):
    CORRIDOR = "corridor"          # collecte hors BE + livraison BE : le modèle exact
    NATIONAL = "national"          # tout en Belgique
    A_VERIFIER = "A_VERIFIER"      # lieu absent ou illisible — jamais écarté
    HORS_ZONE = "hors_zone"        # ne touche pas la Belgique


@dataclass
class Resultat:
    zone: Zone
    raisons: list[str] = field(default_factory=list)
    corridor_eprouve: bool = False
    collecte: list[str] = field(default_factory=list)
    livraison: list[str] = field(default_factory=list)

    @property
    def compatible(self) -> bool:
        return self.zone is not Zone.HORS_ZONE


class Geographie:
    def __init__(self, config: dict):
        self.cfg = config
        self.ancrage = set(config.get("livraison_requise", ["BE"]))
        col = config.get("collecte_possible", {})
        self.prioritaires = set(col.get("prioritaires", []))
        self.acceptables = set(col.get("acceptables", []))
        self.eprouves = {(c["collecte"], c["livraison"])
                         for c in config.get("corridors_eprouves", [])}

    def evaluer(self, collecte: list[str], livraison: list[str]) -> Resultat:
        collecte = [p.upper() for p in (collecte or []) if p]
        livraison = [p.upper() for p in (livraison or []) if p]
        r = Resultat(Zone.A_VERIFIER, collecte=collecte, livraison=livraison)

        if not collecte and not livraison:
            r.raisons.append("aucun lieu publié — zone à vérifier, opportunité conservée")
            return r

        touche_be = bool(self.ancrage & (set(collecte) | set(livraison)))
        if not touche_be:
            r.zone = Zone.HORS_ZONE
            r.raisons.append(
                f"ni collecte ({', '.join(collecte) or '?'}) ni livraison "
                f"({', '.join(livraison) or '?'}) ne touche la Belgique — hors modèle")
            return r

        livre_be = bool(self.ancrage & set(livraison))
        etranger = [p for p in collecte if p not in self.ancrage]

        if livre_be and etranger:
            r.zone = Zone.CORRIDOR
            connus = [p for p in etranger if p in self.prioritaires or p in self.acceptables]
            proches = [p for p in etranger if p in self.prioritaires]
            r.raisons.append(
                f"corridor {'/'.join(etranger)} → BE : c'est exactement le modèle opérationnel")
            if proches:
                r.raisons.append(f"collecte en zone courte ({'/'.join(proches)}) — rotation quotidienne possible")
            elif not connus:
                r.raisons.append(f"collecte hors liste connue ({'/'.join(etranger)}) — faisabilité à vérifier")
            for pays in etranger:
                if any((pays, liv) in self.eprouves for liv in livraison):
                    r.corridor_eprouve = True
                    r.raisons.append(f"corridor {pays} → BE déjà exécuté — référence directe")
        elif livre_be:
            r.zone = Zone.NATIONAL
            r.raisons.append("livraison en Belgique, collecte belge ou non précisée")
        else:
            r.zone = Zone.A_VERIFIER
            r.raisons.append("lien avec la Belgique présent mais sens du flux à confirmer")
        return r
