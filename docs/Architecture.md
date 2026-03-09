# 台股基本面選股器 - Final Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCE LAYER                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              ┌─────▼─────┐   ┌────▼────┐   ┌──────▼──────┐
              │   MOPS    │   │ TWSE    │   │  Industry   │
              │   XBRL    │   │ Stock   │   │ Classification│
              │ Financial │   │ Price   │   │    Data     │
              │  Reports  │   │  API    │   │             │
              └─────┬─────┘   └────┬────┘   └──────┬──────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                       DATA COLLECTION LAYER                         │
│                                                                     │
│  ┌──────────────────┐      ┌──────────────────┐                  │
│  │  Daily Crawler   │      │  Weekly Crawler  │                  │
│  │  (New Reports)   │      │  (Stock Prices)  │                  │
│  │                  │      │                  │                  │
│  │  - Check MOPS    │      │  - Fetch prices  │                  │
│  │  - Download XBRL │      │  - Calculate P/E │                  │
│  │  - Parse data    │      │  - Update DB     │                  │
│  └────────┬─────────┘      └────────┬─────────┘                  │
│           │                         │                            │
└───────────┼─────────────────────────┼────────────────────────────┘
            │                         │
            └────────────┬────────────┘
                         │
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA PROCESSING LAYER                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              Financial Metrics Calculator                     │ │
│  │                                                               │ │
│  │  - ROE (股東權益報酬率)                                        │ │
│  │  - Revenue Growth Rate (營收年增率)                           │ │
│  │  - Net Income Growth Rate (淨利年增率)                        │ │
│  │  - Debt Ratio (負債比率)                                       │ │
│  │  - Gross Margin (毛利率)                                       │ │
│  │  - Operating Margin (營業利益率)                              │ │
│  │  - Net Margin (純益率)                                         │ │
│  │  - P/E Ratio (本益比)                                          │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │                                       │
│  ┌────────────────────────▼─────────────────────────────────────┐ │
│  │            Industry Benchmark Calculator                      │ │
│  │                                                               │ │
│  │  - Group by industry                                         │ │
│  │  - Calculate median ROE per industry                         │ │
│  │  - Calculate average P/E per industry                        │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │                                       │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYER                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                   PostgreSQL / SQLite                         │ │
│  │                                                               │ │
│  │  Tables:                                                      │ │
│  │  - companies (公司基本資料)                                    │ │
│  │  - financial_reports (季度/年度財報)                           │ │
│  │  - stock_prices (股價資料)                                     │ │
│  │  - industry_benchmarks (產業指標)                             │ │
│  │  - screening_results (篩選結果cache)                          │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │                                       │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BUSINESS LOGIC LAYER                           │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              Screening Engine (FastAPI)                     │   │
│  │                                                             │   │
│  │  /api/screen                                                │   │
│  │  ├─ Apply Quality filters                                   │   │
│  │  │  - ROE > industry median                                 │   │
│  │  │  - Debt ratio < 60%                                      │   │
│  │  │  - Revenue growth > 0%                                   │   │
│  │  ├─ Apply Value filters                                     │   │
│  │  │  - P/E < industry avg × 0.85                             │   │
│  │  └─ Return filtered company list                            │   │
│  │                                                             │   │
│  │  /api/daily-reports                                         │   │
│  │  └─ Return newly uploaded reports today                     │   │
│  │                                                             │   │
│  │  /api/company/{id}                                          │   │
│  │  └─ Return detailed company data                            │   │
│  └──────────────────────┬──────────────────────────────────────┘   │
│                         │                                          │
│  ┌──────────────────────▼──────────────────────────────────────┐   │
│  │               AI Analysis Service                            │   │
│  │                                                             │   │
│  │  - Call Claude API                                          │   │
│  │  - Detect anomalies (異常值偵測)                             │   │
│  │    - ROE improvement                                        │   │
│  │    - Margin expansion                                       │   │
│  │    - Growth acceleration                                    │   │
│  │  - Generate insights (生成分析文字)                          │   │
│  │    - Highlight key metrics                                  │   │
│  │    - Compare to industry                                    │   │
│  │    - Flag quality concerns                                  │   │
│  │  - Assign signal strength (⭐⭐⭐ / ⭐⭐ / ⚠️)                │   │
│  └──────────────────────┬──────────────────────────────────────┘   │
│                         │                                          │
└─────────────────────────┼──────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                   React Frontend (Vite)                       │ │
│  │                                                               │ │
│  │  Pages:                                                       │ │
│  │  ┌─────────────────────────────────────────────────────┐    │ │
│  │  │  1. 財報搶先看 (Daily Reports)                       │    │ │
│  │  │     - Today's newly uploaded reports                │    │ │
│  │  │     - AI highlights                                 │    │ │
│  │  │     - Quick screening results                       │    │ │
│  │  └─────────────────────────────────────────────────────┘    │ │
│  │  ┌─────────────────────────────────────────────────────┐    │ │
│  │  │  2. 全市場選股器 (Market Screener)                   │    │ │
│  │  │     - Quality + Value strategy                      │    │ │
│  │  │     - Filtered results list                         │    │ │
│  │  │     - Sorting & filtering                           │    │ │
│  │  └─────────────────────────────────────────────────────┘    │ │
│  │  ┌─────────────────────────────────────────────────────┐    │ │
│  │  │  3. 個股詳細頁 (Company Detail)                      │    │ │
│  │  │     - AI investment highlights                      │    │ │
│  │  │     - Financial metrics                             │    │ │
│  │  │     - Industry comparison                           │    │ │
│  │  │     - Historical trends                             │    │ │
│  │  └─────────────────────────────────────────────────────┘    │ │
│  │                                                               │ │
│  │  Components:                                                  │ │
│  │  - CompanyCard (公司卡片)                                     │ │
│  │  - AIHighlight (AI標註區塊)                                  │ │
│  │  - MetricsTable (指標表格)                                   │ │
│  │  - IndustryComparison (產業比較圖表)                         │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │                                       │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                            ▼
                      ┌──────────┐
                      │  User    │
                      │ (Browser)│
                      └──────────┘
```

---

## Technology Stack

### Backend
- **Language**: Python 3.10+
- **Web Framework**: FastAPI (async, modern, auto-docs)
- **Data Processing**: pandas, numpy
- **XBRL Parsing**: 你現有的parser (已驗證可用)
- **Stock Price**: yfinance or TWSE API
- **Database**: SQLite (MVP) → PostgreSQL (production)
- **AI Integration**: Anthropic Claude API

### Frontend
- **Framework**: React 18 + Vite
- **Language**: JavaScript/TypeScript
- **UI Library**: Tailwind CSS
- **Charts**: Recharts (for industry comparison)
- **Icons**: Lucide React
- **State Management**: React hooks (useState, useEffect)

### DevOps
- **Version Control**: Git + GitHub
- **Scheduling**: cron (Linux) or APScheduler (Python)
- **Deployment**: 
  - MVP: Local + Vercel (frontend) + Railway (backend)
  - Production: AWS / GCP

---

## Data Flow

### Flow 1: Daily Report Monitoring (每日財報監控)

```
1. Cron job triggers at 8:00 AM daily
2. Crawler checks MOPS for new reports uploaded yesterday
3. Download & parse new XBRL files
4. Calculate financial metrics
5. Store in database
6. Trigger AI analysis for new companies
7. Cache results
8. Frontend fetches /api/daily-reports
9. Display to user with AI highlights
```

### Flow 2: Market Screening (全市場篩選)

```
1. User clicks "Quality + Value" strategy
2. Frontend calls /api/screen
3. Backend queries database:
   - Filter: ROE > industry median
   - Filter: Debt ratio < 60%
   - Filter: Revenue growth > 0%
   - Filter: P/E < industry avg × 0.85
4. For each result, call AI analysis service
5. Generate highlights & assign signals
6. Return sorted list (by signal strength)
7. Frontend renders CompanyCard components
```

### Flow 3: Company Detail View (個股詳細頁)

```
1. User clicks on a company card
2. Frontend calls /api/company/{id}
3. Backend queries:
   - Company basic info
   - Latest financial report
   - Historical data (4 quarters)
   - Industry benchmarks
4. Call Claude API to generate analysis:
   - Prompt: "Analyze this company's financials..."
   - Include: metrics, trends, industry comparison
   - Output: 2-3 paragraph analysis + bullet points
5. Return structured data
6. Frontend renders detail page
```

---

## API Design

### Endpoint 1: GET /api/daily-reports

**Purpose**: Get newly uploaded reports today

**Response**:
```json
{
  "date": "2026-03-08",
  "total_new_reports": 5,
  "quality_value_matches": 2,
  "reports": [
    {
      "company_id": "2330",
      "company_name": "台積電",
      "industry": "半導體業",
      "upload_date": "2026-03-08",
      "days_early": 23,
      "ai_highlight": "淨利年增78%，但本益比僅18.2倍...",
      "signal_strength": "strong",
      "metrics": {
        "roe": 28.5,
        "revenue_growth": 33.8,
        "net_income_growth": 78.2,
        "pe_ratio": 18.2,
        "industry_avg_pe": 22.5
      }
    }
  ]
}
```

### Endpoint 2: POST /api/screen

**Purpose**: Screen market with Quality + Value strategy

**Request**:
```json
{
  "strategy": "quality_value"
}
```

**Response**:
```json
{
  "total_companies": 955,
  "matched_companies": 47,
  "results": [
    {
      "company_id": "2330",
      "company_name": "台積電",
      "industry": "半導體業",
      "signal_strength": "strong",
      "ai_highlight": "...",
      "metrics": { ... }
    }
  ]
}
```

### Endpoint 3: GET /api/company/{id}

**Purpose**: Get detailed company analysis

**Response**:
```json
{
  "company_id": "2330",
  "company_name": "台積電",
  "industry": "半導體業",
  "ai_analysis": {
    "summary": "台積電展現強勁獲利能力...",
    "highlights": [
      "ROE 28.5%遠高於產業中位數22%",
      "淨利年增78%，成長動能強勁"
    ],
    "concerns": []
  },
  "current_metrics": { ... },
  "historical_trends": [ ... ],
  "industry_comparison": { ... }
}
```

---

## Database Schema

### Table: companies
```sql
CREATE TABLE companies (
    id VARCHAR(10) PRIMARY KEY,  -- 股票代號 e.g. "2330"
    name VARCHAR(100) NOT NULL,  -- 公司名稱
    industry VARCHAR(50),         -- 產業別
    listed_date DATE              -- 上市日期
);
```

### Table: financial_reports
```sql
CREATE TABLE financial_reports (
    id SERIAL PRIMARY KEY,
    company_id VARCHAR(10) REFERENCES companies(id),
    report_type VARCHAR(20),      -- 'annual' or 'quarterly'
    year INTEGER,
    quarter INTEGER,              -- NULL for annual reports
    upload_date DATE,             -- MOPS上傳日期
    
    -- Income Statement
    revenue DECIMAL(15,2),
    gross_profit DECIMAL(15,2),
    operating_income DECIMAL(15,2),
    net_income DECIMAL(15,2),
    eps DECIMAL(10,2),
    
    -- Balance Sheet
    total_assets DECIMAL(15,2),
    total_liabilities DECIMAL(15,2),
    shareholders_equity DECIMAL(15,2),
    
    -- Calculated Metrics
    roe DECIMAL(5,2),
    debt_ratio DECIMAL(5,2),
    gross_margin DECIMAL(5,2),
    operating_margin DECIMAL(5,2),
    net_margin DECIMAL(5,2),
    
    -- Growth Rates (YoY)
    revenue_growth_rate DECIMAL(5,2),
    net_income_growth_rate DECIMAL(5,2),
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Table: stock_prices
```sql
CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    company_id VARCHAR(10) REFERENCES companies(id),
    date DATE,
    close_price DECIMAL(10,2),
    pe_ratio DECIMAL(10,2),        -- Calculated: price / EPS
    pb_ratio DECIMAL(10,2),        -- Calculated: price / book value
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Table: industry_benchmarks
```sql
CREATE TABLE industry_benchmarks (
    id SERIAL PRIMARY KEY,
    industry VARCHAR(50),
    year INTEGER,
    quarter INTEGER,
    
    median_roe DECIMAL(5,2),
    avg_pe_ratio DECIMAL(10,2),
    avg_debt_ratio DECIMAL(5,2),
    
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## AI Integration Design

### Claude API Usage

**Prompt Template for Company Analysis:**
```
分析以下台股公司的財務表現：

公司：{company_name} ({company_id})
產業：{industry}

最新財報數據：
- ROE: {roe}% (產業中位數: {industry_median_roe}%)
- 營收: {revenue}億 (年增 {revenue_growth}%)
- 淨利: {net_income}億 (年增 {net_income_growth}%)
- 毛利率: {gross_margin}% (去年同期: {prev_gross_margin}%)
- 負債比率: {debt_ratio}%
- 本益比: {pe_ratio} (產業平均: {industry_avg_pe})

請生成：
1. 一句話投資亮點（30字內）
2. 獲利能力分析（1-2句）
3. 估值評估（1-2句）
4. 如有疑慮請標註（optional）

輸出格式為JSON：
{
  "highlight": "...",
  "profitability_analysis": "...",
  "valuation_assessment": "...",
  "concerns": "..." or null
}
```

**Token估算（per company）:**
- Input: ~300 tokens
- Output: ~150 tokens
- Total: ~450 tokens per analysis

**Cost估算：**
- Claude Sonnet 4: $3 / 1M input tokens, $15 / 1M output tokens
- Analyze 100 companies: ~$0.07
- Daily 5-10 new reports: ~$0.01/day
- Monthly: ~$0.30

---

## Deployment Strategy

### Phase 1: MVP (Local Development)
- Run backend locally: `uvicorn main:app --reload`
- Run frontend locally: `npm run dev`
- SQLite database (single file)
- Manual data updates

### Phase 2: Demo Version
- Frontend: Deploy to Vercel (free tier)
- Backend: Deploy to Railway / Render (free tier)
- PostgreSQL: Railway managed DB
- Cron: GitHub Actions for daily updates

### Phase 3: Production (Post-MVP)
- Frontend: Vercel Pro
- Backend: AWS EC2 / GCP Cloud Run
- Database: AWS RDS / GCP Cloud SQL
- Monitoring: Sentry, DataDog

---

## Development Timeline (23 days until 3/31)

### Week 1 (3/8-3/14): Foundation
- Day 1-2: Setup project structure, database schema
- Day 3-4: Data pipeline (XBRL + stock price)
- Day 5-6: Backend API endpoints
- Day 7: Testing & debugging

### Week 2 (3/15-3/21): Core Features
- Day 8-9: Screening engine implementation
- Day 10-11: AI analysis integration
- Day 12-13: Frontend basic UI
- Day 14: Integration testing

### Week 3 (3/22-3/28): Polish & Deploy
- Day 15-16: Frontend refinement
- Day 17-18: Daily reports feature
- Day 19-20: Deployment & testing
- Day 21: Documentation

### Final Days (3/29-3/31): Demo Prep
- Day 22: Record demo video
- Day 23: Final polish & launch

---

## Success Metrics

### Technical Metrics
- Data coverage: 955家上市櫃公司 (100%)
- Update frequency: 每日新財報 + 每週股價
- API response time: < 2 seconds
- Frontend load time: < 3 seconds

### Product Metrics
- 財報搶先看：每日顯示新上傳報告
- 選股器：找出20-50家符合Quality+Value標準的公司
- AI分析：準確標註改善訊號與警示

### Portfolio Metrics
- GitHub stars: Target 10+ (show traction)
- Demo video views: Track engagement
- Interview callbacks: Success indicator

---

**Last Updated**: 2026-03-08
**Version**: 1.0 - Final Architecture
