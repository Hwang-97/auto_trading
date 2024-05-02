import mysql.connector
from mysql.connector import errorcode
import logging

def create_db_connection(host_name, user_name, user_password, db_name, db_port):
    """ 데이터베이스 연결 생성 """
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name,
            port=db_port
        )
        logging.info("MySQL 데이터베이스 연결 성공")
        return connection
    except mysql.connector.Error as err:
        logging.error(f"연결 오류: {err}")
        return None

def execute_query(connection, query, params=None):
    """ 매개변수화된 쿼리 실행 """
    cursor = connection.cursor()
    try:
        cursor.execute(query, params)
        connection.commit()
        logging.info("쿼리 실행 성공")
    except mysql.connector.Error as err:
        logging.error(f"쿼리 실행 오류: {err}")

def read_query(connection, query, params=None):
    """ 데이터 선택 쿼리 실행 """
    cursor = connection.cursor()
    try:
        cursor.execute(query, params)
        result = cursor.fetchall()
        logging.info("데이터 읽기 성공")
        return result
    except mysql.connector.Error as err:
        logging.error(f"데이터 읽기 오류: {err}")
        return None
