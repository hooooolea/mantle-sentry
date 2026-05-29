"""SQLite database layer."""

import sqlite3
import os
from backend.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_hash TEXT UNIQUE NOT NULL,
    block_number INTEGER,
    timestamp INTEGER,
    from_address TEXT,
    to_address TEXT,
    value_usd REAL,
    value_native REAL,
    token TEXT,
    tx_type TEXT,
    protocol TEXT,
    ai_analysis TEXT,
    is_whale_tx BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT UNIQUE NOT NULL,
    label TEXT,
    category TEXT DEFAULT 'normal',
    total_volume_usd REAL DEFAULT 0,
    tx_count INTEGER DEFAULT 0,
    first_seen INTEGER,
    last_active INTEGER,
    profit_score REAL DEFAULT 0,
    ai_profile TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT,
    address TEXT,
    tx_hash TEXT,
    description TEXT,
    severity TEXT DEFAULT 'low',
    is_read BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE,
    summary_text TEXT,
    top_whale_moves TEXT,
    total_volume REAL,
    alert_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_tx_from ON transactions(from_address);
CREATE INDEX IF NOT EXISTS idx_tx_to ON transactions(to_address);
CREATE INDEX IF NOT EXISTS idx_tx_whale ON transactions(is_whale_tx);
CREATE INDEX IF NOT EXISTS idx_addr_category ON addresses(category);
CREATE INDEX IF NOT EXISTS idx_addr_volume ON addresses(total_volume_usd);
CREATE INDEX IF NOT EXISTS idx_alert_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alert_time ON alerts(created_at);
"""


def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_db_cursor():
    """Context-managed DB cursor."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()
