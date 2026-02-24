import sqlite3

# 1. 建立連線 (如果檔案不存在，它會自動創造一個)
conn = sqlite3.connect('market_data.db')
cursor = conn.cursor()

# 2. 建立倉庫架構 (Schema)
# 我們創造一個表格叫 'daily_kline'
# 欄位有：日期 (date), 股票代號 (symbol), 開高低收量 (OHLCV)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_kline (
        date TEXT,
        symbol TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        PRIMARY KEY (date, symbol)
    )
''')

# 3. 存檔並關閉
conn.commit()
conn.close()

print("🎉 market_data.db 建立成功！這就是妳的巨型 Excel！")