#!/bin/bash
# MantleSentry 一键启动
cd "$(dirname "$0")"

# 杀旧进程
lsof -ti:8100 | xargs kill -9 2>/dev/null
pkill -f "cloudflared tunnel run" 2>/dev/null
sleep 1

# 启动后端
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8100 > /tmp/mantle-sentry.log 2>&1 &
echo "后端启动 (PID $!)"

sleep 3

# 启动 tunnel
nohup cloudflared tunnel run --url http://localhost:8100 mantle-sentry > /tmp/mantle-tunnel.log 2>&1 &
echo "Tunnel 启动 (PID $!)"

sleep 3

# 验证
code=$(curl -s -o /dev/null -w "%{http_code}" https://sentry.ejuerz.com)
if [ "$code" = "200" ]; then
    echo "OK: https://sentry.ejuerz.com"
else
    echo "等待就绪... (HTTP $code)"
fi
