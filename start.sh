#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "启动抖音内容读取桥 (http://localhost:8910) ..."
node bridge/server.js
