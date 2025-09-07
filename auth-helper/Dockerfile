FROM python:3.11-slim

ARG TZ=Asia/Seoul
ENV TZ=${TZ}
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/auth-helper

# writable secrets location (mounted by compose)
RUN mkdir -p /opt/secrets && chmod -R 777 /opt/secrets

# azure-cli install (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli/ bookworm main" > /etc/apt/sources.list.d/azure-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends azure-cli \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*

# python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY . ./

CMD ["tail", "-f", "/dev/null"]
