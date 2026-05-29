"""Transaction classifier — identifies tx type and protocol."""

import logging

logger = logging.getLogger(__name__)

# Known Mantle DEX routers
KNOWN_PROTOCOLS = {
    # Merchant Moe
    "0x795548d49b77f43a81bce4b473e45b4e3a315cb8": "merchant_moe",
    # Agni Finance
    "0x31775ebe409be7c157909f7ef28042c2e4d7f7b4": "agni",
    # Byreal (placeholder — fill in actual address)
    # "0x...": "byreal",
}

# Known stablecoins on Mantle
STABLECOINS = {
    "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9": "USDC",
    "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae": "USDT",
    "0xdEAddEaDdeadDEadDEADDEAddEADDEAddead1111": "WETH",
    "0x78c1b0c915c4faa5fffa6cabf0219da63d7f4cb8": "MNT",
}


def classify_tx(tx: dict) -> dict:
    """Classify a transaction by type and protocol.
    
    Args:
        tx: dict with from_address, to_address, input_data, value_native
        
    Returns:
        dict with tx_type, protocol, token fields added
    """
    to_addr = (tx.get("to_address") or "").lower()
    input_data = tx.get("input_data", "0x")
    
    # Detect protocol
    protocol = KNOWN_PROTOCOLS.get(to_addr, "unknown")
    
    # Detect token
    token = STABLECOINS.get(to_addr, "MNT")
    
    # Detect tx type
    tx_type = "transfer"  # default
    if protocol != "unknown":
        tx_type = "swap"
    elif input_data and len(input_data) > 10:
        # Has contract interaction but not a known DEX
        tx_type = "contract"
    elif to_addr == "":
        tx_type = "contract_creation"
    
    tx["tx_type"] = tx_type
    tx["protocol"] = protocol
    tx["token"] = token
    
    return tx
