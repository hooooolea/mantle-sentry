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
from backend.analyzer.ai_analyzer import analyze_transaction
from backend.config import SCAN_INTERVAL_SECONDS, WHALE_THRESHOLD_USD
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
                db = get_db()
                for tx in txs:
                    # Classify (skip system txs)
                    tx = classify_tx(tx)
                    if tx is None:
                        continue

                    # Check whale
                    # value_usd needs price data; for now use native * rough price
                    tx.setdefault("value_usd", tx["value_native"] * 0.8)  # placeholder
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

                    # Broadcast whale tx
                    if tx["is_whale_tx"]:
                        # AI analysis (non-blocking)
                        asyncio.create_task(_ai_and_broadcast(tx, db))
                    else:
                        await broadcast({
                            "type": "new_transaction",
                            "data": {
                                "tx_hash": tx["tx_hash"],
                                "from": tx["from_address"],
                                "to": tx.get("to_address"),
                                "value": tx["value_native"],
                                "token": tx.get("token", "MNT"),
                                "type": tx["tx_type"],
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
                "token": tx.get("token", "MNT"),
                "type": tx["tx_type"],
                "ai_analysis": analysis,
                "is_whale": True,
            }
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(scan_loop())
    logger.info("MantleSentry started — scanning Mantle blocks...")
    yield
    task.cancel()


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
