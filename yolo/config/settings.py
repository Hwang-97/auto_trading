# yolo/config/settings.py

# 데이터베이스 설정
# 사용 가능한 DB 종류: "sqlite", "mysql", "postgresql"
# DB_TYPE에 따라 아래 설정을 변경하여 사용하세요.
DB_TYPE = "sqlite"

# SQLite 설정
SQLITE_DB_PATH = "yolo/data/stock_data.db"

# MySQL / PostgreSQL 설정 (예시)
# DB_USER = "your_user"
# DB_PASSWORD = "your_password"
# DB_HOST = "localhost"
# DB_PORT = "3306" # PostgreSQL은 5432
# DB_NAME = "stock_db"


def get_db_url():
    """
    설정에 맞는 데이터베이스 URL을 반환합니다.
    """
    if DB_TYPE == "sqlite":
        # SQLite의 경우, 프로젝트 루트를 기준으로 하는 상대 경로를 사용합니다.
        # 데이터베이스 파일은 yolo/data/stock_data.db 에 저장됩니다.
        return f"sqlite:///{SQLITE_DB_PATH}"
    elif DB_TYPE == "mysql":
        # pymysql 드라이버 사용 예시
        return f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    elif DB_TYPE == "postgresql":
        return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        raise ValueError(f"Unsupported DB_TYPE: {DB_TYPE}")

# 스케줄러 설정
SCHEDULER_INTERVAL_MINUTES = 60 # 기본 실행 간격 (분)

# XLSX 파일 감시 설정
# 이 경로에 .xlsx 파일을 추가하면 자동으로 DB에 저장됩니다.
XLSX_WATCH_DIR = "yolo/data/xlsx_files"
