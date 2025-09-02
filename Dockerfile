FROM mcr.microsoft.com/powershell:7.4-ubuntu-22.04

ENV DEBIAN_FRONTEND=noninteractive

# System deps: Python, pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# Python libs
RUN python3 -m pip install --no-cache-dir fastapi uvicorn[standard] httpx msal sse-starlette python-dotenv

# PowerShell Graph SDK (optional, for pwsh executor)
RUN pwsh -NoLogo -NoProfile -Command \  "Set-PSRepository -Name PSGallery -InstallationPolicy Trusted; Install-Module Microsoft.Graph -Force"

WORKDIR /app
COPY app/ /app/
COPY pwsh/ /opt/pwsh/

ENV TZ=${TZ}
ENV PYTHONUNBUFFERED=1

EXPOSE 8080
CMD [ "python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080" ]
