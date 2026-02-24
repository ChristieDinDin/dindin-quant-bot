"""
Main Streamlit Dashboard Application.

This is the refactored dashboard with clean separation of concerns.
"""
import sys
import os
from pathlib import Path

# Ensure we run from project root (fixes data/ YAML loading when streamlit changes cwd)
project_root = Path(__file__).resolve().parent.parent.parent.parent
os.chdir(project_root)

# Add src to Python path
sys.path.insert(0, str(project_root))

import streamlit as st
import numpy as np

# NumPy 2.0 compatibility patch
if not hasattr(np, 'bool8'):
    np.bool8 = np.bool_

from src.presentation.dashboard.components.charts import create_price_mfi_chart, create_price_mfi_rsi_chart
from src.presentation.dashboard.components.metrics import display_performance_metrics, display_signal_card
from src.presentation.dashboard.components.controls import create_sidebar_controls

from src.application.services.data_service import DataService
from src.infrastructure.data_providers.yfinance_provider import YFinanceProvider
from src.infrastructure.database.connection import get_database
from src.infrastructure.database.repository import MarketDataRepository
from src.core.indicators.mfi import MFI

try:
    from src.application.services.backtest_service import BacktestService
    from src.application.use_cases.run_backtest import RunBacktestUseCase
    BACKTESTING_AVAILABLE = True
except ImportError:
    BACKTESTING_AVAILABLE = False

@st.cache_resource
def initialize_services():
    """Initialize all services."""
    provider = YFinanceProvider()
    provider.connect()
    
    db = get_database()
    repository = MarketDataRepository(db)
    
    data_service = DataService(provider, repository)
    backtest_service = BacktestService(data_service) if BACKTESTING_AVAILABLE else None
    
    return data_service, backtest_service


def main():
    """Main dashboard application."""
    st.set_page_config(
        page_title="DinDin Quant Terminal",
        layout="wide",
        page_icon="💎"
    )
    
    # Force reload strategy registry to ensure new strategies are loaded
    import importlib
    import src.core.strategies.registry as registry_module
    import src.core.strategies.mfi_hunter
    import src.core.strategies.rsi_mfi_consensus
    
    # Reload all strategy modules
    importlib.reload(src.core.strategies.mfi_hunter)
    importlib.reload(src.core.strategies.rsi_mfi_consensus)
    importlib.reload(registry_module)
    
    # Initialize services
    data_service, backtest_service = initialize_services()
    
    # === Market selector in sidebar (upper left) ===
    st.sidebar.header("市場")
    market = st.sidebar.radio(
        "市場",
        ["tw", "us"],
        format_func=lambda x: "🇹🇼 台灣股市 (TWD)" if x == "tw" else "🇺🇸 美國股市 (USD)",
        key="market_selector",
        label_visibility="collapsed"
    )
    st.sidebar.markdown("---")
    
    # Sidebar controls (filtered by market)
    controls = create_sidebar_controls(market=market)
    
    symbol = controls['symbol']
    strategy_name = controls['strategy_name']
    mfi_period = controls['mfi_period']
    buy_level = controls['buy_level']
    sell_level = controls['sell_level']
    rsi_period = controls['rsi_period']
    rsi_oversold = controls['rsi_oversold']
    rsi_overbought = controls['rsi_overbought']
    initial_capital = controls['initial_cash']
    commission_rate = controls['commission']
    currency = controls.get('currency', 'TWD')
    
    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_terminal, tab_lab = st.tabs(["📊 Trading Terminal", "🧪 Backtest Lab"])

    # =========================================================================
    # TAB 1 — Trading Terminal (existing single-stock view)
    # =========================================================================
    with tab_terminal:
        from src.utils.stock_list import load_stock_metadata
        metadata = load_stock_metadata()
        if symbol is None:
            symbol = "AAPL" if market == "us" else "2330.TW"
        fallback = (symbol or "").replace('.TW', '').replace('.TWO', '') if symbol else ""
        stock_name = metadata.get(symbol, fallback) or symbol

        st.title(f"🚀 {stock_name}")
        st.caption(f"股票代碼: {symbol}")

        try:
            df = data_service.get_data(symbol)

            if df.empty:
                st.error(f"找不到 {symbol} 數據！請先執行數據抓取。")
            else:
                # Calculate indicators
                try:
                    from src.core.indicators.rsi import RSI

                    mfi_indicator = MFI(
                        period=mfi_period,
                        buy_threshold=buy_level,
                        sell_threshold=sell_level
                    )
                    df['MFI'] = mfi_indicator.calculate(df)
                    last_mfi = df['MFI'].iloc[-1]

                    if strategy_name == "rsi_mfi_consensus":
                        rsi_indicator = RSI(
                            period=rsi_period,
                            overbought=rsi_overbought,
                            oversold=rsi_oversold
                        )
                        df['RSI'] = rsi_indicator.calculate(df)
                        last_rsi = df['RSI'].iloc[-1]
                    else:
                        last_rsi = None

                except Exception as e:
                    st.error(f"Failed to calculate indicators: {e}")
                    st.write("Debug - DataFrame columns:", df.columns.tolist())
                    st.write("Debug - DataFrame shape:", df.shape)
                    st.write("Debug - DataFrame head:", df.head())
                    st.stop()

                # Run backtest
                try:
                    if not BACKTESTING_AVAILABLE or backtest_service is None:
                        raise ImportError("backtesting package not available")
                    use_case = RunBacktestUseCase(backtest_service, data_service)

                    if strategy_name == "mfi_hunter":
                        strategy_params = {
                            'mfi_period': mfi_period,
                            'buy_threshold': buy_level,
                            'sell_threshold': sell_level
                        }
                    elif strategy_name == "rsi_mfi_consensus":
                        strategy_params = {
                            'rsi_period': rsi_period,
                            'mfi_period': mfi_period,
                            'rsi_oversold': rsi_oversold,
                            'rsi_overbought': rsi_overbought,
                            'mfi_oversold': buy_level,
                            'mfi_overbought': sell_level
                        }
                    else:
                        strategy_params = {}

                    backtest_results = use_case.execute(
                        symbol=symbol,
                        strategy_name=strategy_name,
                        strategy_params=strategy_params,
                        cash=initial_capital,
                        commission=commission_rate
                    )
                except Exception as e:
                    import traceback
                    full_tb = traceback.format_exc()
                    st.error(f"Backtest failed: {e}")
                    st.code(full_tb)
                    print("=" * 80)
                    print("BACKTEST ERROR:")
                    print(full_tb)
                    print("=" * 80)
                    backtest_results = {'success': False, 'error': str(e)}

                # Two-column layout
                left_col, right_col = st.columns([1, 1])

                with left_col:
                    st.subheader("💡 AI 交易建議 (Action Plan)")
                    if strategy_name == "rsi_mfi_consensus" and last_rsi is not None:
                        col_ind1, col_ind2 = st.columns(2)
                        with col_ind1:
                            st.metric("目前 RSI", f"{last_rsi:.1f}")
                        with col_ind2:
                            st.metric("目前 MFI", f"{last_mfi:.1f}")
                    else:
                        st.metric("目前 MFI", f"{last_mfi:.1f}")
                    display_signal_card(last_mfi, buy_level, sell_level, 20)

                with right_col:
                    st.subheader("📊 歷史回測數據 (Risk & Reward)")
                    st.caption(f"基於過去 {len(df)} 天的數據，使用目前側邊欄參數即時運算：")
                    if backtest_results['success']:
                        display_performance_metrics(
                            backtest_results,
                            initial_capital=initial_capital,
                            currency=currency
                        )
                    else:
                        st.error(f"回測失敗: {backtest_results.get('error')}")

                st.markdown("---")
                st.subheader("📈 趨勢與進出點 (Charts)")

                if strategy_name == "rsi_mfi_consensus":
                    if 'RSI' not in df.columns:
                        from src.core.indicators.rsi import RSI
                        rsi_indicator = RSI(period=rsi_period)
                        df['RSI'] = rsi_indicator.calculate(df)
                    fig = create_price_mfi_rsi_chart(
                        df,
                        mfi_buy=buy_level,
                        mfi_sell=sell_level,
                        rsi_buy=rsi_oversold,
                        rsi_sell=rsi_overbought
                    )
                else:
                    fig = create_price_mfi_chart(df, buy_level, sell_level)

                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"發生錯誤: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    # =========================================================================
    # TAB 2 — Backtest Lab
    # =========================================================================
    with tab_lab:
        from src.presentation.dashboard.components.backtest_lab import render_backtest_lab
        render_backtest_lab(backtest_service, data_service)


if __name__ == '__main__':
    main()
