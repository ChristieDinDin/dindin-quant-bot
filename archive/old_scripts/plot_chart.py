import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 讀取妳算好 MFI 的那個乾淨檔案
df = pd.read_csv("6944_mfi_calculated.csv", index_col=0, parse_dates=True)

# 2. 建立畫布 (兩層：上面是 K 線，下面是 MFI)
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, subplot_titles=('Price', 'MFI'),
                    row_width=[0.2, 0.7])

# 3. 第一層：畫 K 線圖 (Candlestick)
fig.add_trace(go.Candlestick(x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name='OHLC'), 
                row=1, col=1)

# 4. 第二層：畫 MFI 線
fig.add_trace(go.Scatter(x=df.index, y=df['MFI'], line=dict(color='purple', width=2), name='MFI'),
                row=2, col=1)

# 5. 加入 MFI 的超買超賣線 (80 和 20)
fig.add_hline(y=80, line_dash="dot", row=2, col=1, annotation_text="Overbought (80)", annotation_position="bottom right")
fig.add_hline(y=20, line_dash="dot", row=2, col=1, annotation_text="Oversold (20)", annotation_position="top right")

# 6. 美化圖表 (設定黑色主題，像妳的 VS Code 一樣帥)
fig.update_layout(
    title='6944.TW - DinDin Quant Terminal',
    yaxis_title='Stock Price',
    template='plotly_dark',
    height=800
)

# 7. 隱藏下面的 Range Slider (太佔空間)
fig.update_layout(xaxis_rangeslider_visible=False)

# 8. 顯示圖表！
print("正在啟動瀏覽器顯示圖表...")
fig.show()