"""AI analyzer — calls local Ollama Qwen3.5:9b."""

import httpx
import logging

from backend.config import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


async def _ollama_chat(prompt: str, max_tokens: int = 80) -> str:
    """Call Ollama /api/chat."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.3,
                    },
                },
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return ""


async def analyze_transaction(tx: dict) -> str:
    """Generate one-line Chinese analysis for a transaction."""
    from_addr = (tx.get("from_address") or "?")[:8]
    to_addr = (tx.get("to_address") or "合约")[:8]
    value = tx.get("value_native", 0)
    token = tx.get("token", "MNT")
    tx_type = tx.get("tx_type", "")
    protocol = tx.get("protocol", "unknown")

    prompt = (
        f"用一句话（不超过30字）描述这笔Mantle链上交易的意图：\n"
        f"{from_addr}→{to_addr} {value:.2f} {token} 类型:{tx_type} 协议:{protocol}\n"
        f"示例：\"0xabc 通过 Merchant Moe 将 50K USDC 兑换为 MNT，疑似建仓\""
    )
    return await _ollama_chat(prompt, max_tokens=60)


async def classify_address(address: str, stats: dict) -> tuple[str, str]:
    """Classify address type and return (category, description)."""
    prompt = (
        f"判断链上地址类型，返回格式：分类|一句话理由\n"
        f"地址:{address[:12]} 交易数:{stats.get('tx_count', 0)} "
        f"均额:${stats.get('avg_value', 0):,.0f} 协议:{stats.get('protocols', '?')}\n"
        f"选项：whale/mev/arbitrage/defi/normal"
    )

    content = await _ollama_chat(prompt, max_tokens=80)
    if not content:
        return "normal", ""

    parts = content.split("|", 1)
    category = parts[0].strip().lower()
    desc = parts[1].strip() if len(parts) > 1 else content
    valid = {"whale", "mev", "arbitrage", "defi", "normal"}
    if category not in valid:
        category = "normal"
    return category, desc


async def generate_daily_summary(stats: dict) -> str:
    """Generate daily summary from aggregated stats."""
    prompt = (
        f"根据Mantle链24h数据写3句中文摘要，突出异常和聪明钱动向：\n"
        f"交易量:${stats.get('total_volume', 0):,.0f} "
        f"大额交易:{stats.get('whale_tx_count', 0)}笔\n"
        f"Top3聪明钱:{stats.get('top_moves', '暂无')}\n"
        f"异常:{stats.get('alerts', '暂无')}"
    )
    return await _ollama_chat(prompt, max_tokens=200)
