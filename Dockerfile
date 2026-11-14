# The live demo server (see src/dhairya/web/server.py). Free hosts such as Render build this as is.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv

WORKDIR /app
# Dependencies first, so a code change does not reinstall them. The Smart Turn baseline group
# (onnxruntime, transformers) is left out: the live agent does not use it.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-default-groups --no-install-project

COPY src ./src
COPY demo ./demo
RUN uv sync --frozen --no-default-groups

ENV PORT=10000
EXPOSE 10000
CMD ["sh", "-c", "exec uv run --no-sync uvicorn dhairya.web.server:app --host 0.0.0.0 --port ${PORT}"]
