"""Daily summary API routes."""

from fastapi import APIRouter, Query
from backend.models.database import get_db
from backend.scanner.price_fetcher import get_mnt_price_sync

router = APIRouter(tags=["summary"])


@router.get("/summary/daily")
def daily_summary(date: str = Query(..., description="YYYY-MM-DD")):
    db = get_db()
    row = db.execute(
        "SELECT * FROM daily_summaries WHERE date = ?", (date,)
    ).fetchone()
    db.close()
    if not row:
        return {"error": "no summary for this date"}
    return dict(row)


@router.get("/summary/latest")
def latest_summary():
    db = get_db()
    row = db.execute(
        "SELECT * FROM daily_summaries ORDER BY date DESC LIMIT 1"
    ).fetchone()
    db.close()
    if not row:
        return {"message": "no summaries yet"}
    return dict(row)


@router.get("/price/mnt")
def mnt_price():
    return {"price": get_mnt_price_sync()}
