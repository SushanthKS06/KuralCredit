FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY backend/pyproject.toml ./backend/
RUN pip install --upgrade pip && \
    pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "pydantic>=2.7.0" \
    "pydantic-settings>=2.2.0" "sqlalchemy>=2.0.30" "alembic>=1.13.0" \
    "httpx>=0.27.0" "python-jose[cryptography]>=3.3.0" "PyJWT>=2.8.0" \
    "python-multipart>=0.0.9" "pypdf>=4.2.0" "openpyxl>=3.1.2" \
    "groq>=0.9.0"

COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/tests ./tests
COPY scripts ./scripts

RUN mkdir -p /data/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

