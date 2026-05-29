"""Whale/smart money detector."""

import logging

logger = logging.getLogger(__name__)


def is_whale_transaction(tx: dict, threshold_usd: float = 10000) -> bool:
    """Check if transaction qualifies as whale tx."""
    return tx.get("value_usd", 0) >= threshold_usd


def detect_whale_address(address: str, db_conn) -> bool:
    """Check if address has whale-level activity (top volume)."""
    row = db_conn.execute(
        "SELECT total_volume_usd, tx_count FROM addresses WHERE address = ?",
        (address,)
    ).fetchone()
    if not row:
        return False
    return row["total_volume_usd"] > 100000 or row["tx_count"] > 100


def update_address_stats(address: str, tx: dict, db_conn):
    """Upsert address stats after a new transaction."""
    value_usd = tx.get("value_usd", 0)
    timestamp = tx.get("timestamp", 0)

    existing = db_conn.execute(
        "SELECT id, total_volume_usd, tx_count FROM addresses WHERE address = ?",
        (address,)
    ).fetchone()

    if existing:
        db_conn.execute(
            """UPDATE addresses 
            SET total_volume_usd = total_volume_usd + ?, 
                tx_count = tx_count + 1,
                last_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE address = ?""",
            (value_usd, timestamp, address)
        )
    else:
        db_conn.execute(
            """INSERT INTO addresses (address, total_volume_usd, tx_count, first_seen, last_active)
            VALUES (?, ?, 1, ?, ?)""",
            (address, value_usd, timestamp, timestamp)
        )
    db_conn.commit()


def get_top_whales(db_conn, limit: int = 10) -> list[dict]:
    """Get top whale addresses by volume."""
    rows = db_conn.execute(
        """SELECT address, label, category, total_volume_usd, tx_count, profit_score, ai_profile
        FROM addresses 
        WHERE total_volume_usd > 0
        ORDER BY total_volume_usd DESC 
        LIMIT ?""",
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
