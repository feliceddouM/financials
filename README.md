# 台灣上市櫃公司財報自動化解析工具

## 專案概述

這是一個從公開資訊觀測站(MOPS)下載的 inline XBRL 格式財報 HTML 檔案中，批次提取並分析台灣上市櫃公司財務指標的自動化工具。

### 主要功能
- **批次解析財報**：自動從數千個 HTML 檔案中提取結構化財務數據
- **多維度財務分析**：提取單季、累計、同比數據，包含損益表、資產負債表關鍵指標
- **名單過濾**：根據觀測站官方名單篩選目標公司，避免處理不必要的檔案
- **資料品質檢查**：自動驗證資料完整性並標記異常
- **涵蓋率驗證**：檢查哪些公司缺少財報檔案

### 解決的問題
1. 手動整理數百家公司財報耗時費力
2. XBRL 格式複雜，需要理解會計科目代號和 context 邏輯
3. 需要同時處理合併報表和個別報表
4. 需要計算 YoY 成長率、獲利率等衍生指標

---

## 資料夾結構

```
MOPS copy/
├── POC-tifrs-2025Q2/               # 主要程式碼資料夾
│   ├── process_financial_reports_v2.py    # 主程式 - 擴充版解析器 ⭐
│   ├── process_financial_reports.py       # 舊版解析器(簡化版)
│   ├── verify_coverage.py                 # 涵蓋率驗證工具
│   ├── find_missing_files.py              # 缺少檔案搜尋工具
│   ├── t163sb04_20251218_15322930.csv     # 官方上市櫃公司名單(2025Q3)
│   ├── t163sb04_20251117_223655421.csv    # 官方名單(2025Q3舊版)
│   ├── t163sb04_20251013_172201430.csv    # 官方名單(2025Q2)
│   ├── financial_metrics_2025Q3.csv       # 輸出結果(2025Q3)
│   ├── financial_metrics_2025Q2.csv       # 輸出結果(2025Q2)
│   └── missing_companies.csv              # 缺少財報的公司清單
├── tifrs-2025Q2/                   # 2025Q2 財報 HTML 檔案(~2600個)
├── tifrs-2025Q3/                   # 2025Q3 財報 HTML 檔案(~2000個)
├── tifrs-2025Q3-251117/            # 2025Q3 財報備份
├── 0. Presentations/               # 專案說明簡報
│   └── Data Flow.png               # 資料流程圖
├── MOPS_Manual.pdf                 # 觀測站使用手冊
└── README.md                       # 本文件
```

### 檔案用途說明

#### 核心程式
- **process_financial_reports_v2.py**：✅ **主要使用這個**
  - 最完整的版本，支援 50+ 個財務指標
  - 支援合併報表(cr)和個別報表(ir)
  - 自動計算 YoY 成長率、獲利率、負債比等衍生指標
  - 單位自動轉換(千元→百萬元)

- **process_financial_reports.py**：舊版簡化版
  - 較早期的版本，功能較少
  - 建議使用 v2 版本

#### 輔助工具
- **verify_coverage.py**：驗證涵蓋率
  - 比對官方名單和實際下載的 HTML 檔案
  - 產生缺少財報的公司清單

- **find_missing_files.py**：搜尋缺少的檔案
  - 檢查缺少的公司是否有其他格式的財報
  - 統計檔名格式分布

#### 資料檔案
- **t163sb04_*.csv**：觀測站官方名單
  - 從公開資訊觀測站下載的上市櫃公司清單
  - 編碼：Big5 或 CP950
  - 欄位：公司代號、公司名稱、產業別等

- **tifrs-2025Q*/**.html**：財報原始檔案
  - inline XBRL 格式的 HTML 財報
  - 檔名格式：`tifrs-fr1-m1-ci-cr-{股票代號}-2025Q2.html`
  - 從觀測站批次下載

---

## 環境設定

### Python 版本
- **Python 3.9+** (專案在 Python 3.9.6 測試通過)

### 必要套件
```bash
pip install beautifulsoup4 pandas
```

或使用 requirements.txt：
```bash
pip install -r requirements.txt
```

### requirements.txt 內容
```
beautifulsoup4>=4.12.0
pandas>=2.0.0
```

### 系統需求
- 記憶體：建議 4GB 以上(處理數千個 HTML 檔案)
- 硬碟空間：每季財報約 500MB-1GB

---

## 執行方式

### 1. 主要財報解析流程

#### 使用預設參數(推薦)
```bash
cd POC-tifrs-2025Q2
python3 process_financial_reports_v2.py
```

預設會處理：
- 官方名單：`t163sb04_20251218_15322930.csv`
- HTML 資料夾：`../tifrs-2025Q3`
- 輸出檔案：`financial_metrics_2025Q3.csv`

#### 使用自訂參數
```bash
python3 process_financial_reports_v2.py [官方CSV] [HTML資料夾] [輸出檔案]
```

範例：處理 2025Q2 資料
```bash
python3 process_financial_reports_v2.py \
  t163sb04_20251013_172201430.csv \
  ../tifrs-2025Q2 \
  financial_metrics_2025Q2.csv
```

### 2. 驗證涵蓋率

執行前建議先驗證涵蓋率，確認下載的財報檔案是否完整：

```bash
python3 verify_coverage.py [官方CSV] [HTML資料夾]
```

範例：
```bash
python3 verify_coverage.py t163sb04_20251218_15322930.csv ../tifrs-2025Q3
```

輸出：
- 涵蓋率統計
- 缺少財報的公司清單 → `missing_companies.csv`

### 3. 搜尋缺少的檔案

如果發現有公司缺少財報，可以檢查是否有其他格式的檔案：

```bash
python3 find_missing_files.py missing_companies.csv ../tifrs-2025Q3
```

---

## 資料流程

### 完整處理流程

```
1. 從觀測站下載
   ├── 官方公司名單 CSV (Big5編碼)
   └── 各公司財報 HTML (inline XBRL格式)
         │
2. 執行 verify_coverage.py
   ├── 驗證檔案完整性
   └── 產生 missing_companies.csv
         │
3. 執行 process_financial_reports_v2.py
   ├── 讀取官方名單
   ├── 過濾符合格式的 HTML 檔案
   ├── 批次解析財務指標
   └── 輸出 financial_metrics_2025Q3.csv
         │
4. 成果
   └── 結構化財務數據 CSV (UTF-8-SIG編碼)
```

### 詳細解析邏輯

#### Step 1: 檔案過濾
- 支援的檔案格式：
  - `tifrs-fr1-m1-ci-cr-*.html` (合併報表)
  - `tifrs-fr2-m1-ci-cr-*.html` (合併報表)
  - `tifrs-fr1-m1-ci-ir-*.html` (個別報表)
  - `tifrs-fr2-m1-ci-ir-*.html` (個別報表)
- 從檔名提取股票代號，比對官方名單

#### Step 2: HTML 解析
1. 使用 BeautifulSoup 解析 HTML
2. 提取公司基本資訊(代號、名稱、年度、季度)
3. 根據年度季度建立 context 字串
4. 用會計科目代號 + context 精確定位財務數據

#### Step 3: Context 邏輯

財報中的每個數字都有對應的 context，格式如下：

**損益表 - 單季**
- 當季：`From20250701To20250930` (2025Q3: 7/1-9/30)
- 去年同季：`From20240701To20240930` (2024Q3: 7/1-9/30)

**損益表 - 累計**
- 累計：`From20250101To20250930` (2025年初至Q3末)
- 去年累計：`From20240101To20240930` (2024年初至Q3末)

**資產負債表 - 時點**
- 期末：`AsOf20250930` (2025年9月30日)
- 去年同期：`AsOf20240930` (2024年9月30日)

#### Step 4: 會計科目代號

| 財務指標 | 會計科目代號 | 說明 |
|---------|------------|------|
| 營業收入 | 4000 | Revenue |
| 營業毛利 | 5900 | Gross Profit |
| 營業利益 | 6900 | Operating Income |
| 本期淨利(合併) | 8610 | Net Income (Consolidated) |
| 本期淨利(個別) | 8200 | Net Income (Parent) |
| 基本每股盈餘 | 9750 | Basic EPS |
| 資產總額 | 1XXX | Total Assets |
| 負債總額 | 2XXX | Total Liabilities |

#### Step 5: 數據處理
1. 解析數字(處理千分位、括號負數)
2. 處理 `sign="-"` 屬性
3. 單位轉換(千元 → 百萬元)
4. 計算衍生指標：
   - YoY 成長率 = (當期 - 去年同期) / |去年同期| × 100%
   - 獲利率 = 利潤 / 營收 × 100%
   - 負債比 = 負債 / 資產 × 100%

---

## 輸出檔案格式

### financial_metrics_2025Q3.csv

#### 編碼與格式
- **編碼**：UTF-8-SIG (在 Excel 中可正確顯示中文)
- **分隔符**：逗號(,)
- **共 50+ 個欄位**

#### 欄位說明

**基礎資訊**
- `company_id`: 股票代號(如：2330)
- `company_name`: 公司名稱(如：台積電)
- `year`: 年度(如：2025)
- `quarter`: 季度(1-4)
- `report_type`: 報表類型(合併/個別)

**單季數據(百萬元，除 EPS 外)**
- `revenue_q`: 當季營收
- `revenue_q_prev`: 去年同季營收
- `revenue_yoy`: 營收 YoY 成長率(%)
- `gross_profit_q`: 當季營業毛利
- `gross_profit_q_prev`: 去年同季毛利
- `gross_profit_yoy`: 毛利 YoY 成長率(%)
- `operating_income_q`: 當季營業利益
- `operating_income_q_prev`: 去年同季營業利益
- `operating_income_yoy`: 營業利益 YoY(%)
- `net_income_q`: 當季本期淨利
- `net_income_q_prev`: 去年同季淨利
- `net_income_yoy`: 淨利 YoY(%)
- `eps_q`: 當季 EPS(元)
- `eps_q_prev`: 去年同季 EPS(元)
- `eps_change_q`: EPS 變動值(元)

**累計數據(百萬元，除 EPS 外)**
- `revenue_ytd`: 年初至今營收
- `revenue_ytd_prev`: 去年同期累計營收
- `revenue_ytd_yoy`: 累計營收 YoY(%)
- `gross_profit_ytd`: 累計毛利
- `operating_income_ytd`: 累計營業利益
- `net_income_ytd`: 累計淨利
- `eps_ytd`: 累計 EPS(元)
- (以下類推...)

**資產負債數據(百萬元)**
- `total_assets_q`: 期末總資產
- `total_assets_q_prev`: 去年同期總資產
- `total_liabilities_q`: 期末總負債
- `total_liabilities_q_prev`: 去年同期總負債
- `debt_ratio_q`: 負債比(%)
- `debt_ratio_q_prev`: 去年同期負債比(%)
- `debt_ratio_yoy_change`: 負債比變動(百分點)

**獲利率數據(%)**
- `gross_margin_q`: 毛利率
- `gross_margin_q_prev`: 去年同期毛利率
- `gross_margin_yoy_change`: 毛利率變動(百分點)
- `operating_margin_q`: 營益率
- `operating_margin_q_prev`: 去年同期營益率
- `operating_margin_yoy_change`: 營益率變動(百分點)
- `net_margin_q`: 淨利率
- `net_margin_q_prev`: 去年同期淨利率
- `net_margin_yoy_change`: 淨利率變動(百分點)

#### 資料品質標記
- 完整資料：`data_quality = "complete"`
- 資料不完整：`data_quality = "incomplete"`(部分欄位為空)
- 解析失敗：`data_quality = "failed"`(有 error 欄位)

---

## 已知限制與注意事項

### 1. 檔案格式依賴
- **限制**：只能處理觀測站的 inline XBRL 格式 HTML 檔案
- **影響**：如果觀測站改變檔案格式或結構，程式可能需要更新
- **建議**：定期檢查檔案格式是否變更

### 2. 會計科目代號差異
- **問題**：合併報表與個別報表的淨利科目代號不同
  - 合併報表：8610 (歸屬母公司業主)
  - 個別報表：8200 (本期淨利)
- **處理**：程式已自動判斷並使用正確代號
- **注意**：不同產業可能有特殊會計科目，需手動調整

### 3. 特殊公司處理
- **金控/銀行**：損益表結構不同(無營業毛利)
- **部分欄位為 None**：正常現象
- **建議**：針對金融業可能需要客製化程式

### 4. 編碼問題
- **官方 CSV**：通常是 Big5 或 CP950 編碼
- **輸出 CSV**：UTF-8-SIG 編碼(相容 Excel)
- **注意**：程式已處理多種編碼嘗試

### 5. 檔案涵蓋率
- **實際涵蓋率**：約 90-95%
- **原因**：
  - 新上市公司可能尚未有財報
  - 部分公司暫停交易
  - 某些產業不適用 IFRS
- **建議**：執行前先用 `verify_coverage.py` 檢查

### 6. Context 解析限制
- **假設**：財報格式標準化
- **風險**：如果公司財報格式異常，可能解析失敗
- **檢查**：留意 `context_warning` 欄位

### 7. 效能考量
- **處理時間**：2000 個檔案約需 3-5 分鐘
- **記憶體使用**：峰值約 1-2GB
- **建議**：處理大批資料時關閉其他程式

---

## 疑難排解

### 問題 1：找不到檔案或模組

**錯誤訊息**：
```
ModuleNotFoundError: No module named 'bs4'
```

**解決方式**：
```bash
pip install beautifulsoup4 pandas
```

---

### 問題 2：CSV 讀取失敗

**錯誤訊息**：
```
UnicodeDecodeError: 'utf-8' codec can't decode byte...
```

**原因**：官方 CSV 是 Big5 編碼

**解決方式**：
- 程式已內建多重編碼嘗試機制(big5, utf-8, cp950)
- 如果仍失敗，手動轉換編碼：
  ```bash
  iconv -f big5 -t utf-8 input.csv > output.csv
  ```

---

### 問題 3：涵蓋率過低

**狀況**：只找到少數公司的財報

**檢查清單**：
1. 確認 HTML 資料夾路徑正確
   ```bash
   ls ../tifrs-2025Q3 | wc -l  # 應該有 1500+ 個檔案
   ```

2. 確認檔案命名格式正確
   ```bash
   ls ../tifrs-2025Q3 | head -5
   # 應該看到: tifrs-fr1-m1-ci-cr-XXXX-2025Q3.html
   ```

3. 執行涵蓋率驗證
   ```bash
   python3 verify_coverage.py
   ```

---

### 問題 4：某些欄位全是 None

**可能原因**：
1. **金融業特殊**：銀行/保險/金控沒有營業毛利
2. **檔案格式異常**：公司使用非標準格式
3. **會計科目代號錯誤**：該公司使用不同代號

**檢查方式**：
1. 手動開啟該公司的 HTML 檔案
2. 搜尋會計科目代號(如：4000)
3. 檢查 context 是否正確

**解決方式**：
- 如果是特定產業問題：修改 `codes` 字典
- 如果是個別公司問題：可能需要個案處理

---

### 問題 5：YoY 成長率異常(如 -500%)

**原因**：去年同期數據為負或接近零

**說明**：
- 去年虧損，今年獲利 → YoY 可能是 500%+
- 去年微利，今年虧損 → YoY 可能是 -1000%
- **這是正常現象**，不是程式錯誤

**處理建議**：
- 分析時設定 YoY 上下限(如 -300% ~ 500%)
- 搭配絕對金額變化分析

---

### 問題 6：處理速度很慢

**原因**：
- 檔案數量太多(2000+ 個)
- 硬碟 I/O 瓶頸

**優化建議**：
1. 使用 SSD 而非 HDD
2. 減少不必要的檔案處理：
   ```python
   # 只處理特定公司
   official_ids = {'2330', '2317', '2454'}  # 台積電、鴻海、聯發科
   ```

---

### 問題 7：Excel 開啟 CSV 後中文亂碼

**原因**：Excel 未正確識別 UTF-8-SIG

**解決方式**：
1. **方法 1**：不要直接雙擊開啟
   - 開啟 Excel
   - 檔案 → 匯入 → 從文字檔
   - 選擇「UTF-8」編碼

2. **方法 2**：使用 Google Sheets
   - 上傳 CSV 到 Google Drive
   - 自動正確識別編碼

3. **方法 3**：轉換為 Excel 格式
   ```python
   import pandas as pd
   df = pd.read_csv('financial_metrics_2025Q3.csv')
   df.to_excel('financial_metrics_2025Q3.xlsx', index=False)
   ```

---

### 問題 8：某些公司缺少財報檔案

**確認流程**：
1. 檢查公司是否為新上市
2. 檢查是否為特殊產業(如：KY 公司)
3. 使用 `find_missing_files.py` 搜尋其他格式

**範例**：
```bash
python3 find_missing_files.py missing_companies.csv ../tifrs-2025Q3
```

**如果找到其他格式**：
- 修改 `process_financial_reports_v2.py` 中的 `patterns` 列表
- 加入該格式(如：`tifrs-fr1-m1-basi-cr-*.html`)

---

## 進階使用

### 1. 處理不同季度資料

```bash
# 2025Q2
python3 process_financial_reports_v2.py \
  t163sb04_20251013_172201430.csv \
  ../tifrs-2025Q2 \
  financial_metrics_2025Q2.csv

# 2025Q3
python3 process_financial_reports_v2.py \
  t163sb04_20251218_15322930.csv \
  ../tifrs-2025Q3 \
  financial_metrics_2025Q3.csv
```

### 2. 只處理特定產業

修改程式碼，在 `load_official_list()` 函數後加入篩選：

```python
# 只保留電子業(代號 2xxx, 3xxx, 6xxx)
official_ids = {cid for cid in official_ids
                if cid.startswith(('2', '3', '6'))}
```

### 3. 批次處理多個季度

```bash
#!/bin/bash
for quarter in Q1 Q2 Q3 Q4; do
    python3 process_financial_reports_v2.py \
      official_2025${quarter}.csv \
      ../tifrs-2025${quarter} \
      financial_metrics_2025${quarter}.csv
done
```

### 4. 資料合併分析

使用 pandas 合併多季度資料：

```python
import pandas as pd

q2 = pd.read_csv('financial_metrics_2025Q2.csv')
q3 = pd.read_csv('financial_metrics_2025Q3.csv')

# 垂直合併
all_data = pd.concat([q2, q3], ignore_index=True)

# 按公司分組分析
grouped = all_data.groupby('company_id')
```

---

## 技術細節

### HTML 結構範例

財報 HTML 中的數字標籤格式：

```html
<ix:nonFraction
  name="ifrs-full:Revenue"
  contextRef="From20250701To20250930"
  unitRef="TWD"
  decimals="0"
  sign="-"
>123,456,789</ix:nonFraction>
```

解析邏輯：
1. 找到 `name="ifrs-full:Revenue"` 的標籤
2. 確認 `contextRef` 符合當季期間
3. 提取文字內容並解析數字(處理千分位)
4. 檢查 `sign` 屬性，若為 `-` 則轉為負數

### Context 建構邏輯

```python
def build_contexts(year: str, quarter: str) -> Dict[str, str]:
    # Q3 範例
    if quarter == "3":
        return {
            'q_current': 'From20250701To20250930',      # 當季
            'q_prev': 'From20240701To20240930',          # 去年同季
            'ytd_current': 'From20250101To20250930',     # 累計
            'ytd_prev': 'From20240101To20240930',        # 去年累計
            'bs_current': 'AsOf20250930',                # 期末
            'bs_prev': 'AsOf20240930',                   # 去年同期末
        }
```

---

## 常見問題 FAQ

### Q1: 為什麼有些公司有兩筆資料(合併+個別)?
A: 程式同時處理合併報表(cr)和個別報表(ir)，可透過 `report_type` 欄位區分。一般分析使用合併報表即可。

### Q2: 金額單位是什麼?
A: 損益表、資產負債表數據單位為**百萬元(NT$M)**，EPS 單位為**元(NT$)**。

### Q3: YoY 計算公式是什麼?
A: `YoY(%) = (當期 - 去年同期) / |去年同期| × 100`

### Q4: 可以處理年報嗎?
A: 可以，年報就是 Q4 的財報，程式支援 Q1-Q4。

### Q5: 如何加入新的財務指標?
A:
1. 找到對應的會計科目代號(參考 MOPS_Manual.pdf)
2. 在 `codes` 字典中加入
3. 使用 `extract_by_code_and_context()` 提取

### Q6: 支援個股比較分析嗎?
A: 輸出的 CSV 已包含所有需要的數據，可用 Excel、Python pandas 或 Power BI 進行後續分析。

### Q7: 資料來源可靠嗎?
A: 資料直接來自公開資訊觀測站，與官方網站顯示的數據一致。

### Q8: 多久更新一次?
A: 每季財報公布後(大約 4/15、8/15、11/15、隔年 3/30)，從觀測站下載最新財報並執行程式即可。

---

## 參考資源

- [公開資訊觀測站](https://mops.twse.com.tw/)
- [inline XBRL 說明文件](https://mops.twse.com.tw/mops/web/t163sb04)
- MOPS_Manual.pdf (專案資料夾內)
- Data Flow.png (流程圖，在 0. Presentations 資料夾)

---

## 維護建議

### 定期檢查項目
1. **每季執行後**：
   - 執行 `verify_coverage.py` 檢查涵蓋率
   - 確認輸出檔案無異常值
   - 抽樣比對觀測站網頁數據

2. **年度檢查**：
   - 確認會計科目代號無變更
   - 更新官方名單 CSV
   - 備份舊資料

3. **遇到問題時**：
   - 檢查觀測站是否更新檔案格式
   - 查看是否有新的會計準則變更
   - 測試少量檔案找出問題點

---

## 版本歷史

- **v2 (2024/12)**：process_financial_reports_v2.py
  - 支援 50+ 個財務指標
  - 新增累計數據(YTD)
  - 新增獲利率、負債比分析
  - 支援個別報表

- **v1 (2024/10)**：process_financial_reports.py
  - 基礎版本
  - 僅支援基本損益表指標

---

## 聯絡與支援

如有問題或建議，請聯絡專案維護者。

**祝使用順利！**
