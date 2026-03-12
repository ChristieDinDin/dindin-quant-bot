# Divergence Hunter 策略規格 (Spec)

## 一、流程概覽

```
階段 1: 日 K 監測（無持倉）
    └→ 條件 A–F 全部滿足 → 啟動 1 分 K 微觀模式

階段 2: 1 分 K 微觀（等待進場）
    └→ 條件 G 滿足 → 買入（記錄 entry_price, divergence_low, peak_price）

階段 3: 1 分 K 微觀（持倉中）
    └→ 條件 H1–H6 任一滿足 → 賣出
```

---

## 二、階段 1：日 K 監測（無持倉）

**資料來源**：日 K  
**觸發**：以下 **A–F 須全部滿足**，才啟動 5 分 K 微觀模式。

### 前置：Swing Pivot 定義

| 項目 | 條件 |
|------|------|
| Swing Low | `low[i] == min(low[i-N : i+N+1])`，N = 5 |
| Swing High | `high[i] == max(high[i-N : i+N+1])`，N = 5 |
| Pivot 間距 | 相鄰 pivot 至少間隔 8 bars |
| Lookback | 取最近 LOOKBACK_WINDOW (30) + PIVOT_WINDOW (5) × 2 內資料 |

### 條件 A：底背離 Setup

| # | 條件 | 說明 |
|---|------|------|
| A1 | 存在兩個 swing low：(prev_idx, prev_low_val)、(curr_idx, curr_low_val) | 由 `find_last_two_swing_lows` 取得 |
| A2 | `curr_low_val < prev_low_val` | 價創新低 |
| A3 | `curr_mfi_val > prev_mfi_val` | MFI 未創新低（背離成立）|
| A4 | `prev_mfi_val`、`curr_mfi_val` 皆非 NaN | 數值有效 |

### 條件 B：訊號新鮮度

| # | 條件 | 說明 |
|---|------|------|
| B1 | `(當前 bar 索引 - curr_idx) ≤ 8` | 背離 bar 在近 8 日內（Pivot 確認後有更寬裕的等待窗口）|

### 條件 C：RSI 過濾（買入門檻）

| # | 條件 | 說明 |
|---|------|------|
| C1 | `rsi[curr_idx] < rsi_oversold`（預設 40）| 背離當下 RSI 低於超賣門檻 |
| C2 | `rsi[curr_idx]` 非 NaN | 數值有效 |

### 條件 D：右側確認

| # | 條件 | 說明 |
|---|------|------|
| D1 | `Close[今日] > High[昨日]` | 收盤站上昨日最高 |

### 條件 E：盤整環境過濾（Regime Filter）

> **目的**：避免在系統性下跌趨勢中反覆接刀。只在非趨勢（死水箱型）環境下發出買點。

| # | 條件 | 說明 |
|---|------|------|
| E1 | `ADX(14) < 30` | ADX 衡量趨勢強度（不分方向）。≥30 代表明確趨勢（漲跌皆算），拒絕進場 |
| E2 | `\|MA20_slope\| < 5%`（10 bar 內）| 20MA 在最近 10 個交易日的變動幅度 < 5%，代表均線趨近水平 |

**降級處理**：若 `pandas_ta` 未安裝或資料不足導致 ADX / slope 為 NaN，過濾器自動略過（不阻擋訊號），保持向後相容。

### 條件 E3：流動性過濾（Liquidity Filter）

> **目的**：殭屍股成交稀疏，單一大單即可讓 MFI 暴衝，製造假背離。過濾掉近期流動性不足的股票。

| # | 條件 | 說明 |
|---|------|------|
| E3 | 近 20 日平均每日成交值 ≥ 10M TWD | `mean(Close × Volume, 20) ≥ 10,000,000` |

**設計選擇**：以成交「金額」而非「張數」為門檻，高價股與低價股用同一標準衡量。與 DB 准入的 ≥20M TWD 過濾器一致，但採更寬鬆的 10M 作為動態即時檢查。**降級處理**：數值為 NaN 時自動略過。

### 條件 F：資料足夠

| # | 條件 | 說明 |
|---|------|------|
| F1 | `len(df) ≥ LOOKBACK_WINDOW + SWING_PIVOT_WINDOW × 2` | 至少 40 筆日 K |
| F2 | `current_rsi`、`current_mfi` 皆非 NaN | 指標有效 |

### 條件 G：無持倉

| # | 條件 | 說明 |
|---|------|------|
| G1 | 系統無該標的持倉 | 若已持倉則不進入階段 2 |

---

## 三、階段 2：1 分 K 微觀（等待進場）

**資料來源**：1 分 K（僅在階段 1 達標後抓取，不做 resample）  
**觸發**：條件 G 滿足 → 買入。

### 條件 G：進場訊號

| # | 條件 | 說明 |
|---|------|------|
| G1 | 階段 1 已達標（今日或前一交易日）| 日 K 背離 confirmation 有效 |
| G2 | 當前 1 分 K 收盤價 > 昨日日 K 最高價 | 突破昨日高點 |
| G3 | 連續 N 根 1 分 K 收盤皆 > 昨日日 K 最高 | 降低假突破（N=10，對應 5 分 K 的嚴格度）|

**買入時記錄**：
- `entry_price`：買入價
- `divergence_low`：背離低點（來自階段 1）
- `peak_price`：買入價（初始化）

---

## 四、階段 3：1 分 K 微觀（持倉中）

**資料來源**：1 分 K  
**觸發**：**H1–H6 任一**滿足 → 賣出。檢查順序：H1 → H2 → H3 → H4；H5、H6 僅在未觸發停損/停利時檢查。

### 條件 H0：最大虧損停損（Max Loss Cap）

| # | 條件 | 說明 |
|---|------|------|
| H0a | 持倉中 | — |
| H0b | `(Close - entry_price) / entry_price ≤ -0.07` | 從進場價下跌 ≥ 7% |

> 優先於 H1 檢查。防止背離低點距進場太遠的設置造成 -10% ~ -15% 的過大損失。  
> -7% 設計依據：台股盤整期正常震盪 2–4%/日，-7% 已涵蓋 2–3 天正常回測噪訊，再往下代表突破明確失敗。

### 條件 H1：硬停損

| # | 條件 | 說明 |
|---|------|------|
| H1a | 持倉中 | — |
| H1b | `divergence_low` 已記錄 | 來自買入訊號 |
| H1c | `Close[當前 1 分 K] < divergence_low × 0.99` | 跌破背離低點（1% 緩衝）|

### 條件 H2：移動停利

| # | 條件 | 說明 |
|---|------|------|
| H2a | 持倉中 | — |
| H2b | 曾有 `profit_pct > 0.15`（任一 bar）| 曾獲利超過 15% |
| H2c | `peak_price` = 持倉期間所有 bar 的 `max(High, Close)` | 含盤中高點 |
| H2d | `(peak_price - Close) / peak_price ≥ 0.05` | 從高點回跌 ≥ 5% |

### 條件 H3：時間停損（5% < 獲利 ≤ 15%）

| # | 條件 | 說明 |
|---|------|------|
| H3a | 持倉中 | — |
| H3b | `0.05 < profit_pct ≤ 0.15` | 獲利區間 |
| H3c | `days_held ≥ 20`（日曆天）| 持倉達 20 日 |

### 條件 H4：時間停損（獲利 ≤ 5% 或虧損）

| # | 條件 | 說明 |
|---|------|------|
| H4a | 持倉中 | — |
| H4b | `profit_pct ≤ 0.05` | 獲利 ≤ 5% 或虧損 |
| H4c | `days_held ≥ 10`（日曆天）| 持倉達 10 日 |

### 條件 H5：頂背離（選配，策略賣出）

| # | 條件 | 說明 |
|---|------|------|
| H5a | 持倉中 | — |
| H5b | 存在兩個 swing high | 由 `find_last_two_swing_highs` 取得 |
| H5c | `curr_high_val > prev_high_val` | 價創高 |
| H5d | `curr_mfi < prev_mfi` | MFI 未創高 |
| H5e | MFI 數值有效 | 非 NaN |

### 條件 H6：RSI 賣出（選配，可由 UI 關閉）

| # | 條件 | 說明 |
|---|------|------|
| H6a | 持倉中 | — |
| H6b | `use_rsi_sell == True` | UI 啟用 RSI 賣出 |
| H6c | `RSI[當前 bar] ≥ rsi_overbought`（預設 70）| RSI 超買 |

---

## 五、參數一覽

| 參數 | 預設 | 說明 |
|------|------|------|
| SWING_PIVOT_WINDOW | 5 | Pivot 偵測視窗（前後各 5 根）|
| MIN_BARS_BETWEEN_PIVOTS | 8 | 相鄰 pivot 最小間距 |
| LOOKBACK_WINDOW | 30 | 回溯 bar 數 |
| SIGNAL_FRESHNESS_BARS | 8 | 背離 freshness 天數（Pivot 確認後的有效等待窗口）|
| rsi_oversold | 40 | 買入 RSI 門檻 |
| rsi_overbought | 70 | RSI 賣出門檻 |
| use_rsi_sell | True | 是否啟用 RSI 賣出 |
| position_pct | 0.15 | 建議部位比例 |
| min_consecutive_bars_above | 10 | 1 分 K 進場：連續 N 根收盤 > 昨日高 |
| micro_mode_max_symbols | 5 | 微觀模式最大監控檔數 |
| poll_interval_min | 5 | 第 1–4 檔輪詢間隔（分鐘）|
| poll_interval_5th_min | 6 | 第 5 檔輪詢間隔（分鐘，rate limit buffer）|
| REGIME_ADX_PERIOD | 14 | ADX 計算週期 |
| REGIME_ADX_MAX | 30 | ADX 上限：≥30 視為趨勢市場，拒絕進場 |
| REGIME_MA_PERIOD | 20 | Regime 用 MA 週期（月線）|
| REGIME_MA_LOOKBACK | 10 | MA 斜率比較視窗（10 個交易日）|
| REGIME_MA_SLOPE_MAX | 0.05 | MA 斜率上限：10 日內變動 ≥ 5% 視為趨勢，拒絕進場 |
| LIQUIDITY_LOOKBACK | 20 | 流動性過濾用滾動視窗（交易日）|
| LIQUIDITY_MIN_TWD | 10,000,000 | 近 20 日平均每日成交值下限（TWD）|

---

## 六、實作狀態

| 項目 | 狀態 |
|------|------|
| 階段 1（日 K）| ✅ 已實作 |
| 階段 1（Regime Filter — ADX + MA slope）| ✅ 已實作 |
| 階段 1（Liquidity Filter — 20 日平均成交值 ≥ 10M TWD）| ✅ 已實作 |
| 階段 2（1 分 K 進場）| ✅ IntradayMonitor + Shioaji 1-min |
| 階段 3（H1–H4 停損/停利）| ✅ 已實作（日 K 回測 + IntradayMonitor）|
| 階段 3（H5 頂背離）| ✅ 已實作 |
| 階段 3（H6 RSI 賣出）| ✅ 已實作（可關閉）|
| 重複買入防護（同一持倉期間只允許一次進場）| ✅ 已實作 |
