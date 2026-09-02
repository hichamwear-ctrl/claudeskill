"""Correspondance déclarative entre les champs d'une source et le modèle interne.

Les clés ne sont JAMAIS écrites en dur dans le code : elles vivent dans un
fichier par source, et chacune porte son état de vérification. Sur le projet
précédent, la moitié des bugs d'extraction venaient de clés plausibles qui
n'existaient pas — l'antidote est de pouvoir les corriger sans toucher au code,
et de MESURER lesquelles répondent réellement.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def lire_chemin(payload, chemin: str):
    """Lit 'a.b[0].c' dans une réponse imbriquée. Renvoie None si absent."""
    courant = payload
    for morceau in chemin.split("."):
        if not morceau:
            return None
        indice = None
        if "[" in morceau and morceau.endswith("]"):
            morceau, brut = morceau[:morceau.index("[")], morceau[morceau.index("[") + 1:-1]
            try:
                indice = int(brut)
            except ValueError:
                return None
        if isinstance(courant, dict):
            courant = courant.get(morceau)
        else:
            return None
        if courant is None:
            return None
        if indice is not None:
            if not isinstance(courant, (list, tuple)) or len(courant) <= indice:
                return None
            courant = courant[indice]
    return courant


@dataclass
class Correspondance:
    source: str
    champs: dict[str, list[str]]              # champ interne -> chemins candidats
    verifie: bool = False                     # une vraie réponse a-t-elle confirmé ?
    couverture: dict[str, int] = field(default_factory=dict)

    @classmethod
    def depuis_config(cls, cfg: dict) -> "Correspondance":
        champs = {}
        for nom, spec in (cfg.get("champs") or {}).items():
            champs[nom] = [spec] if isinstance(spec, str) else list(spec)
        return cls(source=cfg.get("source", "?"), champs=champs,
                   verifie=bool(cfg.get("verifie", False)))

    def extraire(self, payload: dict) -> dict:
        """Premier chemin qui répond gagne. Aucun champ n'est fabriqué."""
        sortie = {}
        for nom, chemins in self.champs.items():
            for chemin in chemins:
                v = lire_chemin(payload, chemin)
                if v not in (None, "", []):
                    sortie[nom] = v
                    break
        return sortie

    def mesurer(self, payloads: list[dict]) -> dict[str, float]:
        """Taux de présence réel de chaque champ, sur de vraies réponses.

        C'est le recensement des clés — mesuré, pas deviné. Un champ à 0 %
        signale une clé inexistante, pas une source pauvre.
        """
        total = len(payloads) or 1
        taux = {}
        for nom, chemins in self.champs.items():
            trouves = sum(
                1 for p in payloads
                if any(lire_chemin(p, c) not in (None, "", []) for c in chemins)
            )
            taux[nom] = trouves / total
            self.couverture[nom] = trouves
        return taux
