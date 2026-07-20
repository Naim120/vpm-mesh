#!/bin/bash

# Navigate to project directory
cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start Tor daemon if installed
if command -v tor > /dev/null 2>&1; then
    echo "Starting Tor SOCKS5 proxy on 127.0.0.1:9050..."
    tor --SocksPort 9050 --ControlPort 9051 --CookieAuthentication 0 &
    sleep 3
fi

# Fallback port configuration for cloud hostings
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "Starting server on http://$HOST:$PORT ..."
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
