from sqlalchemy import Column, Integer, String, Float, DateTime
from .connection import Base

# 예시: 주식 가격 정보 모델
class StockPrice(Base):
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, index=True)
    date = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)

# 앞으로 생성될 모든 DB 모델(테이블)은 이 파일에 정의하거나
# 이 파일에서 import 하여 Base를 상속받아 생성합니다.
