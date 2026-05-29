# MantleSentry

AI-powered smart money tracker on Mantle Network.

实时分析 Mantle 链上大额交易和聪明钱动向，AI 自然语言解读 + 可视化 Dashboard + 异常预警。

## Tech Stack

- Backend: Python + FastAPI + WebSocket
- AI: Qwen3.5:9b (local Ollama, zero latency, unlimited calls)
- Data: Mantle RPC + web3.py
- Frontend: HTML + Tailwind CSS + ECharts
- DB: SQLite

## Quick Start

```bash
# 1. Install Ollama & pull model
ollama pull qwen3.5:9b

# 2. Install deps
pip install -r requirements.txt

# 3. Run
uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000

## Project Structure

```
backend/
├── main.py              # FastAPI entry + scan loop
├── config.py            # Config from .env
├── scanner/
│   ├── block_scanner.py # Mantle block fetcher
│   └── tx_classifier.py # Tx type/protocol classifier
├── analyzer/
│   ├── ai_analyzer.py   # Ollama Qwen AI analysis
│   ├── whale_detector.py# Smart money detection
│   └── anomaly.py       # Anomaly detection rules
├── models/
│   ├── database.py      # SQLite schema + connection
│   └── schemas.py       # Pydantic models
├── api/
│   ├── transactions.py
│   ├── addresses.py
│   ├── alerts.py
│   └── summary.py
└── ws/
    └── handler.py       # WebSocket push

frontend/
├── index.html           # Dashboard
├── address.html         # Address detail
├── analysis.html        # Charts + AI summary
├── css/style.css
└── js/
    ├── app.js
    ├── websocket.js
    └── charts.js
```

## License

MIT
