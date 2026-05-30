#!/bin/bash
# MantleSentry 一键启动脚本
# 用法：bash start.sh

cd "$(dirname "$0")"

echo "=== MantleSentry 启动 ==="

# 杀掉旧进程
lsof -ti:8100 | xargs kill -9 2>/dev/null
pkill -f "cloudflared tunnel run" 2>/dev/null
sleep 1

# 启动后端
echo "[1/2] 启动后端 (port 8100)..."
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8100 > /tmp/mantle-sentry.log 2>&1 &
echo "  PID: $!"

# 等后端就绪
sleep 3

# 启动 tunnel
echo "[2/2] 启动 Cloudflare Tunnel (sentry.ejuerz.com)..."
nohup cloudflared tunnel run --url http://localhost:8100 mantle-sentry > /tmp/mantle-tunnel.log 2>&1 &
echo "  PID: $!"

sleep 3

# 检查
if curl -s -o /dev/null -w "%{http_code}" https://sentry.ejuerz.com | grep -q 200; then
    echo ""
    echo "=== 启动成功 ==="
    echo "  本地: http://localhost:8100"
    echo "  公网: https://sentry.ejuerz.com"
    echo "  日志: tail -f /tmp/mantle-sentry.log"
else
    echo ""
    echo "=== 启动可能需要更多时间，稍等再检查 ==="
    echo "  检查: curl -s -o /dev/null -w '%{http_code}' https://sentry.ejuerz.com"
fi
