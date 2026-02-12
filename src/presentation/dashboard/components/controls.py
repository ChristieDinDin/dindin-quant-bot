"""
UI controls and input components.
"""
import streamlit as st
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.utils.stock_list import (
    load_stock_metadata, 
    get_stocks_by_category,
    get_available_stocks_from_db
)
from src.utils.watchlist_manager import (
    load_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    is_in_watchlist
)


def create_sidebar_controls() -> dict:
    """
    Create sidebar controls for strategy parameters.
    
    Returns:
        Dict with all control values
    """
    st.sidebar.header("🛠️ 策略參數 (Settings)")
    
    # === IMPROVED STOCK SELECTION ===
    st.sidebar.subheader("📊 選股")
    
    # Load available stocks from database and metadata
    metadata = load_stock_metadata()
    
    # Get stocks from database (what you actually have data for)
    db_stocks = get_available_stocks_from_db()
    available_symbols = [row[0] for row in db_stocks] if db_stocks else []
    
    # If no DB stocks, use metadata
    if not available_symbols:
        available_symbols = list(metadata.keys())
    
    # Selection mode
    selection_mode = st.sidebar.radio(
        "選股方式",
        ["⭐ 自選股", "🔍 搜尋", "📁 分類"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if selection_mode == "⭐ 自選股":
        # Import watchlist manager
        from src.utils.watchlist_manager import (
            load_watchlist, add_to_watchlist, remove_from_watchlist
        )
        
        # Load user's custom watchlist
        watchlist_symbols = load_watchlist()
        watchlist_available = [s for s in watchlist_symbols if s in available_symbols]
        
        if not watchlist_available:
            watchlist_available = available_symbols[:5]  # Default to first 5
        
        # Stock selector
        symbol = st.sidebar.selectbox(
            "我的自選股",
            watchlist_available,
            format_func=lambda x: f"{x} - {metadata.get(x, x.replace('.TW', ''))}",
            help="您常用的股票清單"
        )
        
        # Watchlist management buttons (stacked vertically for full stock names)
        # Add stock to watchlist
        with st.sidebar.expander("➕ 加入自選股"):
            add_symbol = st.selectbox(
                "選擇要加入的股票",
                [s for s in available_symbols if s not in watchlist_symbols],
                format_func=lambda x: f"{x} - {metadata.get(x, '')}",
                key="add_to_watchlist",
                label_visibility="collapsed"
            )
            if st.button("✅ 加入", key="add_btn", use_container_width=True):
                if add_to_watchlist(add_symbol):
                    st.success(f"已加入 {add_symbol}")
                    st.rerun()
        
        # Remove stock from watchlist
        with st.sidebar.expander("➖ 移除自選股"):
            if watchlist_available:
                remove_symbol = st.selectbox(
                    "選擇要移除的股票",
                    watchlist_available,
                    format_func=lambda x: f"{x} - {metadata.get(x, '')}",
                    key="remove_from_watchlist",
                    label_visibility="collapsed"
                )
                if st.button("🗑️ 移除", key="remove_btn", use_container_width=True):
                    if remove_from_watchlist(remove_symbol):
                        st.success(f"已移除 {remove_symbol}")
                        st.rerun()
            else:
                st.caption("自選股是空的")
    
    elif selection_mode == "🔍 搜尋":
        # Search with autocomplete
        search_query = st.sidebar.text_input(
            "🔍 搜尋",
            placeholder="台積電, 2330, TSMC...",
            help="輸入代碼或公司名稱",
            label_visibility="collapsed"
        )
        
        if search_query:
            # Filter stocks
            query_upper = search_query.upper()
            filtered = [
                s for s in available_symbols
                if query_upper in s.upper() or query_upper in metadata.get(s, '').upper()
            ]
            
            if filtered:
                symbol = st.sidebar.selectbox(
                    f"找到 {len(filtered)} 檔股票",
                    filtered,
                    format_func=lambda x: f"{x} - {metadata.get(x, '')}",
                )
            else:
                st.sidebar.warning("找不到，請直接輸入代碼")
                symbol = st.sidebar.text_input("代碼", value="2330.TW", label_visibility="collapsed")
        else:
            # Show all available stocks with search
            symbol = st.sidebar.selectbox(
                f"所有股票 ({len(available_symbols)} 檔)",
                available_symbols,
                format_func=lambda x: f"{x} - {metadata.get(x, '')}",
                help="點擊後可輸入搜尋"
            )
    
    else:  # 📁 分類
        # Browse by category
        category = st.sidebar.radio(
            "類別",
            ["blue_chips", "technology", "financial"],
            format_func=lambda x: {
                "blue_chips": "🏆 藍籌股",
                "technology": "💻 科技",
                "financial": "💰 金融"
            }.get(x, x),
            horizontal=True,
            label_visibility="collapsed"
        )
        
        category_stocks = get_stocks_by_category(category)
        category_available = [s for s in category_stocks.keys() if s in available_symbols]
        
        if category_available:
            symbol = st.sidebar.selectbox(
                f"{category} ({len(category_available)} 檔)",
                category_available,
                format_func=lambda x: f"{x} - {metadata.get(x, category_stocks.get(x, ''))}",
            )
        else:
            st.sidebar.warning("此類別暫無資料")
            symbol = available_symbols[0] if available_symbols else "2330.TW"
    
    # Strategy selection
    st.sidebar.subheader("策略選擇")
    strategy_name = st.sidebar.selectbox(
        "交易策略",
        ["mfi_hunter", "rsi_mfi_consensus"],
        format_func=lambda x: {
            "mfi_hunter": "🎯 MFI Hunter (單一指標)",
            "rsi_mfi_consensus": "🤝 RSI+MFI Consensus (雙重確認)"
        }.get(x, x),
        help="選擇使用的交易策略"
    )
    
    # Strategy-specific parameters
    st.sidebar.subheader("指標參數")
    
    if strategy_name == "mfi_hunter":
        # MFI Hunter parameters
        mfi_period = st.sidebar.slider(
            "MFI 天數",
            min_value=7,
            max_value=30,
            value=16,
            help="計算 MFI 的回看期間"
        )
        
        buy_level = st.sidebar.slider(
            "買進門檻 (Buy <)",
            min_value=10,
            max_value=50,
            value=35,
            help="MFI 低於此值產生買進訊號"
        )
        
        sell_level = st.sidebar.slider(
            "賣出門檻 (Sell >)",
            min_value=60,
            max_value=95,
            value=85,
            help="MFI 高於此值產生賣出訊號"
        )
        
        # Placeholder for other params
        rsi_period = 14
        rsi_oversold = 30
        rsi_overbought = 70
        
    elif strategy_name == "rsi_mfi_consensus":
        # RSI + MFI Consensus parameters
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            rsi_period = st.sidebar.slider(
                "RSI 天數",
                min_value=7,
                max_value=30,
                value=14,
                help="RSI 計算期間"
            )
            
            rsi_oversold = st.sidebar.slider(
                "RSI 超賣",
                min_value=20,
                max_value=40,
                value=30,
                help="RSI 低於此值視為超賣"
            )
            
            rsi_overbought = st.sidebar.slider(
                "RSI 超買",
                min_value=60,
                max_value=80,
                value=70,
                help="RSI 高於此值視為超買"
            )
        
        with col2:
            mfi_period = st.sidebar.slider(
                "MFI 天數",
                min_value=7,
                max_value=30,
                value=14,
                help="MFI 計算期間"
            )
            
            buy_level = st.sidebar.slider(
                "MFI 超賣",
                min_value=20,
                max_value=50,
                value=35,
                help="MFI 低於此值視為超賣"
            )
            
            sell_level = st.sidebar.slider(
                "MFI 超買",
                min_value=60,
                max_value=95,
                value=85,
                help="MFI 高於此值視為超買"
            )
    
    else:
        # Default values
        mfi_period = 16
        buy_level = 35
        sell_level = 85
        rsi_period = 14
        rsi_oversold = 30
        rsi_overbought = 70
    
    # Backtesting parameters
    st.sidebar.subheader("回測設定")
    
    initial_cash = st.sidebar.number_input(
        "初始資金",
        min_value=100_000,
        max_value=10_000_000,
        value=1_000_000,
        step=100_000,
        help="回測起始資金（新台幣）"
    )
    
    commission = st.sidebar.number_input(
        "交易手續費 (%)",
        min_value=0.0,
        max_value=1.0,
        value=0.1425,
        step=0.01,
        help="單邊交易手續費率"
    )
    
    return {
        'symbol': symbol,
        'strategy_name': strategy_name,
        'mfi_period': mfi_period,
        'buy_level': buy_level,
        'sell_level': sell_level,
        'rsi_period': rsi_period,
        'rsi_oversold': rsi_oversold,
        'rsi_overbought': rsi_overbought,
        'initial_cash': initial_cash,
        'commission': commission / 100  # Convert to decimal
    }


def create_stock_search() -> str:
    """
    Create stock search input.
    
    Returns:
        Selected or input symbol
    """
    search_mode = st.radio(
        "選股方式",
        ["熱門股票", "手動輸入"],
        horizontal=True
    )
    
    if search_mode == "熱門股票":
        symbol = st.selectbox(
            "選擇股票",
            ["2330.TW (台積電)", "2337.TW (光磊)", "6944.TW (兆聯實業)"]
        )
        # Extract symbol code
        symbol = symbol.split()[0]
    else:
        symbol = st.text_input(
            "輸入股票代號",
            value="2337.TW",
            help="格式：代號.TW (例如：2330.TW)"
        )
    
    return symbol
