FROM python:3.11-slim

ARG TZ=Asia/Seoul
ENV TZ=${TZ}
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

 # Install uv
RUN pip install --no-cache-dir uv

 # Server dependencies (e.g. FastAPI)
COPY pyproject.toml ./
RUN uv pip install --system --requirements pyproject.toml

 # Application code
 # Explicitly copy required files.
 # Example: COPY app/ ./app/
 # Or, for development convenience, volume mount (./app:/app) is already set in docker-compose, so can be omitted

ENV PYTHONUNBUFFERED=1

ARG PORT=8081
ENV PORT=${PORT}
EXPOSE ${PORT}

 # Run MCP server (main:app location should match your project)
CMD ["sh", "-c", "python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT"]
