"""Transaction classifier — identifies tx type and protocol, filters system txs."""

import logging

logger = logging.getLogger(__name__)

# System / burn addresses to skip
SYSTEM_ADDRS = {
    "0xdeaddeaddeaddeaddeaddeaddeaddeaddead0000",
    "0x4200000000000000000000000000000000000000",
    "0x4200000000000000000000000000000000000010",
    "0x4200000000000000000000000000000000000001",
    "0x4200000000000000000000000000000000000002",
    "0x420000000000000000000000000000000000000f",
    "0x4200000000000000000000000000000000000006",
    "0x4200000000000000000000000000000000000007",
    "0x0000000000000000000000000000000000000000",
    "0x0000000000000000000000000000000000001010",
}

# Known Mantle DEX routers
KNOWN_PROTOCOLS = {
    "0x795548d49b77f43a81bce4b473e45b4e3a315cb8": "merchant_moe",
    "0x31775ebe409be7c157909f7ef28042c2e4d7f7b4": "agni",
    "0xa16d2e503606e5b765c0c68d4f8bb39d5e3d8a4c": "merchant_moe_v2",
}

# Known tokens on Mantle
TOKENS = {
    "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9": "USDC",
    "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae": "USDT",
    "0xdEAddEaDdeadDEadDEADDEAddEADDEAddead1111": "WETH",
    "0x78c1b0c915c4faa5fffa6cabf0219da63d7f4cb8": "MNT",
    "0xdeaddeaddeaddeaddeaddeaddeaddeaddead0000": "MNT",
}

# Function selectors → tx type
FUNC_SELECTORS = {
    # DEX swap functions
    "0x38ed1739": "swap",  # swapExactTokensForTokens
    "0x7ff36ab5": "swap",  # swapExactETHForTokens
    "0x18cbafe5": "swap",  # swapExactTokensForETH
    "0xfb3bdb41": "swap",  # swapETHForExactTokens
    "0x5c11d795": "swap",  # swapExactTokensForTokensSupportingFeeOnTransferTokens
    "0xb6f9de95": "swap",  # swapExactETHForTokensSupportingFeeOnTransferTokens
    "0x1249c58b": "swap",  # mint (AMM)
    "0xa9059cbb": "erc20_transfer",  # transfer
    "0x23b872dd": "erc20_transfer",  # transferFrom
    "0x095ea7b3": "approve",  # approve
    "0xd0e30db0": "deposit",  # deposit (WETH)
    "0x2e1a7d4d": "withdraw",  # withdraw (WETH)
    "0x3593564c": "swap",  # multicall (Uniswap V3)
    "0x5ae401dc": "swap",  # multicall (Uniswap V3 alt)
    "0x128acb08": "swap",  # swapExactTokensForTokens (V3)
    "0xc04b8d59": "swap",  # exactInput
    "0xdb3e2198": "swap",  # exactOutput
}


def is_system_tx(tx: dict) -> bool:
    """Check if tx is a system-level tx."""
    from_addr = (tx.get("from_address") or "").lower()
    to_addr = (tx.get("to_address") or "").lower()

    if from_addr in SYSTEM_ADDRS or to_addr in SYSTEM_ADDRS:
        return True

    if to_addr.startswith("0x420000000000000000000000000000000000") and tx.get("value_native", 0) == 0:
        return True

    # Filter 0-value contract calls to unknown contracts (noise)
    if tx.get("value_native", 0) == 0 and to_addr not in KNOWN_PROTOCOLS and to_addr not in TOKENS:
        input_data = tx.get("input_data", "0x")
        if input_data and len(input_data) > 10:
            return True

    return False


def _get_selector(input_data: str) -> str:
    """Extract first 4 bytes (function selector) from input data."""
    if not input_data or len(input_data) < 10:
        return ""
    return input_data[:10].lower()


def classify_tx(tx: dict) -> dict | None:
    """Classify a transaction by type and protocol.

    Returns None if tx should be filtered out (system tx).
    """
    if is_system_tx(tx):
        return None

    to_addr = (tx.get("to_address") or "").lower()
    input_data = tx.get("input_data", "0x")
    selector = _get_selector(input_data)

    # Detect protocol
    protocol = KNOWN_PROTOCOLS.get(to_addr, "unknown")

    # Detect token (if sending to a token contract with 0 value, it's likely an ERC20 interaction)
    token = TOKENS.get(to_addr, "MNT")

    # Detect tx type by function selector
    tx_type = FUNC_SELECTORS.get(selector, None)

    if tx_type is None:
        # Fallback: classify by context
        if protocol != "unknown":
            tx_type = "swap"
        elif selector and len(selector) >= 10:
            tx_type = "contract"
        elif to_addr == "":
            tx_type = "contract_creation"
        else:
            tx_type = "transfer"

    tx["tx_type"] = tx_type
    tx["protocol"] = protocol
    tx["token"] = token

    return tx
