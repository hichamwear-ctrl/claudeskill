"""La fiche. Comprendre en quelques secondes si ça vaut le temps.

CHANGEMENT : ajout des blocs Source (avec date de consultation réelle),
Raisons de la catégorie, Économie, et une action unique.

Un champ absent s'écrit NON PUBLIÉ, A_VERIFIER ou INCONNU — jamais comblé.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .classification import Type

ABSENT = "NON PUBLIÉ"


def _m(v, devise="EUR"):
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
    moteur: str
    action: str
    titre: str
    client: str | None = None
    secteur: str | None = None
    contact: str | None = None
    marche_parent: str | None = None
    lot: str | None = None
    provenances: list = field(default_factory=list)
    zone: str = ""
    corridor: str = ""
    statut_date: str = ""
    echeance: str = ABSENT
    demarrage: str = ABSENT
    jours_restants: int | None = None
    duree_mois: int | None = None
    cadence: str | None = None
    montant: float | None = None
    devise: str = "EUR"
    objet: str | None = None
    pourquoi: list[str] = field(default_factory=list)
    j_ai_deja: list[str] = field(default_factory=list)
    il_me_manque: list[str] = field(default_factory=list)
    comment_combler: list[str] = field(default_factory=list)
    raisons_categorie: list[str] = field(default_factory=list)
    marge: str = "NON MESURÉE"
    score: int = 0
    detail_score: list[str] = field(default_factory=list)
    lien: str | None = None
    source: str = ""
    reference: str = ""
    nature: object = None          # FAIT · SIGNAL · HYPOTHÈSE
    etat: object = None            # POSTULABLE · ATTRIBUÉ · FERMÉ · …
    confiance_etat: str = ""
    type_information: str = ""
    preuves_etat: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)

    def en_texte(self, avec_detail_score=False) -> str:
        L = [f"{self.type.emoji} {self.type.value} — {self.titre}"]
        if self.lot:
            L.append(f"   (LOT {self.lot} du marché {self.marche_parent})")
        L.append("")

        # Quatre dimensions, quatre lignes. Jamais mélangées.
        if self.etat is not None:
            L.append(f"ÉTAT          {self.etat.emoji} {self.etat.value}"
                     f" — {self.etat.libelle_long}")
            if self.type_information:
                L.append(f"TYPE (source) {self.type_information}")
            if self.confiance_etat:
                L.append(f"CONFIANCE     {self.confiance_etat}")
            for preuve in self.preuves_etat:
                L.append(f"PREUVE        {preuve}")
            for c in self.contradictions[:2]:
                L.append(f"CONTRADICTION {c}")
        if self.nature is not None:
            L.append(f"NATURE        {self.nature.emoji} {self.nature.value}"
                     f" — {self.nature.libelle}")
        L.append(f"CLIENT        {_ou(self.client, 'A_VERIFIER')}"
                 + (f"  ({self.secteur})" if self.secteur else ""))
        # La source dit d'où vient l'information. Elle ne dit rien de sa valeur
        # commerciale : c'est l'économie qui en décide, plus bas.
        L.append(f"VU SUR        {self._provenances()}")
        L.append(f"ZONE          {self.zone or 'A_VERIFIER'}"
                 + (f"   [{self.corridor}]" if self.corridor else ""))
        reste = f"  ({self.jours_restants} j restants)" if self.jours_restants is not None else ""
        L.append(f"DATE          {self.statut_date} · limite {self.echeance}{reste}")
        if self.demarrage != ABSENT:
            L.append(f"DÉMARRAGE     {self.demarrage}")
        L.append(f"DURÉE         {self.duree_mois} mois" if self.duree_mois
                 else f"DURÉE         {ABSENT}")
        if self.cadence:
            L.append(f"CADENCE       {self.cadence}")
        L.append(f"VALEUR        {_m(self.montant, self.devise)}")
        if self.contact:
            L.append(f"CONTACT       {self.contact}")

        L += ["", "CE QU'IL FAUT FAIRE", f"  {_ou(self.objet, 'A_VERIFIER')}"]

        L += ["", "POURQUOI C'EST INTÉRESSANT POUR MOI"]
        L += [f"  · {p}" for p in self.pourquoi] or ["  · A_VERIFIER"]

        L += ["", "CE QUE J'AI DÉJÀ"]
        L += [f"  ✔️ {a}" for a in self.j_ai_deja] or ["  · rien de confirmé automatiquement"]

        if self.il_me_manque:
            L += ["", "CE QUI ME MANQUE"] + [f"  ✗ {m}" for m in self.il_me_manque]
        if self.comment_combler:
            L += ["", "COMMENT COMBLER LE MANQUE"] + [f"  🔧 {c}" for c in self.comment_combler]

        L += ["", f"NIVEAU        {self.type.emoji} {self.type.value}  ·  moteur {self.moteur}"]
        if self.raisons_categorie:
            L += [f"  → {r}" for r in self.raisons_categorie]

        L += ["", f"ÉCONOMIE      score {self.score}/100 · marge {self.marge}"]
        if avec_detail_score:
            L += [f"    {d}" for d in self.detail_score]

        L += ["", f"ACTION        👉 {self.action}"]
        if self.lien:
            L.append(f"              {self.lien}")
        L.append("")
        L.append(f"  réf. {self.reference}")
        return "\n".join(L)

    def _provenances(self) -> str:
        """Ne montre QUE ce qui a réellement été consulté, avec la date."""
        if not self.provenances:
            return f"{self.source} · date de consultation NON ENREGISTRÉE"
        return " + ".join(
            f"{p.get('source')}" + (f" ({p.get('consulte_le', '')[:10]})"
                                    if p.get("consulte_le") else "")
            for p in self.provenances)
