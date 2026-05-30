"""MantleSentry — FastAPI entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.models.database import init_db
from backend.scanner.block_scanner import BlockScanner
from backend.scanner.tx_classifier import classify_tx
from backend.analyzer.whale_detector import is_whale_transaction, update_address_stats
from backend.analyzer.anomaly import check_anomaly, save_alerts
from backend.analyzer.ai_analyzer import analyze_transaction, generate_daily_summary
from backend.config import SCAN_INTERVAL_SECONDS, WHALE_THRESHOLD_USD
from backend.scanner.price_fetcher import get_mnt_price
from backend.api import transactions, addresses, alerts, summary
from backend.ws.handler import router as ws_router, broadcast

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("mantle_sentry")

scanner: BlockScanner | None = None


async def scan_loop():
    """Background loop: scan blocks → classify → detect anomalies → AI analyze."""
    global scanner
    scanner = BlockScanner()
    from backend.models.database import get_db

    while True:
        try:
            txs = await scanner.scan_new_blocks()
            if txs:
                # Get MNT price once per scan cycle
                mnt_price = await get_mnt_price()
                db = get_db()
                for tx in txs:
                    # Classify (skip system txs)
                    tx = classify_tx(tx)
                    if tx is None:
                        continue

                    # Check whale
                    tx.setdefault("value_usd", tx["value_native"] * mnt_price)
                    tx["is_whale_tx"] = is_whale_transaction(tx, WHALE_THRESHOLD_USD)

                    # Store
                    try:
                        db.execute(
                            """INSERT OR IGNORE INTO transactions 
                            (tx_hash, block_number, timestamp, from_address, to_address,
                             value_usd, value_native, token, tx_type, protocol, is_whale_tx)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                            (tx["tx_hash"], tx["block_number"], tx["timestamp"],
                             tx["from_address"], tx.get("to_address"),
                             tx["value_usd"], tx["value_native"],
                             tx.get("token", "MNT"), tx["tx_type"],
                             tx.get("protocol", "unknown"), tx["is_whale_tx"])
                        )
                        db.commit()
                    except Exception:
                        pass  # duplicate

                    # Update address stats
                    if tx["from_address"]:
                        update_address_stats(tx["from_address"], tx, db)
                    if tx.get("to_address"):
                        update_address_stats(tx["to_address"], tx, db)

                    # Anomaly detection
                    anomalies = check_anomaly(tx, db)
                    if anomalies:
                        save_alerts(anomalies, db)
                        for a in anomalies:
                            await broadcast({"type": "alert", "data": a})

                    # Broadcast and AI analyze
                    if tx["value_usd"] >= 1000:
                        # AI analysis for meaningful transactions
                        asyncio.create_task(_ai_and_broadcast(tx, db))
                    else:
                        await broadcast({
                            "type": "new_transaction",
                            "data": {
                                "tx_hash": tx["tx_hash"],
                                "from": tx["from_address"],
                                "to": tx.get("to_address"),
                                "value": tx["value_native"],
                                "value_usd": tx.get("value_usd", 0),
                                "token": tx.get("token", "MNT"),
                                "type": tx["tx_type"],
                                "protocol": tx.get("protocol", "unknown"),
                            }
                        })

                db.close()
                logger.info(f"Processed {len(txs)} txs, block {scanner.last_scanned_block}")
        except Exception as e:
            logger.error(f"Scan loop error: {e}")

        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


async def _ai_and_broadcast(tx: dict, db):
    """Run AI analysis on whale tx, store and broadcast."""
    analysis = await analyze_transaction(tx)
    if analysis:
        try:
            db.execute(
                "UPDATE transactions SET ai_analysis = ? WHERE tx_hash = ?",
                (analysis, tx["tx_hash"])
            )
            db.commit()
        except Exception:
            pass
        tx["ai_analysis"] = analysis
        await broadcast({
            "type": "new_transaction",
            "data": {
                "tx_hash": tx["tx_hash"],
                "from": tx["from_address"],
                "to": tx.get("to_address"),
                "value": tx["value_native"],
                "value_usd": tx.get("value_usd", 0),
                "token": tx.get("token", "MNT"),
                "type": tx["tx_type"],
                "protocol": tx.get("protocol", "unknown"),
                "ai_analysis": analysis,
                "is_whale": True,
            }
        })


async def daily_summary_loop():
    """Generate daily AI summary every hour."""
    from backend.models.database import get_db
    import time

    while True:
        try:
            await asyncio.sleep(3600)  # every hour
            db = get_db()
            today = time.strftime("%Y-%m-%d")

            # Check if already generated today
            existing = db.execute(
                "SELECT id FROM daily_summaries WHERE date = ?", (today,)
            ).fetchone()
            if existing:
                db.close()
                continue

            # Aggregate 24h stats
            now = int(time.time())
            day_ago = now - 86400

            txs = db.execute(
                "SELECT * FROM transactions WHERE timestamp > ?", (day_ago,)
            ).fetchall()

            if not txs:
                db.close()
                continue

            total_volume = sum(t["value_usd"] or 0 for t in txs)
            whale_txs = [t for t in txs if t["is_whale_tx"]]

            # Top whale moves
            top_moves = ""
            if whale_txs:
                top_3 = sorted(whale_txs, key=lambda t: t["value_usd"] or 0, reverse=True)[:3]
                top_moves = "; ".join(
                    f"{t['from_address'][:8]}→{t['to_address'][:8] if t['to_address'] else '?'} "
                    f"{t['value_native']:.0f} {t['token']} (${t['value_usd']:.0f})"
                    for t in top_3
                )

            # Recent alerts
            alerts_rows = db.execute(
                "SELECT description FROM alerts WHERE created_at > datetime(?, 'unixepoch') LIMIT 5",
                (day_ago,)
            ).fetchall()
            alerts_text = "; ".join(a["description"] for a in alerts_rows) if alerts_rows else "暂无"

            # Generate summary
            summary_text = await generate_daily_summary({
                "total_volume": total_volume,
                "whale_tx_count": len(whale_txs),
                "top_moves": top_moves or "暂无",
                "alerts": alerts_text,
            })

            if summary_text:
                db.execute(
                    """INSERT OR REPLACE INTO daily_summaries 
                    (date, summary_text, top_whale_moves, total_volume, alert_count)
                    VALUES (?, ?, ?, ?, ?)""",
                    (today, summary_text, top_moves, total_volume, len(alerts_rows))
                )
                db.commit()
                logger.info(f"Daily summary generated for {today}")

            db.close()
        except Exception as e:
            logger.error(f"Daily summary error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scan_task = asyncio.create_task(scan_loop())
    summary_task = asyncio.create_task(daily_summary_loop())
    logger.info("MantleSentry started — scanning Mantle blocks...")
    yield
    scan_task.cancel()
    summary_task.cancel()


app = FastAPI(title="MantleSentry", version="0.1.0", lifespan=lifespan)

# API routes
app.include_router(transactions.router, prefix="/api")
app.include_router(addresses.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(ws_router)

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def index():
    return FileResponse("frontend/index.html")


@app.get("/address/{addr}")
async def address_page(addr: str):
    return FileResponse("frontend/address.html")


@app.get("/analysis")
async def analysis_page():
    return FileResponse("frontend/analysis.html")
