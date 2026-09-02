"""Adaptateur de source : correspondance déclarative vers le modèle interne.

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
class Adaptateur:
    source: str
    champs: dict[str, list[str]]              # champ interne -> chemins candidats
    verifie: bool = False                     # une vraie réponse a-t-elle confirmé ?
    couverture: dict[str, int] = field(default_factory=dict)

    @classmethod
    def depuis_config(cls, cfg: dict) -> "Adaptateur":
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


# --------------------------------------------------------------- normalisation --

def _liste(v):
    if v in (None, "", []):
        return []
    return [str(x).strip().upper() for x in (v if isinstance(v, (list, tuple)) else [v]) if x]


def vers_opportunite(adaptateur, charge: dict, source: str, defauts: dict | None = None):
    """Traduit une réponse brute en Opportunite. C'est le SEUL endroit qui
    connaît la forme d'une source ; tout l'aval ignore d'où vient l'annonce."""
    from .modele import Nature, Opportunite

    c = adaptateur.extraire(charge)
    d = defauts or {}
    nature = Nature.SIGNAL_COMMERCIAL if d.get("nature") == "signal" else Nature.OPPORTUNITE_DIRECTE

    exigences = {}
    for cle, valeur in c.items():
        if cle.startswith("exige_") and valeur:
            exigences[cle[len("exige_"):]] = valeur
        elif cle in ("surface_min_m2", "vehicules_min", "anciennete_min_annees") and valeur:
            exigences[cle] = valeur

    texte = " ".join(str(c.get(k, "")) for k in ("objet", "intitule", "lieu", "conditions"))
    return Opportunite(
        source=source,
        ref_source=str(c.get("identifiant") or charge.get("id") or ""),
        intitule=str(c.get("intitule") or "(sans intitulé)"),
        nature=nature,
        texte=texte,
        type_avis=c.get("type_avis") or d.get("type_avis"),
        acheteur=c.get("acheteur"),
        contact=c.get("contact_email"),
        secteur_acheteur=c.get("secteur") or d.get("secteur"),
        echeance_brute=c.get("echeance"),
        publie_le=c.get("publie_le"),
        montant=c.get("montant"),
        devise=c.get("devise") or "EUR",
        duree_mois=c.get("duree_mois"),
        recurrent=c.get("recurrent"),
        pays_collecte=_liste(c.get("pays_collecte")),
        pays_livraison=_liste(c.get("pays_livraison")) or _liste(c.get("pays")),
        lieu_texte=c.get("lieu"),
        cpv=[str(x) for x in (c.get("cpv") if isinstance(c.get("cpv"), list) else [c.get("cpv")]) if x],
        exigences=exigences,
        exigences_texte=[t for t in (c.get("exigences_texte") or []) if t],
        lien_dossier=c.get("lien_documents"),
        lien_depot=c.get("plateforme"),
        plateforme=c.get("plateforme"),
        attribue=bool(c.get("attribue")),
        titulaire=c.get("titulaire"),
        attribue_le=c.get("attribue_le"),
        brut=charge,
    )
