# Optival — FastAPI + built React UI
FROM node:22-alpine AS frontend
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY application_analyzer ./application_analyzer
COPY llm_score ./llm_score
COPY api ./api
COPY rubric ./rubric
COPY --from=frontend /ui/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CORS_ORIGINS=*

EXPOSE 8000

# One worker: screening jobs live in process memory.
CMD ["python", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
