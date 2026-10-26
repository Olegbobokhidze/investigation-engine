# Production image for the API, deployed to Google Cloud Run (see
# .github/workflows/deploy-api.yml). Build locally: docker build -t investigation-engine-api .
FROM python:3.12.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

# Run as an unprivileged user, not root.
RUN useradd --create-home app
USER app
WORKDIR /home/app/api

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/home/app/api/.venv/bin:$PATH" \
    FASTEMBED_CACHE_PATH=/home/app/models \
    ENV=prod

# Dependencies before source code, so a code change doesn't reinstall them.
COPY --chown=app pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY --chown=app src ./src
RUN uv sync --locked --no-dev

# Bake the embedding models into the image, so a cold start doesn't download them.
RUN python -c "from investigation_engine.core.config import Settings; \
from investigation_engine.retrieval.embeddings import Embedder; \
settings = Settings(); Embedder(settings.embedding_model, settings.embedding_query_prefix)"

# Cloud Run sends traffic to port 8080.
EXPOSE 8080
CMD ["uvicorn", "--factory", "investigation_engine.main:create_app", "--host", "0.0.0.0", "--port", "8080"]
