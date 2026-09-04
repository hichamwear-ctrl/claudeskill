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
    type          TEXT NOT NULL,      -- DIRECT|RENFORCEMENT|A_CONSTRUIRE|PROSPECT|REJET
    moteur        TEXT,               -- CAPTER | DEVELOPPER
    action        TEXT,               -- POSTULER | CONTACTER LE TITULAIRE | ...
    role          TEXT,               -- PRESTATAIRE | FOURNISSEUR | A_VERIFIER
    statut        TEXT NOT NULL,      -- OUVERT|BIENTOT_FERME|DEPASSE|ATTRIBUE|INCONNUE
    zone          TEXT,
    familles      TEXT,
    marche_ref    TEXT,               -- marché parent quand l'opportunité est un lot
    lot_numero    TEXT,
    marge         TEXT,               -- valeur ou « NON MESURÉE »
    journal       TEXT,               -- les 16 questions et leurs réponses
    intitule      TEXT,
    acheteur      TEXT,
    montant       REAL,
    devise        TEXT,
    duree_mois    INTEGER,
    cadence       TEXT,
    contact       TEXT,
    exigences     TEXT,
    echeance      TEXT,
    jours_restants INTEGER,
    distance_km   REAL,               -- distance publiée au dépôt, NULL = NON PUBLIÉE
    -- B · l'état NORMALISÉ de la procédure. Colonne, pas texte noyé dans la
    -- fiche : sans elle, impossible de détecter une transition ni de requêter.
    etat_procedure TEXT,
    confiance_etat TEXT,
    type_information TEXT,            -- A · ce que la source appelle l'objet
    nature        TEXT,               -- C · FAIT | SIGNAL | HYPOTHÈSE
    -- Qui achète : public ou privé. C'est un fait sur le DEMANDEUR, pas sur la
    -- source — un besoin public peut arriver par un moteur de recherche.
    secteur       TEXT,
    -- FIABILITÉ DE L'INFORMATION — jamais mélangée à la valeur économique.
    -- Une information peu fiable peut être excellente commercialement.
    fiabilite     TEXT,
    fiabilite_motif TEXT,
    score         INTEGER NOT NULL DEFAULT 0,
    -- 0 quand aucun fait économique n'a été observé. Le rapport doit
    -- alors écrire « — » : un nombre affiché prétend être une mesure.
    score_mesurable INTEGER NOT NULL DEFAULT 1,
    manques       TEXT,       -- capacités qui manquent, en JSON
    leviers       TEXT,       -- comment les combler, en JSON
    risques       TEXT,       -- ce qui peut faire perdre l'affaire
    ca_ligne      TEXT,       -- « 15 000 €/mois — PUBLIÉ »
    ca_mensuel    REAL,
    ca_etat       TEXT,       -- PUBLIÉ | ESTIMATION | NON PUBLIÉ
    capacite      TEXT,       -- « 8/10 véhicules » ou « en l'état »

    detail_score  TEXT,
    motif         TEXT,
    fiche         TEXT,
    calcule_le    TEXT NOT NULL,
    etat          TEXT NOT NULL DEFAULT 'non_vu',
    etat_maj      TEXT
);
CREATE INDEX IF NOT EXISTS idx_opp_type ON opportunites(type, score DESC);
CREATE INDEX IF NOT EXISTS idx_opp_moteur ON opportunites(moteur, score DESC);
CREATE INDEX IF NOT EXISTS idx_opp_marche ON opportunites(marche_ref);

-- Registre des sources : une source n'est jamais dite consultée sans trace.
CREATE TABLE IF NOT EXISTS sources (
    nom          TEXT PRIMARY KEY,
    famille      TEXT NOT NULL,
    methode      TEXT NOT NULL,
    etat         TEXT NOT NULL DEFAULT 'JAMAIS CONSULTÉE',
    cycle        TEXT,
    derniere_consultation TEXT,
    derniere_erreur TEXT,
    motif_indisponible TEXT,
    lues         INTEGER NOT NULL DEFAULT 0,
    retenues     INTEGER NOT NULL DEFAULT 0,
    contacts     INTEGER NOT NULL DEFAULT 0,
    contrats     INTEGER NOT NULL DEFAULT 0
);

-- Rendement par requête de découverte : ce qui fait monter ou descendre une
-- recherche Google. Visible et réversible — jamais une boîte noire.
CREATE TABLE IF NOT EXISTS requetes (
    texte      TEXT PRIMARY KEY,
    famille    TEXT,
    zone       TEXT,
    langue     TEXT,
    poids      REAL NOT NULL DEFAULT 0,
    lancee     INTEGER NOT NULL DEFAULT 0,
    resultats  INTEGER NOT NULL DEFAULT 0,
    retenues   INTEGER NOT NULL DEFAULT 0,
    contacts   INTEGER NOT NULL DEFAULT 0,
    contrats   INTEGER NOT NULL DEFAULT 0,
    derniere_execution TEXT
);

-- Provenances : un même besoin vu sur Google ET au BDA garde ses deux origines.
CREATE TABLE IF NOT EXISTS provenances (
    id          INTEGER PRIMARY KEY,
    avis_id     INTEGER NOT NULL REFERENCES avis(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,
    url         TEXT,
    requete     TEXT,
    consulte_le TEXT,
    UNIQUE (avis_id, source, url)
);

-- Marchés attribués : jamais notifiés, gardés pour le calendrier.
CREATE TABLE IF NOT EXISTS attributions (
    avis_id       INTEGER PRIMARY KEY REFERENCES avis(id) ON DELETE CASCADE,
    acheteur      TEXT,
    titulaire     TEXT,
    montant       REAL,
    duree_mois    INTEGER,
    prestation    TEXT,
    zone          TEXT,
    lots          TEXT,
    conclu_le     TEXT,
    debut         TEXT,
    fin           TEXT,
    renouvellement TEXT,
    fiabilite     TEXT NOT NULL,
    commentaire   TEXT,
    contact       TEXT,
    taille_apparente TEXT,
    besoin_sous_traitance TEXT
);

-- Registre des entreprises : une entreprise découverte ne disparaît jamais,
-- elle devient une entité surveillée qui produit ses propres recherches.
CREATE TABLE IF NOT EXISTS entreprises (
    cle           TEXT PRIMARY KEY,
    nom           TEXT NOT NULL,
    domaine       TEXT,
    etat          TEXT NOT NULL DEFAULT 'DÉCOUVERTE',
    motifs        TEXT,
    origine       TEXT,
    decouverte_le TEXT,
    derniere_visite TEXT,
    besoins_detectes INTEGER NOT NULL DEFAULT 0,
    marches_gagnes   INTEGER NOT NULL DEFAULT 0,
    montant_gagne    REAL NOT NULL DEFAULT 0,
    bce           TEXT,
    contact       TEXT,
    motif_ecart   TEXT,
    profondeur    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_entreprises_etat ON entreprises(etat);
CREATE INDEX IF NOT EXISTS idx_attr_renouv ON attributions(renouvellement);

-- Incidents : une ligne qui n'a pas pu être traitée est CONSERVÉE avec son
-- contenu brut et son motif. Elle ne disparaît pas — elle reste consultable,
-- et son motif est traçable ligne par ligne.
CREATE TABLE IF NOT EXISTS incidents (
    id          INTEGER PRIMARY KEY,
    ligne       INTEGER,               -- rang dans le lot d'entrée
    source      TEXT NOT NULL,
    reference   TEXT,
    etape       TEXT NOT NULL,         -- collecte | normalisation | extraction
    motif       TEXT NOT NULL,
    charge      TEXT,                  -- le brut, tel quel
    mode        TEXT NOT NULL,
    cree_le     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_incidents_etape ON incidents(etape);

-- MÉMOIRE DU VOCABULAIRE DÉCOUVERT.
--
-- Quand un portail emploie une formulation jamais rencontrée, elle n'est pas
-- devinée : elle est CONSERVÉE ici, avec son contexte, pour être interprétée
-- une fois — puis reconnue. Tant que personne n'a tranché, `interpretation`
-- reste NULL et l'état de la procédure reste INCONNU.
CREATE TABLE IF NOT EXISTS vocabulaire (
    id            INTEGER PRIMARY KEY,
    source        TEXT NOT NULL,
    champ         TEXT NOT NULL,      -- statut | type_information
    expression    TEXT NOT NULL,      -- ce que le portail a écrit, tel quel
    langue        TEXT,               -- déclarée par l'adaptateur, jamais devinée
    contexte      TEXT,               -- l'intitulé où elle est apparue
    interpretation TEXT,              -- NULL = pas encore tranché
    confiance     TEXT,
    preuve        TEXT,
    version       INTEGER NOT NULL DEFAULT 0,   -- s'incrémente à chaque révision
    occurrences   INTEGER NOT NULL DEFAULT 1,
    vu_le         TEXT NOT NULL,
    revise_le     TEXT,
    revise_par    TEXT,
    UNIQUE (source, champ, expression)
);
CREATE INDEX IF NOT EXISTS idx_voc_a_trancher
    ON vocabulaire(source) WHERE interpretation IS NULL;

-- Une révision n'efface JAMAIS l'ancienne lecture : elle l'archive. Une
-- mauvaise interprétation corrigée plus tard doit rester visible, sinon on ne
-- saura jamais quelles fiches ont été produites avec la version fausse.
CREATE TABLE IF NOT EXISTS vocabulaire_historique (
    id             INTEGER PRIMARY KEY,
    vocabulaire_id INTEGER NOT NULL REFERENCES vocabulaire(id) ON DELETE CASCADE,
    version        INTEGER,
    interpretation TEXT,
    confiance      TEXT,
    motif          TEXT,
    remplace_le    TEXT NOT NULL,
    par            TEXT
);

CREATE TABLE IF NOT EXISTS filigrane (
    source TEXT PRIMARY KEY, valeur TEXT, gele INTEGER NOT NULL DEFAULT 0,
    raison TEXT, maj_le TEXT NOT NULL
);

-- FIL DE VIE D'UNE OPPORTUNITÉ.
--
-- 03/09 POSTULABLE · 14/09 FERMÉ · 28/09 ATTRIBUÉ, ce n'est pas trois
-- opportunités : c'est UNE opportunité, trois observations, deux transitions.
-- Une collecte qui ne change rien n'écrit RIEN — sinon on fabriquerait un
-- événement commercial par passage du collecteur.
CREATE TABLE IF NOT EXISTS etats_historique (
    id                 INTEGER PRIMARY KEY,
    avis_id            INTEGER NOT NULL REFERENCES avis(id) ON DELETE CASCADE,
    ancien_etat        TEXT,               -- NULL = première observation
    nouvel_etat        TEXT NOT NULL,
    ancienne_confiance TEXT,
    nouvelle_confiance TEXT,
    preuve             TEXT NOT NULL,      -- la preuve qui a fait basculer
    source             TEXT NOT NULL,
    -- « le portail a changé » n'est PAS « nous avons changé notre lecture ».
    -- Les confondre ferait croire à un mouvement du marché là où il n'y a
    -- qu'une correction de notre côté.
    origine            TEXT NOT NULL,      -- collecte | revision_vocabulaire
    version_vocabulaire INTEGER,
    constate_le        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hist_avis ON etats_historique(avis_id, id);

CREATE TABLE IF NOT EXISTS envois (
    id         INTEGER PRIMARY KEY,
    source     TEXT NOT NULL, ref_source TEXT NOT NULL,
    -- Pourquoi on alerte. « La première fois » et « le marché vient de
    -- s'ouvrir » sont DEUX événements, pas un doublon : sans ce motif dans la
    -- clé, un changement d'état ne re-notifierait jamais.
    motif      TEXT NOT NULL DEFAULT 'decouverte',
    intensite  TEXT NOT NULL DEFAULT 'normale',   -- forte | normale | silencieuse
    corps      TEXT NOT NULL,
    etat       TEXT NOT NULL DEFAULT 'a_envoyer',
    tentatives INTEGER NOT NULL DEFAULT 0, erreur TEXT,
    cree_le    TEXT NOT NULL, maj_le TEXT NOT NULL,
    UNIQUE (source, ref_source, motif)
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
