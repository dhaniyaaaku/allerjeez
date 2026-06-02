FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/
COPY frontend/ ./frontend/
COPY data/ ./data/
COPY scripts/ ./scripts/
COPY start.sh ./

RUN chmod +x ./start.sh

# Streamlit binds to $PORT (Render's required port).
# FastAPI runs internally on 8000.
EXPOSE 8080

CMD ["./start.sh"]
