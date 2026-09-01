#!/usr/bin/env python3
"""Remplace la base du bot par une base retraitee — avec filet.

    python tools/remplacer_base.py --verifier    controle seul, ne touche a rien
    python tools/remplacer_base.py --appliquer   remplace apres controle

Rien n'est ecrase sans une sauvegarde horodatee de la base actuelle, et le
remplacement est refuse si le candidat perd la moindre donnee
operationnelle (annonces, alertes, retours, filigrane).
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTUELLE = ROOT / "data" / "carsniper.db"
CANDIDATE = ROOT / "data" / "carsniper.V2.db"

# Ce qui ne doit JAMAIS diminuer : ce sont des faits, pas des calculs.
INTOUCHABLES = ["listings", "alerts", "feedback", "listing_snapshots"]
# Ce qui a le droit de changer : ce sont des resultats recalcules.
RECALCULES = ["valuations", "scores", "listing_defects", "defects"]


def compte(con, table: str) -> int:
    try:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.Error:
        return -1


def filigranes(con) -> set:
    try:
        return {r[0] for r in con.execute("SELECT value FROM meta")}
    except sqlite3.Error:
        return set()


def verifier() -> bool:
    for p in (ACTUELLE, CANDIDATE):
        if not p.exists():
            print(f"[ARRET] base introuvable : {p}")
            return False

    a = sqlite3.connect(f"file:{ACTUELLE}?mode=ro", uri=True)
    b = sqlite3.connect(f"file:{CANDIDATE}?mode=ro", uri=True)

    if b.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        print("[ARRET] la base candidate est corrompue")
        return False
    print("[OK] integrite SQLite de la candidate")

    bloquant = False
    print("\n  donnees qui ne doivent jamais diminuer")
    for t in INTOUCHABLES:
        na, nb = compte(a, t), compte(b, t)
        etat = "OK" if nb >= na else "PERTE"
        if nb < na:
            bloquant = True
        print(f"   [{etat:<5}] {t:<20} {na:>7} -> {nb:>7}")

    print("\n  resultats recalcules (peuvent varier)")
    for t in RECALCULES:
        print(f"   [info ] {t:<20} {compte(a, t):>7} -> {compte(b, t):>7}")

    fa, fb = filigranes(a), filigranes(b)
    if fa - fb:
        print(f"\n[ARRET] filigranes perdus : {fa - fb}")
        bloquant = True
    else:
        print(f"\n[OK] filigranes conserves ({len(fb)})")

    # Une base sans evaluation ne sert a rien : autant garder l'ancienne.
    if compte(b, "scores") < compte(a, "scores"):
        print("[ARRET] la candidate a MOINS de scores que la base actuelle")
        bloquant = True

    a.close()
    b.close()
    print("\n" + ("REMPLACEMENT REFUSE" if bloquant else "REMPLACEMENT POSSIBLE"))
    return not bloquant


def appliquer() -> int:
    if not verifier():
        return 1
    horo = datetime.now().strftime("%Y%m%d-%H%M%S")
    sauve = ACTUELLE.with_name(f"carsniper.AVANT-{horo}.db")
    print(f"\nsauvegarde de la base actuelle -> {sauve.name}")
    shutil.copy2(ACTUELLE, sauve)
    print(f"remplacement par {CANDIDATE.name}")
    shutil.copy2(CANDIDATE, ACTUELLE)
    con = sqlite3.connect(ACTUELLE)
    ok = con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    n = compte(con, "listings")
    con.close()
    print(f"[{'OK' if ok else 'ECHEC'}] base en place : {n} annonces")
    print(f"      retour arriere : cp data/{sauve.name} data/carsniper.db")
    return 0 if ok else 1


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--verifier"
    if arg == "--appliquer":
        sys.exit(appliquer())
    if arg != "--verifier":
        print(__doc__)
        sys.exit(2)
    sys.exit(0 if verifier() else 1)
