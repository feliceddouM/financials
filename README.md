# 選股器 — 台股財報事件監控系統

> 用 vibe-coding 建一個真正在用的選股工具：自動解析 MOPS 財報、計算基本面指標、篩出值得深研的公司。

---

## 這個工具解決什麼問題

台灣上市公司每季申報財報，但從「財報公告」到「你知道這家公司值得看」之間，有一段沒人幫你做的工作：下載、解析、計算、比較。

散戶通常靠券商 APP 看摘要，或等財經 YouTuber 講，但這些都是二手資訊，時間差至少一到兩週。

**選股器** 直接從 MOPS（公開資訊觀測站）抓原始 HTML 財報，解析 XBRL 結構，計算毛利率、營業利益率、ROE、YoY 成長率等指標，再用 Quality + Value 雙維度模型篩選，輸出信號強度排序的候選清單。

目標使用者是有基本投資知識、但沒有時間自己做財報分析的上班族。

---

## 系統架構

```
MOPS 財報 (HTML/XBRL)
        ↓
parse_mops_reports.py   ← 解析 inline XBRL，計算財務指標
        ↓
financial_metrics_YYYYQN.csv
        ↓
stock_screening.ipynb   ← 計算 ROE、PE、產業中位數比較
        ↓
screening_results.csv   ← 信號強度排序輸出（⭐⭐⭐ / ⭐⭐ / ⚠️）
```

Tech stack：Python、pandas、BeautifulSoup、SQLite（規劃中）、React + FastAPI（UI，規劃中）

---

## 2026 Q1 實測結果

資料來源：MOPS 上市公司 IFRSs 後季報整批下載（民國 115 年 Q1）

- 解析公司數：**216 家**（涵蓋率 89.6%，其餘 25 家尚未申報，截止日 5/15）
- 資料品質：**complete 216 / incomplete 0 / fail 0**
- 通過篩選：**44 家**

篩選條件（v0）：營收 YoY 正成長、毛利率優於產業中位數、ROE 正值、PE 合理範圍。

---

## Vibe-Coding 開發過程：真實遇到的問題

這個工具從零開始用 Claude Code + Claude Chat 協作建立。以下是開發過程中真正卡住的地方，記錄下來作為產品迭代的依據。

**1. MOPS zip 下載無法自動化**
下載按鈕是 JavaScript 觸發，沒有直接的 href，右鍵複製不到連結。需要開 Network tab 攔截 request URL，目前仍是手動步驟。後續計畫用 requests 搭配攔截到的 URL pattern 自動化。

**2. encoding 問題：big5 失敗，cp950 才能讀**
MOPS 匯總 CSV 用 cp950 編碼，`big5` 在某些字元會噴錯。原本 `except` 直接 `pass`，導致錯誤被吃掉、難以 debug。修正：改成 `except Exception as e: print(enc, e)` 才看到真正的錯誤訊息。

**3. 欄位名稱 mismatch：`公司代號` vs `company_id`**
whitelist CSV 的公司代號欄位是中文 `公司代號`，但程式碼預設抓 `company_id`，靜默失敗，跑完沒有任何錯誤訊息但結果是空的。這是最花時間 debug 的問題。

**4. `quality` 欄位沒有輸出到 CSV**
parser 有計算 `quality`（complete / incomplete / fail），但 `col_order` 清單裡沒有包含它，所以輸出的 CSV 裡根本沒有這欄，下游 notebook 的 quality filter 直接噴 KeyError。

**5. PE ratio 需要年化**
Q1 的 `eps_ytd` 只是單季數字，直接用股價除以 Q1 EPS 會得到極端偏高的 PE（有些超過 300）。修正：`eps_annualized = eps_ytd * 4`，再計算 PE。這是選股邏輯層面的問題，不是 bug，但容易被忽略。

**6. `company_name` 在 merge 後變成 `company_name_x`**
兩個 DataFrame 都有 `company_name` 欄位，merge 之後 pandas 自動加 `_x` / `_y` suffix，下游顯示的時候找不到欄位。

---

## 已知限制與下一步

Q4 財報解析失敗（complete: 0）：年度報告的 XBRL contextRef 格式與季報不同，`make_ctx_strings` 需要針對 Q4 特別處理。

PE 用 Q1 EPS 年化只是粗估，假設四季均等，實際上各季 EPS 差異可能很大。

篩選條件 v0 偏寬，「無」信號的公司仍進入輸出清單，需要在 `screen_stocks` 加硬門檻。

下一步：建 UI 層（React + FastAPI）、實作 MOPS 事件監控（自動偵測新財報上傳）、加入 missing 公司追蹤。

---

## 專案結構

```
financials/
├── code/                    # Python 模組
│   ├── parse_mops_reports.py
│   ├── calculate_metrics.py
│   ├── fetch_stock_price.py
│   └── screening.py
├── notebooks/               # Jupyter notebooks
│   ├── parse_mops_reports.ipynb
│   └── stock_screening.ipynb
└── data/
    ├── raw/                 # MOPS 原始檔案
    │   ├── tifrs-2026Q1/
    │   └── industry_mapping.csv
    └── processed/           # 輸出
        ├── financial_metrics_2026Q1.csv
        └── screening_results.csv
```

---

*這是一個持續迭代的作品集專案。*
