"""Price fetcher — get MNT/USD price, cached."""

import time
import httpx
import logging

logger = logging.getLogger(__name__)

_price_cache = {"price": 0.80, "ts": 0}
CACHE_TTL = 300  # 5 min


async def get_mnt_price() -> float:
    """Get MNT price in USD. Cached for 5 min."""
    now = time.time()
    if now - _price_cache["ts"] < CACHE_TTL:
        return _price_cache["price"]

    # Try CoinGecko
    try:
        async with httpx.AsyncClient(timeout=5) as client:
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
    except Exception:
        pass

    # Fallback: Binance
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "MNTUSDT"},
            )
            resp.raise_for_status()
            price = float(resp.json()["price"])
            _price_cache["price"] = price
            _price_cache["ts"] = now
            logger.info(f"MNT price (Binance): ${price}")
            return price
    except Exception:
        pass

    logger.warning(f"All price sources failed, using cached ${_price_cache['price']}")
    return _price_cache["price"]


def get_mnt_price_sync() -> float:
    return _price_cache["price"]
