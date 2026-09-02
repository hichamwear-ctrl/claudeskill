PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS avis (
    id           INTEGER PRIMARY KEY,
    source       TEXT NOT NULL,
    ref_source   TEXT NOT NULL,
    empreinte    TEXT NOT NULL,
    premiere_vue TEXT NOT NULL,
    derniere_vue TEXT NOT NULL,
    UNIQUE (source, ref_source)
);
CREATE INDEX IF NOT EXISTS idx_avis_empreinte ON avis(empreinte);

-- Réponse brute, écrite une fois, jamais modifiée : tout est recalculable.
CREATE TABLE IF NOT EXISTS reponses (
    id      INTEGER PRIMARY KEY,
    avis_id INTEGER NOT NULL REFERENCES avis(id) ON DELETE CASCADE,
    lue_le  TEXT NOT NULL,
    charge  TEXT NOT NULL,
    UNIQUE (avis_id, lue_le)
);

-- Données calculées, séparées des données reçues.
CREATE TABLE IF NOT EXISTS opportunites (
    avis_id       INTEGER PRIMARY KEY REFERENCES avis(id) ON DELETE CASCADE,
    nature        TEXT NOT NULL,      -- OPPORTUNITE_DIRECTE | SIGNAL_COMMERCIAL
    statut        TEXT NOT NULL,      -- POSTULABLE | A_VERIFIER | NON_POSTULABLE
    eligibilite   TEXT,               -- ELIGIBLE | A_VERIFIER | NON_ELIGIBLE
    zone          TEXT,
    familles      TEXT,
    intitule      TEXT,
    acheteur      TEXT,
    montant       REAL,
    echeance      TEXT,
    jours_restants INTEGER,
    score         INTEGER NOT NULL DEFAULT 0,
    detail_score  TEXT,
    motif         TEXT,
    fiche         TEXT,
    calcule_le    TEXT NOT NULL,
    etat          TEXT NOT NULL DEFAULT 'non_vu',
    etat_maj      TEXT
);
CREATE INDEX IF NOT EXISTS idx_opp_statut ON opportunites(statut, score DESC);

-- Marchés attribués : jamais notifiés, gardés pour le calendrier.
CREATE TABLE IF NOT EXISTS attributions (
    avis_id       INTEGER PRIMARY KEY REFERENCES avis(id) ON DELETE CASCADE,
    acheteur      TEXT,
    titulaire     TEXT,
    montant       REAL,
    duree_mois    INTEGER,
    prestation    TEXT,
    conclu_le     TEXT,
    renouvellement TEXT,
    fiabilite     TEXT NOT NULL,
    commentaire   TEXT
);
CREATE INDEX IF NOT EXISTS idx_attr_renouv ON attributions(renouvellement);

CREATE TABLE IF NOT EXISTS filigrane (
    source TEXT PRIMARY KEY, valeur TEXT, gele INTEGER NOT NULL DEFAULT 0,
    raison TEXT, maj_le TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS envois (
    id         INTEGER PRIMARY KEY,
    source     TEXT NOT NULL, ref_source TEXT NOT NULL,
    corps      TEXT NOT NULL,
    etat       TEXT NOT NULL DEFAULT 'a_envoyer',
    tentatives INTEGER NOT NULL DEFAULT 0, erreur TEXT,
    cree_le    TEXT NOT NULL, maj_le TEXT NOT NULL,
    UNIQUE (source, ref_source)
);
CREATE INDEX IF NOT EXISTS idx_envois_etat ON envois(etat, id);

CREATE TABLE IF NOT EXISTS verrou (
    nom TEXT PRIMARY KEY, porteur TEXT NOT NULL,
    pris_le TEXT NOT NULL, battement REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY, source TEXT NOT NULL,
    debut TEXT NOT NULL, fin TEXT, issue TEXT,
    lus INTEGER NOT NULL DEFAULT 0,
    postulables INTEGER NOT NULL DEFAULT 0,
    notifies INTEGER NOT NULL DEFAULT 0,
    echecs_lecture INTEGER NOT NULL DEFAULT 0,
    detail TEXT
);
