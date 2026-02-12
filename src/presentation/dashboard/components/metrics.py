"""
Metrics display components for the dashboard.
"""
import streamlit as st


def display_performance_metrics(results: dict, initial_capital: float = 1_000_000) -> None:
    """
    Display backtest performance metrics in a compact layout.
    
    Args:
        results: Results dict from BacktestService
        initial_capital: Initial capital amount
    """
    # Calculate values
    total_return = results.get('return_pct', 0)
    final_value = initial_capital * (1 + total_return / 100)
    profit = final_value - initial_capital
    equity_peak = results.get('equity_peak', final_value)
    win_rate = results.get('win_rate_pct', 0)
    max_dd = results.get('max_drawdown_pct', 0)
    num_trades = results.get('num_trades', 0)
    
    # === Row 1: Performance Metrics ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_color = "normal" if total_return >= 0 else "inverse"
        st.metric(
            "報酬率",
            f"{total_return:.1f}%",
            delta=f"{profit/1000:.0f}K TWD",
            delta_color=delta_color,
            help="總報酬率與絕對獲利"
        )
    
    with col2:
        st.metric(
            "勝率",
            f"{win_rate:.0f}%",
            delta=f"{num_trades} 筆",
            help="贏的機率 (交易次數)"
        )
    
    with col3:
        st.metric(
            "最大回撤",
            f"{max_dd:.1f}%",
            delta=f"{(equity_peak - initial_capital)/1000:.0f}K",
            help="最大虧損 (歷史高點)"
        )
    
    with col4:
        st.metric(
            "最終資金",
            f"{final_value/1_000_000:.2f}M",
            delta=f"{initial_capital/1_000_000:.2f}M",
            help="最終 vs 初始資金 (百萬)"
        )


def display_signal_card(mfi_value: float,
                       buy_threshold: float,
                       sell_threshold: float,
                       strong_buy_threshold: float) -> None:
    """
    Display trading signal recommendation card.
    
    Args:
        mfi_value: Current MFI value
        buy_threshold: Buy signal threshold
        sell_threshold: Sell signal threshold
        strong_buy_threshold: Strong buy threshold
    """
    col_a, col_b = st.columns([1, 2])
    
    with col_a:
        # Show current MFI value
        # Calculate delta (change from previous)
        st.metric(
            "目前 MFI",
            f"{mfi_value:.1f}",
            help="Money Flow Index - 資金流量指標"
        )
    
    with col_b:
        # Determine signal
        if mfi_value < strong_buy_threshold:
            st.success(
                "💰 **STRONG BUY (強力買進)**\n\n"
                f"建議部位：**30% (重倉)** - 處於極度超賣區，勝率極高。"
            )
        elif mfi_value < buy_threshold:
            st.success(
                "🟢 **BUY (買進訊號)**\n\n"
                f"建議部位：**15% (試單)** - 分批佈局，保留現金加碼。"
            )
        elif mfi_value > sell_threshold:
            st.error(
                "🔴 **SELL (獲利了結)**\n\n"
                "建議動作：**清空持倉** - 指標過熱，落袋為安。"
            )
        else:
            st.info(
                "😴 **WAIT (觀望)**\n\n"
                "建議動作：空手或續抱，等待更佳機會。"
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
