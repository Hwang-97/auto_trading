import os
import streamlit as st
import pandas as pd
from datetime import datetime
import pyupbit
import db_utils
from dotenv import load_dotenv

def load_data():
    # 환경 변수 로드
    load_dotenv()

    # 환경 변수 설정
    db_host = os.getenv('DB_HOST')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')
    db_port = os.getenv('DB_PORT')

    # 데이터베이스 연결
    connection = db_utils.create_db_connection(db_host, db_user, db_password, db_name, db_port)

    # 데이터 선택
    select_query = "SELECT timestamp, decision, percentage, reason, coin_balance, krw_balance, coin_avg_buy_price, coin_krw_price, coin_name FROM decisions ORDER BY timestamp"
    results = db_utils.read_query(connection, select_query)
    if results:
        df = pd.DataFrame(results, columns=['timestamp', 'decision', 'percentage', 'reason', 'coin_balance', 'krw_balance', 'coin_avg_buy_price', 'coin_krw_price', 'coin_name'])
        return df

def main():
    st.set_page_config(layout="wide")
    st.title("실시간 자동매매 기록")
    st.write("---")
    df = load_data()
    if df is not None and not df.empty:  # df가 None이 아니고 비어있지 않은 경우에만 실행
        start_value = 1000000
        current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]
        latest_row = df.iloc[-1]
        coin_balance = latest_row['coin_balance']
        krw_balance = latest_row['krw_balance']
        coin_avg_buy_price = latest_row['coin_avg_buy_price']
        current_value = int(coin_balance * current_price + krw_balance)
        coin_name=latest_row["coin_name"]

        time_diff = datetime.now() - pd.to_datetime(latest_row['timestamp'])
        days = time_diff.days
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60

        st.header("수익률:"+str(round((current_value-start_value)/start_value*100, 2))+"%")
        st.write("현재 시각:"+str(datetime.now()))
        st.write("투자기간:", days, "일", hours, "시간", minutes, "분")
        st.write("시작 원금", start_value, "원")
        st.write("코인종류", coin_name)
        st.write("현재 코인 가격:", current_price, "원")
        st.write("현재 보유 현금:", krw_balance, "원")
        st.write("현재 보유 코인:", coin_balance, "BTC")
        st.write("매수 평균가격:", coin_avg_buy_price, "원")
        st.write("현재 원화 가치 평가:", current_value, "원")

        st.dataframe(df, use_container_width=True)
    else:
        st.write("데이터를 불러올 수 없습니다.")

if __name__ == '__main__':
    main()
