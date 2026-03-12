"""
Chart components for the dashboard.

Provides reusable chart functions using Plotly.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.core.indicators.pivot import find_swing_lows, find_swing_highs


def create_price_mfi_chart(df: pd.DataFrame, 
                           buy_level: float = 35,
                           sell_level: float = 85) -> go.Figure:
    """
    Create a combined price + MFI chart.
    
    Args:
        df: DataFrame with OHLCV and MFI columns
        buy_level: Buy threshold line
        sell_level: Sell threshold line
        
    Returns:
        Plotly Figure
    """
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=('Price', 'Money Flow Index')
    )
    
    # === Candlestick Chart ===
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price'
        ),
        row=1, col=1
    )
    
    # === MFI Line ===
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['MFI'],
            line=dict(color='#b550ff', width=2),
            name='MFI'
        ),
        row=2, col=1
    )
    
    # === Buy/Sell Signals ===
    buy_signals = df[df['MFI'] < buy_level]
    sell_signals = df[df['MFI'] > sell_level]
    
    fig.add_trace(
        go.Scatter(
            x=buy_signals.index,
            y=buy_signals['MFI'],
            mode='markers',
            marker=dict(color='#00e676', size=10, symbol='triangle-up'),
            name='Buy Signal'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=sell_signals.index,
            y=sell_signals['MFI'],
            mode='markers',
            marker=dict(color='#ff1744', size=10, symbol='triangle-down'),
            name='Sell Signal'
        ),
        row=2, col=1
    )
    
    # === Threshold Lines ===
    # Overbought zone (red)
    fig.add_hrect(
        y0=sell_level, y1=100,
        fillcolor="red",
        opacity=0.1,
        line_width=0,
        row=2, col=1
    )
    
    # Oversold zone (green)
    fig.add_hrect(
        y0=0, y1=buy_level,
        fillcolor="green",
        opacity=0.1,
        line_width=0,
        row=2, col=1
    )
    
    # === Layout ===
    fig.update_layout(
        template='plotly_dark',
        height=600,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=50, b=0),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=10),
            itemsizing='constant',
            tracegroupgap=10
        )
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="MFI", row=2, col=1)
    
    return fig


def create_price_mfi_rsi_chart(df: pd.DataFrame,
                               mfi_buy: float = 35,
                               mfi_sell: float = 85,
                               rsi_buy: float = 30,
                               rsi_sell: float = 70) -> go.Figure:
    """
    Create a combined price + MFI + RSI chart with overlay.
    
    Perfect for RSI+MFI Consensus strategy to see divergence.
    
    Args:
        df: DataFrame with OHLCV, MFI, and RSI columns
        mfi_buy: MFI buy threshold
        mfi_sell: MFI sell threshold
        rsi_buy: RSI buy threshold
        rsi_sell: RSI sell threshold
        
    Returns:
        Plotly Figure
    """
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=('Price', 'Money Flow Index')
    )
    
    # === Candlestick Chart ===
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price'
        ),
        row=1, col=1
    )
    
    # === MFI Line (primary) ===
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['MFI'],
            line=dict(color='#b550ff', width=2),
            name='MFI',
            yaxis='y2'
        ),
        row=2, col=1
    )
    
    # === RSI Line (overlay) ===
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['RSI'],
                line=dict(color='#00e676', width=2, dash='dot'),
                name='RSI',
                yaxis='y2'
            ),
            row=2, col=1
        )
    
    # === Buy/Sell Signals (when BOTH agree) ===
    if 'MFI' in df.columns and 'RSI' in df.columns:
        # Consensus buy: both oversold
        consensus_buy = df[(df['MFI'] < mfi_buy) & (df['RSI'] < rsi_buy)]
        # Consensus sell: both overbought
        consensus_sell = df[(df['MFI'] > mfi_sell) & (df['RSI'] > rsi_sell)]
        
        fig.add_trace(
            go.Scatter(
                x=consensus_buy.index,
                y=consensus_buy['MFI'],
                mode='markers',
                marker=dict(color='#00ff00', size=12, symbol='star', line=dict(width=2, color='white')),
                name='Consensus Buy',
                yaxis='y2'
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=consensus_sell.index,
                y=consensus_sell['MFI'],
                mode='markers',
                marker=dict(color='#ff0000', size=12, symbol='star', line=dict(width=2, color='white')),
                name='Consensus Sell',
                yaxis='y2'
            ),
            row=2, col=1
        )
    
    # === Threshold zones ===
    # MFI zones
    fig.add_hrect(
        y0=mfi_sell, y1=100,
        fillcolor="red",
        opacity=0.05,
        line_width=0,
        row=2, col=1
    )
    
    fig.add_hrect(
        y0=0, y1=mfi_buy,
        fillcolor="green",
        opacity=0.05,
        line_width=0,
        row=2, col=1
    )
    
    # RSI threshold lines (dotted)
    fig.add_hline(
        y=rsi_buy, 
        line_dash="dash", 
        line_color="#00e676", 
        opacity=0.3,
        annotation_text=f"RSI {rsi_buy}",
        annotation_position="right",
        row=2, col=1
    )
    
    fig.add_hline(
        y=rsi_sell,
        line_dash="dash",
        line_color="#00e676",
        opacity=0.3,
        annotation_text=f"RSI {rsi_sell}",
        annotation_position="right",
        row=2, col=1
    )
    
    # === Layout ===
    fig.update_layout(
        template='plotly_dark',
        height=600,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=50, b=0),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=10),
            itemsizing='constant',
            tracegroupgap=10
        )
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="MFI / RSI", range=[0, 100], row=2, col=1)
    
    return fig


def create_divergence_hunter_chart(
    df: pd.DataFrame,
    rsi_buy: float = 35,
    rsi_sell: float = 70,
    box_days: int = 40,
    trades: pd.DataFrame = None,
) -> go.Figure:
    """
    Chart for Divergence Hunter: box range overlay + divergence lines.

    - Box range: rolling high/low band (consolidation zone)
    - Bullish div lines: connect two swing lows (price down, MFI up)
    - Bearish div lines: connect two swing highs (price up, MFI down)
    """
    plot_df = df.tail(max(120, box_days * 2)).copy()
    if len(plot_df) < 50:
        return create_price_mfi_rsi_chart(df, 35, 85, rsi_buy, rsi_sell)

    lows = plot_df["Low"]
    highs = plot_df["High"]
    mfi = plot_df["MFI"]

    swing_lows = find_swing_lows(lows, window=5, min_bars_between=8)
    swing_highs = find_swing_highs(highs, window=5, min_bars_between=8)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=("Price + 箱型區間", "MFI / RSI 背離"),
    )

    fig.add_trace(
        go.Candlestick(
            x=plot_df.index,
            open=plot_df["Open"],
            high=plot_df["High"],
            low=plot_df["Low"],
            close=plot_df["Close"],
            name="Price",
        ),
        row=1, col=1,
    )

    roll_high = plot_df["High"].rolling(box_days, min_periods=box_days // 2).max()
    roll_low = plot_df["Low"].rolling(box_days, min_periods=box_days // 2).min()
    fig.add_trace(
        go.Scatter(
            x=plot_df.index,
            y=roll_high,
            line=dict(color="rgba(255,165,0,0.5)", width=1, dash="dot"),
            name="箱頂",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df.index,
            y=roll_low,
            line=dict(color="rgba(255,165,0,0.5)", width=1, dash="dot"),
            name="箱底",
            fill="tonexty",
            fillcolor="rgba(255,165,0,0.06)",
        ),
        row=1, col=1,
    )

    # Backtest trade markers (buy/sell)
    if trades is not None and not trades.empty and "EntryTime" in trades.columns:
        lo, hi = plot_df.index[0], plot_df.index[-1]
        buys_x, buys_y = [], []
        sells_x, sells_y = [], []
        for _, row in trades.iterrows():
            try:
                et = pd.Timestamp(row["EntryTime"])
                if hasattr(et, "tz") and et.tz is not None:
                    et = et.tz_localize(None)
            except Exception:
                continue
            if lo <= et <= hi:
                buys_x.append(et)
                buys_y.append(row["EntryPrice"])
            ex = row.get("ExitTime")
            if ex is not None and pd.notna(ex):
                try:
                    ext = pd.Timestamp(ex)
                    if hasattr(ext, "tz") and ext.tz is not None:
                        ext = ext.tz_localize(None)
                    if lo <= ext <= hi:
                        sells_x.append(ext)
                        sells_y.append(row["ExitPrice"])
                except Exception:
                    pass
        if buys_x:
            fig.add_trace(
                go.Scatter(
                    x=buys_x, y=buys_y,
                    mode="markers", marker=dict(symbol="triangle-up", size=12, color="#00e676"),
                    name="買入",
                ),
                row=1, col=1,
            )
        if sells_x:
            fig.add_trace(
                go.Scatter(
                    x=sells_x, y=sells_y,
                    mode="markers", marker=dict(symbol="triangle-down", size=12, color="#ff1744"),
                    name="賣出",
                ),
                row=1, col=1,
            )

    for i in range(len(swing_lows) - 1):
        i1, v1 = swing_lows[i]
        i2, v2 = swing_lows[i + 1]
        if v2 < v1 and mfi.iloc[i2] > mfi.iloc[i1]:
            xs = [plot_df.index[i1], plot_df.index[i2]]
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=[v1, v2],
                    mode="lines+markers",
                    line=dict(color="#00e676", width=2, dash="dash"),
                    marker=dict(size=8),
                    name="底背離 (價)",
                ),
                row=1, col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=[mfi.iloc[i1], mfi.iloc[i2]],
                    mode="lines+markers",
                    line=dict(color="#00e676", width=2, dash="dash"),
                    marker=dict(size=8),
                    name="底背離 (MFI)",
                ),
                row=2, col=1,
            )
            break

    for i in range(len(swing_highs) - 1):
        i1, v1 = swing_highs[i]
        i2, v2 = swing_highs[i + 1]
        if v2 > v1 and mfi.iloc[i2] < mfi.iloc[i1]:
            xs = [plot_df.index[i1], plot_df.index[i2]]
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=[v1, v2],
                    mode="lines+markers",
                    line=dict(color="#ff1744", width=2, dash="dash"),
                    marker=dict(size=8),
                    name="頂背離 (價)",
                ),
                row=1, col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=[mfi.iloc[i1], mfi.iloc[i2]],
                    mode="lines+markers",
                    line=dict(color="#ff1744", width=2, dash="dash"),
                    marker=dict(size=8),
                    name="頂背離 (MFI)",
                ),
                row=2, col=1,
            )
            break

    fig.add_trace(
        go.Scatter(
            x=plot_df.index,
            y=plot_df["MFI"],
            line=dict(color="#b550ff", width=2),
            name="MFI",
        ),
        row=2, col=1,
    )
    if "RSI" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df["RSI"],
                line=dict(color="#00e676", width=1.5, dash="dot"),
                name="RSI",
            ),
            row=2, col=1,
        )

    fig.add_hline(y=rsi_buy, row=2, col=1, line_dash="dot", line_color="#00e676", opacity=0.3)
    fig.add_hline(y=rsi_sell, row=2, col=1, line_dash="dot", line_color="#ff1744", opacity=0.3)

    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=50, b=0),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="MFI / RSI", range=[0, 100], row=2, col=1)
    return fig


def create_performance_chart(backtest_results: dict) -> go.Figure:
    """
    Create equity curve chart from backtest results.
    
    Args:
        backtest_results: Results from BacktestService
        
    Returns:
        Plotly Figure
    """
    # This would require extracting equity curve from backtest results
    # Placeholder for now
    fig = go.Figure()
    
    # TODO: Implement equity curve visualization
    
    return fig
