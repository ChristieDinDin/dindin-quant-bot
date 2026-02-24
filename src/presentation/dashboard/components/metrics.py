"""
Metrics display components for the dashboard.
"""
import streamlit as st


def display_performance_metrics(results: dict, initial_capital: float = 1_000_000, currency: str = "TWD") -> None:
    """
    Display backtest performance metrics - compact but complete.
    
    Args:
        results: Results dict from BacktestService
        initial_capital: Initial capital amount
        currency: "TWD" or "USD" for display formatting
    """
    # Calculate values
    total_return = results.get('return_pct', 0)
    final_value = initial_capital * (1 + total_return / 100)
    profit = final_value - initial_capital
    equity_peak = results.get('equity_peak', final_value)
    win_rate = results.get('win_rate_pct', 0)
    max_dd = results.get('max_drawdown_pct', 0)
    num_trades = results.get('num_trades', 0)
    
    # Currency formatting: USD = $ prefix, TWD = suffix
    def fmt(val: float) -> str:
        if currency == "USD":
            if abs(val) >= 1_000_000:
                return f"${val/1_000_000:.2f}M"
            elif abs(val) >= 1_000:
                return f"${val/1_000:.1f}K"
            return f"${val:,.0f}"
        else:  # TWD
            if abs(val) >= 1_000_000:
                return f"{val/1_000_000:.1f}M"
            elif abs(val) >= 1_000:
                return f"{val/1_000:.0f}K"
            return f"{val:,.0f}"
    
    # Use custom CSS to make metrics more compact
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] {
            font-size: 18px;
        }
        [data-testid="stMetricLabel"] {
            font-size: 11px;
            margin-bottom: 2px;
        }
        [data-testid="stMetricDelta"] {
            font-size: 10px;
        }
        div[data-testid="metric-container"] {
            padding: 8px 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # === Row 1: Performance % ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_color = "normal" if total_return >= 0 else "inverse"
        profit_str = f"${profit/1000:+.1f}K" if currency == "USD" else f"{profit/1000:+.0f}K TWD"
        st.metric(
            "總報酬率",
            f"{total_return:.1f}%",
            delta=profit_str,
            delta_color=delta_color,
            help="本金翻了多少倍"
        )
    
    with col2:
        st.metric(
            "歷史勝率",
            f"{win_rate:.0f}%",
            help="過去交易賺錢的機率"
        )
    
    with col3:
        st.metric(
            "最大回撤",
            f"{max_dd:.1f}%",
            help="歷史上最慘曾經跌多少"
        )
    
    with col4:
        st.metric(
            "交易次數",
            f"{num_trades}",
            help="樣本數是否足夠"
        )
    
    # === Row 2: Capital ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "初始資金",
            fmt(initial_capital),
            help=f"起始本金 ({currency})"
        )
    
    with col2:
        profit_delta_color = "normal" if profit >= 0 else "inverse"
        st.metric(
            "最終資金",
            fmt(final_value),
            delta=fmt(profit),
            delta_color=profit_delta_color,
            help=f"回測結束時的總資產 ({currency})"
        )
    
    with col3:
        st.metric(
            "淨利潤",
            fmt(profit),
            delta=f"{total_return:+.1f}%",
            help=f"賺或賠的絕對金額 ({currency})"
        )
    
    with col4:
        st.metric(
            "歷史最高",
            fmt(equity_peak),
            delta=fmt(equity_peak - initial_capital),
            help=f"資產最高點 ({currency})"
        )


def display_signal_card(mfi_value: float,
                       buy_threshold: float,
                       sell_threshold: float,
                       strong_buy_threshold: float) -> None:
    """
    Display trading signal recommendation card - compact version.
    
    Args:
        mfi_value: Current MFI value
        buy_threshold: Buy signal threshold
        sell_threshold: Sell signal threshold
        strong_buy_threshold: Strong buy threshold
    """
    # Determine signal
    if mfi_value < strong_buy_threshold:
        st.success(
            "💰 **STRONG BUY** - 建議部位：**30%** (重倉)"
        )
    elif mfi_value < buy_threshold:
        st.success(
            "🟢 **BUY** - 建議部位：**15%** (試單)"
        )
    elif mfi_value > sell_threshold:
        st.error(
            "🔴 **SELL** - 建議動作：**清空持倉**"
        )
    else:
        st.info(
            "😴 **WAIT** - 空手或續抱，等待機會"
        )


def display_risk_metrics(results: dict) -> None:
    """
    Display detailed risk metrics.
    
    Args:
        results: Results dict from BacktestService
    """
    st.subheader("風險指標 (Risk Metrics)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sharpe = results.get('sharpe_ratio', 0)
        st.metric("Sharpe Ratio", f"{sharpe:.2f}", help="風險調整後報酬")
    
    with col2:
        sortino = results.get('sortino_ratio', 0)
        st.metric("Sortino Ratio", f"{sortino:.2f}", help="下行風險調整報酬")
    
    with col3:
        calmar = results.get('calmar_ratio', 0)
        st.metric("Calmar Ratio", f"{calmar:.2f}", help="回撤調整報酬")
