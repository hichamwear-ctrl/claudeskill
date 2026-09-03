"""Le rapport de mesure — ce que le radar a RÉELLEMENT trouvé.

Il ne force jamais un TOP 20 : s'il n'y a rien de bon dans l'échantillon, il le
dit. Et il porte son mode en tête, pour qu'une capture d'écran ne puisse pas
être prise pour un résultat réel si elle n'en est pas un.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .mode import Mode

CHAMPS_COMPLETUDE = (
    ("acheteur", "acheteur"), ("échéance", "echeance"), ("montant", "montant"),
    ("durée", "duree_mois"), ("cadence", "cadence"), ("lots", "lot_numero"),
    ("contact", "contact"), ("zone", "zone"), ("exigences", "exigences"),
)


@dataclass
class Rapport:
    mode: Mode
    genere_le: str = ""
    sources: dict = field(default_factory=dict)
    total: int = 0
    par_type: dict = field(default_factory=dict)
    par_moteur: dict = field(default_factory=dict)
    completude: dict = field(default_factory=dict)
    rejets: dict = field(default_factory=dict)
    incidents: dict = field(default_factory=dict)
    doublons: dict = field(default_factory=dict)
    a_verifier: int = 0
    top: list = field(default_factory=list)
    livre: object = None

    def _pct(self, n: int) -> str:
        return f"{n:>5}  ({n / self.total:.0%})" if self.total else f"{n:>5}"

    def en_texte(self, avec_fiches=True) -> str:
        L = [self.mode.bandeau(), "",
             f"RAPPORT DE MESURE — généré le {self.genere_le}", "=" * 72, ""]

        L.append("COLLECTE")
        if self.sources:
            for nom, infos in sorted(self.sources.items()):
                quand = infos.get("derniere") or "date de collecte NON ENREGISTRÉE"
                L.append(f"  {nom:<16} {infos['n']:>6} avis   dernière collecte {quand[:19]}")
        else:
            L.append("  aucune source — la base est vide")
        L.append(f"  total analysé    {self.total:>6}")

        L += ["", "COMPLÉTUDE DES DONNÉES"]
        for libelle, n in self.completude.items():
            if n is None:
                L.append(f"  {libelle:<16} NON MESURÉ — champ absent du schéma")
            else:
                L.append(f"  {libelle:<16} {self._pct(n)}")

        L += ["", "CLASSIFICATION"]
        for emoji, cle in (("🟢", "DIRECT"), ("🟡", "RENFORCEMENT"), ("🟣", "A_CONSTRUIRE"),
                           ("🔵", "PROSPECT"), ("🔴", "REJET")):
            L.append(f"  {emoji} {cle:<14} {self._pct(self.par_type.get(cle, 0))}")
        L.append(f"  CAPTER           {self._pct(self.par_moteur.get('CAPTER', 0))}")
        L.append(f"  DÉVELOPPER       {self._pct(self.par_moteur.get('DEVELOPPER', 0))}")

        L += ["", "PRINCIPAUX MOTIFS DE REJET"]
        if self.rejets:
            for motif, n in sorted(self.rejets.items(), key=lambda x: -x[1])[:8]:
                L.append(f"  {n:>5}  {motif[:56]}")
        else:
            L.append("  aucun rejet")

        L += ["", "QUALITÉ"]
        for libelle, cle in (("doublons certains", "certains"),
                             ("doublons probables", "probables"),
                             ("doublons possibles", "possibles")):
            L.append(f"  {libelle:<20} {self.doublons.get(cle, 0):>5}")
        L.append(f"  {'points À VÉRIFIER':<20} {self.a_verifier:>5}")
        if self.incidents:
            for etape, n in sorted(self.incidents.items(), key=lambda x: -x[1]):
                L.append(f"  incident « {etape} » {n:>5}  — avis conservés, consultables")
        else:
            L.append(f"  {'incidents':<20} {0:>5}")

        if self.livre is not None:
            L += ["", self.livre.rapport()]

        L += ["", "=" * 72, ""]
        if not self.top:
            L.append("AUCUNE OPPORTUNITÉ FORTE DÉTECTÉE DANS CET ÉCHANTILLON.")
            L.append("")
            L.append("Le radar ne force pas un classement : rien ici ne mérite ton temps")
            L.append("aujourd'hui. Ce n'est pas une panne, c'est une mesure.")
            return "\n".join(L)

        L.append(f"CE QUE JE REGARDERAIS À TA PLACE — {len(self.top)} opportunité(s)")
        L.append("")
        for i, (score, titre, action, fiche) in enumerate(self.top, 1):
            L.append(f"  {i:>2}. [{score:>3}] {action:<24} {titre[:60]}")
        if avec_fiches:
            L += ["", "=" * 72, ""]
            for _, _, _, fiche in self.top:
                L.append(fiche)
                L.append("\n" + "─" * 72 + "\n")
        return "\n".join(L)


def construire(cx, mode: Mode, limite_top=20, livre=None) -> Rapport:
    r = Rapport(mode=mode,
                genere_le=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                livre=livre)

    for l in cx.execute(
            "SELECT a.source AS s, count(*) n, max(a.derniere_vue) d"
            " FROM opportunites o JOIN avis a ON a.id = o.avis_id GROUP BY a.source"):
        r.sources[l["s"]] = {"n": l["n"], "derniere": l["d"]}
    r.total = sum(v["n"] for v in r.sources.values())

    for l in cx.execute("SELECT type, count(*) n FROM opportunites GROUP BY type"):
        r.par_type[l["type"]] = l["n"]
    for l in cx.execute("SELECT moteur, count(*) n FROM opportunites"
                        " WHERE type <> 'REJET' GROUP BY moteur"):
        r.par_moteur[l["moteur"] or "?"] = l["n"]
    for l in cx.execute("SELECT motif, count(*) n FROM opportunites"
                        " WHERE type = 'REJET' GROUP BY motif"):
        r.rejets[l["motif"] or "motif non enregistré"] = l["n"]
    for l in cx.execute("SELECT etape, count(*) n FROM incidents GROUP BY etape"):
        r.incidents[l["etape"]] = l["n"]

    # Tolérant : une colonne absente du schéma est signalée, pas fatale.
    connues = {l[1] for l in cx.execute("PRAGMA table_info(opportunites)")}
    for libelle, colonne in CHAMPS_COMPLETUDE:
        if colonne not in connues:
            r.completude[libelle] = None
            continue
        r.completude[libelle] = cx.execute(
            f"SELECT count(*) c FROM opportunites"
            f" WHERE {colonne} IS NOT NULL AND {colonne} <> ''").fetchone()["c"]

    r.a_verifier = cx.execute(
        "SELECT count(*) c FROM opportunites WHERE fiche LIKE '%A_VERIFIER%'").fetchone()["c"]

    for l in cx.execute(
            "SELECT score, intitule, action, fiche FROM opportunites"
            " WHERE type <> 'REJET' AND moteur = 'CAPTER'"
            " ORDER BY score DESC LIMIT ?", (limite_top,)):
        r.top.append((l["score"], l["intitule"] or "(sans intitulé)",
                      l["action"] or "?", l["fiche"] or ""))
    return r
