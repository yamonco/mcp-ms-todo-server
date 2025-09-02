FROM python:3.11-slim

ARG TZ=Asia/Seoul
ENV TZ=${TZ}
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# uv 설치
RUN pip install --no-cache-dir uv

# 서버 의존성(예: FastAPI 등)
COPY pyproject.toml ./
RUN uv pip install --system --requirements pyproject.toml

# 애플리케이션 코드
# 필요한 파일을 명시적으로 복사하세요.
# 예: COPY app/ ./app/
# 또는 개발 편의를 위해 docker-compose에서 볼륨 마운트(./app:/app)를 이미 했으니 생략 가능

ENV PYTHONUNBUFFERED=1

ARG PORT=8081
ENV PORT=${PORT}
EXPOSE ${PORT}

# MCP 서버 구동 (main:app 위치는 프로젝트에 맞게 조정)
CMD ["sh", "-c", "python3 -m uvicorn main:app --host 0.0.0.0 --port $PORT"]
