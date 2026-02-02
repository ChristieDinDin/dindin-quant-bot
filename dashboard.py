import streamlit as st
import pandas as pd
import numpy as np  # 1. 先叫出 numpy

# --- 💉 基因改造手術開始 (Monkey Patch) ---
# 這是為了修復 NumPy 2.0 和舊版 Bokeh 的衝突
# 我們手動把被刪除的 bool8 補回去，騙過 Bokeh
if not hasattr(np, 'bool8'):
    np.bool8 = np.bool_
# --- 手術結束 ---

import pandas_ta_classic as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backtesting import Backtest, Strategy

# --- 1. 頁面設定 ---
st.set_page_config(page_title="DinDin Quant Terminal", layout="wide", page_icon="💎")

# --- 2. 側邊欄：控制中心 ---
st.sidebar.header("🛠️ 策略參數 (Settings)")
ticker = st.sidebar.selectbox("選擇股票", ["6944.TW", "2337.TW"])

# 這裡的參數會直接連動到回測引擎！
mfi_period = st.sidebar.slider("MFI 天數", 7, 30, 16)
buy_level = st.sidebar.slider("買進門檻 (Buy <)", 10, 50, 35)
sell_level = st.sidebar.slider("賣出門檻 (Sell >)", 60, 95, 85)

# --- 3. 定義回測策略 (為了即時計算勝率) ---
# 這是為了讓 Dashboard 能動態算出「這組參數好不好」
class DashboardStrategy(Strategy):
    # 這些參數稍後會被動態覆寫
    mfi_period = 14
    buy_level = 30 
    sell_level = 80
    
    def init(self):
        self.mfi = self.I(ta.mfi, pd.Series(self.data.High), pd.Series(self.data.Low), 
                          pd.Series(self.data.Close), pd.Series(self.data.Volume), length=self.mfi_period)

    def next(self):
        # 這裡的邏輯只為了計算績效，簡單版即可
        if not self.position and self.mfi[-1] < self.buy_level:
            self.buy()
        elif self.position and self.mfi[-1] > self.sell_level:
            self.position.close()

# --- 4. 讀取數據 ---
@st.cache_data
def load_data(ticker_name):
    filename = f"{ticker_name}_history.csv"
    try:
        df = pd.read_csv(filename, index_col=0, parse_dates=True, header=[0, 1])
        df.columns = df.columns.droplevel(1)
        df.columns = [c.capitalize() for c in df.columns]
        for c in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna()
        return df
    except FileNotFoundError:
        return None

df = load_data(ticker)
if df is None:
    st.error(f"找不到 {ticker} 數據！請先執行 fetch_data.py")
    st.stop()

# --- 5. 即時運算區 ---

# A. 算指標
df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=mfi_period)
last_mfi = df['MFI'].iloc[-1]
last_price = df['Close'].iloc[-1]

# B. 跑回測 (即時算出勝率與風險)
# 把側邊欄的參數傳進去
DashboardStrategy.mfi_period = mfi_period
DashboardStrategy.buy_level = buy_level
DashboardStrategy.sell_level = sell_level

bt = Backtest(df, DashboardStrategy, cash=1_000_000, commission=.001425)
stats = bt.run()

# 從回測結果抓出我們要的關鍵數據
win_rate = stats['Win Rate [%]']
max_dd = stats['Max. Drawdown [%]']
total_return = stats['Return [%]']
num_trades = stats['# Trades']

# --- 6. 介面顯示 (UI Layout) ---
st.title(f"🚀 {ticker} 智能戰情室")

# --- 區塊一：AI 投顧建議 (最重要！) ---
st.subheader("💡 AI 交易建議 (Action Plan)")

# 定義資金控管邏輯 (Sizing Logic)
# 這裡直接把邏輯寫成文字顯示給 Nini 看
if last_mfi < 20:
    signal_color = "green"
    action_text = "💰 **STRONG BUY (強力買進)**"
    sizing_text = "建議部位：**30% (重倉)** - 處於極度超賣區，勝率極高。"
elif last_mfi < buy_level:
    signal_color = "green"
    action_text = "🟢 **BUY (買進訊號)**"
    sizing_text = "建議部位：**15% (試單)** - 分批佈局，保留現金加碼。"
elif last_mfi > sell_level:
    signal_color = "red"
    action_text = "🔴 **SELL (獲利了結)**"
    sizing_text = "建議動作：**清空持倉** - 指標過熱，落袋為安。"
else:
    signal_color = "gray"
    action_text = "😴 **WAIT (觀望)**"
    sizing_text = "建議動作：空手或續抱，等待更佳機會。"

# 用漂亮的卡片顯示建議
with st.container():
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.metric("目前 MFI", f"{last_mfi:.1f}", delta=f"{last_mfi - df['MFI'].iloc[-2]:.1f}", delta_color="inverse")
    with col_b:
        if signal_color == "green":
            st.success(f"{action_text}\n\n{sizing_text}")
        elif signal_color == "red":
            st.error(f"{action_text}\n\n{sizing_text}")
        else:
            st.info(f"{action_text}\n\n{sizing_text}")

st.markdown("---")

# --- 區塊二：風險與期望值 (回測數據) ---
st.subheader("📊 歷史回測數據 (Risk & Reward)")
st.caption(f"基於過去 {len(df)} 天的數據，使用目前側邊欄參數即時運算：")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("歷史勝率 (Win Rate)", f"{win_rate:.0f}%", help="過去交易賺錢的機率")
kpi2.metric("總報酬率 (Return)", f"{total_return:.1f}%", help="本金翻了多少倍")
kpi3.metric("最大風險 (Max Drawdown)", f"{max_dd:.1f}%", help="歷史上最慘曾經跌多少")
kpi4.metric("交易次數 (# Trades)", f"{num_trades:.0f}", help="樣本數是否足夠")

st.markdown("---")

# --- 區塊三：圖表區 ---
st.subheader("📈 趨勢與進出點 (Charts)")

# 產生訊號點
buy_signals = df[df['MFI'] < buy_level]
sell_signals = df[df['MFI'] > sell_level]

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_width=[0.2, 0.8])

# K 線
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)

# MFI 線
fig.add_trace(go.Scatter(x=df.index, y=df['MFI'], line=dict(color='#b550ff', width=2), name='MFI'), row=2, col=1)

# 買賣點
fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['MFI'], mode='markers', marker=dict(color='#00e676', size=10), name='Buy'), row=2, col=1)
fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['MFI'], mode='markers', marker=dict(color='#ff1744', size=10), name='Sell'), row=2, col=1)

# 警戒線
fig.add_hrect(y0=sell_level, y1=100, row=2, col=1, fillcolor="red", opacity=0.1, line_width=0)
fig.add_hrect(y0=0, y1=buy_level, row=2, col=1, fillcolor="green", opacity=0.1, line_width=0)

fig.update_layout(template='plotly_dark', height=600, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig, use_container_width=True)