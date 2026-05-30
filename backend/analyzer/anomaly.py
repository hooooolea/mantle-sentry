"""Anomaly detection rules."""

import logging
import time

logger = logging.getLogger(__name__)


def check_anomaly(tx: dict, db_conn) -> list[dict]:
    """Run all anomaly checks on a transaction. Returns list of alert dicts."""
    alerts = []
    from_addr = tx.get("from_address", "").lower()
    to_addr = (tx.get("to_address") or "").lower()
    value_usd = tx.get("value_usd", 0)

    # Rule 1: Single tx > 5x historical average
    if from_addr:
        row = db_conn.execute(
            "SELECT total_volume_usd, tx_count FROM addresses WHERE address = ?",
            (from_addr,)
        ).fetchone()
        if row and row["tx_count"] > 5:
            avg = row["total_volume_usd"] / row["tx_count"]
            if avg > 0 and value_usd > avg * 5:
                alerts.append({
                    "alert_type": "large_tx",
                    "address": from_addr,
                    "tx_hash": tx.get("tx_hash"),
                    "description": f"单笔交易 ${value_usd:,.0f} 是历史平均 (${avg:,.0f}) 的 {value_usd/avg:.0f} 倍",
                    "severity": "high",
                })

    # Rule 2: New address first tx > $5K (only if no existing alert for this address)
    for addr in [from_addr, to_addr]:
        if not addr:
            continue
        # Check if address exists in addresses table
        row = db_conn.execute(
            "SELECT tx_count FROM addresses WHERE address = ?", (addr,)
        ).fetchone()
        if row is None and value_usd > 5000:
            # Check if we already have a new_whale alert for this address
            existing = db_conn.execute(
                "SELECT id FROM alerts WHERE address = ? AND alert_type = 'new_whale'",
                (addr,)
            ).fetchone()
            if not existing:
                alerts.append({
                    "alert_type": "new_whale",
                    "address": addr,
                    "tx_hash": tx.get("tx_hash"),
                    "description": f"新地址首次交易 ${value_usd:,.0f}",
                    "severity": "medium",
                })

    # Rule 3: Dormant address suddenly active (30+ days inactive, only once per address)
    for addr in [from_addr, to_addr]:
        if not addr:
            continue
        row = db_conn.execute(
            "SELECT last_active, total_volume_usd FROM addresses WHERE address = ?",
            (addr,)
        ).fetchone()
        if row and row["last_active"]:
            days_inactive = (time.time() - row["last_active"]) / 86400
            if days_inactive > 30 and value_usd > 10000:
                existing = db_conn.execute(
                    "SELECT id FROM alerts WHERE address = ? AND alert_type = 'dormant_active'",
                    (addr,)
                ).fetchone()
                if not existing:
                    alerts.append({
                        "alert_type": "dormant_active",
                        "address": addr,
                        "tx_hash": tx.get("tx_hash"),
                        "description": f"沉寂 {days_inactive:.0f} 天后突然活跃，交易 ${value_usd:,.0f}",
                        "severity": "medium",
                    })

    return alerts


def save_alerts(alerts: list[dict], db_conn):
    """Persist alerts to database, deduplicated by address + alert_type."""
    for a in alerts:
        # Skip if already exists
        existing = db_conn.execute(
            "SELECT id FROM alerts WHERE address = ? AND alert_type = ?",
            (a["address"], a["alert_type"])
        ).fetchone()
        if existing:
            continue
        db_conn.execute(
            """INSERT INTO alerts (alert_type, address, tx_hash, description, severity)
            VALUES (?, ?, ?, ?, ?)""",
            (a["alert_type"], a["address"], a["tx_hash"], a["description"], a["severity"])
        )
    db_conn.commit()


def deduplicate_alerts(db_conn):
    """Remove existing duplicate alerts, keeping only the first one per address+type."""
    db_conn.execute(
        """DELETE FROM alerts WHERE id NOT IN (
            SELECT MIN(id) FROM alerts GROUP BY address, alert_type
        )"""
    )
    db_conn.commit()
    count = db_conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    logger.info(f"Alerts deduplicated, {count} remaining")
