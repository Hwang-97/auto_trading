# YOLO 개발 로그

## 2025년 8월 20일

- `yolo` 디렉터리 생성
- 개발 로그 파일 (`development_log.md`) 생성
- **1단계: 프로젝트 기본 구조 설정 완료**
    - `src`, `tests`, `data`, `docs`, `config` 디렉터리 생성
    - `requirements.txt` 파일 생성 및 의존성 라이브러리 설치 완료
- **2단계: 데이터베이스 추상화 계층 구축 완료**
    - `yolo/src/database` 디렉터리 생성
    - `connection.py`: SQLAlchemy를 이용한 DB 연결 및 세션 관리 모듈 작성 (SQLite 기반)
    - `models.py`: DB 테이블 모델의 기반이 될 `Base` 클래스 정의
    - `yolo/tests/test_database.py`: DB 연결을 검증하는 단위 테스트 작성 및 통과
- **3단계: 주식 데이터 수집 모듈 및 스케줄러 구현**
    - `yolo/src/collectors`: 데이터 수집기 기본 구조(`base.py`) 및 주식 데이터 수집기(`stock_collector.py`) 구현
    - `yolo/tests/test_stock_collector.py`: `StockCollector`의 기능(수집, 저장, 파이프라인)에 대한 단위 테스트 작성 및 통과
    - `yolo/config/settings.py`: DB 연결 정보 및 스케줄러 설정 분리
    - `yolo/config/watchlist.py`: 수집할 주식 목록 관리 기능 추가
    - `yolo/src/scheduler.py`: `APScheduler`를 사용하여 `watchlist`의 주식 데이터를 주기적으로 수집하는 스케줄러 구현
