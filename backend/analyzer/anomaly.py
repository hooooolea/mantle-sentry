"""Anomaly detection rules."""

import logging

logger = logging.getLogger(__name__)


def check_anomaly(tx: dict, db_conn) -> list[dict]:
    """Run all anomaly checks on a transaction. Returns list of alert dicts."""
    alerts = []
    from_addr = tx.get("from_address", "").lower()
    to_addr = (tx.get("to_address") or "").lower()
    value_usd = tx.get("value_usd", 0)

    # Rule 1: Single tx > 10x historical average
    if from_addr:
        row = db_conn.execute(
            "SELECT total_volume_usd, tx_count FROM addresses WHERE address = ?",
            (from_addr,)
        ).fetchone()
        if row and row["tx_count"] > 5:
            avg = row["total_volume_usd"] / row["tx_count"]
            if avg > 0 and value_usd > avg * 10:
                alerts.append({
                    "alert_type": "large_tx",
                    "address": from_addr,
                    "tx_hash": tx.get("tx_hash"),
                    "description": f"单笔交易 ${value_usd:,.0f} 是历史平均 (${avg:,.0f}) 的 {value_usd/avg:.0f} 倍",
                    "severity": "high",
                })

    # Rule 2: New address first tx > $50K
    for addr in [from_addr, to_addr]:
        if not addr:
            continue
        row = db_conn.execute(
            "SELECT tx_count FROM addresses WHERE address = ?",
            (addr,)
        ).fetchone()
        if row is None and value_usd > 50000:
            alerts.append({
                "alert_type": "new_whale",
                "address": addr,
                "tx_hash": tx.get("tx_hash"),
                "description": f"新地址首次交易 ${value_usd:,.0f}",
                "severity": "medium",
            })

    # Rule 3: Dormant address suddenly active (30+ days inactive)
    for addr in [from_addr, to_addr]:
        if not addr:
            continue
        row = db_conn.execute(
            "SELECT last_active, total_volume_usd FROM addresses WHERE address = ?",
            (addr,)
        ).fetchone()
        if row and row["last_active"]:
            import time
            days_inactive = (time.time() - row["last_active"]) / 86400
            if days_inactive > 30 and value_usd > 10000:
                alerts.append({
                    "alert_type": "dormant_active",
                    "address": addr,
                    "tx_hash": tx.get("tx_hash"),
                    "description": f"沉寂 {days_inactive:.0f} 天后突然活跃，交易 ${value_usd:,.0f}",
                    "severity": "medium",
                })

    return alerts


def save_alerts(alerts: list[dict], db_conn):
    """Persist alerts to database."""
    for a in alerts:
        db_conn.execute(
            """INSERT INTO alerts (alert_type, address, tx_hash, description, severity)
            VALUES (?, ?, ?, ?, ?)""",
            (a["alert_type"], a["address"], a["tx_hash"], a["description"], a["severity"])
        )
    db_conn.commit()
