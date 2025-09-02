FROM python:3.11-slim

ARG TZ=Asia/Seoul
ENV TZ=${TZ}
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/auth-helper

# --- azure-cli (APT) 설치 ---
# base: debian bookworm (python:3.11-slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli/ bookworm main" \
    > /etc/apt/sources.list.d/azure-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends azure-cli \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*

# --- uv 설치 & 파이썬 deps 설치 ---
RUN pip install --no-cache-dir uv

COPY pyproject.toml ./     
COPY auth-helper.py ./

RUN uv pip install --system --requirements pyproject.toml

CMD ["tail", "-f", "/dev/null"]
