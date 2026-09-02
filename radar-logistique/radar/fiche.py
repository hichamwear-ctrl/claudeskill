"""La fiche : comprendre l'opportunité en quelques secondes.

Un champ absent est écrit A_VERIFIER ou NON PUBLIÉ — jamais comblé par une
valeur plausible. Une fiche qui invente un montant est pire qu'une fiche
incomplète.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .modele import Nature

ABSENT = "NON PUBLIÉ"


def _ou(v, defaut=ABSENT):
    return defaut if v in (None, "", [], "A_VERIFIER") else v


def _montant(v, devise="EUR"):
    if v in (None, "", 0):
        return ABSENT
    try:
        return f"{float(v):,.0f} {devise}".replace(",", " ")
    except (TypeError, ValueError):
        return str(v)


@dataclass
class Fiche:
    statut_emoji: str
    statut: str
    titre: str
    nature: Nature
    nature_libelle: str
    acheteur: str | None
    secteur: str | None
    contact: str | None
    collecte: list[str] = field(default_factory=list)
    livraison: list[str] = field(default_factory=list)
    lieu_texte: str | None = None
    echeance: str = ABSENT
    jours_restants: int | None = None
    montant: float | None = None
    devise: str = "EUR"
    duree_mois: int | None = None
    pourquoi: list[str] = field(default_factory=list)
    a_verifier: list[str] = field(default_factory=list)
    score: int = 0
    detail_score: list[str] = field(default_factory=list)
    lien: str | None = None
    plateforme: str | None = None
    source: str = ""
    reference: str = ""

    def en_texte(self, avec_detail_score: bool = False) -> str:
        L = [f"{self.statut_emoji} {self.nature_libelle.upper()} — {self.titre}", ""]
        L.append(f"Acheteur      : {_ou(self.acheteur)}")
        L.append(f"Type          : {_ou(self.secteur, 'A_VERIFIER')}")
        if self.collecte:
            L.append(f"Collecte      : {', '.join(self.collecte)}")
        if self.livraison:
            L.append(f"Livraison     : {', '.join(self.livraison)}")
        elif self.lieu_texte:
            L.append(f"Localisation  : {self.lieu_texte}")
        reste = f"  ({self.jours_restants} j restants)" if self.jours_restants is not None else ""
        L.append(f"Date limite   : {self.echeance}{reste}")
        L.append(f"Valeur estimée: {_montant(self.montant, self.devise)}")
        if self.duree_mois:
            L.append(f"Durée         : {self.duree_mois} mois")
        if self.contact:
            L.append(f"Contact       : {self.contact}")

        L += ["", "Pourquoi c'est intéressant pour moi :"]
        L += [f"  · {p}" for p in self.pourquoi] or ["  · A_VERIFIER — aucune correspondance établie automatiquement"]

        if self.a_verifier:
            L += ["", "Points à vérifier :"]
            L += [f"  · {v}" for v in self.a_verifier]

        L += ["", f"Score : {self.score}/100"]
        if avec_detail_score:
            L += [f"    {d}" for d in self.detail_score]

        L += ["", "Action :"]
        if self.nature is Nature.SIGNAL_COMMERCIAL:
            L.append("  👉 prise de contact directe — aucun dossier à déposer")
            if self.lien:
                L.append(f"     {self.lien}")
        elif self.lien:
            L.append(f"  👉 {self.lien}")
            if self.plateforme and self.plateforme != self.lien:
                L.append(f"     plateforme : {self.plateforme}")
        else:
            L.append("  👉 lien de dépôt NON PUBLIÉ — à retrouver sur la plateforme de l'acheteur")

        L.append("")
        L.append(f"  réf. {self.reference} · source {self.source}")
        return "\n".join(L)
