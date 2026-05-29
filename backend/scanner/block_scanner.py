"""Mantle block scanner — fetches latest blocks and extracts transactions."""

import asyncio
import logging
from web3 import Web3

from backend.config import MANTLE_RPC_URL, MANTLE_CHAIN_ID

logger = logging.getLogger(__name__)


class BlockScanner:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL))
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to Mantle RPC: {MANTLE_RPC_URL}")
        self.last_scanned_block = 0
        logger.info(f"Connected to Mantle (chain {MANTLE_CHAIN_ID}), latest block: {self.w3.eth.block_number}")

    def get_latest_block(self) -> int:
        return self.w3.eth.block_number

    def get_block_transactions(self, block_number: int) -> list[dict]:
        """Fetch all transactions in a block."""
        try:
            block = self.w3.eth.get_block(block_number, full_transactions=True)
        except Exception as e:
            logger.error(f"Failed to fetch block {block_number}: {e}")
            return []

        txs = []
        for tx in block.transactions:
            value_wei = tx.get("value", 0)
            value_eth = float(Web3.from_wei(value_wei, "ether"))
            txs.append({
                "tx_hash": tx["hash"].hex(),
                "block_number": block_number,
                "timestamp": block.timestamp,
                "from_address": tx["from"],
                "to_address": tx.get("to"),
                "value_native": value_eth,
                "input_data": tx.get("input", "0x").hex() if isinstance(tx.get("input"), bytes) else tx.get("input", "0x"),
            })
        return txs

    async def scan_new_blocks(self) -> list[dict]:
        """Scan all blocks since last scan. Returns list of transactions."""
        latest = self.get_latest_block()
        if latest <= self.last_scanned_block:
            return []

        all_txs = []
        for block_num in range(self.last_scanned_block + 1, latest + 1):
            txs = self.get_block_transactions(block_num)
            all_txs.extend(txs)
            logger.info(f"Block {block_num}: {len(txs)} transactions")

        self.last_scanned_block = latest
        return all_txs
