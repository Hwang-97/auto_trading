# MemeNews Docker Image
FROM python:3.11-slim

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_HOME=/app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-nanum \
    fonts-nanum-coding \
    fonts-nanum-extra \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR ${APP_HOME}

# 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 디렉토리 생성
RUN mkdir -p data output/images output/videos logs

# 비root 사용자 생성
RUN useradd -m -u 1000 memenews && \
    chown -R memenews:memenews ${APP_HOME}

USER memenews

# 포트 노출 (Admin 패널)
EXPOSE 8000

# 기본 명령어
CMD ["python", "-m", "uvicorn", "admin.app:app", "--host", "0.0.0.0", "--port", "8000"]
