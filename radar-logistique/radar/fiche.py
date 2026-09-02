"""Trois formats de notification, un par type d'opportunité.

Court et concret : savoir en quelques secondes si ça vaut le coup de lire la
suite. Un champ absent est écrit NON PUBLIÉ ou A_VERIFIER — jamais comblé par
une valeur plausible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .classification import Type

ABSENT = "NON PUBLIÉ"


def _montant(v, devise="EUR"):
    if v in (None, "", 0):
        return ABSENT
    try:
        return f"{float(v):,.0f} {devise}".replace(",", " ")
    except (TypeError, ValueError):
        return str(v)


def _ou(v, defaut=ABSENT):
    return defaut if v in (None, "", []) else v


@dataclass
class Fiche:
    type: Type
    titre: str
    acheteur: str | None = None
    secteur: str | None = None
    contact: str | None = None
    lots_retenus: list[str] = field(default_factory=list)
    zone: str = ""
    collecte: list[str] = field(default_factory=list)
    livraison: list[str] = field(default_factory=list)
    echeance: str = ABSENT
    jours_restants: int | None = None
    montant: float | None = None
    devise: str = "EUR"
    duree_mois: int | None = None
    cadence: str | None = None
    compatible: list[str] = field(default_factory=list)      # « pourquoi c'est compatible »
    a_verifier: list[str] = field(default_factory=list)
    a_mobiliser: list[str] = field(default_factory=list)
    score: int = 0
    detail_score: list[str] = field(default_factory=list)
    action: str = ""
    lien_dossier: str | None = None
    lien_depot: str | None = None
    titulaire: str | None = None
    signal: str | None = None
    source: str = ""
    reference: str = ""

    # ------------------------------------------------------------ rendu --
    def en_texte(self, avec_detail_score=False) -> str:
        if self.type is Type.SOUS_TRAITANCE:
            corps = self._sous_traitance()
        elif self.type is Type.PROSPECT:
            corps = self._prospect()
        else:
            corps = self._direct()
        if avec_detail_score:
            corps += "\n" + "\n".join(f"    {d}" for d in self.detail_score)
        return corps + f"\n\n  réf. {self.reference} · source {self.source}"

    # ------------------------------------------------------------ 🟢 --
    def _direct(self) -> str:
        L = [f"🟢 OPPORTUNITÉ À POSTULER", self.titre, ""]
        L.append(f"📍 {self.zone or _ou(None, 'A_VERIFIER')}")
        reste = f"  ({self.jours_restants} j restants)" if self.jours_restants is not None else ""
        L.append(f"📅 Deadline : {self.echeance}{reste}")
        L.append(f"💰 Valeur estimée : {_montant(self.montant, self.devise)}")
        if self.duree_mois:
            L.append(f"⏱️ Durée : {self.duree_mois} mois")
        if self.cadence:
            L.append(f"🔁 Cadence : {self.cadence}")
        if self.acheteur:
            L.append(f"🏢 Acheteur : {self.acheteur}"
                     + (f" ({self.secteur})" if self.secteur else ""))
        if self.lots_retenus:
            L += ["", "Lots compatibles :"] + [f"  · {l}" for l in self.lots_retenus]
        L += ["", "Pourquoi c'est compatible :"]
        L += [f"  · {c} ✔️" for c in self.compatible] or ["  · A_VERIFIER"]
        if self.a_mobiliser:
            L += ["", "À mobiliser :"] + [f"  🔧 {m}" for m in self.a_mobiliser]
        if self.a_verifier:
            L += ["", "Points à vérifier :"] + [f"  🟠 {v}" for v in self.a_verifier]
        L += ["", f"Score : {self.score}/100", "", "Action :"]
        L.append(f"  → {self.lien_dossier}" if self.lien_dossier else "  → dossier NON PUBLIÉ")
        if self.lien_depot and self.lien_depot != self.lien_dossier:
            L.append(f"  → déposer l'offre : {self.lien_depot}")
        return "\n".join(L)

    # ------------------------------------------------------------ 🟡 --
    def _sous_traitance(self) -> str:
        L = ["🟡 OPPORTUNITÉ DE SOUS-TRAITANCE", ""]
        L.append(f"Entreprise : {_ou(self.titulaire, 'titulaire A_VERIFIER')}")
        L.append(f"Contrat : {self.titre}")
        L.append(f"📍 {self.zone or 'A_VERIFIER'}")
        if self.montant:
            L.append(f"💰 {_montant(self.montant, self.devise)}"
                     + (f" sur {self.duree_mois} mois" if self.duree_mois else ""))
        L += ["", "Pourquoi cela peut m'intéresser :"]
        L += [f"  · {c}" for c in self.compatible] or ["  · activité proche de mon savoir-faire"]
        if self.a_verifier:
            L += ["", "Points à vérifier :"] + [f"  🟠 {v}" for v in self.a_verifier]
        L += ["", f"Score : {self.score}/100", "", "Action recommandée :"]
        L.append(f"  → {self.action or 'contacter le titulaire comme transporteur sous-traitant'}")
        if self.lien_dossier:
            L.append(f"  → détail du marché : {self.lien_dossier}")
        return "\n".join(L)

    # ------------------------------------------------------------ 🔵 --
    def _prospect(self) -> str:
        L = ["🔵 PROSPECT COMMERCIAL", ""]
        L.append(f"Entreprise : {_ou(self.acheteur, 'A_VERIFIER')}")
        L.append(f"Signal détecté : {_ou(self.signal, self.titre)}")
        L.append(f"📍 {self.zone or 'A_VERIFIER'}")
        L += ["", "Pourquoi intéressant :"]
        L += [f"  · {c}" for c in self.compatible] or ["  · activité compatible"]
        if self.a_verifier:
            L += ["", "Points à vérifier :"] + [f"  🟠 {v}" for v in self.a_verifier]
        L += ["", f"Score : {self.score}/100", "", "Action :"]
        L.append("  → contacter l'entreprise")
        L.append("  → identifier le responsable logistique")
        L.append("  → proposer mes services")
        if self.lien_dossier:
            L.append(f"  → source : {self.lien_dossier}")
        return "\n".join(L)
