# yolo/src/scheduler.py

import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from .database.connection import get_db
from .collectors.stock_collector import StockCollector
from yolo.config.watchlist import WATCHLIST
from yolo.config.settings import SCHEDULER_INTERVAL_MINUTES

def job_collect_stock_data():
    """
    WATCHLIST에 있는 모든 주식에 대해 최근 데이터를 수집하는 스케줄링 작업
    """
    print(f"[{datetime.now()}] Starting scheduled job: collect_stock_data")
    db_session_gen = get_db()
    db_session = next(db_session_gen)
    
    try:
        collector = StockCollector(db_session)
        
        # 데이터 수집 기간 설정 (예: 최근 3일)
        # 이미 데이터가 있는 경우 중복 수집을 방지하기 위함
        start_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        for ticker in WATCHLIST:
            print(f"Running collector for {ticker}...")
            collector.run(ticker=ticker, start_date=start_date)
            
    except Exception as e:
        print(f"An error occurred during the scheduled job: {e}")
    finally:
        print(f"[{datetime.now()}] Finished scheduled job: collect_stock_data")
        db_session.close()

class Scheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='Asia/Seoul')
        self.scheduler.add_job(
            job_collect_stock_data,
            'interval',
            minutes=SCHEDULER_INTERVAL_MINUTES,
            id="collect_stock_data_job"
        )

    def start(self):
        """
        스케줄러를 시작합니다.
        """
        print("Starting scheduler...")
        self.scheduler.start()
        print(f"Scheduler started. Job 'collect_stock_data_job' will run every {SCHEDULER_INTERVAL_MINUTES} minutes.")

    def stop(self):
        """
        스케줄러를 중지합니다.
        """
        print("Stopping scheduler...")
        self.scheduler.shutdown()
        print("Scheduler stopped.")

def main():
    """
    스케줄러를 실행하는 메인 함수.
    이 파일을 직접 실행하면 스케줄러가 시작됩니다.
    """
    scheduler = Scheduler()
    scheduler.start()
    
    # 스케줄러가 백그라운드에서 실행되도록 메인 스레드를 유지
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()

if __name__ == "__main__":
    main()
