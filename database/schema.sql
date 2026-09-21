-- =============================================================
--  IRONPULSE — Coach IA Fitness
--  Schéma SQLite complet (base locale de développement)
--  Généré à partir de backend/models.py + tables de trace de l'agent.
--
--  Utilisation :
--    sqlite3 application.db < database/schema.sql
--    (ou sqlite3 database/schema.sql pour créer un fichier neuf)
--
--  Le script est idempotent : il peut être relancé sans erreur.
--  Attention : il DROP toutes les tables existantes au début.
-- =============================================================

PRAGMA foreign_keys = ON;

-- =============================================================
--  Suppression (ordre inverse des dépendances)
-- =============================================================

DROP TABLE IF EXISTS resultats;
DROP TABLE IF EXISTS demandes;
DROP TABLE IF EXISTS shopping_lists;
DROP TABLE IF EXISTS meal_items;
DROP TABLE IF EXISTS meals;
DROP TABLE IF EXISTS meal_plans;
DROP TABLE IF EXISTS friendships;
DROP TABLE IF EXISTS machines;
DROP TABLE IF EXISTS weight_entries;
DROP TABLE IF EXISTS session_sets;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS program_exercises;
DROP TABLE IF EXISTS program_days;
DROP TABLE IF EXISTS training_programs;
DROP TABLE IF EXISTS foods;
DROP TABLE IF EXISTS exercises;
DROP TABLE IF EXISTS users;

-- =============================================================
--  1. DOMAINE — données métier (lecture ÉCRITE par l'agent)
-- =============================================================

-- -------------------------------------------------------------
--  Utilisateurs (profil + objectifs + préférences)
-- -------------------------------------------------------------
CREATE TABLE users (
    id                  INTEGER PRIMARY KEY,
    username            VARCHAR(80)  NOT NULL UNIQUE,
    email               VARCHAR(120) NOT NULL UNIQUE,
    password_hash       VARCHAR(256) NOT NULL,
    created_at          DATETIME,
    goal                VARCHAR(20)  DEFAULT 'prise_masse',      -- prise_masse, perte_poids, force, endurance
    level               VARCHAR(20)  DEFAULT 'debutant',         -- debutant, intermediaire, avance
    weight              FLOAT        DEFAULT 70.0,
    target_weight       FLOAT        DEFAULT 75.0,
    height              FLOAT        DEFAULT 175.0,
    age                 INTEGER      DEFAULT 25,
    daily_calories      INTEGER      DEFAULT 2500,
    calories_auto       BOOLEAN      DEFAULT TRUE,               -- True = calcul auto selon le profil
    available_equipment TEXT         DEFAULT '[]',               -- JSON list of equipment names
    dietary_preferences TEXT         DEFAULT '[]',               -- JSON list: vegetarien, vegan, ...
    split_type          VARCHAR(30)  DEFAULT NULL,               -- full_body, upper_lower, push_pull_legs...
    sessions_per_week   INTEGER      DEFAULT NULL                -- 2..6 séances par semaine
);

-- -------------------------------------------------------------
--  Catalogue d'exercices
-- -------------------------------------------------------------
CREATE TABLE exercises (
    id              INTEGER PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    category        VARCHAR(50)  NOT NULL,      -- dos, pectoraux, jambes, epaules, bras, core
    muscle_group    VARCHAR(50)  NOT NULL,      -- grand_dorsal, biceps, quadriceps...
    equipment_needed VARCHAR(100) DEFAULT 'barre',
    description     TEXT         DEFAULT '',
    is_compound     BOOLEAN      DEFAULT FALSE
);

-- -------------------------------------------------------------
--  Programmes d'entraînement (4 semaines, générés)
-- -------------------------------------------------------------
CREATE TABLE training_programs (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal        VARCHAR(20) NOT NULL,
    start_date  DATE,
    end_date    DATE,
    is_active   BOOLEAN DEFAULT TRUE
);

CREATE TABLE program_days (
    id          INTEGER PRIMARY KEY,
    program_id  INTEGER NOT NULL REFERENCES training_programs(id) ON DELETE CASCADE,
    day_number  INTEGER NOT NULL,              -- 1-4 ou 1-5 selon le split
    name        VARCHAR(50) NOT NULL           -- Push, Pull, Jambes...
);

CREATE TABLE program_exercises (
    id              INTEGER PRIMARY KEY,
    day_id          INTEGER NOT NULL REFERENCES program_days(id) ON DELETE CASCADE,
    exercise_id     INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    sets            INTEGER DEFAULT 3,
    reps            INTEGER DEFAULT 10,
    rest_seconds    INTEGER DEFAULT 90,
    target_weight   FLOAT   DEFAULT 0.0,
    "order"         INTEGER DEFAULT 0          -- "order" est un mot réservé SQL, donc entre guillemets
);

-- -------------------------------------------------------------
--  Séances réalisées (avec ressenti et vérification anti-triche)
-- -------------------------------------------------------------
CREATE TABLE sessions (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    program_day_id  INTEGER REFERENCES program_days(id) ON DELETE SET NULL,
    date            DATE,
    completed       BOOLEAN DEFAULT FALSE,
    feeling         INTEGER DEFAULT 3,          -- 1-5 ressenti
    notes           TEXT    DEFAULT '',
    flagged         BOOLEAN DEFAULT FALSE       -- volume/rythme anormal détecté (anti-triche)
);

CREATE TABLE session_sets (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    set_number  INTEGER NOT NULL,
    weight      FLOAT   DEFAULT 0.0,
    reps        INTEGER DEFAULT 0,
    completed   BOOLEAN DEFAULT TRUE,
    difficulty  VARCHAR(20) DEFAULT ''          -- facile, moyen, difficile, impossible
);

-- -------------------------------------------------------------
--  Historique de poids
-- -------------------------------------------------------------
CREATE TABLE weight_entries (
    id      INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    weight  FLOAT NOT NULL,
    date    DATE
);

-- -------------------------------------------------------------
--  Aliments (base nutrition)
-- -------------------------------------------------------------
CREATE TABLE foods (
    id       INTEGER PRIMARY KEY,
    name     VARCHAR(120) NOT NULL,
    category VARCHAR(50)  DEFAULT 'autre',     -- proteine, glucide, lipide, legume, fruit, autre
    kcal     FLOAT DEFAULT 0,                  -- pour 100 g
    protein  FLOAT DEFAULT 0,
    carbs    FLOAT DEFAULT 0,
    fat      FLOAT DEFAULT 0,
    tags     TEXT DEFAULT '[]'                 -- JSON list: viande, poisson, lactier, gluten...
);

-- -------------------------------------------------------------
--  Plans alimentaires générés
-- -------------------------------------------------------------
CREATE TABLE meal_plans (
    id               INTEGER PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    num_days         INTEGER DEFAULT 7,
    target_calories  INTEGER DEFAULT 2500,
    created_at       DATETIME
);

CREATE TABLE meals (
    id           INTEGER PRIMARY KEY,
    meal_plan_id INTEGER NOT NULL REFERENCES meal_plans(id) ON DELETE CASCADE,
    day          INTEGER NOT NULL,             -- 1..num_days
    meal_type    VARCHAR(30) NOT NULL,         -- Petit-déjeuner, Déjeuner, Collation, Dîner
    name         VARCHAR(150) NOT NULL
);

CREATE TABLE meal_items (
    id       INTEGER PRIMARY KEY,
    meal_id  INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    food_id  INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    quantity FLOAT DEFAULT 0                   -- en grammes
);

-- -------------------------------------------------------------
--  Listes de courses agrégées depuis un plan
-- -------------------------------------------------------------
CREATE TABLE shopping_lists (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    meal_plan_id INTEGER REFERENCES meal_plans(id) ON DELETE SET NULL,
    created_at   DATETIME,
    items        TEXT DEFAULT '[]'             -- JSON: [{name, qty_grams}]
);

-- -------------------------------------------------------------
--  Réseau social (amitiés, hors périmètre agent)
-- -------------------------------------------------------------
CREATE TABLE friendships (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status     VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending | accepted
    created_at DATETIME,
    UNIQUE (user_id, friend_id)
);

-- -------------------------------------------------------------
--  Machines de la salle (catalogue)
-- -------------------------------------------------------------
CREATE TABLE machines (
    id          INTEGER PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    brand       VARCHAR(60)  DEFAULT '',
    model       VARCHAR(80)  DEFAULT '',
    category    VARCHAR(50)  DEFAULT 'autre',
    code        VARCHAR(20)  NOT NULL UNIQUE,  -- code QR (ex: TCG-ART-01)
    location    VARCHAR(80)  DEFAULT '',
    image_url   TEXT         DEFAULT '',       -- data-URI SVG
    setup_tips  TEXT         DEFAULT ''
);

-- =============================================================
--  2. TRACE — mémoire de l'agent (lecture/écriture par l'agent)
--     Rendent le raisonnement auditable après coup.
-- =============================================================

-- -------------------------------------------------------------
--  Demandes formulées par l'utilisateur (entrée de l'agent)
-- -------------------------------------------------------------
CREATE TABLE demandes (
    id              INTEGER PRIMARY KEY,
    utilisateur_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    texte           TEXT    NOT NULL,
    date_creation   DATETIME DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------
--  Résultats de l'agent : une ligne par étape de la boucle.
--  outil_utilise = tool appelé (ou NULL si réponse directe),
--  ce qui rend le raisonnement de l'agent reconstructible.
-- -------------------------------------------------------------
CREATE TABLE resultats (
    id              INTEGER PRIMARY KEY,
    demande_id      INTEGER NOT NULL REFERENCES demandes(id) ON DELETE CASCADE,
    etape           INTEGER DEFAULT 1,         -- n° de tour de boucle
    outil_utilise   TEXT,                      -- nom du tool (ex: consulter_progression)
    arguments       TEXT,                      -- arguments JSON passés au tool
    reponse         TEXT,                      -- résultat du tool / réponse finale
    date_creation   DATETIME DEFAULT (datetime('now'))
);

-- =============================================================
--  Index : accélèrent les accès fréquents des tools de l'agent
-- =============================================================

CREATE INDEX IF NOT EXISTS idx_sessions_user_date      ON sessions(user_id, date);
CREATE INDEX IF NOT EXISTS idx_session_sets_session    ON session_sets(session_id);
CREATE INDEX IF NOT EXISTS idx_session_sets_exercise   ON session_sets(exercise_id);
CREATE INDEX IF NOT EXISTS idx_weight_entries_user     ON weight_entries(user_id, date);
CREATE INDEX IF NOT EXISTS idx_program_days_program    ON program_days(program_id);
CREATE INDEX IF NOT EXISTS idx_program_exercises_day   ON program_exercises(day_id);
CREATE INDEX IF NOT EXISTS idx_meals_plan              ON meals(meal_plan_id);
CREATE INDEX IF NOT EXISTS idx_meal_items_meal         ON meal_items(meal_id);
CREATE INDEX IF NOT EXISTS idx_resultats_demande       ON resultats(demande_id, etape);
CREATE INDEX IF NOT EXISTS idx_demandes_user           ON demandes(utilisateur_id, date_creation);