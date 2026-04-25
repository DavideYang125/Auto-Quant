"""
Download 2025 data using Binance API (no auth required for public data)
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def fetch_klines(symbol, interval, start_ts, limit=1000):
    """Fetch klines from Binance API"""
    url = 'https://api.binance.com/api/v3/klines'

    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': start_ts,
        'limit': limit
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data, columns=[
                    'date', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades',
                    'taker_buy_base', 'taker_buy_quote', 'ignore'
                ])
                df['date'] = pd.to_datetime(df['date'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                return df
        return None
    except Exception as e:
        print(f'Error fetching: {e}')
        return None

def download_2025_api():
    """Download 2025 data using API"""
    symbols = ['BTCUSDT', 'ETHUSDT']

    # 2025年1月1日的时间戳
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 4, 30)

    for symbol in symbols:
        print(f'\n=== {symbol} ===')

        all_data = []
        current_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)

        while current_ts < end_ts:
            df = fetch_klines(symbol, '1h', current_ts, limit=1000)

            if df is not None and len(df) > 0:
                all_data.append(df)
                print(f'Fetched {len(df)} candles from {df["date"].min()}', end='\r')

                # Move to next batch
                last_ts = int(df['date'].max().timestamp() * 1000) + 3600000
                if last_ts <= current_ts:
                    break
                current_ts = last_ts

                time.sleep(0.5)  # Rate limiting
            else:
                print(f'No data at timestamp {current_ts}')
                break

        if all_data:
            # Combine all data
            combined = pd.concat(all_data, ignore_index=True)
            combined = combined.sort_values('date').reset_index(drop=True)

            # Select needed columns
            result = combined[['date', 'open', 'high', 'low', 'close', 'volume']].copy()

            # Convert pair name format
            pair_formatted = symbol.replace('USDT', '_USDT')

            # Save to feather
            output_path = f'user_data/data/{pair_formatted}-1h-2025.feather'
            result.to_feather(output_path)

            print(f'\n\nSaved: {output_path}')
            print(f'  Total rows: {len(result)}')
            print(f'  Date range: {result["date"].min()} to {result["date"].max()}')

            # Calculate return
            start_price = result.iloc[0]['close']
            end_price = result.iloc[-1]['close']
            ret = (end_price / start_price - 1) * 100
            print(f'  YTD 2025 return: {ret:+.2f}%')
        else:
            print('\nNo data downloaded')

if __name__ == '__main__':
    download_2025_api()
