import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy

# 1. 策略邏輯 (Tier 2: 階梯式加碼)
class MfiHunter(Strategy):
    # 使用我們之前算出來的神之參數
    mfi_period = 16
    buy_level = 35 
    sell_level = 85
    
    def init(self):
        self.mfi = self.I(ta.mfi, 
                          pd.Series(self.data.High), 
                          pd.Series(self.data.Low), 
                          pd.Series(self.data.Close), 
                          pd.Series(self.data.Volume), 
                          length=self.mfi_period)

    def next(self):
        # A. 安全檢查：如果破產了就別算了
        if self.equity == 0: return 
        
        # --- 修正重點：手動算市值 ---
        # 既然它不給我們 .value 也不給 .cash，我們就自己算！
        # 市值 = 手上的股數 (size) * 現在的股價 (Close[-1])
        position_value = self.position.size * self.data.Close[-1]
        
        # 現在我們可以算出真實的持倉比例了
        current_pct = position_value / self.equity
        # ------------------------

        # B. 出場邏輯 (獲利了結)
        if self.position:
            if self.mfi[-1] > self.sell_level:
                self.position.close()
                return 

        # C. 進場邏輯：階梯式加碼
        if current_pct < 0.8:
            
            # 情況 1: 世紀大特價 (MFI < 20) -> 重倉買
            if self.mfi[-1] < 20:
                self.buy(size=0.3) 
                
            # 情況 2: 普通特價 (MFI < 35) -> 試單
            elif self.mfi[-1] < self.buy_level:
                self.buy(size=0.15)
            
            # 情況 1: 世紀大特價 (MFI < 20) -> 重倉買 30%
            if self.mfi[-1] < 20:
                self.buy(size=0.3) 
                
            # 情況 2: 普通特價 (MFI < 35) -> 試單買 15%
            elif self.mfi[-1] < self.buy_level:
                self.buy(size=0.15) 

# 2. 準備數據 (確保讀取的是 6944)
df = pd.read_csv("6944.TW_history.csv", index_col=0, parse_dates=True, header=[0, 1])
df.columns = df.columns.droplevel(1) 
df.columns = [c.capitalize() for c in df.columns] 
for c in ['Open', 'High', 'Low', 'Close', 'Volume']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df = df.dropna()

# 3. 設定回測引擎
bt = Backtest(df, MfiHunter,
              cash=1_000_000,
              commission=.001425,
              trade_on_close=True)

# 4. 執行「單次」回測 (Single Run)
# 這裡我們不跑 optimize，避免 Mac 報錯，直接看新邏輯的表現
print("正在測試階梯式加碼邏輯...")
stats = bt.run()
print(stats)

# 5. 畫圖
bt.plot()