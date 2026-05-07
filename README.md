# 台股基本面選股器

自動化財報分析工具，從955家上市櫃公司中篩選「體質好且被低估」的投資標的。

## 功能

- **財報自動處理**：從MOPS解析XBRL格式季報，提取20+財務指標
- **ROE計算**：自動計算股東權益報酬率
- **股價整合**：整合即時股價與本益比
- **智慧篩選**：Quality + Value策略，結合產業benchmark分析
- **AI評分**：自動標註改善幅度大的公司（⭐⭐⭐/⭐⭐）

## 使用

```bash
# 1. 執行財報解析
python src/parse_mops_reports.py

# 2. 打開Jupyter Notebook
jupyter notebook notebooks/stock_screening.ipynb

# 3. 執行所有cells，查看篩選結果
```

## 技術架構

- **資料處理**：Python + pandas + BeautifulSoup4
- **股價資料**：yfinance API
- **分析工具**：Jupyter Notebook
- **選股策略**：產業相對估值 + 財務品質篩選

## 成果

- 涵蓋955家上市櫃公司（94%覆蓋率）
- 自動篩選出10-15%符合Quality+Value標準的標的
- 從手動查詢半天 → 自動化3分鐘