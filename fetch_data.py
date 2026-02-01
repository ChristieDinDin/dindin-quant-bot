import yfinance as yf
import pandas as pd

# 1. 設定妳想抓的股票代號 (台股要在後面加 .TW)
# 我們拿妳之前關注的 6944 兆聯實業當範例
stock_id = "2337.TW"

# 2. 抓取過去一年的歷史數據
print(f"正在從交易所搬運 {stock_id} 的數據...")
df = yf.download(stock_id, period="1y", progress=True)

# 3. 看看數據長什麼樣子 (印出最後 5 筆)
print("\n--- 數據搬運完成！這是最新的 5 筆資料 ---")
print(df.tail())

# 4. 把數據存成 CSV 檔，以後不用網路也能跑回測
file_name = f"{stock_id}_history.csv"
df.to_csv(file_name)
print(f"\n✅ 數據已存檔為: {file_name}")