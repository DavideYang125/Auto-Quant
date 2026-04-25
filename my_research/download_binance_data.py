"""
Binance 历史数据下载脚本

这个脚本会从 Binance 公开数据网站下载历史K线数据
不需要 API key，完全免费

使用方法：
    uv run download_binance_data.py
"""

import requests
import pandas as pd
from pathlib import Path
import zipfile
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import io

# 配置
OUTPUT_DIR = Path("user_data/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Binance 公开数据基础URL
BASE_URL = "https://data.binance.vision/data/spot/daily/klines"

# 需要下载的交易对和时间周期
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT"]
TIMEFRAMES = ["1h", "4h", "1d"]

# 日期范围
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2025, 4, 25)


def download_file(url: str, dest_path: Path) -> bool:
    """下载单个文件"""
    try:
        print(f"  下载: {dest_path.name}")
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        # 下载到临时文件
        temp_path = dest_path.with_suffix('.tmp')
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # 如果是zip文件，解压
        if url.endswith('.zip'):
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path.parent)

            # 删除zip文件
            temp_path.unlink()

            # 查找解压后的CSV文件
            csv_files = list(temp_path.parent.glob('*.csv'))
            if csv_files:
                # 读取CSV并转换为Feather
                df = pd.read_csv(csv_files[0], header=None)
                df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_volume', 'trades',
                            'taker_buy_base', 'taker_buy_quote', 'ignore']

                # 转换时间戳
                df['date'] = pd.to_datetime(df['open_time'], unit='ms')

                # 选择需要的列
                result = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
                result = result.sort_values('date').drop_duplicates()

                # 保存为Feather
                result.to_feather(dest_path)
                print(f"    [OK] 转换完成: {len(result)} 行")

                # 删除CSV文件
                for csv_file in csv_files:
                    csv_file.unlink()
                return True

        return False

    except Exception as e:
        print(f"    [FAIL] 失败: {e}")
        return False


def get_all_dates(start: datetime, end: datetime) -> list[str]:
    """生成日期列表"""
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return dates


def download_pair_timeframe(pair: str, timeframe: str) -> bool:
    """下载单个交易对的单个时间周期数据"""
    print(f"\n处理 {pair} {timeframe}:")

    # 输出文件名
    output_filename = f"{pair.replace('USDT', '_USDT')}-{timeframe}.feather"
    output_path = OUTPUT_DIR / output_filename

    # 检查是否已存在
    if output_path.exists():
        print(f"  跳过（已存在）: {output_filename}")
        return True

    # 获取所有日期
    dates = get_all_dates(START_DATE, END_DATE)

    # 收集所有数据
    all_data = []
    success_count = 0

    for date_str in dates:
        # 构建URL: https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2023-01-01.zip
        url = f"{BASE_URL}/{pair}/{timeframe}/{pair}-{timeframe}-{date_str}.zip"

        try:
            # 下载并解压单个文件
            response = requests.get(url, timeout=30, stream=True)

            if response.status_code == 200:
                # 读取zip内容
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    for file_name in zip_ref.namelist():
                        if file_name.endswith('.csv'):
                            # 读取CSV
                            csv_data = zip_ref.read(file_name)
                            df = pd.read_csv(io.StringIO(csv_data.decode('utf-8')), header=None)
                            df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume',
                                        'close_time', 'quote_volume', 'trades',
                                        'taker_buy_base', 'taker_buy_quote', 'ignore']

                            # 转换时间戳
                            df['date'] = pd.to_datetime(df['open_time'], unit='ms')
                            result = df[['date', 'open', 'high', 'low', 'close', 'volume']]
                            all_data.append(result)
                            success_count += 1

                # 每下载10个文件显示一次进度
                if success_count % 10 == 0:
                    print(f"    进度: {success_count}/{len(dates)} 文件")

        except Exception as e:
            # 某些日期可能没有数据，跳过
            continue

    # 合并所有数据
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.sort_values('date').drop_duplicates()

        # 保存为Feather
        combined.to_feather(output_path)
        print(f"  [OK] 完成: {output_filename} ({len(combined)} 行, {success_count} 个文件)")
        return True
    else:
        print(f"  [FAIL] 失败: 没有下载到数据")
        return False


def main():
    print("=" * 60)
    print("Binance 历史数据下载工具")
    print("=" * 60)
    print(f"\n目标交易对: {', '.join(PAIRS)}")
    print(f"时间周期: {', '.join(TIMEFRAMES)}")
    print(f"日期范围: {START_DATE.date()} 到 {END_DATE.date()}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("\n开始下载...\n")

    # 测试网络连接
    try:
        response = requests.get("https://data.binance.vision/", timeout=10)
        print("[OK] 网络连接正常\n")
    except Exception as e:
        print(f"[ERROR] 网络连接失败: {e}")
        print("\n请检查:")
        print("  1. 是否可以访问 https://data.binance.vision/")
        print("  2. 是否需要配置代理")
        return

    total_tasks = len(PAIRS) * len(TIMEFRAMES)
    completed = 0

    for pair in PAIRS:
        for tf in TIMEFRAMES:
            if download_pair_timeframe(pair, tf):
                completed += 1

    print("\n" + "=" * 60)
    print(f"下载完成: {completed}/{total_tasks}")
    print("=" * 60)

    if completed == total_tasks:
        print("\n[SUCCESS] 所有数据下载完成！现在可以运行回测了")
        print("  运行: uv run simple_backtest.py")
    else:
        print(f"\n[WARNING] 部分数据下载失败 ({total_tasks - completed} 个失败)")
        print("  可以重新运行脚本继续下载")


if __name__ == "__main__":
    main()
