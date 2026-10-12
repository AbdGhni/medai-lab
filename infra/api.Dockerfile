# API MedAI Lab (CPU). Construire depuis la racine du dépôt : docker build -f infra/api.Dockerfile .
FROM python:3.13-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --no-cache-dir uv==0.11.* || pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY ml ml
COPY services services
RUN uv sync --frozen --no-dev

FROM python:3.13-slim
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    MEDAI_REPORTS_DIR=/data/reports MEDAI_ARTIFACTS_DIR=/data/artifacts MEDAI_GALLERY_DIR=/data/gallery
RUN useradd --system --uid 10001 --home /app medai
WORKDIR /app
COPY --from=build /app /app
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--app-dir", "services/api", "--host", "0.0.0.0", "--port", "8000"]
