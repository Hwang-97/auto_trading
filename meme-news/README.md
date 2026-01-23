# MemeNews

뉴스/트렌드 기반 밈을 자동 생성하고 YouTube Shorts, TikTok, Instagram Reels에 업로드하는 콘텐츠 자동화 시스템입니다.

## 핵심 기능

### 1. 콘텐츠 소스
- **일상 (AI 창작)**: 직장생활, 연애, 가족, 친구, 일상 주제로 공감 밈 생성
- **트렌드**: 구글 트렌드, 네이버 실검 기반 실시간 밈
- **뉴스 (IT, 주식, 국제)**: RSS 피드 기반 뉴스 밈

### 2. 밈 생성
- **Gemini API**: MZ세대 스타일의 밈 텍스트 생성 (15자 이내)
- **Pillow**: 1080x1920 그라데이션 배경 이미지 생성
- **FFmpeg + gTTS**: 15-30초 숏폼 비디오 생성

### 3. 플랫폼 업로드
- **YouTube**: Data API v3를 통한 자동 업로드
- **TikTok**: 수동 업로드 안내 (알림 전송)
- **Instagram**: 수동 업로드 안내 (알림 전송)

### 4. 채널 시스템
| 채널 | 이름 | 카테고리 | 플랫폼 | 일일 개수 |
|------|------|----------|--------|-----------|
| daily_meme | 일상밈공장 | 일상 | YouTube, TikTok | 5개 |
| trend_meme | 오늘의밈 | 트렌드 | YouTube, TikTok, Instagram | 3개 |
| it_meme | IT밈 | IT | YouTube, TikTok | 2개 |

## 기술 스택

- Python 3.10+
- google-generativeai (Gemini API)
- Pillow, FFmpeg, gTTS
- feedparser, beautifulsoup4
- google-api-python-client (YouTube)
- APScheduler
- SQLite

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/your-repo/meme-news.git
cd meme-news
```

### 2. 가상환경 생성

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. FFmpeg 설치

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# https://ffmpeg.org/download.html
```

### 5. 한글 폰트 설치 (선택)

```bash
# Ubuntu/Debian
sudo apt-get install fonts-nanum
```

## 설정

### 환경 변수 (.env)

```bash
# AI API
GEMINI_API_KEY=your_gemini_api_key

# YouTube API
YOUTUBE_API_KEY=your_youtube_api_key
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret

# TikTok
TIKTOK_ACCESS_TOKEN=your_tiktok_token
TIKTOK_OPEN_ID=your_open_id

# Instagram
INSTAGRAM_ACCESS_TOKEN=your_instagram_token
INSTAGRAM_ACCOUNT_ID=your_account_id

# 알림 (선택)
SLACK_WEBHOOK_URL=your_slack_webhook
DISCORD_WEBHOOK_URL=your_discord_webhook
```

### YouTube API 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. YouTube Data API v3 활성화
3. OAuth 2.0 클라이언트 ID 생성
4. `client_secrets.json` 다운로드 후 프로젝트 루트에 저장

## CLI 사용법

```bash
# 특정 채널 실행
python main.py --channel daily_meme    # 일상밈공장
python main.py --channel trend_meme    # 오늘의밈
python main.py --channel it_meme       # IT밈

# 전체 채널 실행
python main.py --all

# 스케줄러 모드 (기본)
python main.py --schedule
python main.py                         # 동일

# 테스트 모드 (업로드 안함)
python main.py --dry-run --channel daily_meme
python main.py --dry-run --all

# 디버그 모드
python main.py --debug --channel daily_meme
```

## 프로젝트 구조

```
meme-news/
├── config/
│   ├── config.yaml         # 앱 설정, 환경변수 키, 로깅
│   ├── channels.yaml       # 채널 정의 (daily_meme, trend_meme, it_meme)
│   ├── sources.yaml        # 콘텐츠 소스 (RSS, 트렌드, AI 주제)
│   ├── platforms.yaml      # 플랫폼 스펙 (YouTube, TikTok, Instagram)
│   └── prompts.yaml        # LLM 프롬프트 템플릿
├── src/
│   ├── core/
│   │   ├── config_loader.py   # YAML 설정 로더
│   │   ├── pipeline.py        # 콘텐츠 생성 파이프라인
│   │   └── scheduler.py       # APScheduler 기반 스케줄러
│   ├── content/
│   │   ├── news_crawler.py    # RSS 피드 크롤러
│   │   ├── trend_crawler.py   # 트렌드 수집기
│   │   └── ai_generator.py    # Gemini API 연동
│   ├── meme/
│   │   ├── text_gen.py        # 텍스트 포맷터
│   │   ├── image_gen.py       # Pillow 이미지 생성
│   │   └── video_gen.py       # FFmpeg 비디오 생성
│   ├── platforms/
│   │   ├── base.py            # 플랫폼 베이스 클래스
│   │   ├── youtube.py         # YouTube Data API
│   │   ├── tiktok.py          # TikTok API
│   │   └── instagram.py       # Instagram Graph API
│   ├── optimizer/
│   │   └── platform_optimizer.py  # 플랫폼별 최적화
│   └── utils/
│       ├── logger.py          # 로깅 유틸리티
│       └── notifier.py        # Slack/Discord 알림
├── templates/
│   └── meme_templates/        # 밈 템플릿 이미지
├── output/
│   ├── daily_meme/            # 일상밈 출력
│   ├── trend_meme/            # 트렌드밈 출력
│   └── it_meme/               # IT밈 출력
├── data/
│   └── memenews.db            # SQLite 데이터베이스
├── main.py                    # CLI 엔트리포인트
├── requirements.txt
└── .env.example
```

## 콘텐츠 생성 흐름

```
1. 콘텐츠 수집
   ├── daily: AI가 주제 선택 (직장생활, 연애 등)
   ├── trend: 구글 트렌드 / 네이버 실검 수집
   └── it/stock: RSS 피드 크롤링

2. 밈 텍스트 생성 (Gemini API)
   ├── 상단 텍스트 (15자 이내)
   ├── 하단 텍스트 (15자 이내)
   ├── 나레이션 (TTS용)
   └── 해시태그

3. 이미지 생성 (Pillow)
   ├── 1080x1920 그라데이션 배경
   ├── 상단/하단 텍스트 오버레이
   └── 채널 워터마크

4. 비디오 생성 (FFmpeg + gTTS)
   ├── TTS 오디오 생성
   ├── 이미지 + 오디오 합성
   └── 15-30초 MP4 출력

5. 플랫폼 업로드
   ├── YouTube: 자동 업로드 (API)
   ├── TikTok: 수동 업로드 안내
   └── Instagram: 수동 업로드 안내
```

## 스케줄 설정

`config/channels.yaml`에서 각 채널의 스케줄을 설정합니다:

```yaml
channels:
  daily_meme:
    schedule:
      count: 5
      times:
        - "09:00"
        - "12:00"
        - "15:00"
        - "18:00"
        - "21:00"
```

## 알림 설정

Slack 또는 Discord 웹훅을 설정하면 다음 이벤트에 알림을 받습니다:
- 콘텐츠 생성 완료
- 업로드 성공/실패
- 수동 업로드 필요
- 에러 발생

## 라이선스

MIT License
