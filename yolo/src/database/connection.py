from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from yolo.config.settings import get_db_url

# 설정 파일로부터 데이터베이스 URL을 가져옵니다.
DB_URL = get_db_url()

# 데이터베이스 엔진 생성
# SQLite 외의 DB를 사용할 경우 connect_args는 필요 없을 수 있습니다.
engine_args = {}
if DB_URL.startswith("sqlite"):
    engine_args['connect_args'] = {"check_same_thread": False}

engine = create_engine(DB_URL, **engine_args)

# 데이터베이스 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모든 모델 클래스가 상속받을 기본 클래스
Base = declarative_base()

def get_db():
    """
    데이터베이스 세션을 반환하는 함수
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
