"""Price fetcher — get MNT/USD price, cached."""

import time
import httpx
import logging

logger = logging.getLogger(__name__)

_price_cache = {"price": 0.80, "ts": 0}  # fallback price
CACHE_TTL = 120  # seconds


async def get_mnt_price() -> float:
    """Get MNT price in USD. Cached for 120s."""
    now = time.time()
    if now - _price_cache["ts"] < CACHE_TTL:
        return _price_cache["price"]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # CoinGecko free API
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "mantle", "vs_currencies": "usd"},
            )
            resp.raise_for_status()
            price = resp.json()["mantle"]["usd"]
            _price_cache["price"] = price
            _price_cache["ts"] = now
            logger.info(f"MNT price updated: ${price}")
            return price
    except Exception as e:
        logger.warning(f"Failed to fetch MNT price: {e}, using cached ${_price_cache['price']}")
        return _price_cache["price"]


def get_mnt_price_sync() -> float:
    """Sync version — returns cached price without fetching."""
    return _price_cache["price"]
