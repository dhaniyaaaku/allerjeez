#!/bin/sh
# Allerjeez startup script — runs FastAPI + Streamlit in one container.

export PATH="/app/.venv/bin:$PATH"

echo "[start.sh] PATH=$PATH"
echo "[start.sh] launching FastAPI on 127.0.0.1:8000..."

uvicorn app.main:app --host 127.0.0.1 --port 8000 &
FASTAPI_PID=$!
echo "[start.sh] FastAPI pid=$FASTAPI_PID"

PORT="${PORT:-8080}"
echo "[start.sh] launching Streamlit on 0.0.0.0:$PORT..."

exec streamlit run frontend/streamlit_app.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false
