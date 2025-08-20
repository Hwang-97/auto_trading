import FinanceDataReader as fdr
from datetime import datetime
from sqlalchemy.orm import Session
from ..database.models import StockPrice
from .base import BaseCollector

class StockCollector(BaseCollector):
    """
    FinanceDataReader를 사용하여 주식 데이터를 수집하고 DB에 저장하는 클래스.
    """

    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def collect(self, ticker: str, start_date: str, end_date: str = None):
        """
        지정된 티커와 기간의 주식 데이터를 수집합니다.
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"Collecting stock data for {ticker} from {start_date} to {end_date}...")
        try:
            df = fdr.DataReader(ticker, start_date, end_date)
            if df.empty:
                print(f"No data found for {ticker}.")
                return None
            df['code'] = ticker
            # 컬럼명을 DB 모델에 맞게 변경
            df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }, inplace=True)
            df.reset_index(inplace=True)
            df.rename(columns={'Date': 'date'}, inplace=True)
            df.rename(columns={'Date': 'date'}, inplace=True)
            print(f"Successfully collected {len(df)} rows of data for {ticker}.")
            return df
        except Exception as e:
            print(f"Error collecting data for {ticker}: {e}")
            return None

    def save(self, data):
        """
        수집한 데이터프레임을 DB에 저장합니다.
        """
        print(f"Saving {len(data)} rows of stock data to the database...")
        try:
            for _, row in data.iterrows():
                stock_price = StockPrice(
                    code=row['code'],
                    date=row['date'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume']
                )
                self.db_session.add(stock_price)
            self.db_session.commit()
            print("Successfully saved data.")
        except Exception as e:
            print(f"Error saving data: {e}")
            self.db_session.rollback()
