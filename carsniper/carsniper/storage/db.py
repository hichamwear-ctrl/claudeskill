"""Couche base de données — SQLite, zéro administration."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "carsniper.db"
SCHEMA = Path(__file__).with_name("schema.sql")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def _migrate(con: sqlite3.Connection) -> None:
    """Ajoute les colonnes manquantes AVANT l'exécution du schéma, sinon
    la création des index sur ces colonnes échoue sur une base existante."""
    tables = {r["name"] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "listings" not in tables:
        return
    cols = {r["name"] for r in con.execute("PRAGMA table_info(listings)")}
    for c in ("vkey", "vkey_loose", "price_type"):
        if c not in cols:
            con.execute(f"ALTER TABLE listings ADD COLUMN {c} TEXT")
    if "is_lease" not in cols:
        con.execute("ALTER TABLE listings ADD COLUMN is_lease INTEGER DEFAULT 0")

    # `pmin` est la reference qui decide du score, mais elle n'etait nulle
    # part persistee : check.py, `top` et le digest affichaient p25 ou p50,
    # c'est-a-dire un chiffre different de celui qui avait tranche.
    # Champs structures du site, jusqu'ici jetes par le parser.
    for c, t in (("site_model", "TEXT"), ("site_body", "TEXT"),
                 ("latitude", "REAL"), ("longitude", "REAL")):
        if c not in cols:
            con.execute(f"ALTER TABLE listings ADD COLUMN {c} {t}")

    # Colonnes du radar de prix. Les anciennes (true_cost_*, true_deal_value,
    # margin_pct) correspondaient a un calcul de marge qui n'existe plus :
    # on ne les detourne PAS vers un autre sens, on ajoute les bons noms.
    scols = {r["name"] for r in con.execute("PRAGMA table_info(scores)")}
    if scols:
        for c, t in (("score_prix", "REAL"), ("moins_chere_eur", "INTEGER"),
                     ("ecart_eur", "INTEGER"), ("ecart_pct", "REAL"),
                     ("fiabilite", "REAL")):
            if c not in scols:
                con.execute(f"ALTER TABLE scores ADD COLUMN {c} {t}")

    vcols = {r["name"] for r in con.execute("PRAGMA table_info(valuations)")}
    if vcols and "value_pmin" not in vcols:
        con.execute("ALTER TABLE valuations ADD COLUMN value_pmin INTEGER")
    con.commit()


def init(path: Path | str = DB_PATH) -> sqlite3.Connection:
    con = connect(path)
    _migrate(con)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.execute(
        "INSERT OR IGNORE INTO sources(name, kind) VALUES (?,?)",
        ("2ememain", "http"),
    )
    con.execute(
        "INSERT OR IGNORE INTO sources(name, kind) VALUES (?,?)",
        ("manual", "manual"),
    )
    con.commit()
    return con


def source_id(con: sqlite3.Connection, name: str) -> int:
    row = con.execute("SELECT id FROM sources WHERE name=?", (name,)).fetchone()
    if row is None:
        raise KeyError(f"source inconnue: {name}")
    return row["id"]


# ── Payload brut : jamais modifié, permet de tout retraiter ──

def _clean(text: str) -> str:
    """Retire les surrogates isolés : certaines annonces contiennent des
    emojis mal encodés qui font échouer l'écriture en base."""
    return text.encode("utf-8", "replace").decode("utf-8", "replace")


def store_raw(con, src_id: int, external_id: str, url: str, payload: dict) -> int:
    text = _clean(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    dup = con.execute(
        "SELECT id FROM raw_payloads WHERE source_id=? AND external_id=? AND payload_hash=?",
        (src_id, external_id, h),
    ).fetchone()
    if dup:
        return dup["id"]
    cur = con.execute(
        "INSERT INTO raw_payloads(source_id, external_id, url, payload_text, payload_hash) "
        "VALUES (?,?,?,?,?)",
        (src_id, external_id, url, text, h),
    )
    return cur.lastrowid


# ── Annonces ────────────────────────────────────────────────

LISTING_COLS = (
    "title description price_eur price_type is_lease mileage_km year fuel transmission "
    "power_kw location postal_code distance_km seller_type seller_id "
    "photo_count published_at url site_model site_body latitude longitude"
).split()


def upsert_listing(con, src_id: int, external_id: str, data: dict) -> tuple[int, bool]:
    """Retourne (listing_id, is_new)."""
    row = con.execute(
        "SELECT id, price_eur FROM listings WHERE source_id=? AND external_id=?",
        (src_id, external_id),
    ).fetchone()

    fields = {k: data.get(k) for k in LISTING_COLS}
    for k in ("title", "description", "location"):
        if isinstance(fields.get(k), str):
            fields[k] = _clean(fields[k])

    if row is None:
        cols = ["source_id", "external_id"] + LISTING_COLS
        vals = [src_id, external_id] + [fields[k] for k in LISTING_COLS]
        cur = con.execute(
            f"INSERT INTO listings({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            vals,
        )
        lid = cur.lastrowid
        snapshot(con, lid, fields.get("price_eur"), "active")
        return lid, True

    lid = row["id"]
    sets = ", ".join(f"{k}=?" for k in LISTING_COLS)
    con.execute(
        f"UPDATE listings SET {sets}, last_seen_at=?, status='active' WHERE id=?",
        [fields[k] for k in LISTING_COLS] + [now(), lid],
    )
    if row["price_eur"] != fields.get("price_eur"):
        snapshot(con, lid, fields.get("price_eur"), "active")
    return lid, False


def snapshot(con, listing_id: int, price: int | None, status: str) -> None:
    con.execute(
        "INSERT INTO listing_snapshots(listing_id, price_eur, status) VALUES (?,?,?)",
        (listing_id, price, status),
    )


def price_history(con, listing_id: int) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT observed_at, price_eur FROM listing_snapshots "
        "WHERE listing_id=? ORDER BY observed_at",
        (listing_id,),
    ).fetchall()


def known_external_ids(con, src_id: int) -> set[str]:
    return {
        r["external_id"]
        for r in con.execute(
            "SELECT external_id FROM listings WHERE source_id=?", (src_id,)
        )
    }


# ── Défauts : chargement du lexique en base ─────────────────

def load_defects(con, lexicon: dict) -> None:
    """Upsert sur `code` : ne supprime jamais la ligne, donc les clés
    étrangères depuis listing_defects restent valides."""
    for d in lexicon.get("defects", []):
        con.execute(
            "INSERT INTO defects("
            "code, category, severity, market_discount_low, market_discount_high, "
            "pro_cost_low, pro_cost_high, base_confidence, checklist_json) "
            "VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(code) DO UPDATE SET "
            "category=excluded.category, severity=excluded.severity, "
            "market_discount_low=excluded.market_discount_low, "
            "market_discount_high=excluded.market_discount_high, "
            "pro_cost_low=excluded.pro_cost_low, "
            "pro_cost_high=excluded.pro_cost_high, "
            "base_confidence=excluded.base_confidence, "
            "checklist_json=excluded.checklist_json",
            (
                d["code"], d["category"], d["severity"],
                d["market_discount"][0], d["market_discount"][1],
                d["pro_cost"][0], d["pro_cost"][1],
                d.get("base_confidence", 0.7),
                json.dumps(d.get("checklist", []), ensure_ascii=False),
            ),
        )
    con.commit()


def stats(con) -> dict:
    q = lambda s: con.execute(s).fetchone()[0]
    return {
        "annonces": q("SELECT COUNT(*) FROM listings"),
        "actives": q("SELECT COUNT(*) FROM listings WHERE status='active'"),
        "snapshots": q("SELECT COUNT(*) FROM listing_snapshots"),
        "defauts": q("SELECT COUNT(*) FROM listing_defects WHERE is_negated=0"),
        "scores": q("SELECT COUNT(*) FROM scores"),
        "alertes": q("SELECT COUNT(*) FROM alerts"),
    }


if __name__ == "__main__":
    import yaml

    con = init()
    lex = yaml.safe_load((ROOT / "config" / "defects.yaml").read_text(encoding="utf-8"))
    load_defects(con, lex)
    print(f"Base initialisée : {DB_PATH}")
    print(f"Défauts chargés  : {con.execute('SELECT COUNT(*) FROM defects').fetchone()[0]}")
    print(f'Tables           : ' + str(con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]))
