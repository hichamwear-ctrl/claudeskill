"""Ligne de commande.

Un outil qui échoue doit le dire et s'arrêter : chaque commande renvoie un code
de sortie non nul en cas d'échec, plutôt que d'afficher « 0 » partout et de
signaler un succès.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import envoi
from .base import ouvrir
from .chaine import traiter
from .correspondance import Correspondance

RACINE = Path(__file__).resolve().parent.parent


def _charger(source: str):
    cfg = yaml.safe_load((RACINE / "sources" / f"{source}.yaml").read_text(encoding="utf-8"))
    return Correspondance.depuis_config(cfg), cfg


def cmd_recenser(a) -> int:
    """Mesure le taux de présence RÉEL de chaque champ sur de vraies réponses."""
    corr, cfg = _charger(a.source)
    charges = json.loads(Path(a.echantillon).read_text(encoding="utf-8"))
    if not isinstance(charges, list) or not charges:
        print("échantillon vide ou mal formé — rien à mesurer", file=sys.stderr)
        return 2
    taux = corr.mesurer(charges)
    print(f"Recensement « {a.source} » sur {len(charges)} réponses réelles\n")
    for nom, t in sorted(taux.items(), key=lambda x: -x[1]):
        marque = "  " if t > 0.5 else ("~ " if t > 0 else "✗ ")
        print(f"  {marque}{t:6.1%}  {nom}")
    absents = [n for n, t in taux.items() if t == 0]
    if absents:
        print(f"\n{len(absents)} champ(s) à 0 % : la clé déclarée n'existe pas.")
        print(f"Corrige-les dans sources/{a.source}.yaml, PAS dans le code.")
        return 1
    print("\nTous les champs répondent. Passe `verifie: true` dans le fichier de source.")
    return 0


def cmd_traiter(a) -> int:
    corr, _ = _charger(a.source)
    if not corr.verifie:
        print(f"AVERTISSEMENT : la correspondance « {a.source} » n'est pas vérifiée.\n"
              f"Lance d'abord `recenser` sur de vraies réponses.\n", file=sys.stderr)
    profil = yaml.safe_load((RACINE / "profil.yaml").read_text(encoding="utf-8"))
    charges = json.loads(Path(a.entree).read_text(encoding="utf-8"))
    cx = ouvrir(a.base)
    repris = envoi.reprendre_interrompus(cx)
    if repris:
        print(f"{repris} envoi(s) interrompu(s) marqué(s) ambigus — non réémis.")
    b = traiter(cx, a.source, charges, corr, profil)
    print(f"lus {b.lus}  ·  actionnables {b.actionnables}  ·  notifiés {b.notifies}")
    if b.ecartes:
        print("écartés : " + ", ".join(f"{k}={v}" for k, v in sorted(b.ecartes.items())))
    return 0


def cmd_opportunites(a) -> int:
    """Uniquement ce sur quoi on peut encore déposer."""
    cx = ouvrir(a.base, lecture_seule=True)          # incapable d'écrire
    lignes = cx.execute(
        "SELECT o.*, a.ref_source FROM opportunites o JOIN avis a ON a.id=o.avis_id "
        "WHERE o.actionnable=1 AND o.peut_deposer=1 "
        "ORDER BY o.score DESC, o.echeance ASC").fetchall()
    if not lignes:
        print("Aucune opportunité ouverte. (Base lue correctement — ce n'est pas une panne.)")
        return 0
    for l in lignes:
        print(l["fiche"] if a.complet else
              f"[{l['score']:3}] {l['echeance'] or 'échéance ?':<26} {(l['intitule'] or '')[:56]}")
        if a.complet:
            print("\n" + "─" * 66 + "\n")
    print(f"\n{len(lignes)} opportunité(s) encore déposable(s).")
    return 0


def cmd_notifier(a) -> int:
    cx = ouvrir(a.base)
    envoi.reprendre_interrompus(cx)
    if a.pour_de_vrai:
        print("aucun transport configuré dans cet environnement", file=sys.stderr)
        return 3
    en_attente = envoi.a_envoyer(cx)
    print(f"{len(en_attente)} message(s) en attente (essai à blanc, rien n'est envoyé)")
    for l in en_attente:
        print(f"  · {l['source']}/{l['ref_source']}")
    return 0


def principal(argv=None) -> int:
    p = argparse.ArgumentParser(prog="radar", description="Radar de contrats logistiques")
    p.add_argument("--base", default="radar.sqlite3")
    s = p.add_subparsers(dest="cmd", required=True)

    r = s.add_parser("recenser", help="mesurer les clés réelles d'une source")
    r.add_argument("--source", required=True); r.add_argument("--echantillon", required=True)
    r.set_defaults(fn=cmd_recenser)

    t = s.add_parser("traiter", help="traiter un lot de réponses")
    t.add_argument("--source", required=True); t.add_argument("--entree", required=True)
    t.set_defaults(fn=cmd_traiter)

    o = s.add_parser("opportunites", help="les marchés encore déposables")
    o.add_argument("--complet", action="store_true")
    o.set_defaults(fn=cmd_opportunites)

    n = s.add_parser("notifier", help="vider la file d'envoi")
    n.add_argument("--pour-de-vrai", action="store_true")
    n.set_defaults(fn=cmd_notifier)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(principal())
