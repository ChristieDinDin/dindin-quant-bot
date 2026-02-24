import pandas as pd
import sqlite3
import os

# 1. 設定要匯入的股票代號與檔案
csv_files = [
    {'symbol': '2337', 'file': '2337.TW_history.csv'},
    {'symbol': '6944', 'file': '6944.TW_history.csv'}
]

# 2. 連接資料庫
conn = sqlite3.connect('market_data.db')

print("🚀 開始搬運物資...\n")

for item in csv_files:
    symbol = item['symbol']
    filename = item['file']
    
    # 檢查檔案是否存在
    if not os.path.exists(filename):
        print(f"❌ 找不到 {filename}，跳過！")
        continue

    try:
        # A. 讀取 CSV (重要：index_col=0 表示第一欄是日期索引)
        df = pd.read_csv(filename, index_col=0, parse_dates=True)
        
        # B. 把 Date 從 index 變成 column
        df = df.reset_index()
        
        # C. 統一欄位名稱為小寫
        df.columns = [c.lower() for c in df.columns]
        
        # D. 如果 yfinance 下載的檔案有多層 header，清理掉
        # 例如：('Close', '2337.TW') -> 'close'
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]
        
        # E. 補上股票代號
        df['symbol'] = symbol
        
        # F. 只保留需要的欄位
        required_cols = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        
        # 檢查欄位是否齊全
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"⚠️  {symbol} 缺少欄位: {missing_cols}")
            print(f"   實際欄位: {df.columns.tolist()}")
            continue
        
        df = df[required_cols]
        
        # G. 清理髒數據
        df = df.dropna()  # 移除有空值的行
        
        # H. 寫入資料庫
        df.to_sql('daily_kline', conn, if_exists='append', index=False)
        print(f"✅ {symbol} ({filename}) 搬運成功！共 {len(df)} 筆資料。")
        
    except Exception as e:
        print(f"💀 {symbol} 搬運失敗：{e}")
        print(f"   請檢查 {filename} 的格式是否正確\n")

# 3. 驗證匯入結果
cursor = conn.cursor()
cursor.execute("SELECT symbol, COUNT(*) as count FROM daily_kline GROUP BY symbol")
results = cursor.fetchall()

print("\n" + "="*50)
print("📊 資料庫內容統計:")
for row in results:
    print(f"   {row[0]}: {row[1]} 筆")
print("="*50)

# 4. 關閉連接
conn.close()
print("\n🎉 全部搞定！你的資料庫現在肥滋滋的了。")