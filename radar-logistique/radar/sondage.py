"""Mesurer le marché AVANT de construire.

Produit les dix mesures demandées. Toute grandeur non observable dans
l'échantillon fourni sort en « NON MESURÉ » — jamais en estimation déguisée
en fait.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .modele import NON_MESURE
from .statut import Statut

SEUIL_MIN = 30      # sous ce volume, aucun pourcentage n'est publié


@dataclass
class Sondage:
    source: str
    total: int = 0
    par_statut: Counter = field(default_factory=Counter)
    par_eligibilite: Counter = field(default_factory=Counter)
    par_famille: Counter = field(default_factory=Counter)
    par_zone: Counter = field(default_factory=Counter)
    par_pays: Counter = field(default_factory=Counter)
    exigences: Counter = field(default_factory=Counter)
    montants: list = field(default_factory=list)
    attribues: int = 0
    motifs_rejet: Counter = field(default_factory=Counter)
    champs_absents: Counter = field(default_factory=Counter)

    def _pct(self, n):
        if self.total < SEUIL_MIN:
            return f"{n} (échantillon trop petit pour un pourcentage)"
        return f"{n}  ({n / self.total:.0%})"

    def _mediane(self):
        if not self.montants:
            return NON_MESURE
        tri = sorted(self.montants)
        m = tri[len(tri) // 2]
        return f"{m:,.0f} EUR (médiane sur {len(tri)} montants publiés)".replace(",", " ")

    def rapport(self) -> str:
        L = [f"SONDAGE — source « {self.source} »", "=" * 62, ""]
        L.append(f"Opportunités analysées .......... {self.total}")
        if self.total < SEUIL_MIN:
            L.append(f"  /!\\ échantillon inférieur à {SEUIL_MIN} : les proportions ne sont pas")
            L.append("      publiées, elles ne seraient pas significatives.")
        L.append("")
        L.append("COMBIEN SONT RÉELLEMENT EXPLOITABLES")
        for s in (Statut.POSTULABLE, Statut.A_VERIFIER, Statut.NON_POSTULABLE):
            L.append(f"  {s.emoji} {s.value:<16} {self._pct(self.par_statut.get(s.value, 0))}")
        L.append(f"  déjà attribués ..... {self._pct(self.attribues)}")
        L.append("")
        L.append("POURQUOI LES REJETS")
        if self.motifs_rejet:
            for motif, n in self.motifs_rejet.most_common(8):
                L.append(f"  {n:>5}  {motif[:60]}")
        else:
            L.append("  aucun rejet dans cet échantillon")
        L.append("")
        L.append("TYPES DE CONTRATS LES PLUS FRÉQUENTS")
        if self.par_famille:
            for fam, n in self.par_famille.most_common(10):
                L.append(f"  {n:>5}  {fam}")
        else:
            L.append(f"  {NON_MESURE} — aucune famille reconnue dans cet échantillon")
        L.append("")
        L.append("MONTANTS OBSERVÉS")
        L.append(f"  {self._mediane()}")
        if self.montants:
            L.append(f"  min {min(self.montants):,.0f} · max {max(self.montants):,.0f}".replace(",", " "))
            L.append(f"  montant non publié sur {self.total - len(self.montants)} avis")
        L.append("")
        L.append("ZONES GÉOGRAPHIQUES")
        for zone, n in self.par_zone.most_common():
            L.append(f"  {n:>5}  {zone}")
        if self.par_pays:
            L.append("  pays cités : " + ", ".join(f"{p}×{n}" for p, n in self.par_pays.most_common(8)))
        L.append("")
        L.append("EXIGENCES QUI REVIENNENT")
        if self.exigences:
            for ex, n in self.exigences.most_common(10):
                L.append(f"  {n:>5}  {ex}")
        else:
            L.append(f"  {NON_MESURE}")
        L.append("")
        L.append("CHAMPS MANQUANTS DANS LA SOURCE")
        if self.champs_absents:
            for champ, n in self.champs_absents.most_common(10):
                L.append(f"  {n:>5}  {champ} absent")
        else:
            L.append("  aucun champ critique manquant")
        return "\n".join(L)


def sonder(moteur, opportunites: list, source: str, maintenant_dt=None) -> Sondage:
    s = Sondage(source=source, total=len(opportunites))
    for opp in opportunites:
        verdict, elig, note, corr, zone, _ = moteur.analyser(opp, maintenant_dt)
        s.par_statut[verdict.statut.value] += 1
        s.par_eligibilite[elig.statut.value] += 1
        s.par_zone[zone.zone.value] += 1
        for f in corr.familles:
            s.par_famille[f] += 1
        for p in set(opp.pays_collecte) | set(opp.pays_livraison):
            s.par_pays[p] += 1
        for code in (opp.exigences or {}):
            s.exigences[code] += 1
        for code in corr.exigences_suggerees:
            s.exigences[f"{code} (suggérée par la famille)"] += 1
        if opp.montant:
            s.montants.append(float(opp.montant))
        if opp.attribue:
            s.attribues += 1
        if verdict.bloquants:
            s.motifs_rejet[verdict.bloquants[0]] += 1
        for champ in ("acheteur", "montant", "echeance_brute", "plateforme"):
            if not getattr(opp, champ, None):
                s.champs_absents[champ] += 1
    return s
