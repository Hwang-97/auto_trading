from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

class BaseCollector(ABC):
    """
    모든 데이터 수집기의 기본이 되는 추상 클래스입니다.
    """

    def __init__(self, db_session: Session):
        """
        데이터베이스 세션을 인자로 받아 초기화합니다.
        """
        self.db_session = db_session

    @abstractmethod
    def collect(self, *args, **kwargs):
        """
        데이터를 수집하는 메소드입니다.
        하위 클래스에서 반드시 구현해야 합니다.
        """
        pass

    @abstractmethod
    def save(self, data):
        """
        수집한 데이터를 데이터베이스에 저장하는 메소드입니다.
        하위 클래스에서 반드시 구현해야 합니다.
        """
        pass

    def run(self, *args, **kwargs):
        """
        데이터 수집 및 저장 파이프라인을 실행합니다.
        """
        collected_data = self.collect(*args, **kwargs)
        if collected_data is not None and not collected_data.empty:
            self.save(collected_data)
            return True
        return False
