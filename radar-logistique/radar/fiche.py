"""La fiche d'action : ce que l'exploitant reçoit, et rien d'autre.

Sept champs obligatoires. Un champ absent est écrit « NON PUBLIÉ » — jamais
comblé par une valeur plausible. Une fiche qui invente un montant ou une
plateforme de dépôt est pire qu'une fiche incomplète.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ABSENT = "NON PUBLIÉ"


def _ou_absent(v):
    return ABSENT if v in (None, "", []) else v


def _montant(v, devise="EUR"):
    if v in (None, "", 0):
        return ABSENT
    try:
        return f"{float(v):,.0f} {devise}".replace(",", " ")
    except (TypeError, ValueError):
        return str(v)


@dataclass
class Fiche:
    reference: str
    intitule: str
    acheteur: str | None
    contact: str | None
    objet: str | None
    montant: float | None
    devise: str
    echeance_texte: str
    jours_restants: int | None
    plateforme: str | None
    lien_depot: str | None
    lien_documents: str | None
    conditions: list[str] = field(default_factory=list)
    atouts: list[str] = field(default_factory=list)
    reserves: list[str] = field(default_factory=list)
    signalements: list[str] = field(default_factory=list)
    score: int = 0
    source: str = ""

    def en_texte(self) -> str:
        """Rendu destiné à la notification. Ordre imposé par l'exploitant."""
        L = []
        urgence = ""
        if self.jours_restants is not None:
            urgence = f"  ·  {self.jours_restants} j restants" if self.jours_restants >= 0 else ""
        L.append(f"[{self.score}/100] {self.intitule}")
        L.append("")
        L.append(f"CLÔTURE      {self.echeance_texte}{urgence}")
        L.append(f"MONTANT      {_montant(self.montant, self.devise)}")
        L.append(f"ACHETEUR     {_ou_absent(self.acheteur)}")
        if self.contact:
            L.append(f"CONTACT      {self.contact}")
        L.append("")
        L.append("CE QUI EST DEMANDÉ")
        L.append(f"  {_ou_absent(self.objet)}")
        L.append("")
        L.append("CONDITIONS POUR RÉPONDRE")
        if self.conditions:
            L += [f"  · {c}" for c in self.conditions]
        else:
            L.append(f"  {ABSENT} — à lire dans le cahier des charges")
        L.append("")
        L.append("POURQUOI TU CORRESPONDS")
        if self.atouts:
            L += [f"  + {a}" for a in self.atouts]
        else:
            L.append("  aucune correspondance établie automatiquement — à juger toi-même")
        if self.reserves:
            L += [f"  ~ {r}" for r in self.reserves]
        L.append("")
        L.append("OÙ DÉPOSER")
        L.append(f"  {_ou_absent(self.plateforme)}")
        if self.lien_depot and self.lien_depot != self.plateforme:
            L.append(f"  {self.lien_depot}")
        if self.lien_documents:
            L.append(f"  Cahier des charges : {self.lien_documents}")
        if self.signalements:
            L.append("")
            L += [f"  /!\\ {s}" for s in self.signalements]
        L.append("")
        L.append(f"  réf. {self.reference} · source {self.source}")
        return "\n".join(L)

    def champs_manquants(self) -> list[str]:
        """Sert au diagnostic de couverture, pas à masquer la fiche."""
        manquants = []
        for nom, v in (("montant", self.montant), ("acheteur", self.acheteur),
                       ("objet", self.objet), ("plateforme", self.plateforme)):
            if v in (None, ""):
                manquants.append(nom)
        if not self.conditions:
            manquants.append("conditions")
        return manquants
