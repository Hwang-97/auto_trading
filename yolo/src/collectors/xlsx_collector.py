# yolo/src/collectors/xlsx_collector.py

import os
import time
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from sqlalchemy import (Table, Column, Integer, String, Float, DateTime, MetaData, inspect)
from sqlalchemy.exc import SQLAlchemyError
from ..database.connection import engine, SessionLocal
from yolo.config.settings import XLSX_WATCH_DIR

def pandas_type_to_sqlalchemy_type(dtype):
    """Pandas 데이터 타입을 SQLAlchemy 타입으로 변환합니다."""
    if "int" in str(dtype):
        return Integer
    elif "float" in str(dtype):
        return Float
    elif "datetime" in str(dtype):
        return DateTime
    else:
        return String

def create_dynamic_table(table_name, df, metadata):
    """데이터프레임 정보를 기반으로 동적으로 SQLAlchemy 테이블 객체를 생성합니다."""
    columns = [Column('id', Integer, primary_key=True, autoincrement=True)]
    for column_name, dtype in df.dtypes.items():
        # 유효한 컬럼명으로 변환 (공백, 특수문자 처리)
        safe_column_name = ''.join(e for e in column_name if e.isalnum() or e == '_')
        columns.append(Column(safe_column_name, pandas_type_to_sqlalchemy_type(dtype)))
    
    # 이미 메모리에 테이블이 정의되어 있다면 제거
    if table_name in metadata.tables:
        metadata.remove(metadata.tables[table_name])
        
    table = Table(table_name, metadata, *columns)
    return table

class XLSXFileHandler(FileSystemEventHandler):
    """XLSX 파일 생성 이벤트를 감지하고 처리하는 핸들러"""

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.xlsx'):
            print(f"New XLSX file detected: {event.src_path}")
            self.process_xlsx(event.src_path)

    def process_xlsx(self, file_path):
        """XLSX 파일을 읽어 DB에 저장합니다."""
        try:
            # 파일이 완전히 쓰여질 때까지 잠시 대기
            time.sleep(1)
            
            df = pd.read_excel(file_path)
            if df.empty:
                print(f"File is empty: {file_path}")
                return

            # 파일명을 기반으로 테이블명 생성 (확장자 제외, 유효한 이름으로 변환)
            table_name = os.path.basename(file_path).replace('.xlsx', '')
            table_name = f"xlsx_{''.join(e for e in table_name if e.isalnum() or e == '_')}"
            
            print(f"Processing data for table: {table_name}")

            db_session = SessionLocal()
            try:
                inspector = inspect(engine)
                metadata = MetaData()
                
                if not inspector.has_table(table_name):
                    print(f"Table '{table_name}' not found. Creating new table.")
                    dynamic_table = create_dynamic_table(table_name, df, metadata)
                    metadata.create_all(engine, tables=[dynamic_table])
                    print(f"Table '{table_name}' created successfully.")
                else:
                    print(f"Table '{table_name}' already exists. Appending data.")
                    metadata.reflect(bind=engine)

                # 데이터를 DB에 삽입
                # 컬럼명을 DB에 맞게 안전한 이름으로 변경
                df.columns = [''.join(e for e in col if e.isalnum() or e == '_') for col in df.columns]
                df.to_sql(table_name, con=engine, if_exists='append', index=False)
                
                print(f"Successfully saved data from {file_path} to table {table_name}.")

            except SQLAlchemyError as e:
                print(f"Database error: {e}")
                db_session.rollback()
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
            finally:
                db_session.close()

        except Exception as e:
            print(f"Error reading file {file_path}: {e}")


class XLSXCollector:
    """지정된 디렉토리를 모니터링하여 XLSX 파일을 처리하는 클래스"""

    def __init__(self, watch_dir=XLSX_WATCH_DIR):
        self.observer = Observer()
        self.watch_dir = watch_dir

    def start(self):
        """파일 시스템 모니터링을 시작합니다."""
        if not os.path.exists(self.watch_dir):
            print(f"Watch directory not found: {self.watch_dir}. Creating it.")
            os.makedirs(self.watch_dir)
            
        event_handler = XLSXFileHandler()
        self.observer.schedule(event_handler, self.watch_dir, recursive=False)
        self.observer.start()
        print(f"Started monitoring directory: {self.watch_dir}")
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """파일 시스템 모니터링을 중지합니다."""
        self.observer.stop()
        self.observer.join()
        print("Stopped monitoring.")

if __name__ == '__main__':
    collector = XLSXCollector()
    collector.start()
