"""Transaction API routes."""

from fastapi import APIRouter, Query
from backend.models.database import get_db

router = APIRouter(tags=["transactions"])


@router.get("/transactions")
def list_transactions(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    min_value: float = Query(0, ge=0),
):
    db = get_db()
    total = db.execute(
        "SELECT COUNT(*) FROM transactions WHERE value_usd >= ?", (min_value,)
    ).fetchone()[0]
    rows = db.execute(
        """SELECT * FROM transactions 
        WHERE value_usd >= ? 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?""",
        (min_value, limit, offset)
    ).fetchall()
    db.close()
    return {"transactions": [dict(r) for r in rows], "total": total}


@router.get("/transactions/whale")
def whale_transactions(limit: int = Query(20, le=100)):
    db = get_db()
    rows = db.execute(
        """SELECT * FROM transactions 
        WHERE is_whale_tx = 1 
        ORDER BY timestamp DESC 
        LIMIT ?""",
        (limit,)
    ).fetchall()
    db.close()
    return {"transactions": [dict(r) for r in rows]}


@router.get("/transactions/{tx_hash}")
def get_transaction(tx_hash: str):
    db = get_db()
    row = db.execute(
        "SELECT * FROM transactions WHERE tx_hash = ?", (tx_hash,)
    ).fetchone()
    db.close()
    if not row:
        return {"error": "not found"}
    return dict(row)
