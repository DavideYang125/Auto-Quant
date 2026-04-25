"""
将币安下载的 CSV 数据转换为 Feather 格式

使用方法：
1. 从 https://data.binance.vision/data/spot/daily/klines/ 下载数据
2. 将下载的 zip 文件解压到某个目录，如: downloads/BTCUSDT/1h/
3. 运行此脚本转换数据
"""
import pandas as pd
from pathlib import Path
import glob

# 配置
DOWNLOADS_DIR = Path("downloads")  # 修改为你的下载目录
OUTPUT_DIR = Path("user_data/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 需要的交易对和时间周期
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT"]
TIMEFRAMES = ["1h", "4h", "1d"]

def convert_binance_csv_to_feather(pair, timeframe):
    """转换单个交易对和时间周期的数据"""
    # 币安 CSV 列名
    columns = [
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ]

    # 查找所有 CSV 文件
    pattern = f"{DOWNLOADS_DIR}/{pair}/{timeframe}/*.csv"
    files = glob.glob(pattern)

    if not files:
        print(f"  ⚠ 未找到 {pair} {timeframe} 的数据文件")
        return False

    # 读取并合并所有文件
    dfs = []
    for file in sorted(files):
        try:
            df = pd.read_csv(file, header=None, names=columns)
            dfs.append(df)
        except Exception as e:
            print(f"  ⚠ 读取文件失败: {file} - {e}")

    if not dfs:
        return False

    # 合并数据
    combined = pd.concat(dfs, ignore_index=True)

    # 转换时间戳
    combined['date'] = pd.to_datetime(combined['open_time'], unit='ms')

    # 选择需要的列并重命名
    result = combined[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
    result = result.sort_values('date').drop_duplicates()

    # 保存为 Feather
    output_file = OUTPUT_DIR / f"{pair.replace('USDT', '_USDT')}-{timeframe}.feather"
    result.reset_index(drop=True).to_feather(output_file)

    print(f"  ✓ 转换完成: {output_file.name} ({len(result)} 行)")
    return True

def main():
    print("=" * 60)
    print("币安数据转换工具")
    print("=" * 60)
    print(f"\n下载目录: {DOWNLOADS_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"交易对: {', '.join(PAIRS)}")
    print(f"时间周期: {', '.join(TIMEFRAMES)}")
    print()

    if not DOWNLOADS_DIR.exists():
        print(f"❌ 下载目录不存在: {DOWNLOADS_DIR}")
        print(f"\n请先创建目录并下载数据：")
        print(f"  1. 创建目录: mkdir -p {DOWNLOADS_DIR}/BTCUSDT/1h")
        print(f"  2. 从 https://data.binance.vision/ 下载")
        print(f"  3. 解压到对应目录")
        return

    success_count = 0
    total_count = len(PAIRS) * len(TIMEFRAMES)

    for pair in PAIRS:
        print(f"\n处理 {pair}:")
        for tf in TIMEFRAMES:
            if convert_binance_csv_to_feather(pair, tf):
                success_count += 1

    print("\n" + "=" * 60)
    print(f"转换完成: {success_count}/{total_count} 个文件")
    print("=" * 60)

if __name__ == "__main__":
    main()
