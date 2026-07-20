# Multi-stage build for FastAPI + Tor SOCKS5 bundle
FROM python:3.12-slim

# Install Tor and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    tor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configure Tor SOCKS5 port (9050) and ControlPort (9051)
RUN echo "SocksPort 0.0.0.0:9050" >> /etc/tor/torrc && \
    echo "ControlPort 9051" >> /etc/tor/torrc && \
    echo "CookieAuthentication 0" >> /etc/tor/torrc

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

EXPOSE 8000

# Entrypoint script to launch Tor daemon and FastAPI uvicorn server
CMD ["sh", "-c", "tor & sleep 4 && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
