"""Pydantic models for API request/response."""

from pydantic import BaseModel
from typing import Optional


class TransactionOut(BaseModel):
    tx_hash: str
    block_number: int
    timestamp: int
    from_address: str
    to_address: Optional[str] = None
    value_usd: float
    value_native: float
    token: str
    tx_type: str
    protocol: str
    ai_analysis: Optional[str] = None
    is_whale_tx: bool


class AddressProfile(BaseModel):
    address: str
    label: Optional[str] = None
    category: str
    total_volume_usd: float
    tx_count: int
    first_seen: Optional[int] = None
    last_active: Optional[int] = None
    profit_score: float
    ai_profile: Optional[str] = None


class AlertOut(BaseModel):
    id: int
    alert_type: str
    address: Optional[str] = None
    tx_hash: Optional[str] = None
    description: str
    severity: str
    is_read: bool


class DailySummaryOut(BaseModel):
    date: str
    summary_text: str
    top_whale_moves: Optional[str] = None
    total_volume: float
    alert_count: int
