"""Mesurer le marché — public ET privé — avant de construire.

Toute grandeur non observée dans l'échantillon sort en « NON MESURÉ ». Jamais
une statistique inventée. Sous 30 opportunités, aucun pourcentage n'est publié :
un ratio sur six lignes n'est pas une mesure.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .classification import Type
from .modele import NON_MESURE
from .role import Role

SEUIL_MIN = 30


@dataclass
class Sondage:
    source: str
    total: int = 0
    par_type: Counter = field(default_factory=Counter)
    par_role: Counter = field(default_factory=Counter)
    par_famille: Counter = field(default_factory=Counter)
    par_zone: Counter = field(default_factory=Counter)
    par_pays: Counter = field(default_factory=Counter)
    par_cadence: Counter = field(default_factory=Counter)
    par_acheteur: Counter = field(default_factory=Counter)
    exigences: Counter = field(default_factory=Counter)
    motifs_rejet: Counter = field(default_factory=Counter)
    champs_absents: Counter = field(default_factory=Counter)
    montants: list = field(default_factory=list)
    montants_accessibles: list = field(default_factory=list)
    scores: list = field(default_factory=list)
    lots_analyses: int = 0
    marches_sauves_par_un_lot: int = 0
    attribues: int = 0
    recurrents: int = 0

    def _pct(self, n):
        if self.total < SEUIL_MIN:
            return f"{n}"
        return f"{n}  ({n / self.total:.0%})"

    @staticmethod
    def _med(valeurs, unite="EUR"):
        if not valeurs:
            return NON_MESURE
        t = sorted(valeurs)
        return f"{t[len(t)//2]:,.0f} {unite} (médiane sur {len(t)})".replace(",", " ")

    def rapport(self) -> str:
        L = [f"SONDAGE — source « {self.source} »", "=" * 64, ""]
        L.append(f"Opportunités analysées ......... {self.total}")
        L.append(f"Lots réellement examinés ....... {self.lots_analyses}")
        if self.total < SEUIL_MIN:
            L.append(f"  /!\\ moins de {SEUIL_MIN} opportunités : aucun pourcentage n'est publié,")
            L.append("      il ne serait pas significatif.")
        L += ["", "CE QUE JE PEUX RÉELLEMENT ALLER CHERCHER"]
        for t in (Type.DIRECT, Type.RENFORCEMENT, Type.A_CONSTRUIRE,
                  Type.PROSPECT, Type.REJET):
            L.append(f"  {t.emoji} {t.value:<16} {self._pct(self.par_type.get(t.value, 0))}")
        L.append(f"  dont sauvés par un seul lot : {self.marches_sauves_par_un_lot}")

        L += ["", "PRESTATION OU FOURNITURE ?"]
        for r in (Role.PRESTATAIRE, Role.FOURNISSEUR, Role.A_VERIFIER):
            L.append(f"  {r.value:<14} {self._pct(self.par_role.get(r.value, 0))}")

        L += ["", "POURQUOI LES REJETS"]
        if self.motifs_rejet:
            for motif, n in self.motifs_rejet.most_common(8):
                L.append(f"  {n:>5}  {motif[:62]}")
        else:
            L.append("  aucun rejet dans cet échantillon")

        L += ["", "TYPES DE PRESTATION LES PLUS FRÉQUENTS"]
        if self.par_famille:
            for f, n in self.par_famille.most_common(10):
                L.append(f"  {n:>5}  {f}")
        else:
            L.append(f"  {NON_MESURE}")

        L += ["", "MONTANTS"]
        L.append(f"  tous marchés ......... {self._med(self.montants)}")
        L.append(f"  marchés accessibles .. {self._med(self.montants_accessibles)}")
        if self.montants:
            L.append(f"  montant non publié sur {self.total - len(self.montants)} avis")

        L += ["", "MARCHÉ PRIVÉ ET RÉCURRENCE"]
        L.append(f"  besoins récurrents détectés ... {self._pct(self.recurrents)}")
        if self.par_cadence:
            L.append("  cadences : " + ", ".join(f"{c}×{n}" for c, n in self.par_cadence.most_common(5)))
        else:
            L.append(f"  cadences : {NON_MESURE}")
        L.append(f"  à renforcer .................. {self._pct(self.par_type.get('RENFORCEMENT', 0))}")
        L.append(f"  à construire ................. {self._pct(self.par_type.get('A_CONSTRUIRE', 0))}")
        L.append(f"  prospects commerciaux ........ {self._pct(self.par_type.get('PROSPECT', 0))}")

        L += ["", "ACHETEURS QUI REVIENNENT"]
        recurrents = [(a, n) for a, n in self.par_acheteur.most_common(8) if n > 1]
        if recurrents:
            for a, n in recurrents:
                L.append(f"  {n:>5}×  {a[:56]}")
        else:
            L.append(f"  {NON_MESURE} — aucun acheteur vu plus d'une fois")

        L += ["", "ZONES"]
        for z, n in self.par_zone.most_common():
            L.append(f"  {n:>5}  {z}")
        if self.par_pays:
            L.append("  pays : " + ", ".join(f"{p}×{n}" for p, n in self.par_pays.most_common(8)))

        L += ["", "EXIGENCES QUI REVIENNENT"]
        if self.exigences:
            for e, n in self.exigences.most_common(10):
                L.append(f"  {n:>5}  {e}")
        else:
            L.append(f"  {NON_MESURE}")

        L += ["", "CHAMPS MANQUANTS DANS LA SOURCE"]
        if self.champs_absents:
            for c, n in self.champs_absents.most_common(8):
                L.append(f"  {n:>5}  {c}")
        else:
            L.append("  aucun champ critique manquant")

        L += ["", "VERDICT SUR LA SOURCE"]
        # « Exploitable » = tout ce qui n'est pas un rejet. Un marché trop gros
        # pour la structure actuelle reste exploitable : il se renforce, il se
        # groupe, il se sous-traite. Il ne se jette pas.
        utiles = sum(n for t, n in self.par_type.items() if t != "REJET")
        if self.total:
            L.append(f"  {utiles} opportunité(s) exploitable(s) sur {self.total} lues")
            L.append("  → priorité à recalculer sur ce ratio, pas sur la notoriété de la source")
        return "\n".join(L)


def sonder(moteur, opportunites, source: str, maintenant_dt=None) -> Sondage:
    """Mesure la source EXACTEMENT comme la chaîne la traitera.

    Un marché à lots produit une opportunité par lot : sonder devait le faire
    aussi, sinon le sondage annonce un marché là où le traitement en trouvera
    trois — et le premier rapport réel ne serait pas comparable au sondage qui
    l'a précédé.
    """
    from .lots import eclater

    s = Sondage(source=source, total=len(opportunites))
    for marche in opportunites:
        enfants = eclater(marche)
        s.lots_analyses += len(enfants)
        retenus = 0
        for opp in enfants:
            r = moteur.analyser(opp, maintenant_dt)
            if r.classement.type is not Type.REJET:
                retenus += 1
            _compter(s, opp, r)
        # Un marché « sauvé par un lot » : le marché entier aurait pu paraître
        # incompatible, un seul de ses lots le rend exploitable.
        if len(enfants) > 1 and retenus:
            s.marches_sauves_par_un_lot += 1
    return s


def _compter(s: Sondage, opp, r) -> None:
    """Une opportunité — un lot le plus souvent — entre dans la mesure."""
    s.par_type[r.classement.type.value] += 1
    s.par_role[r.role.value] += 1
    s.par_zone[r.zone.zone.value] += 1
    s.scores.append(r.score.total)
    for f in r.correspondance.familles:
        s.par_famille[f] += 1
    for p in set(opp.pays_collecte) | set(opp.pays_livraison):
        s.par_pays[p] += 1
    for code in (opp.exigences or {}):
        s.exigences[code] += 1
    if opp.acheteur:
        s.par_acheteur[opp.acheteur] += 1
    if opp.cadence:
        s.par_cadence[opp.cadence] += 1
        if opp.cadence.lower() not in ("ponctuelle", "inconnue"):
            s.recurrents += 1
    if opp.montant:
        s.montants.append(float(opp.montant))
        if r.classement.type is not Type.REJET:
            s.montants_accessibles.append(float(opp.montant))
    if opp.attribue:
        s.attribues += 1
    if r.classement.raisons_rejet:
        s.motifs_rejet[r.classement.raisons_rejet[0]] += 1
    for champ in ("acheteur", "montant", "echeance_brute", "plateforme", "cadence"):
        if not getattr(opp, champ, None):
            s.champs_absents[champ] += 1
