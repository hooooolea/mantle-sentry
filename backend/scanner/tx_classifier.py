"""Transaction classifier — identifies tx type and protocol, filters system txs."""

import logging

logger = logging.getLogger(__name__)

# System / burn addresses to skip
SYSTEM_ADDRS = {
    "0xdeaddeaddeaddeaddeaddeaddeaddeaddead0000",  # Mantle burn
    "0x4200000000000000000000000000000000000000",  # L2 predeploy base
    "0x4200000000000000000000000000000000000010",  # L2 gas price oracle
    "0x4200000000000000000000000000000000000001",  # L1 block
    "0x4200000000000000000000000000000000000002",  # deployer whitelister
    "0x420000000000000000000000000000000000000f",  # L2ERC721Bridge
    "0x4200000000000000000000000000000000000006",  # WETH9
    "0x4200000000000000000000000000000000000007",  # L2StandardBridge
    "0x0000000000000000000000000000000000000000",  # zero addr
    "0x0000000000000000000000000000000000001010",  # system fee
}

# Known Mantle DEX routers
KNOWN_PROTOCOLS = {
    "0x795548d49b77f43a81bce4b473e45b4e3a315cb8": "merchant_moe",
    "0x31775ebe409be7c157909f7ef28042c2e4d7f7b4": "agni",
    "0xa16d2e503606e5b765c0c68d4f8bb39d5e3d8a4c": "merchant_moe_v2",
}

# Known stablecoins / tokens on Mantle
TOKENS = {
    "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9": "USDC",
    "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae": "USDT",
    "0xdEAddEaDdeadDEadDEADDEAddEADDEAddead1111": "WETH",
    "0x78c1b0c915c4faa5fffa6cabf0219da63d7f4cb8": "MNT",
    "0xdeaddeaddeaddeaddeaddeaddeaddeaddead0000": "MNT",  # burn addr holds MNT
}


def is_system_tx(tx: dict) -> bool:
    """Check if tx is a system-level tx (L1→L2 messaging, burns, etc)."""
    from_addr = (tx.get("from_address") or "").lower()
    to_addr = (tx.get("to_address") or "").lower()

    if from_addr in SYSTEM_ADDRS or to_addr in SYSTEM_ADDRS:
        return True

    # Filter 0-value txs to system predeploys (0x42000000...)
    if to_addr.startswith("0x420000000000000000000000000000000000") and tx.get("value_native", 0) == 0:
        return True

    # Filter 0-value contract calls to unknown contracts (noise)
    if tx.get("value_native", 0) == 0 and to_addr not in KNOWN_PROTOCOLS and to_addr not in TOKENS:
        input_data = tx.get("input_data", "0x")
        if input_data and len(input_data) > 10:
            return True

    return False


def classify_tx(tx: dict) -> dict | None:
    """Classify a transaction by type and protocol.

    Returns None if tx should be filtered out (system tx).
    Otherwise returns tx with tx_type, protocol, token added.
    """
    if is_system_tx(tx):
        return None

    to_addr = (tx.get("to_address") or "").lower()
    from_addr = (tx.get("from_address") or "").lower()
    input_data = tx.get("input_data", "0x")

    # Detect protocol
    protocol = KNOWN_PROTOCOLS.get(to_addr, "unknown")

    # Detect token
    token = TOKENS.get(to_addr, "MNT")

    # Detect tx type
    tx_type = "transfer"
    if protocol != "unknown":
        tx_type = "swap"
    elif input_data and len(input_data) > 10:
        tx_type = "contract"
    elif to_addr == "":
        tx_type = "contract_creation"

    tx["tx_type"] = tx_type
    tx["protocol"] = protocol
    tx["token"] = token

    return tx
