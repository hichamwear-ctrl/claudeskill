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


def _codes(v):
    if v in (None, "", []):
        return []
    return [str(x).strip() for x in (v if isinstance(v, (list, tuple)) else [v]) if x]


def _exigences_de(champs: dict) -> dict:
    """Ne retient que ce qui vient d'un champ NORMÉ : une exigence structurée
    peut bloquer, une exigence lue en texte libre ne le peut jamais."""
    sortie = {}
    for cle, valeur in champs.items():
        if cle.startswith("exige_") and valeur:
            sortie[cle[len("exige_"):]] = valeur
        elif cle in ("surface_min_m2", "vehicules_min", "anciennete_min_annees",
                     "chiffre_affaires_min", "references_min") and valeur:
            sortie[cle] = valeur
    return sortie


def _lots_de(charge: dict, adaptateur) -> list:
    """Extrait les lots. Un marché sans lot déclaré en aura un : lui-même."""
    from .modele import LotBrut

    chemin = (adaptateur.champs.get("lots") or ["lots"])[0]
    brut = lire_chemin(charge, chemin)
    if not isinstance(brut, list):
        return []
    sortie = []
    for i, lot in enumerate(brut, 1):
        if not isinstance(lot, dict):
            continue
        champs = {c: lot.get(c) for c in lot}
        sortie.append(LotBrut(
            numero=str(lot.get("numero") or lot.get("lot-number") or i),
            intitule=str(lot.get("intitule") or lot.get("title") or ""),
            texte=str(lot.get("description") or lot.get("objet") or ""),
            cpv=_codes(lot.get("cpv") or lot.get("classification-cpv")),
            montant=lot.get("montant") or lot.get("estimated-value"),
            duree_mois=lot.get("duree_mois") or lot.get("duration-months"),
            exigences=_exigences_de(champs),
            pays_collecte=_liste(lot.get("pays_collecte")),
            pays_livraison=_liste(lot.get("pays_livraison"))))
    return sortie


def vers_opportunite(adaptateur, charge: dict, source: str, defauts: dict | None = None):
    """Traduit une réponse brute en Opportunite. SEUL endroit qui connaît la
    forme d'une source ; tout l'aval ignore d'où vient l'annonce."""
    from .modele import Opportunite

    c = adaptateur.extraire(charge)
    d = defauts or {}
    est_signal = bool(d.get("signal")) or bool(c.get("signal_code"))

    texte = " ".join(str(c.get(k, "")) for k in ("objet", "intitule", "lieu", "conditions"))
    return Opportunite(
        source=source,
        ref_source=str(c.get("identifiant") or charge.get("id") or ""),
        intitule=str(c.get("intitule") or "(sans intitulé)"),
        lots=_lots_de(charge, adaptateur),
        texte=texte,
        type_avis=c.get("type_avis") or d.get("type_avis"),
        est_signal=est_signal,
        signal_code=c.get("signal_code") or (c.get("type_avis") if est_signal else None),
        acheteur=c.get("acheteur"),
        contact=c.get("contact_email"),
        secteur_acheteur=c.get("secteur") or d.get("secteur"),
        echeance_brute=c.get("echeance"),
        publie_le=c.get("publie_le"),
        montant=c.get("montant"),
        devise=c.get("devise") or "EUR",
        duree_mois=c.get("duree_mois"),
        cadence=c.get("cadence"),
        date_demarrage=c.get("date_demarrage"),
        km_annuels=c.get("km_annuels"),
        distance_depot_km=c.get("distance_depot_km"),
        travail_nuit=c.get("travail_nuit"),
        travail_weekend=c.get("travail_weekend"),
        vehicules_requis=c.get("vehicules_requis"),
        chauffeurs_requis=c.get("chauffeurs_requis"),
        provenances=[{"source": source, "url": c.get("plateforme") or c.get("lien_documents"),
                      "consulte_le": (defauts or {}).get("consulte_le"),
                      "requete": (defauts or {}).get("requete")}],
        pays_collecte=_liste(c.get("pays_collecte")),
        pays_livraison=_liste(c.get("pays_livraison")) or _liste(c.get("pays")),
        lieu_texte=c.get("lieu"),
        cpv=_codes(c.get("cpv")),
        exigences=_exigences_de(c),
        exigences_texte=[t for t in (c.get("exigences_texte") or []) if t],
        lien_dossier=c.get("lien_documents") or c.get("plateforme"),
        lien_depot=c.get("plateforme"),
        plateforme=c.get("plateforme"),
        attribue=bool(c.get("attribue")),
        titulaire=c.get("titulaire"),
        attribue_le=c.get("attribue_le"),
        brut=charge,
    )
