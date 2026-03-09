# 台股基本面選股器

AI-powered台灣股市基本面篩選工具，幫助投資者找出被低估的優質公司。

## 核心功能

- **財報搶先看**：每日追蹤MOPS新上傳的年報，AI自動分析亮點
- **Quality + Value選股**：結合獲利品質與估值優勢，篩選出值得關注的股票
- **AI智能分析**：自動標註財報異常訊號與投資機會

## 技術架構

- **Backend**: Python + FastAPI
- **Frontend**: React + Vite + Tailwind CSS
- **Database**: SQLite (MVP) → PostgreSQL
- **AI**: Claude API
- **Data Source**: MOPS XBRL財報 + 台灣證交所股價

## 專案文件

- [選股判斷標準](./docs/選股判斷標準.md) - Quality + Value策略邏輯與篩選條件
- [系統架構](./docs/Architecture.md) - 完整技術架構與開發規劃

## 開發狀態

🚧 開發中 - 預計2026年3月底完成MVP

---

**作者**: Felice Dou  
**目的**: AI Product Manager Portfolio Project
