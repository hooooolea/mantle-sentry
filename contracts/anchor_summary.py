"""Anchor a daily summary hash on-chain.

Usage:
    python anchor_summary.py "2026-05-30" "summary text here"
"""

import hashlib
import json
import os
import sys
from web3 import Web3

CONTRACT_INFO = os.path.join(os.path.dirname(__file__), "contract_info.json")


def anchor(date: str, summary_text: str):
    """Store keccak256 hash of summary text on-chain."""
    if not os.path.exists(CONTRACT_INFO):
        print("ERROR: contract_info.json not found. Run deploy_contract.py first.")
        sys.exit(1)

    with open(CONTRACT_INFO) as f:
        info = json.load(f)

    private_key = os.getenv("DEPLOYER_PRIVATE_KEY")
    if not private_key:
        print("ERROR: Set DEPLOYER_PRIVATE_KEY")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(info["rpc_url"]))
    account = w3.eth.account.from_key(private_key)

    # Load contract
    contract = w3.eth.contract(
        address=info["address"],
        abi=info["abi"],
    )

    # Hash the summary
    summary_hash = Web3.keccak(text=summary_text)

    # Build tx
    tx = contract.functions.anchorSummary(date, summary_hash).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200000,
        "gasPrice": w3.eth.gas_price,
        "chainId": info["chain_id"],
    })

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    print(f"Anchored: {date}")
    print(f"Hash:     {summary_hash.hex()}")
    print(f"TX:       {info['rpc_url'].replace('rpc.', 'explorer.').replace('/rpc', '')}/tx/{tx_hash.hex()}")
    return tx_hash.hex()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python anchor_summary.py YYYY-MM-DD 'summary text'")
        sys.exit(1)
    anchor(sys.argv[1], sys.argv[2])
