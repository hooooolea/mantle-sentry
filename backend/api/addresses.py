"""Address API routes."""

from fastapi import APIRouter, Query
from backend.models.database import get_db

router = APIRouter(tags=["addresses"])


@router.get("/whales")
def list_whales(
    sort: str = Query("volume", regex="^(volume|count|score)$"),
    limit: int = Query(10, le=50),
):
    order_map = {
        "volume": "total_volume_usd DESC",
        "count": "tx_count DESC",
        "score": "profit_score DESC",
    }
    db = get_db()
    rows = db.execute(
        f"""SELECT address, label, category, total_volume_usd, tx_count, profit_score, ai_profile
        FROM addresses 
        WHERE total_volume_usd > 0
        ORDER BY {order_map[sort]}
        LIMIT ?""",
        (limit,)
    ).fetchall()
    db.close()
    return {"whales": [dict(r) for r in rows]}


@router.get("/address/{address}/profile")
def address_profile(address: str):
    db = get_db()
    row = db.execute(
        "SELECT * FROM addresses WHERE address = ?", (address.lower(),)
    ).fetchone()
    db.close()
    if not row:
        return {"error": "address not found"}
    return dict(row)


@router.get("/address/{address}/transactions")
def address_transactions(address: str, limit: int = Query(50, le=200)):
    addr = address.lower()
    db = get_db()
    rows = db.execute(
        """SELECT * FROM transactions 
        WHERE from_address = ? OR to_address = ?
        ORDER BY timestamp DESC 
        LIMIT ?""",
        (addr, addr, limit)
    ).fetchall()
    db.close()
    return {"transactions": [dict(r) for r in rows]}
