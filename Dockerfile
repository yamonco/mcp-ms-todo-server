FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (optional; keep lean)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install runtime deps (from pyproject or explicit)
COPY pyproject.toml ./
RUN python -m pip install --upgrade pip && \
    python - <<'PY'
import tomllib, sys, subprocess
data = tomllib.loads(open('pyproject.toml','rb').read())
deps = data.get('project',{}).get('dependencies',[])
cmd = [sys.executable,'-m','pip','install','--no-cache-dir', *deps]
print('Installing deps:', deps)
subprocess.check_call(cmd)
PY

# Copy app
COPY app/ ./app/

# Runtime
ARG PORT=8081
ENV PORT=${PORT}
EXPOSE ${PORT}

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
