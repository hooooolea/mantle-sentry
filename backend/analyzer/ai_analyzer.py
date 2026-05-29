"""AI analyzer — calls local Ollama Qwen3.5:9b."""

import httpx
import logging

from backend.config import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


async def _ollama_generate(prompt: str, max_tokens: int = 150) -> str:
    """Call Ollama /api/generate."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return ""


async def _ollama_chat(prompt: str, max_tokens: int = 150) -> str:
    """Call Ollama /api/chat."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.error(f"Ollama chat call failed: {e}")
        return ""


async def analyze_transaction(tx: dict) -> str:
    """Generate one-line Chinese analysis for a transaction."""
    prompt = f"""你是Mantle区块链分析师。分析以下交易并用一句话中文描述其意图。

交易信息：
- 类型: {tx.get('tx_type', '未知')}
- 从: {tx.get('from_address', '?')[:10]}... → 到: {tx.get('to_address', '?')[:10] if tx.get('to_address') else '合约创建'}...
- 金额: {tx.get('value_native', 0)} MNT
- 协议: {tx.get('protocol', 'unknown')}

要求：一句话，不超过50字，包含谁在做什么、金额、目的判断。"""
    return await _ollama_chat(prompt, max_tokens=100)


async def classify_address(address: str, stats: dict) -> tuple[str, str]:
    """Classify address type and return (category, description)."""
    prompt = f"""你是链上行为分析师。根据以下特征判断地址类型。

地址: {address}
- 30天交易数: {stats.get('tx_count', 0)}
- 平均交易金额: ${stats.get('avg_value', 0):,.0f}
- 主要交互协议: {stats.get('protocols', '未知')}

分类选项：whale(鲸鱼) / mev(MEV机器人) / arbitrage(套利) / defi(深度DeFi用户) / normal(普通)
返回格式：分类|一句话理由"""

    content = await _ollama_chat(prompt, max_tokens=150)
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
    prompt = f"""你是加密市场分析师。根据以下Mantle链上数据，生成今日摘要。

数据：
- 24h总交易量: ${stats.get('total_volume', 0):,.0f}
- 大额交易数: {stats.get('whale_tx_count', 0)}
- 聪明钱Top3动向: {stats.get('top_moves', '暂无')}
- 异常事件: {stats.get('alerts', '暂无')}

要求：3-5句话，重点突出异常和聪明钱动向，语气专业但易懂。"""
    return await _ollama_chat(prompt, max_tokens=300)
