"""Alert API routes."""

from fastapi import APIRouter, Query
from backend.models.database import get_db

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
def list_alerts(
    severity: str = Query(None, regex="^(high|medium|low)$"),
    limit: int = Query(20, le=100),
):
    db = get_db()
    if severity:
        total = db.execute(
            "SELECT COUNT(*) FROM alerts WHERE severity = ?", (severity,)
        ).fetchone()[0]
        rows = db.execute(
            "SELECT * FROM alerts WHERE severity = ? ORDER BY created_at DESC LIMIT ?",
            (severity, limit)
        ).fetchall()
    else:
        total = db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        rows = db.execute(
            "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    db.close()
    return {"alerts": [dict(r) for r in rows], "total": total}


@router.get("/alerts/unread")
def unread_alerts():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM alerts WHERE is_read = 0 ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return {"alerts": [dict(r) for r in rows]}
