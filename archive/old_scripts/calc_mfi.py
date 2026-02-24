import pandas as pd
import pandas_ta as ta

# 1. 讀取 CSV (關鍵修正！)
# header=[0, 1] 告訴 pandas：前兩行都是標題，不要把它當成數據讀進來
# 這樣 "6944.TW" 那一行就會被正確處理，不會污染數據
df = pd.read_csv("2337.TW_history.csv", index_col=0, parse_dates=True, header=[0, 1])

# 2. 清洗標題
# 我們不需要第二層的 "6944.TW" 標籤，把它丟掉，讓欄位變回乾淨的 'Close', 'High'
df.columns = df.columns.droplevel(1)

# 3. 雙重保險 (Type Casting)
# 強制把這幾個欄位轉成數字，如果有任何髒東西轉不過來，就變 NaN
cols = ['Open', 'High', 'Low', 'Close', 'Volume']
for c in cols:
    df[c] = pd.to_numeric(df[c], errors='coerce')

# 4. 計算 14 日 MFI
df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)

# 5. 見證奇蹟
print("\n--- 2337.TW MFI 計算結果 (最後 5 天) ---")
print(df[['Close', 'MFI']].tail(5))

# 6. 存個乾淨的檔
df.to_csv("2337_mfi_calculated.csv")
print("\n✅ 修復完成！乾淨的數據已存檔。")