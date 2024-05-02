import os
from dotenv import load_dotenv
import pyupbit
import pandas as pd
import pandas_ta as ta
import json
from openai import OpenAI
import schedule
import time
import requests
from datetime import datetime
import logging
import db_utils

# 환경 변수 로드
load_dotenv()

# Setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
upbit = pyupbit.Upbit(os.getenv("UPBIT_ACCESS_KEY"), os.getenv("UPBIT_SECRET_KEY"))
db_host = os.getenv('DB_HOST')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')
db_port = os.getenv('DB_PORT')

# 데이터베이스 연결
connection = db_utils.create_db_connection(db_host, db_user, db_password, db_name, db_port)

def initialize_db():
    # 테이블 생성
    create_table_query = """
    CREATE TABLE IF NOT EXISTS decisions (
        id BIGINT AUTO_INCREMENT NOT NULL PRIMARY KEY COMMENT 'pk',
        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '작성',
        decision TEXT NOT NULL COMMENT '[0:hold, 1:buy, 2:sell] action',
        percentage DOUBLE NOT NULL DEFAULT 0 COMMENT '코인 비율 (코인/현금)',
        reason TEXT NOT NULL COMMENT '매매 판단 기준',
        coin_name TEXT NOT NULL COMMENT 'coin이름 ex)BTC',
        coin_balance DOUBLE NOT NULL DEFAULT 0 COMMENT '가지고 있는 코인 개수',
        krw_balance DOUBLE NOT NULL DEFAULT 0 COMMENT '가지고 있는 현금',
        coin_avg_buy_price DOUBLE NOT NULL DEFAULT 0 COMMENT '가지고 있는 코인의 평균 구매가',
        coin_krw_price DOUBLE NOT NULL DEFAULT 0 COMMENT '가지고 있는 총 금액(coin의 총 가격 + 가지고 있는 현금)'
    );
    """
    db_utils.execute_query(connection, create_table_query)

def save_decision_to_db(decision, current_status):
    try:
        with connection.cursor() as cursor:
            # Parsing current_status from JSON to Python dict
            status_dict = json.loads(current_status)
            
            # Get the current price of the coin
            current_price = pyupbit.get_current_price("KRW-BTC")  # 이 부분을 수정해야 합니다. 코인 이름에 따라 변경해야 할 수 있습니다.
            
            # Preparing data for insertion
            data_to_insert = (
                decision.get('decision'),
                decision.get('percentage', 100),  # Defaulting to 100 if not provided
                decision.get('reason', ''),  # Defaulting to an empty string if not provided
                'KRW-BTC',  # 코인 이름 추가
                status_dict.get('btc_balance'),
                status_dict.get('krw_balance'),
                status_dict.get('btc_avg_buy_price'),
                current_price  # 코인의 현재 가격 추가
            )
            
            print(data_to_insert)
            # Inserting data into the database
            sql = """
                INSERT INTO decisions (timestamp, decision, percentage, reason, coin_name, coin_balance, krw_balance, coin_avg_buy_price, coin_krw_price)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, data_to_insert)
        
        # Commit the transaction
        connection.commit()
        
    except Exception as e:
        print(f"Failed to save decision to DB: {e}")


    

def fetch_last_decisions(num_decisions=10):
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT timestamp, decision, percentage, reason, coin_balance, krw_balance, coin_avg_buy_price FROM decisions
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cursor.execute(sql, (num_decisions,))
            decisions = cursor.fetchall()

            if decisions:
                formatted_decisions = []
                for decision in decisions:
                    # Converting timestamp to milliseconds since the Unix epoch
                    ts = decision[0].timestamp() * 1000
                    formatted_decision = {
                        "timestamp": int(ts),
                        "decision": decision[1],
                        "percentage": decision[2],
                        "reason": decision[3],
                        "btc_balance": decision[4],  # 수정된 부분
                        "krw_balance": decision[5],
                        "btc_avg_buy_price": decision[6]
                    }
                    formatted_decisions.append(str(formatted_decision))
                return "\n".join(formatted_decisions)
            else:
                return "No decisions found."
    except Exception as e:
        print(f"Failed to fetch last decisions: {e}")



def get_current_status():
    orderbook = pyupbit.get_orderbook(ticker="KRW-BTC")
    current_time = orderbook['timestamp']
    btc_balance = 0
    krw_balance = 0
    btc_avg_buy_price = 0
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == "BTC":
            btc_balance = b['balance']
            btc_avg_buy_price = b['avg_buy_price']
        if b['currency'] == "KRW":
            krw_balance = b['balance']

    current_status = {'current_time': current_time, 'orderbook': orderbook, 'btc_balance': btc_balance, 'krw_balance': krw_balance, 'btc_avg_buy_price': btc_avg_buy_price}
    return json.dumps(current_status)


def fetch_and_prepare_data():
    # Fetch data
    df_daily = pyupbit.get_ohlcv("KRW-BTC", "day", count=30)
    df_hourly = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=24)

    # Define a helper function to add indicators
    def add_indicators(df):
        # Moving Averages
        df['SMA_10'] = ta.sma(df['close'], length=10)
        df['EMA_10'] = ta.ema(df['close'], length=10)

        # RSI
        df['RSI_14'] = ta.rsi(df['close'], length=14)

        # Stochastic Oscillator
        stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3, smooth_k=3)
        df = df.join(stoch)

        # MACD
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_fast - ema_slow
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']

        # Bollinger Bands
        df['Middle_Band'] = df['close'].rolling(window=20).mean()
        # Calculate the standard deviation of closing prices over the last 20 days
        std_dev = df['close'].rolling(window=20).std()
        # Calculate the upper band (Middle Band + 2 * Standard Deviation)
        df['Upper_Band'] = df['Middle_Band'] + (std_dev * 2)
        # Calculate the lower band (Middle Band - 2 * Standard Deviation)
        df['Lower_Band'] = df['Middle_Band'] - (std_dev * 2)

        return df

    # Add indicators to both dataframes
    df_daily = add_indicators(df_daily)
    df_hourly = add_indicators(df_hourly)

    combined_df = pd.concat([df_daily, df_hourly], keys=['daily', 'hourly'])
    combined_data = combined_df.to_json(orient='split')

    return json.dumps(combined_data)

def get_news_data():
    ### Get news data from SERPAPI
    url = "https://serpapi.com/search.json?engine=google_news&q=btc&api_key=" + os.getenv("SERPAPI_API_KEY")

    result = "No news data available."

    try:
        response = requests.get(url)
        news_results = response.json()['news_results']

        simplified_news = []
        
        for news_item in news_results:
            # Check if this news item contains 'stories'
            if 'stories' in news_item:
                for story in news_item['stories']:
                    timestamp = int(datetime.strptime(story['date'], '%m/%d/%Y, %H:%M %p, %z %Z').timestamp() * 1000)
                    simplified_news.append((story['title'], story.get('source', {}).get('name', 'Unknown source'), timestamp))
            else:
                # Process news items that are not categorized under stories but check date first
                if news_item.get('date'):
                    timestamp = int(datetime.strptime(news_item['date'], '%m/%d/%Y, %H:%M %p, %z %Z').timestamp() * 1000)
                    simplified_news.append((news_item['title'], news_item.get('source', {}).get('name', 'Unknown source'), timestamp))
                else:
                    simplified_news.append((news_item['title'], news_item.get('source', {}).get('name', 'Unknown source'), 'No timestamp provided'))
        result = str(simplified_news)
    except Exception as e:
        print(f"Error fetching news data: {e}")

    return result

def fetch_fear_and_greed_index(limit=1, date_format=''):
    """
    Fetches the latest Fear and Greed Index data.
    Parameters:
    - limit (int): Number of results to return. Default is 1.
    - date_format (str): Date format ('us', 'cn', 'kr', 'world'). Default is '' (unixtime).
    Returns:
    - dict or str: The Fear and Greed Index data in the specified format.
    """
    base_url = "https://api.alternative.me/fng/"
    params = {
        'limit': limit,
        'format': 'json',
        'date_format': date_format
    }
    response = requests.get(base_url, params=params)
    myData = response.json()['data']
    resStr = ""
    for data in myData:
        resStr += str(data)
    return resStr

def get_instructions(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            instructions = file.read()
        return instructions
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print("An error occurred while reading the file:", e)

def analyze_data_with_gpt4(news_data, data_json, last_decisions, fear_and_greed, current_status):
    instructions_path = "instructions.md"
    try:
        instructions = get_instructions(instructions_path)
        if not instructions:
            print("No instructions found.")
            return None
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": news_data},
                {"role": "user", "content": data_json},
                {"role": "user", "content": last_decisions},
                {"role": "user", "content": fear_and_greed},
                {"role": "user", "content": current_status}
            ],
            response_format={"type":"json_object"}
        )
        advice = response.choices[0].message.content
        return advice
    except Exception as e:
        print(f"Error in analyzing data with GPT-4: {e}")
        return None

def execute_buy(percentage):
    print("Attempting to buy BTC with a percentage of KRW balance...")
    try:
        krw_balance = upbit.get_balance("KRW")
        amount_to_invest = krw_balance * (percentage / 100)
        if amount_to_invest > 5000:  # Ensure the order is above the minimum threshold
            result = upbit.buy_market_order("KRW-BTC", amount_to_invest * 0.9995)  # Adjust for fees
            print("Buy order successful:", result)
    except Exception as e:
        print(f"Failed to execute buy order: {e}")

def execute_sell(percentage):
    print("Attempting to sell a percentage of BTC...")
    try:
        btc_balance = upbit.get_balance("BTC")
        amount_to_sell = btc_balance * (percentage / 100)
        current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]
        if current_price * amount_to_sell > 5000:  # Ensure the order is above the minimum threshold
            result = upbit.sell_market_order("KRW-BTC", amount_to_sell)
            print("Sell order successful:", result)
    except Exception as e:
        print(f"Failed to execute sell order: {e}")

def make_decision_and_execute():
    print("Making decision and executing...")
    try:
        news_data = get_news_data()
        data_json = fetch_and_prepare_data()
        last_decisions = fetch_last_decisions()
        fear_and_greed = fetch_fear_and_greed_index(limit=30)
        current_status = get_current_status()
        
        # Ensure last_decisions is in string format
        last_decisions_str = last_decisions if isinstance(last_decisions, str) else str(last_decisions)
        
        max_retries = 5
        retry_delay_seconds = 5
        decision = None
        for attempt in range(max_retries):
            try:
                advice = analyze_data_with_gpt4(news_data, data_json, last_decisions_str, fear_and_greed, current_status)
                decision = json.loads(advice)
                break
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed: {e}. Retrying in {retry_delay_seconds} seconds...")
                time.sleep(retry_delay_seconds)
                print(f"Attempt {attempt + 2} of {max_retries}")
        if not decision:
            print("Failed to make a decision after maximum retries.")
            return
        else:
            try:
                percentage = decision.get('percentage', 100)

                if decision.get('decision') == "buy":
                    execute_buy(percentage)
                elif decision.get('decision') == "sell":
                    execute_sell(percentage)
                
                save_decision_to_db(decision, current_status)
            except Exception as e:
                print(f"Failed to execute the decision or save to DB: {e}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    initialize_db()
    
    #testing
    schedule.every().minute.do(make_decision_and_execute)

    # # Schedule the task to run at 00:01
    # schedule.every().day.at("00:01").do(make_decision_and_execute)

    # # Schedule the task to run at 08:01
    # schedule.every().day.at("08:01").do(make_decision_and_execute)

    # # Schedule the task to run at 16:01
    # schedule.every().day.at("16:01").do(make_decision_and_execute)

    while True:
        schedule.run_pending()
        time.sleep(1)