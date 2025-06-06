CREATE TABLE IF NOT EXISTS users (
    discord_id TEXT PRIMARY KEY,
    ign TEXT,
    union TEXT
);

CREATE TABLE IF NOT EXISTS union_roles (
    role_name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS union_leaders (
    role_name TEXT PRIMARY KEY,
    leader_id TEXT
);
