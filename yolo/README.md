# YOLO - 주식 데이터 수집 및 분석 플랫폼

## 개요

YOLO는 주식, 뉴스, 사용자 정의 데이터 등 다양한 금융 관련 데이터를 수집하고 관리하기 위한 플랫폼입니다. 스케줄러를 통해 주기적으로 데이터를 수집하며, 확장 가능한 구조를 통해 새로운 데이터 수집 모듈을 쉽게 추가할 수 있습니다.

## 주요 기능

- **주기적 데이터 수집**: 스케줄러를 사용하여 지정된 시간에 자동으로 데이터를 수집합니다.
- **다양한 데이터 소스 지원**: FinanceDataReader를 이용한 주식 데이터 수집을 기본으로 지원합니다.
- **확장 가능한 구조**: `BaseCollector`를 상속하여 새로운 데이터 수집기를 손쉽게 추가할 수 있습니다.
- **유연한 DB 지원**: SQLAlchemy를 통해 SQLite, MySQL, PostgreSQL 등 다양한 데이터베이스를 지원합니다.
- **동적 XLSX 파일 처리**: 지정된 폴더에 XLSX 파일을 추가하면, 자동으로 DB 테이블을 생성하고 데이터를 적재합니다.

## 설정 방법

1.  **데이터베이스 설정**:
    - `yolo/config/settings.py` 파일을 엽니다.
    - `DB_TYPE`을 "sqlite", "mysql", "postgresql" 중 하나로 설정합니다.
    - 사용하는 DB에 맞게 관련 설정(경로, 사용자 정보 등)을 수정합니다.

2.  **수집 대상 주식 설정**:
    - `yolo/config/watchlist.py` 파일을 엽니다.
    - `WATCHLIST` 리스트에 수집을 원하는 주식의 티커(ticker)를 추가하거나 제거합니다.

3.  **XLSX 파일 경로 설정** (XLSX 수집기 사용 시):
    - `yolo/config/settings.py` 파일에 `XLSX_WATCH_DIR` 변수를 추가하고 모니터링할 디렉토리 경로를 지정해야 합니다. (구현 예정)


## 실행 방법

### 1. 의존성 라이브러리 설치

프로젝트 루트 디렉토리에서 다음 명령어를 실행합니다.

```bash
pip install -r yolo/requirements.txt
```

### 2. 데이터베이스 초기화

(최초 실행 시) Python 인터프리터를 실행하여 다음 코드를 실행하면 `models.py`에 정의된 테이블이 생성됩니다.

```python
from yolo.src.database.connection import engine, Base
# from yolo.src.database import models # 모든 모델을 임포트해야 합니다.
Base.metadata.create_all(bind=engine)
```

### 3. 스케줄러 실행

주식 데이터의 주기적인 수집을 위해 스케줄러를 실행합니다.

```bash
python -m yolo.src.scheduler
```

스케줄러가 실행되면 `settings.py`에 설정된 간격마다 `watchlist.py`에 등록된 주식 정보를 자동으로 수집하여 DB에 저장합니다.

## 개발

새로운 데이터 수집기를 추가하려면 `yolo/src/collectors/base.py`의 `BaseCollector` 클래스를 상속받아 `collect`와 `save` 메소드를 구현하세요.
