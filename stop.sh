#!/bin/bash
# MantleSentry 一键停止
lsof -ti:8100 | xargs kill -9 2>/dev/null && echo "后端已停止" || echo "后端未运行"
pkill -f "cloudflared tunnel run" 2>/dev/null && echo "Tunnel 已停止" || echo "Tunnel 未运行"
