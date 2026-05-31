"""Deploy MantleSentryAnchor contract to Mantle testnet.

Usage:
    python deploy_contract.py

Requires:
    pip install py-solc-x web3
    
Environment:
    DEPLOYER_PRIVATE_KEY — private key with testnet MNT
"""

import json
import os
import sys
from solcx import compile_standard, install_solc
from web3 import Web3

# Mantle Testnet
RPC_URL = "https://rpc.testnet.mantle.xyz"
CHAIN_ID = 5003
EXPLORER = "https://explorer.testnet.mantle.xyz"

# Solidity source
CONTRACT_PATH = os.path.join(os.path.dirname(__file__), "MantleSentryAnchor.sol")


def compile_contract():
    """Compile the Solidity contract."""
    install_solc("0.8.19")

    with open(CONTRACT_PATH, "r") as f:
        source = f.read()

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {"MantleSentryAnchor.sol": {"content": source}},
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}
                }
            },
        },
        solc_version="0.8.19",
    )

    contract = compiled["contracts"]["MantleSentryAnchor.sol"]["MantleSentryAnchor"]
    return contract["abi"], contract["evm"]["bytecode"]["object"]


def deploy(abi, bytecode):
    """Deploy contract to Mantle testnet."""
    private_key = os.getenv("DEPLOYER_PRIVATE_KEY")
    if not private_key:
        print("ERROR: Set DEPLOYER_PRIVATE_KEY environment variable")
        print("  export DEPLOYER_PRIVATE_KEY=0x...")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"ERROR: Cannot connect to {RPC_URL}")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    print(f"Deployer: {account.address}")
    print(f"Balance:  {w3.from_wei(balance, 'ether')} MNT")

    if balance == 0:
        print("ERROR: No testnet MNT. Get some from: https://faucet.testnet.mantle.xyz")
        sys.exit(1)

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Build transaction
    tx = Contract.constructor().build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 500000,
        "gasPrice": w3.eth.gas_price,
        "chainId": CHAIN_ID,
    })

    # Sign and send
    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TX sent: {EXPLORER}/tx/{tx_hash.hex()}")

    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    contract_address = receipt.contractAddress
    print(f"\n=== Deployed ===")
    print(f"Contract: {contract_address}")
    print(f"Explorer: {EXPLORER}/address/{contract_address}")
    print(f"TX:       {EXPLORER}/tx/{tx_hash.hex()}")

    # Save ABI and address
    output = {
        "address": contract_address,
        "abi": abi,
        "chain_id": CHAIN_ID,
        "rpc_url": RPC_URL,
    }
    output_path = os.path.join(os.path.dirname(__file__), "contract_info.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to: {output_path}")

    return contract_address


if __name__ == "__main__":
    print("=== Compiling contract ===")
    abi, bytecode = compile_contract()
    print("Compiled OK")
    print("\n=== Deploying to Mantle Testnet ===")
    deploy(abi, bytecode)
