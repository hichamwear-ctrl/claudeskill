-- CAR SNIPER — schéma SQLite
-- Principe : raw_payloads est immuable. Tout le reste est recalculable.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ═══════════════════════════════════════════════════════════
-- SOURCES & COLLECTE
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    kind        TEXT NOT NULL,              -- http | manual
    enabled     INTEGER NOT NULL DEFAULT 1,
    config_json TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Payload brut, JAMAIS modifié. Permet de retraiter tout
-- l'historique quand le lexique ou la normalisation évoluent.
CREATE TABLE IF NOT EXISTS raw_payloads (
    id           INTEGER PRIMARY KEY,
    source_id    INTEGER NOT NULL REFERENCES sources(id),
    external_id  TEXT NOT NULL,
    url          TEXT,
    fetched_at   TEXT NOT NULL DEFAULT (datetime('now')),
    payload_text TEXT NOT NULL,
    payload_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_raw_ext  ON raw_payloads(source_id, external_id);
CREATE INDEX IF NOT EXISTS ix_raw_hash ON raw_payloads(payload_hash);

-- ═══════════════════════════════════════════════════════════
-- RÉFÉRENTIEL VÉHICULES
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS vehicle_refs (
    id                INTEGER PRIMARY KEY,
    make              TEXT NOT NULL,
    model             TEXT NOT NULL,
    generation        TEXT,
    body              TEXT,
    year_from         INTEGER,
    year_to           INTEGER,
    engine_code       TEXT,
    fuel              TEXT,
    power_kw          INTEGER,
    transmission      TEXT,
    drivetrain        TEXT,
    segment           TEXT,
    popularity_score  REAL DEFAULT 0.5,
    weaknesses_json   TEXT,                 -- faiblesses connues du modèle
    UNIQUE(make, model, generation, engine_code, transmission)
);
CREATE INDEX IF NOT EXISTS ix_vref_lookup ON vehicle_refs(make, model, year_from, year_to);

-- ═══════════════════════════════════════════════════════════
-- ANNONCES
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS listings (
    id             INTEGER PRIMARY KEY,
    source_id      INTEGER NOT NULL REFERENCES sources(id),
    external_id    TEXT NOT NULL,
    url            TEXT,

    first_seen_at  TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at   TEXT NOT NULL DEFAULT (datetime('now')),
    published_at   TEXT,
    status         TEXT NOT NULL DEFAULT 'active',   -- active | gone

    title          TEXT,
    description    TEXT,
    price_eur      INTEGER,
    price_type     TEXT,          -- FIXED, MIN_BID, NOTK...
    is_lease       INTEGER DEFAULT 0,
    mileage_km     INTEGER,
    year           INTEGER,
    fuel           TEXT,
    transmission   TEXT,
    power_kw       INTEGER,

    location       TEXT,
    postal_code    TEXT,
    distance_km    REAL,

    seller_type    TEXT,                    -- particulier | pro
    seller_id      TEXT,
    photo_count    INTEGER DEFAULT 0,

    vehicle_ref_id INTEGER REFERENCES vehicle_refs(id),
    vkey           TEXT,          -- cache de normalisation
    vkey_loose     TEXT,
    site_model     TEXT,          -- modele DECLARE par 2ememain (56 % des cas)
    site_body      TEXT,          -- carrosserie DECLAREE par 2ememain (46 %)
    latitude       REAL,
    longitude      REAL,
    norm_confidence REAL,
    fingerprint    TEXT,
    duplicate_of   INTEGER REFERENCES listings(id),

    enriched_at    TEXT,
    UNIQUE(source_id, external_id)
);
CREATE INDEX IF NOT EXISTS ix_lst_status  ON listings(status, last_seen_at);
CREATE INDEX IF NOT EXISTS ix_lst_comp    ON listings(vehicle_ref_id, year, mileage_km, status);
CREATE INDEX IF NOT EXISTS ix_lst_fp      ON listings(fingerprint);
CREATE INDEX IF NOT EXISTS ix_lst_price   ON listings(price_eur);
CREATE INDEX IF NOT EXISTS ix_lst_vkey    ON listings(vkey, year, mileage_km);
-- Le pool de comparables filtre sur vkey_loose : sans cet index, chaque
-- evaluation faisait un balayage complet des 53 000 annonces.
CREATE INDEX IF NOT EXISTS ix_lst_vloose  ON listings(vkey_loose, status, price_eur);

-- ═══════════════════════════════════════════════════════════
-- MARKET MEMORY — l'actif qui prend de la valeur
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS listing_snapshots (
    id          INTEGER PRIMARY KEY,
    listing_id  INTEGER NOT NULL REFERENCES listings(id),
    observed_at TEXT NOT NULL DEFAULT (datetime('now')),
    price_eur   INTEGER,
    status      TEXT
);
CREATE INDEX IF NOT EXISTS ix_snap ON listing_snapshots(listing_id, observed_at);

-- Une annonce disparue n'est PAS une vente. On stocke une probabilité.
CREATE TABLE IF NOT EXISTS listing_outcomes (
    id                    INTEGER PRIMARY KEY,
    listing_id            INTEGER NOT NULL UNIQUE REFERENCES listings(id),
    disappeared_at        TEXT,
    days_online           INTEGER,
    price_at_disappearance INTEGER,
    price_drops_count     INTEGER DEFAULT 0,
    total_drop_eur        INTEGER DEFAULT 0,
    p_sold                REAL,             -- jamais sold = true
    inferred_reason       TEXT              -- sold | withdrawn | expired | reposted | unknown
);

-- ═══════════════════════════════════════════════════════════
-- DÉFAUTS
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS defects (
    id                   INTEGER PRIMARY KEY,
    code                 TEXT NOT NULL UNIQUE,
    category             TEXT NOT NULL,     -- cosmetic|maintenance|mechanical|major
    severity             INTEGER NOT NULL,  -- 1..4
    market_discount_low  INTEGER,
    market_discount_high INTEGER,
    pro_cost_low         INTEGER,
    pro_cost_high        INTEGER,
    base_confidence      REAL,
    checklist_json       TEXT
);

CREATE TABLE IF NOT EXISTS listing_defects (
    id           INTEGER PRIMARY KEY,
    listing_id   INTEGER NOT NULL REFERENCES listings(id),
    defect_id    INTEGER NOT NULL REFERENCES defects(id),
    matched_text TEXT,
    context      TEXT,
    is_negated   INTEGER NOT NULL DEFAULT 0,
    confidence   REAL,
    detected_by  TEXT DEFAULT 'lexicon',    -- lexicon | llm
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_ldef ON listing_defects(listing_id);

-- ═══════════════════════════════════════════════════════════
-- ANALYSE
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS valuations (
    id               INTEGER PRIMARY KEY,
    listing_id       INTEGER NOT NULL REFERENCES listings(id),
    computed_at      TEXT NOT NULL DEFAULT (datetime('now')),
    comparable_count INTEGER,
    value_pmin       INTEGER,              -- reference REELLE du score
    value_p25        INTEGER,
    value_p50        INTEGER,
    value_p75        INTEGER,
    method           TEXT,                  -- weighted_median | insufficient_data
    confidence       REAL,
    comparables_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_val ON valuations(listing_id, computed_at);

CREATE TABLE IF NOT EXISTS scores (
    id                INTEGER PRIMARY KEY,
    listing_id        INTEGER NOT NULL REFERENCES listings(id),
    computed_at       TEXT NOT NULL DEFAULT (datetime('now')),
    deal_type         TEXT,                 -- A (saine) | B (défaut)

    price_advantage   REAL,
    market_score      REAL,
    repair_score      REAL,
    risk_score        REAL,
    resale_score      REAL,
    confidence_score  REAL,
    urgency_score     REAL,

    deal_score        REAL,
    -- ── radar de prix (v4) : ce que le score mesure vraiment ──
    score_prix          REAL,          -- issu du seul ecart de prix
    moins_chere_eur     INTEGER,       -- la VRAIE moins chere comparable
    ecart_eur           INTEGER,       -- prix annonce - moins chere
    ecart_pct           REAL,
    fiabilite           REAL,          -- qualite de la comparaison, 0.45-1.00
    tier              TEXT,                 -- good | great | sniper | below

    true_cost_low     INTEGER,
    true_cost_high    INTEGER,
    true_deal_value   INTEGER,
    margin_pct        REAL,

    explanation_json  TEXT,
    weights_version   TEXT
);
CREATE INDEX IF NOT EXISTS ix_sc_rank ON scores(deal_score DESC, computed_at DESC);
CREATE INDEX IF NOT EXISTS ix_sc_lst  ON scores(listing_id, computed_at);

-- ═══════════════════════════════════════════════════════════
-- UTILISATEUR
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS profiles (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    active        INTEGER NOT NULL DEFAULT 1,
    criteria_json TEXT NOT NULL,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id                  INTEGER PRIMARY KEY,
    listing_id          INTEGER NOT NULL REFERENCES listings(id),
    profile_id          INTEGER REFERENCES profiles(id),
    sent_at             TEXT NOT NULL DEFAULT (datetime('now')),
    tier                TEXT,
    deal_score          REAL,
    trigger_reason      TEXT,               -- new | price_drop | score_change
    telegram_message_id INTEGER
);
CREATE INDEX IF NOT EXISTS ix_alert ON alerts(listing_id, sent_at);

CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY,
    alert_id   INTEGER REFERENCES alerts(id),
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    reaction   TEXT NOT NULL,               -- good|bad|would_buy|not_interested|bought
    note       TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════════════════════
-- EXPLOITATION
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS run_log (
    id          INTEGER PRIMARY KEY,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    job         TEXT,                       -- fast_loop | night_loop | bootstrap
    seen        INTEGER DEFAULT 0,
    new_items   INTEGER DEFAULT 0,
    errors      INTEGER DEFAULT 0,
    notes       TEXT
);

-- Photographie complete d'une evaluation au moment ou elle a compte.
-- Sans elle, une alerte envoyee est une boite noire : impossible de dire
-- APRES COUP pourquoi le bot a juge cette voiture interessante.
CREATE TABLE IF NOT EXISTS decisions (
    id                  INTEGER PRIMARY KEY,
    listing_id          INTEGER NOT NULL REFERENCES listings(id),
    alert_id            INTEGER REFERENCES alerts(id),
    decided_at          TEXT NOT NULL DEFAULT (datetime('now')),
    envoyee             INTEGER NOT NULL DEFAULT 0,
    deal_score          REAL,
    tier                TEXT,
    confidence          REAL,
    prix_affiche        INTEGER,
    prix_negocie        INTEGER,
    nego_taux           REAL,
    reference_key       TEXT,          -- pmin | p25 | p50
    reference_eur       INTEGER,
    value_pmin          INTEGER,
    value_p25           INTEGER,
    value_p50           INTEGER,
    value_p75           INTEGER,
    comparable_count    INTEGER,
    market_confidence   REAL,
    market_method       TEXT,
    pool_verifie        REAL,
    iqr_ratio           REAL,
    repair_low          INTEGER,
    repair_high         INTEGER,
    true_deal_value     INTEGER,
    marge_affichee      INTEGER,
    part_hypothese      REAL,
    risk_score          REAL,
    defauts_json        TEXT,          -- code, negation, evidence, couts
    comparables_json    TEXT,          -- les annonces ayant servi de base
    limites_json        TEXT,          -- ce qui a limite la confiance
    plafonds_json       TEXT,          -- garde-fous declenches
    refus_json          TEXT,          -- criteres de profil non respectes
    explication_json    TEXT,
    weights_version     TEXT
);
CREATE INDEX IF NOT EXISTS ix_decisions ON decisions(listing_id, decided_at);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Etat du recalcul nocturne. Il joue le meme role que le filigrane du
-- radar : au tout premier passage on recalcule TOUT sans rien envoyer, on
-- note ou en etait chaque annonce, et les passages suivants ne notifient
-- que ce qui a REELLEMENT change (franchissement du seuil, baisse de prix).
-- Sans cet etat, le premier recalcul d'une base de 50 000 annonces aurait
-- envoye des milliers de notifications d'un coup ; avec lui, aucun plafond
-- artificiel n'est necessaire.
CREATE TABLE IF NOT EXISTS recalc_state (
    listing_id  INTEGER PRIMARY KEY REFERENCES listings(id) ON DELETE CASCADE,
    deal_score  REAL,
    price_eur   INTEGER,
    seen_at     TEXT NOT NULL
);
