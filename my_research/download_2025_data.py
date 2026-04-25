"""
Download 2025 data from Binance (daily files)
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import os

def download_day(pair, interval, date_str):
    """Download one day of data"""
    url = f'https://data.binance.vision/data/spot/daily/klines/{pair}/{interval}/{pair}-{interval}-{date_str}.zip'

    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return None

        # Extract from ZIP in memory
        import zipfile
        import io

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith('.csv'):
                    with zip_ref.open(file) as csv_file:
                        df = pd.read_csv(csv_file, header=None)
                        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume',
                                     'close_time', 'quote_volume', 'trades',
                                     'taker_buy_base', 'taker_buy_quote', 'ignore']
                        df['date'] = pd.to_datetime(df['date'], unit='ms')
                        return df

        return None

    except Exception as e:
        return None

def download_2025_data():
    """Download 2025 data (Jan to Apr)"""
    pairs = ['BTCUSDT', 'ETHUSDT']

    # 2025年1-4月
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 4, 30)

    for pair in pairs:
        print(f'\n=== {pair} ===')
        all_data = []
        current = start_date

        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            df = download_day(pair, '1h', date_str)

            if df is not None:
                all_data.append(df)
                print(f'{date_str}: OK', end='\r')

            current += timedelta(days=1)

        if all_data:
            # Combine all data
            combined = pd.concat(all_data, ignore_index=True)
            combined = combined.sort_values('date').reset_index(drop=True)

            # Convert pair name format
            pair_formatted = pair.replace('USDT', '_USDT')

            # Save to feather
            output_path = f'user_data/data/{pair_formatted}-1h-2025.feather'
            combined.to_feather(output_path)

            print(f'\n\nSaved: {output_path}')
            print(f'  Total rows: {len(combined)}')
            print(f'  Date range: {combined["date"].min()} to {combined["date"].max()}')

            # Calculate return
            start_price = combined.iloc[0]['close']
            end_price = combined.iloc[-1]['close']
            ret = (end_price / start_price - 1) * 100
            print(f'  YTD 2025 return: {ret:+.2f}%')

if __name__ == '__main__':
    download_2025_data()
