import pytest
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yolo.src.database.models import Base, StockPrice
from yolo.src.collectors.stock_collector import StockCollector

# 테스트용 인메모리 SQLite 데이터베이스 설정
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

# FinanceDataReader.DataReader를 모의(mock)하기 위한 픽스처
@pytest.fixture
def mock_fdr(mocker):
    mock_data = {
        'Open': [1000, 1100],
        'High': [1200, 1300],
        'Low': [900, 1000],
        'Close': [1100, 1200],
        'Volume': [10000, 20000]
    }
    mock_df = pd.DataFrame(mock_data, index=pd.to_datetime(['2023-01-01', '2023-01-02']))
    return mocker.patch('FinanceDataReader.DataReader', return_value=mock_df)

def test_collect_data(db_session, mock_fdr):
    """데이터 수집 기능이 정상적으로 동작하는지 테스트합니다."""
    collector = StockCollector(db_session)
    df = collector.collect(ticker="005930", start_date="2023-01-01", end_date="2023-01-02")
    
    mock_fdr.assert_called_once_with("005930", "2023-01-01", "2023-01-02")
    assert df is not None
    assert len(df) == 2
    assert 'code' in df.columns
    assert df['code'].iloc[0] == "005930"

def test_save_data(db_session, mock_fdr):
    """수집된 데이터가 DB에 정상적으로 저장되는지 테스트합니다."""
    collector = StockCollector(db_session)
    df = collector.collect(ticker="005930", start_date="2023-01-01")
    
    # 수집된 데이터를 저장
    collector.save(df)
    
    # DB에서 저장된 데이터를 조회하여 확인
    saved_data = db_session.query(StockPrice).all()
    assert len(saved_data) == 2
    
    first_record = saved_data[0]
    assert first_record.code == "005930"
    assert first_record.date == datetime(2023, 1, 1)
    assert first_record.open == 1000
    assert first_record.close == 1100
    assert first_record.volume == 10000

def test_run_pipeline(db_session, mock_fdr):
    """전체 수집-저장 파이프라인이 정상적으로 동작하는지 테스트합니다."""
    collector = StockCollector(db_session)
    result = collector.run(ticker="005930", start_date="2023-01-01")

    assert result is True
    saved_data = db_session.query(StockPrice).all()
    assert len(saved_data) == 2
    assert saved_data[0].code == "005930"
