"""Accès à la base. Ouvre en lecture seule quand on ne fait que lire.

Sur le projet précédent, un outil d'audit annoncé « sans modification » a écrit
298 lignes en double dans la base active. Un outil de lecture doit être
INCAPABLE d'écrire, pas simplement promettre de ne pas le faire.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ouvrir(chemin, lecture_seule: bool = False) -> sqlite3.Connection:
    if lecture_seule:
        uri = f"file:{Path(chemin).resolve()}?mode=ro"
        cx = sqlite3.connect(uri, uri=True)
    else:
        cx = sqlite3.connect(chemin)
        cx.executescript(SCHEMA.read_text(encoding="utf-8"))
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys = ON")
    return cx


def enregistrer_reponse(cx, source: str, ref: str, charge: dict, empreinte: str = "") -> int:
    """Écrit la réponse brute. N'écrase jamais rien : elle s'ajoute."""
    t = maintenant()
    cx.execute(
        "INSERT INTO avis(source, ref_source, empreinte, premiere_vue, derniere_vue) "
        "VALUES(?,?,?,?,?) ON CONFLICT(source, ref_source) DO UPDATE SET "
        "derniere_vue=excluded.derniere_vue, empreinte=excluded.empreinte",
        (source, ref, empreinte, t, t))
    avis_id = cx.execute(
        "SELECT id FROM avis WHERE source=? AND ref_source=?", (source, ref)).fetchone()["id"]
    cx.execute(
        "INSERT OR IGNORE INTO reponses(avis_id, lue_le, charge) VALUES(?,?,?)",
        (avis_id, t, json.dumps(charge, ensure_ascii=False)))
    return avis_id


def reponses_fusionnees(cx, avis_id: int) -> dict:
    """Relit TOUTES les réponses et les fusionne, de la plus ancienne à la plus
    récente. C'est le correctif du bug « valeur revenue à l'ancienne » : ne
    jamais laisser SQLite choisir de quelle ligne vient une colonne."""
    fusion: dict = {}
    for ligne in cx.execute(
            "SELECT charge FROM reponses WHERE avis_id=? ORDER BY lue_le, id", (avis_id,)):
        fusion.update(json.loads(ligne["charge"]))
    return fusion
