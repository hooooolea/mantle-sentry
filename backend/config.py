import os
from dotenv import load_dotenv

load_dotenv()

# Mantle Network
MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
MANTLE_CHAIN_ID = int(os.getenv("MANTLE_CHAIN_ID", "5000"))

# Local Ollama (Qwen3.5:9b)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

# Database
DB_PATH = os.getenv("DB_PATH", "data/mantle_sentry.db")

# Scanner
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL", "12"))
WHALE_THRESHOLD_USD = float(os.getenv("WHALE_THRESHOLD", "10000"))
