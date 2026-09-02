PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Une ligne par avis vu, toutes sources confondues.
CREATE TABLE IF NOT EXISTS avis (
    id            INTEGER PRIMARY KEY,
    source        TEXT NOT NULL,
    ref_source    TEXT NOT NULL,
    premiere_vue  TEXT NOT NULL,
    derniere_vue  TEXT NOT NULL,
    UNIQUE (source, ref_source)
);

-- La réponse brute, écrite une fois, jamais modifiée. Tout est recalculable
-- à partir d'elle : c'est ce qui permet de réparer un bug d'extraction sans
-- re-collecter une seule annonce.
CREATE TABLE IF NOT EXISTS reponses (
    id         INTEGER PRIMARY KEY,
    avis_id    INTEGER NOT NULL REFERENCES avis(id) ON DELETE CASCADE,
    lue_le     TEXT NOT NULL,
    charge     TEXT NOT NULL,
    UNIQUE (avis_id, lue_le)
);

-- Données CALCULÉES, strictement séparées des données reçues : un nouvel
-- enregistrement de réponse ne peut pas écraser une valeur calculée.
CREATE TABLE IF NOT EXISTS opportunites (
    avis_id        INTEGER PRIMARY KEY REFERENCES avis(id) ON DELETE CASCADE,
    statut_action  TEXT NOT NULL,      -- ouvert | echeance_inconnue | cloture | attribue | informatif
    actionnable    INTEGER NOT NULL,
    statut_elig    TEXT,
    peut_deposer   INTEGER,
    echeance       TEXT,
    montant        REAL,
    acheteur       TEXT,
    intitule       TEXT,
    score          INTEGER NOT NULL DEFAULT 0,
    fiche          TEXT,
    motif          TEXT,
    calcule_le     TEXT NOT NULL,
    -- état de traitement, piloté par l'exploitant seul
    etat           TEXT NOT NULL DEFAULT 'non_vu',
    etat_maj       TEXT
);
CREATE INDEX IF NOT EXISTS idx_opp_action ON opportunites(actionnable, echeance);
CREATE INDEX IF NOT EXISTS idx_opp_etat   ON opportunites(etat);

CREATE TABLE IF NOT EXISTS filigrane (
    source     TEXT PRIMARY KEY,
    valeur     TEXT,
    gele       INTEGER NOT NULL DEFAULT 0,
    raison     TEXT,
    maj_le     TEXT NOT NULL
);

-- File d'envoi : indexée sur (source, ref_source), jamais sur avis.id —
-- l'identifiant interne change après un rollback et refait partir les alertes.
CREATE TABLE IF NOT EXISTS envois (
    id          INTEGER PRIMARY KEY,
    source      TEXT NOT NULL,
    ref_source  TEXT NOT NULL,
    corps       TEXT NOT NULL,
    etat        TEXT NOT NULL DEFAULT 'a_envoyer',   -- a_envoyer|en_cours|delivre|ambigu|echec
    tentatives  INTEGER NOT NULL DEFAULT 0,
    erreur      TEXT,
    cree_le     TEXT NOT NULL,
    maj_le      TEXT NOT NULL,
    UNIQUE (source, ref_source)
);
CREATE INDEX IF NOT EXISTS idx_envois_etat ON envois(etat, id);

CREATE TABLE IF NOT EXISTS verrou (
    nom       TEXT PRIMARY KEY,
    porteur   TEXT NOT NULL,
    pris_le   TEXT NOT NULL,
    battement REAL NOT NULL
);

-- Le sondage est tracé séparément de son résultat : zéro opportunité après un
-- cycle réussi est un état normal, pas une panne.
CREATE TABLE IF NOT EXISTS cycles (
    id          INTEGER PRIMARY KEY,
    source      TEXT NOT NULL,
    debut       TEXT NOT NULL,
    fin         TEXT,
    issue       TEXT,
    lus         INTEGER NOT NULL DEFAULT 0,
    actionnables INTEGER NOT NULL DEFAULT 0,
    notifies    INTEGER NOT NULL DEFAULT 0,
    echecs_lecture INTEGER NOT NULL DEFAULT 0,
    detail      TEXT
);
