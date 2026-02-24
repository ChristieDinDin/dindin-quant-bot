"""
Backtest Lab Component - Batch backtest across multiple stocks.

Runs a chosen strategy against an entire universe of stocks,
collects performance metrics, and ranks them in a sortable table.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_backtest_lab(backtest_service, data_service):
    """Main Backtest Lab entry point — call this from app.py inside a tab."""
    st.header("🧪 Backtest Lab")
    st.caption("一次回測多支股票，找出策略最佳表現的標的 · Cross-sectional strategy screening")

    if backtest_service is None:
        st.error("Backtesting package not available. Check that `backtesting` is in requirements.txt.")
        return

    # ── Lazy imports (keep top-level imports minimal) ────────────────────────
    from src.utils.stock_list import load_stock_metadata, get_available_stocks_from_db
    from src.core.strategies.registry import get_global_registry

    metadata = load_stock_metadata()
    db_rows = get_available_stocks_from_db()
    db_symbols = {row[0] for row in db_rows} if db_rows else set()

    us_symbols = sorted([s for s in metadata if not (s.endswith('.TW') or s.endswith('.TWO'))])
    tw_symbols = sorted([s for s in metadata if s.endswith('.TW') or s.endswith('.TWO')])

    # ── Settings panel ───────────────────────────────────────────────────────
    st.subheader("⚙️ 批量回測設定")
    col_uni, col_strat, col_params = st.columns([1.2, 1, 1.2])

    # --- Universe ----
    with col_uni:
        st.markdown("**股票範圍**")
        market_choice = st.radio(
            "市場",
            ["🇺🇸 美國", "🇹🇼 台灣"],
            horizontal=True,
            key="lab_market"
        )
        universe_pool = us_symbols if "美國" in market_choice else tw_symbols

        scope = st.radio(
            "範圍",
            ["DB 已有資料", "YAML 完整清單", "自訂"],
            key="lab_scope"
        )
        if scope == "DB 已有資料":
            symbols_to_test = [s for s in universe_pool if s in db_symbols]
        elif scope == "YAML 完整清單":
            symbols_to_test = universe_pool
        else:
            raw = st.text_area(
                "每行一個代碼",
                placeholder="AAPL\nNVDA\nTSLA",
                height=120,
                key="lab_custom"
            )
            symbols_to_test = [s.strip().upper() for s in raw.splitlines() if s.strip()]

        st.info(f"待測股票：**{len(symbols_to_test)}** 支")
        if symbols_to_test:
            with st.expander("查看清單"):
                st.write(", ".join(symbols_to_test[:80]))
                if len(symbols_to_test) > 80:
                    st.caption(f"... 還有 {len(symbols_to_test) - 80} 支")

    # --- Strategy ----
    with col_strat:
        st.markdown("**策略 & 資金**")
        registry = get_global_registry()
        avail_strats = registry.list_strategies()
        _labels = {
            "mfi_hunter": "🎯 MFI Hunter",
            "rsi_mfi_consensus": "📡 RSI+MFI Consensus"
        }
        strategy_name = st.selectbox(
            "交易策略",
            avail_strats,
            format_func=lambda x: _labels.get(x, x),
            key="lab_strategy"
        )
        initial_capital = st.number_input(
            "初始資金 ($)",
            min_value=10_000,
            max_value=10_000_000,
            value=1_000_000,
            step=100_000,
            key="lab_capital"
        )
        market_key = "us" if "美國" in market_choice else "tw"
        default_commission = 0.001425 if market_key == "tw" else 0.001
        commission = st.number_input(
            "手續費率",
            min_value=0.0001,
            max_value=0.01,
            value=default_commission,
            format="%.4f",
            key="lab_commission"
        )

    # --- Strategy params ----
    with col_params:
        st.markdown("**策略參數**")
        if strategy_name == "mfi_hunter":
            mfi_period = st.slider("MFI 週期", 5, 30, 14, key="lab_mfi_p")
            buy_thr = st.slider("買入閾值 (oversold)", 10, 40, 20, key="lab_buy_t")
            sell_thr = st.slider("賣出閾值 (overbought)", 60, 90, 80, key="lab_sell_t")
            strategy_params = {
                "mfi_period": mfi_period,
                "buy_threshold": buy_thr,
                "sell_threshold": sell_thr
            }
        elif strategy_name == "rsi_mfi_consensus":
            mfi_period = st.slider("MFI 週期", 5, 30, 14, key="lab_mfi_p")
            rsi_period = st.slider("RSI 週期", 5, 30, 14, key="lab_rsi_p")
            mfi_os = st.slider("MFI 買入", 10, 40, 20, key="lab_mfi_os")
            rsi_os = st.slider("RSI 買入", 20, 50, 30, key="lab_rsi_os")
            strategy_params = {
                "mfi_period": mfi_period,
                "rsi_period": rsi_period,
                "mfi_oversold": mfi_os,
                "rsi_oversold": rsi_os,
                "mfi_overbought": 80,
                "rsi_overbought": 70
            }
        else:
            strategy_params = {}

    st.markdown("---")

    # ── Run button ───────────────────────────────────────────────────────────
    run_col, clear_col, _ = st.columns([1.2, 0.8, 4])
    with run_col:
        run_clicked = st.button(
            f"▶ 開始回測 ({len(symbols_to_test)} 支)",
            type="primary",
            disabled=(len(symbols_to_test) == 0),
            use_container_width=True,
            key="lab_run"
        )
    with clear_col:
        if st.button("🗑 清除結果", use_container_width=True, key="lab_clear"):
            st.session_state.pop("lab_results_df", None)
            st.session_state.pop("lab_drill_symbol", None)
            st.rerun()

    # ── Batch execution ──────────────────────────────────────────────────────
    if run_clicked and symbols_to_test:
        df_results = _run_batch(
            symbols_to_test, strategy_name, strategy_params,
            backtest_service, data_service,
            initial_capital, commission, metadata
        )
        if df_results is not None and not df_results.empty:
            st.session_state["lab_results_df"] = df_results
            st.session_state.pop("lab_drill_symbol", None)

    # ── Display results if available ─────────────────────────────────────────
    if "lab_results_df" in st.session_state:
        _display_results(st.session_state["lab_results_df"], metadata, data_service)


# ─────────────────────────────────────────────────────────────────────────────
# Batch runner
# ─────────────────────────────────────────────────────────────────────────────

def _run_batch(symbols, strategy_name, strategy_params,
               backtest_service, data_service,
               capital, commission, metadata) -> pd.DataFrame | None:
    """Run strategy on every symbol with a progress bar. Returns results DataFrame."""
    from src.application.use_cases.run_backtest import RunBacktestUseCase

    use_case = RunBacktestUseCase(backtest_service, data_service)

    rows = []
    errors = []

    progress = st.progress(0, text="準備中...")
    status = st.empty()

    for i, symbol in enumerate(symbols):
        pct = (i + 1) / len(symbols)
        display_name = metadata.get(symbol, symbol)
        status.markdown(f"⏳ **{symbol}** — {display_name} &nbsp;&nbsp; ({i + 1} / {len(symbols)})")
        progress.progress(pct)

        try:
            result = use_case.execute(
                symbol=symbol,
                strategy_name=strategy_name,
                strategy_params=strategy_params,
                cash=capital,
                commission=commission
            )
            if result.get("success"):
                rows.append({
                    "Symbol":      symbol,
                    "Name":        metadata.get(symbol, symbol),
                    "Return %":    round(result.get("return_pct", 0), 2),
                    "B&H %":       round(result.get("buy_hold_return_pct", 0), 2),
                    "Sharpe":      round(result.get("sharpe_ratio", 0), 3),
                    "Sortino":     round(result.get("sortino_ratio", 0), 3),
                    "Max DD %":    round(result.get("max_drawdown_pct", 0), 2),
                    "Win Rate %":  round(result.get("win_rate_pct", 0), 1),
                    "# Trades":    int(result.get("num_trades", 0)),
                    "Avg Trade %": round(result.get("avg_trade_pct", 0), 2),
                    "Exposure %":  round(result.get("exposure_time_pct", 0), 1),
                })
            else:
                errors.append(f"{symbol}: {result.get('error', 'unknown')}")
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")

    progress.empty()
    status.empty()

    if not rows:
        st.error("沒有成功的回測結果。請確認資料庫已有資料。")
        if errors:
            with st.expander(f"⚠️ 所有 {len(errors)} 個錯誤"):
                for e in errors:
                    st.text(e)
        return None

    st.success(f"✅ 完成！成功 {len(rows)} 支，失敗 {len(errors)} 支")

    if errors:
        with st.expander(f"⚠️ {len(errors)} 支失敗"):
            for e in errors:
                st.text(e)

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Results table + drill-down
# ─────────────────────────────────────────────────────────────────────────────

def _display_results(df: pd.DataFrame, metadata: dict, data_service):
    """Render ranked results table and optional drill-down chart."""
    st.subheader("🏆 策略排名")

    # Sort controls
    s_col, a_col, _ = st.columns([2, 1, 5])
    with s_col:
        sort_by = st.selectbox(
            "排序依據",
            ["Sharpe", "Return %", "Win Rate %", "Max DD %", "Sortino", "# Trades", "Avg Trade %"],
            key="lab_sort_by"
        )
    with a_col:
        asc = st.checkbox("升序 ↑", value=(sort_by == "Max DD %"), key="lab_sort_asc")

    sorted_df = df.sort_values(sort_by, ascending=asc).reset_index(drop=True)
    sorted_df.index = sorted_df.index + 1  # rank starts at 1

    # Apply colour styling
    def _ret_color(val):
        return f"color: {'#2ecc71' if val > 0 else '#e74c3c'}; font-weight: bold"

    def _sharpe_color(val):
        if val >= 1.5:
            return "color: #2ecc71"
        elif val >= 0.5:
            return "color: #f39c12"
        return "color: #e74c3c"

    styled = (
        sorted_df.style
        .applymap(_ret_color, subset=["Return %"])
        .applymap(_sharpe_color, subset=["Sharpe"])
    )
    st.dataframe(styled, use_container_width=True, height=420)

    # ── Summary strip ────────────────────────────────────────────────────────
    st.markdown("---")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("成功回測", f"{len(df)} 支")
    m2.metric("平均報酬率", f"{df['Return %'].mean():.1f}%")
    m3.metric("最高 Sharpe", f"{df['Sharpe'].max():.2f}")
    m4.metric("勝率 > 50%", f"{(df['Win Rate %'] > 50).sum()} 支")
    m5.metric("正報酬股數", f"{(df['Return %'] > 0).sum()} 支")

    # ── Top 10 bar chart ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"📊 Top 10 — {sort_by}")
    top10 = sorted_df.head(10) if not asc else sorted_df.tail(10).iloc[::-1]
    fig_bar = go.Figure(go.Bar(
        x=top10["Symbol"],
        y=top10[sort_by],
        text=top10[sort_by],
        textposition="outside",
        marker_color=[
            "#2ecc71" if v >= 0 else "#e74c3c"
            for v in top10[sort_by]
        ]
    ))
    fig_bar.update_layout(
        height=300,
        margin=dict(t=20, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        yaxis_title=sort_by,
        showlegend=False
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Drill-down ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔍 個股深入分析")
    drill_options = sorted_df["Symbol"].tolist()
    default_idx = 0
    if "lab_drill_symbol" in st.session_state and st.session_state["lab_drill_symbol"] in drill_options:
        default_idx = drill_options.index(st.session_state["lab_drill_symbol"])

    drill_symbol = st.selectbox(
        "選擇股票查看 K 線圖",
        drill_options,
        index=default_idx,
        format_func=lambda s: f"{s} — {metadata.get(s, s)}",
        key="lab_drill_select"
    )
    st.session_state["lab_drill_symbol"] = drill_symbol

    if drill_symbol:
        _render_drill_chart(drill_symbol, data_service, sorted_df)

    # ── Download ─────────────────────────────────────────────────────────────
    st.markdown("---")
    csv = sorted_df.to_csv(index=True).encode("utf-8-sig")
    st.download_button(
        "⬇️ 下載完整結果 CSV",
        csv,
        file_name="backtest_results.csv",
        mime="text/csv",
        key="lab_download"
    )


def _render_drill_chart(symbol: str, data_service, results_df: pd.DataFrame):
    """Show OHLC candlestick + MFI for a drilled-down symbol."""
    try:
        df = data_service.get_data(symbol)
        if df.empty:
            st.warning(f"找不到 {symbol} 的資料")
            return

        # Show result row for this symbol
        row = results_df[results_df["Symbol"] == symbol]
        if not row.empty:
            row = row.iloc[0]
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("報酬率", f"{row['Return %']}%")
            c2.metric("Sharpe", f"{row['Sharpe']}")
            c3.metric("勝率", f"{row['Win Rate %']}%")
            c4.metric("最大回撤", f"{row['Max DD %']}%")
            c5.metric("交易次數", f"{int(row['# Trades'])}")

        from src.core.indicators.mfi import MFI
        mfi_ind = MFI(period=14, buy_threshold=20, sell_threshold=80)
        df["MFI"] = mfi_ind.calculate(df)

        # Use last 252 trading days (~1 year)
        df = df.tail(252)

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.03
        )

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"],
            name=symbol,
            increasing_line_color="#2ecc71",
            decreasing_line_color="#e74c3c"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df.index, y=df["MFI"],
            line=dict(color="#9b59b6", width=1.5),
            name="MFI"
        ), row=2, col=1)

        fig.add_hline(y=20, line_dash="dot", line_color="#2ecc71", row=2, col=1)
        fig.add_hline(y=80, line_dash="dot", line_color="#e74c3c", row=2, col=1)

        fig.update_layout(
            height=500,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis_rangeslider_visible=False,
            showlegend=False,
            margin=dict(t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"圖表載入失敗: {e}")
