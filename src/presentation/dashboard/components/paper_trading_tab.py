"""
Paper Trading Tab — automatic strategy simulation (no manual order entry).

Flow:
  1. [執行今日掃描] button → runs DivergenceHunterStrategy on every DB symbol
     → opens paper positions for confirmed BUY signals
     → updates existing positions with latest close prices
     → fires stop/take-profit exits automatically
  2. Dashboard refreshes to show open positions, closed trade log,
     equity curve, and performance stats.
  3. All logic is identical to the live IntraydayMonitor; only order submission
     is replaced by PaperTradingService.open_position().
"""
from __future__ import annotations

from datetime import date
from typing import Dict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

EXIT_REASON_ZH: Dict[str, str] = {
    "max_loss_stop":           "最大虧損停損（-7%）",
    "hard_stop":               "硬停損（跌破背離低點）",
    "trailing_stop":           "移動停利",
    "time_stop_20d":           "時間停損 20 日",
    "time_stop_10d":           "時間停損 10 日",
    "bearish_div":             "頂背離賣出",
    "rsi_overbought":          "RSI 超買",
    "force_close_replacement": "強制平倉（替換）",
    "manual":                  "手動平倉",
}


def _fmt_pct(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"


def _render_scan_result(result: dict) -> None:
    """Render the summary block for a completed scan."""
    st.subheader("📊 最新掃描結果")
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("掃描標的數", result.get("scanned", "—"))
    rc2.metric("新進場",     len(result.get("new_entries", [])))
    rc3.metric("自動出場",   len(result.get("auto_exits",  [])))
    rc4.metric("跳過（滿倉）", len(result.get("skipped",   [])))

    if result.get("new_entries"):
        st.success("✅ 新進場訊號")
        for e in result["new_entries"]:
            st.markdown(
                f"• **{e['symbol']}** ＠ {e['entry_price']:.2f}　"
                f"{e['shares']} 股（零股）　部位 {e['position_pct']*100:.0f}%　"
                f"分數 {e['signal_score']:.2f}  \n"
                f"　　*{e.get('reason', '')}*"
            )
    else:
        st.info("本次掃描無新買入訊號（或持倉已滿 5 檔）。")

    if result.get("auto_exits"):
        st.warning("🚨 自動觸發出場")
        for t in result["auto_exits"]:
            reason_zh = EXIT_REASON_ZH.get(t["exit_reason"], t["exit_reason"])
            emoji = "✅" if t["pnl_twd"] >= 0 else "🔴"
            st.markdown(
                f"• {emoji} **{t['symbol']}** — {reason_zh}　"
                f"P&L {t['pnl_twd']:+,.0f} TWD ({_fmt_pct(t['pnl_pct'])})"
            )

    if result.get("errors"):
        with st.expander(f"⚠️ 處理失敗 ({len(result['errors'])} 個)", expanded=False):
            for sym, err in result["errors"]:
                st.caption(f"`{sym}`: {err}")


def render_paper_trading_tab(paper_service, data_service) -> None:
    """Main entry point — called from app.py inside the 📋 模擬單 tab."""
    from datetime import date as _date

    st.header("📋 模擬單（自動模擬）")
    st.caption(
        "使用真實市場資料，全自動模擬底背離策略進出場。**不實際下單。**  \n"
        "初始資金 **70,000 TWD** · 動態部位 **5–20%** · 最多同時持有 **5** 檔"
    )

    # ── Status banner: last scan time ────────────────────────────────────────
    last_summary = paper_service.get_last_scan_summary()
    last_date    = paper_service._state.get("last_scan_date", "")
    today_str    = _date.today().isoformat()
    already_done = last_date == today_str

    if already_done:
        st.success(
            f"✅ 今日掃描已完成（由 GitHub Actions 自動執行）　"
            f"最後更新：{last_summary.get('run_at', last_date)}"
        )
    else:
        st.warning(
            f"⚠️ 今日尚未掃描（上次：{last_date or '從未'}）。  \n"
            "GitHub Actions 每個交易日 06:30 TWD 自動執行。  \n"
            "如需立即更新，請按下方「🔍 立即執行掃描」。"
        )

    # ── Action bar ────────────────────────────────────────────────────────────
    col_scan, col_close_all, col_reset, _ = st.columns([1.6, 1.4, 1, 3])
    with col_scan:
        btn_label = "🔍 立即執行掃描" if not already_done else "🔄 重新執行掃描"
        do_scan = st.button(btn_label, use_container_width=True,
                            type="primary" if not already_done else "secondary")
    with col_close_all:
        do_close_all = st.button("📤 全部平倉（收盤價）", use_container_width=True)
    with col_reset:
        do_reset = st.button("🗑️ 重置帳戶", use_container_width=True, type="secondary")

    if do_reset:
        paper_service.reset()
        st.success("模擬帳戶已重置為 70,000 TWD。")
        st.rerun()

    if do_close_all:
        open_positions = paper_service.get_open_positions()
        if not open_positions:
            st.info("目前無持倉。")
        else:
            with st.spinner("抓取收盤價並平倉…"):
                for pos in list(open_positions):
                    sym = pos["symbol"]
                    try:
                        df = data_service.get_data(sym)
                        price = float(df["Close"].iloc[-1]) if df is not None and not df.empty else pos["entry_price"]
                    except Exception:
                        price = pos["entry_price"]
                    paper_service.close_position(sym, price, reason="manual")
            st.success("所有持倉已按最新收盤價平倉。")
            st.rerun()

    # ── Manual / fallback scan ────────────────────────────────────────────────
    if do_scan:
        progress_bar = st.progress(0, text="初始化掃描…")
        status_text  = st.empty()

        def on_progress(current: int, total: int, symbol: str) -> None:
            pct = int(current / max(total, 1) * 100)
            progress_bar.progress(pct, text=f"掃描中 {current}/{total}：{symbol}")
            status_text.caption(f"正在分析 `{symbol}`…")

        with st.spinner("執行底背離掃描 + 更新持倉…"):
            result = paper_service.run_daily_scan(
                data_service=data_service,
                max_positions=5,
                progress_cb=on_progress,
            )

        progress_bar.empty()
        status_text.empty()
        last_summary = result
        st.rerun()   # refresh to pick up updated state

    # ── Last scan result (always shown after a scan exists) ───────────────────
    if last_summary:
        st.markdown("---")
        _render_scan_result(last_summary)

    # ── Summary cards (always visible) ───────────────────────────────────────
    st.markdown("---")
    summary = paper_service.get_summary()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        delta_str = f"{_fmt_pct(summary['total_pnl_pct'])} / {summary['total_pnl_twd']:+,.0f}"
        st.metric("總資產", f"{summary['current_equity']:,.0f} TWD", delta=delta_str)
    with c2:
        st.metric("可用現金", f"{summary['cash']:,.0f} TWD")
    with c3:
        st.metric(
            "持倉未實現 P&L",
            f"{summary['open_pnl_twd']:+,.0f} TWD",
            delta=f"{summary['open_count']} 個持倉",
        )
    with c4:
        st.metric(
            "完成交易", f"{summary['total_trades']} 筆",
            delta=f"勝率 {summary['win_rate']:.1f}%",
        )
    with c5:
        pf = summary["profit_factor"]
        pf_str = f"{pf:.2f}" if pf != float("inf") else "∞"
        st.metric(
            "Profit Factor", pf_str,
            delta=f"均盈 {_fmt_pct(summary['avg_win_pct'])} / 均虧 {_fmt_pct(summary['avg_loss_pct'])}",
        )

    # ── Open positions table ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📂 持倉中")

    open_positions = paper_service.get_open_positions()
    if not open_positions:
        st.info("目前無持倉。按「執行今日掃描」開始自動模擬。")
    else:
        rows = []
        for pos in open_positions:
            sym         = pos["symbol"]
            entry       = pos["entry_price"]
            peak        = pos["peak_price"]
            entry_date  = pos["entry_date"]
            days_held   = (date.today() - date.fromisoformat(entry_date)).days
            cost        = entry * pos["shares"]
            # Latest price not fetched here (only updated on scan); use entry as placeholder
            pnl_t = 0.0
            pnl_p = 0.0
            rows.append({
                "股票":       sym,
                "進場日":     entry_date,
                "持倉天數":   days_held,
                "進場價":     entry,
                "最高價（峰）": peak,
                "股數":        pos["shares"],
                "成本 (TWD)": f"{cost:,.0f}",
                "訊號分數":   f"{pos['signal_score']:.2f}",
                "部位 %":     f"{pos['position_pct']*100:.0f}%",
                "背離低點":   pos["divergence_low"],
                "硬停損":     f"{pos['divergence_low'] * 0.99:.2f}",
                "-7% 停損":   f"{entry * 0.93:.2f}",
            })
        df_open = pd.DataFrame(rows)
        st.dataframe(df_open, use_container_width=True, hide_index=True)

        # Per-symbol manual close buttons
        st.caption("手動強制平倉（以最後一次掃描收盤價）：")
        btn_cols = st.columns(min(len(open_positions), 5))
        for i, pos in enumerate(open_positions):
            sym = pos["symbol"]
            with btn_cols[i % 5]:
                if st.button(f"強平 {sym}", key=f"force_close_{sym}", use_container_width=True):
                    try:
                        df = data_service.get_data(sym)
                        price = float(df["Close"].iloc[-1]) if df is not None and not df.empty else pos["entry_price"]
                    except Exception:
                        price = pos["entry_price"]
                    trade = paper_service.close_position(sym, price, "manual")
                    if trade:
                        st.success(
                            f"{sym} 手動平倉 @ {price:.2f}　"
                            f"P&L {trade['pnl_twd']:+,.0f} TWD ({_fmt_pct(trade['pnl_pct'])})"
                        )
                        st.rerun()

    # ── Closed trades table ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📜 完成交易紀錄")

    closed = paper_service.get_closed_trades()
    if not closed:
        st.info("尚無已完成交易。")
    else:
        df_closed = pd.DataFrame(closed)
        df_closed["出場原因"] = df_closed["exit_reason"].map(
            lambda r: EXIT_REASON_ZH.get(r, r)
        )
        display_map = {
            "symbol":       "股票",
            "entry_date":   "進場日",
            "exit_date":    "出場日",
            "entry_price":  "進場價",
            "exit_price":   "出場價",
            "shares":       "股數",
            "pnl_twd":      "P&L (TWD)",
            "pnl_pct":      "P&L %",
            "出場原因":     "出場原因",
            "signal_score": "訊號分數",
        }
        df_show = df_closed.rename(columns=display_map)[list(display_map.values())]
        df_show["P&L (TWD)"] = df_show["P&L (TWD)"].apply(lambda x: f"{x:+,.0f}")
        df_show["P&L %"]     = df_show["P&L %"].apply(_fmt_pct)
        df_show["訊號分數"]  = df_show["訊號分數"].apply(lambda x: f"{x:.2f}")
        st.dataframe(df_show, use_container_width=True, hide_index=True)

    # ── Equity curve ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📈 資產曲線")

    eq_curve = paper_service.get_equity_curve()
    if len(eq_curve) < 2:
        st.info("執行至少兩次掃描後，資產曲線將顯示在此。")
    else:
        df_eq = pd.DataFrame(eq_curve)
        df_eq["date"] = pd.to_datetime(df_eq["date"])
        df_eq = df_eq.drop_duplicates("date").sort_values("date")

        initial = paper_service._state["initial_equity"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_eq["date"],
            y=df_eq["equity"],
            mode="lines+markers",
            name="資產",
            line=dict(color="#00c896", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,200,150,0.08)",
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.0f} TWD<extra></extra>",
        ))
        fig.add_hline(
            y=initial, line_dash="dash", line_color="gray",
            annotation_text=f"初始 {initial:,.0f}",
            annotation_position="bottom right",
        )
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=20, b=20),
            xaxis_title=None,
            yaxis_title="TWD",
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Win / loss bar chart
        if closed:
            winners = [t for t in closed if t["pnl_twd"] > 0]
            losers  = [t for t in closed if t["pnl_twd"] <= 0]
            fig2 = go.Figure(data=[
                go.Bar(name="獲利", x=["交易統計"], y=[len(winners)], marker_color="#00c896"),
                go.Bar(name="虧損", x=["交易統計"], y=[len(losers)],  marker_color="#ff4b4b"),
            ])
            fig2.update_layout(
                barmode="group", height=220,
                margin=dict(l=10, r=10, t=10, b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── Strategy parameter reference ──────────────────────────────────────────
    with st.expander("⚙️ 模擬參數參考", expanded=False):
        st.markdown("""
| 參數 | 數值 |
|---|---|
| 初始資金 | 70,000 TWD |
| 最大同時持倉 | 5 檔 |
| 動態部位大小 | 5%（弱訊號）— 20%（強訊號） |
| 最大虧損停損 | -7%（從進場價） |
| 硬停損 | 背離低點 × 0.99 |
| 移動停利觸發 | 獲利 ≥ 15% |
| 移動停利出場 | 從最高點回落 5% |
| 時間停損 | 持倉 ≥ 10 日且獲利 < 5%；或 ≥ 20 日且獲利 5–15% |
| 手續費（模擬） | 0.40%（來回，含折扣+稅） |
| 資料來源 | 本地 DB（yfinance） |
        """)
