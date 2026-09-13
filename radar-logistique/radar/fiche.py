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
    # PAR OÙ FRAPPER. Informatif : ne change ni l'état, ni le score, ni
    # l'action. Une porte d'entrée ne rend pas un besoin postulable.
    porte_entree: object = None
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
    score_affiche: str = ""        # « 84/100 » ou « NON MESURABLE — … »
    detail_score: list[str] = field(default_factory=list)
    lien: str | None = None
    source: str = ""
    reference: str = ""
    nature: object = None          # FAIT · SIGNAL · HYPOTHÈSE
    etat: object = None            # POSTULABLE · ATTRIBUÉ · FERMÉ · …
    etat_libelle: str = ""
    confiance_etat: str = ""
    type_information: str = ""
    preuves_etat: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    fiabilite: str = ""
    fiabilite_motif: str = ""
    fil_de_vie: list = field(default_factory=list)
    # Ce qui a été observé, écarté, et pourquoi. Une information écartée en
    # silence est une boîte noire ; écartée à voix haute, c'est une question.
    reserves: list = field(default_factory=list)

    def _besoin(self) -> str:
        """Le besoin en une phrase, pour l'en-tête.

        C'est une TRONCATURE d'affichage, pas une reformulation : on coupe à
        la première ponctuation forte du texte réellement observé. Rien n'est
        réécrit, rien n'est résumé — un résumé serait une invention.
        """
        brut = (self.objet or "").strip()
        if not brut:
            return "A_VERIFIER"
        for fin in ("? ", "! ", ". "):
            coupe = brut.find(fin)
            if 0 < coupe < 160:
                return brut[:coupe + 1].strip()
        return (brut[:140] + "…") if len(brut) > 140 else brut

    def _capacite(self) -> str:
        """Ce que le bilan de capacité a déjà conclu, en une ligne.

        Aucun calcul ici. Si la source ne publie pas ce qu'elle exige, l'écart
        n'est pas zéro : il est À DÉTERMINER.
        """
        # `il_me_manque` mélange deux choses : les manques de capacité et les
        # incertitudes d'état. Mesuré sur DHL, où l'en-tête annonçait en
        # « CAPACITÉ » une preuve d'état écartée en pied de page. Seul
        # `comment_combler` vient exclusivement du bilan de capacité : c'est
        # donc lui qui autorise à parler d'un manque chiffré.
        if self.comment_combler:
            manque = self.il_me_manque[0] if self.il_me_manque else "manque de capacité"
            return f"{manque} — comblable : {self.comment_combler[0]}"
        if self.j_ai_deja:
            return f"couverte — {self.j_ai_deja[0]}"
        return "requise NON PUBLIÉE · écart À DÉTERMINER"

    def _urgence(self) -> str:
        """Ce que la source dit du temps. Jamais une estimation."""
        if self.jours_restants is not None:
            return f"{self.jours_restants} jours restants"
        if self.echeance and self.echeance != ABSENT:
            return f"échéance {self.echeance}"
        return "NON PUBLIÉE"

    def _entete_commercial(self) -> list[str]:
        """Les sept questions, dans l'ordre où un commercial se les pose.

        Rien n'est calculé ici : chaque ligne reprend une valeur déjà établie
        plus bas dans la fiche. C'est un ORDRE DE LECTURE, pas une source de
        vérité — si une valeur manque, elle manque ici aussi.
        """
        porte = self.porte_entree if hasattr(self.porte_entree, "type") else None
        comment = "AUCUNE PORTE OBSERVÉE"
        if porte is not None and porte.existe:
            comment = porte.type
            if porte.champs_a_remplir:
                comment += f" — {porte.champs_a_remplir} champs"
            if porte.certitude == "À VÉRIFIER":
                comment += " (À VÉRIFIER)"

        L = [f"👉 ACTION       {self.action}",
             f"   QUI          {_ou(self.client, 'A_VERIFIER')}"
             + (f"  ({self.secteur})" if self.secteur else ""),
             f"   QUOI         {self._besoin()}",
             f"   OÙ           {self.zone or 'A_VERIFIER'}",
             f"   POURQUOI     {self.pourquoi[0] if self.pourquoi else 'AUCUN ARGUMENT MESURÉ'}",
             f"   COMMENT      {comment}"]
        if porte is not None and porte.lien:
            L.append(f"                {porte.lien}")
        if porte is not None and porte.informations_demandees:
            L.append("   À PRÉPARER   "
                     + " · ".join(porte.informations_demandees[:6]))
        L.append(f"   CAPACITÉ     {self._capacite()}")
        L.append(f"   URGENCE      {self._urgence()}")
        L.append(f"   CA           {_m(self.montant, self.devise)}")
        return L

    def en_texte(self, avec_detail_score=False) -> str:
        L = [f"{self.type.emoji} {self.type.value} — {self.titre}"]
        if self.lot:
            L.append(f"   (LOT {self.lot} du marché {self.marche_parent})")
        L.append("")
        # ── CE QU'ON LIT EN DIX SECONDES ─────────────────────────────────
        L += self._entete_commercial()
        L += ["", "─" * 66, ""]

        # Quatre dimensions, quatre lignes. Jamais mélangées.
        if self.etat is not None and self.etat_libelle:
            L.append(f"ÉTAT          {self.etat_libelle}")
            if self.type_information:
                L.append(f"TYPE (source) {self.type_information}")
            if self.confiance_etat:
                L.append(f"CONFIANCE     {self.confiance_etat}")
            for preuve in self.preuves_etat:
                L.append(f"PREUVE        {preuve}")
            for c in self.contradictions[:2]:
                L.append(f"CONTRADICTION {c}")
        if self.fil_de_vie:
            L.append(f"HISTORIQUE    {self.fil_de_vie[0]}")
            for etape in self.fil_de_vie[1:]:
                L.append(f"              {etape}")
        if self.nature is not None:
            L.append(f"NATURE        {self.nature.emoji} {self.nature.value}"
                     f" — {self.nature.libelle}")
        if self.fiabilite:
            # La fiabilité dit à quel point c'est PROUVÉ. Elle ne dit rien de ce
            # que ça peut rapporter : le score s'en charge, et il l'ignore.
            L.append(f"FIABILITÉ     {self.fiabilite} — {self.fiabilite_motif}")
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

        lignes_porte = (self.porte_entree.en_lignes()
                        if self.porte_entree is not None
                        and hasattr(self.porte_entree, "en_lignes") else [])
        if lignes_porte:
            L += [""] + lignes_porte

        L += ["", "CE QU'IL FAUT FAIRE", f"  {_ou(self.objet, 'A_VERIFIER')}"]

        L += ["", "POURQUOI C'EST INTÉRESSANT POUR MOI"]
        L += ([f"  · {p}" for p in self.pourquoi] or
              ["  · rien dans cette source ne constitue un argument commercial"])

        L += ["", "CE QUE J'AI DÉJÀ"]
        L += [f"  ✔️ {a}" for a in self.j_ai_deja] or ["  · rien de confirmé automatiquement"]

        if self.reserves:
            L += ["", "OBSERVÉ MAIS ÉCARTÉ — À VÉRIFIER"] + [f"  ⚠ {r}" for r in self.reserves]
        if self.il_me_manque:
            L += ["", "CE QUI ME MANQUE"] + [f"  ✗ {m}" for m in self.il_me_manque]
        if self.comment_combler:
            L += ["", "COMMENT COMBLER LE MANQUE"] + [f"  🔧 {c}" for c in self.comment_combler]

        L += ["", f"NIVEAU        {self.type.emoji} {self.type.value}  ·  moteur {self.moteur}"]
        if self.raisons_categorie:
            L += [f"  → {r}" for r in self.raisons_categorie]

        L += ["", f"ÉCONOMIE      score {self.score_affiche or f'{self.score}/100'}"
                  f" · marge {self.marge}"]
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
