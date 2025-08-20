import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 테스트용 인메모리 SQLite 데이터베이스 사용
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="module")
def test_engine():
    """테스트용 데이터베이스 엔진을 생성합니다."""
    return create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})

@pytest.fixture(scope="module")
def test_session_local(test_engine):
    """테스트용 데이터베이스 세션 클래스를 생성합니다."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def test_database_connection(test_session_local):
    """데이터베이스 연결 및 세션 생성이 정상적으로 이루어지는지 테스트합니다."""
    db = test_session_local()
    assert db is not None
    try:
        # 간단한 쿼리를 실행하여 연결을 확인합니다.
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1
        print("Database connection successful.")
    finally:
        db.close()

if __name__ == "__main__":
    pytest.main()
