
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    pin_hash TEXT NOT NULL,
    reset_token TEXT,
    reset_token_expires_at TIMESTAMP
);
