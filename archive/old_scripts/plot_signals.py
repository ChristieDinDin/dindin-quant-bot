import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 讀取數據
df = pd.read_csv("2337_mfi_calculated.csv", index_col=0, parse_dates=True)

# 2. 定義訊號
buy_signals = df[df['MFI'] < 30]  # 為了讓妳開心，我稍微放寬到 30，讓妳多看幾個綠點
sell_signals = df[df['MFI'] > 80]

# 3. 建立畫布
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, 
                    subplot_titles=('Price Action', 'MFI Momentum'),
                    row_width=[0.25, 0.75])

# --- Row 1: K 線圖 ---
fig.add_trace(go.Candlestick(x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], 
                name='OHLC',
                increasing_line_color='#26a69a', 
                decreasing_line_color='#ef5350'
               ), row=1, col=1)

# --- Row 2: MFI 指標與訊號 (魔改 Tooltip 版) ---

# A. MFI 線
fig.add_trace(go.Scatter(x=df.index, y=df['MFI'], 
                         line=dict(color='#b550ff', width=2), 
                         name='MFI'), row=2, col=1)

# B. 買進訊號 (綠點) - 加入 Price 資訊
fig.add_trace(go.Scatter(
    x=buy_signals.index, 
    y=buy_signals['MFI'],
    # 關鍵魔法：把 Price 塞進 customdata
    customdata=buy_signals[['Close']], 
    # 顯示格式：<br> 是換行，%{customdata[0]} 就是我們塞進去的股價
    hovertemplate='<b>Buy Signal</b> 🟢<br>Date: %{x|%Y-%m-%d}<br>MFI: %{y:.1f}<br><b>Price: %{customdata[0]:.1f}</b><extra></extra>',
    mode='markers',
    marker=dict(symbol='circle', color='#00e676', size=10, line=dict(width=2, color='white')), 
    name='Buy Trigger'
), row=2, col=1)

# C. 賣出訊號 (紅點) - 加入 Price 資訊
fig.add_trace(go.Scatter(
    x=sell_signals.index, 
    y=sell_signals['MFI'], 
    customdata=sell_signals[['Close']], # 一樣要把 Price 塞進來
    hovertemplate='<b>Sell Signal</b> 🔴<br>Date: %{x|%Y-%m-%d}<br>MFI: %{y:.1f}<br><b>Price: %{customdata[0]:.1f}</b><extra></extra>',
    mode='markers',
    marker=dict(symbol='circle', color='#ff1744', size=10, line=dict(width=2, color='white')), 
    name='Sell Trigger'
), row=2, col=1)

# D. 背景區塊
fig.add_hrect(y0=80, y1=100, row=2, col=1, fillcolor="red", opacity=0.1, line_width=0)
fig.add_hrect(y0=0, y1=20, row=2, col=1, fillcolor="green", opacity=0.1, line_width=0)

# --- 美化設定 (Final Polish) ---
fig.update_layout(
    title=dict(text='2337.TW - DinDin Quant Terminal v1.0', x=0.5),
    template='plotly_dark',
    height=800,
    showlegend=True,
    hovermode="x unified", # 這一行就夠了，不需要 update_traces
    # 這是對付殭屍線的雙重封印
    xaxis_rangeslider_visible=False,
    xaxis2_rangeslider_visible=False, 
)

# 確保所有 X 軸都沒有滑桿 (The Nuke Option)
fig.update_xaxes(rangeslider_visible=False)

print("啟動 v1.0 完美版圖表... Bye Bye Range Slider!")
fig.show()
