"""
籌碼面分析 UI Component

Renders the institutional flow and margin trading section
inside the Terminal tab, below the price chart.
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def render_chip_analysis(symbol: str):
    """
    Main entry point. Call this from app.py after the price chart.
    Only renders for Taiwan stocks (.TW / .TWO).
    """
    if not (symbol.endswith(".TW") or symbol.endswith(".TWO")):
        return   # US stocks — no chip data available

    from src.utils.chip_data import get_institutional_flow, get_margin_trading, chip_summary

    st.markdown("---")
    st.subheader("🏦 籌碼面分析 (Institutional Flow)")

    summary = chip_summary(symbol)

    if not summary.get("has_data"):
        st.info(
            "⏳ 尚無籌碼資料。請先執行 `python scripts/fetch_chip_data.py` 以獲取歷史資料。\n\n"
            "GitHub Actions 每日自動更新，明天即可看到資料。"
        )
        return

    st.caption(f"資料日期：{summary['latest_date']} ｜ 單位：千股 (thousands of shares)")

    # ── Signal Cards ───────────────────────────────────────────────────────────
    _render_signal_cards(summary)

    st.markdown("---")

    # ── Two tabs: 三大法人 / 融資融券 ──────────────────────────────────────────
    tab_inst, tab_margin = st.tabs(["📊 三大法人", "💳 融資融券"])

    with tab_inst:
        inst_df = get_institutional_flow(symbol, days=30)
        if not inst_df.empty:
            _render_institutional_charts(inst_df)
        else:
            st.info("無三大法人資料")

    with tab_margin:
        margin_df = get_margin_trading(symbol, days=30)
        if not margin_df.empty:
            _render_margin_charts(margin_df, symbol)
        else:
            st.info("無融資融券資料")


# ── Signal Cards ───────────────────────────────────────────────────────────────

def _render_signal_cards(s: dict):
    """Four signal cards: 外資 / 投信 / 自營商 / 融資."""

    def _streak_label(net: float, streak: int, positive: bool) -> str:
        direction = "買超" if positive else "賣超"
        return f"{'連續' if streak > 1 else ''}{streak}日{direction}"

    def _fmt_net(val: float) -> str:
        if val is None or pd.isna(val):
            return "—"
        sign = "+" if val > 0 else ""
        return f"{sign}{val:,.0f}"

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        net = s.get("foreign_net_today", 0)
        streak = s.get("foreign_streak", 0)
        pos = s.get("foreign_positive", True)
        delta_color = "normal" if pos else "inverse"
        st.metric(
            "外資",
            _fmt_net(net),
            _streak_label(net, streak, pos),
            delta_color=delta_color,
        )

    with c2:
        net = s.get("invest_net_today", 0)
        streak = s.get("invest_streak", 0)
        pos = s.get("invest_positive", True)
        st.metric(
            "投信",
            _fmt_net(net),
            _streak_label(net, streak, pos),
            delta_color="normal" if pos else "inverse",
        )

    with c3:
        net = s.get("dealer_net_today", 0)
        streak = s.get("dealer_streak", 0)
        pos = s.get("dealer_positive", True)
        st.metric(
            "自營商",
            _fmt_net(net),
            _streak_label(net, streak, pos),
            delta_color="normal" if pos else "inverse",
        )

    with c4:
        margin_bal = s.get("margin_balance")
        margin_chg = s.get("margin_change")
        if margin_bal is not None and not pd.isna(margin_bal):
            chg_str = f"{'+' if margin_chg > 0 else ''}{margin_chg:,.0f}" if margin_chg and not pd.isna(margin_chg) else "—"
            chg_color = "inverse" if (margin_chg or 0) > 0 else "normal"  # rising margin = risk
            st.metric("融資餘額", f"{margin_bal:,.0f}", chg_str, delta_color=chg_color)
        else:
            st.metric("融資餘額", "—", "無資料")


# ── 三大法人 Charts ────────────────────────────────────────────────────────────

def _render_institutional_charts(df: pd.DataFrame):
    """
    Top: grouped net buy/sell bar chart (外資/投信/自營 net, last 20 days)
    Bottom: raw buy/sell table for latest date
    """
    plot_df = df.tail(20)

    # ── Chart 1: Net Buy/Sell grouped bars ───────────────────────────────────
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=plot_df["date"],
        y=plot_df["foreign_net"] / 1000,   # convert shares → lots (thousands)
        name="外資淨",
        marker_color=[
            "#2ecc71" if v >= 0 else "#e74c3c"
            for v in plot_df["foreign_net"]
        ],
        opacity=0.9,
    ))

    fig.add_trace(go.Bar(
        x=plot_df["date"],
        y=plot_df["invest_net"] / 1000,
        name="投信淨",
        marker_color=[
            "#3498db" if v >= 0 else "#e67e22"
            for v in plot_df["invest_net"]
        ],
        opacity=0.9,
    ))

    fig.add_trace(go.Bar(
        x=plot_df["date"],
        y=plot_df["dealer_net"] / 1000,
        name="自營商淨",
        marker_color=[
            "#9b59b6" if v >= 0 else "#95a5a6"
            for v in plot_df["dealer_net"]
        ],
        opacity=0.9,
    ))

    # Total net line
    fig.add_trace(go.Scatter(
        x=plot_df["date"],
        y=plot_df["total_net"] / 1000,
        name="三大法人合計",
        line=dict(color="#f1c40f", width=2),
        mode="lines+markers",
        marker=dict(size=4),
    ))

    fig.update_layout(
        title="三大法人 買賣超 (千股)",
        barmode="group",
        height=380,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=50, b=20),
        yaxis_title="千股",
        hovermode="x unified",
    )
    fig.add_hline(y=0, line_color="white", line_width=0.5, opacity=0.3)
    st.plotly_chart(fig, use_container_width=True)

    # ── Chart 2: Cumulative net (trend) ──────────────────────────────────────
    cum_df = df.copy()
    cum_df["foreign_cum"] = cum_df["foreign_net"].cumsum() / 1000
    cum_df["invest_cum"]  = cum_df["invest_net"].cumsum() / 1000
    cum_df["dealer_cum"]  = cum_df["dealer_net"].cumsum() / 1000

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=cum_df["date"], y=cum_df["foreign_cum"],
                              name="外資累計", line=dict(color="#2ecc71", width=2)))
    fig2.add_trace(go.Scatter(x=cum_df["date"], y=cum_df["invest_cum"],
                              name="投信累計", line=dict(color="#3498db", width=2)))
    fig2.add_trace(go.Scatter(x=cum_df["date"], y=cum_df["dealer_cum"],
                              name="自營累計", line=dict(color="#9b59b6", width=2)))
    fig2.add_hline(y=0, line_color="white", line_width=0.5, opacity=0.3)
    fig2.update_layout(
        title="三大法人 累計買賣超 (千股)",
        height=280,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=50, b=20),
        yaxis_title="千股",
        hovermode="x unified",
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Raw numbers table (last 10 days) ─────────────────────────────────────
    with st.expander("📋 原始數據 (近10日)"):
        show = df.tail(10).copy()
        show["date"] = show["date"].dt.strftime("%Y-%m-%d")
        for col in ["foreign_buy", "foreign_sell", "foreign_net",
                    "invest_buy", "invest_sell", "invest_net",
                    "dealer_buy", "dealer_sell", "dealer_net", "total_net"]:
            show[col] = (show[col] / 1000).round(1)
        show.columns = [
            "日期",
            "外資買", "外資賣", "外資淨",
            "投信買", "投信賣", "投信淨",
            "自營買", "自營賣", "自營淨",
            "合計淨"
        ]
        st.dataframe(show.sort_values("日期", ascending=False), use_container_width=True)


# ── 融資融券 Charts ────────────────────────────────────────────────────────────

def _render_margin_charts(df: pd.DataFrame, symbol: str):
    """
    Dual-chart: margin balance trend + short balance trend
    Both with day-over-day change bars on secondary axis.
    """
    plot_df = df.tail(30)

    # ── Margin (融資) ─────────────────────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.4],
        vertical_spacing=0.08,
        subplot_titles=("融資餘額", "融資增減"),
    )

    fig.add_trace(go.Scatter(
        x=plot_df["date"],
        y=plot_df["margin_balance"] / 1000,
        name="融資餘額",
        fill="tozeroy",
        line=dict(color="#e67e22", width=2),
        fillcolor="rgba(230,126,34,0.15)",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=plot_df["date"],
        y=plot_df["margin_change"] / 1000,
        name="融資增減",
        marker_color=[
            "#e74c3c" if v > 0 else "#2ecc71"   # rising margin = warning (red)
            for v in plot_df["margin_change"].fillna(0)
        ],
    ), row=2, col=1)

    fig.add_hline(y=0, row=2, col=1, line_color="white", line_width=0.5, opacity=0.3)
    fig.update_layout(
        height=380,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        showlegend=False,
        margin=dict(t=40, b=20),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="千股", row=1, col=1)
    fig.update_yaxes(title_text="千股", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # ── Short (融券) ──────────────────────────────────────────────────────────
    fig2 = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.4],
        vertical_spacing=0.08,
        subplot_titles=("融券餘額", "融券增減"),
    )

    fig2.add_trace(go.Scatter(
        x=plot_df["date"],
        y=plot_df["short_balance"] / 1000,
        name="融券餘額",
        fill="tozeroy",
        line=dict(color="#3498db", width=2),
        fillcolor="rgba(52,152,219,0.15)",
    ), row=1, col=1)

    fig2.add_trace(go.Bar(
        x=plot_df["date"],
        y=plot_df["short_change"] / 1000,
        name="融券增減",
        marker_color=[
            "#e74c3c" if v > 0 else "#2ecc71"
            for v in plot_df["short_change"].fillna(0)
        ],
    ), row=2, col=1)

    fig2.add_hline(y=0, row=2, col=1, line_color="white", line_width=0.5, opacity=0.3)
    fig2.update_layout(
        height=380,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        showlegend=False,
        margin=dict(t=40, b=20),
        hovermode="x unified",
    )
    fig2.update_yaxes(title_text="千股", row=1, col=1)
    fig2.update_yaxes(title_text="千股", row=2, col=1)
    st.plotly_chart(fig2, use_container_width=True)

    # ── Raw table ────────────────────────────────────────────────────────────
    with st.expander("📋 原始數據 (近10日)"):
        show = df.tail(10).copy()
        show["date"] = show["date"].dt.strftime("%Y-%m-%d")
        for col in ["margin_buy", "margin_sell", "margin_balance", "margin_change",
                    "short_sell", "short_buy", "short_balance", "short_change"]:
            if col in show.columns:
                show[col] = (show[col] / 1000).round(1)
        show = show[["date", "margin_buy", "margin_sell", "margin_balance", "margin_change",
                     "short_sell", "short_buy", "short_balance", "short_change"]]
        show.columns = ["日期", "融資買", "融資賣", "融資餘額", "融資增減",
                        "融券賣", "融券買", "融券餘額", "融券增減"]
        st.dataframe(show.sort_values("日期", ascending=False), use_container_width=True)
