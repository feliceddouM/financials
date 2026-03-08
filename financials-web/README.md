# 台灣股市財報分析平台

個人投資者用的台股財報 Web 分析工具，基於公開資訊觀測站（MOPS）資料。

## 功能

- 📋 **公司財務總覽** — 搜尋任一公司，查看歷史財務趨勢與 KPI
- 🔍 **選股篩選器** — 依毛利率、EPS、YoY 成長率等條件篩選股票
- ⚖️ **同業比較** — 與同產業公司財務指標對比、雷達圖視覺化

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 準備資料

從 MOPS 下載季報 HTML 壓縮包並解壓，然後執行解析：

```bash
# 一鍵更新（解析 + 載入資料庫）
python pipeline/run_quarter.py \
    --html-dir /path/to/tifrs-2025Q3 \
    --whitelist /path/to/t163sb04_20251218.csv \
    --quarter 2025Q3 \
    --fetch-companies
```

或分步執行：

```bash
# Step 1: 解析 HTML → CSV
python pipeline/parse_mops_reports.py \
    /path/to/t163sb04.csv \
    /path/to/tifrs-2025Q3 \
    financial_metrics_2025Q3.csv

# Step 2: 載入 CSV → SQLite
python pipeline/db_loader.py \
    --csv financial_metrics_2025Q3.csv \
    --fetch-companies
```

### 3. 啟動應用

```bash
streamlit run app.py
```

瀏覽器開啟 http://localhost:8501

## 資料說明

- 財務數字單位：百萬元台幣（EPS 為元）
- 資料來源：公開資訊觀測站（MOPS）inline XBRL 格式財報
- 支援季度：2025Q2、2025Q3（可持續新增）

## 專案結構

```
financials-web/
├── app.py                 ← Streamlit 主入口
├── pages/
│   ├── 1_company.py       ← 公司財務總覽
│   ├── 2_screener.py      ← 選股篩選器
│   └── 3_peers.py         ← 同業比較
├── utils/
│   ├── db.py              ← 資料庫查詢 helper
│   ├── charts.py          ← Plotly 圖表函式
│   └── format.py          ← 數字格式化工具
├── pipeline/
│   ├── parse_mops_reports.py  ← HTML 解析器（來自 Working Files）
│   ├── db_loader.py           ← CSV → SQLite 載入器
│   └── run_quarter.py         ← 一鍵更新腳本
└── data/
    └── financials.db      ← SQLite 資料庫
```

## 新增季度資料

每季財報公告後：

1. 從 MOPS 下載新季度 HTML 壓縮包
2. 執行 `python pipeline/run_quarter.py --html-dir ... --whitelist ... --quarter 2025Q4`
3. 重新整理 Streamlit 頁面

## 部署給朋友（Streamlit Community Cloud）

1. 將 `data/financials.db` 推送至私有 GitHub repo
2. 在 share.streamlit.io 連結 repo 並設定 `app.py` 為入口
3. 分享連結給朋友即可使用（免費，需登入 GitHub 帳號）
