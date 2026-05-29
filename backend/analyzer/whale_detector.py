"""Whale/smart money detector — scoring algorithm."""

import logging
import time

logger = logging.getLogger(__name__)


def is_whale_transaction(tx: dict, threshold_usd: float = 10000) -> bool:
    """Check if transaction qualifies as whale tx."""
    return tx.get("value_usd", 0) >= threshold_usd


def calculate_smart_score(db_conn, address: str) -> float:
    """Calculate smart money score (0-100) for an address.
    
    Factors:
    - Volume score (0-40): higher total volume = higher score
    - Frequency score (0-30): more transactions = higher score
    - Avg tx size score (0-20): larger avg tx = higher score
    - Recency score (0-10): active recently = higher score
    """
    row = db_conn.execute(
        "SELECT total_volume_usd, tx_count, first_seen, last_active FROM addresses WHERE address = ?",
        (address,)
    ).fetchone()
    if not row:
        return 0.0

    vol = row["total_volume_usd"] or 0
    count = row["tx_count"] or 0
    last_active = row["last_active"] or 0
    now = int(time.time())

    # Volume score (log scale, max at $100K+)
    import math
    vol_score = min(40, (math.log10(max(vol, 1)) / 5) * 40)

    # Frequency score (max at 50+ txs)
    freq_score = min(30, (count / 50) * 30)

    # Avg tx size score (max at $10K+ avg)
    avg_tx = vol / count if count > 0 else 0
    size_score = min(20, (avg_tx / 10000) * 20)

    # Recency score (max if active in last hour)
    hours_since = (now - last_active) / 3600 if last_active > 0 else 999
    recency_score = max(0, 10 - (hours_since / 24) * 10)

    total = vol_score + freq_score + size_score + recency_score
    return round(min(100, total), 1)


def classify_address_by_score(score: float) -> str:
    """Classify address based on smart money score."""
    if score >= 70:
        return "whale"
    elif score >= 50:
        return "defi"
    elif score >= 30:
        return "active"
    return "normal"


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

    # Update smart score
    score = calculate_smart_score(db_conn, address)
    category = classify_address_by_score(score)
    db_conn.execute(
        "UPDATE addresses SET profit_score = ?, category = ? WHERE address = ?",
        (score, category, address)
    )
    db_conn.commit()


def get_top_whales(db_conn, limit: int = 10) -> list[dict]:
    """Get top whale addresses by smart score."""
    rows = db_conn.execute(
        """SELECT address, label, category, total_volume_usd, tx_count, profit_score, ai_profile
        FROM addresses 
        WHERE total_volume_usd > 0
        ORDER BY profit_score DESC 
        LIMIT ?""",
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
