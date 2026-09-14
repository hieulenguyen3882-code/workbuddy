@echo off
cd /d "%~dp0"
echo Starting Douyin content bridge (http://localhost:8910) ...
node bridge\server.js
