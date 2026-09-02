"""Les seize questions à poser avant de notifier quoi que ce soit.

Aucune n'a le droit d'être devinée. Ce qui ne peut pas être répondu vaut
A_VERIFIER, jamais une réponse inventée. Le journal produit ici est ce qui
permet de dire, plus tard, pourquoi une opportunité est passée ou non.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .classification import Type
from .role import Role

A_VERIFIER = "A_VERIFIER"


@dataclass
class Journal:
    reponses: dict[str, str] = field(default_factory=dict)

    def sans_reponse(self) -> list[str]:
        return [q for q, r in self.reponses.items() if r == A_VERIFIER]

    def en_lignes(self) -> list[str]:
        return [f"{q} → {r}" for q, r in self.reponses.items()]


def interroger(*, opp, role, correspondance, zone, bilan, classement, verdict,
               score, lots_retenus) -> Journal:
    j = Journal()
    r = j.reponses

    r["1. qui achète ?"] = opp.acheteur or A_VERIFIER
    r["2. qu'est-ce qui est acheté ?"] = opp.intitule or A_VERIFIER
    r["3. quelle prestation dois-je fournir ?"] = (
        ", ".join(correspondance.familles) if correspondance.familles else A_VERIFIER)
    r["4. puis-je fournir cette prestation ?"] = {
        Role.PRESTATAIRE: "oui — la prestation logistique est l'objet du marché",
        Role.FOURNISSEUR: "non — l'acheteur veut un bien, pas une prestation",
        Role.A_VERIFIER: A_VERIFIER}[role]
    r["5. où s'exécute-t-elle ?"] = (
        " → ".join(filter(None, ["/".join(zone.collecte), "/".join(zone.livraison)]))
        or opp.lieu_texte or A_VERIFIER)
    r["6. compatible avec mon modèle géographique ?"] = (
        zone.raisons[0] if zone.raisons else A_VERIFIER)
    r["7. quelle capacité est nécessaire ?"] = (
        "; ".join(list(opp.exigences or {})) or A_VERIFIER)
    r["8. est-ce que je l'ai ?"] = (
        "; ".join(bilan.atouts[:2]) if bilan.atouts else A_VERIFIER)
    r["9. sinon, puis-je la mobiliser ?"] = (
        "; ".join(bilan.mobilisations[:2]) if bilan.mobilisations
        else ("sans objet" if bilan.atouts and not bilan.bloquants else A_VERIFIER))
    r["10. y a-t-il une exigence bloquante ?"] = (
        "; ".join(bilan.bloquants) if bilan.bloquants else "aucune détectée")
    r["11. la deadline est-elle ouverte ?"] = verdict.motif or A_VERIFIER
    r["12. puis-je être titulaire ?"] = (
        "oui" if classement.type is Type.DIRECT else "non")
    r["13. sinon, sous-traitant ?"] = (
        "oui" if classement.sous_traitance_possible else
        ("sans objet" if classement.type is Type.DIRECT else A_VERIFIER))
    r["14. sinon, prospect commercial ?"] = (
        "oui" if classement.type is Type.PROSPECT else "sans objet")
    r["15. quel potentiel économique ?"] = (
        f"{opp.montant:,.0f} {opp.devise}".replace(",", " ")
        + (f" sur {opp.duree_mois} mois" if opp.duree_mois else "")
        if opp.montant else A_VERIFIER)
    r["16. quelle action maintenant ?"] = classement.action or A_VERIFIER

    if lots_retenus:
        r["lots retenus"] = "; ".join(lots_retenus)
    return j
